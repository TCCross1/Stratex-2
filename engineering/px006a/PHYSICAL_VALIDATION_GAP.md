# PX-006A Physical Validation Gap

Public external datasets and digest-pinned ODM reconstructions validate
**software compatibility only**.

They do **not** authorize:

- contractor-grade accuracy claims
- insurance-grade / insurer-grade accuracy claims
- homeowner truth claims
- thermal diagnosis claims
- RTK accuracy claims without proof
- Passport canonical property truth

Still required for real Stratex validation:

- Stratex-controlled homes / sites
- ground-truth dimensions / measured checkpoints
- blind field validation protocols
- governed Atlas authorization before any field-accuracy statement

`physical_validation: NOT_PERFORMED` on every PX-006A artifact.

Reconstruction-derived dimensions, when present, must be labeled:

- source=RECONSTRUCTION_DERIVED_CANDIDATE
- physical_validation=NOT_PERFORMED
- confidence=UNVALIDATED
- authoritative=false
