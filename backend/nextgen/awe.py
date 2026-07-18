"""AWE Composite Intelligence — deterministic scoring engine.

Directive 008 · first production calculation. Every rule documented; no
LLM or randomness. Consumes only approved (or passport_committed) PIOs.

Score model per category (Air / Water / Energy):

    start_score       = 100
    severity_penalty  = sum over PIOs where category impacted:
        - INFORMATIONAL:  1
        - MINOR:          4
        - MODERATE:      10
        - MAJOR:         22
        - CRITICAL:      40
    priority_weight   = {IMMEDIATE:1.20, URGENT:1.10, IMPORTANT:1.00,
                          SCHEDULE:0.85, MONITOR:0.65}
    penalty_i         = base_penalty * priority_weight
    score             = max(0, round(start_score - sum(penalty_i)))

Composite AWE Index = weighted mean(air, water, energy)  with weights
    {air: 0.30, water: 0.40, energy: 0.30}   # water carries more weight
                                              # because leaks compound.

Confidence: derived from AI confidences of contributing PIOs (mean) and
falls back to 100% if all PIOs are human-authored.

Evidence completeness: % of PIOs whose linked evidence items are all
finalized (i.e. part of a finalized mission package).

Release state (Blueprint §17.1) is *never* raised above INTERNAL_DRAFT
in Phase 1 field pilot output — externally-asserted display requires
the calibration program.
"""
from __future__ import annotations

from typing import Any, Dict, List


SEVERITY_PENALTY = {
    "INFORMATIONAL": 1,
    "MINOR": 4,
    "MODERATE": 10,
    "MAJOR": 22,
    "CRITICAL": 40,
}
PRIORITY_WEIGHT = {
    "IMMEDIATE": 1.20,
    "URGENT": 1.10,
    "IMPORTANT": 1.00,
    "SCHEDULE": 0.85,
    "MONITOR": 0.65,
}
COMPOSITE_WEIGHTS = {"air": 0.30, "water": 0.40, "energy": 0.30}


def _category_score(pios: List[Dict[str, Any]], category: str) -> Dict[str, Any]:
    penalty = 0.0
    contributing = 0
    for p in pios:
        if not (p.get("awe_impact") or {}).get(category):
            continue
        base = SEVERITY_PENALTY.get(p.get("severity"), 0)
        weight = PRIORITY_WEIGHT.get(p.get("priority"), 1.0)
        penalty += base * weight
        contributing += 1
    score = max(0, round(100 - penalty))
    return {"score": score, "contributing_pios": contributing}


def _confidence(pios: List[Dict[str, Any]]) -> float:
    ai = [p.get("ai_confidence_pct") for p in pios if p.get("ai_confidence_pct") is not None]
    if not ai:
        return 100.0
    return round(sum(ai) / len(ai), 1)


def compute_composite(
    approved_pios: List[Dict[str, Any]],
    finalized_evidence_ids: set,
) -> Dict[str, Any]:
    air = _category_score(approved_pios, "air")
    water = _category_score(approved_pios, "water")
    energy = _category_score(approved_pios, "energy")
    composite = round(
        air["score"] * COMPOSITE_WEIGHTS["air"]
        + water["score"] * COMPOSITE_WEIGHTS["water"]
        + energy["score"] * COMPOSITE_WEIGHTS["energy"]
    )
    total_pios = len(approved_pios)
    if total_pios == 0:
        completeness = 0
    else:
        with_evidence = sum(
            1 for p in approved_pios
            if p.get("evidence_ids")
            and all(e in finalized_evidence_ids for e in p["evidence_ids"])
        )
        completeness = round((with_evidence / total_pios) * 100)
    return {
        "air": air, "water": water, "energy": energy,
        "composite_index": composite,
        "release_state": "INTERNAL_DRAFT",  # Phase 1 gate (Blueprint §17.1)
        "confidence_pct": _confidence(approved_pios),
        "evidence_completeness_pct": completeness,
        "weights": COMPOSITE_WEIGHTS,
        "penalty_scale": SEVERITY_PENALTY,
        "priority_weight": PRIORITY_WEIGHT,
        "total_approved_pios": total_pios,
    }
