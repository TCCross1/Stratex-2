# PX-006A Data Governance

Every external dataset is classified with:

| Label | Value |
|-------|-------|
| data_origin | EXTERNAL_PUBLIC_DATASET |
| truth_status | NON_CANONICAL_TEST_DATA |
| physical_validation | NOT_PERFORMED |
| property_use | DEVELOPMENT_ONLY |
| customer_use | PROHIBITED |
| passport_publication | PROHIBITED |
| habitat_canonical_display | PROHIBITED |
| field_accuracy_claim | PROHIBITED |

## Rules

- No dataset may become approved Passport truth.
- No downloaded home/structure/site may be represented as a Stratex customer property.
- No person, address, owner, or resident may be identified.
- GPS retained only when technically necessary; never reverse-geocoded; never shown as street address.
- Committed summaries may state `GPS_PRESENT` / `GPS_ABSENT` / `GPS_PARTIAL` only.
- Public availability does not imply free redistribution.
