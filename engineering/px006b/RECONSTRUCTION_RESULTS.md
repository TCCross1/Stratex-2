# PX-006B Reconstruction Results

Statuses: successfully_executed | failed | skipped | license-blocked | not_attempted

Do not use PASS for an unexecuted reconstruction.

## ODM image

- Version: OpenDroneMap **3.5.6**
- Digest: `sha256:56be7b87a5ef3abfc0bb2afe88df839862fd18c41d26ca13672bf79cd2d59dd1`
- No silent replacement of the PX-006A-R1 accepted digest

## MYGLA — successfully_executed (prior PX-006A-R1; reused)

- Profile: smoke / roof-smoke compatible
- Status: SUCCESS, promoted
- Outputs: orthophoto, point_cloud, report, cameras
- DSM/mesh: not produced by smoke profile (`--skip-3dmodel`, `--fast-orthophoto`)
- Role in PX-006B: capture-quality / pipeline benchmark structure

## BELLUS — successfully_executed (prior PX-006A-R1; reused)

- Profile: gcp-reduced
- Status: SUCCESS, promoted; GCP accepted_and_used
- Outputs: orthophoto, point_cloud, report, cameras
- Role: GCP / small-building structure benchmark

## CALITERRA — roof-detail attempt

- Profile: roof-detail (digest-pinned ODM 3.5.6)
- Intent: residential roof-focused reconstruction
- Result: recorded at completion time in local receipts under `STRATEX_DATASET_ROOT`
- Local path only; not in Git

## AUKERMAN — roof-detail attempt

- Profile: roof-detail
- Intent: useful small-building / pitched-roof complexity
- Result: recorded at completion time in local receipts under `STRATEX_DATASET_ROOT`
- Local path only; not in Git

## COPR — failed (honest)

- Profile: gcp-reduced
- License: CC-BY-SA-4.0 (VERIFIED_RESTRICTED after `license.txt` inspection)
- GCP: accepted_and_used (27 points)
- Failure: ODM texrecon aborted with `stack smashing detected` / child return 134 during MVS texturing
- Promoted: false
- Outputs: none promoted
- Classification: failed / ODM_PROCESS_FAILED

## DJI_TERRA_SAMPLE — license-blocked

- Reconstruction not attempted for geometry benchmark
- LICENSE_REVIEW_REQUIRED / redistribution PROHIBITED

## Environment limitations

- Host Docker storage-driver: vfs (nested overlayfs remediation from PX-006A-R1)
- Host cgroupv2: docker `--memory` / `--cpus` unavailable (`HOST_CGROUP_MEMORY_CONTROLLER_UNAVAILABLE`)
- Bounds: taskset CPU affinity, `--pids-limit`, wall-clock timeout
- physical_validation: NOT_PERFORMED
