# fleet_telemetry.py
# -----------------------------------------------------------------------------
# STRATEX™ Fleet Telemetry — verbatim user spec, plus an in-memory
# FleetCommandRegistry singleton that holds the active swarm.
# Pure addition (preservation lock); no existing files modified.
# -----------------------------------------------------------------------------
from __future__ import annotations
from typing import Dict, Any, List, Optional


class FleetStateNode:
    """Manages tactical hardware diagnostic states and deployment variables."""
    def __init__(self, unit_id: str, pilot_name: str):
        self.unit_id = unit_id  # e.g. 'Alpha-08'
        self.pilot = pilot_name
        self.telemetry: Dict[str, Any] = {
            "charge_level": 100.0,
            "battery_charging": False,
            "starlink_active": True,
            "wifi_signal": "STRONG",
            "bluetooth_mesh": "CONNECTED",
            "hardware_nodes": "OPERABLE",
        }
        self.current_flight_phase = "LANDING"
        self.lifetime_scans = 0

    def sync_hardware_state(self, updates: Dict[str, Any]) -> None:
        self.telemetry.update(updates)

    def transition_phase(self, target_phase: str) -> None:
        valid_phases = [
            "TRANSIT_TO_JOB", "FLIGHT_ASSESSMENT", "LAUNCH_PROTOCOL",
            "IN_FLIGHT", "DATA_TRANSFER", "LANDING",
        ]
        if target_phase in valid_phases:
            self.current_flight_phase = target_phase

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "pilot": self.pilot,
            "telemetry": self.telemetry,
            "current_flight_phase": self.current_flight_phase,
            "lifetime_scans": self.lifetime_scans,
        }


class FleetCommandRegistry:
    """Process-local registry of all active drone units."""
    def __init__(self):
        self._units: Dict[str, FleetStateNode] = {}

    def ensure(self, unit_id: str, pilot_name: str) -> FleetStateNode:
        node = self._units.get(unit_id)
        if not node:
            node = FleetStateNode(unit_id, pilot_name)
            self._units[unit_id] = node
        return node

    def get(self, unit_id: str) -> Optional[FleetStateNode]:
        return self._units.get(unit_id)

    def all_units(self) -> List[FleetStateNode]:
        return list(self._units.values())

    def seed_demo(self) -> None:
        """Idempotent: spin up Christy Cross Alpha-08 + 3 supporting units."""
        if self._units:
            return
        seeds = [
            ("Alpha-08", "Christy Cross"),
            ("Bravo-04", "Ramon Field"),
            ("Charlie-11", "Sasha Cole"),
            ("Delta-02", "Hank Reyes"),
        ]
        for uid, pilot in seeds:
            n = FleetStateNode(uid, pilot)
            n.lifetime_scans = 27 if uid == "Alpha-08" else 14
            self._units[uid] = n


REGISTRY = FleetCommandRegistry()
