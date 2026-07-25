# PX-006A — External Drone Dataset Laboratory

Development and compatibility laboratory for license-governed acquisition,
corpus registration, fault injection, and repeatable Stratex pipeline validation
against approved public drone-imagery datasets.

## What this is

- Software compatibility laboratory
- External public development corpus tooling
- Candidate-only ATC rehearsal inputs

## What this is not

- Physical property truth
- Field validation
- Customer evidence
- Production readiness
- Canonical Passport truth
- Habitat canonical display

## Permanent law

PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY.

## Storage

Downloaded binaries live under `STRATEX_DATASET_ROOT` (default
`/tmp/stratex-external-datasets`). They are never committed to Git.

## CLI

```bash
export STRATEX_DATASET_ROOT=/tmp/stratex-external-datasets
cd backend
python -m nextgen.dataset_lab acquire MYGLA
python -m nextgen.dataset_lab license-check MYGLA
python -m nextgen.dataset_lab inventory MYGLA
python -m nextgen.dataset_lab run --dataset MYGLA --profile smoke
```

## Atlas

No merge without separate Atlas authorization.
