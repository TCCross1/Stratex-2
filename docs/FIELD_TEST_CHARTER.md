# Stratex Field Test Charter — v1

**Branch:** field-test/ready-v1  
**Status:** Active  
**Owner:** Atlas (Principal Authority)  
**Date:** 2026-08-01

## Purpose
This document is the single definition of “Done” for the first controlled field test of Stratex.

## Definition of Successful First Controlled Field Test

The first controlled field test is considered successful only when **all** of the following are true:

1. A real or high-fidelity Matrice 4E (daytime geometry) mission can pass ATC readiness checks.
2. Evidence is collected and sealed into a **Canonical Mission Package** that is content-addressed (SHA-256), provenance-bearing, and immutable.
3. The sealed package is published through the **single** governed publisher into the **single** Passport writer (`nextgen.passport_service.append_entry`).
4. The resulting Passport entry is hash-chained and verifiable via the existing verification endpoint.
5. Low-confidence or incomplete geometry is correctly **withheld** (never published as truth).
6. A clean, versioned projection is produced that Habitat’s `PassportProjectionAdapter` can successfully consume.
7. The entire path is covered by automated tests + this written checklist.
8. Atlas reviews the evidence package and signs off.

## Explicitly Out of Scope for Field Test v1
- Full Habitat visual polish
- Interior Reality Studio / LiDAR
- Advanced estimator sophistication
- Multi-property batch processing
- Production-scale performance tuning

## Success Metrics
- Zero fabricated measurements, dimensions, or confidence scores
- All published findings carry truth classification (VERIFIED / ESTIMATED / PROJECTED / UNKNOWN)
- Habitat never writes canonical Passport data
- One writer, one governed publisher preserved

## Sign-off
- [ ] Technical readiness (ATC + Sealing + Publication + Projection)
- [ ] Evidence package reviewed
- [ ] Atlas final approval

