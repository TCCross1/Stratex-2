# CONFIDENCE CALIBRATION PLAN
## CENTCOM DIRECTIVE 016 · OPERATION EXPLAINER VALIDATION™ (v1.0)
**Prepared by:** General Atlas & The Stratex-2 Executive Committee  
**Status:** APPROVED / OPERATIONAL  
**Classification:** CORE + PROPERTY PASSPORT (EXECUTIVE PRIORITY)  

---

## 1. Objectives of Confidence Calibration

Confidence value without reproducible factors is strictly prohibited. The Stratex-2 confidence model ensures that our users (homeowners, contractors, and insurers) are presented with mathematically defensible certainty indices. 

The **Confidence Calibration Plan** defines the program for isolating, testing, and jointly validating each factor within the canonical confidence formula:

$$C = R_s \times D_t \times F_c \times W_c \times 100$$

Where:
*   $R_s$ is the **Base Source Reliability** coefficient.
*   $D_t$ is the **Temporal Decay** factor.
*   $F_c$ is the **Evidence Conflict** multiplier.
*   $W_c$ is the **System Coverage** weight.

---

## 2. Independent Factor Validation

### A. Base Source Reliability ($R_s$)
We isolate $R_s$ by setting $D_t = 1.0$ (age $t = 0$ days), $F_c = 1.0$ (no conflicts), and $W_c = 1.0$ (complete scan). 

The test harness must verify that the base reliability values map exactly to the active authority of the ingestion source:

```
┌───────────────────────────────────────┬─────────┬──────────────────────────┐
│ Source Category                       │ Target  │ Margin of Error Allowed  │
├───────────────────────────────────────┼─────────┼──────────────────────────┤
│ Certified Inspector / Civil Engineer  │ R_s=1.00│ ±0.000 (Absolute)        │
│ Calibrated Telemetric Sensor          │ R_s=0.95│ ±0.000 (Absolute)        │
│ High-Resolution Vision / Thermal UAV  │ R_s=0.85│ ±0.000 (Absolute)        │
│ Manual Self-Reported / Resident Upload│ R_s=0.40│ ±0.000 (Absolute)        │
│ Missing / Unverified Data             │ R_s=0.00│ System fallback triggers │
└───────────────────────────────────────┴─────────┴──────────────────────────┘
```

*   **Test RS-1 (Inspector Rank):** Ensure that any finding authored by a certified inspector or licensed engineer receives $R_s = 1.00$.
*   **Test RS-2 (Sensor Quality):** Ensure that live IoT telemetry feeds, such as rafter moisture pins or electrical CT clamps, map to $R_s = 0.95$ when calibrated within tolerance.
*   **Test RS-3 (Missing Fallback):** When no evidence is present, $R_s$ must equal $0.00$. The engine must immediately transition the system health state to `UNKNOWN` and disable any score output.

### B. Temporal Decay ($D_t$)
We isolate $D_t$ by setting $R_s = 1.0$, $F_c = 1.0$, and $W_c = 1.0$. The temporal decay follows an exponential decay curve:

$$D_t = e^{-\lambda \cdot t}$$

Where $t$ is the elapsed age in days since the observation, and $\lambda$ is the domain-specific decay constant. The validation tests must verify decay calculations across all 12 domains, split into three decay speeds:

```
              TEMPORAL DECAY CURVE CHARACTERISTICS (By System Category)
  1.00 ┼─────────---───
       │              \───
  0.75 ┼                  \─── Slow Decay (Foundation / Electrical) [λ = 0.00038]
       │                      \─── Medium Decay (Roof / Windows) [λ = 0.00095]
  0.50 ┼                          \─── Fast Decay (Water / HVAC) [λ = 0.0038]
       │                              \───
  0.00 ┼───────────────────────────────────┴────────────────────────────►
       0 days                             1000 days                         2000 days
```

*   **Fast-Decaying Systems ($\lambda = 0.0038$):** Includes **Water Intrusion** and **HVAC**.
    *   *Half-life targets:* $t = 182$ days $\rightarrow$ $D_t \approx 0.50$.
    *   *Verification Points:*
        - At $t = 0$: $D_t = 1.00$.
        - At $t = 90$ days: $D_t \approx 0.71$.
        - At $t = 365$ days: $D_t \approx 0.25$.
*   **Medium-Decaying Systems ($\lambda = 0.00095$):** Includes **Roof**, **Windows**, **Plumbing**, **Energy Performance**, **Insurance Claims**, **Maintenance**, and **Project Opportunities**.
    *   *Half-life targets:* $t = 730$ days $\rightarrow$ $D_t \approx 0.50$.
    *   *Verification Points:*
        - At $t = 0$: $D_t = 1.00$.
        - At $t = 365$ days: $D_t \approx 0.71$.
        - At $t = 1000$ days: $D_t \approx 0.39$.
*   **Slow-Decaying Systems ($\lambda = 0.00038$):** Includes **Foundation**, **Electrical**, and **Thermal Findings** (structural anomalies).
    *   *Half-life targets:* $t = 1824$ days $\rightarrow$ $D_t \approx 0.50$.
    *   *Verification Points:*
        - At $t = 0$: $D_t = 1.00$.
        - At $t = 365$ days: $D_t \approx 0.87$.
        - At $t = 3650$ days (10 years): $D_t \approx 0.25$.

### C. Evidence Conflict Factor ($F_c$)
We isolate $F_c$ by setting $R_s = 1.0$, $D_t = 1.0$, and $W_c = 1.0$.

The conflict validator verifies that contradictions among multi-source evidence penalize total confidence correctly. We test 6 distinct conflict configurations:

1. **Direct Conflicts ($F_c = 0.50$):** Contradictory statements within the same component (e.g. Homeowner asserts "no basement water" vs Inspector logs "wet walls").
2. **Partial Conflicts ($F_c = 0.85$):** Small variance in measurements (e.g., thermal scan reports "mild attic drafts" but physical blower door measures "tight framing").
3. **Reviewer-Resolved Conflicts ($F_c = 1.00$):** If a certified reviewer reviews a conflict and submits a formal manual override resolution, the penalty must be removed ($F_c = 1.00$) and the resolution reason stored in the audit ledger.
4. **Different-Date Observations:** If a newer observation contradicts an older one, the system must NOT trigger a conflict penalty. Instead, the older observation's temporal decay must prevent conflict inflation, letting the fresh finding supersede the stale one.
5. **Different-Area Observations:** If defects are in different physical spaces (e.g., "shingle tear on north slope" and "pristine south slope"), the system must treat them as co-existing localized facts rather than a conflict ($F_c = 1.00$).
6. **Sensor-versus-Visual Conflicts ($F_c = 0.50$):** Active humidity sensors reporting 95% saturation while visual inspector logs note "dry cavity" must trigger a Major Conflict penalty ($F_c = 0.50$), prioritising sensor caution.

### D. System Coverage Weight ($W_c$)
We isolate $W_c$ by setting $R_s = 1.0$, $D_t = 1.0$, and $F_c = 1.0$.

System coverage represents the fraction of the physical system inspected:
- **Complete Scan ($W_c = 1.00$):** 100% envelope coverage (e.g. all 4 roof slopes).
- **Representative Sample ($W_c = 0.80$):** Standard statistical spot-checks (e.g. 5 out of 10 windows).
- **Partial Scan ($W_c = 0.50$):** Highly localized or obscured scans (e.g. checking only the crawlspace entryway).

*   **Localization Verification Rule:** Missing coverage must lower total confidence but **must not** invalidate or change supported localized facts. For example, a partial scan of the roof showing a localized shingle crack remains a high-confidence localized fact ($RF-02$), but the total roof system confidence drops to Amber/Medium.

---

## 3. Joint Multi-Factor Validation Scenarios

The test harness must execute joint multi-factor permutations to ensure that confidence ratings do not experience extreme mathematical outliers:

### Scenario J-01: Decayed, Low-Quality, Conflicting Spot Check
*   *Inputs:* Manual Homeowner Upload ($R_s = 0.40$), age $t = 365$ days on a Roof ($\lambda = 0.00095 \rightarrow D_t = 0.706$), major conflict with past inspection ($F_c = 0.50$), partial coverage ($W_c = 0.50$).
*   *Calculation:*
    $$C = 0.40 \times 0.706 \times 0.50 \times 0.50 \times 100 = 7.06\%$$
*   *Expected Classification:* `LOW` (Red Badge). Narrative must alert the user that the assessment is highly speculative, decayed, and unverified, recommending a certified inspector dispatch.

### Scenario J-02: Calibrated Sensor, Fresh, Complete, Consensual Feed
*   *Inputs:* Calibrated Moisture Sensor ($R_s = 0.95$), age $t = 2$ days on Water Intrusion ($\lambda = 0.0038 \rightarrow D_t = 0.992$), consensus ($F_c = 1.00$), complete scan ($W_c = 1.00$).
*   *Calculation:*
    $$C = 0.95 \times 0.992 \times 1.00 \times 1.00 \times 100 = 94.24\%$$
*   *Expected Classification:* `HIGH` (Green Badge).

---

## 4. Calibration Acceptance & Tuning Thresholds

```
┌─────────────────┬─────────────────┬────────────────────────────────────────┐
│ Confidence Band │ Certainty Level │ UI Presentation Mandates               │
├─────────────────┼─────────────────┼────────────────────────────────────────┤
│ 80% to 100%     │ HIGH (Green)    │ Approved for direct public projection. │
│ 50% to 79%      │ MEDIUM (Amber)  │ Render warning, suggest spot checks.   │
│ 0% to 49%       │ LOW (Red)       │ Explicit disclaimer, require inspector.│
└─────────────────┴─────────────────┴────────────────────────────────────────┘
```

The confidence weights and variables are locked in staging. If joint testing reveals that average certitudes across the golden corpus fall out of their assigned bands, the QA team may adjust the source weights or decay coefficients within a strict range of $\pm 0.05$, pending CEO approval.
