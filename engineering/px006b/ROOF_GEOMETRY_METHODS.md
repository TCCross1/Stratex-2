# PX-006B Roof Geometry Methods

Deterministic and explainable roof geometry candidate extraction.

## Structure segmentation

- Algorithm: `orthophoto_extent_bbox_v1` (deterministic extent heuristic)
- State: PROPOSED → REVIEW_REQUIRED → BENCHMARK_ACCEPTED | REJECTED
- AI may propose; AI may not approve

## Roof-plane extraction

- Primary method: RANSAC plane fitting on georeferenced LAZ point clouds
- Supporting methods available for extension: normal clustering, region growing, DSM slope segmentation
- No single opaque AI geometry authority

## Edge classification

Edge classes: EAVE, RAKE, RIDGE, HIP, VALLEY, STEP, UNKNOWN

Each edge retains detected class, confidence, supporting geometry, alternative classifications, and review state.

## Measurements

All measurements are deterministic from annotated or derived geometry:

- shoelace polygon area for footprint and roof outline
- summed plane areas for total roof surface
- edge-length aggregation by class
- pitch from plane normal vector

Rounding rule: `half_up_2dp`

## Authority

All outputs are `RECONSTRUCTION_DERIVED_CANDIDATE` or manual benchmark annotations with `authoritative=false`.
