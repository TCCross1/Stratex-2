# PX-006A Reconstruction Protocol

## Immutable image

Execution uses only the pinned reference in `ODM_IMAGE_DIGEST.yaml`:

`opendronemap/odm@sha256:<digest>`

- Never execute `opendronemap/odm:latest`
- Never invent digests
- Resolve digests via `docker pull <versioned-tag>` then `docker image inspect` RepoDigests

## Resource bounds

- CPU affinity via `taskset`
- PID limit via `docker --pids-limit`
- Wall-clock timeout
- No privileged container
- No host networking
- No Docker socket mount
- Source mount read-only; project output mount writable
- Disk preflight threshold: 15 GiB free

If the host cgroupv2 memory/cpu controllers are unavailable (threaded mode),
docker `--memory` / `--cpus` are not applied; the receipt documents the limitation
and remaining enforceable bounds.

## Success criteria

Container exit 0 alone is insufficient. Success requires non-empty expected
output class (orthophoto and/or point cloud), complete checksum manifest,
quarantine-before-promotion, and no path escape.

## Authority

Reconstruction-derived geometry remains unvalidated candidate reference only.
`physical_validation=NOT_PERFORMED`.
