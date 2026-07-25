# PX-006B Confidence Model

Explainable **development-only** confidence states.

## Allowed states

- HIGH_DEVELOPMENT_CONFIDENCE
- MODERATE_DEVELOPMENT_CONFIDENCE
- LOW_DEVELOPMENT_CONFIDENCE
- INSUFFICIENT_EVIDENCE
- UNVALIDATED

## Inputs

Image count, overlap estimate, GPS completeness, reconstruction status, point density, plane residual, vegetation, oblique coverage, benchmark history, occlusion.

## Required explanation fields

- contributing_factors
- degrading_factors
- missing_evidence
- recommended_additional_capture
- human_review_required

These are **not** contractor-grade or insurance-grade accuracy levels.
