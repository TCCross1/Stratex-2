# STRATEX BLUEPRINT — ARCHITECTURE DECISION RECORDS (ADRs)
**Companion to Blueprint v1.1 · Each ADR justifies one major correction.**

---

## ADR-001 · Model-Vendor Neutrality
**Status**: Accepted (v1.1)
**Context**: Blueprint v1.0 hardcoded "Claude Sonnet 4.6" into agent registry, creating vendor lock-in and incorrectly treating a general-purpose LLM as the principal engine for measurement and safety-critical operations.
**Decision**: Architecture references only capability interfaces (`ReasoningProvider`, `VisionProvider`, `ThermalAnalysisProvider`, `SegmentationProvider`, `MeasurementProvider`, `NarrativeProvider`, `RuleEngine`, `PhotogrammetryProvider`, `BimProvider`, `CalibrationProvider`). Concrete vendor + model bindings live in deployment configuration only.
**Consequences**: Provider swap is a config change, not a code change. LLM outputs are confined to narrative composition; deterministic and specialized systems remain authoritative for measurements, safety, and structural findings. Every `agent_runs` row records the actual provider + model + prompt version at runtime for audit.

---

## ADR-002 · Calibrated Thermal Registration Pipeline
**Status**: Accepted (v1.1)
**Context**: Feature-based homography per capture is insufficient for complex three-dimensional houses (roofs, dormers, valleys, soffits, projections, occlusions).
**Decision**: 10-step calibrated registration pipeline. Estimate thermal-camera extrinsics against RGB + property coordinate system → reproject radiometric data onto validated 3D surfaces → depth and occlusion testing → reject reflected, grazing, poorly registered surfaces → store per-region confidence. Local homography permitted only for verified planar regions.
**Consequences**: Thermal findings become scientifically defensible. Registration residuals are stored per region. Findings above configurable error thresholds require human review before Passport append. Colored thermal texture is never presented as a scientifically validated thermal finding.

---

## ADR-003 · Preserve Original Sensor Data
**Status**: Accepted (v1.1)
**Context**: Normalized derivatives (TIFF, PNG, glTF) cannot be the source of truth. Conversion loss and lossy re-encoding invalidate any later scientific claim.
**Decision**: The **canonical mission package** stores original DJI radiometric files, RGB, video, flight logs, telemetry, sensor metadata, checksums, calibration data, environmental records, and operator notes. All derived assets are labeled as derivatives.
**Consequences**: Retention costs increase (mitigated by §13 lifecycle policy). Evidence chain-of-custody becomes provable. Reprocessing with a swapped `ThermalAnalysisProvider` or `PhotogrammetryProvider` is possible against the original evidence.

---

## ADR-004 · Air Intelligence Scope Correction
**Status**: Accepted (v1.1)
**Context**: Exterior thermal imagery cannot establish indoor air quality, mold presence, CO₂, radon, or definitive airflow rates.
**Decision**: AWE Air scope initially limited to ventilation indicators, exterior air-leakage indicators, condensation-risk indicators, crawlspace/foundation ventilation observations, and areas requiring interior verification. Any indoor air quality diagnosis requires appropriate sensors and field validation.
**Consequences**: Product marketing must not claim indoor air quality. "A mold-risk indicator is not a mold diagnosis" enshrined in v1.1. Future indoor air quality capability requires separate sensor product + hardware.

---

## ADR-005 · Risk-Tiered Human QA
**Status**: Accepted (v1.1)
**Context**: Blueprint v1.0 required human approval on nearly every finding — an operational bottleneck at scale.
**Decision**: Four-tier QA framework. Tier 1 auto-publishes if confidence and inputs pass. Tier 2 requires contractor/inspector. Tier 3 requires MFA-authenticated qualified human. Tier 4 requires licensed professional. Finding schema mandates `risk_tier`, `required_reviewer_role`, `release_restriction`.
**Consequences**: Operating cost scales sensibly. High-consequence findings still receive expert sign-off. Every publisher (Passport append, report render, Habitat sync) checks tier before releasing.

---

## ADR-006 · Public Passport Access Is Not Hash-Based
**Status**: Accepted (v1.1)
**Context**: A permanent hash is not a bearer credential. Anonymous read access via hash-only leaks all passport data to anyone who ever received the URL.
**Decision**: Public access requires expiring signed links + scoped audience projection + revocation + access logging + rate limiting + optional recipient binding. Separate projections per audience (public / homeowner / contractor / adjuster / insurer).
**Consequences**: Existing `/passport/:hash` route must be re-routed through a signed-link factory during Phase 1a-2 migration. Homeowner-share, contractor-share, and adjuster-share flows all mint scoped links rather than exposing the hash.

---

## ADR-007 · Optimistic Concurrency with Explicit Rebase
**Status**: Accepted (v1.1)
**Context**: "First-writer-wins" language implies silent data loss for the losing submission.
**Decision**: Optimistic concurrency with 7-step rebase workflow. Losing submissions preserved in `passport_sync_log`, automatically rebased when non-conflicting, routed to Human QA queue when materially conflicting. Never silently discarded.
**Consequences**: Cosign receipt scheme unchanged. `409 SEQUENCE_CONFLICT` still returned to client, but with a rebase-attempt link + queue routing on materially conflicting content.

---

## ADR-008 · Layered Digital Twin Package
**Status**: Accepted (v1.1)
**Context**: A single glTF cannot be both a scientifically valid measurement record and an optimized mobile presentation.
**Decision**: Four canonical layers: Evidence (originals + reconstruction report), Measurement (validated surfaces + tolerances), Presentation (compressed glTF/KTX2 for mobile), Interchange (IFC/DXF/PLY/LAS/LAZ/E57/GeoTIFF only where source supports).
**Consequences**: Presentation optimization can never alter the measurement record. IFC/DXF exports are provably restricted to observed geometry — no invented concealed framing.

---

## ADR-009 · Durable Delivery for Critical Events
**Status**: Accepted (v1.1)
**Context**: FastAPI background tasks lose work on process restart, deploy, or worker failure. Passport and Habitat delivery are business-critical.
**Decision**: Transactional outbox + durable jobs collection with locking and idempotent retries for the critical event set. In-process background tasks retained only for non-critical (UI notifications, cache warming). No external broker required in Phase 1.
**Consequences**: Approved findings pending Passport append, passport-to-Habitat handoffs, and evidence-package finalization survive deployment. External broker (NATS/Redis Streams) may be introduced in Phase 2+ if cross-service messaging demands it — not before.

---

## ADR-010 · Validation Program Precedes Marketing Language
**Status**: Accepted (v1.1)
**Context**: Marketing phrases like "engineering-grade" or "insurance-grade accuracy" without empirical validation are legally and ethically indefensible.
**Decision**: Formal field-validation program (15 dimensions) defined before any external claim of accuracy. Truth Score displayed only in 10-point bands until calibrated. Product copy uses "Prototype scoring — not calibrated to industry standard yet" during pre-validation.
**Consequences**: Marketing team receives a documented gate. Any external claim of accuracy is tied to a specific validation report by version. Insurance carriers can request the validation report before granting evidentiary weight to Stratex outputs.

---

## Meta-ADR · Documentation-Only Discipline
**Status**: Accepted throughout v1.1 revision pass
**Decision**: No implementation code was written during the v1.1 revision. No production deploy occurred. All v1.0 artifacts preserved read-only at `/app/memory/_v1.0_PRESERVED_*`.
**Consequences**: Reversibility is absolute. If v1.1 is rejected, v1.0 is untouched and can resume as the reference document.

---

# ADRs ADDED IN v1.2

## ADR-011 · Fifteen-stage Workflow Enumeration
**Status**: Accepted (v1.2)
**Context**: v1.0 and v1.1 loosely referenced a "14-stage" workflow while enumerating 15 stages in the chain.
**Decision**: Standardize on 15 stages. Every reference explicitly enumerates them. §22 workflow verification report cross-lists producer + consumer per stage.
**Consequences**: Downstream module counts, workflow diagrams, dashboard progress indicators, and event log producers all reference 15 stages.

## ADR-012 · Property Lifecycle Operations
**Status**: Accepted (v1.2)
**Context**: Merge, split, identity-link, identity-unlink, and ownership-transfer were undefined operations, creating risk of silent data corruption.
**Decision**: Five first-class audited operations (§11.3) with explicit ledger event types, authorization tiers, and invariants. No operation destroys prior history.
**Consequences**: Human QA queue receives merge/split events at Tier 3. Ownership transfer is Tier 2 with MFA + Habitat notification. Reversibility within a documented rollback window.

## ADR-013 · Tier 3 / Tier 4 Boundary Rule
**Status**: Accepted (v1.2)
**Context**: v1.1 listed "structural concerns" and "engineering deviations" in both Tier 3 and Tier 4, creating routing ambiguity.
**Decision**: Tier 4 has exclusive authority over structure, code compliance, and engineering deviations. Tier 3 handles high-consequence non-structural findings only. Explicit escalation rule enshrined in §10.
**Consequences**: Human QA router has an unambiguous rule. No finding can be silently signed off at Tier 3 when it touches structure.

## ADR-014 · AWE Index™ Release-State Gate
**Status**: Accepted (v1.2)
**Context**: Displaying a composite AWE Index™ before validation risks premature external claims.
**Decision**: Five release states with published transition requirements (§17.1). The Index is never rendered without its current release-state chip.
**Consequences**: Marketing team, contractor UI, and Passport payload each read the release state before rendering the Index. Transitions require published validation report + Executive Architect sign-off.

## ADR-015 · Phase 1a-Only Authorization Boundary
**Status**: Accepted (v1.2)
**Context**: v1.1 approval block risked being interpreted as authorizing all of Phase 1 sub-phases.
**Decision**: v1.2 approval authorizes **Phase 1a only**. Each subsequent sub-phase (1b, 1c, 1d) requires its own explicit executive authorization following review of the prior sub-phase's completion package (§20.2).
**Consequences**: Cannot accidentally slide into shell scaffolding, workspace stubs, or screenshot packaging without additional approval gates. Prevents scope creep by construction.
