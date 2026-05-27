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
const MATRIX   = 0x00ff66;    // framing layer — neon green
const ELECTRIC = 0x00f0ff;    // gutter layer — neon cyan
const NEON_MAGENTA = 0xff1ec8; // shingle layer — neon magenta
const NEON_AMBER   = 0xffb300; // metal layer   — neon amber/gold
const NEON_VIOLET  = 0x9d3cff; // slate layer   — neon violet

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
  // NEON MAGENTA — staggered architectural shingle tabs glowing on near-black ground
  const size = 256;
  const c = document.createElement("canvas"); c.width = c.height = size;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#1a0414"; ctx.fillRect(0, 0, size, size);
  const rowH = size / 8;
  const tabW = size / 4;
  for (let r = 0; r < 8; r++) {
    const offset = (r % 2) * (tabW / 2);
    for (let cIdx = -1; cIdx <= 4; cIdx++) {
      const x = cIdx * tabW + offset;
      const y = r * rowH;
      const grad = ctx.createLinearGradient(x, y, x, y + rowH);
      grad.addColorStop(0,   "#ff5fd8");
      grad.addColorStop(0.55,"#ff1ec8");
      grad.addColorStop(1,   "#7a0760");
      ctx.fillStyle = grad;
      ctx.fillRect(x + 1, y + 1, tabW - 2, rowH - 2);
      // Neon vertical seam glow
      ctx.strokeStyle = "rgba(255,120,225,0.85)";
      ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.moveTo(x + tabW / 2, y); ctx.lineTo(x + tabW / 2, y + rowH); ctx.stroke();
      // Dark row separator
      ctx.strokeStyle = "rgba(0,0,0,0.75)";
      ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(x, y + rowH); ctx.lineTo(x + tabW, y + rowH); ctx.stroke();
    }
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(4, 4);
  return tex;
}

function makeMetalTexture() {
  // NEON AMBER/GOLD — vertical standing-seam panels with hot edge glow
  const size = 256;
  const c = document.createElement("canvas"); c.width = c.height = size;
  const ctx = c.getContext("2d");
  const panelW = size / 6;
  for (let i = 0; i < 6; i++) {
    const x = i * panelW;
    const grad = ctx.createLinearGradient(x, 0, x + panelW, 0);
    grad.addColorStop(0,   "#3a2105");
    grad.addColorStop(0.5, "#ffb300");
    grad.addColorStop(1,   "#3a2105");
    ctx.fillStyle = grad; ctx.fillRect(x, 0, panelW, size);
    // Bright raised seam
    ctx.fillStyle = "#fff0a8";
    ctx.fillRect(x + panelW - 2, 0, 2, size);
    ctx.fillStyle = "rgba(255,220,120,0.65)";
    ctx.fillRect(x + panelW - 4, 0, 1, size);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(3, 3);
  return tex;
}

function makeSlateTexture() {
  // NEON VIOLET — staggered slate tiles glowing on deep indigo ground
  const size = 256;
  const c = document.createElement("canvas"); c.width = c.height = size;
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#10041f"; ctx.fillRect(0, 0, size, size);
  const rowH = size / 10;
  const tileW = size / 6;
  for (let r = 0; r < 12; r++) {
    const yo = r * rowH;
    const offset = (r % 2) * (tileW / 2);
    for (let cIdx = -1; cIdx <= 6; cIdx++) {
      const x = cIdx * tileW + offset;
      const wobble = Math.sin(r * 1.7 + cIdx * 1.3) * 18;
      const rC = 130 + Math.floor(wobble);
      const gC = 50  + Math.floor(wobble * 0.5);
      const bC = 240 + Math.floor(wobble * 0.6);
      ctx.fillStyle = `rgb(${rC},${gC},${bC})`;
      ctx.beginPath();
      ctx.moveTo(x + tileW / 2, yo);
      ctx.lineTo(x + tileW, yo + rowH * 0.45);
      ctx.lineTo(x + tileW, yo + rowH);
      ctx.lineTo(x, yo + rowH);
      ctx.lineTo(x, yo + rowH * 0.45);
      ctx.closePath();
      ctx.fill();
      // Bright violet edge highlight
      ctx.strokeStyle = "rgba(220,160,255,0.75)";
      ctx.lineWidth = 1.1;
      ctx.stroke();
    }
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(3, 3);
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

  // Per-finish neon material: distinct hue, strong emissive glow.
  const finishConfig = {
    shingle: { tex: finishTex("shingle"), baseColor: NEON_MAGENTA, emissive: NEON_MAGENTA, metalness: 0.15, roughness: 0.55, opacity: 0.96, emissiveIntensity: 0.75 },
    metal:   { tex: finishTex("metal"),   baseColor: NEON_AMBER,   emissive: NEON_AMBER,   metalness: 0.90, roughness: 0.20, opacity: 0.97, emissiveIntensity: 0.70 },
    slate:   { tex: finishTex("slate"),   baseColor: NEON_VIOLET,  emissive: NEON_VIOLET,  metalness: 0.30, roughness: 0.55, opacity: 0.95, emissiveIntensity: 0.65 },
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
  });
  const mesh = new THREE.Mesh(g, mat);

  // soft outline highlight — orange perimeter (like the reference frames)
  const wf = new THREE.LineSegments(
    new THREE.EdgesGeometry(g, 1),
    new THREE.LineBasicMaterial({ color: ORANGE, transparent: true, opacity: 0.65 }),
  );
  const group = new THREE.Group();
  group.add(mesh); group.add(wf);
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

    // -------- FRAMING LAYER (neon-green matrix wireframe) --------
    const framingGroup = new THREE.Group();
    framingGroup.visible = resolvedPrimary === "framing";
    const tele = telemetry || {};
    const framing = tele.framing || {};
    // Rafters
    (framing.rafters || []).forEach((r) => {
      const geom = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(...r.a), new THREE.Vector3(...r.b),
      ]);
      const mat = new THREE.LineBasicMaterial({ color: MATRIX, transparent: true, opacity: 0.78 });
      framingGroup.add(new THREE.Line(geom, mat));
    });
    // Sub-fascia (slightly below + along each eave)
    (framing.sub_fascia || []).forEach((s) => {
      const a = new THREE.Vector3(s.a[0], s.a[1] - 0.5, s.a[2]);
      const b = new THREE.Vector3(s.b[0], s.b[1] - 0.5, s.b[2]);
      const geom = new THREE.BufferGeometry().setFromPoints([a, b]);
      framingGroup.add(new THREE.Line(geom, new THREE.LineBasicMaterial({ color: MATRIX, transparent: true, opacity: 0.95, linewidth: 3 })));
    });
    scene.add(framingGroup);

    // -------- GUTTERS LAYER (neon-cyan extruded tube along eaves + downspouts) --------
    const gutterGroup = new THREE.Group();
    gutterGroup.visible = !!resolvedGutters;
    const gutters = tele.gutters || {};
    (gutters.polylines || []).forEach((p) => {
      const a = new THREE.Vector3(p.a[0], p.a[1] - 0.6, p.a[2]);
      const b = new THREE.Vector3(p.b[0], p.b[1] - 0.6, p.b[2]);
      const path = new THREE.LineCurve3(a, b);
      const tube = new THREE.TubeGeometry(path, 1, 0.22, 8, false);
      const mat = new THREE.MeshStandardMaterial({
        color: ELECTRIC, emissive: ELECTRIC, emissiveIntensity: 0.55,
        transparent: true, opacity: 0.9, metalness: 0.4, roughness: 0.35,
      });
      gutterGroup.add(new THREE.Mesh(tube, mat));
      // hangers — small node points every 2 ft along the segment
      const len = a.distanceTo(b);
      const n = Math.max(2, Math.floor(len / 2));
      for (let i = 0; i <= n; i++) {
        const t = i / n;
        const pos = a.clone().lerp(b, t);
        const dot = new THREE.Mesh(new THREE.SphereGeometry(0.12, 6, 6),
          new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.8 }));
        dot.position.copy(pos); gutterGroup.add(dot);
      }
    });
    (gutters.downspouts || []).forEach((d) => {
      const top = new THREE.Vector3(d.drop[0], d.drop[1] - 0.6, d.drop[2]);
      const bot = new THREE.Vector3(d.ground[0], d.ground[1], d.ground[2]);
      const path = new THREE.LineCurve3(top, bot);
      const tube = new THREE.TubeGeometry(path, 1, 0.16, 6, false);
      gutterGroup.add(new THREE.Mesh(tube, new THREE.MeshStandardMaterial({
        color: ELECTRIC, emissive: ELECTRIC, emissiveIntensity: 0.5,
        transparent: true, opacity: 0.85, metalness: 0.4, roughness: 0.35,
      })));
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
