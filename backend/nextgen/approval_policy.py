"""Unified approval policy for Findings and Property Intelligence (C-P-002).

Both approval doors must use this service. Separation of duties is uniform:
author may not approve their own record; admin / ceo / superadmin status
alone must not silently bypass SoD. No emergency override in this phase.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .taxonomy import allowed_reviewer_roles_for_tier

# Findings keep their Phase-3 reviewer set; Intelligence uses risk-tier roles.
FINDINGS_APPROVER_ROLES: Set[str] = frozenset({"ceo", "admin", "gm"})


@dataclass
class ApprovalDecision:
    allowed: bool
    reason: str
    code: str
    details: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "code": self.code,
            "details": self.details,
        }


def _norm_role(role: Optional[str]) -> str:
    return (role or "").strip().lower()


def _author_ids(source: Dict[str, Any]) -> Set[str]:
    """Collect tracked authorship identities for SoD."""
    ids: Set[str] = set()
    for key in (
        "author_id",
        "created_by",
        "inspector_user_id",
        "last_editor_id",
        "processed_by",
        "materially_revised_by",
    ):
        val = source.get(key)
        if val:
            ids.add(str(val))
    # Material revisions recorded in review_history count as authorship.
    for entry in source.get("review_history") or []:
        action = (entry.get("action") or "").lower()
        if action in {
            "create_draft", "edit_draft", "create_supersede_draft",
            "material_revise", "process",
        }:
            by = entry.get("by")
            if by:
                ids.add(str(by))
    return ids


def evaluate_approval_policy(
    *,
    source_kind: str,  # "finding" | "intelligence"
    source: Dict[str, Any],
    actor_id: str,
    actor_role: str,
    tenant_id: str,
    property_id: str,
    require_evidence: bool = False,
    expected_revision: Optional[int] = None,
    expected_head_hash: Optional[str] = None,
    require_expected_state: bool = True,
    actor_attributes: Optional[Dict[str, Any]] = None,
) -> ApprovalDecision:
    """Single policy evaluation used by Findings and Intelligence."""
    role = _norm_role(actor_role)
    attrs = actor_attributes or {}

    if source.get("tenant_id") != tenant_id:
        return ApprovalDecision(
            False, "Tenant mismatch", "TENANT_MISMATCH",
            {"source_tenant": source.get("tenant_id"), "actor_tenant": tenant_id},
        )

    src_property = source.get("property_id")
    if src_property and src_property != property_id:
        return ApprovalDecision(
            False, "Property mismatch", "PROPERTY_MISMATCH",
            {"source_property": src_property, "requested_property": property_id},
        )

    # Uniform separation of duties — evaluated before role privilege so that
    # admin / ceo / superadmin status alone cannot silently bypass SoD.
    authors = _author_ids(source)
    if str(actor_id) in authors:
        return ApprovalDecision(
            False,
            "Separation of duties: author may not approve their own record. "
            "Administrator, CEO, or superadmin status alone does not bypass SoD.",
            "SEPARATION_OF_DUTIES",
            {
                "actor_id": actor_id,
                "actor_role": role,
                "author_ids": sorted(authors),
                "bypass_attempted": role in {"admin", "ceo", "superadmin", "gm"},
            },
        )

    # Source state gates
    if source_kind == "finding":
        if source.get("status") != "PENDING_REVIEW":
            return ApprovalDecision(
                False,
                f"Finding status {source.get('status')!r} is not approvable",
                "SOURCE_STATE_INVALID",
                {"status": source.get("status")},
            )
        if role not in FINDINGS_APPROVER_ROLES:
            return ApprovalDecision(
                False,
                f"Role {role!r} may not approve findings",
                "ROLE_INELIGIBLE",
                {"allowed_roles": sorted(FINDINGS_APPROVER_ROLES)},
            )
    elif source_kind == "intelligence":
        if source.get("state") in {"passport_committed", "rejected"}:
            return ApprovalDecision(
                False,
                f"Intelligence state {source.get('state')!r} is not approvable",
                "SOURCE_STATE_INVALID",
                {"state": source.get("state")},
            )
        tier = source.get("risk_tier") or "tier_2_contractor_review"
        allowed = {_norm_role(r) for r in allowed_reviewer_roles_for_tier(tier)}
        if role not in allowed:
            return ApprovalDecision(
                False,
                f"Role {role!r} may not review tier {tier}",
                "ROLE_INELIGIBLE",
                {"allowed_roles": sorted(allowed), "tier": tier},
            )
        if tier == "tier_4_engineering_controlled":
            if not attrs.get("engineer_license_active"):
                return ApprovalDecision(
                    False,
                    "Tier 4 review requires an engineer license",
                    "LICENSE_REQUIRED",
                    {"tier": tier},
                )
        evidence_ids = source.get("evidence_ids") or []
        if require_evidence and not evidence_ids:
            return ApprovalDecision(
                False,
                "Required evidence is missing",
                "EVIDENCE_REQUIRED",
                {},
            )
    else:
        return ApprovalDecision(
            False, f"Unknown source_kind {source_kind!r}", "UNKNOWN_SOURCE_KIND", {},
        )

    if require_expected_state:
        if expected_revision is None and not expected_head_hash:
            return ApprovalDecision(
                False,
                "Governed approval requires expected_revision or expected_head_hash",
                "MISSING_EXPECTED_STATE",
                {},
            )

    return ApprovalDecision(
        True,
        "Approval permitted under unified policy",
        "APPROVED_POLICY",
        {
            "actor_id": actor_id,
            "actor_role": role,
            "source_kind": source_kind,
            "expected_revision": expected_revision,
            "expected_head_hash": expected_head_hash,
        },
    )


def policy_identity() -> str:
    """Stable identity so tests can prove both doors use the same policy."""
    return "nextgen.approval_policy.evaluate_approval_policy"
