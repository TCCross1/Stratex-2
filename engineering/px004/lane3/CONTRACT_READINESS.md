# CONTRACT_READINESS — PX-004 / LANE 3 / ESTIMATOR-E-002

**Lane:** `LANE_3_ESTIMATOR_REPORT`  
**Checkpoint:** E-002 — Deterministic Assembly Quantity Engine  
**Branch / worktree:** `cursor/lane3-estimator-e002-assemblies` @ `/tmp/stratex-px004-lane3`  
**Base SHA:** `5c9c78a23c18da84440d4bbdc117da7c961cc1f6`  
**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY  
**Recommendation:** **PROPOSED / NOT_READY for freeze**

---

## Official estimator law (binding)

> Evidence supplies measurements. Deterministic engines calculate. AI
> interprets/advises. Qualified humans approve. Passport preserves
> assumptions/formulas/sources/revisions/results.

**No language model may perform final authoritative arithmetic.**

---

## What E-002 delivered

| Component | Path | Role |
| --- | --- | --- |
| Assembly quantity engine | `backend/nextgen/estimator/assemblies.py` | Roofing, siding, concrete, flooring, drywall, insulation → net material lines |
| Materials conversion engine | `backend/nextgen/estimator/materials.py` | Base → waste → purchase with formula/version/rounding/waste provenance |
| Purchase rules registry | `backend/nextgen/estimator/purchase_rules.py` | Versioned package / increment rules; transparent base/waste/purchase |
| Waste registry expansion | `backend/nextgen/estimator/waste.py` | Flooring / drywall / insulation policies (additive) |
| Formula registry expansion | `backend/nextgen/estimator/formulas.py` | Assembly + materials.convert formulas; registry_version `e002.1.0.0` |
| Ledger replay expansion | `backend/nextgen/estimator/ledger.py` + schema `0.2.0` | Ordered `replay[]` for full deterministic reconstruction |
| Tests | `backend/tests/test_estimator_e002_assemblies.py` | Family coverage, rejection, replay, no-pricing guard |

E-001 Construction Math Engine remains authoritative for primitive math
(`ENGINE_VERSION = e001.1.0.0`). E-002 engines compose it; they do not replace it.

---

## Contract posture

| Contract | Registry version | Executable schema | Status | Freeze readiness |
| --- | --- | --- | --- | --- |
| EstimateCalculationLedger | 0.0.0 | 0.2.0 (additive replay) | **PROPOSED** | **NOT_READY** |
| EstimateInputPackage | 0.0.0 | — | NOT_IMPLEMENTED | NOT_READY |
| EstimateResult | 0.0.0 | — | NOT_IMPLEMENTED | NOT_READY |
| ReportPublicationPackage | 0.0.0 | — | NOT_IMPLEMENTED | NOT_READY |

### Contract recommendation

- Keep `EstimateCalculationLedger` **PROPOSED**.
- Do **not** mark FROZEN / ACCEPTED without `ATLAS_ARCHITECTURE_APPROVAL`.
- Production consumers must treat 0.2.0 as additive / non-authoritative until Atlas freeze.
- `EstimateInputPackage` / `EstimateResult` remain blocked until assembly profiles +
  (future) price provenance contracts are separately proposed — **out of E-002 scope**.

---

## Pricing / AI boundaries (hard)

| May | Must not |
| --- | --- |
| Deterministic quantity math | Invent unit prices, margins, or sell prices |
| Transparent base / waste / purchase qty | AI final authoritative arithmetic |
| Formula / waste / purchase-rule version stamps | Silent zero-fill of missing inputs |
| AI advisory interpretation of gaps | Passport ledger writes / governed publish |
| Human approval of assumptions | Claim FROZEN without Atlas |

Purchase cubic yards and package counts are **quantities**, not prices.
Notes in conversion provenance explicitly state “not a price”.

---

## Rejection policy (E-002)

Engines reject (raise) rather than invent:

- NaN / ±Infinity (non-finite)
- Negative base quantities where physically invalid
- Incompatible units / dimensions vs purchase rule
- Zero or non-positive package size / unit factor / purchase increment
- Unknown assembly family, missing required inputs, unknown rule ids

Known-zero (`0`) remains a valid deterministic quantity.

---

## Authority boundaries

- No Passport writer / `governed_publish` / approval-policy ownership.
- No Habitat canonical mutation.
- No report composition / homeowner proposal features.
- Shared `engineering/contracts/registry.yaml` touched only for EstimateCalculationLedger
  schema_notes (still PROPOSED). Merge serialization remains Atlas-owned.
- Builder does **not** authorize merge.

---

## Verify commands

```bash
pytest backend/tests/test_estimator_e001_math_foundation.py \
       backend/tests/test_estimator_e002_assemblies.py -q
./stratex verify --architecture
./stratex verify --security
./stratex verify --fast
```

---

## Handoff

Auditor should confirm: no pricing surfaces, no LM arithmetic authority, no
false freeze, no Passport authority paths, E-001 regressions green, replay
ledger remains PROPOSED. Merge requires `ATLAS_MERGE_AUTHORIZATION`.
