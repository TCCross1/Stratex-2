import React, { useEffect, useState } from "react";
import { HudCard, SectionTitle } from "@/components/HudCard";
import { listProjects, pdfUrl } from "@/lib/api";
import { FileText, Download } from "lucide-react";

export default function Reports() {
  const [items, setItems] = useState([]);
  useEffect(()=>{ listProjects().then(setItems).catch(()=>setItems([])); },[]);
  const completed = items.filter((p)=>p.status === "complete");

  return (
    <div data-testid="reports-page" className="px-6 md:px-12 py-10 max-w-[1500px] mx-auto">
      <SectionTitle eyebrow="// FORENSIC REPORT LIBRARY" title="Insurance-Grade Reports"/>
      {completed.length === 0 && (
        <HudCard className="p-10 text-center">
          <FileText size={42} className="text-teal mx-auto mb-4" strokeWidth={1.2}/>
          <div className="font-display text-xl uppercase tracking-widest text-silver">No completed missions yet</div>
          <p className="text-muted-hud text-sm mt-2">Reports auto-publish after an authorized recon completes.</p>
        </HudCard>
      )}
      <div className="grid md:grid-cols-2 gap-4">
        {completed.map((p)=>(
          <HudCard key={p.id} className="p-5" data-testid={`report-${p.id.slice(0,8)}`}>
            <div className="font-mono text-[10px] tracking-widest uppercase text-muted-hud mb-1">REPORT • {p.id.slice(0,8)}</div>
            <div className="font-display text-xl uppercase tracking-widest text-silver">{p.intake?.customer_name}</div>
            <div className="font-mono text-xs text-muted-hud mb-3">{p.intake?.property_address}</div>
            <p className="text-sm text-silver leading-relaxed">{(p.agent_reports?.forensic || "").slice(0, 240)}…</p>
            <div className="mt-4 flex items-center justify-between">
              <span className="tag-pill">{p.intake?.project_type}</span>
              <div className="flex items-center gap-3">
                <span className="font-mono text-teal">${(p.pricing?.final_total||0).toLocaleString(undefined,{minimumFractionDigits:2})}</span>
                <a href={pdfUrl(p.id)} target="_blank" rel="noreferrer" data-testid={`report-pdf-${p.id.slice(0,8)}`} className="btn-hud btn-hud-ghost text-[10px] py-1 px-2"><Download size={12}/> PDF</a>
              </div>
            </div>
          </HudCard>
        ))}
      </div>
    </div>
  );
}
