# EXPLANATION REVIEW WORKBENCH
## CENTCOM DIRECTIVE 016 · OPERATION EXPLAINER VALIDATION™ (v1.0)
**Prepared by:** General Atlas & The Stratex-2 Executive Committee  
**Status:** APPROVED / OPERATIONAL  
**Classification:** CORE + PROPERTY PASSPORT (EXECUTIVE PRIORITY)  

---

## 1. Scope & Purpose of the Human-in-the-Loop Gate

No explanation shall project to public audiences without passing the human-in-the-loop review queue. The **Explanation Review Workbench** provides certified Stratex reviewers (CEOs, GMs, and Senior Engineers) with a secure workspace to audit, edit, and approve dynamic explanations.

The primary safety gate is: **A reviewer may correct or reject conclusions. A reviewer may not silently remove evidence, unknowns, conflicts, or provenance.**

---

## 2. Reviewer Experience & Functional Workflows

The Workbench interface is divided into 5 interactive control cards:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      HUMAN REVIEW WORKBENCH SCREEN                     │
├───────────────────────────────────┬────────────────────────────────────┤
│ 1. Evidence Compare Card          │ 2. Confidence & Conflict Card      │
│ - View raw images/sensors side-by-│ - View formula variables & weights │
│   side with generated conclusion. │ - Detail active conflict multipliers│
├───────────────────────────────────┼────────────────────────────────────┤
│ 3. Text Editing Card              │ 4. History Diffs Card              │
│ - Edit allowed human-language     │ - Side-by-side comparison of active│
│   fields only (e.g. Next Steps).  │   draft vs previous versions.      │
├───────────────────────────────────┴────────────────────────────────────┤
│ 5. Action Control Deck                                                 │
│ - [APPROVE]  - [REJECT]  - [REQUEST REGENERATION]  - [OVERRIDE RATIONALE]│
└────────────────────────────────────────────────────────────────────────┘
```

### A. Comparing Conclusion to Evidence
*   *Workflow:* The screen renders the generated explanation on the left, and lists the direct supporting evidence (original photos, sensor logs, and Passport Entries) on the right.
*   *Safety Check:* Reviewers can click any element in the "Evidence Trace" to instantly highlight and load the corresponding source asset, verifying that the text is grounded in physical fact.

### B. Reviewing Confidence Factors
*   *Workflow:* Displays the raw inputs of the confidence formula: $R_s$, $D_t$, $F_c$, and $W_c$.
*   *Safety Check:* If the system applied a temporal decay or conflict penalty, the exact calculation details are displayed in a transparent breakdown table.

### C. Viewing Active Conflicts
*   *Workflow:* If a conflict is detected ($F_c < 1.00$), the screen displays the conflicting evidence items side-by-side (e.g. resident report vs inspector photo).
*   *Safety Check:* Reviewers must either accept the conflict (leaving the penalty active) or resolve it by choosing the authoritative source and recording an override rationale.

### D. Editing Permitted Fields
*   *Workflow:* Reviewers can edit permitted human-language fields (such as "Next Steps" or "Tone Polish") directly inside textareas.
*   *Safety Check:* Form validation blocks any attempt to edit or delete the immutable elements of the explanation:
    - The raw evidence list
    - The overall confidence percentage
    - The identified unknowns or conflicts
    - The cryptographic signature of the trace

### E. Actions Deck: Reject, Regenerate, Approve
*   *Reject:* Rejects the explanation, marking its status as `Validation Failed` and moving it out of the active queue.
*   *Request Regeneration:* Triggers a background job to regenerate the explanation using a fresh prompt run, retaining the same inputs.
*   *Approve:* Changes the status to `Approved` and triggers the cryptographic signing chain, prepending the reviewer's identity and timestamp.

---

## 3. Override Rationale & Audit Enforcement

No human override is permitted without an identity, timestamp, reason, and an immutable audit event.

When a reviewer overrides a conclusion or rating, the workbench enforces the completion of a **Manual Override Block**:

```json
{
  "override_block": {
    "reviewer_id": "usr_atlas_001",
    "timestamp": "2026-07-21T12:00:00Z",
    "rationale": "Upgraded shingle rating from POOR to FAIR based on completed physical mastic seal repair, verified on msn_1091.",
    "audit_hash_chain": "7c88b90aef902bcd89ffde012abcefeef8bc0128acbde120abcefeef12034eab"
  }
}
```

This block is merged into the explanation document and committed to the MongoDB database. Simultaneously, an event is emitted to the nextgen outbox, publishing to the audit ledger. Any attempt to modify or delete a historical override record results in cryptographic trace failure, locking the property file.
