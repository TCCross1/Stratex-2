"""Evidence-based recapture recommendations for PX-006B."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from .authority_guard import assert_recapture_not_mission_approval
from .constants import RECAPTURE_STATES


def build_recapture_recommendations(
    *,
    dataset_id: str,
    structure_id: str,
    failures: Sequence[Mapping[str, Any]],
    confidence: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    patterns = set()
    for failure in failures:
        pattern = failure.get("recapture_pattern")
        if pattern and pattern != "none":
            patterns.add(str(pattern))
    for hint in confidence.get("recommended_additional_capture") or []:
        patterns.add(str(hint))

    recommendations: List[Dict[str, Any]] = []
    for pattern in sorted(patterns):
        rec = {
            "dataset_id": dataset_id,
            "structure_id": structure_id,
            "recommendation_state": "PROPOSED_CAPTURE_ADJUSTMENT",
            "pattern": pattern,
            "evidence_basis": {
                "failure_classes": [f.get("failure_class") for f in failures],
                "confidence_state": confidence.get("confidence_state"),
            },
            "mission_approved": False,
            "atc_authority_note": "ATC retains mission orchestration authority; this is not mission approval.",
            "authoritative": False,
            "physical_validation": "NOT_PERFORMED",
        }
        assert_recapture_not_mission_approval(rec)
        if rec["recommendation_state"] not in RECAPTURE_STATES:
            raise ValueError("invalid recapture state")
        recommendations.append(rec)
    return recommendations
