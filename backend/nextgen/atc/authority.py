"""ATC authority guards — no Passport writer / publisher / approval.

Law: PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY.
"""
from __future__ import annotations


class AuthorityViolation(RuntimeError):
    """Raised when ATC attempts Passport write, publish, or approved emission."""


def refuse_passport_write(action: str = "passport write") -> None:
    raise AuthorityViolation(
        f"ATC-001B refuses {action}: Passport writer/publisher authority "
        "remains LANE_1 only (append_entry / governed_publish)."
    )


def refuse_approved_emission(contract_name: str) -> None:
    raise AuthorityViolation(
        f"ATC-001B refuses to emit {contract_name}: candidates only. "
        "ApprovedGeometry / ApprovedFinding require Atlas / LANE_1 authority."
    )
