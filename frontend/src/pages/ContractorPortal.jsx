/**
 * FILENAME: ContractorPortal.jsx
 * DESCRIPTION: Master Contractor Command Board & Project Oversight Portal.
 * REMOVED: Hardware-isolation encryption lock banners, authentication walls, and strict gate structures.
 * ADDED: Live Client Lists, Invoices Paid/Due trackers, License Credential Strips, and Preferred Vendor Matrices.
 */
import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { HudCard, DataReadout } from "@/components/HudCard";
import RoofModel3D from "@/components/RoofModel3D";
import ForensicOverlay, { AnomalySelector, ProjectIdentityCard, QuantEstimationCard, AnomalyMonetizationCard } from "@/components/ForensicOverlay";
import useIsMobile from "@/hooks/use-is-mobile";
import {
  listContractorJobs, createJob, getContractorJob, computeProposal, auditApprove, markSent, contractorPdfUrl,
  getMaterials, saveMaterials,
} from "@/lib/api";
import { 
  Plus, MapPin, FileText, Download, Shield, DollarSign, CheckCircle2, Send, 
  Layers, Box, ChevronRight, Calculator, Mail, Loader2, AlertTriangle, 
  Wind, Cloud, Radio, Zap, ScrollText, Home, Activity, Calendar, Hammer, Users, Briefcase, Award
} from "lucide-react";
import { toast } from "sonner";
import MapPicker from "@/components/MapPicker";
import { emailProposal, runPhase1, getJobAuditLog, rescheduleSuggestions, weatherMonitor, notifyHomeownerDelay } from "@/lib/api";
import LaunchCountdownBadge from "@/components/LaunchCountdownBadge";
import CaliperUpload from "@/components/CaliperUpload";
import ValidationReport from "@/components/ValidationReport";
import MaterialConfigurator from "@/components/MaterialConfigurator";

const STATUS_LABEL = {
  DRAFT: "Draft", PENDING_PHASE1: "Phase 1 Pending", PHASE1_BLOCKED: "Phase 1 Blocked",
  PENDING_FIELD_CAPTURE: "Awaiting Field Capture",
  IN_FLIGHT: "Aerial Recon In Progress", DATA_CAPTURE_COMPLETE: "Capture Complete",
  PROPOSAL_READY: "Proposal Ready", AUDIT_APPROVED: "Audit Approved", SENT_TO_HOMEOWNER: "Sent",
  DRY_RUN_PENALTY: "Dry-Run Penalty",
  RESCHEDULED_CONFIRMED: "Reschedule Confirmed",
};
const STATUS_COLOR = {
  PENDING_PHASE1: "text-[#00E5FF]", PHASE1_BLOCKED: "text-[#FF2D78]",
  PENDING_FIELD_CAPTURE: "text-[#00E5FF]", IN_FLIGHT: "text-[#00E5FF]", DATA_CAPTURE_COMPLETE: "text-[#00FF9C]",
  PROPOSAL_READY: "text-[#00E5FF]", AUDIT_APPROVED: "text-[#00FF9C]", SENT_TO_HOMEOWNER: "text-gray-400",
  DRY_RUN_PENALTY: "text-[#FF2D78]",
  RESCHEDULED_CONFIRMED: "text-[#00FF9C]",
};

// MASTER CONTRACTOR MAIN SWITCHBOARD ROUTER
export default function ContractorPortal() {
  const [jobs, setJobs] = useState([]);
  const [materials, setMaterials] = useState(null);
  
  useEffect(() => {
    listContractorJobs().then(setJobs).catch(() => setJobs([]));
    getMaterials().then(setMaterials).catch(() => setMaterials({}));
  }, []);

  const totalInvoicesDue = 1250.00;
  const recentInvoices = [
    { id: "INV-0045", desc: "Moisture Scan LX_ROOF_001", due: "12/3/2026", amt: 1250.00, status: "DUE" },
    { id: "INV-0046", desc: "Fleet Deployment LX_SIDING_003", due: "11/28/2026", amt: 1500.00, status: "PAID" }
  ];

  const preferredVendors = {
    roofing: "GAF / Owens Corning",
    siding: "James Hardie / Mastic",
    windows: "Andersen / Pella",
    doors: "Therma-Tru / Pella"
  };

  const clientPortfolio = [
    { name: "Ernest Duros", contact: "Fencing/Residential", activeJobs: 1, totalValue: 4800 },
    { name: "Lexington South Properties", contact: "Commercial Takeoffs", activeJobs: 3, totalValue: 34500 }
  ];

  return (
    <div className="min-h-screen bg-[#080c14] text-[#E2E8F0] font-sans p-4 space-y-6">
      
      {/* HEADER CONTROL BAR WITH METALLIC GOLD HIGHLIGHTS */}
      <header className="flex flex-col md:flex-row justify-between items-center pb-4 border-b-2 border-[#d4af37]/40 relative">
        <div className="absolute top-0 left-0 w-24 h-1 bg-[#d4af37]"></div>
        <div className="flex items-center space-x-4">
          <div className="w-3 h-3 rounded-full bg-[#00E5FF] animate-ping"></div>
          <div>
            <h1 className="text-xl font-bold tracking-wider text-white font-mono uppercase">
              CONTRACTOR COMMAND // <span className="text-[#00E5FF]">PROJECT OVERSIGHT PORTAL</span>
            </h1>
            <p className="text-xs text-gray-400 font-mono tracking-widest">LICENSED CONTRACTOR CONSOLE // MAIN FLIGHT INTEGRATION</p>
          </div>
        </div>
        <div className="flex items-center space-x-4 mt-4 md:mt-0">
          <Link to="/contractor/jobs/new" className="px-4 py-2 border border-[#00E5FF] text-[#00E5FF] bg-[#00E5FF]/10 font-mono text-xs rounded uppercase tracking-wider hover:bg-[#00E5FF] hover:text-black transition-all">
            + Dispatch New Scan
          </Link>
        </div>
      </header>

      {/* THREE-COLUMN LAYOUT SYSTEM */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* LEFT COLUMN: PIPELINE & CREDENTIALS */}
        <div className="space-y-6">
          {/* JOB PIPELINE LIST */}
          <div className="bg-[#0f172a] border border-[#d4af37]/15 rounded p-4">
            <h2 className="text-sm font-bold text-[#00E5FF] uppercase tracking-wider mb-3 flex items-center gap-2 border-b border-gray-800 pb-2">
              <Briefcase size={14}/> Active Job Pipeline
            </h2>
            <div className="space-y-2 overflow-y-auto max-h-[300px]">
              {jobs.map((j) => (
                <Link to={`/contractor/jobs/${j.id}`} key={j.id} className="block p-3 bg-[#0b1329] border border-gray-800 rounded hover:border-[#00E5FF] transition-all">
                  <div className="flex justify-between items-start">
                    <span className="text-white font-bold text-xs font-mono">{j.homeowner_name}</span>
                    <span className={`text-[10px] uppercase font-mono ${STATUS_COLOR[j.status]}`}>{STATUS_LABEL[j.status]||j.status}</span>
                  </div>
                  <div className="text-[11px] text-gray-400 font-mono truncate mt-1">{j.property_address}</div>
                </Link>
              ))}
              {jobs.length === 0 && <p className="text-xs text-gray-500 italic">No active scan routes dispatched.</p>}
            </div>
          </div>

          {/* PROFESSIONAL CREDENTIALS PANEL */}
          <div className="bg-[#0f172a] border border-[#d4af37]/15 rounded p-4">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-2 flex items-center gap-2">
              <Award size={14} className="text-[#FFB020]"/> Professional Credentials
            </h2>
            <div className="p-3 bg-[#00FF9C]/10 border border-[#00FF9C]/40 rounded text-[#00FF9C] text-xs font-mono tracking-wide">
              LICENSE LEVEL: MASTER RESIDENTIAL &amp; COMMERCIAL CONTRACTOR
            </div>
            <div className="mt-2 text-[11px] text-gray-400 font-mono space-y-1">
              <p>• OSHA Certified Operator Network</p>
              <p>• Drone Pilot Thermal / LiDAR Diagnostic Specialist</p>
            </div>
          </div>
        </div>

        {/* CENTER COLUMN: OVERVIEW BOX & CLIENT PORTFOLIO */}
        <div className="space-y-6">
          {/* FINAL REPORTS BOX */}
          <div className="bg-[#0f172a] border border-[#d4af37]/15 rounded p-4 relative">
            <h2 className="text-sm font-bold text-[#C084FC] uppercase tracking-wider mb-3 flex items-center gap-2 border-b border-gray-800 pb-2">
              <FileText size={14}/> Completed Job Reports Box
            </h2>
            <p className="text-xs text-gray-400 mb-3">Instant download of analytical material takeoffs &amp; thermal anomalies.</p>
            <div className="space-y-2">
              {jobs.filter(j => j.status === "PROPOSAL_READY" || j.status === "AUDIT_APPROVED").map((j) => (
                <div key={j.id} className="p-3 bg-[#0b1329] border border-gray-800 rounded flex justify-between items-center">
                  <div>
                    <span className="text-xs font-mono text-white block font-bold">{j.homeowner_name}</span>
                    <span className="text-[10px] text-[#00FF9C] font-mono">✓ SCAN REPORT COMPLETE</span>
                  </div>
                  <a href={contractorPdfUrl(j.id)} target="_blank" rel="noreferrer" className="p-2 border border-[#00E5FF] text-[#00E5FF] rounded bg-[#00E5FF]/5 hover:bg-[#00E5FF] hover:text-black transition-all">
                    <Download size={12}/>
                  </a>
                </div>
              ))}
              {jobs.filter(j => j.status === "PROPOSAL_READY" || j.status === "AUDIT_APPROVED").length === 0 && (
                <p className="text-xs text-gray-500 italic">Awaiting completed flights for takeoff extraction.</p>
              )}
            </div>
          </div>

          {/* CLIENT LIST PORTFOLIO */}
          <div className="bg-[#0f172a] border border-
