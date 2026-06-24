// STRATEX™ — Parametric Triple-Layer Digital Twin Viewer
//
// Renders a forensic-grade, measurement-faithful 3D twin from REAL scan
// data (facets, edges, rafters) — not AI hallucinated images. Used in
// the analysis dashboard when topology data is available.
//
// Props:
//   topology  — { facets:[{vertices,normal,...}], edges:[...], rafters:[...] }
//   layer     — 0 (Finished Slate) | 1 (Decking) | 2 (Framing)
//   height    — viewport height (px)

import { useEffect, useRef } from "react";
import * as THREE from "three";

// Light hand-rolled OrbitControls (no addons) — just enough rotation +
// auto-spin for the demo dashboard.
function autoRotateLoop(scene, camera, controls) {
  let theta = controls.theta;
  let dragging = false;
  let dragX = 0, dragY = 0;
  let phi = controls.phi;
  const update = () => {
    if (!dragging) theta += 0.0012;
    const r = controls.radius;
    camera.position.x = r * Math.sin(theta) * Math.cos(phi);
    camera.position.y = r * Math.sin(phi);
    camera.position.z = r * Math.cos(theta) * Math.cos(phi);
    camera.lookAt(0, 2, 0);
  };
  const onDown = (e) => { dragging = true; dragX = e.clientX; dragY = e.clientY; };
  const onMove = (e) => {
    if (!dragging) return;
    theta -= (e.clientX - dragX) * 0.006;
    phi   = Math.max(0.1, Math.min(1.3, phi - (e.clientY - dragY) * 0.004));
    dragX = e.clientX; dragY = e.clientY;
  };
  const onUp = () => { dragging = false; };
  return { update, onDown, onMove, onUp };
}

function buildLayer({ topology, layer }) {
  const group = new THREE.Group();
  const facets = topology.facets || [];
  const edges = topology.edges || [];
  const rafters = topology.rafters || topology.framing?.rafters || [];

  // ---------- LAYER 0 — Finished Slate (shingle plane + neon edges) ----------
  if (layer === 0) {
    facets.forEach((f) => {
      const v = f.vertices;
      // Triangle-fan from vertex 0 (roof facets are convex polygons)
      const positions = [];
      for (let i = 1; i < v.length - 1; i++) {
        positions.push(...v[0], ...v[i], ...v[i + 1]);
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
      geo.computeVertexNormals();
      const mat = new THREE.MeshStandardMaterial({
        color: 0x1a2330, roughness: 0.85, metalness: 0.05,
        side: THREE.DoubleSide,
      });
      group.add(new THREE.Mesh(geo, mat));
    });
    // Neon-cyan edge wireframe
    edges.forEach((e) => {
      const color = {
        ridge: 0x4DF6FF, valley: 0xFF2D78, hip: 0xFFB020,
        eave: 0x4DF6FF, rake: 0x4DF6FF,
      }[e.classification] || 0x4DF6FF;
      const g = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(...e.a), new THREE.Vector3(...e.b),
      ]);
      group.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color, linewidth: 2 })));
    });
  }

  // ---------- LAYER 1 — Decking + Underlayment (offset plywood) ----------
  if (layer === 1) {
    facets.forEach((f) => {
      const v = f.vertices;
      const n = new THREE.Vector3(...(f.normal || [0, 1, 0])).normalize().multiplyScalar(-0.05);
      const positions = [];
      for (let i = 1; i < v.length - 1; i++) {
        positions.push(
          v[0][0] + n.x, v[0][1] + n.y, v[0][2] + n.z,
          v[i][0] + n.x, v[i][1] + n.y, v[i][2] + n.z,
          v[i + 1][0] + n.x, v[i + 1][1] + n.y, v[i + 1][2] + n.z,
        );
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
      geo.computeVertexNormals();
      const mat = new THREE.MeshStandardMaterial({
        color: 0xb98a4a, roughness: 0.9, metalness: 0.03,
        side: THREE.DoubleSide,
      });
      group.add(new THREE.Mesh(geo, mat));
    });
    // Amber seam grid (perimeter edges)
    edges.forEach((e) => {
      const g = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(...e.a), new THREE.Vector3(...e.b),
      ]);
      group.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0xFF7B00 })));
    });
  }

  // ---------- LAYER 2 — Structural Framing (rafters + edges) ----------
  if (layer === 2) {
    rafters.forEach((r) => {
      const g = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(...r.a), new THREE.Vector3(...r.b),
      ]);
      group.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0x00FF9C })));
    });
    // Edges become beams (ridges/hips/eaves)
    edges.forEach((e) => {
      const color = {
        ridge: 0x00FF9C, valley: 0xFFB020, hip: 0x4DF6FF, eave: 0x4DF6FF,
      }[e.classification] || 0x00FF9C;
      const g = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(...e.a), new THREE.Vector3(...e.b),
      ]);
      group.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color, linewidth: 2 })));
    });
  }

  return group;
}

export default function ParametricTwin({ topology, layer = 0, height = 360 }) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current || !topology) return;
    const mount = mountRef.current;
    const w = mount.clientWidth;
    const h = height;

    // Scene + camera
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x03070C);
    scene.fog = new THREE.Fog(0x03070C, 25, 70);

    const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 200);
    const ctrl = { radius: 36, theta: Math.PI / 5, phi: 0.5 };
    camera.position.set(20, 18, 24);
    camera.lookAt(0, 2, 0);

    // Lights
    const amb = new THREE.AmbientLight(0xffffff, 0.45);
    scene.add(amb);
    const key = new THREE.DirectionalLight(0x4df6ff, 0.55);
    key.position.set(15, 25, 10);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0xff7b00, 0.35);
    rim.position.set(-20, 12, -8);
    scene.add(rim);

    // Ground plate (just to anchor visually)
    const plate = new THREE.Mesh(
      new THREE.CircleGeometry(28, 64),
      new THREE.MeshBasicMaterial({ color: 0x0a1420, transparent: true, opacity: 0.85 }),
    );
    plate.rotation.x = -Math.PI / 2;
    plate.position.y = -0.02;
    scene.add(plate);
    // Subtle grid
    const grid = new THREE.GridHelper(50, 25, 0x123040, 0x0a1825);
    grid.position.y = -0.01;
    scene.add(grid);

    // Twin
    const twin = buildLayer({ topology, layer });
    twin.position.y = 0.5;
    scene.add(twin);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(w, h);
    mount.innerHTML = "";
    mount.appendChild(renderer.domElement);

    // Controls
    const ctl = autoRotateLoop(scene, camera, ctrl);
    renderer.domElement.addEventListener("mousedown", ctl.onDown);
    window.addEventListener("mousemove", ctl.onMove);
    window.addEventListener("mouseup", ctl.onUp);

    let raf;
    const loop = () => {
      ctl.update();
      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    };
    loop();

    // Resize
    const onResize = () => {
      const nw = mount.clientWidth;
      camera.aspect = nw / h;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, h);
    };
    window.addEventListener("resize", onResize);

    sceneRef.current = { scene, renderer, camera, raf, mount };

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", ctl.onMove);
      window.removeEventListener("mouseup", ctl.onUp);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      try { mount.removeChild(renderer.domElement); } catch (e) {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topology, layer, height]);

  return (
    <div
      ref={mountRef}
      data-testid="parametric-twin"
      style={{
        width: "100%",
        height,
        borderRadius: 6,
        background: "radial-gradient(ellipse at center, #0B1A22 0%, #03070C 100%)",
        cursor: "grab",
        position: "relative",
        overflow: "hidden",
      }}
    />
  );
}
