"""EstimateCalculationLedger — PROPOSED executable schema (not FROZEN).

Contract status: PROPOSED under E-001.
Atlas remains sole freeze / ACCEPTED authority.
No Passport writes. No publication authority.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from .provenance import QuantityResult

LEDGER_SCHEMA_VERSION = "0.1.0"
LEDGER_CONTRACT_STATUS: Literal["PROPOSED"] = "PROPOSED"


class LedgerProvenance(BaseModel):
    """Ledger-level provenance (calculator + input package identity)."""

    calculator_version: str
    formula_registry_version: str
    input_package_hash: str
    source_type: str = "deterministic_engine"
    notes: Optional[str] = None


class LedgerEntry(BaseModel):
    """One append-oriented calculation step."""

    entry_id: str
    sequence: int
    formula_id: str
    formula_version: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    output_value: str
    output_unit: str
    output_dimension: str
    waste_policy_id: Optional[str] = None
    confidence: str = "deterministic"
    unknown_state: Optional[str] = None
    engine_version: str
    notes: Optional[str] = None


class EstimateCalculationLedger(BaseModel):
    """PROPOSED EstimateCalculationLedger executable schema.

    Status is intentionally PROPOSED — never claim FROZEN/ACCEPTED here.
    """

    schema_name: Literal["EstimateCalculationLedger"] = "EstimateCalculationLedger"
    schema_version: str = LEDGER_SCHEMA_VERSION
    contract_status: Literal["PROPOSED"] = LEDGER_CONTRACT_STATUS
    ledger_id: str
    created_at: str
    provenance: LedgerProvenance
    confidence: str = "deterministic"
    unknown_state: Optional[str] = None
    entries: List[LedgerEntry] = Field(default_factory=list)
    compatibility: str = "0.x additive only until ACCEPTED"
    breaking_change: str = "requires ATLAS_ARCHITECTURE_APPROVAL"

    def append_entry(self, entry: LedgerEntry) -> "EstimateCalculationLedger":
        """Return a new ledger with entry appended (immutable append pattern)."""
        data = self.model_dump()
        data["entries"] = list(data["entries"]) + [entry.model_dump()]
        # Propagate unknown_state if any entry is unknown.
        if entry.unknown_state and not data.get("unknown_state"):
            data["unknown_state"] = entry.unknown_state
        return EstimateCalculationLedger.model_validate(data)


def hash_input_package(payload: Any) -> str:
    """Stable SHA-256 of a JSON-serializable input package."""
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def entry_from_quantity_result(
    result: QuantityResult,
    *,
    entry_id: str,
    sequence: int,
) -> LedgerEntry:
    return LedgerEntry(
        entry_id=entry_id,
        sequence=sequence,
        formula_id=result.provenance.formula_id,
        formula_version=result.provenance.formula_version,
        inputs=dict(result.provenance.input_refs),
        output_value=str(result.value),
        output_unit=result.unit,
        output_dimension=result.dimension.value,
        waste_policy_id=result.provenance.waste_policy_id,
        confidence=result.confidence,
        unknown_state=result.unknown_state,
        engine_version=result.provenance.engine_version,
        notes=result.provenance.notes,
    )


def build_ledger(
    *,
    ledger_id: str,
    calculator_version: str,
    formula_registry_version: str,
    input_package: Any,
    results: Sequence[QuantityResult],
    confidence: str = "deterministic",
    unknown_state: Optional[str] = None,
    notes: Optional[str] = None,
) -> EstimateCalculationLedger:
    """Build a PROPOSED ledger from deterministic QuantityResult steps."""
    if results is None:
        from .errors import UnknownInputError

        raise UnknownInputError("results", "results sequence is required")

    pkg_hash = hash_input_package(input_package)
    entries: List[LedgerEntry] = []
    unresolved: List[str] = []
    for i, result in enumerate(results):
        entry = entry_from_quantity_result(
            result,
            entry_id=f"{ledger_id}:{i + 1:04d}",
            sequence=i + 1,
        )
        entries.append(entry)
        if result.unknown_state:
            unresolved.append(result.unknown_state)

    ledger_unknown = unknown_state
    if unresolved and not ledger_unknown:
        ledger_unknown = ";".join(unresolved)

    return EstimateCalculationLedger(
        ledger_id=ledger_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        provenance=LedgerProvenance(
            calculator_version=calculator_version,
            formula_registry_version=formula_registry_version,
            input_package_hash=pkg_hash,
            notes=notes,
        ),
        confidence=confidence,
        unknown_state=ledger_unknown,
        entries=entries,
    )
