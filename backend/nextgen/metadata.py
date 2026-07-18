"""Best-effort metadata extraction (Directive 006 §10).

Never fabricates absent values — missing fields return `null`. Extraction
failures write a diagnostic to `metadata.errors` but never delete the
underlying evidence.

We deliberately keep this Pillow-only for Phase 2A. Full DJI R-JPG
radiometric parsing arrives in a later block via a dedicated adapter.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, Optional

try:
    from PIL import Image, ExifTags
    _PIL_OK = True
except Exception:  # pragma: no cover
    _PIL_OK = False


def _gps_to_decimal(coord, ref) -> Optional[float]:
    try:
        d, m, s = coord
        val = float(d) + float(m) / 60.0 + float(s) / 3600.0
        if ref in ("S", "W"):
            val = -val
        return val
    except Exception:
        return None


def extract_image_metadata(raw: bytes, mime: str) -> Dict[str, Any]:
    """Return a structured metadata blob. Missing values remain None.

    Never raises — errors are surfaced under `metadata.errors`.
    """
    result: Dict[str, Any] = {
        "camera_make": None,
        "camera_model": None,
        "lens": None,
        "focal_length_mm": None,
        "exposure": None,
        "iso": None,
        "orientation": None,
        "dimensions": None,
        "capture_time": None,
        "gps": None,
        "thermal": None,
        "errors": [],
    }
    if not _PIL_OK or not mime.startswith("image/"):
        return result
    try:
        img = Image.open(BytesIO(raw))
        result["dimensions"] = {"width": img.width, "height": img.height}
        exif = getattr(img, "_getexif", lambda: None)()
        if not exif:
            return result
        tags = {ExifTags.TAGS.get(k, str(k)): v for k, v in exif.items()}
        result["camera_make"] = tags.get("Make")
        result["camera_model"] = tags.get("Model")
        result["lens"] = tags.get("LensModel") or tags.get("LensMake")
        fl = tags.get("FocalLength")
        if fl is not None:
            try:
                result["focal_length_mm"] = float(fl)
            except Exception:
                result["focal_length_mm"] = None
        exposure = tags.get("ExposureTime")
        if exposure is not None:
            try:
                result["exposure"] = float(exposure)
            except Exception:
                result["exposure"] = str(exposure)
        result["iso"] = tags.get("ISOSpeedRatings")
        result["orientation"] = tags.get("Orientation")
        result["capture_time"] = tags.get("DateTimeOriginal") or tags.get("DateTime")
        gps = tags.get("GPSInfo")
        if gps:
            gtags = {ExifTags.GPSTAGS.get(k, str(k)): v for k, v in gps.items()}
            lat = _gps_to_decimal(gtags.get("GPSLatitude"), gtags.get("GPSLatitudeRef"))
            lon = _gps_to_decimal(gtags.get("GPSLongitude"), gtags.get("GPSLongitudeRef"))
            if lat is not None and lon is not None:
                result["gps"] = {
                    "lat": lat, "lon": lon,
                    "altitude": float(gtags.get("GPSAltitude", 0) or 0) or None,
                }
    except Exception as e:  # pragma: no cover
        result["errors"].append(f"pil:{type(e).__name__}:{str(e)[:120]}")
    return result
