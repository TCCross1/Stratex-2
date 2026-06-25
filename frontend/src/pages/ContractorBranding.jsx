// STRATEX™ — Contractor Branding & Profile
// Lets the contractor upload their logo and tweak business info that flows
// through to every dashboard surface AND every PDF deliverable.

import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { getContractor, saveContractor, resetContractor, DEFAULT_CONTRACTOR } from "@/lib/contractor";
import { StratexLogo } from "@/components/StratexBrand";
import { Upload, RotateCcw, ArrowRight } from "lucide-react";

export default function ContractorBranding() {
  const nav = useNavigate();
  const [brand, setBrand] = useState(getContractor);
  const fileRef = useRef(null);

  const update = (patch) => setBrand((b) => ({ ...b, ...patch }));

  const onPickLogo = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 4 * 1024 * 1024) {
      toast.error("Logo must be under 4 MB");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      update({ logo_url: reader.result });
      toast.success("Logo loaded · save to apply");
    };
    reader.readAsDataURL(file);
  };

  const onSave = () => {
    saveContractor(brand);
    toast.success("Branding saved · every dashboard & report will now use it");
  };

  const onReset = () => {
    const d = resetContractor();
    setBrand(d);
    toast.message("Reverted to American Roofing Company defaults");
  };

  return (
    <div
      data-testid="contractor-branding-page"
      className="min-h-screen text-slate-100 px-4 sm:px-8 py-8"
      style={{
        background:
          "radial-gradient(ellipse at 60% 0%, rgba(0,229,255,0.10) 0%, transparent 50%)," +
          "radial-gradient(ellipse at 10% 100%, rgba(212,184,106,0.08) 0%, transparent 55%)," +
          "#02060B",
        fontFamily: "'Sora', sans-serif",
      }}
    >
      <div className="max-w-[1100px] mx-auto">
        <div className="flex items-center justify-between mb-6">
          <StratexLogo height={36}/>
          <button
            data-testid="back-deck"
            onClick={() => nav("/deck")}
            className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md"
            style={{ background: "rgba(0,229,255,0.10)", border: "1px solid #00E5FF99", color: "#00E5FF" }}
          >
            ← Command Deck
          </button>
        </div>

        <div className="font-mono text-[10px] tracking-[0.32em] text-cyan-400 uppercase mb-2">
          // CONTRACTOR PROFILE · BRAND IDENTITY
        </div>
        <h1 className="font-display uppercase tracking-[0.04em] text-4xl sm:text-5xl text-white leading-[1.05]">
          Your <span style={{ color: "#D4B86A", textShadow: "0 0 18px rgba(212,184,106,0.5)" }}>Brand</span>, Everywhere
        </h1>
        <p className="font-mono text-[11px] tracking-[0.14em] text-slate-400 mt-3 max-w-2xl uppercase">
          Upload your logo and verify your business profile. STRATEX will paint it across the Command Deck,
          adjuster reports, homeowner deliverables and 3-D twin overlays.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-6 mt-8">
          {/* ─── LOGO UPLOAD ─── */}
          <div className="rounded-2xl p-5"
               style={{ background: "rgba(8,14,24,0.86)", border: "1.5px solid rgba(212,184,106,0.55)",
                        boxShadow: "0 0 36px rgba(212,184,106,0.10) inset" }}>
            <div className="font-mono text-[10px] tracking-[0.28em] uppercase mb-3" style={{ color: "#D4B86A" }}>
              // PRIMARY LOGO
            </div>
            <div className="rounded-md p-6 flex items-center justify-center min-h-[220px]"
                 style={{ background: "rgba(255,255,255,0.04)", border: "1px dashed rgba(212,184,106,0.45)" }}>
              {brand.logo_url ? (
                <img src={brand.logo_url} alt="Contractor logo preview"
                     data-testid="logo-preview"
                     style={{ maxHeight: 180, maxWidth: "100%", objectFit: "contain" }}/>
              ) : (
                <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-slate-500">
                  No logo loaded
                </span>
              )}
            </div>
            <input ref={fileRef} type="file" accept="image/*" hidden onChange={onPickLogo}
                   data-testid="logo-file-input"/>
            <div className="flex gap-2 mt-4">
              <button
                data-testid="upload-logo-btn"
                onClick={() => fileRef.current?.click()}
                className="flex-1 flex items-center justify-center gap-2 font-mono text-[10.5px] tracking-[0.22em] uppercase py-2.5 rounded-md transition hover:brightness-125"
                style={{ background: "rgba(212,184,106,0.12)", border: "1px solid #D4B86A99", color: "#F5E0A3" }}
              >
                <Upload size={14}/> Upload Logo
              </button>
              <button
                data-testid="reset-defaults-btn"
                onClick={onReset}
                className="flex items-center gap-2 font-mono text-[10.5px] tracking-[0.22em] uppercase py-2.5 px-4 rounded-md"
                style={{ background: "rgba(255,45,120,0.10)", border: "1px solid #FF2D7899", color: "#FF2D78" }}
              >
                <RotateCcw size={14}/>
              </button>
            </div>
            <div className="mt-3 font-mono text-[9.5px] tracking-[0.16em] uppercase text-slate-500 leading-relaxed">
              PNG · JPG · SVG · WEBP · &lt;4 MB. Transparent background recommended.
            </div>
          </div>

          {/* ─── BUSINESS INFO FORM ─── */}
          <div className="rounded-2xl p-5"
               style={{ background: "rgba(8,14,24,0.86)", border: "1.5px solid rgba(0,229,255,0.55)",
                        boxShadow: "0 0 36px rgba(0,229,255,0.10) inset" }}>
            <div className="font-mono text-[10px] tracking-[0.28em] uppercase mb-3 text-cyan-400">
              // BUSINESS PROFILE
            </div>
            {[
              { k: "business_name",    l: "Business Name" },
              { k: "tagline",          l: "Tagline" },
              { k: "primary_contact",  l: "Primary Contact" },
              { k: "contact_title",    l: "Contact Title" },
              { k: "license_no",       l: "License No." },
              { k: "license_level",    l: "License Level" },
              { k: "address",          l: "Address" },
              { k: "city_state",       l: "City, State ZIP" },
              { k: "phone",            l: "Phone" },
              { k: "email",            l: "Email" },
              { k: "website",          l: "Website" },
            ].map((f) => (
              <label key={f.k} className="block mb-2">
                <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-400">{f.l}</span>
                <input
                  data-testid={`field-${f.k}`}
                  type="text"
                  value={brand[f.k] || ""}
                  onChange={(e) => update({ [f.k]: e.target.value })}
                  className="w-full mt-0.5 px-3 py-1.5 bg-transparent outline-none font-mono text-[11.5px] tracking-[0.04em] text-white rounded-sm"
                  style={{ background: "rgba(0,229,255,0.04)", border: "1px solid rgba(0,229,255,0.35)" }}
                />
              </label>
            ))}
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            data-testid="save-branding-btn"
            onClick={onSave}
            className="flex items-center gap-2 font-mono text-[11px] tracking-[0.22em] uppercase py-3 px-6 rounded-md transition hover:brightness-125"
            style={{ background: "#00E5FF", color: "#02060B", boxShadow: "0 0 22px rgba(0,229,255,0.55)" }}
          >
            Save & Apply Branding <ArrowRight size={14}/>
          </button>
        </div>
      </div>
    </div>
  );
}
