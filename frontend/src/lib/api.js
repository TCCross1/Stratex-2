import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const inst = axios.create({ baseURL: API });
inst.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("stratex_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

// Flatten Pydantic 422 errors so they never reach React render as objects
inst.interceptors.response.use(
  (r) => r,
  (err) => {
    const d = err.response?.data?.detail;
    if (Array.isArray(d)) {
      const msg = d.map((e) => `${e.loc?.slice(-1)?.[0] || "field"}: ${e.msg}`).join(" · ");
      err.response.data.detail = msg;
    }
    return Promise.reject(err);
  },
);

export const api = inst;

// ---------- Auth ----------
export const signup = (body) => inst.post("/auth/signup", body).then(r => r.data);
export const loginStep1 = (email, password) => inst.post("/auth/login", { email, password }).then(r => r.data);
export const loginStep2 = (email, password, totp_code) => inst.post("/auth/login", { email, password, totp_code }).then(r => r.data);
export const me = () => inst.get("/auth/me").then(r => r.data);
export const previewNDA = () => inst.get("/auth/nda-preview").then(r => r.data);
export const acceptNDA = (typed_name) => inst.post("/auth/accept-nda", { typed_name }).then(r => r.data);
export const totpDebug = (email) => inst.get(`/auth/totp-debug?email=${encodeURIComponent(email)}`).then(r => r.data);

// ---------- Contractor ----------
export const getMaterials = () => inst.get("/contractor/materials").then(r => r.data);
export const saveMaterials = (body) => inst.put("/contractor/materials", body).then(r => r.data);
export const listContractorJobs = () => inst.get("/contractor/jobs").then(r => r.data);
export const getContractorJob = (id) => inst.get(`/contractor/jobs/${id}`).then(r => r.data);
export const createJob = (body) => inst.post("/contractor/jobs", body).then(r => r.data);
export const computeProposal = (id) => inst.post(`/contractor/jobs/${id}/compute-proposal`).then(r => r.data);
export const auditApprove = (id) => inst.post(`/contractor/jobs/${id}/audit-approve`).then(r => r.data);
export const markSent = (id) => inst.post(`/contractor/jobs/${id}/mark-sent`).then(r => r.data);
export const contractorPdfUrl = (id) => `${API}/contractor/jobs/${id}/report.pdf`;

const BLOB_REVOKE_DELAY_MS = 120000;

export const openContractorPdf = async (id) => {
  try {
    const r = await inst.get(`/contractor/jobs/${id}/report.pdf`, {
      responseType: "blob",
    });
    const blob = new Blob([r.data], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const w = window.open(url, "_blank", "noopener,noreferrer");
    setTimeout(() => URL.revokeObjectURL(url), BLOB_REVOKE_DELAY_MS);
    return w;
  } catch (err) {
    const d = err.response?.data?.detail || err.message;
    alert(`Failed to load PDF report: ${d}`);
    throw err;
  }
};

// ---------- Operator ----------
export const listOperatorJobs = () => inst.get("/operator/jobs").then(r => r.data);
export const getOperatorJob = (id) => inst.get(`/operator/jobs/${id}`).then(r => r.data);
export const operatorLaunch = (id, preflight) => inst.post(`/operator/jobs/${id}/launch`, preflight).then(r => r.data);
export const operatorWeatherMonitor = (id) => inst.get(`/operator/jobs/${id}/weather-monitor`).then(r => r.data);

// ---------- Fleet ----------
export const fleetStatus = () => inst.get("/fleet/status").then(r => r.data);

// ---------- Risk Engine ----------
export const runPhase1 = (id) => inst.post(`/contractor/jobs/${id}/run-phase1`).then(r => r.data);
export const getJobAuditLog = (id) => inst.get(`/contractor/jobs/${id}/audit-log`).then(r => r.data);
export const operatorDryRun = (id, reason, notes) => inst.post(`/operator/jobs/${id}/dry-run`, { reason, notes }).then(r => r.data);
export const getBillingMeter = () => inst.get("/contractor/billing/meter").then(r => r.data);
export const rescheduleSuggestions = (id) => inst.get(`/contractor/jobs/${id}/reschedule-suggestions`).then(r => r.data);
export const weatherMonitor = (id) => inst.get(`/contractor/jobs/${id}/weather-monitor`).then(r => r.data);
export const notifyHomeownerDelay = (id, homeowner_email, homeowner_phone) => inst.post(`/contractor/jobs/${id}/notify-homeowner-delay`, { homeowner_email, homeowner_phone }).then(r => r.data);

// ---------- Email ----------
export const emailNda = () => inst.post("/auth/email-nda").then(r => r.data);
export const emailProposal = (id, homeowner_email, cc_self=true) => inst.post(`/contractor/jobs/${id}/email-proposal`, { homeowner_email, cc_self }).then(r => r.data);

// ---------- Google OAuth ----------
export const googleSessionExchange = (session_id) => inst.post("/auth/google/session", { session_id }).then(r => r.data);

// ---------- Billing (Stripe) ----------
export const getBillingPlans = () => inst.get("/billing/plans").then(r => r.data);
export const getBillingMe = () => inst.get("/billing/me").then(r => r.data);
export const createCheckout = (tier, origin_url) => inst.post("/billing/checkout", { tier, origin_url }).then(r => r.data);
export const getCheckoutStatus = (session_id) => inst.get(`/billing/status/${session_id}`).then(r => r.data);
