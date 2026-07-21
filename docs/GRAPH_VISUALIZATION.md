# PROPERTY KNOWLEDGE GRAPH VISUALIZATION PLATFORM SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 012 · OPERATION PROPERTY KNOWLEDGE GRAPH
**Status:** DESIGN COMPLETE  
**Scope:** Interactive 2D/3D Network Layouts, Bento Grid Panels, and CENTCOM Workspace Integrations.

---

## 1. Executive Aesthetic & UI Architecture

The Property Knowledge Graph Visualization Platform is the flagship interface module integrated directly into the CENTCOM executive operations hub. Aligned to the **Stratex "Mission Control" visual design guidelines**, it is characterized by:
* **Deep Charcoal Backdrop:** Pure pitch-black or `#0B0F19` slate canvas background to minimize visual fatigue.
* **Cyber Neon Indicators:** Interactive glowing nodes and laser-etched lines (`#10B981` Emerald for Verified connections, `#F59E0B` Amber for Estimated, `#EF4444` Rose for Critical anomalies).
* **High-Density Bento Containers:** Modular, micro-bordered panels displaying immediate topological insights, query consoles, and evidence ledgers.

---

## 2. 2D Interactive Force-Graph Module

The primary interface features an interactive, high-performance 2D node-link network visualization utilizing `react-force-graph-2d` or a optimized `d3-force` SVG canvas.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ CENTCOM COMMAND CENTRE  ·  PROPERTY KNOWLEDGE GRAPH WORKSPACE                          │
├──────────────────────────────────────┬─────────────────────────────────────────────────┤
│ [A] TOPOLOGY EXPLORER CANVAS         │ [B] DETAILED METADATA SIDEBAR (Selected Node)   │
│                                      │                                                 │
│       (Timeline Event)               │  NODE: s3://photos/shingle_damage_02.jpg        │
│             ☼                        │  Type: PHOTO                                    │
│             │                        │  Confidence Score: 0.96                         │
│             ▼                        │  Captured at: 2026-07-15 14:10:00 UTC           │
│         [System: Roof]               ├─────────────────────────────────────────────────┤
│           ▲    ▲                     │ [C] RELATIONSHIP EVIDENCE LEDGER                │
│           │    │                     │                                                 │
│  CONTAINS │    │ INSTALLED_BY        │  Edge: SYSTEM -[INSTALLED_BY]-> CONTRACTOR      │
│           │    │                     │                                                 │
│       (Material) (Contractor)        │  Verifying Passport Evidence:                   │
│                                      │  - Doc #FL-2026-CONTRACT (Certified Closeout)   │
│                                      │  - Photo #01H2Z4J6P9 (Drone Validation Scan)    │
└──────────────────────────────────────┴─────────────────────────────────────────────────┘
```

### Visual Rendering Invariants & Rules
1. **Node Radii Scaling:** Node size corresponds to its connection degree (number of active edges). A Property root or System assembly is rendered larger than individual Photos or Evidence markers.
2. **Edge Line Styles:**
   * **Solid Lines:** Represent `VERIFIED` relationships (confidence ≥ 0.90).
   * **Dashed Lines:** Represent `ESTIMATED` relationships (0.60 ≤ confidence < 0.90).
   * **Dotted Lines:** Represent `PROJECTED` relations (confidence < 0.60).
3. **Interactive Hover/Focus state:** Hovering over a node dims all unrelated connections in the graph, emphasizing immediate first-degree neighbors. Clicking a node locks focus and populates the sidebar.

---

## 3. 3D Spatial Relationship Overlay (Three.js/WebGL)

To support executive zoom-ins on structural systems, the platform supports a 3D Digital Twin visualization mode that maps semantic graph connections directly onto the 3D photogrammetric roof mesh.

```
                  Z-Axis (Altitude/Elevation)
                     ▲
                     │          ┌─── SYSTEM: South-facing Roof Plane (Node ID: 01H2)
                     │         /
                     │    _   ▼_
                     │   / \_/  \  ◄── Radiometric/Moisture Anomaly Node
                     │  / /   \  \
                     │ /_/_____\__\
                     │ [  Aerial  ]
                     │ [DigitalTwin]
                     │
                     └────────────────────────► X-Axis (Latitude)
                    /
                   /
                  ▼
                Y-Axis (Longitude)
```

### Spatial Mapping Protocol
1. **Raycasting Node Coordinates:** 3D coordinates `(X, Y, Z)` of structural components are loaded from photogrammetric OBJ/GLTF files. Node anchors in the graph (e.g., `EVIDENCE` of moisture leakage) are positioned directly at their localized coordinate vertex.
2. **Dynamic Spline Edges:** Relationships are rendered as glowing, curved 3D splines (`THREE.CatmullRomCurve3`) connecting the model vertices to floating, spatial metadata billboarding tags.
3. **Radiometric Thermography:** Applying thermal CV outputs as a dynamic color layer over the 3D mesh model, highlighting where high thermal-loss or water-risk edges propagate risk into the structural framing systems.

---

## 4. Responsive Layout Sizes & Viewports

The visualization shell fluidly adapts to different display architectures to support command centers as well as remote mobile GMs.

### A. Ultra-Wide & Desktop Monitors (1440px and higher)
* **Layout:** Dual-pane Bento layout. Left 70% of the screen displays the full canvas (3D Canvas or 2D Force-Graph). Right 30% displays collapsible Inspector sidebars containing metadata fields, GraphQL query inputs, and verification documents.
* **Refreshes:** Real-time event streams animate nodes on-the-fly when events bubble up.

### B. Tablet Screens (768px - 1024px)
* **Layout:** Single-column layout. The force-graph acts as a full-screen background canvas.
* **Inspector:** Accessible via a slide-up tray or sliding overlay drawer triggered from a floating action button on the bottom-right.
* **Gestures:** Optimizes pinch-to-zoom and double-tap-to-focus to preserve precise inspection accuracy.

### C. Mobile Screens (Below 768px)
* **Layout:** Complete transition from active force-graph links to a high-density, searchable **Relational Card List**.
* **Visualization:** Complex graph rendering is bypassed; instead, each node type acts as a card header, displaying its active outgoing relationships with direct links to S3-backed photos and PDF receipts. This bypasses client-side CPU constraints on mobile webview threads.
