# regional_switchboard.py
# -----------------------------------------------------------------------------
# STRATEX™ Regional Switchboard — verbatim user spec.
# National multi-store rollup engine. Pinned local state first, then alphabetical
# states. Per-store ROI saturation calculated from fleet unit scan totals.
# Pure addition (preservation lock); no existing files modified.
# -----------------------------------------------------------------------------
from __future__ import annotations
from typing import Dict, Any, List

from fleet_telemetry import FleetStateNode


class RegionalSwitchboard:
    """Applies a strict regional sorting layout, placing the local store context first."""
    def __init__(self):
        self.regional_mesh: Dict[str, Dict[str, List[FleetStateNode]]] = {}

    def get_sorted_jurisdictions(self, local_state_override: str) -> List[str]:
        all_states = list(self.regional_mesh.keys())
        all_states.sort()
        if local_state_override in all_states:
            all_states.remove(local_state_override)
            return [local_state_override] + all_states
        return all_states

    def aggregate_store_metrics(self, state: str, city: str, store_id: str) -> Dict[str, Any]:
        nodes = self.regional_mesh.get(state, {}).get(f"{city}_{store_id}", [])
        total_scans = sum(n.lifetime_scans for n in nodes)
        # Sponsoring store pricing metrics: $1500 license baseline + $200 individual scan cost allocation
        operational_cost = 1500 + (total_scans * 200)
        simulated_sales = total_scans * 18410

        return {
            "combined_units": len(nodes),
            "accumulated_scans": total_scans,
            "gross_pipeline_sales": simulated_sales,
            "operational_expense_cost": operational_cost,
            "roi_target_saturation_met": simulated_sales >= 110000,
        }


# Process-local singleton — same pattern as fleet_telemetry.REGISTRY
SWITCHBOARD = RegionalSwitchboard()


def seed_regional_demo() -> Dict[str, Any]:
    """Idempotent: hydrate the switchboard with 4 states · 9 stores · 22 units.

    Lifetime-scan tuning ensures some stores cross the $110k gross-pipeline
    ROI saturation threshold (need ≥ 6 scans @ $18,410/scan) while others
    sit just under it — gives the dashboard a mixed green/amber distribution.
    """
    if SWITCHBOARD.regional_mesh:
        return {"seeded": False, "states": len(SWITCHBOARD.regional_mesh)}

    seeds = {
        "KY": {
            "Lexington_KY-FLAGSHIP": [
                ("Alpha-08", "Christy Cross", 27),
                ("Bravo-04", "Ramon Field", 14),
                ("Charlie-11", "Sasha Cole", 9),
            ],
            "Louisville_KY-002": [
                ("Delta-02", "Hank Reyes", 7),
                ("Echo-05", "Mira Vega", 4),
            ],
            "BowlingGreen_KY-003": [
                ("Foxtrot-01", "Jordan Marsh", 3),
            ],
        },
        "OH": {
            "Cincinnati_OH-101": [
                ("Golf-07", "Priya Naidu", 11),
                ("Hotel-02", "Devon Black", 6),
            ],
            "Columbus_OH-102": [
                ("India-09", "Lena Park", 5),
                ("Juliet-03", "Marcus Webb", 2),
            ],
        },
        "TN": {
            "Nashville_TN-201": [
                ("Kilo-12", "Wendy Cho", 8),
                ("Lima-06", "Owen Doss", 6),
            ],
            "Knoxville_TN-202": [
                ("Mike-04", "Tessa Quinn", 3),
            ],
        },
        "IN": {
            "Indianapolis_IN-301": [
                ("November-10", "Casey Lin", 12),
                ("Oscar-08", "Diego Faro", 4),
            ],
        },
    }
    for state, stores in seeds.items():
        SWITCHBOARD.regional_mesh.setdefault(state, {})
        for store_key, units in stores.items():
            nodes = []
            for uid, pilot, scans in units:
                n = FleetStateNode(uid, pilot)
                n.lifetime_scans = scans
                nodes.append(n)
            SWITCHBOARD.regional_mesh[state][store_key] = nodes
    return {"seeded": True, "states": len(SWITCHBOARD.regional_mesh)}
