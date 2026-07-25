# Stratex Ground-Truth Home Program Protocol

Field-executable protocol for the first Stratex-controlled residential homes.
PX-006B prepares and completes this protocol package; it does **not** execute field validation.

**TOLERANCE_STATUS: PENDING_FIELD_EVIDENCE**

## Operational artifacts

| Artifact | Path |
|----------|------|
| Homeowner permission | `forms/HOMEOWNER_PERMISSION_CHECKLIST.md` |
| Property privacy | `forms/PROPERTY_PRIVACY_CHECKLIST.md` |
| Flight readiness | `forms/FLIGHT_READINESS_CHECKLIST.md` |
| M4E geometry mission | `forms/M4E_GEOMETRY_MISSION_CHECKLIST.md` |
| M4T visual/thermal | `forms/M4T_VISUAL_THERMAL_MISSION_CHECKLIST.md` |
| Field measurement forms | `forms/FIELD_MEASUREMENT_FORMS.md` |
| Checkpoint diagram | `forms/CHECKPOINT_DIAGRAM_TEMPLATE.md` |
| Truth lock / blind compare | `forms/TRUTH_LOCK_AND_BLIND_COMPARISON.md` |
| Field kit | `FIRST_FIELD_VALIDATION_KIT.md` |

## Tier 1 — Capture Development Home

**Purpose:** mission tuning, metadata validation, reconstruction tuning, operator training.

**Required:** owner permission, safe/legal flight, M4E geometry capture, M4T visual/thermal where available, flight logs, weather, lighting, RTK status, calibration status, source manifests, image manifest + checksum procedure.

## Tier 2 — Measured Control Home

Adds laser or tape control measurements, roof perimeter checkpoints where safely accessible, ground control/check points, wall and opening dimensions where relevant, roof-pitch and building-height reference, instrument identification and calibration, observer, timestamp, measurement uncertainty.

## Tier 3 — Blind Validation Home

**Separation controls:**

1. Field Truth Team collects and locks measurements
2. Software Team processes without seeing field truth
3. Algorithm output is locked
4. Independent Comparator reveals and compares results
5. No post-disclosure result alteration
6. Every difference preserved

See `forms/TRUTH_LOCK_AND_BLIND_COMPARISON.md`.

## Governance

- Homeowner consent and privacy required
- Address masking in all tracked artifacts
- No inspection diagnosis beyond evidence
- Failure handling, rerun rules, and audit records required
- **No numeric contractor-grade tolerances in PX-006B** — Atlas approval required after measured homes
- TOLERANCE_STATUS remains PENDING_FIELD_EVIDENCE

## Physical validation

NOT PERFORMED until authorized ground-truth program executes.

## First controlled-home readiness

READY_WITH_PREREQUISITES when protocol, forms, and field kit checklist are complete.

Remaining prerequisites: staffing separation for Tier 3, equipment procurement, Atlas tolerance governance after measured homes.
