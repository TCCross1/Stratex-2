// STRATEX™ — Architect-Grade Parametric Twin Renderer
//
// QUALITY STANDARDS (locked into memory by CEO directive):
//   - NEVER ship wireframe-only "amateur" twins
//   - SHADED filled surfaces (sun-direction lighting)
//   - Multiple stroke weights (heavy outer edges, medium ridges/valleys, light hatching)
//   - Dimension lines with measurement labels
//   - Cross-hatching/grain texture per material per layer
//   - Camera angle: 3/4 isometric, never straight-on
//   - Anti-aliased, premium feel — like an architect's stamped drawing
import { useEffect, useRef } from "react";
import * as THREE from "three";

function autoRotateLoop(controls) {
  let theta = controls.theta;
  let dragging = false, dragX = 0, dragY = 0;
  let phi = controls.phi;
  const onDown = (e) => { dragging = true; dragX = e.clientX; dragY = e.clientY; };
  const onMove = (e) => {
    if (!dragging) return;
    theta -= (e.clientX - dragX) * 0.006;
    phi = Math.max(0.15, Math.min(1.25, phi - (e.clientY - dragY) * 0.004));
    dragX = e.clientX; dragY = e.clientY;
  };
  const onUp = () => { dragging = false; };
  return {
    apply: (cam) => {
      if (!dragging) theta += 0.0009;
      const r = controls.radius;
      cam.position.x = r * Math.sin(theta) * Math.cos(phi);
      cam.position.y = r * Math.sin(phi);
      cam.position.z = r * Math.cos(theta) * Math.cos(phi);
      cam.lookAt(0, 2, 0);
    },
    onDown, onMove, onUp,
  };
}

// Triangulate a convex polygon (fan from vertex 0)
function fanTriangles(verts) {
  const out = [];
  for (let i = 1; i < verts.length - 1; i++) {
    out.push(...verts[0], ...verts[i], ...verts[i + 1]);
  }
  return out;
}

function buildScene({ topology, layer }) {
  const group = new THREE.Group();
  const facets = topology.facets || [];
  const edges = topology.edges || [];
  const rafters = topology.rafters || [];

  // ---------- LAYER 0 — Finished Slate / Shingle ----------
  if (layer === 0) {
    facets.forEach((f) => {
      const positions = fanTriangles(f.vertices);
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
      geo.computeVertexNormals();
      // Shingle: dark slate with subtle gradient
      const mat = new THREE.MeshStandardMaterial({
        color: 0x202a38, roughness: 0.78, metalness: 0.18,
        side: THREE.DoubleSide, flatShading: false,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.castShadow = mesh.receiveShadow = true;
      group.add(mesh);
      // Edge outline (heavy stroke)
      const eg = new THREE.EdgesGeometry(geo, 1);
      group.add(new THREE.LineSegments(eg, new THREE.LineBasicMaterial({
        color: 0x4DF6FF, transparent: true, opacity: 0.85,
      })));
    });
    // Edge classification with stroke-weight differentiation
    edges.forEach((e) => {
      const cfg = {
        ridge:  { color: 0x4DF6FF, w: 3 },
        valley: { color: 0xFF2D78, w: 2.5 },
        hip:    { color: 0xFFB020, w: 2 },
        eave:   { color: 0xFF7B00, w: 2 },
        rake:   { color: 0x9AE6FF, w: 1 },
      }[e.classification] || { color: 0x4DF6FF, w: 1 };
      const g = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(...e.a), new THREE.Vector3(...e.b),
      ]);
      group.add(new THREE.Line(g, new THREE.LineBasicMaterial({
        color: cfg.color, linewidth: cfg.w,
      })));
    });
  }

  // ---------- LAYER 1 — Decking + Plywood Seams ----------
  if (layer === 1) {
    facets.forEach((f) => {
      const n = new THREE.Vector3(...(f.normal || [0, 1, 0])).normalize().multiplyScalar(-0.04);
      const offset = f.vertices.map((v) => [v[0] + n.x, v[1] + n.y, v[2] + n.z]);
      const positions = fanTriangles(offset);
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
      geo.computeVertexNormals();
      const mat = new THREE.MeshStandardMaterial({
        color: 0xc89760, roughness: 0.92, metalness: 0.02,
        side: THREE.DoubleSide,
      });
      group.add(new THREE.Mesh(geo, mat));
      const eg = new THREE.EdgesGeometry(geo, 1);
      group.add(new THREE.LineSegments(eg, new THREE.LineBasicMaterial({
        color: 0xFFB020, transparent: true, opacity: 0.9,
      })));
    });
    // Plywood seam grid — 4'×8' across the largest facet
    facets.forEach((f) => {
      const v0 = new THREE.Vector3(...f.vertices[0]);
      const v1 = new THREE.Vector3(...f.vertices[1]);
      const dir = v1.clone().sub(v0).normalize();
      for (let s = 4; s < 30; s += 4) {
        const p1 = v0.clone().addScaledVector(dir, s);
        const p2 = p1.clone().add(new THREE.Vector3(0, 1.5, 0));
        const g = new THREE.BufferGeometry().setFromPoints([p1, p2]);
        group.add(new THREE.Line(g, new THREE.LineBasicMaterial({
          color: 0xFF7B00, transparent: true, opacity: 0.35,
        })));
      }
    });
    edges.forEach((e) => {
      const g = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(...e.a), new THREE.Vector3(...e.b),
      ]);
      group.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0xFFB020 })));
    });
  }

  // ---------- LAYER 2 — Structural Framing ----------
  if (layer === 2) {
    // Render rafters as thin cylinders for body, not just lines (architecturally accurate)
    rafters.forEach((r) => {
      const a = new THREE.Vector3(...r.a);
      const b = new THREE.Vector3(...r.b);
      const dir = b.clone().sub(a);
      const len = dir.length();
      const geom = new THREE.CylinderGeometry(0.06, 0.06, len, 6, 1);
      const mat = new THREE.MeshStandardMaterial({
        color: 0xb29368, roughness: 0.85, metalness: 0.05,
      });
      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.copy(a.clone().add(b).multiplyScalar(0.5));
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
      group.add(mesh);
    });
    // Edge classifications as beams
    edges.forEach((e) => {
      const cfg = {
        ridge:  { color: 0x00FF9C },
        valley: { color: 0xFFB020 },
        hip:    { color: 0x4DF6FF },
        eave:   { color: 0x4DF6FF },
      }[e.classification] || { color: 0x00FF9C };
      const g = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(...e.a), new THREE.Vector3(...e.b),
      ]);
      group.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: cfg.color })));
    });
  }

  return group;
}

export default function ParametricTwin({ topology, layer = 0, height = 360 }) {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current || !topology) return;
    const mount = mountRef.current;
    const w = mount.clientWidth;
    const h = height;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x05090F);
    scene.fog = new THREE.Fog(0x05090F, 30, 80);

    const camera = new THREE.PerspectiveCamera(35, w / h, 0.1, 200);
    const ctrl = { radius: 32, theta: Math.PI / 4 + 0.15, phi: 0.58 };

    // Architect-grade three-point lighting
    scene.add(new THREE.AmbientLight(0xffffff, 0.32));
    const sun = new THREE.DirectionalLight(0xfff2d4, 0.95);
    sun.position.set(22, 32, 14);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 1024;
    sun.shadow.mapSize.height = 1024;
    scene.add(sun);
    const fill = new THREE.DirectionalLight(0x4df6ff, 0.4);
    fill.position.set(-18, 14, -12);
    scene.add(fill);
    const rim = new THREE.DirectionalLight(0xff7b00, 0.25);
    rim.position.set(8, 6, -20);
    scene.add(rim);

    // Ground / context plate with grid
    const plate = new THREE.Mesh(
      new THREE.CircleGeometry(32, 96),
      new THREE.MeshStandardMaterial({ color: 0x0a1623, roughness: 0.95, metalness: 0 }),
    );
    plate.rotation.x = -Math.PI / 2;
    plate.position.y = -0.05;
    plate.receiveShadow = true;
    scene.add(plate);
    const grid = new THREE.GridHelper(60, 30, 0x1b3344, 0x0d1a26);
    grid.position.y = -0.04;
    scene.add(grid);
    // Compass / North arrow
    const compassGeo = new THREE.ConeGeometry(0.35, 1.2, 4);
    const compass = new THREE.Mesh(
      compassGeo,
      new THREE.MeshBasicMaterial({ color: 0xFF2D78 }),
    );
    compass.position.set(-14, 0.2, -14);
    compass.rotation.x = Math.PI / 2;
    scene.add(compass);

    const twin = buildScene({ topology, layer });
    twin.position.y = 0.5;
    scene.add(twin);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(w, h);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    mount.innerHTML = "";
    mount.appendChild(renderer.domElement);

    const orbit = autoRotateLoop(ctrl);
    renderer.domElement.addEventListener("pointerdown", orbit.onDown);
    window.addEventListener("pointermove", orbit.onMove);
    window.addEventListener("pointerup", orbit.onUp);

    let raf;
    const loop = () => {
      orbit.apply(camera);
      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    };
    loop();

    const onResize = () => {
      const nw = mount.clientWidth;
      camera.aspect = nw / h;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, h);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", orbit.onMove);
      window.removeEventListener("pointerup", orbit.onUp);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      try { mount.removeChild(renderer.domElement); } catch (e) { /* unmounted */ }
    };
  }, [topology, layer, height]);

  return (
    <div
      ref={mountRef}
      data-testid="parametric-twin"
      style={{
        width: "100%",
        height,
        borderRadius: 6,
        background: "radial-gradient(ellipse at 60% 25%, #122035 0%, #03070C 75%)",
        cursor: "grab",
        position: "relative",
        overflow: "hidden",
        border: "1px solid rgba(77,246,255,0.18)",
        boxShadow: "inset 0 0 60px rgba(77,246,255,0.05)",
      }}
    />
  );
}
