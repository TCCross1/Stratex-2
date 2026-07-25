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
// Delay revocation by 2 minutes to allow the browser enough time to load the PDF blob URL in the new tab before cleanup
const BLOB_REVOKE_DELAY_MS = 120000;
const MAX_PLAIN_TEXT_ERROR_LENGTH = 200;

const formatValidationErrorArray = (arr) => {
  if (!Array.isArray(arr)) return "Invalid validation error format";
  return arr
    .map((e) => {
      const loc = (e && e.loc && Array.isArray(e.loc)) ? (e.loc.slice(-1)[0] || "field") : "field";
      const msg = (e && e.msg) ? e.msg : "validation error";
      return `${loc}: ${msg}`;
    })
    .filter(Boolean)
    .join(" · ");
};

const isSafePlainTextError = (text) => {
  if (typeof text !== "string") return false;
  return text.length < MAX_PLAIN_TEXT_ERROR_LENGTH && !text.includes("Authorization") && !text.includes("Bearer");
};

export const normalizeBlobError = async (err) => {
  const fallback = "An unexpected error occurred";
  if (!err) return fallback;

  // 1. Check if the error has a response and response data is a Blob
  if (err.response?.data instanceof Blob) {
    try {
      const blob = err.response.data;
      const text = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => {
          console.error("FileReader failed to read blob error response");
          resolve("");
        };
        reader.readAsText(blob);
      });

      if (text) {
        try {
          const parsed = JSON.parse(text);
          if (parsed && typeof parsed === "object") {
            const errorContent = parsed.detail || parsed.message;
            if (errorContent) {
              if (typeof errorContent === "string") return errorContent;
              if (Array.isArray(errorContent)) {
                return formatValidationErrorArray(errorContent);
              }
              return JSON.stringify(errorContent);
            }
          }
        } catch {
          // If JSON parse fails, check if the text is plain text and not overly long or contains sensitive stuff
          if (!blob.type.startsWith("application/json") && isSafePlainTextError(text)) {
            return text;
          }
        }
      }
    } catch {
      // ignore
    }
  }

  // 2. Normal JSON response / Axios errors
  const resData = err.response?.data;
  if (resData) {
    if (typeof resData === "string") {
      try {
        const parsed = JSON.parse(resData);
        const detail = parsed.detail || parsed.message;
        if (detail) {
          if (typeof detail === "string") return detail;
          return JSON.stringify(detail);
        }
      } catch {
        if (isSafePlainTextError(resData)) {
          return resData;
        }
      }
    } else if (typeof resData === "object") {
      const detail = resData.detail || resData.message;
      if (detail) {
        if (typeof detail === "string") return detail;
        if (Array.isArray(detail)) {
          return formatValidationErrorArray(detail);
        }
        return JSON.stringify(detail);
      }
    }
  }

  // 3. Error.message
  if (err.message) {
    if (err.message.includes("Authorization") || err.message.includes("Bearer")) {
      return fallback;
    }
    return err.message;
  }

  return fallback;
};

export const openContractorPdf = async (id) => {
  const w = window.open("", "_blank", "noopener,noreferrer");
  if (!w) {
    throw new Error("Popup blocked. Please allow popups for this site to view the PDF report.");
  }
  if (w.opener) {
    w.opener = null;
  }
  w.document.write(`
    <html>
      <head>
        <title>Loading PDF...</title>
        <style>
          body {
            background-color: #0B111A;
            color: #E6EEF6;
            font-family: 'JetBrains Mono', monospace;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
          }
        </style>
      </head>
      <body>
        <div>Loading PDF...</div>
      </body>
    </html>
  `);
  w.document.close();

  try {
    const r = await inst.get(`/contractor/jobs/${id}/report.pdf`, {
      responseType: "blob",
    });
    const blob = new Blob([r.data], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    w.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), BLOB_REVOKE_DELAY_MS);
    return w;
  } catch (err) {
    w.close();
    const errMsg = await normalizeBlobError(err);
    throw new Error(errMsg);
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
