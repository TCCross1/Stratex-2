"""STRATEX™ Sub-Surface Ice & Water Shield Detection — CV Pipeline.

Strict-typed module that validates parsed thermal-IR roof-valley frames against
the Ice & Water Shield (I&WS) compliance rule set and routes uncertain frames
to the active P1 Dynamic Telemetry Anomaly Halting Loop.

The raw radiometric pixel processing runs on the drone/edge SDK (DJI Matrice
thermal SDK + a 0.92 emissivity-corrected radiometric pass). This module is
the platform-side validator that:

  1. Accepts a parsed valley-frame payload (delta-T band stats, edge metrics,
     capture-window timestamps, valley track polyline ID).
  2. Enforces the four ingestion preconditions (emissivity, ΔT band, valley
     mask geometry, post-sunset capture window).
  3. Discriminates `Ice_Water_Shield_Present` vs. `Moisture_Anomaly`.
  4. Emits a halt-payload to the Overseer queue if confidence < 0.90.

Wire-compatible with the existing `/api/telemetry/halt` POST + the
`db.materials_config` / `db.sales_targets` collections. Pure functions; the
endpoint handler lives in server.py and imports `analyze_valley_frame`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Final, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Radiometric & geometric constants (TASK 1 + 2)
# ---------------------------------------------------------------------------
ASPHALT_SHINGLE_EMISSIVITY: Final[float] = 0.92            # ε for composition shingles
DELTA_T_LOWER_C: Final[float] = 0.5                       # inclusive band lower bound (°C)
DELTA_T_UPPER_C: Final[float] = 1.5                       # inclusive band upper bound (°C)

VALLEY_MASK_HALF_WIDTH_IN: Final[float] = 18.0            # 18" on each side of centerline
VALLEY_MASK_TOTAL_WIDTH_IN: Final[float] = 36.0           # 36" total band width
VALLEY_MASK_TOLERANCE_IN: Final[float] = 2.0              # ±2" parameter constraint

POST_SUNSET_WINDOW_START_HOURS: Final[int] = 2            # sunset + 2h
POST_SUNSET_WINDOW_END_HOURS: Final[int] = 6              # sunset + 6h

CONFIDENCE_HALT_THRESHOLD: Final[float] = 0.90            # P1 halting cutoff
LINEAR_EDGE_STRAIGHTNESS_MIN: Final[float] = 0.92         # 1.0 = perfectly linear
STANDARD_ROLL_WIDTH_TOLERANCE_IN: Final[float] = 1.5      # I&WS rolls are 36" ± mfg tolerance


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------
class ValleyClassification(str, Enum):
    ICE_WATER_SHIELD_PRESENT = "Ice_Water_Shield_Present"
    MOISTURE_ANOMALY = "Moisture_Anomaly"
    UNVERIFIED_HALT = "Unverified_Halt"


class EdgeProfile(BaseModel):
    """Geometric description of the thermal anomaly's boundary."""
    model_config = ConfigDict(extra="forbid")

    straightness_score: float = Field(..., ge=0.0, le=1.0,
        description="1.0 = perfectly linear; 0.0 = fully amorphous.")
    follows_gravity_channels: bool = Field(...,
        description="True iff the anomaly bleeds down rafter channels under gravity.")
    measured_band_width_in: float = Field(..., gt=0.0,
        description="Observed continuous-band width across the valley (inches).")
    centerline_offset_in: float = Field(..., ge=0.0,
        description="Band-centroid offset from the valley centerline (inches).")


class CaptureContext(BaseModel):
    """Capture-time metadata sourced from the drone telemetry stream."""
    model_config = ConfigDict(extra="forbid")

    captured_at_utc: datetime
    sunset_utc: datetime
    surface_emissivity: float = Field(..., gt=0.0, le=1.0)

    @field_validator("captured_at_utc", "sunset_utc")
    @classmethod
    def _require_tzaware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("datetimes must be timezone-aware (UTC)")
        return v.astimezone(timezone.utc)


class ValleyFrame(BaseModel):
    """Single parsed thermal-IR roof-valley frame ready for compliance validation."""
    model_config = ConfigDict(extra="forbid")

    frame_id: str = Field(..., min_length=1)
    contractor_id: str = Field(..., min_length=1)
    job_id: str = Field(..., min_length=1)
    valley_track_id: str = Field(..., min_length=1)

    capture: CaptureContext
    delta_t_band_c: Tuple[float, float] = Field(...,
        description="(min, max) ΔT observed across the candidate band, in °C.")
    edge: EdgeProfile
    base_confidence: float = Field(..., ge=0.0, le=1.0,
        description="Drone-side CV classifier confidence (pre-platform validation).")


class PreconditionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    passed: bool
    detail: str


class IceShieldAnalysis(BaseModel):
    """Result of the full pipeline pass on a single ValleyFrame."""
    model_config = ConfigDict(extra="forbid")

    frame_id: str
    classification: ValleyClassification
    confidence: float = Field(..., ge=0.0, le=1.0)
    halted: bool
    preconditions: List[PreconditionResult]
    has_ice_and_water_shield: bool
    code_compliant_underlayment: bool
    flag_for_estimation_pipeline: bool
    halt_payload: Optional[dict] = None
    reasoning: str


# ---------------------------------------------------------------------------
# TASK 1 — Thermodynamic precondition checks
# ---------------------------------------------------------------------------
def _check_emissivity(ctx: CaptureContext) -> PreconditionResult:
    expected = ASPHALT_SHINGLE_EMISSIVITY
    ok = abs(ctx.surface_emissivity - expected) < 1e-6
    return PreconditionResult(
        name="emissivity_calibration",
        passed=ok,
        detail=f"ε observed={ctx.surface_emissivity:.4f}, expected={expected:.2f}",
    )


def _check_delta_t_band(delta_t: Tuple[float, float]) -> PreconditionResult:
    lo, hi = delta_t
    in_band = (lo >= DELTA_T_LOWER_C) and (hi <= DELTA_T_UPPER_C) and (lo <= hi)
    return PreconditionResult(
        name="delta_t_band",
        passed=in_band,
        detail=f"ΔT=[{lo:.2f}, {hi:.2f}]°C; required ⊆ [{DELTA_T_LOWER_C}, {DELTA_T_UPPER_C}]°C",
    )


def _check_capture_window(ctx: CaptureContext) -> PreconditionResult:
    start = ctx.sunset_utc + timedelta(hours=POST_SUNSET_WINDOW_START_HOURS)
    end = ctx.sunset_utc + timedelta(hours=POST_SUNSET_WINDOW_END_HOURS)
    ok = start <= ctx.captured_at_utc <= end
    return PreconditionResult(
        name="post_sunset_window",
        passed=ok,
        detail=f"capture={ctx.captured_at_utc.isoformat()} window=[{start.isoformat()}, {end.isoformat()}]",
    )


# ---------------------------------------------------------------------------
# TASK 2 — VALLEY_MASK spatial validation
# ---------------------------------------------------------------------------
def _check_valley_mask(edge: EdgeProfile) -> PreconditionResult:
    width_ok = abs(edge.measured_band_width_in - VALLEY_MASK_TOTAL_WIDTH_IN) <= VALLEY_MASK_TOLERANCE_IN
    centered_ok = edge.centerline_offset_in <= VALLEY_MASK_TOLERANCE_IN
    ok = width_ok and centered_ok
    return PreconditionResult(
        name="valley_mask",
        passed=ok,
        detail=(
            f"band_width={edge.measured_band_width_in:.2f}\" required "
            f"{VALLEY_MASK_TOTAL_WIDTH_IN}±{VALLEY_MASK_TOLERANCE_IN}\"; "
            f"centerline_offset={edge.centerline_offset_in:.2f}\" "
            f"max={VALLEY_MASK_TOLERANCE_IN}\""
        ),
    )


# ---------------------------------------------------------------------------
# TASK 3 — Shape discrimination + P1 halting hook
# ---------------------------------------------------------------------------
def _classify_edge(edge: EdgeProfile) -> Tuple[ValleyClassification, float]:
    """Returns (classification, geometric_confidence).

    Edge straightness above the linear threshold AND band width within roll
    tolerance → I&WS present. Gravity-following amorphous bleed → moisture.
    """
    linear_ok = edge.straightness_score >= LINEAR_EDGE_STRAIGHTNESS_MIN
    width_within_roll = (
        abs(edge.measured_band_width_in - VALLEY_MASK_TOTAL_WIDTH_IN)
        <= STANDARD_ROLL_WIDTH_TOLERANCE_IN
    )

    if linear_ok and width_within_roll and not edge.follows_gravity_channels:
        # Confidence rises with straightness and falls with width deviation.
        width_term = 1.0 - (
            abs(edge.measured_band_width_in - VALLEY_MASK_TOTAL_WIDTH_IN)
            / STANDARD_ROLL_WIDTH_TOLERANCE_IN
        )
        conf = max(0.0, min(1.0, 0.55 * edge.straightness_score + 0.45 * width_term))
        return ValleyClassification.ICE_WATER_SHIELD_PRESENT, conf

    if edge.follows_gravity_channels or edge.straightness_score < 0.55:
        # Strong moisture-anomaly signal: irregular bleed along rafter channels.
        conf = max(0.0, min(1.0, 0.5 + (1.0 - edge.straightness_score) * 0.5))
        return ValleyClassification.MOISTURE_ANOMALY, conf

    # Ambiguous middle band — geometric_confidence intentionally low to trigger halt.
    return ValleyClassification.MOISTURE_ANOMALY, 0.45


def build_halt_payload(frame: ValleyFrame, analysis_partial: dict) -> dict:
    """Construct the Overseer halt-queue payload (wire-compatible with /api/telemetry/halt)."""
    return {
        "contractor_id": frame.contractor_id,
        "job_id": frame.job_id,
        "source": "ice_shield_cv",
        "error_state": "CV_CONFIDENCE_BELOW_THRESHOLD",
        "frame_id": frame.frame_id,
        "valley_track_id": frame.valley_track_id,
        "captured_at_utc": frame.capture.captured_at_utc.isoformat(),
        "details": analysis_partial,
        "review_priority": "P1",
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def analyze_valley_frame(frame: ValleyFrame) -> IceShieldAnalysis:
    """Run the full validation pipeline on one parsed valley frame.

    Returns a strictly-typed IceShieldAnalysis. If overall confidence falls
    below `CONFIDENCE_HALT_THRESHOLD`, halts ingestion for the frame and emits
    a halt_payload suitable for POST to /api/telemetry/halt or direct insert
    into db.telemetry_halts.
    """
    preconditions: List[PreconditionResult] = [
        _check_emissivity(frame.capture),
        _check_delta_t_band(frame.delta_t_band_c),
        _check_capture_window(frame.capture),
        _check_valley_mask(frame.edge),
    ]
    precond_passed = all(p.passed for p in preconditions)

    geom_class, geom_conf = _classify_edge(frame.edge)
    # Composite confidence: base CV × geometric × precondition factor.
    precond_factor = 1.0 if precond_passed else 0.6
    confidence = round(frame.base_confidence * geom_conf * precond_factor, 4)

    if confidence < CONFIDENCE_HALT_THRESHOLD:
        partial = {
            "candidate_classification": geom_class.value,
            "base_confidence": frame.base_confidence,
            "geometric_confidence": geom_conf,
            "precondition_results": [p.model_dump() for p in preconditions],
            "composite_confidence": confidence,
        }
        return IceShieldAnalysis(
            frame_id=frame.frame_id,
            classification=ValleyClassification.UNVERIFIED_HALT,
            confidence=confidence,
            halted=True,
            preconditions=preconditions,
            has_ice_and_water_shield=False,
            code_compliant_underlayment=False,
            flag_for_estimation_pipeline=False,
            halt_payload=build_halt_payload(frame, partial),
            reasoning=(
                f"Composite confidence {confidence:.3f} < threshold "
                f"{CONFIDENCE_HALT_THRESHOLD}. Frame frozen and routed to Overseer queue."
            ),
        )

    # Above-threshold: commit a definitive classification.
    if geom_class is ValleyClassification.ICE_WATER_SHIELD_PRESENT:
        return IceShieldAnalysis(
            frame_id=frame.frame_id,
            classification=geom_class,
            confidence=confidence,
            halted=False,
            preconditions=preconditions,
            has_ice_and_water_shield=True,
            code_compliant_underlayment=True,
            flag_for_estimation_pipeline=False,
            halt_payload=None,
            reasoning=(
                "Linear edge boundary, 36\" ± tolerance band, no gravity-channel bleed → "
                "rubberized I&WS membrane confirmed."
            ),
        )

    # Confident MOISTURE_ANOMALY → flag to Section 3.2 Estimation Controller.
    return IceShieldAnalysis(
        frame_id=frame.frame_id,
        classification=geom_class,
        confidence=confidence,
        halted=False,
        preconditions=preconditions,
        has_ice_and_water_shield=False,
        code_compliant_underlayment=False,
        flag_for_estimation_pipeline=True,
        halt_payload=None,
        reasoning=(
            "Amorphous/irregular edge bleeding along rafter channels → latent moisture "
            "entrapment. Routed to Estimation Controller (Section 3.2)."
        ),
    )


__all__ = [
    "ASPHALT_SHINGLE_EMISSIVITY",
    "DELTA_T_LOWER_C",
    "DELTA_T_UPPER_C",
    "VALLEY_MASK_TOTAL_WIDTH_IN",
    "CONFIDENCE_HALT_THRESHOLD",
    "ValleyClassification",
    "EdgeProfile",
    "CaptureContext",
    "ValleyFrame",
    "PreconditionResult",
    "IceShieldAnalysis",
    "analyze_valley_frame",
    "build_halt_payload",
]
