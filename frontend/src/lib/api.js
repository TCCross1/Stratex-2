import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const inst = axios.create({ baseURL: API });
inst.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("stratex_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

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
export const contractorPdfUrl = (id) => `${API}/contractor/jobs/${id}/report.pdf?_t=${localStorage.getItem("stratex_token")}`;

// ---------- Operator ----------
export const listOperatorJobs = () => inst.get("/operator/jobs").then(r => r.data);
export const getOperatorJob = (id) => inst.get(`/operator/jobs/${id}`).then(r => r.data);
export const operatorLaunch = (id, preflight) => inst.post(`/operator/jobs/${id}/launch`, preflight).then(r => r.data);
