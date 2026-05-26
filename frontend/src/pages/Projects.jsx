import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { HudCard } from "@/components/HudCard";
import { listProjects } from "@/lib/api";
import { Plus, Folder, ArrowRight } from "lucide-react";

const STATUS_COLOR = {
  draft: "text-muted-hud",
  configured: "text-teal",
  scoped: "text-teal",
  priced: "text-teal",
  launched: "text-volt",
  complete: "text-volt",
};

export default function Projects() {
  const [items, setItems] = useState(null);
  useEffect(()=>{ listProjects().then(setItems).catch(()=>setItems([])); },[]);

  return (
    <div data-testid="projects-page" className="px-4 md:px-12 py-6 md:py-10 max-w-[1500px] mx-auto">
      <div className="flex items-center justify-between mb-6 gap-3 flex-wrap">
        <div>
          <div className="font-mono text-[10px] md:text-[11px] tracking-[0.32em] text-teal uppercase">// MISSION LEDGER</div>
          <h1 className="font-display text-2xl md:text-4xl uppercase tracking-[0.06em] md:tracking-[0.14em] text-silver" style={{ overflowWrap: "anywhere", wordBreak: "break-word" }}>Project Archive</h1>
        </div>
        <Link to="/mission/new" className="btn-hud pulse-glow" data-testid="projects-new-btn">
          <Plus size={14}/> New Mission
        </Link>
      </div>

      {items === null && <div className="text-muted-hud font-mono uppercase tracking-widest">Loading…</div>}
      {items && items.length === 0 && (
        <HudCard className="p-10 text-center">
          <Folder size={42} className="text-teal mx-auto mb-4" strokeWidth={1.2}/>
          <div className="font-display text-xl uppercase tracking-widest text-silver">No missions yet</div>
          <p className="text-muted-hud text-sm mt-2">Initiate your first autonomous mission to populate the ledger.</p>
          <div className="mt-6 flex justify-center"><Link to="/mission/new" className="btn-hud" data-testid="empty-new-mission">Initiate Mission</Link></div>
        </HudCard>
      )}

      {items && items.length > 0 && (
        <HudCard className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="hud-table">
              <thead><tr><th>Customer</th><th>Address</th><th>Type</th><th>Status</th><th>Final Total</th><th></th></tr></thead>
              <tbody data-testid="projects-table">
                {items.map((p)=>(
                  <tr key={p.id}>
                    <td className="text-silver whitespace-nowrap">{p.intake?.customer_name}</td>
                    <td className="text-muted-hud whitespace-nowrap">{p.intake?.property_address}</td>
                    <td><span className="tag-pill">{p.intake?.project_type}</span></td>
                    <td><span className={`font-mono uppercase tracking-widest ${STATUS_COLOR[p.status] || "text-muted-hud"}`}>{p.status}</span></td>
                    <td className="text-teal whitespace-nowrap">{p.pricing?.final_total ? `$${p.pricing.final_total.toLocaleString(undefined,{minimumFractionDigits:2})}` : "—"}</td>
                    <td><Link to={`/mission/${p.id}`} data-testid={`project-open-${p.id.slice(0,8)}`} className="text-teal hover:underline flex items-center gap-1 whitespace-nowrap">Open <ArrowRight size={12}/></Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </HudCard>
      )}
    </div>
  );
}
