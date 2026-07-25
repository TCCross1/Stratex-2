# ATC-001B Contract Readiness — LANE_2 Evidence Boundary

**Mission:** ATC-001B / PX-004  
**Lane:** `LANE_2_ATC_FIELD`  
**Branch:** `cursor/lane2-atc001b-evidence-boundary`  
**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY  

## Recommendation

**Keep shared registry contracts PROPOSED / READY_FOR_FREEZE.**  
Do **not** freeze `EvidenceManifest`, `ApprovedGeometry`, or `ApprovedFinding` from this checkpoint.

ATC-001B establishes an **executable producer/consumer boundary** and compatibility validator. It does **not** advance freeze status and does **not** claim production readiness.

| Contract | Registry status | ATC-001B stance | Notes |
| --- | --- | --- | --- |
| EvidenceManifest | PROPOSED | Producer output (candidates/fixtures) | Compatibility validated at 0.0.0 |
| ApprovedGeometryCandidate / GeometryCandidate | PROPOSED (candidate schema) | Producer alias only | `GeometryCandidate` ≡ ATC-001A type |
| ApprovedGeometry | PROPOSED | **Consumer only** — ATC must not emit | Marker schema under `schemas/atc` |
| AweEvidenceCandidate / AWEEvidenceCandidate | lane-local PROPOSED | Producer alias only | Spelling-normalized alias |
| ApprovedFinding | PROPOSED | **Consumer only** — ATC must not emit | Marker schema under `schemas/atc` |

## Alias / migration

See `backend/nextgen/schemas/atc/MIGRATION.md`.

- Do **not** silently rename shared contracts.
- Prefer `nextgen.schemas.atc` / `nextgen.atc` imports.
- **Collision risk:** `schemas/__init__.py` intentionally untouched (LANE_4 habitat coexistence).

## Profile boundary

| Profile | Producer emits | Consumer approved form | Doctrine |
| --- | --- | --- | --- |
| M4E_MAPPING | GeometryCandidate, EvidenceManifest | ApprovedGeometry | Not approved merely because from 4E |
| M4T_AWE | AWEEvidenceCandidate, EvidenceManifest | ApprovedFinding | Not dimensional authority; thermal ≠ dimensions |
| M400_P1_MAPPING | GeometryCandidate, EvidenceManifest | ApprovedGeometry | Forward-compat stub, same boundary |
| M400_H30T_AWE | AWEEvidenceCandidate, EvidenceManifest | ApprovedFinding | Forward-compat stub, same boundary |

## Quality gates

Executable enum (fixture evaluation only):

- `READY_FOR_REVIEW`
- `USABLE_WITH_LIMITATIONS`
- `ADDITIONAL_CAPTURE_REQUIRED`
- `REJECTED_PACKAGE`
- `UNSUPPORTED_FORMAT`

### C-N-003 pipeline limitation honesty (PX-005)

Synthetic parser → quality-gate pipeline remains foundational. It does **not**
claim complete professional review or approval. Synthetic packages stop at
`USABLE_WITH_LIMITATIONS` with explicit `SYNTHETIC_FIXTURE` and
`MISSING_PROFESSIONAL_REVIEW` limitations. Remaining review/approval producer
is outside ATC (Atlas / LANE_1 Passport path).

## Authority confirmation

ATC-001B modules under `backend/nextgen/atc/` and `backend/nextgen/schemas/atc/`:

- Do **not** call `append_entry` / `governed_publish` / `evaluate_approval_policy`
- Do **not** create Passport writer, publisher, or approval authority
- Refuse emission of `ApprovedGeometry` / `ApprovedFinding` via `AuthorityViolation`

## Physical-proof limitations

Synthetic fixtures only. This checkpoint does **not** prove:

- Live DJI SDK integration
- Physical field flights
- RTK survey accuracy
- Real radiometric R-JPG decode
- Automated thermal diagnosis
- Production-approved geometry or findings

## Atlas handoff

Builder does not self-authorize freeze or merge. Draft PR only. Atlas owns freeze and merge gates.
