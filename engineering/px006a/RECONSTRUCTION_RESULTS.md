# PX-006A Reconstruction Results

Statuses: successfully_executed | failed | skipped | unsupported | license-blocked | not_attempted

Do not use PASS for an unexecuted reconstruction.

## MYGLA — successfully_executed

- Profile: smoke
- Attempts: 2 successful (smoke_run1, smoke_run2); prior failed attempts before Docker vfs remediation and cgroup workarounds
- Dataset revision: `cf0ef2f1dd779c04fc0d55324692c60fe6cc7597`
- Manifest checksum verified: True
- License: VERIFIED_RESTRICTED (CC-BY-3.0)
- ODM digest: `sha256:56be7b87a5ef3abfc0bb2afe88df839862fd18c41d26ca13672bf79cd2d59dd1`
- Duration run1: 152.496s; run2: 153.842s
- Images: 29
- Output bytes (run1): 8066613
- Output classes present: orthophoto, point_cloud (.laz), report, cameras
- Promoted: true (quarantine then atomic rename)
- Local path only under STRATEX_DATASET_ROOT (not in Git)

## BELLUS — successfully_executed

- Profile: gcp-reduced
- gcp_run1: SUCCESS with GCP initially misclassified rejected due to header parser bug (WGS84 UTM 17N)
- gcp_run2: SUCCESS (543.649s); GCP accepted_and_used; outputs promoted
- Dataset revision: `36f80864035e243aa443420b9be867770d7e8118`
- License: VERIFIED_PERMISSIVE (CC0-1.0)
- Duration gcp_run1: 726.152s
- Images: 122
- Output bytes (gcp_run1): 174551230
- Output classes: orthophoto, point_cloud, report, cameras
- Not dimensional validation; GCP does not prove contractor-grade accuracy

## DJI_TERRA_SAMPLE — license-blocked

- Reconstruction attempted: false
- Disposition: LICENSE_REVIEW_REQUIRED
- redistribution_allowed: false
- Metadata inventory counts: {"terra_project_metadata": 0, "mission_metadata": 0, "aerotriangulation_products": 0, "orthophotos": 0, "point_clouds": 0, "meshes": 0, "reconstruction_reports": 0, "mission_json": 0, "camera_sensor_metadata": 2, "images": 238, "other": 6}

## Environment limitations

- Host nested overlayfs required Docker storage-driver=vfs remediation
- Host cgroupv2 docker controller threaded: docker --memory/--cpus unavailable
- Bounds applied via taskset CPU affinity, --pids-limit, wall-clock timeout
- physical_validation: NOT_PERFORMED
