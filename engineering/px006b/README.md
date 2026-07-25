# PX-006B Residential Geometry Benchmark

Development-only residential geometry and measurement benchmark built on the merged PX-006A External Drone Dataset Laboratory.

## Status

- **PX-006B classification:** algorithmic benchmark work
- **Production readiness:** NOT READY
- **Physical validation:** NOT PERFORMED
- **Canonical property truth:** PROHIBITED
- **Approved geometry / findings:** PROHIBITED

## Scope

1. Evaluate external corpus residential usefulness
2. Acquire additional license-approved datasets when needed
3. Execute digest-pinned ODM reconstruction
4. Detect structures and roof planes
5. Calculate deterministic measurement candidates
6. Compare machine output against manual benchmark annotations
7. Identify failure modes and confidence limits
8. Prepare capture protocol for first Stratex-controlled homes

## Module

```bash
cd backend
export STRATEX_DATASET_ROOT=/tmp/stratex-external-datasets
python3 -m nextgen.residential_geometry_benchmark audit-corpus
python3 -m nextgen.residential_geometry_benchmark reconstruct CALITERRA --profile roof-detail
python3 -m nextgen.residential_geometry_benchmark run-benchmark
```

## ODM digest

Uses immutable PX-006A-R1 digest `sha256:56be7b87a5ef3abfc0bb2afe88df839862fd18c41d26ca13672bf79cd2d59dd1` (OpenDroneMap 3.5.6). No silent replacement.

## Artifacts

- Local benchmark runs: `$STRATEX_DATASET_ROOT/px006b_benchmark/`
- Local reconstructions: `$STRATEX_DATASET_ROOT/reconstructions/`
- No external imagery, point clouds, meshes, or orthophotos are tracked in Git.

## Related documents

- `EXISTING_CORPUS_SUITABILITY.md`
- `RESIDENTIAL_DATASET_RESEARCH.md`
- `BENCHMARK_DATA_MODEL.md`
- `ANNOTATION_PROTOCOL.md`
- `ROOF_GEOMETRY_METHODS.md`
- `BENCHMARK_METRICS.md`
- `CONFIDENCE_MODEL.md`
- `FAILURE_TAXONOMY.md`
- `RECONSTRUCTION_RESULTS.md`
- `RESIDENTIAL_BENCHMARK_MATRIX.md`
- `STRATEX_GROUND_TRUTH_HOME_PROTOCOL.md`
- `FIRST_FIELD_VALIDATION_KIT.md`
- `PHYSICAL_VALIDATION_GAP.md`
