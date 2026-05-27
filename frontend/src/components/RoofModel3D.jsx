import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";

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
// Multi-Agent Expert Panel ratified palette — unified blue+orange architectural neon
const NEON_CYAN_BLUE = 0x1ea7ff;   // SHINGLE detail lines
const NEON_CYAN      = 0x00f0ff;   // METAL standing-seam lines + Framing rafters
const NEON_VIOLET    = 0xc77dff;   // SLATE scallop edges
const NEON_YELLOW    = 0xffea00;   // (reserved)
const NEON_ORANGE    = 0xff7a00;   // GUTTER system + Sub-fascia accent
const MATRIX         = NEON_CYAN;  // back-compat alias (framing)
const ELECTRIC       = NEON_ORANGE;// back-compat alias (gutter)

// Per-agent-3 rule C1: each material texture covers REPEAT_FT × REPEAT_FT
// of real-world roof surface (1 unit = 1 ft in topology). Tweaking this
// changes apparent shingle/seam scale uniformly.
const REPEAT_FT = {
  shingle: 4.0,   // 4 ft of texture → 4 courses × 5" exposure ≈ 20", matches 3-tab proportions
  metal:   3.0,   // 3 ft → 2 panels at 18" each
  slate:   3.5,   // 3.5 ft → ~3.5 courses
};

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
  // ASPHALT 3-TAB SHINGLE per Agent 2 / R1 — RAZOR-SHARP CAD aesthetic.
  // No blur halos: crisp 1-2 px neon cyan-blue lines on a pitch-black field.
  // Each course = 5" exposure. 4 courses per texture tile = 20"; texture tile = 4 ft slope.
  const size = 512;
  const c = document.createElement("canvas"); c.width = c.height = size;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#02060c"; ctx.fillRect(0, 0, size, size);
  // Faint granular asphalt noise — keeps interior from looking flat-black
  for (let i = 0; i < 900; i++) {
    const x = Math.random() * size, y = Math.random() * size;
    ctx.fillStyle = `rgba(30,80,130,${0.025 + Math.random() * 0.04})`;
    ctx.fillRect(x, y, 1, 1);
  }
  const courses = 4;
  const rowH = size / courses;
  const shinglesPerRow = 3;
  const shingleW = size / shinglesPerRow;
  const tabW = shingleW / 3;
  for (let r = 0; r < courses; r++) {
    const y = r * rowH;
    const offset = (r % 2) * (tabW * 1.5);
    // Course separator — single crisp 2px neon line, no glow halo
    ctx.strokeStyle = "#1ea7ff";
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(0, y + rowH); ctx.lineTo(size, y + rowH); ctx.stroke();
    // Per-tab vertical cuts — hairline 1.2px, brighter than course separator
    for (let cIdx = -1; cIdx <= shinglesPerRow + 1; cIdx++) {
      const sx = cIdx * shingleW + offset;
      for (let t = 1; t < 3; t++) {
        const cutX = sx + t * tabW;
        ctx.strokeStyle = "#7fd4ff";
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(cutX, y + rowH * 0.40);
        ctx.lineTo(cutX, y + rowH - 2);
        ctx.stroke();
      }
    }
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(1, 1);
  tex.anisotropy = 8;
  return tex;
}

function makeMetalTexture() {
  // STANDING-SEAM METAL per Agent 2 / R3 — RAZOR-SHARP CAD aesthetic.
  // Single crisp seam stroke + small bright dot rivets at clip points. No blur.
  const size = 512;
  const c = document.createElement("canvas"); c.width = c.height = size;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#020912"; ctx.fillRect(0, 0, size, size);
  // Vertical brushed grain — extremely faint
  for (let x = 0; x < size; x += 3) {
    ctx.fillStyle = `rgba(15,50,90,${0.04 + Math.random() * 0.025})`;
    ctx.fillRect(x, 0, 1, size);
  }
  const panels = 2;
  const panelW = size / panels;
  for (let i = 0; i <= panels; i++) {
    const x = i * panelW;
    // Seam — single crisp 2.4px neon cyan line
    ctx.strokeStyle = "#00f0ff";
    ctx.lineWidth = 2.4;
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, size); ctx.stroke();
    // Clip/rivet dots — small bright cores, no halo
    const dotsPerTile = 3;
    for (let d = 0; d < dotsPerTile; d++) {
      const dy = (d + 0.5) * (size / dotsPerTile);
      ctx.fillStyle = "#e8fbff";
      ctx.beginPath(); ctx.arc(x, dy, 2.4, 0, Math.PI * 2); ctx.fill();
    }
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(1, 1);
  tex.anisotropy = 8;
  return tex;
}

function makeSlateTexture() {
  // SLATE per Agent 2 / R4 — RAZOR-SHARP CAD aesthetic. Crisp scallop outlines.
  const size = 512;
  const c = document.createElement("canvas"); c.width = c.height = size;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#070420"; ctx.fillRect(0, 0, size, size);
  for (let i = 0; i < 1100; i++) {
    const x = Math.random() * size, y = Math.random() * size;
    ctx.fillStyle = `rgba(120,70,200,${0.03 + Math.random() * 0.06})`;
    ctx.fillRect(x, y, 1, 1);
  }
  const courses = 3;
  const rowH = size / courses;
  const tilesPerRow = 3;
  const tileW = size / tilesPerRow;
  for (let r = 0; r < courses; r++) {
    const yo = r * rowH;
    const offset = (r % 2) * (tileW / 2);
    for (let cIdx = -1; cIdx <= tilesPerRow + 1; cIdx++) {
      const x = cIdx * tileW + offset;
      // Scalloped top edge — single 2px violet stroke
      ctx.strokeStyle = "#c77dff";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x, yo + rowH * 0.45);
      ctx.lineTo(x + tileW / 2, yo);
      ctx.lineTo(x + tileW, yo + rowH * 0.45);
      ctx.stroke();
      // Vertical tile edges — hairline 1.2px, dimmer violet
      ctx.strokeStyle = "rgba(160,100,220,0.85)";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(x, yo + rowH * 0.45); ctx.lineTo(x, yo + rowH);
      ctx.moveTo(x + tileW, yo + rowH * 0.45); ctx.lineTo(x + tileW, yo + rowH);
      ctx.stroke();
      // Bottom course separator — same violet hairline
      ctx.strokeStyle = "rgba(160,100,220,0.6)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, yo + rowH); ctx.lineTo(x + tileW, yo + rowH);
      ctx.stroke();
    }
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(1, 1);
  tex.anisotropy = 8;
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

  // ---- Agent 3 / Rule C1: slope-aligned UV basis ----
  // Build (U, V) frame on the facet plane:
  //   N = facet normal
  //   U = horizontal (along eave) = normalize(cross(N, worldUp))
  //   V = up the slope             = normalize(cross(U, N))
  // Then UVs are world-space distances along (U, V) divided by REPEAT_FT, so the
  // texture scale is constant across all facets (3-tab tabs always read at 12").
  const [nx, ny, nz] = facet.normal || [0, 1, 0];
  const N = new THREE.Vector3(nx, ny, nz).normalize();
  const worldUp = new THREE.Vector3(0, 1, 0);
  let U = new THREE.Vector3().crossVectors(N, worldUp);
  if (U.lengthSq() < 1e-4) U.set(1, 0, 0);   // horizontal facet (e.g. chimney top) fallback
  else U.normalize();
  const V = new THREE.Vector3().crossVectors(U, N).normalize();
  const repeatFt = REPEAT_FT[finishKind] || 4.0;
  const uvs = [];
  // fan triangulation: v0, v_i, v_{i+1} for i in [1, n-2]
  for (let i = 1; i < v.length - 1; i++) {
    [0, i, i + 1].forEach((k) => {
      const p = new THREE.Vector3(v[k][0], v[k][1], v[k][2]);
      uvs.push(p.dot(U) / repeatFt, p.dot(V) / repeatFt);
    });
  }
  g.setAttribute("uv", new THREE.BufferAttribute(new Float32Array(uvs), 2));

  // CAD-blueprint aesthetic: pitch-black interior, RAZOR-SHARP neon lines on top.
  // emissiveMap routes only the painted line work; emissiveIntensity is tuned so
  // the lines read as saturated neon without bleeding into the dark background.
  const finishConfig = {
    shingle: { tex: finishTex("shingle"), baseColor: 0x040b14, emissive: 0xffffff, accentHex: NEON_CYAN_BLUE, metalness: 0.25, roughness: 0.55, opacity: 0.99, emissiveIntensity: 0.85 },
    metal:   { tex: finishTex("metal"),   baseColor: 0x030812, emissive: 0xffffff, accentHex: NEON_CYAN,      metalness: 0.85, roughness: 0.30, opacity: 0.99, emissiveIntensity: 0.95 },
    slate:   { tex: finishTex("slate"),   baseColor: 0x070420, emissive: 0xffffff, accentHex: NEON_VIOLET,    metalness: 0.30, roughness: 0.55, opacity: 0.99, emissiveIntensity: 0.80 },
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

  // Per-facet perimeter — single crisp line in the layer accent color. No halo.
  // (top-CAD aesthetic: no glow, just a saturated 1-2px stroke).
  const edgeGeo = new THREE.EdgesGeometry(g, 1);
  const accent = new THREE.Color(cfg.accentHex);
  const wfInner = new THREE.LineSegments(
    edgeGeo,
    new THREE.LineBasicMaterial({ color: accent, transparent: true, opacity: 0.95 }),
  );
  const group = new THREE.Group();
  group.add(mesh); group.add(wfInner);
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
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    mount.appendChild(renderer.domElement);

    // ----- POST-PROCESSING -----
    // Top-tier CAD neon work (Jarvis HUD, Forma renderings) is RAZOR-SHARP lines —
    // never blurred bloom haze. We keep a composer + RenderPass for resize symmetry,
    // but bloom strength is intentionally near-zero. The "glow" comes from saturated
    // line colors + a 1px additive halo on each edge (see buildFacetMesh).
    const composer = new EffectComposer(renderer);
    composer.setPixelRatio(window.devicePixelRatio);
    composer.setSize(w, h);
    const renderPass = new RenderPass(scene, camera);
    composer.addPass(renderPass);
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(w, h),
      0.18,   // strength — subtle lift on only the BRIGHTEST highlights
      0.30,   // radius   — tight, almost imperceptible
      0.75,   // threshold — only fully-saturated neon detail lines bloom at all
    );
    composer.addPass(bloomPass);
    composer.addPass(new OutputPass());

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
    grad.addColorStop(0,   "rgba(0,240,255,0.14)");
    grad.addColorStop(0.4, "rgba(0,240,255,0.04)");
    grad.addColorStop(1,   "rgba(0,0,0,0)");
    gctx.fillStyle = grad; gctx.fillRect(0, 0, 512, 512);
    const groundTex = new THREE.CanvasTexture(groundCanvas);
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(groundSize, groundSize),
      new THREE.MeshBasicMaterial({ map: groundTex, transparent: true, opacity: 0.7, depthWrite: false }),
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

    // -------- FRAMING LAYER per Agent 1 — cyan rafters/ridge boards + ORANGE sub-fascia --------
    const framingGroup = new THREE.Group();
    framingGroup.visible = resolvedPrimary === "framing";
    const tele = telemetry || {};
    const framing = tele.framing || {};
    const cyanCore  = new THREE.Color(NEON_CYAN);
    const cyanGlow  = new THREE.Color(0xb0f0ff);
    const orangeCore = new THREE.Color(NEON_ORANGE);
    const orangeHot  = new THREE.Color(0xffb877);
    // Rafters: tube geometry, every 3rd is a heavier doubled trimmer (Agent 1 / F3)
    (framing.rafters || []).forEach((r, idx) => {
      const a = new THREE.Vector3(...r.a);
      const b = new THREE.Vector3(...r.b);
      const path = new THREE.LineCurve3(a, b);
      const heavy = idx % 3 === 0;
      const radius = heavy ? 0.06 : 0.032;
      const tube = new THREE.TubeGeometry(path, 1, radius, 6, false);
      const mat = new THREE.MeshStandardMaterial({
        color: cyanCore, emissive: cyanCore,
        emissiveIntensity: heavy ? 0.55 : 0.42,
        metalness: 0.3, roughness: 0.45,
        transparent: true, opacity: 0.96,
      });
      framingGroup.add(new THREE.Mesh(tube, mat));
    });
    // Sub-fascia: ORANGE heavy tubes along every eave (Agent 1 / F4 + F6, Agent 4 / G6)
    (framing.sub_fascia || []).forEach((s) => {
      const a = new THREE.Vector3(s.a[0], s.a[1] - 0.5, s.a[2]);
      const b = new THREE.Vector3(s.b[0], s.b[1] - 0.5, s.b[2]);
      const path = new THREE.LineCurve3(a, b);
      const tube = new THREE.TubeGeometry(path, 1, 0.10, 8, false);
      framingGroup.add(new THREE.Mesh(tube, new THREE.MeshStandardMaterial({
        color: orangeCore, emissive: orangeCore, emissiveIntensity: 0.65,
        metalness: 0.4, roughness: 0.3, transparent: true, opacity: 0.98,
      })));
    });
    scene.add(framingGroup);

    // -------- GUTTERS LAYER per Agent 4 — neon ORANGE continuous trough + downspouts + elbows --------
    const gutterGroup = new THREE.Group();
    gutterGroup.visible = !!resolvedGutters;
    const gutters = tele.gutters || {};
    (gutters.polylines || []).forEach((p) => {
      const a = new THREE.Vector3(p.a[0], p.a[1] - 0.6, p.a[2]);
      const b = new THREE.Vector3(p.b[0], p.b[1] - 0.6, p.b[2]);
      const path = new THREE.LineCurve3(a, b);
      // K-style gutter — clean orange tube, no glow halo (Agent 4 / G2)
      const tube = new THREE.TubeGeometry(path, 1, 0.22, 10, false);
      gutterGroup.add(new THREE.Mesh(tube, new THREE.MeshStandardMaterial({
        color: orangeCore, emissive: orangeCore, emissiveIntensity: 0.55,
        metalness: 0.55, roughness: 0.28,
        transparent: true, opacity: 0.98,
      })));
      // Hanger studs every ~2 ft (Agent 4 / G5)
      const len = a.distanceTo(b);
      const n = Math.max(2, Math.floor(len / 2));
      for (let i = 0; i <= n; i++) {
        const t = i / n;
        const pos = a.clone().lerp(b, t);
        const dot = new THREE.Mesh(
          new THREE.SphereGeometry(0.11, 8, 8),
          new THREE.MeshStandardMaterial({
            color: 0xffd6a8, emissive: 0xff9447, emissiveIntensity: 0.55,
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
      const tube = new THREE.TubeGeometry(path, 1, 0.18, 8, false);
      gutterGroup.add(new THREE.Mesh(tube, new THREE.MeshStandardMaterial({
        color: orangeCore, emissive: orangeCore, emissiveIntensity: 0.9,
        metalness: 0.55, roughness: 0.3, transparent: true, opacity: 0.95,
      })));
      // Splash elbow at the bottom (Agent 4 / G4)
      const elbow = new THREE.Mesh(
        new THREE.TorusGeometry(0.26, 0.09, 6, 12, Math.PI),
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
      composer.render();

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
      composer.setSize(nw, nh);
      bloomPass.setSize(nw, nh);
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
