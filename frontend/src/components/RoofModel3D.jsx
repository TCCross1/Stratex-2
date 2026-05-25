import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

/**
 * STRATEX™ Vision Advanced 3D Diagnostic Viewer
 * ---------------------------------------------
 * Renders the full multi-facet roof topology returned by the backend
 * (facets + classified edges + anomaly polygons on the affected facets).
 *
 * Edge classifications drive color:
 *   ridge  → cyber teal  (#00F0FF)
 *   valley → plasma orange (#FF5500)
 *   hip    → cyan-cyan
 *   eave   → silver dim
 *   rake   → silver
 *
 * Anomalies are drawn as glowing polygons sized to area_affected_sf and
 * placed near the facet centroid. The active/selected anomaly gets a leader
 * label "Anomaly ID: AD-KY041-XXX".
 */

const TEAL = 0x00f0ff;
const ORANGE = 0xff5500;
const SILVER = 0xc7d4dd;

const EDGE_COLOR = {
  ridge: TEAL,
  valley: ORANGE,
  hip: 0x4cd6e0,
  eave: SILVER,
  rake: 0x9bb0c0,
};

function poly3dArea(verts) {
  let n = [0, 0, 0];
  const m = verts.length;
  for (let i = 0; i < m; i++) {
    const a = verts[i];
    const b = verts[(i + 1) % m];
    n[0] += (a[1] - b[1]) * (a[2] + b[2]);
    n[1] += (a[2] - b[2]) * (a[0] + b[0]);
    n[2] += (a[0] - b[0]) * (a[1] + b[1]);
  }
  return 0.5 * Math.hypot(n[0], n[1], n[2]);
}

function projectToScreen(vec, camera, w, h) {
  const v = vec.clone().project(camera);
  return {
    x: (v.x * 0.5 + 0.5) * w,
    y: (1 - (v.y * 0.5 + 0.5)) * h,
    visible: v.z < 1,
  };
}

function fanTriangulate(verts) {
  // verts: [[x,y,z],...]
  const out = [];
  for (let i = 1; i < verts.length - 1; i++) {
    out.push(...verts[0], ...verts[i], ...verts[i + 1]);
  }
  return new Float32Array(out);
}

function buildFacetMesh(facet, color) {
  const v = facet.vertices;
  const positions = fanTriangulate(v);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  g.computeVertexNormals();
  const mat = new THREE.MeshStandardMaterial({
    color: new THREE.Color(color),
    metalness: 0.25,
    roughness: 0.7,
    transparent: true,
    opacity: 0.62,
    side: THREE.DoubleSide,
    emissive: new THREE.Color(color),
    emissiveIntensity: 0.18,
  });
  const mesh = new THREE.Mesh(g, mat);
  // wireframe edges
  const wf = new THREE.LineSegments(
    new THREE.EdgesGeometry(g, 1),
    new THREE.LineBasicMaterial({ color: TEAL, transparent: true, opacity: 0.55 })
  );
  const group = new THREE.Group();
  group.add(mesh);
  group.add(wf);
  group.userData.facet = facet;
  return group;
}

function buildClassifiedEdge(edge) {
  const colorHex = EDGE_COLOR[edge.classification] || TEAL;
  const geom = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(...edge.a),
    new THREE.Vector3(...edge.b),
  ]);
  const mat = new THREE.LineBasicMaterial({
    color: colorHex,
    transparent: true,
    opacity: edge.classification === "valley" ? 0.95 : 0.85,
  });
  const line = new THREE.Line(geom, mat);
  line.userData.edge = edge;
  return line;
}

function buildAnomalyPatch(anomaly, facet) {
  // Approximate the patch as a flat polygon hovering just above the facet plane.
  const verts = facet.vertices.map((v) => new THREE.Vector3(...v));
  const centroid = verts.reduce(
    (acc, v) => acc.add(v),
    new THREE.Vector3()
  ).multiplyScalar(1 / verts.length);
  // shrink polygon around centroid proportional to area ratio
  const facetArea = poly3dArea(facet.vertices);
  const ratio = Math.max(0.06, Math.min(0.45, anomaly.area_affected_sf / Math.max(facetArea, 1)));
  const shrunk = verts.map((v) =>
    centroid.clone().lerp(v, Math.sqrt(ratio))
  );
  const positions = fanTriangulate(shrunk.map((p) => [p.x, p.y, p.z]));
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  g.computeVertexNormals();
  const mat = new THREE.MeshBasicMaterial({
    color: ORANGE,
    transparent: true,
    opacity: 0.62,
    side: THREE.DoubleSide,
  });
  const mesh = new THREE.Mesh(g, mat);
  mesh.position.copy(facet_offset_normal(facet, 0.04));
  const wf = new THREE.LineSegments(
    new THREE.EdgesGeometry(g, 1),
    new THREE.LineBasicMaterial({ color: ORANGE, transparent: true, opacity: 0.95 })
  );
  wf.position.copy(mesh.position);
  const group = new THREE.Group();
  group.add(mesh);
  group.add(wf);
  group.userData.anomaly = anomaly;
  group.userData.labelTarget = centroid.clone().add(facet_offset_normal(facet, 0.04));
  return group;
}

function facet_offset_normal(facet, d) {
  const n = facet.normal;
  return new THREE.Vector3(n[0] * d, n[1] * d, n[2] * d);
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
}) {
  const mountRef = useRef(null);
  const stateRef = useRef({});
  const labelLayerRef = useRef(null);
  const [labelPositions, setLabelPositions] = useState([]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const facets = telemetry?.facets || [];
    const edges = telemetry?.edges || [];
    if (facets.length === 0) return;

    const w = mount.clientWidth || 800;
    const h = mount.clientHeight || height;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06080b);
    scene.fog = new THREE.Fog(0x06080b, 60, 240);

    // compute bbox to centre + frame camera
    const bbox = new THREE.Box3();
    facets.forEach((f) =>
      f.vertices.forEach((v) => bbox.expandByPoint(new THREE.Vector3(...v)))
    );
    const centre = new THREE.Vector3();
    bbox.getCenter(centre);
    const size = new THREE.Vector3();
    bbox.getSize(size);
    const span = Math.max(size.x, size.z) || 30;

    const camera = new THREE.PerspectiveCamera(36, w / h, 0.1, 2000);
    camera.position.set(centre.x + span * 1.15, span * 1.1, centre.z + span * 1.25);
    camera.lookAt(centre);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(w, h);
    mount.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.55));
    const p1 = new THREE.PointLight(TEAL, 800, 600);
    p1.position.set(centre.x + span, span * 1.5, centre.z + span);
    scene.add(p1);
    const p2 = new THREE.PointLight(ORANGE, 280, 600);
    p2.position.set(centre.x - span, span * 0.6, centre.z - span);
    scene.add(p2);

    // grid floor
    const grid = new THREE.GridHelper(span * 4, 60, TEAL, 0x10141d);
    grid.position.set(centre.x, bbox.min.y - 1, centre.z);
    scene.add(grid);

    // facets
    const facetGroups = facets.map((f) => {
      const g = buildFacetMesh(f, f.color_tag || "#7BB7C6");
      scene.add(g);
      return g;
    });

    // classified edges
    edges.forEach((e) => scene.add(buildClassifiedEdge(e)));

    // anomalies
    const facetById = Object.fromEntries(facets.map((f) => [f.id, f]));
    const anomalyGroups = anomalies
      .map((a) => {
        const f = facetById[a.facet_id];
        if (!f) return null;
        const g = buildAnomalyPatch(a, f);
        scene.add(g);
        return g;
      })
      .filter(Boolean);

    // scanner sweep
    const scanner = new THREE.Mesh(
      new THREE.PlaneGeometry(span * 3, span * 3),
      new THREE.MeshBasicMaterial({
        color: TEAL,
        transparent: true,
        opacity: 0.4,
        side: THREE.DoubleSide,
      })
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
    controls.minDistance = span * 0.5;
    controls.maxDistance = span * 4;
    controls.autoRotate = autoRotate && !scanning;
    controls.autoRotateSpeed = 0.55;

    let raf;
    const start = performance.now();
    const tick = () => {
      const t = (performance.now() - start) / 1000;
      anomalyGroups.forEach((g) => {
        const op = 0.55 + Math.sin(t * 3 + (g.userData.anomaly?.confidence || 0) * 10) * 0.22;
        g.children[0].material.opacity = op;
        const wf = g.children[1];
        wf.material.opacity = 0.7 + Math.sin(t * 4 + g.userData.anomaly?.area_affected_sf || 0) * 0.25;
      });
      if (scanning) {
        scanner.visible = true;
        const cycle = (t % 4) / 4;
        scanner.position.y = bbox.min.y - 1 + cycle * (span * 1.5);
        scanner.material.opacity = 0.42 * (1 - cycle);
      } else {
        scanner.visible = false;
      }
      controls.update();
      renderer.render(scene, camera);

      // update label positions
      if (showLabels) {
        const positions = anomalyGroups.map((g) => {
          const target = g.userData.labelTarget;
          const sp = projectToScreen(target, camera, w, h);
          return {
            anomaly: g.userData.anomaly,
            x: sp.x,
            y: sp.y,
            visible: sp.visible,
          };
        });
        // throttle by writing only every 5 frames
        if (Math.floor(t * 20) % 1 === 0) setLabelPositions(positions);
      }
      raf = requestAnimationFrame(tick);
    };
    tick();

    const onResize = () => {
      const nw = mount.clientWidth;
      const nh = mount.clientHeight || height;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };
    window.addEventListener("resize", onResize);

    // click → select anomaly via raycaster
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
      if (hits.length > 0) {
        const hit = hits[0].object.parent;
        onSelectAnomaly(hit.userData.anomaly);
      }
    };
    renderer.domElement.addEventListener("click", onClick);

    stateRef.current = { scene, renderer, controls, scanner, anomalyGroups, facetGroups };

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
  }, [telemetry?.style, telemetry?.scale, anomalies.length, height]);

  // toggle scanning + autoRotate without rebuilding
  useEffect(() => {
    const { controls, scanner } = stateRef.current;
    if (controls) controls.autoRotate = autoRotate && !scanning;
    if (scanner) scanner.visible = scanning;
  }, [scanning, autoRotate]);

  // highlight pulse on the selected anomaly
  useEffect(() => {
    const { anomalyGroups } = stateRef.current;
    if (!anomalyGroups) return;
    anomalyGroups.forEach((g) => {
      const isSel = g.userData.anomaly?.id === highlightAnomalyId;
      g.children[1].material.color.set(isSel ? 0xffd37a : ORANGE);
      g.children[0].scale.setScalar(isSel ? 1.12 : 1);
    });
  }, [highlightAnomalyId]);

  return (
    <div className="relative w-full" style={{ height }} ref={labelLayerRef}>
      <div ref={mountRef} className="absolute inset-0" data-testid="roof-3d-canvas" />
      {/* overlay labels */}
      {showLabels && labelPositions.map((l, i) => l.visible && (
        <div
          key={l.anomaly.id + i}
          className="absolute pointer-events-none"
          style={{ left: l.x + 12, top: l.y - 10 }}
        >
          <div className={`font-mono text-[10px] uppercase tracking-widest px-2 py-1 border ${l.anomaly.id === highlightAnomalyId ? "border-plasma text-plasma" : "border-[#00F0FF]/40 text-teal"}`} style={{ background: "rgba(6,8,11,0.85)", textShadow: l.anomaly.id === highlightAnomalyId ? "0 0 6px rgba(255,85,0,0.85)" : "0 0 6px rgba(0,240,255,0.5)" }}>
            Anomaly ID: <span className="text-silver">{l.anomaly.id}</span>
          </div>
        </div>
      ))}
      <div className="absolute top-3 left-3 font-mono text-[10px] tracking-widest uppercase text-teal flex items-center gap-2 pointer-events-none" style={{ textShadow: "0 0 6px rgba(0,240,255,0.6)" }}>
        <span className="led led-teal" /> STRATEX Vision™ • Spatial Model
      </div>
      <div className="absolute bottom-3 right-3 font-mono text-[10px] tracking-widest uppercase text-muted-hud pointer-events-none">
        DRAG TO ORBIT • SCROLL TO ZOOM • CLICK ANOMALY
      </div>
      {/* legend */}
      <div className="absolute bottom-3 left-3 flex gap-3 font-mono text-[10px] tracking-widest uppercase pointer-events-none">
        <span className="flex items-center gap-1 text-teal"><span className="w-3 h-[2px] bg-[#00F0FF]"/> Ridge</span>
        <span className="flex items-center gap-1 text-plasma"><span className="w-3 h-[2px] bg-[#FF5500]"/> Valley</span>
        <span className="flex items-center gap-1" style={{color:"#4cd6e0"}}><span className="w-3 h-[2px]" style={{background:"#4cd6e0"}}/> Hip</span>
        <span className="flex items-center gap-1 text-silver"><span className="w-3 h-[2px] bg-[#c7d4dd]"/> Eave</span>
      </div>
    </div>
  );
}
