# PX-006B Benchmark Data Model

Every benchmark object is non-authoritative development data.

## Required entities

| Entity | Purpose |
|--------|---------|
| ResidentialBenchmarkDataset | Corpus-level benchmark scope |
| BenchmarkStructure | One building or structure under test |
| BenchmarkRoof | Roof aggregate geometry |
| BenchmarkRoofPlane | Individual plane candidate |
| BenchmarkRoofEdge | Classified edge candidate |
| BenchmarkRoofOpening | Penetration or opening annotation |
| BenchmarkWallPlane | Visible wall extent where supportable |
| BenchmarkAnnotation | Manual or derived truth pass |
| BenchmarkMeasurement | Deterministic calculated candidate |
| BenchmarkRun | End-to-end benchmark execution receipt |
| BenchmarkComparison | Candidate vs annotation metrics |
| BenchmarkFailure | Taxonomy-classified failure |
| BenchmarkConfidenceAssessment | Explainable development confidence |

## Required fields (all objects)

- `benchmark_id`, `dataset_id`, `source_revision`, `structure_id`
- `annotation_version`, `algorithm_version`, `reconstruction_version`, `odm_digest`
- `coordinate_reference`, `units`, `evidence_references`
- `created_at`, `created_by`, `source_classification`, `truth_classification`
- `physical_validation=NOT_PERFORMED`, `authoritative=false`, `limitations`

## Allowed truth classifications

- MANUAL_IMAGE_ANNOTATION
- MANUAL_POINT_CLOUD_ANNOTATION
- MANUAL_MESH_ANNOTATION
- SOURCE_PROVIDED_CONTROL
- RECONSTRUCTION_DERIVED_CANDIDATE
- SYNTHETIC_REFERENCE

## Prohibited

- CANONICAL_PROPERTY_TRUTH
- ApprovedGeometry / ApprovedFinding emission

## Implementation

Python package: `backend/nextgen/residential_geometry_benchmark/`
