# STRATEX™ Trifecta Verification Stack · Permanent Architectural Spec

> Locked by founder directive (2026-06-01). Every data point that is destined
> for a dashboard, a PDF, a DB write, or a downstream economic decision MUST
> pass through this gauntlet. No exceptions.

---

## 1. Mission

Make STRATEX data **factually accurate, semantically correctly placed, and
adversarially verified** before it touches user-facing surfaces. Eliminate
hallucinations and silent off-by-one errors by forcing three independent
LLMs from three different providers to compete and agree.

---

## 2. Three-Panel Architecture

```
                ┌──────────────────────────┐
   INGEST  ──▶  │  PANEL A · ARCHITECTS    │  (build proposal)
                │  4 specialist roles      │
                └────────┬─────────────────┘
                         │ proposal_A
                         ▼
                ┌──────────────────────────┐
                │  PANEL B · SKEPTICS      │  (adversarial review)
                │  4 mirror specialists    │
                │  (different LLM)         │
                └────────┬─────────────────┘
                         │ critique_B + corrected_B
                         ▼
                ┌──────────────────────────┐
                │  PANEL C · TRIBUNAL      │  (3 judges, must 2-of-3)
                │  3 independent judges    │
                └────────┬─────────────────┘
                         │
                   ACCEPT │ REJECT
                         ▼
                   write → render
```

---

## 3. Provider Diversity Mandate

Each panelist uses a DIFFERENT provider for the same domain so they cannot
share blind spots:

| Specialist domain | Panel A (Architect) | Panel B (Skeptic) | Panel C judge slot |
|---|---|---|---|
| Materials-Brain   | Claude Sonnet 4.6 | GPT-5.4            | Gemini 3.1 Pro |
| Geometry-Brain    | GPT-5.4           | Gemini 3.1 Pro     | Claude Sonnet 4.6 |
| Anomaly-Brain     | Gemini 3.1 Pro    | Claude Sonnet 4.6  | GPT-5.4 |
| Pricing-Brain     | Claude Sonnet 4.6 | GPT-5.4            | Gemini 3.1 Pro |

Models accessed via `emergentintegrations.llm.chat.LlmChat` using the
universal `EMERGENT_LLM_KEY`.

---

## 4. Round Budget

- Per-LLM timeout: **12s**
- Total orchestration budget: **25s**
- Max LLM calls per round: **3 (Panel A) + 3 (Panel B) + 3 (Panel C) = 9**
  (we drop the 4th specialist for MVP since 3 covers materials/anomaly/pricing
   and we can swap geometry in as we expand)
- Degraded mode: if 1 LLM fails per panel, continue with 2 and flag
  `degraded=true` on the verdict
- Hard reject: if 2+ LLMs fail in any single panel, fail-closed

---

## 5. Output Contract

```json
{
  "verdict": "ACCEPT" | "REJECT",
  "consensus_count": 0..3,
  "round_id": "uuid",
  "input_hash": "sha256(input)",
  "winning_panelist": "claude-sonnet-4-6 | gpt-5.4 | gemini-3.1-pro-preview",
  "panel_a": [{ "panelist": "...", "proposal": {...}, "score": 0..100 }],
  "panel_b": [{ "panelist": "...", "critique": "...", "corrected": {...}, "score": 0..100 }],
  "panel_c": [{ "panelist": "...", "verdict": "ACCEPT" | "REJECT", "reasoning": "..." }],
  "accepted_payload": {...},     // present only when verdict=ACCEPT
  "dissent_notes": [...],
  "degraded": false,
  "elapsed_ms": 18450,
  "created_at_iso": "..."
}
```

---

## 6. Scoreboard

`db.trifecta_scoreboard` accumulates per-panelist:
- `wins`: times this panelist's output was promoted
- `losses`: times the OTHER panel rebutted this panelist
- `draws`: 2-of-3 with this panelist on losing side but no error found
- `accuracy_pct`: rolling 30-day
- `avg_latency_ms`: per-call median
- `last_dispute_id`: link to the most recent round they were in

Surface: `/ceo/tribunal` page + dock tile + CEO Command Center side widget.

---

## 7. Endpoints

- `POST /api/trifecta/verify` — body: `{ domain, payload }` → full output contract
- `GET  /api/trifecta/scoreboard` — leaderboard
- `GET  /api/trifecta/round/{round_id}` — full transcript (audit)
- `GET  /api/trifecta/stream/{round_id}` — SSE live deliberation feed for the
  Tribunal Theater UI (Phase 3)

---

## 8. First Wired Flow (Phase 2)

**Anomaly tiering.** When `routes/anomaly_estimator.py` returns a Yellow/Orange/Red
verdict + cost projection, the result passes through `trifecta/verify` with
`domain="anomaly"` BEFORE landing on the contractor deliverable PDF. If
REJECT, escalate to `db.anomaly_human_queue` and display a "Tribunal Hold"
banner in the deliverable instead of the data.

---

## 9. Roll-out Plan

| Phase | Scope | Status |
|---|---|---|
| 1 | Spec + backend skeleton + scoreboard schema | ✅ documented here |
| 2 | Anomaly domain wired through Trifecta | ⏳ next turn |
| 3 | Materials pricing + geofence breach wired through | backlog |
| 4 | SSE live deliberation stream + Tribunal Theater UI | backlog |
| 5 | Auto-tuning prompts based on scoreboard losses | backlog |
