import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  nxGetMission, nxEvidenceProfile, nxListEvidence, nxUploadEvidence,
  nxValidatePackage, nxFinalizePackage, nxListPackages, nxOpenManifestJson,
  nxGetEvidence, nxDeleteEvidence, nxRetryMetadata,
} from "@/nextgen/api";

/* Evidence workspace — Wave 2A · SD-007 canonical mission package.
   Route: /nextgen/missions/:missionId/evidence */

const CATEGORIES = [
  "RGB_IMAGE","THERMAL_RADIOMETRIC","THERMAL_DERIVATIVE","VIDEO",
  "FLIGHT_LOG","TELEMETRY","CAMERA_METADATA","CALIBRATION_FILE",
  "WEATHER_RECORD","AIRSPACE_RECORD","OPERATOR_NOTE",
  "PROPERTY_DOCUMENT","PRIOR_REPORT","MANUAL_MEASUREMENT",
  "INTERIOR_IMAGE","LIDAR_POINT_CLOUD","PHOTOGRAMMETRY_OUTPUT",
  "DIGITAL_TWIN_MODEL","CAD_BIM_DERIVATIVE","REPORT_DERIVATIVE","OTHER",
];

const DERIVATIVE_ONLY = new Set([
  "THERMAL_DERIVATIVE","PHOTOGRAMMETRY_OUTPUT","DIGITAL_TWIN_MODEL",
  "CAD_BIM_DERIVATIVE","REPORT_DERIVATIVE",
]);

function humanBytes(n) {
  if (!n && n !== 0) return "—";
  const u = ["B","KB","MB","GB"]; let i = 0; let v = n;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(v >= 100 ? 0 : 1)} ${u[i]}`;
}

function Pill({ children, kind = "" }) {
  return <span className={`nx-pill ${kind}`}>{children}</span>;
}

export default function EvidencePage() {
  const { missionId } = useParams();
  const [missionData, setMissionData] = useState(null);
  const [profile, setProfile] = useState(null);
  const [items, setItems] = useState([]);
  const [validation, setValidation] = useState(null);
  const [packages, setPackages] = useState([]);
  const [selectedCat, setSelectedCat] = useState("RGB_IMAGE");
  const [mode, setMode] = useState("DEMO");
  const [operatorNote, setOperatorNote] = useState("");
  const [uploads, setUploads] = useState({});    // filename -> { pct, err }
  const [drawer, setDrawer] = useState(null);
  const [err, setErr] = useState(null);
  const [finalizeBusy, setFinalizeBusy] = useState(false);
  const dropRef = useRef(null);

  const load = async () => {
    try {
      const m = await nxGetMission(missionId);
      setMissionData(m);
      const p = await nxEvidenceProfile(m.mission.product);
      setProfile(p);
      const ev = await nxListEvidence(missionId);
      setItems(ev.items);
      const val = await nxValidatePackage(missionId);
      setValidation(val);
      const pkgs = await nxListPackages(missionId);
      setPackages(pkgs.items);
    } catch (e) { setErr(e?.response?.data?.detail || e.message); }
  };
  useEffect(() => { load(); }, [missionId]);

  const counts = useMemo(() => {
    const c = { total: items.length, original: 0, derivative: 0, byCat: {}, size: 0 };
    for (const it of items) {
      c[it.role] = (c[it.role] || 0) + 1;
      c.byCat[it.kind] = (c.byCat[it.kind] || 0) + 1;
      c.size += it.size_bytes || 0;
    }
    return c;
  }, [items]);

  const uploadOne = async (file) => {
    setUploads((u) => ({ ...u, [file.name]: { pct: 0 } }));
    const fd = new FormData();
    fd.append("file", file);
    fd.append("category", selectedCat);
    fd.append("is_original", String(!DERIVATIVE_ONLY.has(selectedCat)));
    fd.append("mode", mode);
    if (operatorNote && selectedCat === "OPERATOR_NOTE") fd.append("operator_note", operatorNote);
    try {
      await nxUploadEvidence(missionId, fd, (evt) => {
        const pct = Math.round((evt.loaded / (evt.total || file.size)) * 100);
        setUploads((u) => ({ ...u, [file.name]: { pct } }));
      });
      setUploads((u) => ({ ...u, [file.name]: { pct: 100, done: true } }));
    } catch (e) {
      const d = e?.response?.data?.detail;
      const msg = typeof d === "string" ? d : (d?.code === "duplicate_detected"
        ? `Duplicate · already at ${d.scope}` : (d?.message || e.message));
      setUploads((u) => ({ ...u, [file.name]: { pct: 0, err: msg } }));
    }
  };

  const onFiles = async (fileList) => {
    const files = Array.from(fileList || []);
    for (const f of files) await uploadOne(f);
    await load();
  };

  const onDrop = (e) => {
    e.preventDefault();
    dropRef.current?.classList.remove("dragover");
    onFiles(e.dataTransfer.files);
  };

  const openDrawer = async (id) => {
    setDrawer({ loading: true });
    try {
      const d = await nxGetEvidence(id);
      setDrawer(d);
    } catch (e) { setDrawer({ error: e.message }); }
  };

  const doFinalize = async () => {
    setFinalizeBusy(true);
    try {
      await nxFinalizePackage(missionId, operatorNote || null);
      await load();
    } catch (e) {
      const d = e?.response?.data?.detail;
      setErr(typeof d === "string" ? d : JSON.stringify(d).slice(0, 400));
    } finally { setFinalizeBusy(false); }
  };

  const deletePending = async (id) => {
    if (!window.confirm("Delete this evidence item (only allowed pre-finalization)?")) return;
    try { await nxDeleteEvidence(id); await load(); }
    catch (e) { alert(e?.response?.data?.detail || e.message); }
  };

  const retryMeta = async (id) => {
    try { await nxRetryMetadata(id); await load(); }
    catch (e) { alert(e?.response?.data?.detail || e.message); }
  };

  if (!missionData) return <div className="nx-empty">Loading mission…</div>;
  const { mission: m, property: prop, product, stage_labels } = missionData;
  const finalizedPkg = packages.find((p) => p.status === "finalized");

  return (
    <div data-testid="nx-evidence">
      <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>
        // MISSION EVIDENCE · SD-007 · WAVE 2A
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 18 }}>
        <div>
          <h1 className="nx-h1">{product.display_name}</h1>
          <div className="nx-sub">
            {prop?.address.line1}, {prop?.address.city} {prop?.address.region} · Mission
            <span style={{ fontFamily: "'JetBrains Mono', monospace", marginLeft: 6, color: "#4DF6FF" }}>
              {m.canonical_id.slice(0, 12)}…
            </span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <Link to={`/nextgen/missions/${missionId}`} className="nx-btn ghost small">
            ← Mission
          </Link>
          <Pill kind="gold">Stage {m.stage}/15 · {stage_labels[m.stage - 1]}</Pill>
        </div>
      </div>

      {/* Header stats */}
      <div className="nx-grid cols-4">
        <div className="nx-stat">
          <div className="k">// Files</div><div className="v">{counts.total}</div>
          <div className="s">{humanBytes(counts.size)} total</div>
        </div>
        <div className="nx-stat">
          <div className="k">// Originals</div><div className="v cy">{counts.original || 0}</div>
          <div className="s">Immutable sensor evidence</div>
        </div>
        <div className="nx-stat">
          <div className="k">// Derivatives</div><div className="v" style={{ color: "#FFB020" }}>{counts.derivative || 0}</div>
          <div className="s">Generated · never overwrite originals</div>
        </div>
        <div className="nx-stat">
          <div className="k">// Package State</div>
          <div className="v" style={{ fontSize: 20, color: finalizedPkg ? "#00FF9C" : "#FFB020" }}>
            {finalizedPkg ? `v${finalizedPkg.package_version} FINALIZED` : "PENDING"}
          </div>
          <div className="s">
            {finalizedPkg
              ? `Digest ${finalizedPkg.manifest_digest.slice(0, 12)}…`
              : `Validation ${validation?.overall || "…"}`}
          </div>
        </div>
      </div>

      {/* Upload panel */}
      <h2 className="nx-h2"><span className="num">§01</span>Upload Evidence</h2>
      <div className="nx-panel">
        <div className="corner">// SD-007 CAPTURE FINALIZATION</div>
        <div className="nx-grid cols-3" style={{ marginBottom: 14 }}>
          <div>
            <label className="nx-label">Category</label>
            <select className="nx-select" value={selectedCat}
              onChange={(e) => setSelectedCat(e.target.value)}
              data-testid="nx-evidence-category">
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}{DERIVATIVE_ONLY.has(c) ? " (derivative)" : ""}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="nx-label">Mode</label>
            <select className="nx-select" value={mode} onChange={(e) => setMode(e.target.value)}
              data-testid="nx-evidence-mode">
              <option value="DEMO">DEMO · Preview only</option>
              <option value="PILOT">PILOT · Field validation</option>
              <option value="OPERATIONAL" disabled>OPERATIONAL · Awaiting validation program (§17)</option>
            </select>
          </div>
          <div>
            <label className="nx-label">Optional operator note</label>
            <input className="nx-input" value={operatorNote} onChange={(e) => setOperatorNote(e.target.value)}
              placeholder="Attached to OPERATOR_NOTE uploads" data-testid="nx-evidence-note" />
          </div>
        </div>

        <div
          ref={dropRef}
          onDragOver={(e) => { e.preventDefault(); dropRef.current?.classList.add("dragover"); }}
          onDragLeave={() => dropRef.current?.classList.remove("dragover")}
          onDrop={onDrop}
          style={{
            border: "2px dashed #2A3A4E", padding: "36px 20px",
            borderRadius: 4, textAlign: "center", background: "#06090F",
          }}
          data-testid="nx-evidence-drop"
        >
          <div style={{ fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.24em",
            color: "#8A9BAE", fontSize: 11, textTransform: "uppercase" }}>
            // DRAG FILES · OR
          </div>
          <input type="file" multiple onChange={(e) => onFiles(e.target.files)}
            data-testid="nx-evidence-file-input"
            style={{ marginTop: 12, color: "#E6EEF6" }} />
        </div>

        {Object.entries(uploads).length > 0 && (
          <div style={{ marginTop: 14 }}>
            {Object.entries(uploads).map(([name, s]) => (
              <div key={name} style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
                display: "flex", justifyContent: "space-between", padding: "4px 0", color: "#8A9BAE" }}>
                <span>{name}</span>
                <span style={{ color: s.err ? "#FF5A5F" : (s.done ? "#00FF9C" : "#4DF6FF") }}>
                  {s.err || (s.done ? "✓ Uploaded" : `${s.pct || 0}%`)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Requirement profile + Validation */}
      <h2 className="nx-h2"><span className="num">§02</span>Product Requirements · {profile?.display_name}</h2>
      <div className="nx-panel">
        <div className="corner">// {profile?.product_key?.toUpperCase()}</div>
        {profile?.requirements.map((r) => {
          const got = counts.byCat[r.category] || 0;
          const ok = got >= r.min_count;
          return (
            <div key={r.category} style={{
              display: "grid", gridTemplateColumns: "220px 1fr 100px 80px",
              alignItems: "center", padding: "8px 0", borderBottom: "1px solid #1D2836",
              fontSize: 12,
            }}>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "#4DF6FF", fontSize: 11 }}>
                {r.category}
              </span>
              <span style={{ color: "#E6EEF6" }}>{r.label}</span>
              <span style={{ color: "#8A9BAE" }}>{got} / {r.min_count}</span>
              <Pill kind={ok ? "ok" : (r.required ? "warn" : "dim")}>
                {ok ? "MET" : (r.required ? "REQUIRED" : "OPTIONAL")}
              </Pill>
            </div>
          );
        })}
      </div>

      {validation && (
        <>
          <h2 className="nx-h2"><span className="num">§03</span>Package Validation</h2>
          <div className="nx-panel">
            <div className="corner">// {validation.overall}</div>
            {validation.results.map((r, i) => (
              <div key={i} style={{ padding: "6px 0", borderBottom: "1px solid #1D2836",
                display: "grid", gridTemplateColumns: "120px 1fr", fontSize: 12 }}>
                <Pill kind={r.result === "PASS" ? "ok" : r.result === "FAIL" ? "warn" : "dim"}>
                  {r.result}
                </Pill>
                <span style={{ color: "#E6EEF6" }}>{r.message}</span>
              </div>
            ))}
            <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
              <button className="nx-btn ghost" onClick={load} data-testid="nx-revalidate-btn">
                Re-Validate
              </button>
              <button className="nx-btn" onClick={doFinalize}
                disabled={validation.overall !== "PASS" || finalizeBusy || !!finalizedPkg}
                data-testid="nx-finalize-btn">
                {finalizedPkg ? "Finalized" : "Finalize Package"}
              </button>
              {finalizedPkg && (
                <button className="nx-btn ghost" onClick={() => nxOpenManifestJson(finalizedPkg.canonical_id)}
                  data-testid="nx-download-manifest">
                  Download Manifest JSON
                </button>
              )}
            </div>
          </div>
        </>
      )}

      {/* Evidence inventory */}
      <h2 className="nx-h2"><span className="num">§04</span>Evidence Inventory</h2>
      {items.length === 0 ? (
        <div className="nx-empty">No evidence uploaded yet</div>
      ) : (
        <div className="nx-panel" style={{ padding: 0 }}>
          <table className="nx-table" data-testid="nx-evidence-table">
            <thead><tr>
              <th>Filename</th><th>Category</th><th>Role</th><th>Size</th><th>SHA-256</th><th>Mode</th><th></th>
            </tr></thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.canonical_id}>
                  <td style={{ fontSize: 12 }}>{it.original_filename}</td>
                  <td><Pill>{it.kind}</Pill></td>
                  <td>
                    <Pill kind={it.role === "original" ? "ok" : "gold"}>{it.role.toUpperCase()}</Pill>
                  </td>
                  <td style={{ fontSize: 11, color: "#8A9BAE" }}>{humanBytes(it.size_bytes)}</td>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#4DF6FF" }}>
                    {it.content_sha256.slice(0, 16)}…
                  </td>
                  <td><Pill kind="dim">{it.mode}</Pill></td>
                  <td>
                    <button className="nx-btn ghost small" onClick={() => openDrawer(it.canonical_id)}
                      data-testid={`nx-evidence-open-${it.canonical_id}`}>Inspect</button>{" "}
                    {!finalizedPkg && (
                      <button className="nx-btn ghost small" style={{ borderColor: "#FF5A5F", color: "#FF5A5F" }}
                        onClick={() => deletePending(it.canonical_id)}
                        data-testid={`nx-evidence-delete-${it.canonical_id}`}>Delete</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {err && <div className="nx-panel" style={{ borderColor: "#FF5A5F", color: "#FF5A5F", marginTop: 18 }}>
        {String(err)}
      </div>}

      {/* Detail drawer */}
      {drawer && (
        <div onClick={() => setDrawer(null)} style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 40,
        }}>
          <div onClick={(e) => e.stopPropagation()} style={{
            position: "absolute", right: 0, top: 0, bottom: 0, width: "min(560px, 92vw)",
            background: "#0B111A", borderLeft: "1px solid #2A3A4E", padding: 22, overflowY: "auto",
          }} data-testid="nx-evidence-drawer">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>// EVIDENCE DETAIL</div>
              <button className="nx-btn ghost small" onClick={() => setDrawer(null)}>Close</button>
            </div>
            {drawer.loading && <div className="nx-empty">Loading…</div>}
            {drawer.error && <div style={{ color: "#FF5A5F" }}>{drawer.error}</div>}
            {drawer.evidence && (
              <>
                <div style={{ marginBottom: 12 }}>
                  <div className="nx-label">Canonical ID</div>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", color: "#4DF6FF", fontSize: 11 }}>
                    {drawer.evidence.canonical_id}
                  </div>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <div className="nx-label">SHA-256</div>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", color: "#00FF9C", fontSize: 11, wordBreak: "break-all" }}>
                    {drawer.evidence.content_sha256}
                  </div>
                </div>
                <div style={{ marginBottom: 12 }}>
                  <div className="nx-label">Storage Key</div>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", color: "#8A9BAE", fontSize: 10, wordBreak: "break-all" }}>
                    {drawer.evidence.object_key}
                  </div>
                </div>
                <div className="nx-grid cols-2">
                  <div><div className="nx-label">Category</div><Pill>{drawer.evidence.kind}</Pill></div>
                  <div><div className="nx-label">Role</div>
                    <Pill kind={drawer.evidence.role === "original" ? "ok" : "gold"}>{drawer.evidence.role}</Pill>
                  </div>
                  <div><div className="nx-label">Size</div>{humanBytes(drawer.evidence.size_bytes)}</div>
                  <div><div className="nx-label">MIME</div>{drawer.evidence.mime}</div>
                  <div><div className="nx-label">Captured</div>{drawer.evidence.captured_at || "—"}</div>
                  <div><div className="nx-label">Uploaded</div>{drawer.evidence.created_at.slice(0, 19).replace("T", " ")}</div>
                </div>
                <h3 className="nx-label" style={{ marginTop: 18, marginBottom: 6 }}>Metadata (best effort)</h3>
                <pre style={{ background: "#06090F", padding: 10, fontSize: 10, color: "#8A9BAE",
                  border: "1px solid #1D2836", borderRadius: 3, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                  {JSON.stringify(drawer.metadata?.extracted || {}, null, 2)}
                </pre>
                <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                  <button className="nx-btn ghost small" onClick={() => retryMeta(drawer.evidence.canonical_id)}
                    data-testid="nx-retry-meta">Retry Metadata</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
