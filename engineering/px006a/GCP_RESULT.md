# PX-006A GCP Result (BELLUS)

## Classification

- gcp_present_in_source: true
- gcp_use_classification: **accepted_and_used** (gcp_run2)
- gcp_sha256: `149e439dfb77908bc559e9a3b55575369ff0a9ac58e429a4fc8a8a444691bf0b`
- gcp_point_rows: 4
- header: WGS84 UTM 17N (ODM header accepted)

## Reconstruction

- status: SUCCESS
- duration_seconds: 543.649
- promoted: True
- outputs present: ['orthophoto', 'point_cloud', 'report', 'cameras']

## Honesty

GCP use improves reconstruction referencing but does **not** prove contractor-grade
measurement accuracy. physical_validation: NOT_PERFORMED

## Prior attempt

gcp_run1 succeeded photogrammetrically but misclassified GCP as rejected due to a
header-parser defect treating `WGS84 UTM 17N` as a data row. Parser repaired; gcp_run2
is the authoritative GCP-aware result.
