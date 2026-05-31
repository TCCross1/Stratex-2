/**
 * ConsensusBadge — public, read-only deliverable badge.
 *
 * Hits the public summary endpoint (no auth) so contractors can drop it
 * inline on the deliverable page without leaking inner agent payloads.
 */
import React, { useEffect, useState } from "react";
import axios from "axios";
import { ShieldCheck, AlertTriangle } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ConsensusBadge({ jobId }) {
  const [data, setData] = useState(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await axios.get(`${API}/consensus/public/by-job/${jobId}`);
        if (!cancelled) setData(data);
      } catch (_) {
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => { cancelled = true; };
  }, [jobId]);

  if (!loaded) return null;
  if (!data || !data.verification_status) return null;

  const authenticated = data.verification_status === "AUTHENTICATED";
  const color = authenticated ? "#10b981" : "#f59e0b";
  const Icon = authenticated ? ShieldCheck : AlertTriangle;

  return (
    <div
      data-testid="deliverable-consensus-badge"
      title={`Consensus score: ${(data.consensus_score ?? 0).toFixed(1)}% · ${data.created_at || ""}`}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        padding: "4px 10px", borderRadius: 999,
        border: `1px solid ${color}55`,
        background: `${color}10`,
        color, fontFamily: "monospace",
        fontSize: 10, letterSpacing: "0.2em", textTransform: "uppercase",
      }}
    >
      <Icon size={11}/>
      {authenticated
        ? `4/4 CONSENSUS · ${(data.consensus_score ?? 100).toFixed(0)}%`
        : "VARIANCE FLAGGED · ADMIN REVIEW"}
    </div>
  );
}
