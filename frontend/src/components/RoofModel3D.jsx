import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

/**
 * STRATEX™ Vision Advanced Diagnostics — Forensic Engineering Canvas
 * ------------------------------------------------------------------
 * - Tactical Cyber-Industrial console aesthetic (#0B0F19 ambient)
 * - Multi-color geometry: cyan ridges/hips, plasma valleys, silver eaves
 * - Facet color-segmentation by orientation (front/rear/side)
 * - Translucent architectural blueprint grid texture per facet
 * - Heat-mapped anomaly glow patches on affected facets
 * - HTML-overlay dimension callouts on classified edges
 * - HTML-overlay leader labels for anomaly IDs
 */

const TEAL    = 0x00f0ff;
const ORANGE  = 0xff5500;
const SAND    = 0xc99a5e;
const STEEL   = 0x8fb8c6;
const SILVER  = 0xc7d4dd;
const BG      = 0x0b0f19;
// World-class neon palette — per user spec
const NEON_BLUE    = 0x1ea7ff;  // SHINGLE base
const NEON_RED     = 0xff2d4a;  // METAL base
const NEON_VIOLET  = 0xc77dff;  // SLATE base (brighter)
const NEON_YELLOW  = 0xffea00;  // FRAMING wireframe
const NEON_ORANGE  = 0xff7a00;  // GUTTER system
const MATRIX       = NEON_YELLOW;   // back-compat alias
const ELECTRIC     = NEON_ORANGE;   // back-compat alias

const EDGE_COLOR = {
  ridge:  TEAL,
  valley: ORANGE,
  hip:    0x4cd6e0,
  eave:   SILVER,
  rake:   0x9bb0c0,
};

// ---------- math helpers ----------
function poly3dArea(verts) {
  let n = [0, 0, 0];
  const m = verts.length;
  for (let i = 0; i < m; i++) {
    const a = verts[i], b = verts[(i + 1) % m];
    n[0] += (a[1] - b[1]) * (a[2] + b[2]);
    n[1] += (a[2] - b[2]) * (a[0] + b[0]);
    n[2] += (a[0] - b[0]) * (a[1] + b[1]);
  }
  return 0.5 * Math.hypot(n[0], n[1], n[2]);
}
function fanTriangulate(verts) {
  const out = [];
  for (let i = 1; i < verts.length - 1; i++) out.push(...verts[0], ...verts[i], ...verts[i + 1]);
  return new Float32Array(out);
}
function projectToScreen(vec, camera, w, h) {
  const v = vec.clone().project(camera);
  return { x: (v.x * 0.5 + 0.5) * w, y: (1 - (v.y * 0.5 + 0.5)) * h, visible: v.z < 1 };
}
function facet_offset_normal(facet, d) {
  const n = facet.normal || [0, 1, 0];
  return new THREE.Vector3(n[0] * d, n[1] * d, n[2] * d);
}
function edgeLength(a, b) {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
}
function orientationColor(facet) {
  // dot with cardinal axes — north (+z), south (-z), east (+x), west (-x)
  const [nx, ny, nz] = facet.normal || [0, 1, 0];
  // front-facing (toward camera viewer / +z): cyan
  // rear-facing  (-z): warm sand/bronze
  // side-facing  (±x): silver-teal
  const dotZpos = nz;
  const dotZneg = -nz;
  const dotX = Math.abs(nx);
  const best = Math.max(dotZpos, dotZneg, dotX);
  if (best === dotZpos) return TEAL;
  if (best === dotZneg) return SAND;
  return STEEL;
}

// ---------- blueprint grid texture (one canvas per facet color tint) ----------
function makeBlueprintTexture(tintHex) {
  const size = 256;
  const c = document.createElement("canvas");
  c.width = c.height = size;
  const ctx = c.getContext("2d");
  // soft inner gradient
  const tint = new THREE.Color(tintHex);
  ctx.fillStyle = `rgba(${(tint.r*255)|0},${(tint.g*255)|0},${(tint.b*255)|0},0.18)`;
  ctx.fillRect(0, 0, size, size);
  // grid lines
  ctx.strokeStyle = `rgba(${(tint.r*255)|0},${(tint.g*255)|0},${(tint.b*255)|0},0.55)`;
  ctx.lineWidth = 1;
  for (let i = 0; i <= 16; i++) {
    const p = (i / 16) * size;
    ctx.beginPath(); ctx.moveTo(p, 0); ctx.lineTo(p, size); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, p); ctx.lineTo(size, p); ctx.stroke();
  }
  // heavier major axes
  ctx.strokeStyle = `rgba(${(tint.r*255)|0},${(tint.g*255)|0},${(tint.b*255)|0},0.85)`;
  ctx.lineWidth = 1.4;
  for (let i = 0; i <= 4; i++) {
    const p = (i / 4) * size;
    ctx.beginPath(); ctx.moveTo(p, 0); ctx.lineTo(p, size); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0, p); ctx.lineTo(size, p); ctx.stroke();
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(2, 2);
  return tex;
}

// cache textures by color so we don't burn GPU mem
const TEX_CACHE = {};
function blueprintTex(tintHex) {
  if (!TEX_CACHE[tintHex]) TEX_CACHE[tintHex] = makeBlueprintTexture(tintHex);
  return TEX_CACHE[tintHex];
}

// ---------- FINISH-SPECIFIC textures ----------
// Each generator returns a CanvasTexture sized 256x256 for tiled mapping on facets.

function makeShingleTexture() {
  // ASPHALT 3-TAB SHINGLE — dark base, neon BLUE detail lines only.
  // You read the material from the staggered 3-tab pattern + horizontal courses.
  const size = 512;
  const c = document.createElement("canvas"); c.width = c.height = size;
  const ctx = c.getContext("2d");
  // Dark interior fill with a hint of granular texture
  ctx.fillStyle = "#05080d"; ctx.fillRect(0, 0, size, size);
  for (let i = 0; i < 1400; i++) {
    const x = Math.random() * size, y = Math.random() * size;
    ctx.fillStyle = `rgba(40,70,110,${0.04 + Math.random() * 0.08})`;
    ctx.fillRect(x, y, 1, 1);
  }
  const rowH = size / 10;       // 10 courses
  const shingleW = size / 4;    // each "shingle" piece spans 4 across, contains 3 tabs
  const tabW = shingleW / 3;    // 3 tabs per shingle = standard 3-tab asphalt
  for (let r = 0; r < 10; r++) {
    const offset = (r % 2) * (shingleW / 2);
    const y = r * rowH;
    // BOLD horizontal course shadow + glowing cyan top edge of next course
    ctx.strokeStyle = "#0c1626";
    ctx.lineWidth = 6;
    ctx.beginPath(); ctx.moveTo(0, y + rowH); ctx.lineTo(size, y + rowH); ctx.stroke();
    // Glow line ABOVE the shadow — gives the "lifted" tab feel
    ctx.strokeStyle = "#5fc8ff";
    ctx.lineWidth = 2;
    ctx.shadowColor = "#1ea7ff";
    ctx.shadowBlur = 6;
    ctx.beginPath(); ctx.moveTo(0, y + rowH - 3); ctx.lineTo(size, y + rowH - 3); ctx.stroke();
    ctx.shadowBlur = 0;
    // Tab dividers — 3 short cuts per shingle (only top ~55% of row)
    for (let cIdx = -1; cIdx <= 5; cIdx++) {
      const sx = cIdx * shingleW + offset;
      for (let t = 1; t < 3; t++) {
        const cutX = sx + t * tabW;
        ctx.strokeStyle = "#1ea7ff";
        ctx.lineWidth = 2.4;
        ctx.shadowColor = "#5fc8ff";
        ctx.shadowBlur = 5;
        ctx.beginPath();
        ctx.moveTo(cutX, y + rowH * 0.45);
        ctx.lineTo(cutX, y + rowH - 2);
        ctx.stroke();
      }
      // Shingle-piece divider (full vertical between groups of 3 tabs)
      ctx.strokeStyle = "#3ab3ff";
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(sx, y + rowH * 0.15);
      ctx.lineTo(sx, y + rowH - 2);
      ctx.stroke();
    }
    ctx.shadowBlur = 0;
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(5, 5);
  tex.anisotropy = 4;
  return tex;
}

function makeMetalTexture() {
  // STANDING-SEAM METAL — dark base, neon RED seam lines + rivet dots only.
  const size = 512;
  const c = document.createElement("canvas"); c.width = c.height = size;
  const ctx = c.getContext("2d");
  // Dark interior fill w/ subtle brushed grain
  ctx.fillStyle = "#08030a"; ctx.fillRect(0, 0, size, size);
  for (let y = 0; y < size; y += 2) {
    ctx.fillStyle = `rgba(60,15,25,${0.08 + Math.random() * 0.05})`;
    ctx.fillRect(0, y, size, 1);
  }
  const panelW = size / 6;
  for (let i = 0; i <= 6; i++) {
    const x = i * panelW;
    // BOLD raised seam — black shadow + neon red core + outer halo
    ctx.shadowColor = "#ff2d4a";
    ctx.shadowBlur = 10;
    ctx.strokeStyle = "#ff2d4a";
    ctx.lineWidth = 3.5;
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, size); ctx.stroke();
    ctx.shadowBlur = 0;
    // Inner hot core on the seam
    ctx.strokeStyle = "#ffd0d4";
    ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, size); ctx.stroke();
    // Rivet dots along the seam every ~30px — hot halo + bright core
    for (let y = 14; y < size; y += 30) {
      ctx.fillStyle = "rgba(255,60,90,0.7)";
      ctx.beginPath(); ctx.arc(x, y, 5.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#fff5f6";
      ctx.beginPath(); ctx.arc(x, y, 2.4, 0, Math.PI * 2); ctx.fill();
    }
  }
  // Faint horizontal trim line every 1/3 of texture to suggest panel splice
  ctx.strokeStyle = "rgba(255,80,110,0.35)";
  ctx.lineWidth = 1;
  for (let y = size / 3; y < size; y += size / 3) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(size, y); ctx.stroke();
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(4, 4);
  tex.anisotropy = 4;
  return tex;
}

function makeSlateTexture() {
  // SLATE TILES — dark base, neon VIOLET scalloped outlines only.
  const size = 512;
  const c = document.createElement("canvas"); c.width = c.height = size;
  const ctx = c.getContext("2d");
  // Dark interior fill w/ violet noise
  ctx.fillStyle = "#06031a"; ctx.fillRect(0, 0, size, size);
  for (let i = 0; i < 1800; i++) {
    const x = Math.random() * size, y = Math.random() * size;
    ctx.fillStyle = `rgba(120,70,200,${0.04 + Math.random() * 0.08})`;
    ctx.fillRect(x, y, 1, 1);
  }
  const rowH = size / 12;
  const tileW = size / 6;
  for (let r = 0; r < 14; r++) {
    const yo = r * rowH;
    const offset = (r % 2) * (tileW / 2);
    for (let cIdx = -1; cIdx <= 7; cIdx++) {
      const x = cIdx * tileW + offset;
      // Neon violet scalloped outline — TOP scallop is bright (lit edge)
      ctx.shadowColor = "#c77dff";
      ctx.shadowBlur = 7;
      ctx.strokeStyle = "#e8c8ff";
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      ctx.moveTo(x, yo + rowH * 0.45);
      ctx.lineTo(x + tileW / 2, yo);
      ctx.lineTo(x + tileW, yo + rowH * 0.45);
      ctx.stroke();
      ctx.shadowBlur = 0;
      // Vertical tile edges in mid violet
      ctx.strokeStyle = "rgba(199,125,255,0.85)";
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(x, yo + rowH * 0.45);
      ctx.lineTo(x, yo + rowH);
      ctx.moveTo(x + tileW, yo + rowH * 0.45);
      ctx.lineTo(x + tileW, yo + rowH);
      ctx.stroke();
      // Bottom seam in dark
      ctx.strokeStyle = "rgba(0,0,0,0.85)";
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.moveTo(x, yo + rowH);
      ctx.lineTo(x + tileW, yo + rowH);
      ctx.stroke();
    }
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(4, 4);
  tex.anisotropy = 4;
  return tex;
}

let SHINGLE_TEX, METAL_TEX, SLATE_TEX;
function finishTex(kind) {
  if (kind === "shingle") return (SHINGLE_TEX ||= makeShingleTexture());
  if (kind === "metal")   return (METAL_TEX   ||= makeMetalTexture());
  if (kind === "slate")   return (SLATE_TEX   ||= makeSlateTexture());
  return null;
}

function buildFacetMesh(facet, hasAnomaly = false, finishKind = "shingle") {
  const v = facet.vertices;
  const positions = fanTriangulate(v);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  g.computeVertexNormals();
  // generate planar UVs by projecting vertices to the dominant plane
  const [nx, ny, nz] = facet.normal || [0, 1, 0];
  const ax = Math.abs(nx), ay = Math.abs(ny), az = Math.abs(nz);
  const uvs = [];
  const proj = (vt) => (ay >= ax && ay >= az) ? [vt[0], vt[2]]
                     : (ax >= az)              ? [vt[2], vt[1]]
                                               : [vt[0], vt[1]];
  // bounds
  const projVerts = v.map(proj);
  const xs = projVerts.map(p => p[0]), ys = projVerts.map(p => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const dx = (maxX - minX) || 1, dy = (maxY - minY) || 1;
  // fan triangulation matches positions ordering: v0, v1, v2, v0, v2, v3, ...
  for (let i = 1; i < v.length - 1; i++) {
    const idxs = [0, i, i + 1];
    idxs.forEach((k) => {
      const p = projVerts[k];
      uvs.push((p[0] - minX) / dx, (p[1] - minY) / dy);
    });
  }
  g.setAttribute("uv", new THREE.BufferAttribute(new Float32Array(uvs), 2));

  // Blueprint-engineering aesthetic: DARK interior fill, neon detail lines self-illuminate.
  // baseColor stays near-black so the dark canvas of each texture remains dark;
  // emissiveMap (same texture) lifts ONLY the painted line work to neon glow.
  const finishConfig = {
    shingle: { tex: finishTex("shingle"), baseColor: 0x0a1322, emissive: 0xffffff, accentHex: NEON_BLUE,   metalness: 0.30, roughness: 0.50, opacity: 0.99, emissiveIntensity: 1.45 },
    metal:   { tex: finishTex("metal"),   baseColor: 0x14060a, emissive: 0xffffff, accentHex: NEON_RED,    metalness: 0.85, roughness: 0.28, opacity: 0.99, emissiveIntensity: 1.55 },
    slate:   { tex: finishTex("slate"),   baseColor: 0x0c0524, emissive: 0xffffff, accentHex: NEON_VIOLET, metalness: 0.30, roughness: 0.55, opacity: 0.99, emissiveIntensity: 1.35 },
  };
  const cfg = finishConfig[finishKind] || finishConfig.shingle;
  const mat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(cfg.baseColor),
    map: cfg.tex,
    metalness: cfg.metalness,
    roughness: cfg.roughness,
    transparent: true,
    opacity: hasAnomaly ? Math.min(1, cfg.opacity) : cfg.opacity,
    side: THREE.DoubleSide,
    emissive: new THREE.Color(cfg.emissive),
    emissiveIntensity: cfg.emissiveIntensity,
    emissiveMap: cfg.tex,
  });
  const mesh = new THREE.Mesh(g, mat);

  // Bright neon perimeter outline in the layer's accent color — variable thickness
  // simulated via two stacked LineSegments (inner thin + outer wider feathered glow).
  const edgeGeo = new THREE.EdgesGeometry(g, 1);
  const accent = new THREE.Color(cfg.accentHex);
  const wfInner = new THREE.LineSegments(
    edgeGeo,
    new THREE.LineBasicMaterial({ color: accent, transparent: true, opacity: 0.95 }),
  );
  const wfGlow = new THREE.LineSegments(
    edgeGeo,
    new THREE.LineBasicMaterial({ color: accent, transparent: true, opacity: 0.35, blending: THREE.AdditiveBlending, depthWrite: false }),
  );
  wfGlow.scale.setScalar(1.004);
  const group = new THREE.Group();
  group.add(mesh); group.add(wfInner); group.add(wfGlow);
  group.userData.facet = facet;
  group.userData.finishKind = finishKind;
  return group;
}

function buildClassifiedEdge(edge) {
  const colorHex = EDGE_COLOR[edge.classification] || TEAL;
  const geom = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(...edge.a), new THREE.Vector3(...edge.b),
  ]);
  const mat = new THREE.LineBasicMaterial({
    color: colorHex,
    transparent: true,
    opacity: edge.classification === "valley" ? 0.98 : edge.classification === "ridge" ? 0.92 : 0.78,
    linewidth: 2,
  });
  const line = new THREE.Line(geom, mat);
  line.userData.edge = edge;
  return line;
}

function buildAnomalyPatch(anomaly, facet) {
  const verts = facet.vertices.map((v) => new THREE.Vector3(...v));
  const centroid = verts.reduce((acc, v) => acc.add(v), new THREE.Vector3()).multiplyScalar(1 / verts.length);
  const facetArea = poly3dArea(facet.vertices);
  const ratio = Math.max(0.08, Math.min(0.5, anomaly.area_affected_sf / Math.max(facetArea, 1)));
  const shrunk = verts.map((v) => centroid.clone().lerp(v, Math.sqrt(ratio)));
  const positions = fanTriangulate(shrunk.map((p) => [p.x, p.y, p.z]));
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  g.computeVertexNormals();
  // radial UVs for the heat texture
  const uvs = [];
  for (let i = 1; i < shrunk.length - 1; i++) {
    const idxs = [0, i, i + 1];
    idxs.forEach((k) => uvs.push(k === 0 ? 0.5 : 0.5 + Math.cos(k) * 0.5, k === 0 ? 0.5 : 0.5 + Math.sin(k) * 0.5));
  }
  g.setAttribute("uv", new THREE.BufferAttribute(new Float32Array(uvs), 2));

  const mat = new THREE.MeshBasicMaterial({
    color: ORANGE,
    transparent: true,
    opacity: 0.72,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(g, mat);
  mesh.position.copy(facet_offset_normal(facet, 0.05));
  const wf = new THREE.LineSegments(
    new THREE.EdgesGeometry(g, 1),
    new THREE.LineBasicMaterial({ color: ORANGE, transparent: true, opacity: 0.98 }),
  );
  wf.position.copy(mesh.position);
  const group = new THREE.Group();
  group.add(mesh); group.add(wf);
  group.userData.anomaly = anomaly;
  group.userData.labelTarget = centroid.clone().add(facet_offset_normal(facet, 0.08));
  return group;
}

export default function RoofModel3D({
  telemetry,
  anomalies = [],
  scanning = false,
  autoRotate = true,
  height = 460,
  highlightAnomalyId = null,
  onSelectAnomaly,
  showLabels = true,
  showDimensions = true,
  // NEW BEES Layer Visibility Constraints (mutually exclusive primary layers + secondary gutter overlay)
  primaryLayer = "shingle",  // "framing" | "shingle" | "metal" | "slate"
  showGutters = true,
  // legacy prop (backward-compat) — if `layers` is provided, derive primaryLayer + showGutters from it
  layers = null,
}) {
  // ----- Back-compat shim: translate legacy {roofing, framing, gutters} to BEES contract -----
  const resolvedPrimary = layers
    ? (layers.framing ? "framing" : (layers.roofing ? "shingle" : "framing"))
    : primaryLayer;
  const resolvedGutters = layers ? !!layers.gutters : !!showGutters;
  const mountRef = useRef(null);
  const stateRef = useRef({});
  const [labelPositions, setLabelPositions] = useState([]);
  const [dimensionPositions, setDimensionPositions] = useState([]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const facets = telemetry?.facets || [];
    const edges  = telemetry?.edges  || [];
    if (facets.length === 0) return;

    const anomalyFacetSet = new Set((anomalies || []).map((a) => a.facet_id));

    const w = mount.clientWidth || 800;
    const h = mount.clientHeight || height;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(BG);
    scene.fog = new THREE.Fog(BG, 90, 300);

    // bbox + camera framing
    const bbox = new THREE.Box3();
    facets.forEach((f) => f.vertices.forEach((v) => bbox.expandByPoint(new THREE.Vector3(...v))));
    const centre = new THREE.Vector3(); bbox.getCenter(centre);
    const size = new THREE.Vector3(); bbox.getSize(size);
    const span = Math.max(size.x, size.z) || 30;

    const camera = new THREE.PerspectiveCamera(28, w / h, 0.1, 2000);
    camera.position.set(centre.x + span * 0.95, span * 1.4, centre.z + span * 1.15);
    camera.lookAt(centre);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(w, h);
    renderer.setClearColor(BG, 1);
    mount.appendChild(renderer.domElement);

    // -------- ambient lighting (tactical console) --------
    scene.add(new THREE.AmbientLight(0xffffff, 0.42));
    const key = new THREE.PointLight(TEAL, 1300, 700);
    key.position.set(centre.x + span * 0.9, span * 1.6, centre.z + span * 0.9);
    scene.add(key);
    const fill = new THREE.PointLight(ORANGE, 380, 600);
    fill.position.set(centre.x - span * 1.1, span * 0.55, centre.z - span * 1.1);
    scene.add(fill);
    const rim = new THREE.DirectionalLight(0xffffff, 0.3);
    rim.position.set(0, 1, 0); scene.add(rim);

    // -------- ground plane with radial glow --------
    const groundSize = span * 5;
    const groundCanvas = document.createElement("canvas");
    groundCanvas.width = groundCanvas.height = 512;
    const gctx = groundCanvas.getContext("2d");
    const grad = gctx.createRadialGradient(256, 256, 30, 256, 256, 256);
    grad.addColorStop(0,   "rgba(0,240,255,0.32)");
    grad.addColorStop(0.4, "rgba(0,240,255,0.08)");
    grad.addColorStop(1,   "rgba(0,0,0,0)");
    gctx.fillStyle = grad; gctx.fillRect(0, 0, 512, 512);
    const groundTex = new THREE.CanvasTexture(groundCanvas);
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(groundSize, groundSize),
      new THREE.MeshBasicMaterial({ map: groundTex, transparent: true, opacity: 0.85, depthWrite: false }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(centre.x, bbox.min.y - 0.8, centre.z);
    scene.add(ground);

    const grid = new THREE.GridHelper(groundSize, 80, TEAL, 0x101824);
    grid.material.transparent = true; grid.material.opacity = 0.35;
    grid.position.set(centre.x, bbox.min.y - 0.78, centre.z);
    scene.add(grid);

    // -------- facets --------
    const facetGroups = facets.map((f) => {
      const finishKind = resolvedPrimary === "framing" ? "shingle" : resolvedPrimary;
      const g = buildFacetMesh(f, anomalyFacetSet.has(f.id), finishKind);
      // Framing-mode hides finish meshes entirely
      g.visible = resolvedPrimary !== "framing";
      scene.add(g);
      return g;
    });

    // -------- classified edges (drawn ABOVE facets) --------
    const edgeGroups = edges.map((e) => {
      const line = buildClassifiedEdge(e);
      scene.add(line);
      return { mesh: line, edge: e };
    });

    // -------- anomalies --------
    const facetById = Object.fromEntries(facets.map((f) => [f.id, f]));
    const anomalyGroups = anomalies.map((a) => {
      const f = facetById[a.facet_id]; if (!f) return null;
      const g = buildAnomalyPatch(a, f); scene.add(g); return g;
    }).filter(Boolean);

    // -------- FRAMING LAYER — NEON YELLOW wireframe, variable line thickness --------
    const framingGroup = new THREE.Group();
    framingGroup.visible = resolvedPrimary === "framing";
    const tele = telemetry || {};
    const framing = tele.framing || {};
    const yellowCore  = new THREE.Color(NEON_YELLOW);
    const yellowGlow  = new THREE.Color(0xfff79a);
    // Major rafters: render as thin tubes for true thickness (THREE LineWidth is unreliable in WebGL)
    (framing.rafters || []).forEach((r, idx) => {
      const a = new THREE.Vector3(...r.a);
      const b = new THREE.Vector3(...r.b);
      const path = new THREE.LineCurve3(a, b);
      // Every 3rd rafter is a heavier load-bearing member → thicker tube
      const heavy = idx % 3 === 0;
      const radius = heavy ? 0.085 : 0.045;
      const tube = new THREE.TubeGeometry(path, 1, radius, 6, false);
      const mat = new THREE.MeshStandardMaterial({
        color: yellowCore, emissive: yellowCore,
        emissiveIntensity: heavy ? 0.95 : 0.75,
        metalness: 0.3, roughness: 0.4,
        transparent: true, opacity: 0.95,
      });
      framingGroup.add(new THREE.Mesh(tube, mat));
      // Additive feathered glow line over the tube
      const glowGeom = new THREE.BufferGeometry().setFromPoints([a, b]);
      framingGroup.add(new THREE.Line(glowGeom, new THREE.LineBasicMaterial({
        color: yellowGlow, transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending, depthWrite: false,
      })));
    });
    // Sub-fascia: heavy tubes along each eave — primary structural edge
    (framing.sub_fascia || []).forEach((s) => {
      const a = new THREE.Vector3(s.a[0], s.a[1] - 0.5, s.a[2]);
      const b = new THREE.Vector3(s.b[0], s.b[1] - 0.5, s.b[2]);
      const path = new THREE.LineCurve3(a, b);
      const tube = new THREE.TubeGeometry(path, 1, 0.12, 8, false);
      framingGroup.add(new THREE.Mesh(tube, new THREE.MeshStandardMaterial({
        color: yellowCore, emissive: yellowCore, emissiveIntensity: 1.0,
        metalness: 0.4, roughness: 0.3, transparent: true, opacity: 0.97,
      })));
    });
    scene.add(framingGroup);

    // -------- GUTTERS LAYER — NEON ORANGE thick tube + bright downspouts --------
    const gutterGroup = new THREE.Group();
    gutterGroup.visible = !!resolvedGutters;
    const gutters = tele.gutters || {};
    const orangeCore = new THREE.Color(NEON_ORANGE);
    const orangeHot  = new THREE.Color(0xffa64d);
    (gutters.polylines || []).forEach((p) => {
      const a = new THREE.Vector3(p.a[0], p.a[1] - 0.6, p.a[2]);
      const b = new THREE.Vector3(p.b[0], p.b[1] - 0.6, p.b[2]);
      const path = new THREE.LineCurve3(a, b);
      // Thick orange gutter
      const tube = new THREE.TubeGeometry(path, 1, 0.32, 10, false);
      const mat = new THREE.MeshStandardMaterial({
        color: orangeCore, emissive: orangeCore, emissiveIntensity: 0.95,
        metalness: 0.55, roughness: 0.25,
        transparent: true, opacity: 0.97,
      });
      gutterGroup.add(new THREE.Mesh(tube, mat));
      // Additive feathered glow on top
      const glowGeom = new THREE.BufferGeometry().setFromPoints([a, b]);
      gutterGroup.add(new THREE.Line(glowGeom, new THREE.LineBasicMaterial({
        color: orangeHot, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false,
      })));
      // Hanger studs every ~2 ft
      const len = a.distanceTo(b);
      const n = Math.max(2, Math.floor(len / 2));
      for (let i = 0; i <= n; i++) {
        const t = i / n;
        const pos = a.clone().lerp(b, t);
        const dot = new THREE.Mesh(
          new THREE.SphereGeometry(0.14, 8, 8),
          new THREE.MeshStandardMaterial({
            color: 0xfff0d6, emissive: 0xffb877, emissiveIntensity: 1.0,
            transparent: true, opacity: 0.95,
          }),
        );
        dot.position.copy(pos);
        gutterGroup.add(dot);
      }
    });
    (gutters.downspouts || []).forEach((d) => {
      const top = new THREE.Vector3(d.drop[0], d.drop[1] - 0.6, d.drop[2]);
      const bot = new THREE.Vector3(d.ground[0], d.ground[1], d.ground[2]);
      const path = new THREE.LineCurve3(top, bot);
      const tube = new THREE.TubeGeometry(path, 1, 0.22, 8, false);
      gutterGroup.add(new THREE.Mesh(tube, new THREE.MeshStandardMaterial({
        color: orangeCore, emissive: orangeCore, emissiveIntensity: 0.9,
        metalness: 0.55, roughness: 0.3, transparent: true, opacity: 0.95,
      })));
      // Splash elbow at the bottom
      const elbow = new THREE.Mesh(
        new THREE.TorusGeometry(0.28, 0.1, 6, 12, Math.PI),
        new THREE.MeshStandardMaterial({
          color: orangeCore, emissive: orangeCore, emissiveIntensity: 0.9,
          metalness: 0.55, roughness: 0.3, transparent: true, opacity: 0.95,
        }),
      );
      elbow.position.copy(bot);
      elbow.rotation.x = Math.PI / 2;
      gutterGroup.add(elbow);
    });
    scene.add(gutterGroup);

    // -------- scanner sweep --------
    const scanner = new THREE.Mesh(
      new THREE.PlaneGeometry(span * 3, span * 3),
      new THREE.MeshBasicMaterial({ color: TEAL, transparent: true, opacity: 0.4, side: THREE.DoubleSide }),
    );
    scanner.rotation.x = Math.PI / 2;
    scanner.position.set(centre.x, bbox.min.y - 1, centre.z);
    scanner.visible = scanning;
    scene.add(scanner);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.copy(centre);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = true;
    controls.minDistance = span * 0.45;
    controls.maxDistance = span * 5;
    controls.autoRotate = autoRotate && !scanning;
    controls.autoRotateSpeed = 0.45;

    let raf;
    const start = performance.now();
    // Camera intro — 5s slow recon sweep before user-control resumes
    const introDuration = 5000;
    const introStartAngle = Math.atan2(camera.position.x - centre.x, camera.position.z - centre.z);
    const introRadius = Math.hypot(camera.position.x - centre.x, camera.position.z - centre.z);
    const introY = camera.position.y;
    let introActive = true;
    controls.enabled = false;

    const tick = () => {
      const t = (performance.now() - start) / 1000;
      anomalyGroups.forEach((g) => {
        const op = 0.6 + Math.sin(t * 3 + (g.userData.anomaly?.confidence || 0) * 10) * 0.22;
        g.children[0].material.opacity = op;
        g.children[1].material.opacity = 0.75 + Math.sin(t * 4) * 0.22;
      });
      if (scanning) {
        scanner.visible = true;
        const cycle = (t % 4) / 4;
        scanner.position.y = bbox.min.y - 1 + cycle * (span * 1.5);
        scanner.material.opacity = 0.42 * (1 - cycle);
      } else { scanner.visible = false; }
      // === intro camera sweep ===
      if (introActive) {
        const elapsed = performance.now() - start;
        const u = Math.min(1, elapsed / introDuration);
        const ease = 1 - Math.pow(1 - u, 3); // ease-out cubic
        const sweep = ease * Math.PI * 1.4;  // ~250° arc
        const angle = introStartAngle + sweep;
        camera.position.set(
          centre.x + Math.sin(angle) * introRadius,
          introY + Math.sin(u * Math.PI) * span * 0.35,  // gentle vertical arc
          centre.z + Math.cos(angle) * introRadius,
        );
        camera.lookAt(centre);
        if (u >= 1) {
          introActive = false;
          controls.enabled = true;
          controls.update();
        }
      } else {
        controls.update();
      }
      renderer.render(scene, camera);

      // Update HTML overlay positions every ~3 frames
      if (Math.floor(t * 20) % 2 === 0) {
        if (showLabels) {
          const positions = anomalyGroups.map((g) => {
            const sp = projectToScreen(g.userData.labelTarget, camera, w, h);
            return { anomaly: g.userData.anomaly, x: sp.x, y: sp.y, visible: sp.visible };
          });
          setLabelPositions(positions);
        }
        if (showDimensions) {
          // pick the longest edges from each classification (max 8) to label
          const labeled = [];
          ["ridge", "valley", "hip", "eave"].forEach((cls) => {
            const eOfCls = edgeGroups.filter((e) => e.edge.classification === cls);
            eOfCls.sort((a, b) => edgeLength(b.edge.a, b.edge.b) - edgeLength(a.edge.a, a.edge.b));
            eOfCls.slice(0, 2).forEach(({ edge }) => labeled.push(edge));
          });
          const dimPos = labeled.map((edge) => {
            const a = new THREE.Vector3(...edge.a);
            const b = new THREE.Vector3(...edge.b);
            const mid = a.clone().lerp(b, 0.5);
            const sp = projectToScreen(mid, camera, w, h);
            return {
              cls: edge.classification,
              len: edgeLength(edge.a, edge.b).toFixed(3),
              x: sp.x, y: sp.y, visible: sp.visible,
            };
          });
          setDimensionPositions(dimPos);
        }
      }
      raf = requestAnimationFrame(tick);
    };
    tick();

    const onResize = () => {
      const nw = mount.clientWidth, nh = mount.clientHeight || height;
      camera.aspect = nw / nh; camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };
    window.addEventListener("resize", onResize);

    const ray = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const onClick = (ev) => {
      if (!onSelectAnomaly) return;
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
      ray.setFromCamera(mouse, camera);
      const meshes = anomalyGroups.map((g) => g.children[0]);
      const hits = ray.intersectObjects(meshes, false);
      if (hits.length > 0) onSelectAnomaly(hits[0].object.parent.userData.anomaly);
    };
    renderer.domElement.addEventListener("click", onClick);

    stateRef.current = { scene, renderer, controls, scanner, anomalyGroups, facetGroups, framingGroup, gutterGroup };

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      renderer.domElement.removeEventListener("click", onClick);
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) mount.removeChild(renderer.domElement);
      scene.traverse((obj) => {
        obj.geometry?.dispose?.();
        if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose?.());
        else obj.material?.dispose?.();
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [telemetry?.style, telemetry?.scale, anomalies.length, height, resolvedPrimary]);

  useEffect(() => {
    const { controls, scanner } = stateRef.current;
    if (controls) controls.autoRotate = autoRotate && !scanning;
    if (scanner) scanner.visible = scanning;
  }, [scanning, autoRotate]);

  useEffect(() => {
    const { framingGroup, gutterGroup, facetGroups } = stateRef.current;
    // BEES Layer Visibility Rules:
    //   - resolvedPrimary === "framing":  facets HIDDEN, framing visible
    //   - resolvedPrimary === any finish: facets VISIBLE (texture chosen at mount), framing HIDDEN
    //   - gutters: independent secondary
    if (framingGroup) framingGroup.visible = resolvedPrimary === "framing";
    if (gutterGroup)  gutterGroup.visible  = !!resolvedGutters;
    if (facetGroups)  facetGroups.forEach((g) => {
      g.visible = resolvedPrimary !== "framing";
    });
  }, [resolvedPrimary, resolvedGutters]);

  useEffect(() => {
    const { anomalyGroups } = stateRef.current; if (!anomalyGroups) return;
    anomalyGroups.forEach((g) => {
      const isSel = g.userData.anomaly?.id === highlightAnomalyId;
      g.children[1].material.color.set(isSel ? 0xffd37a : ORANGE);
      g.children[0].scale.setScalar(isSel ? 1.16 : 1);
    });
  }, [highlightAnomalyId]);

  const dimColor = (cls) => cls === "valley" ? "text-plasma" : cls === "ridge" || cls === "hip" ? "text-teal" : "text-silver";

  return (
    <div className="relative w-full" style={{ height }}>
      <div ref={mountRef} className="absolute inset-0" data-testid="roof-3d-canvas" />

      {/* Dimension callouts */}
      {showDimensions && dimensionPositions.map((d, i) => d.visible && (
        <div
          key={i}
          className={`absolute pointer-events-none font-mono text-[10px] tracking-widest ${dimColor(d.cls)}`}
          style={{
            left: d.x, top: d.y,
            transform: "translate(-50%, -120%)",
            textShadow: d.cls === "valley" ? "0 0 6px rgba(255,85,0,0.85)" : "0 0 6px rgba(0,240,255,0.65)",
          }}
        >
          {d.len}
        </div>
      ))}

      {/* Anomaly leader labels */}
      {showLabels && labelPositions.map((l, i) => l.visible && (
        <div key={l.anomaly.id + i} className="absolute pointer-events-none" style={{ left: l.x + 14, top: l.y - 12 }}>
          <div className={`font-mono text-[10px] uppercase tracking-widest px-2 py-1 border ${l.anomaly.id === highlightAnomalyId ? "border-plasma text-plasma" : "border-[#00F0FF]/40 text-teal"}`} style={{ background: "rgba(11,15,25,0.88)", textShadow: l.anomaly.id === highlightAnomalyId ? "0 0 6px rgba(255,85,0,0.85)" : "0 0 6px rgba(0,240,255,0.55)" }}>
            Anomaly ID: <span className="text-silver">{l.anomaly.id}</span>
          </div>
        </div>
      ))}

      {/* Top-left STRATEX Vision header */}
      <div className="absolute top-3 left-3 font-mono text-[10px] tracking-widest uppercase text-teal flex items-center gap-2 pointer-events-none" style={{ textShadow: "0 0 6px rgba(0,240,255,0.6)" }}>
        <span className="led led-teal" /> STRATEX™ VISION • ADVANCED DIAGNOSTICS
      </div>

      {/* Help text */}
      <div className="absolute bottom-3 right-3 font-mono text-[10px] tracking-widest uppercase text-muted-hud pointer-events-none">
        DRAG TO ORBIT • SCROLL TO ZOOM • CLICK ANOMALY
      </div>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex flex-wrap gap-3 font-mono text-[10px] tracking-widest uppercase pointer-events-none">
        <span className="flex items-center gap-1 text-teal"><span className="w-3 h-[2px] bg-[#00F0FF]"/> Ridge</span>
        <span className="flex items-center gap-1 text-plasma"><span className="w-3 h-[2px] bg-[#FF5500]"/> Valley</span>
        <span className="flex items-center gap-1" style={{color:"#4cd6e0"}}><span className="w-3 h-[2px]" style={{background:"#4cd6e0"}}/> Hip</span>
        <span className="flex items-center gap-1 text-silver"><span className="w-3 h-[2px] bg-[#c7d4dd]"/> Eave</span>
      </div>
    </div>
  );
}
