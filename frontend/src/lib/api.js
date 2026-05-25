import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

export const createProject = (payload) => api.post("/projects", payload).then(r => r.data);
export const listProjects = () => api.get("/projects").then(r => r.data);
export const getProject = (id) => api.get(`/projects/${id}`).then(r => r.data);
export const submitCaliper = (id, edge_thickness_in) =>
  api.post(`/projects/${id}/caliper`, { edge_thickness_in }).then(r => r.data);
export const computePricing = (id) => api.post(`/projects/${id}/pricing`).then(r => r.data);
export const launchMission = (id, preflight) =>
  api.post(`/projects/${id}/launch`, preflight).then(r => r.data);
