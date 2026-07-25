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

## Immutable ODM reconstruction

```bash
# Uses engineering/px006a/ODM_IMAGE_DIGEST.yaml pinned digest only
python -m nextgen.dataset_lab reconstruct MYGLA --profile smoke
python -m nextgen.dataset_lab reconstruct BELLUS --profile gcp-reduced
```

Never execute `opendronemap/odm:latest`. Large reconstruction outputs remain under
`STRATEX_DATASET_ROOT` and are never committed.
