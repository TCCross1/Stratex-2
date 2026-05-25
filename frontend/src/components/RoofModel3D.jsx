import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

/**
 * Pure vanilla three.js roof model — no react-three-fiber.
 * Wireframe gable-hip roof generated from telemetry with glowing anomaly markers.
 */

const TEAL = 0x00f0ff;
const ORANGE = 0xff5500;

function anomalyPlacement(id, length, width, pitch) {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  const side = (h % 2 === 0) ? -1 : 1;
  const t = ((h >> 1) % 1000) / 1000;
  const u = (((h >> 8) % 800) / 1000) + 0.05;
  const x = (t - 0.5) * (length * 0.85);
  const z = side * (width / 2) * (1 - u);
  const apex = (width / 2) * (pitch / 12);
  const y = u * apex;
  const slopeAngle = Math.atan2(apex, width / 2);
  const rotX = side === -1 ? slopeAngle : -slopeAngle;
  return { position: [x, y, z], rotation: [rotX, 0, 0] };
}

function buildRoofGroup(length, width, pitch, ridgeOffset) {
  const apex = (width / 2) * (pitch / 12);
  const L = length / 2;
  const W = width / 2;
  const verts = new Float32Array([
    -L, 0, -W,
     L, 0, -W,
     L, 0,  W,
    -L, 0,  W,
    -L + ridgeOffset, apex, 0,
     L - ridgeOffset, apex, 0,
  ]);
  const idx = [0, 1, 5, 0, 5, 4, 2, 3, 4, 2, 4, 5, 0, 4, 3, 1, 2, 5];
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(verts, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  const mesh = new THREE.Mesh(
    g,
    new THREE.MeshStandardMaterial({
      color: 0x0a1320,
      metalness: 0.45,
      roughness: 0.55,
      transparent: true,
      opacity: 0.55,
      side: THREE.DoubleSide,
    })
  );
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(g, 1),
    new THREE.LineBasicMaterial({ color: TEAL })
  );
  const group = new THREE.Group();
  group.add(mesh);
  group.add(edges);
  return group;
}

function buildWallsGroup(length, width, height) {
  const L = length / 2;
  const W = width / 2;
  const verts = new Float32Array([
    -L, -height, -W,   L, -height, -W,   L, 0, -W,
    -L, -height, -W,   L, 0, -W,        -L, 0, -W,
     L, -height,  W,  -L, -height,  W,  -L, 0,  W,
     L, -height,  W,  -L, 0,  W,         L, 0,  W,
    -L, -height,  W,  -L, -height, -W,  -L, 0, -W,
    -L, -height,  W,  -L, 0, -W,        -L, 0,  W,
     L, -height, -W,   L, -height,  W,   L, 0,  W,
     L, -height, -W,   L, 0,  W,         L, 0, -W,
  ]);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(verts, 3));
  g.computeVertexNormals();
  const mesh = new THREE.Mesh(
    g,
    new THREE.MeshBasicMaterial({ color: 0x06080b, transparent: true, opacity: 0.85 })
  );
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(g, 1),
    new THREE.LineBasicMaterial({ color: TEAL, transparent: true, opacity: 0.45 })
  );
  const group = new THREE.Group();
  group.add(mesh);
  group.add(edges);
  return group;
}

function buildAnomalyMarker(anomaly, length, width, pitch) {
  const { position, rotation } = anomalyPlacement(anomaly.id, length, width, pitch);
  const size = anomaly.severity === "CRITICAL" ? 1.6 : anomaly.severity === "HIGH" ? 1.2 : 0.9;
  const core = new THREE.Mesh(
    new THREE.PlaneGeometry(size, size * 0.85),
    new THREE.MeshBasicMaterial({ color: ORANGE, transparent: true, opacity: 0.7 })
  );
  const halo = new THREE.Mesh(
    new THREE.PlaneGeometry(size * 1.6, size * 1.3),
    new THREE.MeshBasicMaterial({ color: ORANGE, transparent: true, opacity: 0.12 })
  );
  const group = new THREE.Group();
  group.add(halo);
  group.add(core);
  group.position.set(...position);
  group.rotation.set(...rotation);
  group.userData.core = core;
  group.userData.seed = anomaly.id.length;
  return group;
}

export default function RoofModel3D({
  telemetry,
  anomalies = [],
  scanning = false,
  autoRotate = true,
  height = 460,
}) {
  const mountRef = useRef(null);
  const stateRef = useRef({});

  // build/teardown scene whenever telemetry shape changes
  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const ridge = telemetry?.ridge_lf || 60;
    const eaves = telemetry?.eaves_lf || 100;
    const pitch = telemetry?.pitch_num || 7;
    const length = Math.max(8, ridge * 0.16);
    const width = Math.max(6, (eaves * 0.5) * 0.16);
    const ridgeOffset = Math.max(0.3, length * 0.08);

    const w = mount.clientWidth || 800;
    const h = mount.clientHeight || height;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06080b);
    scene.fog = new THREE.Fog(0x06080b, 20, 90);

    const camera = new THREE.PerspectiveCamera(38, w / h, 0.1, 1000);
    camera.position.set(length * 1.7, length * 0.95, length * 1.7);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(w, h);
    mount.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xffffff, 0.45));
    const p1 = new THREE.PointLight(TEAL, 220, 200);
    p1.position.set(10, 14, 10);
    scene.add(p1);
    const p2 = new THREE.PointLight(ORANGE, 90, 200);
    p2.position.set(-12, 10, -10);
    scene.add(p2);

    // grid
    const grid = new THREE.GridHelper(40, 40, TEAL, 0x10141d);
    grid.position.y = -1.5;
    scene.add(grid);

    // walls + roof
    const walls = buildWallsGroup(length, width, 1.4);
    scene.add(walls);
    const roof = buildRoofGroup(length, width, pitch, ridgeOffset);
    scene.add(roof);

    // anomalies
    const anomalyGroups = anomalies.map((a) => {
      const g = buildAnomalyMarker(a, length, width, pitch);
      scene.add(g);
      return g;
    });

    // scanner plane
    const scanner = new THREE.Mesh(
      new THREE.PlaneGeometry(26, 26),
      new THREE.MeshBasicMaterial({ color: TEAL, transparent: true, opacity: 0.4, side: THREE.DoubleSide })
    );
    scanner.rotation.x = Math.PI / 2;
    scanner.visible = scanning;
    scene.add(scanner);

    // controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.enablePan = false;
    controls.minDistance = 6;
    controls.maxDistance = 60;
    controls.autoRotate = autoRotate && !scanning;
    controls.autoRotateSpeed = 0.6;

    let raf;
    const start = performance.now();
    const tick = () => {
      const t = (performance.now() - start) / 1000;
      anomalyGroups.forEach((g) => {
        const core = g.userData.core;
        core.material.opacity = 0.55 + Math.sin(t * 3 + g.userData.seed) * 0.2;
      });
      if (scanning) {
        scanner.visible = true;
        const cycle = (t % 4) / 4;
        scanner.position.y = -1.5 + cycle * 6;
        scanner.material.opacity = 0.4 * (1 - cycle);
      } else {
        scanner.visible = false;
      }
      controls.update();
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    tick();

    // resize
    const onResize = () => {
      const nw = mount.clientWidth;
      const nh = mount.clientHeight || height;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };
    window.addEventListener("resize", onResize);

    stateRef.current = { scene, renderer, controls, scanner };

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
      scene.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose?.();
        if (obj.material) {
          if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose?.());
          else obj.material.dispose?.();
        }
      });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [telemetry?.ridge_lf, telemetry?.eaves_lf, telemetry?.pitch_num, anomalies.length, height]);

  // toggle scanning + autoRotate without rebuilding
  useEffect(() => {
    const { controls, scanner } = stateRef.current;
    if (controls) controls.autoRotate = autoRotate && !scanning;
    if (scanner) scanner.visible = scanning;
  }, [scanning, autoRotate]);

  return (
    <div className="relative w-full" style={{ height }}>
      <div ref={mountRef} className="absolute inset-0" data-testid="roof-3d-canvas" />
      <div className="absolute top-3 left-3 font-mono text-[10px] tracking-widest uppercase text-teal flex items-center gap-2 pointer-events-none" style={{ textShadow: "0 0 6px rgba(0,240,255,0.6)" }}>
        <span className="led led-teal" /> STRATEX Vision™ • Spatial Model
      </div>
      <div className="absolute bottom-3 right-3 font-mono text-[10px] tracking-widest uppercase text-muted-hud pointer-events-none">
        DRAG TO ORBIT • SCROLL TO ZOOM
      </div>
      {anomalies.length > 0 && (
        <div className="absolute top-3 right-3 font-mono text-[10px] tracking-widest uppercase text-plasma pointer-events-none" style={{ textShadow: "0 0 6px rgba(255,85,0,0.7)" }}>
          {anomalies.length} ANOMALIES • {anomalies.filter((a) => a.severity === "CRITICAL").length} CRIT
        </div>
      )}
    </div>
  );
}
