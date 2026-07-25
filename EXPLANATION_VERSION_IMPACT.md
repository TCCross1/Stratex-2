# EXPLANATION VERSION IMPACT
## CENTCOM DIRECTIVE 016 · OPERATION EXPLAINER VALIDATION™ (v1.0)
**Prepared by:** General Atlas & The Stratex-2 Executive Committee  
**Status:** APPROVED / OPERATIONAL  
**Classification:** CORE + PROPERTY PASSPORT (EXECUTIVE PRIORITY)  

---

## 1. Principles of Version & Impact Integrity

As physical conditions, expert reviews, and building standards evolve, the data driving our property assessments changes. 

The **Explanation Version Impact Plan** establishes how the system manages updates without corrupting canonical history.

All historical explanations must be **preserved immutably**. The system must identify the active version while determining the impact of changes on existing generated explanations.

---

## 2. Version State Classifications

When upstream evidence or canonical intelligence changes, the Explainer Engine evaluates existing explanations and assigns one of five impact states:

```
  UPSTREAM CHANGE EVENT ──► [Impact Evaluator] ──► DETERMINES STATE:
                                  │
      ┌───────────────────┬───────┴───────────┬───────────────────┐
      ▼                   ▼                   ▼                   ▼
[ Still Current ]   [ Superseded ]     [ Partially Stale ]  [ Invalidated ]
- No impact         - Outdated by      - Older evidence     - Vital proof is
- Match active      - newer approved   - decayed, must      - revoked/deleted;
- metadata          - finding          - run recalculation  - fallback to UNKNOWN
```

1.  **Still Current:** No upstream changes have occurred. The explanation metadata aligns with the active Property DNA, Knowledge Graph, and Passport ledger.
2.  **Superseded:** A newer approved finding has been published for this system, rendering the older explanation outdated.
3.  **Partially Stale:** The underlying evidence has decayed slightly (temporal decay), or non-critical related systems have changed. The explanation is still readable but is flagged for automatic, low-priority regeneration.
4.  **Invalidated:** Vital supporting evidence was revoked, or a critical data error was corrected. The explanation can no longer be used or projected; it falls back immediately to an unverified `UNKNOWN` state.
5.  **Requiring Regeneration:** Critical changes to the confidence formula weights, or a direct manual reviewer override, require immediate compilation of a new version.

---

## 3. Impact Assessment Test Suites

The test harness must validate version transitions across 9 upstream change scenarios:

### A. Evidence Approval
*   *Test Path:* A new, certified drone flight is approved and added to the `findings` collection.
*   *System Impact:* The existing explanation's state transitions to **Superseded**. The engine queues a background worker to compile a new explanation version incorporating the fresh evidence.

### B. Evidence Revocation
*   *Test Path:* A reviewer marks a previously-used image as `revoked` due to calibration error.
*   *System Impact:* The active explanation is immediately marked as **Invalidated**. The system falls back to `UNKNOWN` health until a new explanation compiles excluding the revoked file.

### C. Finding Amendment
*   *Test Path:* An inspector edits an active finding's description (e.g. changing 5 shingles to 15).
*   *System Impact:* The active explanation transitions to **Requiring Regeneration**. The system must maintain the old version in the history but mark the current projection version as pending.

### D. Passport Correction
*   *Test Path:* An administrative correction is made to the Passport ledger (e.g. correcting a physical address or transaction sequence).
*   *System Impact:* The engine checks if the correction affects core variables. If yes, it transitions the state to **Requiring Regeneration**.

### E. DNA Refresh
*   *Test Path:* The Property DNA Engine pushes a new, updated summary node.
*   *System Impact:* The active explanation’s metadata block is compared to the new DNA version. If a mismatch exists in referenced fields, the state transitions to **Partially Stale**.

### F. Graph-Edge Rollback
*   *Test Path:* A relationship edge between systems is deleted or rolled back in the Knowledge Graph.
*   *System Impact:* The engine re-traverses the path. If the active trace path is broken, the explanation transitions to **Invalidated**.

### G. Standard Update
*   *Test Path:* An engineering standard is updated (e.g., ASCE 7-22 is replaced by ASCE 7-28).
*   *System Impact:* The template registry triggers a state change to **Partially Stale** for all explanations referencing that code, indicating that a recalculation is required.

### H. Confidence-Model Update
*   *Test Path:* The system updates a temporal decay constant $\lambda$ or weight variable in the confidence model.
*   *System Impact:* All active explanations are marked as **Partially Stale**. A system-wide batch regeneration is scheduled.

### I. Reviewer Override
*   *Test Path:* A certified reviewer manually inputs an override on a system category rating.
*   *System Impact:* The automated explanation is immediately marked as **Superseded**. The reviewer's manually-authored explanation becomes the active current projection.

---

## 4. Preservation of Historical Ledger

All historical explanations must remain preserved in the `intelligence_explanations` database with sequential version numbers (`version: 1`, `version: 2`, etc.).

The active projection API endpoint `/api/nextgen/v1/intelligence/active` must execute a query filtering by:
- `property_id`
- `system_category`
- `status: "PUBLISHED"`

It must return the document with the highest `version` integer, ensuring that clients always view the current active explanation while history remains intact for audit.
