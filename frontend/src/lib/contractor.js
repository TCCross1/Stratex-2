// STRATEX™ — Contractor brand registry (single-source-of-truth).
//
// One small module that any page or report can import to read the active
// contractor's logo, business name, license, address and primary contact.
// Backed by localStorage so the demo can be re-branded in one click without a
// backend round-trip — perfect for tomorrow's American Roofing Company pitch.
//
// On first boot we seed AMERICAN ROOFING COMPANY · Regency Road · Lexington KY
// as the active contractor, so every screen and every PDF deliverable carries
// their branding out of the box.

const STORAGE_KEY = "stratex.contractor.brand.v1";

export const DEFAULT_CONTRACTOR = {
  business_name: "American Roofing Company",
  tagline: "Changing the Industry",
  logo_url: "/contractors/american_roofing.jpg",
  primary_contact: "Anthony Cross",
  contact_title: "Master Contractor",
  license_no: "BC-0043",
  license_level: "MASTER · RESIDENTIAL & COMMERCIAL",
  certifications: ["OSHA CERTIFIED", "DRONE PILOT · THERMAL/LIDAR SPECIALIST"],
  address: "2440 Regency Road",
  city_state: "Lexington, KY 40503",
  phone: "(859) 555-0143",
  email: "ops@americanroofing.co",
  website: "americanroofing.co",
  status: "ACTIVE",
  // Demo numbers used across dashboards & deliverables.
  metrics: {
    current_balance_usd: 1250.0,
    total_units: 5,
    active_scans: 3,
    queued: 2,
    alerts: 1,
    total_finalized_reports: 12,
  },
};

export function getContractor() {
  if (typeof window === "undefined") return DEFAULT_CONTRACTOR;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_CONTRACTOR;
    const parsed = JSON.parse(raw);
    // Merge so newly added defaults still flow through.
    return { ...DEFAULT_CONTRACTOR, ...parsed };
  } catch {
    return DEFAULT_CONTRACTOR;
  }
}

export function saveContractor(patch) {
  if (typeof window === "undefined") return;
  const current = getContractor();
  const next = { ...current, ...patch };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  // Notify any listening dashboards in the same tab.
  window.dispatchEvent(new CustomEvent("stratex:contractor-updated", { detail: next }));
  return next;
}

export function resetContractor() {
  if (typeof window === "undefined") return DEFAULT_CONTRACTOR;
  window.localStorage.removeItem(STORAGE_KEY);
  window.dispatchEvent(new CustomEvent("stratex:contractor-updated", { detail: DEFAULT_CONTRACTOR }));
  return DEFAULT_CONTRACTOR;
}

// React hook — keeps the page in sync if the contractor is updated elsewhere.
import { useEffect, useState } from "react";
export function useContractor() {
  const [brand, setBrand] = useState(getContractor);
  useEffect(() => {
    const handler = (e) => setBrand(e.detail || getContractor());
    window.addEventListener("stratex:contractor-updated", handler);
    return () => window.removeEventListener("stratex:contractor-updated", handler);
  }, []);
  return brand;
}
