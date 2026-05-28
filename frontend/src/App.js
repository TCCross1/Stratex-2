import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/lib/auth";
import Nav from "@/components/Nav";
import Landing from "@/pages/Landing";
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
import InvestorAssistant from "@/components/InvestorAssistant";

function Protected({ role, children }) {
  const { user } = useAuth();
  const loc = useLocation();
  if (user === undefined) return <div className="p-10 text-muted-hud font-mono uppercase tracking-widest">Authenticating…</div>;
  if (user === null) return <Navigate to="/auth" state={{ from: loc }} replace/>;
  // Admin (incl. investor tour-mode) gets full-app access — passes any role gate
  if (role && user.role !== role && user.role !== "admin") {
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

  const hideNav = ["/auth", "/nda", "/onboard", "/launch"].includes(loc.pathname) || loc.pathname.startsWith("/operator/launch/");
  return (
    <>
      {!hideNav && <Nav role={user?.role}/>}
      <InvestorAssistant/>
      <Routes>
        <Route path="/" element={<Landing/>}/>
        <Route path="/onboard" element={<OnboardingROI/>}/>
        <Route path="/_neon-preview" element={<NeonLayerPreview/>}/>
        <Route path="/_roof-audit" element={<RoofAuditHarness/>}/>
        <Route path="/auth" element={<AuthPage/>}/>
        <Route path="/nda" element={<Protected><NDAPage/></Protected>}/>

        <Route path="/contractor" element={<Protected role="contractor"><ContractorJobs/></Protected>}/>
        <Route path="/contractor/jobs/new" element={<Protected role="contractor"><NewJob/></Protected>}/>
        <Route path="/contractor/jobs/:id" element={<Protected role="contractor"><JobDetail/></Protected>}/>
        <Route path="/contractor/materials" element={<Protected role="contractor"><MaterialsConfig/></Protected>}/>

        <Route path="/operator" element={<Protected role="operator"><OperatorBoard/></Protected>}/>
        <Route path="/operator/jobs/:id" element={<Protected role="operator"><OperatorJobDetail/></Protected>}/>
        <Route path="/operator/launch/:jobId" element={<Protected role="operator"><FleetLaunch/></Protected>}/>

        <Route path="/launch" element={<Protected><FleetLaunch/></Protected>}/>

        <Route path="/admin/sales" element={<Protected role="admin"><AdminSalesHub/></Protected>}/>
        <Route path="/admin/overseer" element={<Protected role="admin"><OverseerQueue/></Protected>}/>
        <Route path="/admin/flight-audit" element={<Protected role="admin"><FlightAudit/></Protected>}/>

        <Route path="/fleet" element={<Protected><FleetBoard/></Protected>}/>
        <Route path="/billing" element={<Protected role="contractor"><Pricing/></Protected>}/>
        <Route path="/billing/success" element={<Protected role="contractor"><BillingSuccess/></Protected>}/>

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
          <Toaster theme="dark" position="top-right" toastOptions={{ style: { background: "#10141D", border: "1px solid rgba(0,240,255,0.35)", color: "#E2E8F0", fontFamily: "JetBrains Mono, monospace", fontSize: "12px", letterSpacing: "0.08em", textTransform: "uppercase" } }}/>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
