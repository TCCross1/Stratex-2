# PX-006B Minimum Benchmark Structure Selection

Target: three structures. Expand only to replace unusable cases.

| Structure | Dataset | Role | Roof | Rationale |
|-----------|---------|------|------|-----------|
| mygla_starter_structure | MYGLA | Structure A — simple/moderate baseline | unknown / low complexity | Successful smoke reconstruction; clear orthophoto + point cloud; capture-quality baseline |
| bellus_gcp_structure | BELLUS | Structure B — GCP/control | low_slope / moderate | Successful gcp-reduced reconstruction; GCP accepted_and_used; control-aware path |
| aukerman_barn_primary or caliterra_primary_estate | AUKERMAN / CALITERRA | Structure C — complexity | gable / multi_plane_pitched | Pitched agricultural or residential estate complexity; roof-detail reconstruction inherited when complete |

## Known limitations

- External corpus is not Stratex-controlled residential truth
- MYGLA is not confirmed detached residential home
- BELLUS is construction-site, not homeowner property
- Annotation coordinates are orthophoto-local development references
- physical_validation=NOT_PERFORMED for all
