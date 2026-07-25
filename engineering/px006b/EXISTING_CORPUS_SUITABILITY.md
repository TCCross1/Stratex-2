# PX-006B Existing Corpus Suitability

Development benchmark suitability only. Not physical validation.

- Datasets reviewed: 7
- Residential structures identified: 1
- Small-building candidates: 4

## MYGLA

- Suitability: `CAPTURE_QUALITY_ONLY`
- License: `VERIFIED_RESTRICTED` (CC-BY-3.0)
- Residential structures: False
- Roof-plane benchmark: False
- Reconstruction executed: True

  - Starter ODM corpus (~29 images); useful for pipeline smoke only.
  - Not a residential roof benchmark corpus.

## AUKERMAN

- Suitability: `USEFUL_SMALL_BUILDING`
- License: `VERIFIED_PERMISSIVE` (CC0-1.0)
- Residential structures: False
- Roof-plane benchmark: True
- Reconstruction executed: False

  - Ohio dairy farm with barns and agricultural structures.
  - Pitched roofs present; not detached residential homes.

## BELLUS

- Suitability: `USEFUL_SMALL_BUILDING`
- License: `VERIFIED_PERMISSIVE` (CC0-1.0)
- Residential structures: False
- Roof-plane benchmark: True
- Reconstruction executed: True

  - Construction-site structures with GCP file.
  - Strong GCP/control reference for development benchmarking.

## CALITERRA

- Suitability: `HIGH_VALUE_RESIDENTIAL`
- License: `VERIFIED_PERMISSIVE` (CC0-1.0)
- Residential structures: True
- Roof-plane benchmark: True
- Reconstruction executed: False

  - Chile vineyard/residential estate structures.
  - Best existing corpus candidate for residential roof-plane work.

## GARFIELD

- Suitability: `GENERAL_GEOMETRY_ONLY`
- License: `VERIFIED_PERMISSIVE` (CC0-1.0)
- Residential structures: False
- Roof-plane benchmark: False
- Reconstruction executed: False

  - Minneapolis-St Paul urban/industrial mix; neighbor contamination risk.

## COPR

- Suitability: `USEFUL_SMALL_BUILDING`
- License: `VERIFIED_RESTRICTED` (CC-BY-SA-4.0)
- Residential structures: False
- Roof-plane benchmark: True
- Reconstruction executed: False

  - ODM COPR corpus with explicit CC-BY-SA-4.0 license.txt and GCP control files.
  - Share-alike and attribution required; never treat as CC0.
  - Acquired in PX-006B for GCP-aware roof benchmark development.

## DJI_TERRA_SAMPLE

- Suitability: `LICENSE_RESTRICTED_INVENTORY_ONLY`
- License: `REVIEW_REQUIRED` (DJI_TERMS_REVIEW_REQUIRED)
- Residential structures: unknown
- Roof-plane benchmark: False
- Reconstruction executed: False

  - License redistribution prohibited; inventory/metadata only.
  - Reconstruction blocked by license gate.

