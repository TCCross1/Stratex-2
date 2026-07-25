# PX-006A License Review

Conservative license gate. Never guess permissive status from repository visibility.
Never treat “publicly downloadable” as “freely redistributable”.

## Status vocabulary

- `VERIFIED_PERMISSIVE`
- `VERIFIED_RESTRICTED`
- `REVIEW_REQUIRED`
- `UNKNOWN`
- `REJECTED`

Datasets with `UNKNOWN`, `REVIEW_REQUIRED`, or `REJECTED` may be inventoried locally
but must not create redistributable tracked fixtures from third-party imagery.

## Classifications (updated after acquisition)

| Dataset | License status | Redistribution | Notes |
|---------|----------------|----------------|-------|
| MYGLA | PENDING_ACQUISITION | BLOCKED_UNTIL_VERIFIED | Read LICENSE from acquired repo |
| AUKERMAN | PENDING_ACQUISITION | BLOCKED_UNTIL_VERIFIED | Expected CC0 — verify text |
| BELLUS | PENDING_ACQUISITION | BLOCKED_UNTIL_VERIFIED | Expected CC0 — verify text |
| CALITERRA | PENDING_ACQUISITION | BLOCKED_UNTIL_VERIFIED | Read LICENSE before use |
| GARFIELD | PENDING_ACQUISITION | BLOCKED_UNTIL_VERIFIED | Read LICENSE before use |
| DJI_TERRA_SAMPLE | REVIEW_REQUIRED | PROHIBITED | Local evaluation only; do not redistribute |

Attribution: preserve source organization and source page for every corpus.
