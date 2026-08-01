"""
ATC Readiness Gate — Field Test v1 (minimum viable)
Stratex Core

Performs the pre-flight readiness checks required before a mission
may advance to capture. This is the operational gate in front of
evidence ingest and sealing.

Does not launch drones. Does not write Passport.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    blocking: bool = True


@dataclass
class ReadinessReport:
    mission_id: str
    ready: bool
    checks: List[CheckResult] = field(default_factory=list)
    evaluated_at: str = ""
    blocking_failures: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "ready": self.ready,
            "evaluated_at": self.evaluated_at,
            "blocking_failures": self.blocking_failures,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "detail": c.detail,
                    "blocking": c.blocking,
                }
                for c in self.checks
            ],
        }


def evaluate_readiness(
    mission_id: str,
    *,
    weather_ok: bool = True,
    airspace_clear: bool = True,
    geofence_ok: bool = True,
    battery_pct: float = 100.0,
    sensor_status_ok: bool = True,
    storage_ok: bool = True,
    network_ok: bool = True,
    calibration_ok: bool = True,
    rtk_ready: bool = True,
    pilot_authorized: bool = True,
    equipment_health_ok: bool = True,
    mission_plan_present: bool = True,
) -> ReadinessReport:
    """
    Evaluate the minimum set of ATC readiness checks for Field Test v1.
    All listed checks are blocking by default.
    """
    checks: List[CheckResult] = [
        CheckResult("weather", weather_ok, "Within operational limits" if weather_ok else "Out of limits"),
        CheckResult("airspace", airspace_clear, "No active restrictions" if airspace_clear else "Restriction present"),
        CheckResult("geofence", geofence_ok, "Inside approved boundary" if geofence_ok else "Outside boundary"),
        CheckResult("battery", battery_pct >= 40.0, f"{battery_pct}%", blocking=True),
        CheckResult("sensors", sensor_status_ok, "All sensors nominal" if sensor_status_ok else "Sensor fault"),
        CheckResult("storage", storage_ok, "Sufficient free space" if storage_ok else "Storage low"),
        CheckResult("network", network_ok, "Link available" if network_ok else "No link"),
        CheckResult("calibration", calibration_ok, "Current" if calibration_ok else "Required"),
        CheckResult("rtk", rtk_ready, "FIXED or FLOAT acceptable" if rtk_ready else "RTK unavailable"),
        CheckResult("pilot_authorization", pilot_authorized, "Authorized" if pilot_authorized else "Not authorized"),
        CheckResult("equipment_health", equipment_health_ok, "Healthy" if equipment_health_ok else "Fault"),
        CheckResult("mission_plan", mission_plan_present, "Present" if mission_plan_present else "Missing"),
    ]

    blocking_failures = [c.name for c in checks if c.blocking and not c.passed]
    ready = len(blocking_failures) == 0

    return ReadinessReport(
        mission_id=mission_id,
        ready=ready,
        checks=checks,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        blocking_failures=blocking_failures,
    )
