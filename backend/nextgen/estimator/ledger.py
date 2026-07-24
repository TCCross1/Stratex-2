"""EstimateCalculationLedger — PROPOSED executable schema (not FROZEN).

Contract status: PROPOSED under E-001 / expanded under E-002 for
deterministic assembly + materials conversion replay.
Atlas remains sole freeze / ACCEPTED authority.
No Passport writes. No publication authority. No pricing.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from .provenance import QuantityResult

LEDGER_SCHEMA_VERSION = "0.2.0"
LEDGER_CONTRACT_STATUS: Literal["PROPOSED"] = "PROPOSED"


class LedgerProvenance(BaseModel):
    """Ledger-level provenance (calculator + input package identity)."""

    calculator_version: str
    formula_registry_version: str
    input_package_hash: str
    source_type: str = "deterministic_engine"
    waste_registry_version: Optional[str] = None
    purchase_rules_version: Optional[str] = None
    assembly_engine_version: Optional[str] = None
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
    # E-002 additive replay fields (optional)
    assembly_family: Optional[str] = None
    assembly_id: Optional[str] = None
    material_code: Optional[str] = None
    purchase_rule_id: Optional[str] = None
    base_quantity: Optional[str] = None
    waste_quantity: Optional[str] = None
    purchase_quantity: Optional[str] = None
    rounding_mode: Optional[str] = None
    package_size: Optional[str] = None


class ReplayStep(BaseModel):
    """Deterministic replay step for full reconstruction of an estimate path."""

    step_id: str
    sequence: int
    kind: Literal["assembly", "conversion", "math"]
    formula_id: str
    formula_version: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    output_value: str
    output_unit: str
    output_dimension: str
    engine_version: str
    assembly_family: Optional[str] = None
    assembly_id: Optional[str] = None
    material_code: Optional[str] = None
    purchase_rule_id: Optional[str] = None
    waste_policy_id: Optional[str] = None
    rounding_mode: Optional[str] = None
    package_size: Optional[str] = None
    base_quantity: Optional[str] = None
    waste_quantity: Optional[str] = None
    purchase_quantity: Optional[str] = None
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
    replay: List[ReplayStep] = Field(default_factory=list)
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
    assembly_family: Optional[str] = None,
    assembly_id: Optional[str] = None,
    material_code: Optional[str] = None,
    purchase_rule_id: Optional[str] = None,
    base_quantity: Optional[str] = None,
    waste_quantity: Optional[str] = None,
    purchase_quantity: Optional[str] = None,
    rounding_mode: Optional[str] = None,
    package_size: Optional[str] = None,
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
        assembly_family=assembly_family,
        assembly_id=assembly_id,
        material_code=material_code,
        purchase_rule_id=purchase_rule_id,
        base_quantity=base_quantity,
        waste_quantity=waste_quantity,
        purchase_quantity=purchase_quantity,
        rounding_mode=rounding_mode,
        package_size=package_size,
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
    waste_registry_version: Optional[str] = None,
    purchase_rules_version: Optional[str] = None,
    assembly_engine_version: Optional[str] = None,
    replay: Optional[Sequence[ReplayStep]] = None,
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
            waste_registry_version=waste_registry_version,
            purchase_rules_version=purchase_rules_version,
            assembly_engine_version=assembly_engine_version,
            notes=notes,
        ),
        confidence=confidence,
        unknown_state=ledger_unknown,
        entries=entries,
        replay=list(replay or []),
    )


def build_assembly_ledger(
    *,
    ledger_id: str,
    expansion: Any,
    formula_registry_version: str,
    waste_registry_version: Optional[str] = None,
    purchase_rules_version: Optional[str] = None,
    notes: Optional[str] = None,
) -> EstimateCalculationLedger:
    """Build a full deterministic-replay ledger from an AssemblyExpansion."""
    from .assemblies import AssemblyExpansion

    if expansion is None:
        from .errors import UnknownInputError

        raise UnknownInputError("expansion", "assembly expansion is required")
    if not isinstance(expansion, AssemblyExpansion):
        from .errors import UnknownInputError

        raise UnknownInputError("expansion", "expansion must be an AssemblyExpansion")

    entries: List[LedgerEntry] = []
    replay: List[ReplayStep] = []
    seq = 0

    for line in expansion.lines:
        seq += 1
        result = line.to_quantity_result(engine_version=expansion.engine_version)
        entry = entry_from_quantity_result(
            result,
            entry_id=f"{ledger_id}:{seq:04d}",
            sequence=seq,
            assembly_family=expansion.family,
            assembly_id=expansion.assembly_id,
            material_code=line.material_code,
            purchase_rule_id=line.default_purchase_rule_id,
            base_quantity=str(line.base_quantity),
        )
        entries.append(entry)
        replay.append(
            ReplayStep(
                step_id=f"{ledger_id}:replay:{seq:04d}",
                sequence=seq,
                kind="assembly",
                formula_id=line.formula_id,
                formula_version=line.formula_version,
                inputs=dict(line.input_refs),
                output_value=str(line.base_quantity),
                output_unit=line.unit,
                output_dimension=line.dimension.value,
                engine_version=expansion.engine_version,
                assembly_family=expansion.family,
                assembly_id=expansion.assembly_id,
                material_code=line.material_code,
                purchase_rule_id=line.default_purchase_rule_id,
                base_quantity=str(line.base_quantity),
                notes=line.notes,
            )
        )

    from .purchase_rules import PURCHASE_RULES

    for conv in expansion.conversions:
        seq += 1
        t = conv.transparent
        result = conv.purchase_result
        material_code = PURCHASE_RULES.get(t.purchase_rule_id).material_code
        entry = entry_from_quantity_result(
            result,
            entry_id=f"{ledger_id}:{seq:04d}",
            sequence=seq,
            assembly_family=expansion.family,
            assembly_id=expansion.assembly_id,
            material_code=material_code,
            purchase_rule_id=t.purchase_rule_id,
            base_quantity=str(t.base_quantity),
            waste_quantity=str(t.waste_quantity),
            purchase_quantity=str(t.purchase_quantity),
            rounding_mode=t.rounding_mode,
            package_size=str(t.package_size),
        )
        entries.append(entry)
        replay.append(
            ReplayStep(
                step_id=f"{ledger_id}:replay:{seq:04d}",
                sequence=seq,
                kind="conversion",
                formula_id=conv.formula_id,
                formula_version=conv.formula_version,
                inputs=dict(result.provenance.input_refs),
                output_value=str(t.purchase_quantity),
                output_unit=t.purchase_unit,
                output_dimension=result.dimension.value,
                engine_version=conv.engine_version,
                assembly_family=expansion.family,
                assembly_id=expansion.assembly_id,
                material_code=material_code,
                purchase_rule_id=t.purchase_rule_id,
                waste_policy_id=t.waste_policy_id,
                rounding_mode=t.rounding_mode,
                package_size=str(t.package_size),
                base_quantity=str(t.base_quantity),
                waste_quantity=str(t.waste_quantity),
                purchase_quantity=str(t.purchase_quantity),
                notes="transparent base/waste/purchase conversion; not a price",
            )
        )

    pkg_hash = hash_input_package(expansion.input_package)
    return EstimateCalculationLedger(
        ledger_id=ledger_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        provenance=LedgerProvenance(
            calculator_version=expansion.engine_version,
            formula_registry_version=formula_registry_version,
            input_package_hash=pkg_hash,
            waste_registry_version=waste_registry_version,
            purchase_rules_version=purchase_rules_version,
            assembly_engine_version=expansion.engine_version,
            notes=notes,
        ),
        confidence="deterministic",
        unknown_state=None,
        entries=entries,
        replay=replay,
    )


def replay_is_deterministic(ledger: EstimateCalculationLedger) -> bool:
    """True when every replay step is present, ordered, and deterministic-ready."""
    if not ledger.replay:
        return False
    if ledger.provenance.source_type != "deterministic_engine":
        return False
    prev = 0
    for step in ledger.replay:
        if step.sequence != prev + 1:
            return False
        prev = step.sequence
        if not step.formula_id or not step.formula_version:
            return False
        if step.output_value in ("NaN", "Infinity", "-Infinity"):
            return False
    return True
