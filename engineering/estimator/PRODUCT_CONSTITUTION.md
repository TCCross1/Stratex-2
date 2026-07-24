# Estimator Product Constitution (E-001)

**Product:** Stratex Estimator / Report Engine  
**Lane:** `LANE_3_ESTIMATOR_REPORT`  
**Checkpoint:** E-001 — Construction Mathematics Foundation  
**Status:** Binding product law for LANE 3 estimator work  
**Authority class:** Implementation constitution (not Passport authority)

---

## Official estimator law

> **Evidence supplies measurements. Deterministic engines calculate. AI interprets/advises. Qualified humans approve. Passport preserves assumptions/formulas/sources/revisions/results.**

### Non-negotiable arithmetic authority

1. **No language model may perform final authoritative arithmetic.**
2. Evidence and approved geometry supply measured or declared quantities.
3. The Construction Math Engine (and successor deterministic engines) alone
   compute linear, area, volume, board-foot, roofing-square, concrete
   purchase quantities, piece/package rounding, and waste/overage expansions.
4. AI may interpret results, propose assemblies, or advise on gaps — never
   replace engine outputs as the system of record.
5. Qualified humans approve estimate packages before any governed publication.
6. Passport (when later wired) preserves assumptions, formulas, sources,
   revisions, and results — it does not invent quantities.

---

## Separation of concerns

| Role | May do | Must not do |
| --- | --- | --- |
| Evidence / capture | Supply measurements, uncertainty, provenance | Invent purchase quantities |
| Construction Math Engine | Deterministic unit math, rounding, waste, ledgers | Price, margin, publish, approve |
| AI advisory | Explain, flag gaps, suggest alternatives | Final authoritative arithmetic |
| Qualified human | Approve / reject / revise assumptions | Silently alter ledger history |
| Passport / publication | Preserve approved truth | Recalculate outside approved engines |

---

## Mathematical foundation scope (E-001)

In scope for this checkpoint:

- Unit and dimensional arithmetic
- Feet / inches / fraction parsing
- Linear, area, and volume quantities
- Board-foot and roofing-square conversions
- Concrete volume and purchase-unit conversion
- Piece / package rounding
- Waste / overage registry
- Formula / version registry
- Quantity provenance structures
- Explicit unknown-input behavior (no silent zero-fill)
- `EstimateCalculationLedger` as a **PROPOSED** executable schema

Out of scope (forbidden in E-001):

- AI pricing or nationwide price feeds
- Homeowner proposals and contractor margins
- Complete report generation
- Unapproved Passport publishing
- Passport ledger writes
- Habitat canonical mutation
- Drone capture
- Marking contracts `FROZEN` / `ACCEPTED` without Atlas

---

## Unknown-input policy

Missing, null, or dimensionally incompatible inputs are **unknown states**.

- Engines must raise or return an explicit unknown — never coerce to `0`.
- Silent zero-fill is a constitutional violation.
- Ledger entries retain gaps instead of rewriting history.

---

## Provenance minimum

Every computed quantity must carry:

- `formula_id` and `formula_version`
- Input references (or explicit unknown markers)
- Calculator / engine version
- Waste / overage policy id when applied
- Confidence class compatible with shared contract fields

---

## Contract posture

`EstimateCalculationLedger` advances to **PROPOSED** executable schema under
E-001. It is **not FROZEN**. Atlas remains sole freeze/acceptance authority.
Dependent production routes must not treat PROPOSED as production-ready.

---

## Parallelization law

`PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY.`

Builders implement math and schemas. Auditors verify. Atlas authorizes merges
and freezes. No lane invents a second Passport writer, governed publish path,
or approval-policy owner.
