# Canonical Mission Package Sealing Contract

**Version:** 1.0.0  
**Status:** Required for Field Test v1  
**Authority:** Core only. Habitat is read-only.

## Purpose
Defines the exact structure that a sealed evidence package from Matrice 4E / 4T missions must conform to before it may be published into Passport.

## Package Identity
- `package_id`: UUID v4
- `mission_id`: UUID of the parent mission
- `tenant_id` + `property_id`: Required isolation keys
- `created_at`: ISO-8601 UTC
- `seal_algorithm`: HMAC-SHA256 (or stronger)
- `content_hash`: SHA-256 of the canonical payload
- `prior_package_hash`: Optional chain to previous package for the same property

## Required Sections
1. **Mission Metadata**
   - Aircraft profile (4E or 4T)
   - Pilot / operator
   - Capture type (DAYTIME_PRECISION_MAPPING | NIGHTTIME_AWE_VISUAL_THERMAL)
   - Weather, RTK status, battery, calibration flags

2. **Evidence Manifest**
   - List of all media items with:
     - content_hash (SHA-256)
     - media_type (RGB | THERMAL | RADIOMETRIC | OTHER)
     - capture_timestamp
     - camera_model / lens
     - geolocation (if available)
     - size_bytes

3. **Geometry Candidate** (4E path)
   - Roof planes, ridges, valleys, hips, eaves, rakes
   - Linear measurements and areas
   - Confidence scores per plane
   - Withholding flags for low-confidence geometry

4. **AWE Candidate** (4T path)
   - Surface temperature patterns
   - Anomaly candidates (heat loss, moisture indicators, etc.)
   - Truth classification per finding
   - Explicit “requires confirmation” flags

5. **Seal Record**
   - seal_key_version
   - signature
   - sealed_at
   - sealer_identity

## Rules
- A package that fails any required section or seal verification is rejected.
- Geometry with confidence below threshold is marked WITHHELD and never enters Passport as truth.
- Only the governed publisher may submit a sealed package for Passport append.
- Idempotency key must be derived from package_id + content_hash.

## Implementation Notes
- This contract is enforced in Core before any call to `governed_publish`.
- Habitat receives only the resulting Passport projections, never the raw package.
