# STRATEX CORE — NEXTGEN ARCHITECTURE BLUEPRINT v1.1
**Status**: REVISED · Awaiting Executive Approval
**Classification**: CONFIDENTIAL — PROPRIETARY *(revised per §15 correction)*
**Created**: Feb 26, 2026 · **Revised**: Feb 26, 2026 · **Approved**: —
**Author**: TC · Stratex AI Product Manager, under directive of Anthony Cross
**Reviewer**: Anthony Cross (Executive Architect)
**Revision identifier**: v1.1 · Directive-driven correction pass
**Preserves**: v1.0 (frozen, read-only in `/app/memory/_v1.0_PRESERVED_*`)

> **Version 1.1 principle**: Model-vendor names removed from architecture. Thermal registration made scientifically credible. Human-QA tiered. Passport access secured. Performance targets replaced with validation targets. All 20 executive corrections incorporated verbatim.

---

## 0. EXECUTIVE FRAMING

Stratex Core NextGen is the **Residential Property Intelligence Operating System** — an enterprise mission-control platform fusing hardware, specialized computation, and human review across three pillars:

| Pillar | Purpose |
|---|---|
| **Stratex Core** | Contractor operating system — mission, capture, intelligence, delivery |
| **Stratex Passport** | Permanent, hash-chained property intelligence record — the source of truth |
| **Stratex Habitat** | Homeowner-facing intelligence platform |

The drone is one sensor among many. Specialized computer-vision, photogrammetry, radiometric, and rule-based engines perform the authoritative technical work. General-purpose language models are used **only for narrative composition and orchestration hints**, never as the principal engine for measurement, safety, structural, or diagnostic decisions.

**Mandatory workflow chain — no module bypasses this:**
```
Mission Control → Mission Planning → Mission Validation → Flight →
Mission Assurance → Capture Validation → Digital Twin Generation →
AI Workforce Processing → Property Intelligence → AWE™ Intelligence →
Human QA → Report Generation → Property Passport Update →
Habitat Synchronization → Customer Delivery
```

---

## 1. APPLICATION STATE MODEL *(unchanged from v1.0)*

| State | Location | Deploy target | Modifiable? |
|---|---|---|---|
| **PRODUCTION** | `stratexdrone.com` | Frozen | Read-only |
| **NEXTGEN** | Preview | Active dev | Yes |
| **LEGACY** | `/legacy/*` | Not deployable | Read-only after freeze |

Migration is irreversible only after 10 parity gates pass (unchanged from v1.0).

---

## 2. MODULE HIERARCHY *(unchanged)*

14 first-class modules across four layers — Operations · Intelligence · Delivery · Platform. Full list identical to v1.0 §2.

---

## 3. NAVIGATION HIERARCHY

**Correction §4 applied** — AWE™ nav labels revised to reflect scientifically supportable scope:

```
AWE™ INTELLIGENCE
· Air        (ventilation indicators, intake/exhaust observations,
              exterior air-leakage indicators, condensation-risk
              indicators — NOT indoor air quality)
· Water      (moisture-retention indicators, roof water risk,
              wall retention indicators, thermal moisture proxies)
· Energy     (envelope thermal performance, heat-loss indicators,
              exterior thermal signatures)
· AWE Composite Index™  (calibrated per §20 validation program only)
```

All other nav sections identical to v1.0.

---

## 4. DATABASE DOMAINS

Ten **logical modules** inside a single MongoDB database initially. Only the **Passport domain** extracts to a separate database in Phase 2 (unchanged from v1.0 §4 + Appendix Q10).

New retention + PII classification rules per **§13 (new)** now apply per domain.

---

## 5. AI WORKFORCE ARCHITECTURE — REVISED

### 5.1 Vendor-neutral provider interfaces *(correction §1)*

Every logical agent binds to **capability interfaces**, not vendor names. Concrete provider mapping lives in deployment config, never in the architecture.

| Interface | Purpose | Concrete implementations may include |
|---|---|---|
| `ReasoningProvider` | Orchestration hints, workflow decisions | LLMs, rule engines |
| `NarrativeProvider` | Human-readable text composition | LLMs |
| `VisionProvider` | RGB scene classification, semantic segmentation | CV models, foundation vision models |
| `SegmentationProvider` | Pixel-level object/roof-plane segmentation | Specialized CV |
| `ThermalAnalysisProvider` | Radiometric anomaly detection | Specialized thermal CV + calibrated statistics |
| `MeasurementProvider` | Precise measurement extraction from twin | Deterministic geometry engines |
| `PhotogrammetryProvider` | Mesh + point-cloud generation | Commercial/open-source photogrammetry stacks |
| `BimProvider` | CAD/BIM derivative generation | Commercial BIM stacks |
| `RuleEngine` | Deterministic policies (ATC gates, product routing, tier logic) | In-house rules |
| `CalibrationProvider` | Sensor calibration + registration math | Deterministic algorithms |

**Safety-critical, measurement-critical, and engineering-relevant operations are performed by deterministic and specialized systems.** LLMs never author these values; they may only compose the narrative that accompanies them.

### 5.2 Agent-run audit record *(strengthened per §1)*

Every agent run persists to `agent_runs` with **all of the following mandatory fields**:

```
agent_run_id, agent_id, agent_version,
provider_id, provider_model, model_version, prompt_version,
algorithm_id, algorithm_version, runtime_config_hash,
input_hash, output_hash,
started_at, finished_at, cost_usd,
confidence_pct, evidence_ids[], provenance{}, 
implementation_state, verification_status
```

### 5.3 Twenty-four logical agents

Same 24-agent logical count as v1.0, mapped to five deployable services (Appendix Q1 unchanged). **Every agent binds to interfaces above** — no vendor names in the registry.

---

## 6. API BOUNDARIES

Five **logical route-prefix planes with distinct middleware chains** (Appendix Q11 unchanged). **Correction §6 applied to Public plane** — see §9 below.

---

## 7. EVENT FLOW & STATE MANAGEMENT

### 7.1 Frontend state
React Query (server state) + Zustand (small UI state). Adoption cost + rationale in Appendix Q13.

### 7.2 Critical event delivery — durable *(correction §11)*

Critical events must survive process restart, deploy, network interruption, worker failure, and duplicate delivery. **Phase 1 pattern**: transactional outbox in MongoDB + durable jobs collection with locking and idempotent retries. No external broker required.

**Critical event set** (durable):
- `finding.approved` → Passport append
- `passport.appended` → Habitat sync
- `habitat.ack_pending`
- `report.generation_pending`
- `evidence.package_finalization_pending`

**Non-critical events** (FastAPI in-process background tasks are acceptable):
- UI notifications
- Cache warming
- Log aggregation ticks

---

## 8. SYNCHRONIZATION FLOW

Core → Passport → Habitat. Cryptographic receipts (existing cosign SHA-256 pattern) on every accepted append. **Passport concurrency revised per §8 correction** — see §11 below.

---

## 9. SECURITY MODEL — REVISED

### 9.1 Public passport access *(correction §6)*

**The permanent Passport identifier hash is not a bearer credential.** Public access requires:
- **Expiring signed links** (default 24h TTL, configurable per recipient class)
- **Narrowly scoped projection** per audience: public / homeowner / contractor / adjuster / insurer
- **Recipient binding** optional (link tied to email or org)
- **Revocation** endpoint + kill-list check on every access
- **Access logging** to `audit_events` on every retrieval
- **Rate limiting** per recipient + per IP
- **No exposure** of private owner name, contact info, claim details, contractor internals, or security data on the public projection

### 9.2 MFA scope *(correction §7)*

MFA (or a phishing-resistant equivalent — WebAuthn/passkeys preferred) required for:
- CEO · Administrators · Organization owners
- Anyone managing credentials
- Anyone approving Tier 3 or Tier 4 findings (§10 below)
- Adjusters accessing claim evidence
- Engineers/reviewers signing controlled findings
- Users exporting sensitive property packages
- Users changing Passport authority or property ownership
- Users initiating privileged service actions

**Step-up authentication** required for high-risk actions even inside an active session (approvals, cosigns, ownership transfers, service-key rotation, evidence deletion).

### 9.3 Roles & authorization

Phase 1: `admin`, `contractor`, `pilot`, `inspector`, `homeowner`, `adjuster`, `engineer_reviewer`, `service`. RBAC + property-level ABAC via `property_org_bindings`. Full detail in Appendix Q9.

### 9.4 Tenant isolation for object storage *(correction §12)*

The **security outcome required is tenant isolation** — not a specific storage layout. Permitted implementations:
- Separate buckets per tenant
- Shared bucket with tenant-prefixed keys enforced by IAM policy
- Per-object access control
- Separate encryption contexts per tenant
- Signed URLs with tenant-scoped claims
- Service-mediated access

Provider choice, cost, and physical layout are deployment decisions — the architecture specifies the security guarantee, not the implementation.

### 9.5 Provenance chain
Every value resolves to `{provenance_type, model_confidence, measurement_uncertainty, finding_confidence, verification_status, reviewer, reviewed_at, truth_score_band, implementation_state}`.

### 9.6 Observability
Sentry, structured logs, OpenTelemetry tracing — **AWAITING INTEGRATION** (Phase 2+).

---

## 10. HUMAN QA — RISK-TIERED *(correction §5)*

Replaces the prior blanket "human gate on every finding" with a four-tier framework:

### Tier 1 — Automated informational
Image inventory · coverage status · visible-component counts · low-consequence classifications.
**May publish automatically when**: input quality passes · confidence ≥ approved threshold · no contradictory evidence · finding clearly labeled as automated.

### Tier 2 — Contractor review
Roof damage candidates · material quantities · window/door classifications · maintenance recommendations · estimate components.
**Requires**: qualified contractor or inspector review before customer delivery.

### Tier 3 — High-consequence
Probable moisture intrusion · significant energy-loss claims · structural concerns · insurance-related conclusions · safety issues · repair-release decisions · engineering deviations.
**Requires**: MFA-authenticated qualified human approval with signed cosign receipt.

### Tier 4 — Engineering-controlled
Structural adequacy · code compliance · engineering deviations · repair designs · safety certification · building release decisions.
**System must not independently approve.** Requires appropriately licensed or authorized professional signature.

### Finding schema (mandatory fields)
```
finding_id, risk_tier, required_reviewer_role, approval_status,
verification_method, release_restriction, ...
```

Every publisher (Passport append, report render, Habitat sync) checks `risk_tier` + `approval_status` before releasing.

---

## 11. PROPERTY PASSPORT AUTHORITY — REVISED

Ownership matrix unchanged from v1.0 §2 Appendix Q2 (Passport service alone writes; Core submits deltas; Habitat receives projections).

### 11.1 Concurrency: optimistic with explicit rebase *(correction §8)*

Replaces the prior "first-writer-wins" language. Workflow:

1. Client re-reads current Passport `seq`
2. Compare submitted delta against accepted intervening changes
3. **Automatically rebase** when non-conflicting
4. **Route materially conflicting findings to Human QA queue** — never silently discard
5. Preserve **both** attempted submissions in the audit trail (`passport_sync_log`)
6. Never overwrite or silently discard accepted history
7. Issue a new signed receipt only after successful append

Losing submissions are queued and surfaced; the losing user is notified with a rebase link.

### 11.2 Property identity resolution *(correction §14 — new)*

Passport identity is **never** a typed street address alone. Identity = controlled combination of:
- Normalized address (postal + geocoded)
- Parcel identifier (county/jurisdiction)
- Geographic coordinates (lat/lon with precision floor)
- Jurisdiction (city/county/state)
- Unit or structure identifier (for multi-unit buildings)
- Property boundary (polygon)
- Existing Passport records (fuzzy match + human review on conflict)

**Identity rules**:
- Duplicate Passports for the same home → rejected at mint with a match candidate list surfaced to human review
- Two homes incorrectly merged → separable via SUPERSEDE ledger entries
- Unit-level records not confused with parcel-level records (unit is a distinct identity slot)
- Ownership change is **not** a new property — it is a new record in `owners`, linked to the same Passport
- Address changes (renaming, renumbering) do not break history — Passport identity persists

**Property identity ≠ ownership identity.** They are distinct concepts modeled in separate collections (`properties`, `owners`, `property_org_bindings`).

---

## 12. DIGITAL TWIN ARCHITECTURE — REVISED

### 12.1 Layered canonical package *(correction §9)*

The Digital Twin is not one file. It is a **layered evidence package**:

| Layer | Contents |
|---|---|
| **Evidence geometry** | Original imagery, telemetry, point clouds, camera poses, control points, calibration data, reconstruction report, residual errors |
| **Measurement geometry** | Validated surfaces, coordinate reference, scale constraints, measurement entities, tolerances, confidence, provenance |
| **Presentation geometry** | glTF/GLB, Draco compression, KTX2 textures, mobile LODs, thermal + findings overlays |
| **Interchange derivatives** | IFC, DXF, PLY / LAS / LAZ / E57 where appropriate, GeoTIFF, report images |

**Compression, decimation, or presentation optimization must never alter the authoritative measurement record.** Presentation geometry is derived from — and always subordinate to — measurement geometry.

**IFC and DXF exports are generated only where source information supports those elements.** The system does not invent concealed framing, wall assemblies, or structural elements it did not observe.

### 12.2 Thermal-to-3D registration — calibrated pipeline *(correction §2)*

Replaces the prior "feature-based homography per capture" language, which was insufficient for complex three-dimensional houses.

Canonical pipeline:
1. **Preserve original radiometric thermal files** (see §14 below)
2. **Preserve** camera intrinsics, distortion coefficients, timestamps, pose, gimbal position, range information, environmental metadata
3. **Estimate thermal-camera extrinsics** relative to RGB and the property coordinate system
4. **Register each thermal observation** through calibrated camera projection
5. **Reproject radiometric data** onto validated 3D surfaces
6. **Perform depth and occlusion testing**
7. **Reject** reflected, grazing-angle, poorly registered, and hidden surfaces
8. **Store registration residuals and per-region confidence**
9. **Permit local homography only** as a limited method for verified planar regions
10. **Require human review** where registration error exceeds the approved threshold

**A colored thermal texture is never presented as a scientifically validated thermal finding.**

### 12.3 Vendor-neutral processors *(unchanged from v1.0)*
Photogrammetry, CAD/BIM, radiometric processing are all adapter contracts (`PhotogrammetryProvider`, `BimProvider`, `ThermalAnalysisProvider`). Concrete provider is swappable without changing Core.

### 12.4 Performance validation targets *(correction §10)*

Prior claim of "iPhone 12 60 fps" replaced with **testable acceptance targets, subject to measured validation**:

| Metric | Target |
|---|---|
| Initial useful view time | ≤ 4 s on supported devices |
| Maximum mobile payload (L2) | ≤ 25 MB per property |
| Interaction frame-rate | 30–60 fps target during normal interaction, subject to measured validation |
| Peak memory | ≤ 400 MB on iOS Safari |
| Crash-free session rate | ≥ 99% target once validated |
| Layer-switch latency | ≤ 1.5 s target |
| Progressive-loading | L2 → L1 → L0 on demand |
| Fallback behavior | 2D exhibit + gallery view for unsupported devices |
| Tested devices/browsers | Documented per release |

Nothing is promised as a guarantee until benchmarked on approved test properties.

---

## 13. DATA RETENTION, DELETION & LEGAL HOLD *(correction §13 — new)*

The Passport ledger is permanent. Not all other data is.

### Data classes + retention

| Class | Retention |
|---|---|
| **Passport ledger records** | Permanent (immutable, chain-verified) |
| **Raw mission evidence** (imagery, radiometric files, telemetry) | 7 years hot storage, then cold storage indefinitely |
| **Derived models** (twin, CAD, thermal reprojections) | 3 years hot, regenerable from evidence |
| **Temporary working files** (renders, caches) | 90 days rolling |
| **Personal information** (owner name, contact) | Retained while owner-property binding is active; corrected on request; scrubbed on legal deletion request |
| **Authentication logs** | 2 years hot, 7 years cold |
| **AI prompts + outputs** | 2 years hot, 7 years cold (audit-linked) |
| **Customer exports** | 30 days recoverable |
| **Deleted / corrected ownership data** | Corrected via SUPERSEDE ledger entries; historical record preserved unless legal deletion overrides |

### Policies
- **Customer-requested deletion**: honored per GDPR/CCPA where applicable, with cryptographic proof-of-deletion. Passport chain remains but PII fields are tombstoned.
- **Legal hold**: overrides retention; freezes deletion until released.
- **Insurance / claim preservation**: preserves evidence for claim-window duration + statutory buffer.
- **PII correction**: applied via SUPERSEDE, never destructive.
- **Account closure**: contractor-side data retained under org retention policy; homeowner-side data subject to deletion request.
- **Storage lifecycle**: hot → cold transitions automated per class.
- **Secure deletion**: crypto-shred keys for tombstoned records.
- **Backup retention**: matches primary; encrypted; access-audited.
- **Evidence immutability**: raw sensor data is never modified; corrections are new records.
- **Legal / contract exceptions**: documented per contract, override defaults.

**Nothing is claimed to be kept forever except the Passport ledger.**

---

## 14. ORIGINAL SENSOR DATA PRESERVATION *(correction §3)*

Normalized radiometric TIFF is **not** the sole thermal source of truth. The **canonical mission package** preserves:

- Original DJI radiometric files (R-JPG or vendor-native format)
- Original RGB files
- Original video where collected
- Flight logs
- Telemetry streams
- Sensor metadata (intrinsics, distortion, calibration)
- Checksums per file
- Calibration data
- Environmental records (temperature, humidity, wind, solar loading, precipitation history)
- Operator notes

Normalized TIFF, PNG, JPEG, glTF, point-cloud, and report derivatives are **generated derivatives** stored alongside the mission package.

Original evidence is **immutable and retained per §13**. The mission package — not a converted image — is the evidence source of truth.

---

## 15. PROVENANCE, CONFIDENCE & VERIFICATION LANGUAGE *(corrections §17 + §18)*

### 15.1 Distinct fields (correction §17)

"Verified" is a review state, not a confidence value. The finding schema separates:

| Field | Type | Purpose |
|---|---|---|
| `provenance_type` | enum | Source lineage (measured, calculated, estimated, imported, AI-assisted, human-entered) |
| `model_confidence` | 0–100 | Per-inference confidence |
| `measurement_uncertainty` | ± value with unit | Per-measurement error bar |
| `finding_confidence` | 0–100 | Aggregate confidence for a finding |
| `verification_status` | enum | Unreviewed / reviewed / verified / rejected / requires_field_verification |
| `reviewer` | user_id \| null | Approver identity |
| `reviewed_at` | timestamp \| null | Approval time |
| `truth_score_band` | enum (10-pt band) | Property record trust indicator |
| `implementation_state` | enum | Feature-state per §7 taxonomy |

Human approval does not automatically raise measurement accuracy. It raises `verification_status`, not `measurement_uncertainty`.

### 15.2 Provenance chip taxonomy (correction §18)

Chips are separated by category. UI may combine visually; the data model keeps them separate.

**Derivation**: Measured · Calculated · Estimated · Imported · AI-assisted · Human-entered
**Verification**: Unreviewed · Reviewed · Verified · Rejected · Requires field verification
**Implementation state**: Operational · Partially operational · Mocked · Planned · Awaiting credentials · Awaiting hardware · Awaiting validation · Deprecated · Legacy
**Evidence availability**: Complete · Partial · Missing · Contradictory

### 15.3 Truth Score (unchanged from Appendix Q4)
10-point bands only, never decimals. Marketing restricted until §20 validation passes.

---

## 16. PRODUCT-COST & PROCESSING-GATE ARCHITECTURE *(correction §19 — new)*

Stratex sells predictable **contractor products**, not token accounting. Three first-class products:

### Product definitions

| Product | Required mission type | Sensors | Processing engines | Human QA tier | Report template | Passport update | Habitat entitlement |
|---|---|---|---|---|---|---|---|
| **Stratex Core DayScan™** | Daytime RGB | RGB · GPS/RTK | Photogrammetry · Measurement · Roof/Window/Door Intelligence | Tier 2 | DayScan template | DayScan chain | DayScan projection |
| **Stratex AWE™ Scan** | Nighttime, eligibility-gated | Radiometric thermal · reference RGB · environmental sensors | Thermal Analysis · Water/Air/Energy AWE agents · Registration | Tier 3 | AWE template | AWE chain | AWE projection |
| **Stratex Elite™ Property Intelligence** | Both missions (DayScan + AWE Scan) | All | All + cross-registration + AWE Index™ | Tier 3 | Elite template | Combined update | Elite projection |

### Per-product policy fields (mandatory)
- Required capture conditions
- Human QA tier
- Contractor price
- Internal estimated cost (recorded to Cost Ledger)
- Upgrade rules (DayScan → Elite path)
- Rescan rules (failed capture → free rescan window)
- Failed-mission policy (partial-refund vs credit)

### Orchestrator responsibilities
The AI orchestrator **selects processing engines according to the purchased product and property complexity** — not by exposing token accounting to the contractor.

Internal compute + provider costs are still recorded per mission in the `cost_ledger` collection for finance and margin management.

---

## 17. FORMAL VALIDATION PROGRAM *(correction §20 — new)*

**No measurement, AWE score, defect classifier, or performance claim is promoted to "validated" merely because the software runs.**

### Field-validation program (Phase 2+)

Covers:
- Known-dimension test structures (in-house calibration properties)
- Independent manual roof measurements (surveyor-grade)
- Survey control (fixed control points on test properties)
- Repeat-flight reproducibility
- Different pilots
- Different weather
- Different roof materials (asphalt shingle, metal, tile, membrane)
- Different house geometries (simple gable → complex hip/valley)
- Thermal false positives (moisture-mimic exclusion, ventilation-shadow rejection)
- Moisture-meter comparison
- Blower-door comparison where applicable
- Interior/exterior thermal comparison
- Ground-truth repair findings (post-teardown reconciliation)
- Processor-to-processor comparison (swap `PhotogrammetryProvider` implementations)
- Measurement-error distributions (published per class)
- Failure-rate reporting

### Acceptance thresholds
Defined **before** Stratex uses any of the following marketing phrases:
- "Unmatched accuracy"
- "Certified"
- "Verified"
- "Engineering-grade"
- "Insurance-grade"

**Marketing language follows validation evidence. Until validated, product copy uses:**
"Prototype scoring — not calibrated to industry standard yet."

---

## 18. VISUAL DESIGN PRINCIPLES *(unchanged from v1.0)*

Mission-control aesthetic. Dark graphite base. Provenance chip taxonomy per §15.2. No generic SaaS.

---

## 19. EXECUTIVE ARCHITECTURE REVIEW *(unchanged from v1.0 §12)*

Strengths, weaknesses, tech debt, risks, missing integrations, performance, security, scalability, recommended improvements — retained from v1.0 with the addition that every v1.1 correction resolves a specific weakness.

---

## 20. PHASE 1 SCOPE CONTROL *(unchanged, reinforced)*

Phase 1 delivers architecture + operating shell. Does **not** claim production-ready photogrammetry, thermal diagnosis, engineering measurement, or automated AWE conclusions. Every screen carrying intelligence content wears a chip from §15.2.

---

## 21. FORBIDDEN LIST (Phase 1 non-scope) *(unchanged)*

- No DJI SDK integration
- No photogrammetry pipeline
- No real radiometric thermal ingest
- No CAD/BIM generator
- No real materials/labor DB
- No Habitat platform itself (only sync surface)
- No SSO
- No live payments checkout
- No multi-tenant migration (Phase 2)

---

## 22. IMPLEMENTATION SEQUENCE *(unchanged from v1.0)*

Phase 1a Legacy Freeze · Phase 1b NextGen Shell · Phase 1c Workspace Stubs · Phase 1d Screenshot + Executive Review Package.

---

## 23. APPROVAL BLOCK — v1.1

| Field | Value |
|---|---|
| Blueprint version | 1.1 |
| Created date | Feb 26, 2026 |
| Revised date | Feb 26, 2026 |
| Approved date | ☐ awaiting signature |
| Author | TC · Stratex AI Product Manager |
| Reviewer | Anthony Cross (Executive Architect) |
| Status | REVISED · AWAITING APPROVAL |
| Revision identifier | v1.1 · Directive-driven correction pass |

☐ Version 1.1 reviewed by Anthony Cross
☐ All 20 corrections confirmed incorporated
☐ Executive Architecture Review reviewed
☐ Phase 1 acceptance criteria confirmed
☐ Authorized to proceed to Phase 1a implementation

Signature: ______________________ Date: ______________

---

## APPENDIX — REVISION HISTORY

| Version | Date | Author | Change summary |
|---|---|---|---|
| 1.0 | Feb 26, 2026 | TC | Initial draft (623 lines) |
| 1.0-app | Feb 26, 2026 | TC | Review Appendix (Q1-Q14 · 950 lines) |
| **1.1** | Feb 26, 2026 | TC | **20 mandatory corrections applied. See STRATEX_Blueprint_v1.1_REDLINE.md for redline. v1.0 preserved unchanged at `/app/memory/_v1.0_PRESERVED_*`** |

**End of Blueprint v1.1.**
