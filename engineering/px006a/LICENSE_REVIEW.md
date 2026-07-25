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

## Classifications (post-acquisition)

| Dataset | License status | License name | Redistribution | Attribution | Notes |
|---------|----------------|--------------|----------------|-------------|-------|
| MYGLA | VERIFIED_RESTRICTED | CC-BY-3.0 | ATTRIBUTION_REQUIRED_NO_TRACKED_IMAGERY | REQUIRED | README CC-BY marker (Tomasz Nycz). Imagery not committed. |
| AUKERMAN | VERIFIED_PERMISSIVE | CC0-1.0 | PERMITTED_WITH_SOURCE_ATTRIBUTION | RECORD_SOURCE | `license.txt` CC0 text matched. Raw imagery still not committed. |
| BELLUS | VERIFIED_PERMISSIVE | CC0-1.0 | PERMITTED_WITH_SOURCE_ATTRIBUTION | RECORD_SOURCE | `license.txt` CC0 text matched. |
| CALITERRA | VERIFIED_PERMISSIVE | CC0-1.0 | PERMITTED_WITH_SOURCE_ATTRIBUTION | RECORD_SOURCE | `license.html` CC0 text matched (Dennis Baldwin attribution recorded). |
| GARFIELD | VERIFIED_PERMISSIVE | CC0-1.0 | PERMITTED_WITH_SOURCE_ATTRIBUTION | RECORD_SOURCE | `license.txt` CC0 text matched. |
| DJI_TERRA_SAMPLE | REVIEW_REQUIRED | DJI_TERMS_REVIEW_REQUIRED | PROHIBITED | REQUIRED | Local evaluation only. `redistribution_allowed=false`. Do not redistribute. |

## Redistribution decisions

- Third-party drone imagery binaries: **never tracked in Git**
- Tiny Stratex-generated synthetic fixtures: allowed when license gate permits
- DJI Terra sample: **PROHIBITED** redistribution

## License blockers

- DJI_TERRA_SAMPLE blocks tracked derivative fixtures and commercial/promotional claims
- MYGLA CC-BY requires attribution; blocks tracked third-party imagery fixtures
