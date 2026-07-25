"""Authority and emission guards for PX-006B benchmark outputs."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping

PROHIBITED_EMISSIONS = frozenset(
    {
        "ApprovedGeometry",
        "ApprovedFinding",
        "ApprovedSide",
        "passport_append",
        "governed_final_publish",
        "habitat_canonical_write",
        "purchase_price",
        "contractor_grade_accuracy",
        "insurance_grade_accuracy",
        "homeowner_truth",
        "canonical_property_truth",
    }
)


class AuthorityViolation(RuntimeError):
    pass


def assert_benchmark_object(obj: Mapping[str, Any]) -> None:
    if obj.get("authoritative") is not False:
        raise AuthorityViolation("benchmark object must set authoritative=false")
    if obj.get("physical_validation") != "NOT_PERFORMED":
        raise AuthorityViolation("benchmark object must set physical_validation=NOT_PERFORMED")
    truth = str(obj.get("truth_classification", ""))
    if truth == "CANONICAL_PROPERTY_TRUTH":
        raise AuthorityViolation("canonical property truth is prohibited")
    if truth and truth.startswith("APPROVED_"):
        raise AuthorityViolation("approved truth classifications are prohibited")


def reject_prohibited_emission(name: str) -> None:
    if name in PROHIBITED_EMISSIONS:
        raise AuthorityViolation(f"prohibited emission attempted: {name}")


def assert_no_pricing(payload: Mapping[str, Any]) -> None:
    forbidden_keys = {"price", "unit_price", "purchase_price", "contract_value"}
    for key in payload.keys():
        if key in forbidden_keys:
            raise AuthorityViolation(f"pricing field prohibited: {key}")


def assert_recapture_not_mission_approval(rec: Mapping[str, Any]) -> None:
    if rec.get("recommendation_state") != "PROPOSED_CAPTURE_ADJUSTMENT":
        raise AuthorityViolation("recapture must remain PROPOSED_CAPTURE_ADJUSTMENT")
    if rec.get("mission_approved") is True:
        raise AuthorityViolation("recapture recommendations must not approve missions")


def scan_objects(objects: Iterable[Mapping[str, Any]]) -> None:
    for obj in objects:
        assert_benchmark_object(obj)
        assert_no_pricing(obj)
