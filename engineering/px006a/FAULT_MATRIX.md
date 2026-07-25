# PX-006A Fault Matrix

Local-only derived fault scenarios (original corpus untouched):

| Scenario | Expected ATC/lab result |
|----------|-------------------------|
| one image removed | ADDITIONAL_DATA_REQUIRED_OR_WARNING |
| multiple images removed | ADDITIONAL_DATA_REQUIRED |
| duplicate image | DUPLICATE_CONTENT_DETECTED |
| renamed duplicate | DUPLICATE_CONTENT_DETECTED |
| truncated JPEG | MALFORMED_IMAGE_DETECTED |
| random binary as JPEG | MALFORMED_IMAGE_DETECTED |
| checksum mismatch | CHECKSUM_MISMATCH |
| timestamp outlier | TIMESTAMP_OUTLIER_WARNING |
| GPS missing one | GPS_PARTIAL |
| GPS missing all | GPS_ABSENT |
| camera-model mismatch | MIXED_CAMERA_DETECTED |
| focal-length inconsistency | FOCAL_INCONSISTENCY_WARNING |
| GCP removed | GCP_MISSING |
| GCP malformed | GCP_MALFORMED |
| unsupported file inserted | UNSUPPORTED_FORMAT |
| hidden file inserted | HIDDEN_FILE_WARNING |
| path traversal archive entry | ARCHIVE_TRAVERSAL_REJECTED |
| thermal/visual false pairing | THERMAL_PAIRING_WARNING |
| candidate declaring approved status | APPROVED_STATUS_REJECTED |
| raw-dictionary approval bypass | RAW_DICT_APPROVAL_REJECTED |
| mixed dataset contamination | MIXED_DATASET_CONTAMINATION |

Fault outputs remain under `STRATEX_DATASET_ROOT` and are untracked except tiny synthetic unit fixtures.
