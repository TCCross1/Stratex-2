# PX-006B Failure Taxonomy

Residential reconstruction and geometry failure classes for development benchmarking.

## Classes implemented

INSUFFICIENT_OVERLAP, NADIR_ONLY_ROOF_LIMITATION, VEGETATION_OCCLUSION, GCP_MISSING, LICENSE_BLOCKED, ATTACHED_GARAGE_MERGED, NEIGHBORING_HOME_CONTAMINATION, POINT_CLOUD_HOLE

(Full taxonomy registry includes additional classes for future detectors.)

## Each failure defines

- detector
- severity
- affected outputs
- whether reconstruction may continue
- whether measurement candidates must be withheld
- recommended recapture pattern
- homeowner-safe explanation
- audit event

## Recapture recommendations

All recommendations use state `PROPOSED_CAPTURE_ADJUSTMENT`. They are not mission approval. ATC retains orchestration authority.
