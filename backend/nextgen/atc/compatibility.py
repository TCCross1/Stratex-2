"""Executable compatibility validation for ATC evidence contracts.

Checks versions, unknown fields, provenance presence, and doctrine
separations (thermal ≠ dimensions; geometry ≠ thermal diagnosis).

Does not freeze contracts. Does not approve geometry/findings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set


SUPPORTED_CONTRACT_VERSIONS: Mapping[str, Set[str]] = {
    "EvidenceManifest": {"0.0.0"},
    "GeometryCandidate": {"0.0.0"},
    "ApprovedGeometryCandidate": {"0.0.0"},
    "AWEEvidenceCandidate": {"0.0.0"},
    "AweEvidenceCandidate": {"0.0.0"},
    "ApprovedGeometry": {"0.0.0"},
    "ApprovedFinding": {"0.0.0"},
    "MissionTypeContract": {"0.0.0"},
    "CapturePackageManifest": {"0.0.0"},
    "PreflightResult": {"0.0.0"},
}

# Known fields per contract family (compatibility surface; additive 0.x).
_GEOMETRY_FIELDS = {
    "meta",
    "candidate_id",
    "mission_id",
    "aircraft_profile_id",
    "source_evidence_manifest_id",
    "approval_status",
    "approved_because_from_4e",
    "is_production_approved",
    "rtk_accuracy_claimed",
    "extents",
    "control_points_unknown",
    "provenance",
    "confidence",
    "unknown_state",
}
_AWE_FIELDS = {
    "meta",
    "candidate_id",
    "mission_id",
    "aircraft_profile_id",
    "source_evidence_manifest_id",
    "approval_status",
    "is_dimensional_authority",
    "thermal_changes_dimensions",
    "automated_thermal_diagnosis",
    "is_production_approved",
    "observations",
    "provenance",
    "confidence",
    "unknown_state",
}
KNOWN_FIELDS: Mapping[str, Set[str]] = {
    "EvidenceManifest": {
        "meta",
        "mission_id",
        "mission_type",
        "aircraft_profile_id",
        "package_hash",
        "artifacts",
        "completeness_ok",
        "atc_validation_status",
        "passport_accepted",
        "provenance",
        "confidence",
        "unknown_state",
    },
    "GeometryCandidate": _GEOMETRY_FIELDS,
    "ApprovedGeometryCandidate": _GEOMETRY_FIELDS,
    "AWEEvidenceCandidate": _AWE_FIELDS,
    "AweEvidenceCandidate": _AWE_FIELDS,
}

MAPPING_PROFILES = frozenset({"M4E_MAPPING", "M400_P1_MAPPING"})
AWE_PROFILES = frozenset({"M4T_AWE", "M400_H30T_AWE"})


@dataclass
class CompatibilityIssue:
    code: str
    severity: str  # error | warn
    message: str
    field: Optional[str] = None


@dataclass
class CompatibilityResult:
    ok: bool
    contract_name: str
    contract_version: str
    unknown_fields: List[str] = field(default_factory=list)
    issues: List[CompatibilityIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[CompatibilityIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[CompatibilityIssue]:
        return [i for i in self.issues if i.severity == "warn"]


def _meta_dict(payload: Mapping[str, Any]) -> Dict[str, Any]:
    meta = payload.get("meta") or {}
    if hasattr(meta, "model_dump"):
        return meta.model_dump()
    return dict(meta) if isinstance(meta, Mapping) else {}


def _as_mapping(payload: Any) -> Dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if isinstance(payload, Mapping):
        return dict(payload)
    raise TypeError("payload must be a mapping or pydantic model")


def validate_compatibility(
    payload: Any,
    *,
    expected_contract: Optional[str] = None,
    allow_unknown_fields: bool = True,
) -> CompatibilityResult:
    """Validate contract compatibility for an evidence payload.

    - Versions must be in the supported 0.0.0 set for the contract family.
    - Unknown fields are recorded; severity depends on ``allow_unknown_fields``.
    - Provenance must be present with source_type / source_id.
    - Doctrine: thermal ≠ dimensions; geometry ≠ thermal diagnosis.
    """
    data = _as_mapping(payload)
    meta = _meta_dict(data)
    contract_name = expected_contract or meta.get("contract_name") or "Unknown"
    # Normalize alias names for field tables
    field_key = contract_name
    if contract_name == "ApprovedGeometryCandidate":
        field_key = "GeometryCandidate"
    elif contract_name == "AweEvidenceCandidate":
        field_key = "AWEEvidenceCandidate"

    version = str(meta.get("contract_version") or "0.0.0")
    issues: List[CompatibilityIssue] = []

    supported = SUPPORTED_CONTRACT_VERSIONS.get(contract_name)
    if supported is None:
        issues.append(
            CompatibilityIssue(
                code="UNKNOWN_CONTRACT",
                severity="error",
                message=f"Unsupported contract name for ATC-001B: {contract_name}",
            )
        )
    elif version not in supported:
        issues.append(
            CompatibilityIssue(
                code="UNSUPPORTED_VERSION",
                severity="error",
                message=f"Version {version} not supported for {contract_name}; "
                f"supported={sorted(supported)}",
                field="meta.contract_version",
            )
        )

    known = KNOWN_FIELDS.get(field_key, set())
    unknown = sorted(k for k in data.keys() if k not in known) if known else []
    if unknown:
        severity = "warn" if allow_unknown_fields else "error"
        issues.append(
            CompatibilityIssue(
                code="UNKNOWN_FIELDS",
                severity=severity,
                message=f"Unknown fields present: {unknown}",
            )
        )

    provenance = data.get("provenance")
    if provenance is None:
        issues.append(
            CompatibilityIssue(
                code="MISSING_PROVENANCE",
                severity="error",
                message="provenance is required",
                field="provenance",
            )
        )
    else:
        prov = provenance.model_dump() if hasattr(provenance, "model_dump") else dict(provenance)
        for req in ("source_type", "source_id"):
            if not prov.get(req):
                issues.append(
                    CompatibilityIssue(
                        code="PROVENANCE_INCOMPLETE",
                        severity="error",
                        message=f"provenance.{req} is required",
                        field=f"provenance.{req}",
                    )
                )

    profile = data.get("aircraft_profile_id")
    _check_doctrine(data, contract_name=field_key, profile=profile, issues=issues)

    ok = not any(i.severity == "error" for i in issues)
    return CompatibilityResult(
        ok=ok,
        contract_name=contract_name,
        contract_version=version,
        unknown_fields=unknown,
        issues=issues,
    )


def _check_doctrine(
    data: Mapping[str, Any],
    *,
    contract_name: str,
    profile: Any,
    issues: List[CompatibilityIssue],
) -> None:
    """Encode thermal≠dimensions and geometry≠thermal diagnosis separations."""
    if contract_name in {"AWEEvidenceCandidate", "AweEvidenceCandidate"} or profile in AWE_PROFILES:
        if data.get("is_dimensional_authority") is True:
            issues.append(
                CompatibilityIssue(
                    code="THERMAL_DIMENSION_VIOLATION",
                    severity="error",
                    message="thermal/AWE path must not claim dimensional authority",
                    field="is_dimensional_authority",
                )
            )
        if data.get("thermal_changes_dimensions") is True:
            issues.append(
                CompatibilityIssue(
                    code="THERMAL_DIMENSION_VIOLATION",
                    severity="error",
                    message="thermal does not change dimensions",
                    field="thermal_changes_dimensions",
                )
            )
        if data.get("automated_thermal_diagnosis") is True:
            issues.append(
                CompatibilityIssue(
                    code="THERMAL_DIAGNOSIS_VIOLATION",
                    severity="error",
                    message="automated thermal diagnosis is forbidden in ATC-001B",
                    field="automated_thermal_diagnosis",
                )
            )
        # Geometry-like keys must not appear on thermal candidates
        for geom_key in ("extents", "rtk_accuracy_claimed", "approved_because_from_4e"):
            if geom_key in data and data.get(geom_key) not in (None, False):
                issues.append(
                    CompatibilityIssue(
                        code="GEOMETRY_ON_THERMAL",
                        severity="error",
                        message=f"thermal/AWE candidate must not carry geometry claim field {geom_key}",
                        field=geom_key,
                    )
                )

    if contract_name in {"GeometryCandidate", "ApprovedGeometryCandidate"} or profile in MAPPING_PROFILES:
        if data.get("automated_thermal_diagnosis") is True:
            issues.append(
                CompatibilityIssue(
                    code="THERMAL_ON_GEOMETRY",
                    severity="error",
                    message="geometry candidate must not claim thermal diagnosis",
                    field="automated_thermal_diagnosis",
                )
            )
        if data.get("observations"):
            # observations are AWE-only
            issues.append(
                CompatibilityIssue(
                    code="THERMAL_ON_GEOMETRY",
                    severity="error",
                    message="geometry candidate must not include thermal observations",
                    field="observations",
                )
            )
        if data.get("is_production_approved") is True:
            issues.append(
                CompatibilityIssue(
                    code="PREMATURE_APPROVAL",
                    severity="error",
                    message="geometry candidate must not be production-approved by ATC",
                    field="is_production_approved",
                )
            )
        if data.get("approved_because_from_4e") is True:
            issues.append(
                CompatibilityIssue(
                    code="PREMATURE_APPROVAL",
                    severity="error",
                    message="geometry is not approved merely because from 4E",
                    field="approved_because_from_4e",
                )
            )
