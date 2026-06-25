import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/lib/auth";
import Nav from "@/components/Nav";
import TcAssistant from "@/components/TcAssistant";
import BackToLauncher from "@/components/BackToLauncher";
import Landing from "@/pages/Landing";
import Switchboard from "@/pages/Switchboard";
import CommandDeck from "@/pages/CommandDeck";
import ContractorBranding from "@/pages/ContractorBranding";
import ReportsBinder from "@/pages/ReportsBinder";
import PassportPortal from "@/pages/PassportPortal";
import ContractorVerify from "@/pages/ContractorVerify";
import GmRoster from "@/pages/GmRoster";
import MissionControl from "@/pages/MissionControl";
import DemoScanWizard from "@/pages/DemoScanWizard";
import AuthPage from "@/pages/AuthPage";
import AuthCallback from "@/pages/AuthCallback";
import NDAPage from "@/pages/NDAPage";
import { ContractorJobs, NewJob, JobDetail, MaterialsConfig } from "@/pages/ContractorPortal";
import { OperatorBoard, OperatorJobDetail } from "@/pages/OperatorTerminal";
import FleetBoard from "@/pages/FleetBoard";
import Pricing, { BillingSuccess } from "@/pages/Pricing";
import NeonLayerPreview from "@/pages/NeonLayerPreview";
import RoofAuditHarness from "@/pages/RoofAuditHarness";
import OnboardingROI from "@/pages/OnboardingROI";
import AdminSalesHub from "@/pages/AdminSalesHub";
import OverseerQueue from "@/pages/OverseerQueue";
import FleetLaunch from "@/pages/FleetLaunch";
import FlightAudit from "@/pages/FlightAudit";
import CVIceShield from "@/pages/CVIceShield";
import AdminWeather from "@/pages/AdminWeather";
import AdminOps from "@/pages/AdminOps";
import QuoteBuilder from "@/pages/QuoteBuilder";
import BranchConsole from "@/pages/BranchConsole";
import ContractorDeliverable from "@/pages/ContractorDeliverable";
import DeliverableDeck from "@/pages/DeliverableDeck";
import SimulationRun from "@/pages/SimulationRun";
import CeoLogin from "@/pages/CeoLogin";
import CeoCommandCenter from "@/pages/CeoCommandCenter";
import SupplyPipeline from "@/pages/SupplyPipeline";
import InventoryCost from "@/pages/InventoryCost";
import AdminConsensus from "@/pages/AdminConsensus";
import PilotDashboard from "@/pages/PilotDashboard";
import PilotJobSheet from "@/pages/PilotJobSheet";
import PilotPreflight from "@/pages/PilotPreflight";
import FleetLiveMap from "@/pages/FleetLiveMap";
import RegionalSwitchboard from "@/pages/RegionalSwitchboard";
import MduFleetPortal from "@/pages/MduFleetPortal";
import BlacklistMatrix from "@/pages/BlacklistMatrix";
import CeoSuppliers from "@/pages/CeoSuppliers";
import CeoOpsPage from "@/pages/CeoOpsPage";
import GmOpsPage from "@/pages/GmOpsPage";
import InvestorAssistant from "@/components/InvestorAssistant";

function Protected({ role, children }) {
  const { user } = useAuth();
  const loc = useLocation();
  if (user === undefined) return <div className="p-10 text-muted-hud font-mono uppercase tracking-widest">Authenticating…</div>;
  if (user === null) {
    // CEO routes have their own login page
    const target = loc.pathname.startsWith("/ceo") ? "/ceo/login" : "/auth";
    return <Navigate to={target} state={{ from: loc }} replace/>;
  }
  // CEO is an isolated portal — only ceo role can enter
  if (role === "ceo" && user.role !== "ceo") return <Navigate to="/" replace/>;
  // CEO role accessing non-CEO routes → bounce to /ceo/command (clean isolation)
  if (user.role === "ceo" && !loc.pathname.startsWith("/ceo")) return <Navigate to="/ceo/command" replace/>;
  // Admin (incl. investor tour-mode) gets full-app access — passes any role gate
  if (role && role !== "ceo" && user.role !== role && user.role !== "admin") {
    const home = user.role === "operator" ? "/operator" : "/contractor";
    return <Navigate to={home} replace/>;
  }
  if (user.role === "contractor" && !user.nda_accepted && loc.pathname !== "/nda") return <Navigate to="/nda" replace/>;
  return children;
}

function AppShell() {
  const { user } = useAuth();
  const loc = useLocation();

  // Synchronously detect Google OAuth callback BEFORE other routing runs
  if (typeof window !== "undefined" && window.location.hash && window.location.hash.includes("session_id=")) {
    return <AuthCallback/>;
  }

  const isCeoArea = loc.pathname.startsWith("/ceo");
  const isDemo = loc.pathname.startsWith("/demo") || loc.pathname === "/switchboard" || loc.pathname === "/deck" || loc.pathname === "/contractor/brand" || loc.pathname === "/reports/binder" || loc.pathname.startsWith("/passport/") || loc.pathname === "/contractor/verify" || loc.pathname === "/gm/roster" || loc.pathname === "/mission-control";
  const hideNav = isDemo || ["/auth", "/nda", "/onboard", "/launch", "/deliverable/demo", "/deck/demo"].includes(loc.pathname) || loc.pathname.startsWith("/operator/launch/") || loc.pathname.startsWith("/contractor/deliverable/") || loc.pathname.endsWith("/deck") || isCeoArea;
  return (
    <>
      {!hideNav && <Nav role={user?.role}/>}
      {!isCeoArea && !isDemo && <InvestorAssistant/>}
      <Routes>
        <Route path="/" element={<Landing/>}/>
        <Route path="/deck" element={<CommandDeck/>}/>
        <Route path="/contractor/brand" element={<ContractorBranding/>}/>
        <Route path="/reports/binder" element={<ReportsBinder/>}/>
        <Route path="/passport/:hash" element={<PassportPortal/>}/>
        <Route path="/contractor/verify" element={<ContractorVerify/>}/>
        <Route path="/gm/roster" element={<GmRoster/>}/>
        <Route path="/mission-control" element={<MissionControl/>}/>
        <Route path="/switchboard" element={<Switchboard/>}/>
        <Route path="/demo/scan" element={<DemoScanWizard/>}/>
        <Route path="/demo/twin" element={<DemoScanWizard initialStep={3}/>}/>
        <Route path="/demo/maintenance" element={<DemoScanWizard initialStep={3}/>}/>
        <Route path="/demo/quant" element={<DemoScanWizard initialStep={3}/>}/>
        <Route path="/demo/supply-chain" element={<DemoScanWizard initialStep={3}/>}/>
        <Route path="/onboard" element={<OnboardingROI/>}/>
        <Route path="/_neon-preview" element={<NeonLayerPreview/>}/>
        <Route path="/_roof-audit" element={<RoofAuditHarness/>}/>
        <Route path="/auth" element={<AuthPage/>}/>
        <Route path="/nda" element={<Protected><NDAPage/></Protected>}/>

        <Route path="/contractor" element={<Protected role="contractor"><ContractorJobs/></Protected>}/>
        <Route path="/contractor/jobs/new" element={<Protected role="contractor"><NewJob/></Protected>}/>
        <Route path="/contractor/jobs/:id" element={<Protected role="contractor"><JobDetail/></Protected>}/>
        <Route path="/contractor/materials" element={<Protected role="contractor"><MaterialsConfig/></Protected>}/>
        <Route path="/contractor/deliverable/:jobId" element={<Protected><ContractorDeliverable/></Protected>}/>
        <Route path="/contractor/deliverable/:jobId/deck" element={<Protected><DeliverableDeck/></Protected>}/>
        <Route path="/deliverable/demo" element={<Protected><ContractorDeliverable/></Protected>}/>
        <Route path="/deck/demo" element={<Protected><DeliverableDeck/></Protected>}/>
        <Route path="/simulation/:jobId" element={<Protected><SimulationRun/></Protected>}/>
        <Route path="/simulation/demo" element={<Protected><SimulationRun/></Protected>}/>

        <Route path="/operator" element={<Protected role="operator"><OperatorBoard/></Protected>}/>
        <Route path="/operator/jobs/:id" element={<Protected role="operator"><OperatorJobDetail/></Protected>}/>
        <Route path="/operator/launch/:jobId" element={<Protected role="operator"><FleetLaunch/></Protected>}/>

        <Route path="/launch" element={<Protected><FleetLaunch/></Protected>}/>

        <Route path="/admin/sales" element={<Protected role="admin"><AdminSalesHub/></Protected>}/>
        <Route path="/admin/overseer" element={<Protected role="admin"><OverseerQueue/></Protected>}/>
        <Route path="/admin/flight-audit" element={<Protected role="admin"><FlightAudit/></Protected>}/>
        <Route path="/admin/cv-ice-shield" element={<Protected role="admin"><CVIceShield/></Protected>}/>
        <Route path="/admin/weather" element={<Protected role="admin"><AdminWeather/></Protected>}/>
        <Route path="/admin/ops" element={<Protected role="admin"><AdminOps/></Protected>}/>
        <Route path="/contractor/quote-builder" element={<Protected role="contractor"><QuoteBuilder/></Protected>}/>
        <Route path="/admin/branch-console" element={<Protected role="admin"><BranchConsole/></Protected>}/>
        <Route path="/admin/consensus" element={<Protected role="admin"><AdminConsensus/></Protected>}/>

        <Route path="/fleet" element={<Protected><FleetBoard/></Protected>}/>
        <Route path="/billing" element={<Protected role="contractor"><Pricing/></Protected>}/>
        <Route path="/billing/success" element={<Protected role="contractor"><BillingSuccess/></Protected>}/>

        {/* CEO Portal — isolated, single-tenant access via /ceo/login only */}
        <Route path="/ceo/login" element={<CeoLogin/>}/>
        <Route path="/ceo/command" element={<Protected role="ceo"><CeoCommandCenter/></Protected>}/>
        <Route path="/ceo/leads" element={<Protected role="ceo"><SupplyPipeline status="lead"/></Protected>}/>
        <Route path="/ceo/orders/build" element={<Protected role="ceo"><SupplyPipeline status="to_build"/></Protected>}/>
        <Route path="/ceo/orders/ready" element={<Protected role="ceo"><SupplyPipeline status="ready"/></Protected>}/>
        <Route path="/ceo/orders/shipped" element={<Protected role="ceo"><SupplyPipeline status="shipped"/></Protected>}/>
        <Route path="/ceo/inventory" element={<Protected role="ceo"><InventoryCost/></Protected>}/>

        {/* Pilot App — tablet-first surface for field operators */}
        <Route path="/pilot" element={<Protected role="operator"><PilotDashboard/></Protected>}/>
        <Route path="/pilot/job/:jobId" element={<Protected role="operator"><PilotJobSheet/></Protected>}/>
        <Route path="/pilot/preflight/:jobId" element={<Protected role="operator"><PilotPreflight/></Protected>}/>
        <Route path="/fleet/live-map" element={<Protected><FleetLiveMap/></Protected>}/>
        <Route path="/ceo/live-map" element={<Protected role="ceo"><FleetLiveMap/></Protected>}/>
        <Route path="/ceo/regional" element={<Protected role="ceo"><RegionalSwitchboard/></Protected>}/>
        <Route path="/ceo/fleet" element={<Protected role="ceo"><MduFleetPortal/></Protected>}/>
        <Route path="/ceo/blacklist" element={<Protected role="ceo"><BlacklistMatrix/></Protected>}/>
        <Route path="/ceo/suppliers" element={<Protected role="ceo"><CeoSuppliers/></Protected>}/>
        <Route path="/ceo/ops" element={<Protected role="ceo"><CeoOpsPage/></Protected>}/>
        <Route path="/admin/ops" element={<Protected role="admin"><GmOpsPage/></Protected>}/>
        <Route path="/gm/ops" element={<Protected role="gm"><GmOpsPage/></Protected>}/>
        <Route path="/admin/fleet" element={<Protected role="admin"><MduFleetPortal/></Protected>}/>
        <Route path="/admin/blacklist" element={<Protected role="admin"><BlacklistMatrix/></Protected>}/>

        <Route path="*" element={<Navigate to="/" replace/>}/>
      </Routes>
    </>
  );
}

function App() {
  return (
    <div className="App min-h-screen bg-obsidian text-silver">
      <BrowserRouter>
        <AuthProvider>
          <AppShell/>
          <BackToLauncher/>
          <TcAssistant/>
          <Toaster theme="dark" position="top-right" toastOptions={{ style: { background: "#10141D", border: "1px solid rgba(0,240,255,0.35)", color: "#E2E8F0", fontFamily: "JetBrains Mono, monospace", fontSize: "12px", letterSpacing: "0.08em", textTransform: "uppercase" } }}/>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
