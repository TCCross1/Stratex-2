# PX-006B Annotation Protocol

Manual benchmark truth workflow for external residential geometry benchmarking.

## Views

Annotators may use orthophoto, point cloud, mesh, DSM, source photographs, or roof-plan projections stored locally under `STRATEX_DATASET_ROOT`.

## Required objects

- building footprint
- roof outline
- individual roof planes
- ridges, hips, valleys, eaves, rakes
- roof penetrations, dormers, skylights, chimneys where visible
- wall extents where supportable
- obscured and uncertain regions

## Required metadata

- annotator, annotation method, source view, confidence, uncertainty reason
- coordinate system, version, revision history, review state

## Review states

DRAFT → SECOND_REVIEW_REQUIRED → BENCHMARK_ACCEPTED | DISPUTED | REJECTED

## Dual-pass requirement

At least two independent annotation passes are supported for selected structures. Inter-annotator disagreement is calculated and preserved without silent averaging.

## Truth classification

Manual annotations use `MANUAL_IMAGE_ANNOTATION` (or point-cloud/mesh variants). They are **not** canonical property truth.

## Physical validation

NOT PERFORMED for all external benchmark annotations.
