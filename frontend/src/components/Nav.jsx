import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ASSETS } from "@/lib/constants";
import { useAuth } from "@/lib/auth";
import { Radar, Plus, Layers, Lock, FileText, Menu, X, LogOut, LogIn, Shield, ClipboardList, Truck, CreditCard, Target, Activity, Plane, Snowflake, CloudLightning, Command, Calculator, Atom } from "lucide-react";

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

const CONTRACTOR_ITEMS = [
  { to: "/contractor", label: "Pipeline", icon: Layers, testid: "nav-pipeline" },
  { to: "/contractor/jobs/new", label: "New Job", icon: Plus, testid: "nav-new-job" },
  { to: "/contractor/materials", label: "Business Brain", icon: Lock, testid: "nav-materials" },
  { to: "/contractor/quote-builder", label: "Quote Builder", icon: Calculator, testid: "nav-quote-builder" },
  { to: "/fleet", label: "Fleet", icon: Truck, testid: "nav-fleet" },
  { to: "/billing", label: "Billing", icon: CreditCard, testid: "nav-billing" },
];
const OPERATOR_ITEMS = [
  { to: "/pilot", label: "Pilot Tablet", icon: Plane, testid: "nav-pilot-app" },
  { to: "/operator", label: "Job Board", icon: ClipboardList, testid: "nav-operator-board" },
  { to: "/fleet", label: "Fleet", icon: Truck, testid: "nav-operator-fleet" },
];
const ADMIN_ITEMS = [
  { to: "/admin/ops", label: "Ops Command", icon: Command, testid: "nav-admin-ops" },
  { to: "/admin/branch-console", label: "Branch Console", icon: Atom, testid: "nav-admin-branch" },
  { to: "/admin/sales", label: "Sales Hub", icon: Target, testid: "nav-admin-sales" },
  { to: "/admin/overseer", label: "Overseer", icon: Activity, testid: "nav-admin-overseer" },
  { to: "/admin/flight-audit", label: "Flight Audit", icon: Plane, testid: "nav-admin-flight-audit" },
  { to: "/admin/cv-ice-shield", label: "I&W Shield", icon: Snowflake, testid: "nav-admin-cv-ice-shield" },
  { to: "/admin/weather", label: "Weather", icon: CloudLightning, testid: "nav-admin-weather" },
  { to: "/fleet/live-map", label: "Live Theater", icon: Radar, testid: "nav-admin-fleet-live" },
  { to: "/fleet", label: "Fleet", icon: Truck, testid: "nav-admin-fleet" },
];
const ANON_ITEMS = [
  { to: "/", label: "Command", icon: Radar, testid: "nav-command" },
];

export default function Nav({ role }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const items = role === "contractor" ? CONTRACTOR_ITEMS : role === "operator" ? OPERATOR_ITEMS : role === "admin" ? ADMIN_ITEMS : ANON_ITEMS;

  const doLogout = () => {
    logout();
    setOpen(false);
    navigate("/", { replace: true });
  };

  return (
    <nav data-testid="primary-nav" className="sticky top-0 z-50 backdrop-blur-md bg-[#06080B]/85 border-b border-[#00F0FF]/15 safe-top">
      <div className="max-w-[1600px] mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-3">
        <Link to={user ? (user.role === "admin" ? "/admin/sales" : user.role === "operator" ? "/operator" : "/contractor") : "/"} data-testid="nav-home-logo" className="flex items-center gap-3 min-w-0" onClick={()=>setOpen(false)}>
          <img src={ASSETS.logo} alt="STRATEX" className="h-8 md:h-9 w-auto"/>
          <div className="hidden sm:flex flex-col leading-tight min-w-0">
            <span className="font-display text-[10px] tracking-[0.34em] text-muted-hud truncate">STRATEGIC THERMAL RECON</span>
            <span className="font-display text-[11px] tracking-[0.34em] text-teal glow-teal truncate">/ TOPOLOGY ESTIMATOR</span>
          </div>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1">
          {items.map((it) => <NavLink key={it.to} {...it} />)}
        </div>

        <div className="hidden lg:flex items-center gap-3 text-[11px] font-mono text-muted-hud">
          {user ? (
            <>
              <span className="flex items-center gap-2"><Shield size={12} className="text-volt"/><span className="text-volt uppercase tracking-widest">{user.role}</span><span className="text-muted-hud">• {user.email}</span></span>
              <button onClick={doLogout} data-testid="nav-logout" className="flex items-center gap-1 text-plasma hover:text-silver uppercase tracking-widest"><LogOut size={12}/> Logout</button>
            </>
          ) : null}
        </div>

        {/* Mobile menu button */}
        <button
          onClick={() => { try{navigator.vibrate?.(8);}catch(_){}; setOpen(!open); }}
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
          {items.map((it) => (
            <NavLink key={it.to} {...it} onClick={() => setOpen(false)} />
          ))}
          <div className="mt-2 border-t border-[#00F0FF]/10 pt-2 flex items-center justify-between text-[11px] font-mono text-muted-hud">
            {user ? (
              <>
                <span className="flex items-center gap-1"><Shield size={11} className="text-volt"/><span className="text-volt uppercase tracking-widest">{user.role}</span></span>
                <button onClick={doLogout} data-testid="nav-logout-mobile" className="flex items-center gap-1 text-plasma uppercase tracking-widest"><LogOut size={11}/> Logout</button>
              </>
            ) : null}
          </div>
        </div>
      )}
    </nav>
  );
}
