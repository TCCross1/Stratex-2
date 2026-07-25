"""Reality-model reference states for Habitat read models (HABITAT-P-002).

Lifecycle (reference states): ``no_scan`` → … → ``superseded``.

Layer kinds remain separated — existing condition, proposed work, and
completed-as-built must never be collapsed into a single ambiguous plane.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..schemas.habitat.common import (
    ConfidenceDisplay,
    ProvenanceDisplay,
    UnknownStateDisplay,
)

RealityReferenceState = Literal[
    "no_scan",
    "scan_recorded",
    "existing",
    "proposed",
    "completed_as_built",
    "superseded",
]

RealityLayerKind = Literal["existing", "proposed", "completed_as_built"]

# Ordered lifecycle — consumers may advance, never invent skip-ahead certainty.
REALITY_STATE_ORDER: tuple[RealityReferenceState, ...] = (
    "no_scan",
    "scan_recorded",
    "existing",
    "proposed",
    "completed_as_built",
    "superseded",
)


class RealityModelLayer(BaseModel):
    """One reality plane (existing / proposed / completed-as-built)."""

    model_config = ConfigDict(extra="forbid")

    kind: RealityLayerKind
    reference_state: RealityReferenceState
    label: str = Field(min_length=1)
    source_ids: List[str] = Field(default_factory=list)
    unknown_state: UnknownStateDisplay
    confidence: ConfidenceDisplay
    # Honesty: a layer may be present as a slot even when empty / no_scan.
    is_authoritative: bool = False

    @model_validator(mode="after")
    def _layer_honesty(self) -> "RealityModelLayer":
        if self.reference_state == "no_scan":
            if self.unknown_state.state == "known":
                raise ValueError("no_scan layer must not claim unknown_state=known")
            if self.is_authoritative:
                raise ValueError("no_scan layer cannot be authoritative")
        if self.reference_state == "superseded":
            if self.is_authoritative:
                raise ValueError("superseded layer cannot be authoritative")
        # Kind / state alignment: proposed kind may not claim completed_as_built.
        if self.kind == "existing" and self.reference_state in {
            "proposed",
            "completed_as_built",
        }:
            raise ValueError(
                "existing layer cannot use proposed/completed_as_built reference_state"
            )
        if self.kind == "proposed" and self.reference_state in {
            "existing",
            "completed_as_built",
        }:
            raise ValueError(
                "proposed layer cannot use existing/completed_as_built reference_state"
            )
        if self.kind == "completed_as_built" and self.reference_state in {
            "existing",
            "proposed",
        }:
            raise ValueError(
                "completed_as_built layer cannot use existing/proposed reference_state"
            )
        return self


class RealityModelBundle(BaseModel):
    """Separated reality planes for a property read model."""

    model_config = ConfigDict(extra="forbid")

    property_id: str = Field(min_length=1)
    overall_reference_state: RealityReferenceState
    existing: RealityModelLayer
    proposed: RealityModelLayer
    completed_as_built: RealityModelLayer
    provenance: ProvenanceDisplay

    @model_validator(mode="after")
    def _require_separated_layers(self) -> "RealityModelBundle":
        if self.existing.kind != "existing":
            raise ValueError("existing slot must have kind=existing")
        if self.proposed.kind != "proposed":
            raise ValueError("proposed slot must have kind=proposed")
        if self.completed_as_built.kind != "completed_as_built":
            raise ValueError(
                "completed_as_built slot must have kind=completed_as_built"
            )
        return self


def _confidence(band: str, label: str, *, reduced: bool = True) -> ConfidenceDisplay:
    return ConfidenceDisplay(
        band=band,  # type: ignore[arg-type]
        inherited_from_source=True,
        display_label=label,
        reduced_for_audience=reduced,
    )


def _layer(
    kind: RealityLayerKind,
    state: RealityReferenceState,
    *,
    label: str,
    source_ids: Optional[Sequence[str]] = None,
    unknown: Optional[UnknownStateDisplay] = None,
    authoritative: bool = False,
    confidence: Optional[ConfidenceDisplay] = None,
) -> RealityModelLayer:
    if unknown is None:
        if state in {"no_scan", "scan_recorded"}:
            unknown = UnknownStateDisplay.unavailable(
                f"{kind} reality plane has no authoritative scan"
            )
        elif state == "superseded":
            unknown = UnknownStateDisplay.unavailable(
                f"{kind} reality plane superseded"
            )
        else:
            unknown = UnknownStateDisplay.known()
    if confidence is None:
        if state in {"no_scan", "scan_recorded", "superseded"}:
            confidence = _confidence("unknown", f"{kind}: {state}")
        else:
            confidence = _confidence("medium", f"{kind}: {state}")
    return RealityModelLayer(
        kind=kind,
        reference_state=state,
        label=label,
        source_ids=list(source_ids or []),
        unknown_state=unknown,
        confidence=confidence,
        is_authoritative=authoritative,
    )


def derive_overall_reference_state(
    *,
    has_scan: bool,
    existing_present: bool,
    proposed_present: bool,
    completed_present: bool,
    superseded: bool,
) -> RealityReferenceState:
    """Derive overall state without inventing completed/proposed from silence."""
    if superseded:
        return "superseded"
    if completed_present:
        return "completed_as_built"
    if proposed_present:
        return "proposed"
    if existing_present:
        return "existing"
    if has_scan:
        return "scan_recorded"
    return "no_scan"


def build_reality_model(
    *,
    property_id: str,
    has_scan: bool = False,
    existing_source_ids: Optional[Sequence[str]] = None,
    proposed_source_ids: Optional[Sequence[str]] = None,
    completed_as_built_source_ids: Optional[Sequence[str]] = None,
    superseded: bool = False,
    superseded_reason: Optional[str] = None,
    projected_at: str,
    passport_revision: Optional[int] = None,
) -> RealityModelBundle:
    """Build separated reality layers from source presence flags / ids.

    Absence is ``no_scan`` / unavailable — never fabricated as zeroed existing.
    """
    existing_ids = list(existing_source_ids or [])
    proposed_ids = list(proposed_source_ids or [])
    completed_ids = list(completed_as_built_source_ids or [])

    if superseded:
        existing = _layer(
            "existing",
            "superseded",
            label="Existing condition (superseded)",
            source_ids=existing_ids,
            unknown=UnknownStateDisplay.unavailable(
                superseded_reason or "Reality model superseded"
            ),
            authoritative=False,
        )
        proposed = _layer(
            "proposed",
            "superseded",
            label="Proposed work (superseded)",
            source_ids=proposed_ids,
            unknown=UnknownStateDisplay.unavailable(
                superseded_reason or "Reality model superseded"
            ),
            authoritative=False,
        )
        completed = _layer(
            "completed_as_built",
            "superseded",
            label="Completed as-built (superseded)",
            source_ids=completed_ids,
            unknown=UnknownStateDisplay.unavailable(
                superseded_reason or "Reality model superseded"
            ),
            authoritative=False,
        )
    else:
        if existing_ids:
            existing = _layer(
                "existing",
                "existing",
                label="Existing condition",
                source_ids=existing_ids,
                authoritative=True,
            )
        elif has_scan:
            existing = _layer(
                "existing",
                "scan_recorded",
                label="Scan recorded — existing condition pending",
                source_ids=[],
                unknown=UnknownStateDisplay.awaiting_review(
                    "Scan recorded; existing condition not yet approved"
                ),
                authoritative=False,
            )
        else:
            existing = _layer(
                "existing",
                "no_scan",
                label="No scan — existing condition unavailable",
                source_ids=[],
                authoritative=False,
            )

        if proposed_ids:
            proposed = _layer(
                "proposed",
                "proposed",
                label="Proposed work",
                source_ids=proposed_ids,
                authoritative=True,
            )
        else:
            proposed = _layer(
                "proposed",
                "no_scan" if not has_scan else "scan_recorded",
                label="Proposed work not available",
                source_ids=[],
                unknown=UnknownStateDisplay.unavailable(
                    "No proposed reality plane published"
                ),
                authoritative=False,
            )

        if completed_ids:
            completed = _layer(
                "completed_as_built",
                "completed_as_built",
                label="Completed as-built",
                source_ids=completed_ids,
                authoritative=True,
            )
        else:
            completed = _layer(
                "completed_as_built",
                "no_scan" if not has_scan else "scan_recorded",
                label="Completed as-built not available",
                source_ids=[],
                unknown=UnknownStateDisplay.unavailable(
                    "No completed-as-built reality plane published"
                ),
                authoritative=False,
            )

    overall = derive_overall_reference_state(
        has_scan=has_scan,
        existing_present=bool(existing_ids) and not superseded,
        proposed_present=bool(proposed_ids) and not superseded,
        completed_present=bool(completed_ids) and not superseded,
        superseded=superseded,
    )

    return RealityModelBundle(
        property_id=property_id,
        overall_reference_state=overall,
        existing=existing,
        proposed=proposed,
        completed_as_built=completed,
        provenance=ProvenanceDisplay(
            source_type="habitat_projection",
            source_id=property_id,
            publication_context="habitat.reality_model",
            passport_revision=passport_revision,
            projected_at=projected_at,
            projector="habitat.read_model",
        ),
    )


def reality_model_as_dict(bundle: RealityModelBundle) -> Dict[str, Any]:
    return bundle.model_dump()
