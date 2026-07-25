# PX-006A Experiment Protocol

## Profiles

- `smoke`
- `inventory`
- `atc-validation`
- `reconstruction`
- `fault-matrix`
- `full-development`

## Receipt fields

Each run emits an immutable experiment receipt with:

- experiment_id (deterministic over dataset + profile + source revision + software commit + configuration)
- dataset_id, source revision, software commit
- configuration, parser versions
- ODM version/digest when applicable
- started_at, completed_at, duration
- stages executed and stage results
- warnings, failures
- generated artifact checksums
- truth limitations
- physical_validation = NOT_PERFORMED

Repeated identical runs must be comparable. A random timestamp alone must not define experiment identity.
