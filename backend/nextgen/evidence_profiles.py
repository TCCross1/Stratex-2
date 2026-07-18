"""Per-product evidence requirement profiles — Directive 006 §7.

Profiles are configuration data, not conditionals in the UI. Each profile
enumerates the required evidence categories, the recommended minimum
counts, and any product-specific validation rules (e.g. AWE thermal delta).
"""
from __future__ import annotations

from typing import Dict, List, TypedDict


class Requirement(TypedDict, total=False):
    category: str
    min_count: int
    label: str
    required: bool


PROFILES: Dict[str, Dict] = {
    "dayscan": {
        "product_key": "dayscan",
        "display_name": "Stratex Core DayScan™",
        "requirements": [
            {"category": "RGB_IMAGE", "min_count": 12, "label": "RGB coverage set", "required": True},
            {"category": "FLIGHT_LOG", "min_count": 1, "label": "Flight log", "required": True},
            {"category": "CAMERA_METADATA", "min_count": 1, "label": "Camera metadata", "required": False},
            {"category": "OPERATOR_NOTE", "min_count": 1, "label": "Operator note", "required": False},
            {"category": "VIDEO", "min_count": 0, "label": "Optional video", "required": False},
            {"category": "MANUAL_MEASUREMENT", "min_count": 0, "label": "Optional manual measurement", "required": False},
        ],
        "validators": ["duplicate_review_complete", "checksums_complete", "metadata_present"],
    },
    "awe_scan": {
        "product_key": "awe_scan",
        "display_name": "Stratex AWE™ Scan",
        "requirements": [
            {"category": "THERMAL_RADIOMETRIC", "min_count": 8, "label": "Radiometric thermal captures", "required": True},
            {"category": "RGB_IMAGE", "min_count": 4, "label": "RGB references", "required": True},
            {"category": "FLIGHT_LOG", "min_count": 1, "label": "Flight log", "required": True},
            {"category": "WEATHER_RECORD", "min_count": 1, "label": "Environmental record", "required": True},
            {"category": "CAMERA_METADATA", "min_count": 1, "label": "Camera + calibration metadata", "required": True},
            {"category": "OPERATOR_NOTE", "min_count": 1, "label": "Operator note", "required": True},
        ],
        "validators": [
            "duplicate_review_complete", "checksums_complete", "metadata_present",
            "awe_environmental_present",
        ],
    },
    "elite": {
        "product_key": "elite",
        "display_name": "Stratex Elite™ Property Intelligence",
        "requirements": [
            {"category": "RGB_IMAGE", "min_count": 12, "label": "RGB coverage (from DayScan)", "required": True},
            {"category": "THERMAL_RADIOMETRIC", "min_count": 8, "label": "Radiometric thermal (from AWE)", "required": True},
            {"category": "FLIGHT_LOG", "min_count": 1, "label": "Flight logs (day + night)", "required": True},
            {"category": "WEATHER_RECORD", "min_count": 1, "label": "Environmental record", "required": True},
            {"category": "OPERATOR_NOTE", "min_count": 1, "label": "Combined operator notes", "required": True},
        ],
        "validators": [
            "duplicate_review_complete", "checksums_complete", "metadata_present",
            "elite_property_link_valid",
        ],
    },
}


ALLOWED_CATEGORIES = {
    "RGB_IMAGE", "THERMAL_RADIOMETRIC", "THERMAL_DERIVATIVE", "VIDEO",
    "FLIGHT_LOG", "TELEMETRY", "CAMERA_METADATA", "CALIBRATION_FILE",
    "WEATHER_RECORD", "AIRSPACE_RECORD", "OPERATOR_NOTE",
    "PROPERTY_DOCUMENT", "PRIOR_REPORT", "MANUAL_MEASUREMENT",
    "INTERIOR_IMAGE", "LIDAR_POINT_CLOUD", "PHOTOGRAMMETRY_OUTPUT",
    "DIGITAL_TWIN_MODEL", "CAD_BIM_DERIVATIVE", "REPORT_DERIVATIVE",
    "OTHER",
}


ORIGINAL_CATEGORIES = {
    "RGB_IMAGE", "THERMAL_RADIOMETRIC", "VIDEO", "FLIGHT_LOG", "TELEMETRY",
    "CAMERA_METADATA", "CALIBRATION_FILE", "WEATHER_RECORD", "AIRSPACE_RECORD",
    "OPERATOR_NOTE", "PROPERTY_DOCUMENT", "PRIOR_REPORT", "MANUAL_MEASUREMENT",
    "INTERIOR_IMAGE", "LIDAR_POINT_CLOUD",
}


DERIVATIVE_CATEGORIES = {
    "THERMAL_DERIVATIVE", "PHOTOGRAMMETRY_OUTPUT", "DIGITAL_TWIN_MODEL",
    "CAD_BIM_DERIVATIVE", "REPORT_DERIVATIVE",
}


ALLOWED_MIME_PREFIXES = (
    "image/", "video/", "text/plain", "text/csv",
    "application/json", "application/octet-stream", "application/pdf",
    "application/x-ndjson",
)


BLOCKED_EXTENSIONS = {
    ".exe", ".bat", ".sh", ".cmd", ".ps1", ".msi", ".dll",
    ".js", ".jse", ".vbs", ".vbe", ".wsf", ".wsh", ".scr",
    ".apk", ".ipa", ".jar",
}
