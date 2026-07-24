"""Waste / overage policy registry — versioned, deterministic."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

from .errors import UnknownInputError
from .units import require_known


@dataclass(frozen=True)
class WastePolicy:
    """Named waste/overage policy.

    `multiplier` is applied as net * multiplier (e.g. 1.10 = +10%).
    Alternatively `percent` may be supplied; registry stores both forms.
    """

    policy_id: str
    version: str
    trade: str
    description: str
    multiplier: Decimal
    percent: Decimal

    def apply(self, net: Decimal) -> Decimal:
        return net * self.multiplier

    def as_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "trade": self.trade,
            "description": self.description,
            "multiplier": str(self.multiplier),
            "percent": str(self.percent),
        }


def _policy(
    policy_id: str,
    version: str,
    trade: str,
    description: str,
    percent: str,
) -> WastePolicy:
    pct = Decimal(percent)
    mult = Decimal("1") + (pct / Decimal("100"))
    return WastePolicy(
        policy_id=policy_id,
        version=version,
        trade=trade,
        description=description,
        multiplier=mult,
        percent=pct,
    )


class WasteRegistry:
    """Immutable-by-convention registry of waste/overage policies."""

    def __init__(self, policies: Dict[str, WastePolicy]) -> None:
        self._policies = dict(policies)

    def get(self, policy_id: Optional[str]) -> WastePolicy:
        if policy_id is None:
            raise UnknownInputError("waste_policy_id", "waste policy id is required")
        if policy_id not in self._policies:
            raise UnknownInputError(
                "waste_policy_id",
                f"unknown waste policy {policy_id!r}",
            )
        return self._policies[policy_id]

    def apply(self, policy_id: str, net_quantity: Decimal) -> Decimal:
        net = require_known(net_quantity, name="net_quantity")
        return self.get(policy_id).apply(net)

    def list_ids(self) -> list[str]:
        return sorted(self._policies.keys())

    def as_dict(self) -> dict:
        return {k: v.as_dict() for k, v in sorted(self._policies.items())}


# Locked E-001 starter policies — change requires formula/version bump + tests.
WASTE_REGISTRY = WasteRegistry(
    {
        "roofing.shingles.v1": _policy(
            "roofing.shingles.v1",
            "1.0.0",
            "roofing",
            "Standard asphalt shingle waste (10%)",
            "10",
        ),
        "roofing.felt.v1": _policy(
            "roofing.felt.v1",
            "1.0.0",
            "roofing",
            "Underlayment / felt waste (5%)",
            "5",
        ),
        "siding.composite.v1": _policy(
            "siding.composite.v1",
            "1.0.0",
            "siding",
            "Composite / fiber-cement board waste (7%)",
            "7",
        ),
        "siding.wood.v1": _policy(
            "siding.wood.v1",
            "1.0.0",
            "siding",
            "Wood plank waste (10%)",
            "10",
        ),
        "framing.lumber.v1": _policy(
            "framing.lumber.v1",
            "1.0.0",
            "framing",
            "Dimensional lumber waste (10%)",
            "10",
        ),
        "concrete.slab.v1": _policy(
            "concrete.slab.v1",
            "1.0.0",
            "concrete",
            "Slab / flatwork overage (8%)",
            "8",
        ),
        "gutters.sections.v1": _policy(
            "gutters.sections.v1",
            "1.0.0",
            "gutters",
            "Gutter section waste (5%)",
            "5",
        ),
        "general.none.v1": _policy(
            "general.none.v1",
            "1.0.0",
            "general",
            "No waste applied (identity multiplier)",
            "0",
        ),
    }
)
