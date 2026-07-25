"""Shared helpers for PX-006B residential geometry benchmark."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .constants import GOVERNANCE_LABELS

DEFAULT_DATASET_ROOT = Path("/tmp/stratex-external-datasets")
ENV_DATASET_ROOT = "STRATEX_DATASET_ROOT"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def px006b_dir() -> Path:
    return repo_root() / "engineering" / "px006b"


def benchmark_root() -> Path:
    raw = os.environ.get(ENV_DATASET_ROOT, str(DEFAULT_DATASET_ROOT))
    path = Path(raw).expanduser().resolve() / "px006b_benchmark"
    path.mkdir(parents=True, exist_ok=True)
    return path


def benchmark_runs_dir() -> Path:
    path = benchmark_root() / "runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def benchmark_annotations_dir() -> Path:
    path = benchmark_root() / "annotations"
    path.mkdir(parents=True, exist_ok=True)
    return path


def dataset_root() -> Path:
    raw = os.environ.get(ENV_DATASET_ROOT, str(DEFAULT_DATASET_ROOT))
    path = Path(raw).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def reconstruction_root(dataset_id: str) -> Path:
    return dataset_root() / "reconstructions" / sanitize_dataset_id(dataset_id)


def sanitize_dataset_id(dataset_id: str) -> str:
    text = (dataset_id or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9_]{2,64}", text):
        raise ValueError(f"invalid dataset_id: {dataset_id!r}")
    return text


def new_benchmark_id(prefix: str = "bench") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, *, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_bytes(encoded.encode("utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> Any:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def governance_block(**overrides: str) -> Dict[str, str]:
    block = dict(GOVERNANCE_LABELS)
    block.update(overrides)
    return block


def base_entity(
    *,
    benchmark_id: str,
    dataset_id: str,
    structure_id: str,
    source_revision: str,
    truth_classification: str,
    coordinate_reference: str = "LOCAL_ENU",
    units: str = "meters",
    algorithm_version: str,
    reconstruction_version: str,
    odm_digest: str,
    created_by: str = "benchmark_builder",
    source_classification: str,
    limitations: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "benchmark_id": benchmark_id,
        "dataset_id": dataset_id,
        "source_revision": source_revision,
        "structure_id": structure_id,
        "annotation_version": "manual_v1",
        "algorithm_version": algorithm_version,
        "reconstruction_version": reconstruction_version,
        "odm_digest": odm_digest,
        "coordinate_reference": coordinate_reference,
        "units": units,
        "evidence_references": [],
        "created_at": now_iso(),
        "created_by": created_by,
        "source_classification": source_classification,
        "truth_classification": truth_classification,
        "physical_validation": "NOT_PERFORMED",
        "authoritative": False,
        "limitations": limitations or [],
        "governance": governance_block(),
    }


def polygon_area_xy(points: Sequence[Tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def polygon_perimeter(points: Sequence[Tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        total += math.hypot(x2 - x1, y2 - y1)
    return total


def iou_polygons(
    a: Sequence[Tuple[float, float]],
    b: Sequence[Tuple[float, float]],
) -> float:
    """Axis-aligned bounding-box IoU proxy for development benchmark comparisons."""
    if not a or not b:
        return 0.0

    def bounds(points: Sequence[Tuple[float, float]]) -> Tuple[float, float, float, float]:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return min(xs), min(ys), max(xs), max(ys)

    ax0, ay0, ax1, ay1 = bounds(a)
    bx0, by0, bx1, by1 = bounds(b)
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(0.0, (ax1 - ax0) * (ay1 - ay0))
    area_b = max(0.0, (bx1 - bx0) * (by1 - by0))
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def normalize_vector(vec: Sequence[float]) -> Tuple[float, float, float]:
    x, y, z = float(vec[0]), float(vec[1]), float(vec[2])
    mag = math.sqrt(x * x + y * y + z * z)
    if mag <= 1e-12:
        return 0.0, 0.0, 1.0
    return x / mag, y / mag, z / mag


def slope_degrees_from_normal(normal: Sequence[float]) -> float:
    _, _, nz = normalize_vector(normal)
    nz = max(-1.0, min(1.0, abs(nz)))
    return math.degrees(math.acos(nz))


def azimuth_degrees_from_normal(normal: Sequence[float]) -> float:
    nx, ny, _ = normalize_vector(normal)
    deg = math.degrees(math.atan2(nx, ny))
    return deg % 360.0


def angular_difference_deg(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def percent_difference(reference: float, candidate: float) -> Optional[float]:
    if reference == 0:
        return None
    return abs(candidate - reference) / abs(reference) * 100.0


def redact_gps_from_text(text: str) -> str:
    """Remove raw coordinate literals from tracked report text."""
    text = re.sub(
        r"-?\d{1,3}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}",
        "[REDACTED_COORDINATES]",
        text,
    )
    text = re.sub(
        r"\b(?:lat|lon|latitude|longitude)\s*[:=]\s*-?\d+\.\d+\b",
        "[REDACTED_COORDINATES]",
        text,
        flags=re.IGNORECASE,
    )
    return text


def merge_limitations(*groups: Iterable[str]) -> List[str]:
    seen = set()
    merged: List[str] = []
    for group in groups:
        for item in group:
            if item not in seen:
                seen.add(item)
                merged.append(item)
    return merged
