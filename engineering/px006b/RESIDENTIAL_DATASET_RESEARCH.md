# PX-006B Residential Dataset Research

Research date: 2026-07-25

## Sources researched

1. OpenDroneMap ODMdata catalog
2. OpenDroneMap individual dataset repositories (COPR, Toledo, Waterbury, Seneca)
3. ZRG academic residential rooftop dataset (WACV 2024) — not acquired; release gated
4. DJI Terra sample — already inventoried; redistribution prohibited

## Accepted for local development

| Dataset | Decision | Bytes |
|---------|----------|-------|
| COPR | APPROVED_WITH_ATTRIBUTION | ~331 MB acquired |

COPR selected because explicit `license.txt` (CC-BY-SA-4.0) and GCP control files are present. Initial registry mislabel as CC0 was corrected after reading `license.txt` — share-alike attribution applies; imagery remains untracked.

## License review required (not acquired)

| Dataset | Reason |
|---------|--------|
| TOLEDO | No explicit license file in repository root |
| WATERBURY | No explicit license file; large RTK corpus |
| ZRG | Academic gated release; privacy/commercial review required |

## Rejected

| Dataset | Reason |
|---------|--------|
| SENECA | Farm-field corpus; insufficient residential roof value |

## Privacy decisions

- No reverse geocoding performed
- No addresses or owner identity recorded
- Raw GPS coordinates redacted from tracked reports
- All binaries remain local under `STRATEX_DATASET_ROOT`

## Git tracking

No external imagery, point clouds, meshes, orthophotos, DSMs, or DTMs committed.
