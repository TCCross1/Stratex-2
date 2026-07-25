# CONFIDENCE EXPLANATIONS SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 013 · OPERATION INTELLIGENCE EXPLAINER
**Status:** SPEC COMPLETE · STANDARDIZED  
**Scope:** Confidence calculations, mathematical models, reliability weights, and natural language translation guidelines.

---

## 1. Core Philosophy of Confidence Transparency

A major pitfall of traditional AI engines is the output of arbitrary confidence numbers (e.g., "Confidence: 87%") without any explanation of how that number was reached. To earn and maintain trust, the Stratex-2 Explainer Engine enforces a strict law: **No score without provenance; no confidence rating without a clear, natural-language explanation of its factors.**

Confidence is not an arbitrary rating. It is a dynamic, mathematically rigorous reflection of:
*   **The Reliability of the Source:** Who or what gathered the data.
*   **The Freshness of the Data:** How long ago the observation was made.
*   **The Presence of Conflicting Evidence:** Whether different data sources agree.
*   **The Completeness of Coverage:** Whether we have inspected the entire system or only a small part of it.

---

## 2. Mathematical Confidence Model

The overall confidence score ($C$) for any building system or domain explanation is computed via a multi-variate product-sum formulation:

$$C = R_s \times D_t \times F_c \times W_c \times 100$$

Where:
*   $R_s$ is the **Base Source Reliability** coefficient.
*   $D_t$ is the **Temporal Decay** factor.
*   $F_c$ is the **Evidence Conflict** multiplier.
*   $W_c$ is the **System Coverage** weight.

---

### Key Variables & Weights

#### A. Base Source Reliability ($R_s$)
Different evidence collection methods possess different degrees of technical reliability. The ecosystem recognizes five distinct categories:

| Source Type | Base Reliability ($R_s$) | Description |
| :--- | :--- | :--- |
| **Certified Inspector / Engineer** | `1.00` | In-person physical assessment, core drilling, or certified contractor receipt with closeout QA. |
| **Calibrated Telemetric Sensor** | `0.95` | On-site, calibrated, self-testing hardware nodes (e.g., pin moisture sensors, electric CT clamps). |
| **High-Res Vision / Thermal UAV** | `0.85` | Drone imagery, infrared scans, photogrammetric spatial reconstructions. |
| **Self-Reported / Homeowner** | `0.40` | Manual input, unverified photo uploads, resident notes. |
| **Missing / Unverified Data** | `0.00` | Zero physical evidence recorded. **Requires fallback to UNKNOWN state.** |

#### B. Temporal Decay ($D_t$)
As building systems age, the value of past inspections decays. This decay is calculated using an exponential decay function:

$$D_t = e^{-\lambda \cdot t}$$

Where:
*   $t$ is the age of the evidence in days.
*   $\lambda$ is the decay constant, determined by the building system's expected rate of physical change:
    *   *Fast-Changing Systems (Water Intrusion, HVAC):* $\lambda = 0.0038$ (reaches $50\%$ decay in ~180 days).
    *   *Medium-Changing Systems (Roof, Windows):* $\lambda = 0.00095$ (reaches $50\%$ decay in ~2 years / 730 days).
    *   *Slow-Changing Systems (Foundation, Electrical Panel):* $\lambda = 0.00038$ (reaches $50\%$ decay in ~5 years / 1825 days).

#### C. Evidence Conflict Multiplier ($F_c$)
If multiple sources of evidence are associated with the same building system, the system checks for consistency.
*   **Consensus State ($F_c = 1.00$):** All sources agree on the system's condition (e.g., both thermal and moisture sensors indicate dry attic rafter state).
*   **Minor Conflict ($F_c = 0.85$):** Small variance in readings (e.g., moisture sensor reads 15% dampness but contractor notes state "dry").
*   **Major Conflict ($F_c = 0.50$):** Contradictory inputs (e.g., homeowner reports "No roof leaks," but active moisture sensors trigger 24% saturation alerts).

#### D. System Coverage Weight ($W_c$)
Measures what fraction of the physical system was actually inspected.
*   **Complete Scan ($W_c = 1.00$):** $100\%$ coverage (e.g., complete drone scan of all roof slopes).
*   **Representative Sample ($W_c = 0.80$):** Spot-checks performed across key sections (e.g., checking 4 out of 10 windows).
*   **Partial Scan ($W_c = 0.50$):** Opaque, obstructed, or highly localized check (e.g., viewing only the front slope of a roof from the ground).

---

## 3. Confidence Mapping & Certainty Levels

The resulting percentage score is mapped to one of three **Certainty Levels**. This level dictates how the explanation is presented to the user, ensuring absolute transparency.

```
┌─────────────────────────────────────────────────────────────┐
│                       CONFIDENCE BANDS                      │
├─────────────────┬─────────────────┬─────────────────────────┤
│ Score Range     │ Certainty Level │ Presentation Rule       │
├─────────────────┼─────────────────┼─────────────────────────┤
│ 80% to 100%     │ HIGH            │ Display with Green badge│
│ 50% to 79%      │ MEDIUM          │ Display with Amber badge│
│ 0% to 49%       │ LOW             │ Display with Red badge  │
└─────────────────┴─────────────────┴─────────────────────────┘
```

*   **HIGH (80% - 100%):**
    *   *Meaning:* The assessment is backed by fresh, high-reliability evidence (inspectors or calibrated sensors) with complete system coverage and zero conflicts.
*   **MEDIUM (50% - 79%):**
    *   *Meaning:* The assessment is generally reliable but relies on older data (mild temporal decay), partial coverage, or lower-weight sources (e.g. self-reported data).
*   **LOW (0% - 49%):**
    *   *Meaning:* The assessment is speculative. It is driven by heavily decayed data, majorly conflicting evidence, or unverified self-reporting. **Users are explicitly warned of potential inaccuracies, and scheduling an inspection is recommended.**

---

## 4. Guidelines for Writing Natural-Language Confidence Explanations

The AI Reasoning Engine must never output a confidence score without writing a corresponding, natural-language explanation. The text must explain the exact mathematical inputs and decay states in a clear, narrative style.

### Standard Phrasing Blueprints

#### 1. High Confidence Phrasing
*   *Blueprint:* "Our confidence is High ({score}%) because this assessment is based on a fresh {source_type} conducted on {date}, which covered {coverage} of the system and matches our active {sensor/photo} data."
*   *Example:* "Our confidence is High (95%) because this assessment is based on a fresh professional roof inspection conducted on 2026-07-20, which covered 100% of the slopes and matches our active aerial drone photography taken yesterday."

#### 2. Medium Confidence Phrasing
*   *Blueprint:* "Our confidence is Medium ({score}%) because although we have {source_type} verifying the condition, the data is {age} days old and has decayed. Additionally, we only have {coverage} of the system scanned."
*   *Example:* "Our confidence is Medium (68%) because although we have certified contractor receipts verifying the HVAC installation, the records are now 520 days old. Additionally, we only have a partial scan of the indoor ductwork."

#### 3. Low Confidence Phrasing
*   *Blueprint:* "Our confidence is Low ({score}%) because we are relying on {source_type} data which has not been verified by a certified field agent. Furthermore, there is an active conflict between {source_A} and {source_B}."
*   *Example:* "Our confidence is Low (35%) because we are relying on self-reported homeowner notes which have not been verified by a certified field agent. Furthermore, there is an active conflict between the homeowner notes ('no leaks') and our dampness sensor, which has triggered moisture warnings."

---

## 5. Implementation Validation Rules

The Explainer Engine's test suite enforces the following validation checks to guarantee compliance with confidence writing standards:

1.  **Strict Boundary Matching:** A computed score of `92.5%` must select a `HIGH` certainty badge. Setting a `92.5%` score with a `MEDIUM` or `LOW` certainty badge triggers a JSON schema validation error.
2.  **Explicit Ingredient Mention:** The natural-language explanation MUST contain the words or direct references to the primary factors contributing to the score reduction (e.g., if the score is under 80% due to age, the text must specify that the data is old/decayed).
3.  **Automatic Action Binds:** Any explanation with a `LOW` confidence rating must automatically include "Schedule a certified field verification mission" as the very first item in the `Recommended Next Steps` array.
