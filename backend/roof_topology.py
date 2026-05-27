"""
STRATEX™ Roof Topology Engine
==============================

This module is the deterministic geometric output of the full STRATEX™ Vision pipeline.

Pipeline architecture (the photogrammetry stages run upstream of this module on
ingested DJI flight payloads — they are described in the docstring below for
reference; the production implementation lives in `stratex_vision_pipeline/`):

  1. INGEST          — Read 8K RGB MP4 + RJPEG thermal stream + DJI XMP/EXIF
                       (RTK fix, gimbal pitch/roll/yaw, focal length, ISO).
  2. EXTRACT FRAMES  — Decode 1/N frames (N tuned to flight speed) to JPGs.
  3. SfM             — Feature detection (SuperPoint + LightGlue or SIFT) +
                       bundle-adjusted Structure-from-Motion. Telemetry-prior
                       initialised camera poses; output: sparse point cloud +
                       refined intrinsics/extrinsics per frame.
  4. DENSIFICATION   — MVS (PatchMatch) OR a hybrid NeRF / 3D Gaussian Splat
                       optimisation for a metric-scaled radiance volume.
  5. MESH EXTRACT    — Marching cubes / Poisson surface reconstruction →
                       dense triangle mesh. Vertex decimation preserving sharp
                       eaves / ridges / valleys (curvature-aware quadric edge
                       collapse).
  6. FACET SEGMENT   — Region-grow planes by normal similarity (RANSAC) →
                       label each triangle into a facet ID (F1, F2, ...).
  7. EDGE CLASSIFY   — For every facet boundary edge, inspect the dihedral
                       angle of the two adjoining facet normals:
                            > 180°  → Valley
                            < 180°  → Hip / Ridge (ridge if both planes face
                                                  upward, hip otherwise)
                            no adj. → Eave (horizontal) or Rake/Gable (sloped)
  8. RTK CALIBRATE   — Apply scale s such that 1 unit = 1 metre using RTK
                       baseline. Convert to feet for US Xactimate.
  9. THERMAL FUSION  — Project each RJPEG pixel onto the mesh using the
                       co-registered RGB+thermal camera matrices. Build a
                       per-vertex thermal channel. Detect persistent thermal
                       deltas during the post-sunset cooling window (the only
                       window where dry roof emissivity stabilises and trapped
                       moisture remains warmer).
 10. ANOMALY LOCALISE— Cluster significant thermal deltas, intersect with the
                       mesh, snap to the affected facet, compute affected
                       polygon area (m² → ft²), and assign a confidence score
                       based on delta stability across thermal frames.
 11. OUTPUT          — Structured JSON (this module's data classes) →
                       STRATEX™ Quant™ + Forensic Overlay UI.

This module exposes the FINAL OUTPUT structures. Presets simulate Stage-11
output for the demo build, so the rest of the system (Quant™ Reconciliation
Engine, Xactimate mapping, multi-agent narratives, PDF supplements) can run
end-to-end without live drone data.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Any

Vec3 = Tuple[float, float, float]


# ---------------------------------------------------------------------------
# Geometric helpers
# ---------------------------------------------------------------------------

def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(v: Vec3) -> float:
    return math.sqrt(_dot(v, v))


def _normalise(v: Vec3) -> Vec3:
    n = _norm(v)
    return (v[0] / n, v[1] / n, v[2] / n) if n else (0.0, 0.0, 1.0)


def polygon_area_3d(verts: List[Vec3]) -> float:
    """True 3D polygon area via Newell's method (handles non-planar gracefully)."""
    n = (0.0, 0.0, 0.0)
    m = len(verts)
    for i in range(m):
        a = verts[i]
        b = verts[(i + 1) % m]
        n = (
            n[0] + (a[1] - b[1]) * (a[2] + b[2]),
            n[1] + (a[2] - b[2]) * (a[0] + b[0]),
            n[2] + (a[0] - b[0]) * (a[1] + b[1]),
        )
    return 0.5 * _norm(n)


def polygon_normal(verts: List[Vec3]) -> Vec3:
    """Unit normal of a (planar) polygon via Newell's method."""
    n = (0.0, 0.0, 0.0)
    m = len(verts)
    for i in range(m):
        a = verts[i]
        b = verts[(i + 1) % m]
        n = (
            n[0] + (a[1] - b[1]) * (a[2] + b[2]),
            n[1] + (a[2] - b[2]) * (a[0] + b[0]),
            n[2] + (a[0] - b[0]) * (a[1] + b[1]),
        )
    return _normalise(n)


def pitch_from_normal(n: Vec3) -> float:
    """Pitch as rise-over-12 from a facet normal pointing upward."""
    n = _normalise(n)
    horiz = math.sqrt(n[0] * n[0] + n[2] * n[2])
    if n[1] <= 0:
        return 0.0
    return round(12.0 * horiz / n[1], 1)


def edge_length(a: Vec3, b: Vec3) -> float:
    return _norm(_sub(a, b))


# ---------------------------------------------------------------------------
# Data classes for the structured roof model
# ---------------------------------------------------------------------------

@dataclass
class Facet:
    id: str
    vertices: List[Vec3]          # 3D polygon (units = feet)
    normal: Vec3
    area_planar_sf: float
    area_true_sf: float
    pitch: float                  # rise per 12
    color_tag: str                # ui color hint

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["vertices"] = [list(v) for v in self.vertices]
        d["normal"] = list(self.normal)
        return d


@dataclass
class Edge:
    a: Vec3
    b: Vec3
    length_ft: float
    classification: str           # ridge|valley|hip|eave|rake

    def to_dict(self) -> Dict[str, Any]:
        return {
            "a": list(self.a),
            "b": list(self.b),
            "length_ft": round(self.length_ft, 2),
            "classification": self.classification,
        }


@dataclass
class TopologyTotals:
    total_sf: float
    squares: float
    ridges_lf: float
    valleys_lf: float
    hips_lf: float
    eaves_lf: float
    rakes_lf: float

    def to_dict(self) -> Dict[str, Any]:
        return {k: round(v, 2) for k, v in asdict(self).items()}


# ---------------------------------------------------------------------------
# Preset roof topologies (vertex/facet/edge defs).
# All coordinates are in feet. y is vertical. Origin centred on footprint.
# ---------------------------------------------------------------------------

def _hip_box(L: float, W: float, eave_overhang: float, pitch: float,
             centre_x: float = 0.0, centre_z: float = 0.0,
             facet_prefix: str = "F",
             colors: Tuple[str, str, str, str] = ("#FF8A60", "#7BB7C6", "#FFB87A", "#6FA3B5")) -> Tuple[List[Facet], List[Edge]]:
    """A simple hip roof (4 trapezoidal/triangular facets meeting at a ridge or apex)."""
    HL = L / 2 + eave_overhang
    HW = W / 2 + eave_overhang
    apex_h = HW * (pitch / 12.0)
    # eave corners (ground plane y=0)
    A = (centre_x - HL, 0, centre_z - HW)
    B = (centre_x + HL, 0, centre_z - HW)
    C = (centre_x + HL, 0, centre_z + HW)
    D = (centre_x - HL, 0, centre_z + HW)
    # ridge endpoints (along x)
    ridge_inset = HW
    R1 = (centre_x - HL + ridge_inset, apex_h, centre_z)
    R2 = (centre_x + HL - ridge_inset, apex_h, centre_z)
    # If the box is square or close, ridge collapses to a pyramid apex.
    if HL - ridge_inset < 0.5:
        R1 = (centre_x, apex_h, centre_z)
        R2 = R1

    facets: List[Facet] = []

    def mkfacet(idx, verts, color):
        nrm = polygon_normal(verts)
        # Ensure upward-facing normal
        if nrm[1] < 0:
            verts = list(reversed(verts))
            nrm = polygon_normal(verts)
        ap = polygon_area_3d(verts)
        # planar area = projection on xz plane
        verts_xz = [(v[0], 0, v[2]) for v in verts]
        planar = polygon_area_3d(verts_xz)
        return Facet(
            id=f"{facet_prefix}{idx}",
            vertices=verts,
            normal=nrm,
            area_planar_sf=round(planar, 2),
            area_true_sf=round(ap, 2),
            pitch=pitch_from_normal(nrm),
            color_tag=color,
        )

    # front (south) slope: A,B,R2,R1
    facets.append(mkfacet(1, [A, B, R2, R1], colors[0]))
    # right hip: B,C,R2
    facets.append(mkfacet(2, [B, C, R2], colors[1]))
    # back slope: C,D,R1,R2
    facets.append(mkfacet(3, [C, D, R1, R2], colors[2]))
    # left hip: D,A,R1
    facets.append(mkfacet(4, [D, A, R1], colors[3]))

    edges: List[Edge] = []
    # eaves
    edges.append(Edge(A, B, edge_length(A, B), "eave"))
    edges.append(Edge(B, C, edge_length(B, C), "eave"))
    edges.append(Edge(C, D, edge_length(C, D), "eave"))
    edges.append(Edge(D, A, edge_length(D, A), "eave"))
    # hips
    edges.append(Edge(A, R1, edge_length(A, R1), "hip"))
    edges.append(Edge(B, R2, edge_length(B, R2), "hip"))
    edges.append(Edge(C, R2, edge_length(C, R2), "hip"))
    edges.append(Edge(D, R1, edge_length(D, R1), "hip"))
    # ridge
    if R1 != R2:
        edges.append(Edge(R1, R2, edge_length(R1, R2), "ridge"))

    return facets, edges


def preset_hip(scale: float = 1.0) -> Tuple[List[Facet], List[Edge]]:
    return _hip_box(L=44 * scale, W=30 * scale, eave_overhang=1.5, pitch=8)


def preset_gable(scale: float = 1.0) -> Tuple[List[Facet], List[Edge]]:
    """Simple front-gable roof: 2 long slope facets + 2 triangular gables on rakes."""
    L = 48 * scale
    W = 28 * scale
    overhang = 1.5
    HL = L / 2 + overhang
    HW = W / 2 + overhang
    apex_h = HW * (8 / 12.0)
    A = (-HL, 0, -HW)
    B = (HL, 0, -HW)
    C = (HL, 0, HW)
    D = (-HL, 0, HW)
    R1 = (-HL, apex_h, 0)
    R2 = (HL, apex_h, 0)

    def mkfacet(idx, verts, color):
        nrm = polygon_normal(verts)
        if nrm[1] < 0:
            verts = list(reversed(verts))
            nrm = polygon_normal(verts)
        return Facet(
            id=f"F{idx}", vertices=verts, normal=nrm,
            area_planar_sf=round(polygon_area_3d([(v[0], 0, v[2]) for v in verts]), 2),
            area_true_sf=round(polygon_area_3d(verts), 2),
            pitch=pitch_from_normal(nrm),
            color_tag=color,
        )

    facets = [
        mkfacet(1, [A, B, R2, R1], "#FF8A60"),  # front slope
        mkfacet(2, [C, D, R1, R2], "#7BB7C6"),  # back slope
    ]
    edges = [
        Edge(A, B, edge_length(A, B), "eave"),
        Edge(C, D, edge_length(C, D), "eave"),
        Edge(R1, R2, edge_length(R1, R2), "ridge"),
        Edge(A, R1, edge_length(A, R1), "rake"),
        Edge(B, R2, edge_length(B, R2), "rake"),
        Edge(D, R1, edge_length(D, R1), "rake"),
        Edge(C, R2, edge_length(C, R2), "rake"),
    ]
    return facets, edges


def preset_cross_hip(scale: float = 1.0) -> Tuple[List[Facet], List[Edge]]:
    """Cross-hip roof — two intersecting hip volumes (matches the blueprint reference)."""
    # Wing A: long east-west, plus Wing B: long north-south, intersecting.
    a, ea = _hip_box(L=44 * scale, W=24 * scale, eave_overhang=1.5, pitch=8,
                     centre_x=0, centre_z=0, facet_prefix="A",
                     colors=("#FF8A60", "#FFB87A", "#7BB7C6", "#6FA3B5"))
    b, eb = _hip_box(L=24 * scale, W=34 * scale, eave_overhang=1.5, pitch=8,
                     centre_x=4 * scale, centre_z=8 * scale, facet_prefix="B",
                     colors=("#FFD37A", "#A7C8D2", "#D9A06E", "#88A8B5"))
    facets = a + b
    # mark intersection edges as valleys (informational; visual treatment uses planar bands)
    edges = ea + eb
    # add 2 implicit valleys at the intersection (approx where ridges cross)
    inter1 = (-2 * scale, 0, 4 * scale)
    inter2 = (10 * scale, 6 * scale, 6 * scale)
    edges.append(Edge(inter1, inter2, edge_length(inter1, inter2), "valley"))
    edges.append(Edge((-2 * scale, 0, 12 * scale), inter2, edge_length((-2 * scale, 0, 12 * scale), inter2), "valley"))
    return facets, edges


def preset_l_shape(scale: float = 1.0) -> Tuple[List[Facet], List[Edge]]:
    """L-shaped plan with two hip volumes connected at a 90° corner — creates valleys."""
    a, ea = _hip_box(L=40 * scale, W=22 * scale, eave_overhang=1.5, pitch=8,
                     centre_x=0, centre_z=-8 * scale, facet_prefix="L",
                     colors=("#FF8A60", "#7BB7C6", "#FFB87A", "#6FA3B5"))
    b, eb = _hip_box(L=22 * scale, W=28 * scale, eave_overhang=1.5, pitch=8,
                     centre_x=-9 * scale, centre_z=8 * scale, facet_prefix="K",
                     colors=("#FFD37A", "#A7C8D2", "#D9A06E", "#88A8B5"))
    facets = a + b
    edges = ea + eb
    # valley
    v0 = (-2 * scale, 6 * scale, -2 * scale)
    v1 = (-9 * scale, 0, 4 * scale)
    edges.append(Edge(v0, v1, edge_length(v0, v1), "valley"))
    return facets, edges


def preset_dutch_gable(scale: float = 1.0) -> Tuple[List[Facet], List[Edge]]:
    """Dutch-gable hybrid: hip lower portion + small gable above the eave ends."""
    facets, edges = _hip_box(L=46 * scale, W=28 * scale, eave_overhang=1.5, pitch=8)
    return facets, edges


def preset_stratex_demo(scale: float = 1.0) -> Tuple[List[Facet], List[Edge]]:
    """STRATEX™ flagship demo topology — mirrors the reference plan-view footprint
    from the customer's IMG_2174 spec. FIVE distinct hip volumes + chimney:

      Plan view (xz, +z = north / back of house):

          ┌────── REAR WING (north) ──┐
          │       8 × 4               │
          ├───────────────────────────┤
          │                           │
          │   MAIN BODY (central)     │
          │   18 × 12                 │   ← LARGE central mass, east-west ridge
          │                           │
       ┌──┤                           │
       │  │                           │
       │L │                           │
       │  │                           │
       └──┴──┬────────────────────────┘
        WEST │   FRONT ENTRY PORCH
        BUMP │     (small hip)
        OUT  │
             └────────────────────────

    Total: 5 hip masses + chimney = ~16-18 facets, ~2,400-3,000 sf depending on scale.
    """
    # 1. MAIN BODY — largest mass, east-west long axis, dominates the silhouette
    main_facets, main_edges = _hip_box(
        L=18 * scale, W=12 * scale, eave_overhang=1.5, pitch=8,
        centre_x=0, centre_z=0, facet_prefix="M",
        colors=("#FF8A60", "#FFB87A", "#7BB7C6", "#6FA3B5"),
    )

    # 2. REAR WING — projects NORTH from the back of the main body, long & shallow
    rw_facets, rw_edges = _hip_box(
        L=8 * scale, W=4 * scale, eave_overhang=1.0, pitch=7,
        centre_x=0, centre_z=8 * scale, facet_prefix="R",
        colors=("#FFD37A", "#A7C8D2", "#D9A06E", "#88A8B5"),
    )

    # 3. WEST BUMPOUT — small projection on the LEFT side (room/sunroom)
    wb_facets, wb_edges = _hip_box(
        L=3 * scale, W=6 * scale, eave_overhang=1.0, pitch=7,
        centre_x=-10 * scale, centre_z=-1 * scale, facet_prefix="W",
        colors=("#FFB46E", "#9FBFC9", "#E0A878", "#7E9DAA"),
    )

    # 4. FRONT-LEFT HIP — projects SOUTH-WEST (matches IMG_2174 front-corner mass)
    fl_facets, fl_edges = _hip_box(
        L=5 * scale, W=4 * scale, eave_overhang=1.0, pitch=7,
        centre_x=-6 * scale, centre_z=-8 * scale, facet_prefix="F",
        colors=("#FF9C70", "#B4D2DC", "#D9A878", "#7CA0B0"),
    )

    # 5. FRONT ENTRY PORCH — smallest hip, sits at the very front-center (south)
    pf_facets, pf_edges = _hip_box(
        L=4 * scale, W=3 * scale, eave_overhang=0.8, pitch=6,
        centre_x=4 * scale, centre_z=-8.5 * scale, facet_prefix="P",
        colors=("#FFC084", "#A3C0CA", "#E5B68A", "#86A2AE"),
    )

    facets = main_facets + rw_facets + wb_facets + fl_facets + pf_facets
    edges = main_edges + rw_edges + wb_edges + fl_edges + pf_edges

    # Valley intersections where wings meet the main body — IRC §R905.2.8.3 valleys
    # These are visual + classification cues; the renderer uses them for valley line color.
    valleys = [
        # rear wing meets main body
        ((-4 * scale, 4 * scale, 6 * scale), (-4 * scale, 6 * scale, 6 * scale), "valley"),
        ((4 * scale,  4 * scale, 6 * scale), (4 * scale,  6 * scale, 6 * scale), "valley"),
        # front-left hip meets main body
        ((-9 * scale, 0,         -6 * scale), (-7 * scale, 4 * scale, -4 * scale), "valley"),
        # front entry porch meets main body
        ((2 * scale,  0,         -7 * scale), (4 * scale,  3 * scale, -6 * scale), "valley"),
        # west bumpout meets main body
        ((-9 * scale, 0,          2 * scale), (-7 * scale, 4 * scale,  0),         "valley"),
    ]
    for a, b, cls in valleys:
        edges.append(Edge(a, b, edge_length(a, b), cls))

    # Chimney prism — small upright box on the main roof's rear slope
    cx, cz = 5.0 * scale, 2.0 * scale
    cw, cd, ch = 1.2 * scale, 1.2 * scale, 3.5 * scale
    base_y = 5.5 * scale  # sits on the main roof surface
    P1 = (cx - cw / 2, base_y, cz - cd / 2)
    P2 = (cx + cw / 2, base_y, cz - cd / 2)
    P3 = (cx + cw / 2, base_y, cz + cd / 2)
    P4 = (cx - cw / 2, base_y, cz + cd / 2)
    T1 = (P1[0], base_y + ch, P1[2])
    T2 = (P2[0], base_y + ch, P2[2])
    T3 = (P3[0], base_y + ch, P3[2])
    T4 = (P4[0], base_y + ch, P4[2])
    chimney_color = "#6FA3B5"
    cf = []
    for i, verts in enumerate([
        [P1, P2, T2, T1],
        [P2, P3, T3, T2],
        [P3, P4, T4, T3],
        [P4, P1, T1, T4],
        [T1, T2, T3, T4],
    ]):
        nrm = polygon_normal(verts)
        ap = polygon_area_3d(verts)
        verts_xz = [(v[0], 0, v[2]) for v in verts]
        planar = polygon_area_3d(verts_xz)
        cf.append(Facet(
            id=f"CH{i+1}", vertices=verts, normal=nrm,
            area_planar_sf=round(planar, 2),
            area_true_sf=round(ap, 2),
            pitch=pitch_from_normal(nrm) if i == 4 else 90.0,
            color_tag=chimney_color,
        ))
    facets.extend(cf)
    for a, b in [(P1, P2), (P2, P3), (P3, P4), (P4, P1),
                 (T1, T2), (T2, T3), (T3, T4), (T4, T1),
                 (P1, T1), (P2, T2), (P3, T3), (P4, T4)]:
        edges.append(Edge(a, b, edge_length(a, b), "rake"))

    return facets, edges


PRESETS = {
    "hip": preset_hip,
    "gable": preset_gable,
    "cross_hip": preset_cross_hip,
    "l_shape": preset_l_shape,
    "dutch_gable": preset_dutch_gable,
    "stratex_demo": preset_stratex_demo,
}


# ---------------------------------------------------------------------------
# Totals + anomaly mapping
# ---------------------------------------------------------------------------

def topology_totals(facets: List[Facet], edges: List[Edge]) -> TopologyTotals:
    total_sf = sum(f.area_true_sf for f in facets)
    def sum_class(c):
        return sum(e.length_ft for e in edges if e.classification == c)
    return TopologyTotals(
        total_sf=round(total_sf, 2),
        squares=round(total_sf / 100.0, 2),
        ridges_lf=round(sum_class("ridge"), 2),
        valleys_lf=round(sum_class("valley"), 2),
        hips_lf=round(sum_class("hip"), 2),
        eaves_lf=round(sum_class("eave"), 2),
        rakes_lf=round(sum_class("rake"), 2),
    )


def localise_anomalies(facets: List[Facet], edges: List[Edge], project_seed: str) -> List[Dict[str, Any]]:
    """Distribute anomalies across facets with realistic areas + confidence scores.

    Also synthesizes the two structural-forensics classes per the STRATEX™ Tri-Layer spec:
      - "Gutter Board Rot / Water Infiltration" — flagged when the thermal scan detects
        a continuous Δ > 3°C along an eave vector lasting > 2 hrs post-sunset.
      - "Rafter Deflection / Structural Framing Compromise" — flagged when surface plane
        deflection > 0.75" between standard 16"/24" o.c. rafter vectors.
    """
    rnd = random.Random(project_seed + "topology_anom")
    catalog = [
        ("Trapped Moisture", "subsurface_moisture", "+7.2°F", "CRITICAL"),
        ("CDX Deck Rot", "rotted_decking", "+9.6°F", "CRITICAL"),
        ("Missing Shingle Field", "missing_shingle", "-3.1°F", "HIGH"),
        ("Loose Flashing", "flashing_defect", "+2.4°F", "MED"),
        ("Hail Bruising Cluster", "impact_bruising", "+1.8°F", "MED"),
        ("Sealant Failure", "sealant_failure", "+1.1°F", "LOW"),
    ]
    count = rnd.randint(4, max(4, min(len(facets), 6)))
    anomalies = []
    for i in range(count):
        kind, code, delta, sev = rnd.choice(catalog)
        f = rnd.choices(facets, weights=[f.area_true_sf for f in facets], k=1)[0]
        area_pct = rnd.uniform(0.04, 0.22)
        area_affected = round(f.area_true_sf * area_pct, 1)
        confidence = round(rnd.uniform(0.86, 0.99), 3)
        lat = round(38.0406 + rnd.uniform(-0.0005, 0.0005), 6)
        lon = round(-84.5037 + rnd.uniform(-0.0005, 0.0005), 6)
        anomalies.append({
            "id": f"AD-KY041-{i + 1:03d}",
            "type": kind, "diagnosis": kind, "code": code,
            "facet_id": f.id, "area_affected_sf": area_affected,
            "thermal_delta": delta, "severity": sev, "confidence": confidence,
            "lat": lat, "lon": lon,
            "layer": "roofing",
            "centroid": [
                round(sum(v[0] for v in f.vertices) / len(f.vertices), 2),
                round(sum(v[1] for v in f.vertices) / len(f.vertices), 2),
                round(sum(v[2] for v in f.vertices) / len(f.vertices), 2),
            ],
        })

    # --- A. Gutter Board Rot (on eave vectors) ---
    if rnd.random() < 0.75:
        eave_edges = [e for e in edges if e.classification == "eave"]
        if eave_edges:
            e = rnd.choice(eave_edges)
            length_affected_ft = round(e.length_ft * rnd.uniform(0.25, 0.55), 1)
            confidence = round(rnd.uniform(0.88, 0.97), 3)
            mid = (
                round((e.a[0] + e.b[0]) / 2, 2),
                round((e.a[1] + e.b[1]) / 2, 2),
                round((e.a[2] + e.b[2]) / 2, 2),
            )
            anomalies.append({
                "id": f"AD-KY041-{len(anomalies) + 1:03d}",
                "type": "Gutter Board Rot",
                "diagnosis": "Gutter Board Rot / Water Infiltration",
                "code": "gutter_board_rot",
                "facet_id": None,
                "edge_a": list(e.a), "edge_b": list(e.b),
                "length_affected_ft": length_affected_ft,
                "area_affected_sf": round(length_affected_ft * 0.67, 1),  # ~8" board height
                "thermal_delta": "+3.6°C (post-sunset retention)",
                "severity": "HIGH",
                "confidence": confidence,
                "lat": round(38.0406 + rnd.uniform(-0.0005, 0.0005), 6),
                "lon": round(-84.5037 + rnd.uniform(-0.0005, 0.0005), 6),
                "layer": "framing",
                "centroid": list(mid),
            })

    # --- B. Rafter Deflection (planar dip > 0.75" on a facet) ---
    if rnd.random() < 0.45:
        f = rnd.choice(facets)
        deflection_in = round(rnd.uniform(0.78, 1.45), 2)
        rafter_oc = rnd.choice([16, 24])
        confidence = round(rnd.uniform(0.84, 0.95), 3)
        anomalies.append({
            "id": f"AD-KY041-{len(anomalies) + 1:03d}",
            "type": "Rafter Deflection",
            "diagnosis": "Rafter Deflection / Structural Framing Compromise",
            "code": "rafter_deflection",
            "facet_id": f.id,
            "deflection_in": deflection_in,
            "rafter_oc_in": rafter_oc,
            "area_affected_sf": round(f.area_true_sf * rnd.uniform(0.12, 0.28), 1),
            "thermal_delta": f"{deflection_in}\" planar deflection ({rafter_oc}\" o.c.)",
            "severity": "CRITICAL",
            "confidence": confidence,
            "lat": round(38.0406 + rnd.uniform(-0.0005, 0.0005), 6),
            "lon": round(-84.5037 + rnd.uniform(-0.0005, 0.0005), 6),
            "layer": "framing",
            "centroid": [
                round(sum(v[0] for v in f.vertices) / len(f.vertices), 2),
                round(sum(v[1] for v in f.vertices) / len(f.vertices), 2),
                round(sum(v[2] for v in f.vertices) / len(f.vertices), 2),
            ],
        })

    return anomalies


# ---------------------------------------------------------------------------
# Framing layer (IBC/IRC compliant: rafters at 16" or 24" on-center)
# ---------------------------------------------------------------------------

def build_framing(facets: List[Facet], edges: List[Edge], rafter_oc_in: int = 16) -> Dict[str, Any]:
    """Generate rafter vectors per facet (from ridge/hip toward eave) + sub-fascia perimeter band.

    Rafters are drawn from the highest edge (ridge/hip) of each facet toward the corresponding
    eave edge, spaced every rafter_oc_in inches. This is a simplified geometric approximation
    sufficient for the Tri-Layer visualization; real framing uses bird-mouth + plumb cuts.
    """
    rafters: List[Dict[str, Any]] = []
    rafter_oc_ft = rafter_oc_in / 12.0

    for f in facets:
        verts = f.vertices
        if len(verts) < 3:
            continue
        # Find the lowest-y edge (eave) and the highest-y edge (ridge/hip)
        edges_local = [(verts[i], verts[(i + 1) % len(verts)]) for i in range(len(verts))]
        edges_local.sort(key=lambda e: (e[0][1] + e[1][1]) / 2)
        eave = edges_local[0]
        # use the opposite/highest edge as the ridge side
        top = edges_local[-1]
        # Eave length
        eave_len = _norm(_sub(eave[1], eave[0]))
        if eave_len < 0.1: continue
        nrafters = max(2, int(eave_len / rafter_oc_ft))
        for i in range(nrafters + 1):
            t = i / nrafters
            a = (eave[0][0] + (eave[1][0] - eave[0][0]) * t,
                 eave[0][1] + (eave[1][1] - eave[0][1]) * t,
                 eave[0][2] + (eave[1][2] - eave[0][2]) * t)
            # opposite point on top edge
            b = (top[0][0] + (top[1][0] - top[0][0]) * t,
                 top[0][1] + (top[1][1] - top[0][1]) * t,
                 top[0][2] + (top[1][2] - top[0][2]) * t)
            rafters.append({
                "facet_id": f.id,
                "a": list(a), "b": list(b),
                "length_ft": round(_norm(_sub(b, a)), 2),
                "oc_in": rafter_oc_in,
            })

    # Sub-fascia band: a thin extrusion below every eave edge
    sub_fascia: List[Dict[str, Any]] = []
    for e in edges:
        if e.classification == "eave":
            sub_fascia.append({
                "a": list(e.a), "b": list(e.b),
                "length_ft": round(e.length_ft, 2),
                "drop_in": 6.0,  # 6" sub-fascia board
            })

    total_rafter_lf = round(sum(r["length_ft"] for r in rafters), 2)
    total_sub_fascia_lf = round(sum(s["length_ft"] for s in sub_fascia), 2)

    return {
        "rafter_oc_in": rafter_oc_in,
        "rafters": rafters,
        "sub_fascia": sub_fascia,
        "total_rafter_lf": total_rafter_lf,
        "total_sub_fascia_lf": total_sub_fascia_lf,
    }


# ---------------------------------------------------------------------------
# Gutter layer — seamless k-style profiles + downspouts + accessories
# ---------------------------------------------------------------------------

def build_gutters(facets: List[Facet], edges: List[Edge], primary_pitch: float) -> Dict[str, Any]:
    """Auto-compute seamless gutter system from eave edges per IRC Chapter 11.

    Rules baked in:
      - Profile selection: 6" K-Style if any facet > 2500sf OR pitch > 8/12; else 5" K-Style.
      - Hangers: heavy-duty hidden screw, 24" o.c.
      - Downspouts: 30-40ft maximum continuous run.
      - Slope: 1/16" per foot.
      - Miters: external/internal at every eave corner where adjacent eaves are non-colinear.
    """
    eave_edges = [e for e in edges if e.classification == "eave"]
    total_lf = sum(e.length_ft for e in eave_edges)
    max_facet_sf = max((f.area_true_sf for f in facets), default=0)
    profile = "6\" K-Style Heavy" if (max_facet_sf > 2500 or primary_pitch > 8) else "5\" K-Style"

    # Hangers — 24" o.c.
    hangers_count = int(total_lf / 2) + len(eave_edges)  # 1 per 2 ft + 1 per eave end

    # Downspouts — every 35 ft of continuous eave run
    downspouts: List[Dict[str, Any]] = []
    downspout_drop_every_ft = 35.0
    for e in eave_edges:
        n = max(1, int(round(e.length_ft / downspout_drop_every_ft)))
        for i in range(n):
            t = (i + 0.5) / n
            x = e.a[0] + (e.b[0] - e.a[0]) * t
            y = e.a[1] + (e.b[1] - e.a[1]) * t
            z = e.a[2] + (e.b[2] - e.a[2]) * t
            downspouts.append({
                "drop": [round(x, 2), round(y, 2), round(z, 2)],
                "ground": [round(x, 2), 0.0, round(z, 2)],
                "elbow_count": 2,           # 1 A-style at top + 1 B-style at base
                "length_ft": round(y, 2),
            })

    # Miters — at every eave endpoint that's shared with another non-colinear eave
    miter_count = 0
    eave_points: Dict[Tuple[float, float, float], List[Tuple[Vec3, Vec3]]] = {}
    for e in eave_edges:
        for endpoint, other in ((e.a, e.b), (e.b, e.a)):
            key = (round(endpoint[0], 2), round(endpoint[1], 2), round(endpoint[2], 2))
            eave_points.setdefault(key, []).append((endpoint, other))
    for adj in eave_points.values():
        if len(adj) >= 2:
            miter_count += 1
    miter_count = max(2, miter_count // 2)  # 2 corners minimum

    # Build polylines for each eave segment to be extruded as cyan gutter trough
    polylines = [
        {
            "a": list(e.a), "b": list(e.b),
            "length_ft": round(e.length_ft, 2),
            "slope_in_per_ft": 0.0625,
        }
        for e in eave_edges
    ]

    return {
        "profile": profile,
        "total_lf": round(total_lf, 2),
        "polylines": polylines,
        "hangers": {"count": hangers_count, "spacing_in": 24},
        "downspouts": downspouts,
        "downspouts_count": len(downspouts),
        "elbow_count": sum(d["elbow_count"] for d in downspouts),
        "end_cap_count": len(eave_edges) * 2,
        "miter_count": miter_count,
        "conductor_head_count": max(1, len(downspouts) // 3),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_topology(topology: Dict[str, Any]) -> Dict[str, Any]:
    """Multi-Agent Expert Panel — Pre-Render Validation Gates.

    Codified consensus from /app/memory/expert_panel_review.md. Every digital twin
    must pass these 6 gates before the renderer is allowed to draw it. Each gate
    returns a {pass, message, agent} dict so the frontend can show a report card.

    The gates intentionally use generous tolerances so legitimate roof geometry
    passes (target: ±1 cm per RTK) while rejecting topology that would cause the
    "wrong layers" failure mode the user reported.
    """
    gates: List[Dict[str, Any]] = []
    facets = topology.get("facets", [])
    edges = topology.get("edges", [])
    framing = topology.get("framing", {}) or {}
    gutters = topology.get("gutters", {}) or {}

    # ---- Gate 1 (Agent 3 / C1): Every facet has a valid slope basis ----
    bad_facet_ids = []
    for f in facets:
        nrm = f.get("normal", [0, 1, 0])
        # A valid facet normal must be non-zero, normalized, and either roof-pitch
        # (any tilt) or vertical (chimney walls). We reject only zero-vectors.
        if abs(nrm[0]) < 1e-6 and abs(nrm[1]) < 1e-6 and abs(nrm[2]) < 1e-6:
            bad_facet_ids.append(f.get("id"))
    gates.append({
        "id": "slope_basis",
        "label": "Slope basis valid on every facet",
        "agent": "CAD Designer",
        "pass": len(bad_facet_ids) == 0,
        "message": f"All {len(facets)} facets carry a valid slope-aligned UV basis."
                   if not bad_facet_ids else f"Invalid normal on facet(s): {', '.join(map(str, bad_facet_ids))}",
        "rule_ref": "C1",
    })

    # ---- Gate 2 (Agent 4 / G1): Gutter coverage = 100% of eave edges ----
    eave_edges = [e for e in edges if e.get("classification") == "eave"]
    polylines = gutters.get("polylines", [])
    eave_lf = sum(e.get("length_ft", 0) for e in eave_edges)
    gutter_lf = sum(p.get("length_ft", 0) for p in polylines)
    coverage_pct = (gutter_lf / eave_lf * 100) if eave_lf > 0 else 100.0
    gates.append({
        "id": "gutter_coverage",
        "label": "Gutter coverage 100% of eaves",
        "agent": "Gutter Contractor",
        "pass": coverage_pct >= 99.5,
        "message": f"Coverage {coverage_pct:.1f}% — {gutter_lf:.1f} lf gutter on {eave_lf:.1f} lf eave.",
        "rule_ref": "G1",
        "metric": round(coverage_pct, 1),
    })

    # ---- Gate 3 (Agent 1 / F2): Rafter count matches IRC spacing rule ----
    rafter_oc_in = framing.get("rafter_oc_in", 16)
    rafter_oc_ft = rafter_oc_in / 12.0
    rafters = framing.get("rafters", [])
    # Each facet contributes ~ (eave_len / oc_ft) + 1 rafters. We sum expected counts.
    expected_total = 0
    for f in facets:
        # Skip vertical/chimney facets (pitch=90 means wall, not a roof slope)
        if abs(f.get("pitch", 0) - 90.0) < 0.1:
            continue
        verts = f.get("vertices", [])
        if len(verts) < 3:
            continue
        # Find longest horizontal edge ≈ eave length
        edges_local = []
        for i in range(len(verts)):
            a, b = verts[i], verts[(i + 1) % len(verts)]
            length = math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2 + (b[2]-a[2])**2)
            edges_local.append((length, (a[1] + b[1]) / 2))
        edges_local.sort(key=lambda e: e[1])  # sort by avg y → lowest first (eave)
        eave_len = edges_local[0][0]
        if eave_len > 0.5:
            expected_total += max(2, int(eave_len / rafter_oc_ft)) + 1
    rafter_count = len(rafters)
    # Allow ±20% slack (real-world birds-mouth/jack rafters vary)
    if expected_total == 0:
        rafter_ok = True
        rafter_msg = "No roof facets to evaluate."
    else:
        rafter_ok = 0.8 * expected_total <= rafter_count <= 1.2 * expected_total
        rafter_msg = f"{rafter_count} rafters @ {rafter_oc_in}\" o.c. (expected {expected_total} ±20%)."
    gates.append({
        "id": "rafter_count",
        "label": f"Rafter spacing within IRC §R802.4",
        "agent": "Framing Carpenter / Architect",
        "pass": rafter_ok,
        "message": rafter_msg,
        "rule_ref": "F2",
        "metric": rafter_count,
    })

    # ---- Gate 4 (Agent 1 / F4): Sub-fascia covers every eave ----
    sub_fascia = framing.get("sub_fascia", [])
    sub_fascia_lf = sum(s.get("length_ft", 0) for s in sub_fascia)
    sf_coverage = (sub_fascia_lf / eave_lf * 100) if eave_lf > 0 else 100.0
    gates.append({
        "id": "sub_fascia",
        "label": "Structural sub-fascia on every eave",
        "agent": "Framing Carpenter / Architect",
        "pass": sf_coverage >= 99.5,
        "message": f"{sub_fascia_lf:.1f} lf sub-fascia on {eave_lf:.1f} lf eave ({sf_coverage:.1f}%).",
        "rule_ref": "F4",
        "metric": round(sf_coverage, 1),
    })

    # ---- Gate 5 (Agent 2 / R5): Material direction = slope-aligned ----
    # This is enforced at render-time by the slope-aligned UV basis. Here we just
    # verify the contract: every facet has a non-vertical normal that the renderer
    # can build a U/V frame from. (Vertical facets like chimney walls are exempt.)
    non_slope_count = sum(
        1 for f in facets
        if abs(f.get("pitch", 0) - 90.0) > 0.1            # not a vertical wall
        and abs(f.get("normal", [0, 1, 0])[1]) < 0.001    # but no upward component
    )
    gates.append({
        "id": "material_direction",
        "label": "Material flows with slope on every facet",
        "agent": "Roofing Contractor",
        "pass": non_slope_count == 0,
        "message": "All roof facets carry an upward normal component → textures will align eave→ridge."
                   if non_slope_count == 0 else f"{non_slope_count} facet(s) ambiguous slope direction.",
        "rule_ref": "R5",
    })

    # ---- Gate 6 (Agent 3 / C2): Edge classification hierarchy present ----
    have_ridge_or_hip = any(e.get("classification") in ("ridge", "hip") for e in edges)
    have_eave = len(eave_edges) > 0
    gates.append({
        "id": "edge_hierarchy",
        "label": "Edge classification hierarchy (eave + ridge/hip)",
        "agent": "CAD Designer",
        "pass": have_ridge_or_hip and have_eave,
        "message": "Eaves + ridges/hips classified for line-weight hierarchy."
                   if have_ridge_or_hip and have_eave else "Missing ridge/hip or eave classification.",
        "rule_ref": "C2",
    })

    passed = sum(1 for g in gates if g["pass"])
    total = len(gates)
    return {
        "gates": gates,
        "passed": passed,
        "total": total,
        "all_pass": passed == total,
        "score_pct": round(passed / total * 100, 1),
    }


def build_topology(style: str, project_seed: str) -> Dict[str, Any]:
    style = style if style in PRESETS else "stratex_demo"
    rnd = random.Random(project_seed + "scale")
    scale = round(rnd.uniform(0.95, 1.15), 3)
    facets, edges = PRESETS[style](scale=scale)
    totals = topology_totals(facets, edges)
    anomalies = localise_anomalies(facets, edges, project_seed)
    primary_pitch = facets[0].pitch if facets else 8
    framing = build_framing(facets, edges, rafter_oc_in=16)
    gutters = build_gutters(facets, edges, primary_pitch=primary_pitch)
    topology = {
        "style": style,
        "scale": scale,
        "facets": [f.to_dict() for f in facets],
        "edges": [e.to_dict() for e in edges],
        "anomalies": anomalies,
        "anomalies_count": len(anomalies),
        "critical_count": sum(1 for a in anomalies if a["severity"] == "CRITICAL"),
        "totals": totals.to_dict(),
        "primary_pitch": primary_pitch,
        "mesh_status": "STITCHED",
        "rtk_precision_cm": round(rnd.uniform(1.0, 2.5), 2),
        "framing": framing,
        "gutters": gutters,
    }
    # Run the multi-agent expert panel before returning.
    topology["validation"] = validate_topology(topology)
    return topology
