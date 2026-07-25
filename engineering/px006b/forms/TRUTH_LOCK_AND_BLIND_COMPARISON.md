# Truth-Lock and Blind Comparison Procedures (Tier 3)

TOLERANCE_STATUS: PENDING_FIELD_EVIDENCE

## Field-truth lock procedure

1. Field Truth Team completes measurements.
2. Seal measurement forms and instrument records.
3. Compute checksum of locked truth package.
4. Store sealed package inaccessible to Software Team.
5. Record lock timestamp and custodian.

## Software-output lock procedure

1. Software Team processes capture without field truth access.
2. Lock algorithm outputs and receipts.
3. Compute checksum of locked software package.
4. Record lock timestamp and operator.

## Blind comparison procedure

1. Independent Comparator receives both sealed packages.
2. Reveal and compare only after both locks confirmed.
3. Preserve every difference; no post-disclosure alteration.
4. Publish discrepancy review record.

## Discrepancy review procedure

- Catalog each difference by metric group
- Classify as measurement, reconstruction, annotation, or process error
- No silent averaging

## Rerun authorization procedure

- Requires Atlas or designated program lead authorization
- Record reason, scope, and new lock IDs
- Prior sealed packages retained as evidence
