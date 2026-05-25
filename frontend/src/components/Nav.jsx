import React from "react";
import { Link, useLocation } from "react-router-dom";
import { ASSETS } from "@/lib/constants";
import { Radar, Plus, Layers, Truck, FileText } from "lucide-react";

const NavLink = ({ to, label, icon: Icon, testid }) => {
  const loc = useLocation();
  const active = loc.pathname === to || (to !== "/" && loc.pathname.startsWith(to));
  return (
    <Link
      to={to}
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
  return (
    <nav data-testid="primary-nav" className="sticky top-0 z-50 backdrop-blur-md bg-[#06080B]/85 border-b border-[#00F0FF]/15">
      <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
        <Link to="/" data-testid="nav-home-logo" className="flex items-center gap-3">
          <img src={ASSETS.logo} alt="STRATEX" className="h-9 w-auto" />
          <div className="hidden sm:flex flex-col leading-tight">
            <span className="font-display text-[10px] tracking-[0.34em] text-muted-hud">STRATEGIC THERMAL RECON</span>
            <span className="font-display text-[11px] tracking-[0.34em] text-teal glow-teal">/ TOPOLOGY ESTIMATOR</span>
          </div>
        </Link>
        <div className="flex items-center gap-1">
          <NavLink to="/" label="Command" icon={Radar} testid="nav-command" />
          <NavLink to="/mission/new" label="New Mission" icon={Plus} testid="nav-new-mission" />
          <NavLink to="/projects" label="Projects" icon={Layers} testid="nav-projects" />
          <NavLink to="/fleet" label="Fleet" icon={Truck} testid="nav-fleet" />
          <NavLink to="/reports" label="Reports" icon={FileText} testid="nav-reports" />
        </div>
        <div className="hidden md:flex items-center gap-3 text-[11px] font-mono text-muted-hud">
          <span className="led led-ok inline-block" /> <span>UPLINK STARLINK • OK</span>
        </div>
      </div>
    </nav>
  );
}
