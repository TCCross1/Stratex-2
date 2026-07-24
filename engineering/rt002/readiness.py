"""RT-002 readiness model — component and overall states.

Permitted overall states:
  NOT_INITIALIZED | INITIALIZING | READY | FAILED | UNAVAILABLE

Overall READY only when every required live check passes.
Never exposes credentials or password-bearing connection strings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class OverallState(str, Enum):
    NOT_INITIALIZED = "NOT_INITIALIZED"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


REQUIRED_COMPONENTS = (
    "mongo_reachable",
    "replica_set_initialized",
    "writable_primary",
    "transaction_proof",
    "critical_passport_indexes",
    "object_storage_reachable",
    "bucket_operation",
    "checksum_proof",
)


@dataclass
class ComponentStatus:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class ReadinessReport:
    components: Dict[str, ComponentStatus] = field(default_factory=dict)
    overall: OverallState = OverallState.NOT_INITIALIZED
    marker_notes: List[str] = field(default_factory=list)

    def set(self, name: str, ok: bool, detail: str = "") -> None:
        self.components[name] = ComponentStatus(name=name, ok=ok, detail=detail)

    def compute_overall(self, *, initializing: bool = False) -> OverallState:
        if initializing and not self.components:
            self.overall = OverallState.INITIALIZING
            return self.overall
        if not self.components:
            self.overall = OverallState.NOT_INITIALIZED
            return self.overall
        # Any explicit unavailable detail wins over READY.
        vals = list(self.components.values())
        if any(not c.ok and "UNAVAILABLE" in (c.detail or "") for c in vals):
            self.overall = OverallState.UNAVAILABLE
            return self.overall
        if any(not c.ok for c in vals):
            self.overall = OverallState.FAILED
            return self.overall
        missing = [n for n in REQUIRED_COMPONENTS if n not in self.components]
        if missing:
            self.overall = OverallState.FAILED
            self.marker_notes.append(f"missing_components={missing}")
            return self.overall
        self.overall = OverallState.READY
        return self.overall

    def as_public_dict(self) -> dict:
        """Safe public view — never include secrets."""
        return {
            "overall": self.overall.value,
            "production_readiness": "NOT_READY",
            "components": {
                k: {"ok": v.ok, "detail": v.detail}
                for k, v in self.components.items()
            },
            "notes": list(self.marker_notes),
        }


def redact_url(url: Optional[str]) -> str:
    if not url:
        return ""
    # Strip credentials if present: scheme://user:pass@host
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        host = rest.split("@", 1)[-1]
        return f"{scheme}://***@{host}"
    return url
