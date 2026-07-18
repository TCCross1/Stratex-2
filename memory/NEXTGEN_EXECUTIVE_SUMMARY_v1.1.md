# STRATEX CORE — NEXTGEN ARCHITECTURE BLUEPRINT v1.1
## Executive Summary (One Page)

**Classification**: CONFIDENTIAL — PROPRIETARY
**Status**: REVISED · Awaiting Executive Approval
**Author**: TC · under directive of Anthony Cross
**Delivered**: Feb 26, 2026

---

### What v1.1 is
A **documentation-only revision pass** applying **all 20 mandatory executive corrections** to Blueprint v1.0. v1.0 is preserved unchanged as read-only reference. No implementation code was written. Production (`stratexdrone.com`) remains untouched.

### The four architectural shifts that matter
1. **Model-vendor neutrality** — Architecture references capability interfaces (`ThermalAnalysisProvider`, `MeasurementProvider`, etc.), never vendor names. Language models are confined to narrative composition; deterministic and specialized systems remain authoritative for measurement, safety, and structural decisions.
2. **Scientifically credible thermal registration** — A 10-step calibrated pipeline (extrinsics estimation, reprojection, occlusion testing, per-region residuals) replaces the single-homography approach. Colored thermal texture is never presented as a validated thermal finding.
3. **Secure Passport access** — The permanent hash is not a bearer credential. Access requires expiring signed links + scoped projections + revocation + access logging + rate limiting. Separate projections per audience (public / homeowner / contractor / adjuster / insurer).
4. **Risk-tiered Human QA** — Four tiers replace blanket approval, preventing a review bottleneck while preserving expert sign-off on high-consequence findings.

### New sections introduced in v1.1
- **§10** Risk-tiered Human QA (four tiers)
- **§11.2** Property identity resolution (address ≠ identity; identity ≠ ownership)
- **§13** Retention, deletion, legal-hold policy per data class
- **§14** Original sensor data preservation (mission package is source of truth)
- **§16** Product-cost architecture (DayScan · AWE Scan · Elite as first-class products)
- **§17** Formal validation program (15 dimensions) gates marketing language

### Deliverables included in this package
1. Full Markdown blueprint v1.1
2. Professional PDF v1.1 (cover · TOC · page numbers · revision history)
3. Redline change log (v1.0 → v1.1)
4. Architecture Decision Records (10 ADRs)
5. This one-page executive summary
6. Preserved v1.0 (read-only)

### Approval status
Blueprint v1.0 — approved directionally
Blueprint v1.1 — awaiting explicit executive approval
Phase 1a implementation — **withheld** until v1.1 is signed on Section 23

### The single sentence answer to "what changed"
> v1.1 replaces vendor lock-in, over-confident thermal claims, insecure public access, and unscalable human-QA gates with capability interfaces, calibrated thermal registration, signed access links, and risk-tiered review — while preserving every strategic declaration of v1.0.

---

**Files preserved** (v1.0 unchanged, chmod 444):
- `/app/memory/_v1.0_PRESERVED_BLUEPRINT.md`
- `/app/memory/_v1.0_PRESERVED_APPENDIX.md`
- `/app/memory/_v1.0_PRESERVED_Blueprint.pdf`

**Files added / regenerated** (v1.1):
- `/app/memory/NEXTGEN_ARCHITECTURE_BLUEPRINT_v1.1.md`
- `/app/memory/NEXTGEN_ARCHITECTURE_REDLINE_v1.0_to_v1.1.md`
- `/app/memory/NEXTGEN_ARCHITECTURE_ADRs_v1.1.md`
- `/app/memory/NEXTGEN_EXECUTIVE_SUMMARY_v1.1.md` (this file)
- `/app/memory/_blueprint_out/STRATEX_NextGen_Architecture_Blueprint_v1.1.pdf`

**Production**: Untouched. **Implementation code**: None written.
