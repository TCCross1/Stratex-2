# PX-006B Reconstruction Results

Statuses: successfully_executed | failed | running | skipped | license-blocked | not_attempted

Do not use PASS for an unexecuted reconstruction.

## ODM image

- Version: OpenDroneMap **3.5.6**
- Digest: `sha256:56be7b87a5ef3abfc0bb2afe88df839862fd18c41d26ca13672bf79cd2d59dd1`
- No silent replacement of the PX-006A-R1 accepted digest

## MYGLA — successfully_executed (inherited PX-006A-R1)

- Classification: SUCCESS
- Profile: smoke
- Promoted: true
- Outputs: orthophoto, point_cloud, report, cameras
- DSM/mesh: not produced (`--skip-3dmodel`, `--fast-orthophoto`)
- Role: Structure A baseline

## BELLUS — successfully_executed (inherited PX-006A-R1)

- Classification: SUCCESS
- Profile: gcp-reduced
- Promoted: true
- GCP: accepted_and_used
- Outputs: orthophoto, point_cloud, report, cameras
- Role: Structure B GCP/control

## AUKERMAN — running (inherited PX-006B job; not duplicated)

- Classification: RUNNING
- Profile: roof-detail
- Started: 2026-07-25T15:07Z (local)
- Status at PX-006B-F1 audit: densify/openmvs still active; no SUCCESS receipt yet
- No duplicate job started

## CALITERRA — running (inherited PX-006B job; not duplicated)

- Classification: RUNNING
- Profile: roof-detail
- Started: 2026-07-25T15:07Z (local)
- Status at PX-006B-F1 audit: densify/openmvs still active; no SUCCESS receipt yet
- No duplicate job started

## COPR — failed (honest)

- Classification: FAILED
- Profile: gcp-reduced
- License: CC-BY-SA-4.0 (VERIFIED_RESTRICTED)
- GCP: accepted_and_used (27 points)
- Failure: ODM texrecon aborted (`stack smashing detected`, child return 134)
- Promoted: false
- Outputs: none promoted

## DJI_TERRA_SAMPLE — license-blocked

- Reconstruction not attempted
- LICENSE_REVIEW_REQUIRED / redistribution PROHIBITED

## Environment limitations

- Host Docker storage-driver: vfs
- Host cgroupv2: docker `--memory` / `--cpus` unavailable (`HOST_CGROUP_MEMORY_CONTROLLER_UNAVAILABLE`)
- Bounds: taskset CPU affinity, `--pids-limit`, wall-clock timeout
- physical_validation: NOT_PERFORMED

## Minimum coverage assessment

| Requirement | Evidence |
|-------------|----------|
| Simple/moderate building | MYGLA SUCCESS |
| GCP-aware structure | BELLUS SUCCESS |
| More-complex roof if available | AUKERMAN/CALITERRA RUNNING (not yet available as completed proof) |

High-detail DSM/mesh proof remains incomplete while roof-detail jobs run.
