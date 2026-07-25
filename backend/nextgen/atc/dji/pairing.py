"""Visual / thermal pairing helpers for AWE packages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .interfaces import InventoryItem, PackageInventory


@dataclass
class PairingReport:
    ok: bool
    pairs: List[Tuple[str, str]] = field(default_factory=list)
    unpaired_visual: List[str] = field(default_factory=list)
    unpaired_thermal: List[str] = field(default_factory=list)
    notes: str = "Synthetic pairing — not a live registration claim"


def pair_visual_thermal(inventory: PackageInventory) -> PairingReport:
    """Pair RGB and radiometric thermal artifacts for AWE profiles.

    Mapping-only packages (no thermal) return ok=True with empty pairs —
    pairing is not required for geometry candidate paths.
    """
    visual = [
        i
        for i in inventory.items
        if i.category == "RGB_IMAGE" and i.present
    ]
    thermal = [
        i
        for i in inventory.items
        if i.category in {"THERMAL_RADIOMETRIC", "THERMAL_DERIVATIVE"} and i.present
    ]

    if not thermal:
        # Mapping packages do not require thermal pairing.
        return PairingReport(ok=True, pairs=[], unpaired_visual=[v.artifact_id for v in visual])

    pairs: List[Tuple[str, str]] = []
    used_thermal: set = set()
    unpaired_visual: List[str] = []

    # Prefer explicit paired_with links, else positional zip.
    thermal_by_id = {t.artifact_id: t for t in thermal}
    for v in visual:
        target = v.paired_with
        if target and target in thermal_by_id and target not in used_thermal:
            pairs.append((v.artifact_id, target))
            used_thermal.add(target)
        else:
            unpaired_visual.append(v.artifact_id)

    # Fill remaining by order
    remaining_thermal = [t for t in thermal if t.artifact_id not in used_thermal]
    still_unpaired: List[str] = []
    for vid in unpaired_visual:
        if remaining_thermal:
            t = remaining_thermal.pop(0)
            pairs.append((vid, t.artifact_id))
            used_thermal.add(t.artifact_id)
        else:
            still_unpaired.append(vid)

    unpaired_thermal = [t.artifact_id for t in thermal if t.artifact_id not in used_thermal]
    # AWE packages require at least one pair and no unpaired required thermals.
    ok = bool(pairs) and not unpaired_thermal
    return PairingReport(
        ok=ok,
        pairs=pairs,
        unpaired_visual=still_unpaired,
        unpaired_thermal=unpaired_thermal,
    )
