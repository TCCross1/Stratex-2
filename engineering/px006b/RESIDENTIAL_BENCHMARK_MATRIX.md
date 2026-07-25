# PX-006B Residential Benchmark Matrix

Development-only matrix. No universal production tolerances. Physical validation NOT PERFORMED.

Machine-readable: `RESIDENTIAL_BENCHMARK_MATRIX.yaml` (generated under `engineering/px006b/` and refreshed by the benchmark runner).

## Required fields

- benchmark structure ID, dataset, building type, roof type, roof complexity
- source camera, image count, nadir/oblique coverage, point-cloud density
- GCP status, manual annotation status, algorithm run
- structure IoU, roof boundary metric, roof-plane metric
- area difference, edge-length difference
- confidence state, failure classes, recommended recapture
- benchmark disposition

## Allowed dispositions

BENCHMARK_ACCEPTED | ACCEPTED_WITH_LIMITATIONS | INSUFFICIENT_EVIDENCE | RECONSTRUCTION_FAILED | ANNOTATION_DISPUTED | LICENSE_BLOCKED | PRIVACY_BLOCKED

## Selected structures (initial)

| Structure | Dataset | Building type | Roof | Disposition basis |
|-----------|---------|---------------|------|-------------------|
| mygla_starter_structure | MYGLA | unknown_small_structure | unknown | Capture-quality only; dual annotation |
| bellus_gcp_structure | BELLUS | construction_structure | low_slope | GCP control; dual annotation |
| caliterra_primary_estate | CALITERRA | residential_estate | multi_plane_pitched | Highest residential usefulness |
| aukerman_barn_primary | AUKERMAN | agricultural_barn | gable | Useful small building |
| copr_gcp_structure | COPR | small_building_with_gcp | unknown | GCP; reconstruction may fail |

## Metric limitations

- Bounding-box IoU proxies are development aids
- External corpus does not authorize contractor-grade tolerances
- All rows: `authoritative=false`, `physical_validation=NOT_PERFORMED`
