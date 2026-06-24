"""STRATEX™ — Expert Agent Dispatcher

Implements the Phase 3 BIM/Quantification dispatcher pattern.

The dispatcher is the architectural backbone of the analysis pipeline:
  1. GEOMETRY_AGENT  — surface areas (wall/roof) minus fenestration
  2. MATERIAL_AGENT  — siding + accessories (J-channel, starter, soffit/fascia, gutters)
  3. THERMAL_AGENT   — saturation + Probability-of-Damage correlation
  4. ENERGY_AGENT    — air leakage / BTU loss behind windows/doors/walls
  5. BIM_RENDER_AGENT— 3-layer digital twin renderer (Finish / Vapor / Framing)

In demo mode the actual analysis runs through Gemini multi-agent prompts
(see routes/demo_scan.py); this module records the manifest and provides
the canonical agent registry that the rest of the system depends on.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StratexProjectManager")

MANIFEST_DIR = Path("/app/backend/data/manifests")
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

EXPERT_CHAIN = [
    {"id": "GEOMETRY_AGENT", "desc": "Wall + Roof surface areas minus fenestration"},
    {"id": "MATERIAL_AGENT", "desc": "Multi-material siding & accessory BOM"},
    {"id": "THERMAL_AGENT",  "desc": "Saturation + Probability-of-Damage correlation"},
    {"id": "ENERGY_AGENT",   "desc": "BTU loss / air-leakage modeling"},
    {"id": "BIM_RENDER_AGENT","desc": "Finish / Vapor / Framing digital-twin renderer"},
]


def dispatch_to_experts(scan_id: str, raw_data_path: Optional[Path] = None) -> dict:
    """Record an analysis manifest noting which experts were assigned.

    Returns the manifest dict so the calling route can include it in the
    response payload.
    """
    logger.info("🚀 Project Manager: BIM/Quantification initiated for %s", scan_id)
    for agent in EXPERT_CHAIN:
        logger.info("👉 Delegating to: %s — %s", agent["id"], agent["desc"])

    manifest = {
        "scan_id": scan_id,
        "raw_data_path": str(raw_data_path) if raw_data_path else None,
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "status": "IN_PROGRESS",
        "experts_assigned": [a["id"] for a in EXPERT_CHAIN],
        "agent_registry": EXPERT_CHAIN,
    }

    out_path = MANIFEST_DIR / f"{scan_id}_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2))
    logger.info("✅ Manifest saved: %s", out_path.name)
    return manifest


def parse_diagnostic_file(file_path: Path) -> dict:
    """Trigger point for the data/diagnostics file-watcher."""
    return dispatch_to_experts(file_path.stem, file_path)
