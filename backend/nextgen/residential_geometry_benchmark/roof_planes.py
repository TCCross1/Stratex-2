"""Roof-plane candidate extraction for PX-006B."""
from __future__ import annotations

import math
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from .authority_guard import assert_benchmark_object
from .common import (
    azimuth_degrees_from_normal,
    base_entity,
    new_benchmark_id,
    normalize_vector,
    slope_degrees_from_normal,
)
from .constants import ALGORITHM_VERSION, ROOF_EDGE_CLASSES


class RoofPlaneError(RuntimeError):
    pass


def _read_laz_points(path: Path, *, max_points: int = 50000) -> np.ndarray:
    try:
        import laspy  # type: ignore
    except ImportError:
        laspy = None
    if laspy is not None:
        las = laspy.read(str(path))
        xyz = np.vstack((las.x, las.y, las.z)).T.astype(float)
        if len(xyz) > max_points:
            idx = np.linspace(0, len(xyz) - 1, max_points, dtype=int)
            xyz = xyz[idx]
        return xyz
    # Fallback: attempt laszip decompression if available.
    laszip = __import__("shutil").which("laszip")
    if laszip:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "cloud.las"
            subprocess.run([laszip, "-i", str(path), "-o", str(out)], check=True, capture_output=True)
            return _read_las_uncompressed(out, max_points=max_points)
    raise RoofPlaneError("point cloud reader unavailable (install laspy or laszip)")


def _read_las_uncompressed(path: Path, *, max_points: int) -> np.ndarray:
    with path.open("rb") as handle:
        header = handle.read(375)
        if len(header) < 100:
            raise RoofPlaneError("invalid LAS header")
        point_format = header[104]
        offset_to_points = struct.unpack("<I", header[96:100])[0]
        point_record_length = struct.unpack("<H", header[105:107])[0]
        num_points = struct.unpack("<I", header[107:111])[0]
        handle.seek(offset_to_points)
        coords: List[Tuple[float, float, float]] = []
        step = max(1, num_points // max_points) if num_points else 1
        for idx in range(0, num_points, step):
            handle.seek(offset_to_points + idx * point_record_length)
            data = handle.read(point_record_length)
            if len(data) < 20:
                break
            if point_format in {0, 1}:
                x, y, z = struct.unpack("<iii", data[:12])
                scale_x, scale_y, scale_z = struct.unpack("<3d", header[131:155])
                offset_x, offset_y, offset_z = struct.unpack("<3d", header[155:179])
                coords.append(
                    (
                        x * scale_x + offset_x,
                        y * scale_y + offset_y,
                        z * scale_z + offset_z,
                    )
                )
        if not coords:
            raise RoofPlaneError("no LAS points decoded")
        return np.array(coords, dtype=float)


def _ransac_plane(points: np.ndarray, *, iterations: int = 200, threshold: float = 0.15) -> Tuple[np.ndarray, np.ndarray, float]:
    if len(points) < 3:
        raise RoofPlaneError("insufficient points for plane fitting")
    best_inliers = np.array([], dtype=int)
    best_normal = np.array([0.0, 0.0, 1.0])
    best_d = 0.0
    rng = np.random.default_rng(42)
    for _ in range(iterations):
        sample_idx = rng.choice(len(points), size=3, replace=False)
        p1, p2, p3 = points[sample_idx]
        normal = np.cross(p2 - p1, p3 - p1)
        norm = np.linalg.norm(normal)
        if norm <= 1e-9:
            continue
        normal = normal / norm
        d = -np.dot(normal, p1)
        distances = np.abs(points @ normal + d)
        inliers = np.where(distances <= threshold)[0]
        if len(inliers) > len(best_inliers):
            best_inliers = inliers
            best_normal = normal
            best_d = d
    if len(best_inliers) < 3:
        raise RoofPlaneError("RANSAC failed to find a stable plane")
    inlier_points = points[best_inliers]
    residual = float(np.mean(np.abs(inlier_points @ best_normal + best_d)))
    return best_normal, best_inliers, residual


def _plane_boundary_polygon(points: np.ndarray) -> List[List[float]]:
    if len(points) < 3:
        return []
    xy = points[:, :2]
    center = xy.mean(axis=0)
    angles = np.arctan2(xy[:, 1] - center[1], xy[:, 0] - center[0])
    order = np.argsort(angles)
    hull = xy[order]
    return [[float(x), float(y)] for x, y in hull]


def extract_roof_planes_from_point_cloud(
    *,
    dataset_id: str,
    structure_id: str,
    source_revision: str,
    reconstruction_version: str,
    odm_digest: str,
    point_cloud_path: str,
    max_planes: int = 3,
) -> Dict[str, Any]:
    path = Path(point_cloud_path)
    if not path.is_file():
        raise RoofPlaneError(f"point cloud missing: {point_cloud_path}")
    points = _read_laz_points(path)
    remaining = points.copy()
    planes: List[Dict[str, Any]] = []
    for idx in range(max_planes):
        if len(remaining) < 50:
            break
        normal, inliers, residual = _ransac_plane(remaining)
        inlier_points = remaining[inliers]
        if len(inlier_points) < 50:
            break
        nx, ny, nz = normalize_vector(normal.tolist())
        slope = slope_degrees_from_normal((nx, ny, nz))
        azimuth = azimuth_degrees_from_normal((nx, ny, nz))
        boundary = _plane_boundary_polygon(inlier_points)
        area = 0.0
        if boundary:
            from .common import polygon_area_xy

            tuples = [(p[0], p[1]) for p in boundary]
            area = polygon_area_xy(tuples)
        planes.append(
            {
                "plane_id": f"plane_{idx + 1}",
                "normal_vector": [nx, ny, nz],
                "slope_degrees": slope,
                "azimuth_degrees": azimuth,
                "boundary_polygon": boundary,
                "area_candidate": area,
                "supporting_point_count": int(len(inlier_points)),
                "residual_error": residual,
                "point_density": float(len(inlier_points) / max(area, 1.0)),
                "occlusion_estimate": "unknown",
                "candidate_confidence": "MODERATE_DEVELOPMENT_CONFIDENCE" if residual < 0.2 else "LOW_DEVELOPMENT_CONFIDENCE",
                "validation_status": "REVIEW_REQUIRED",
            }
        )
        mask = np.ones(len(remaining), dtype=bool)
        mask[inliers] = False
        remaining = remaining[mask]
    entity = base_entity(
        benchmark_id=new_benchmark_id("roof"),
        dataset_id=dataset_id,
        structure_id=structure_id,
        source_revision=source_revision,
        truth_classification="RECONSTRUCTION_DERIVED_CANDIDATE",
        algorithm_version=ALGORITHM_VERSION,
        reconstruction_version=reconstruction_version,
        odm_digest=odm_digest,
        source_classification="RANSAC_POINT_CLOUD_PLANE_FIT",
        limitations=[
            "Roof planes are reconstruction-derived candidates only.",
            "No ApprovedGeometry emission.",
        ],
    )
    entity["roof_planes"] = planes
    entity["algorithm_id"] = "ransac_plane_v1"
    entity["input_artifact"] = str(path)
    assert_benchmark_object(entity)
    return entity


def classify_roof_edges(
    roof_planes: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    edges: List[Dict[str, Any]] = []
    for idx, plane in enumerate(roof_planes):
        boundary = plane.get("boundary_polygon") or []
        if len(boundary) < 2:
            continue
        for edge_idx in range(len(boundary)):
            p1 = boundary[edge_idx]
            p2 = boundary[(edge_idx + 1) % len(boundary)]
            length = math.hypot(float(p2[0]) - float(p1[0]), float(p2[1]) - float(p1[1]))
            edge_class = "EAVE" if plane.get("slope_degrees", 0) < 5 else "RAKE"
            if edge_class not in ROOF_EDGE_CLASSES:
                edge_class = "UNKNOWN"
            edges.append(
                {
                    "edge_id": f"edge_{idx + 1}_{edge_idx + 1}",
                    "detected_class": edge_class,
                    "confidence": 0.4,
                    "supporting_geometry": [p1, p2],
                    "alternative_classifications": ["UNKNOWN"],
                    "review_state": "REVIEW_REQUIRED",
                    "length_candidate": length,
                }
            )
    return edges
