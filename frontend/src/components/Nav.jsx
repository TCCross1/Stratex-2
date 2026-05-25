import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ASSETS } from "@/lib/constants";
import { Radar, Plus, Layers, Truck, FileText, Menu, X } from "lucide-react";

const ITEMS = [
  { to: "/",            label: "Command",     icon: Radar,    testid: "nav-command" },
  { to: "/mission/new", label: "New Mission", icon: Plus,     testid: "nav-new-mission" },
  { to: "/projects",    label: "Projects",    icon: Layers,   testid: "nav-projects" },
  { to: "/fleet",       label: "Fleet",       icon: Truck,    testid: "nav-fleet" },
  { to: "/reports",     label: "Reports",     icon: FileText, testid: "nav-reports" },
];

const NavLink = ({ to, label, icon: Icon, testid, onClick }) => {
  const loc = useLocation();
  const active = loc.pathname === to || (to !== "/" && loc.pathname.startsWith(to));
  return (
    <Link
      to={to}
      onClick={onClick}
      data-testid={testid}
      className={`flex items-center gap-2 px-3 py-2 text-[12px] uppercase tracking-[0.2em] font-heading font-semibold border transition-all ${
        active
          ? "border-[#00F0FF] text-[#00F0FF] bg-[#00F0FF]/10 shadow-[0_0_16px_rgba(0,240,255,0.35)]"
          : "border-transparent text-silver hover:text-[#00F0FF] hover:border-[#00F0FF]/40"
      }`}
    >
      <Icon size={14} strokeWidth={1.5} />
      <span>{label}</span>
    </Link>
  );
};

export default function Nav() {
  const [open, setOpen] = useState(false);
  return (
    <nav data-testid="primary-nav" className="sticky top-0 z-50 backdrop-blur-md bg-[#06080B]/85 border-b border-[#00F0FF]/15 safe-top">
      <div className="max-w-[1600px] mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-3">
        <Link to="/" data-testid="nav-home-logo" className="flex items-center gap-3 min-w-0" onClick={()=>setOpen(false)}>
          <img src={ASSETS.logo} alt="STRATEX" className="h-8 md:h-9 w-auto"/>
          <div className="hidden sm:flex flex-col leading-tight min-w-0">
            <span className="font-display text-[10px] tracking-[0.34em] text-muted-hud truncate">STRATEGIC THERMAL RECON</span>
            <span className="font-display text-[11px] tracking-[0.34em] text-teal glow-teal truncate">/ TOPOLOGY ESTIMATOR</span>
          </div>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1">
          {ITEMS.map((it) => <NavLink key={it.to} {...it} />)}
        </div>

        <div className="hidden lg:flex items-center gap-2 text-[11px] font-mono text-muted-hud">
          <span className="led led-ok inline-block"/> <span>UPLINK STARLINK • OK</span>
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => setOpen(!open)}
          data-testid="nav-mobile-toggle"
          aria-label="Toggle menu"
          className="md:hidden w-11 h-11 flex items-center justify-center border border-[#00F0FF]/40 text-teal"
          style={{ minWidth: 44, minHeight: 44 }}
        >
          {open ? <X size={20}/> : <Menu size={20}/>}
        </button>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div data-testid="nav-mobile-drawer" className="md:hidden border-t border-[#00F0FF]/15 bg-[#06080B]/95 backdrop-blur-md px-4 py-3 flex flex-col gap-1.5 safe-bottom">
          {ITEMS.map((it) => (
            <NavLink key={it.to} {...it} onClick={() => setOpen(false)} />
          ))}
          <div className="flex items-center gap-2 mt-2 text-[11px] font-mono text-muted-hud">
            <span className="led led-ok inline-block"/> UPLINK STARLINK • OK
          </div>
        </div>
      )}
    </nav>
  );
}
