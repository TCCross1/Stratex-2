// NextGen API client — talks to /api/nextgen/* only.
// Reuses the shared axios instance from lib/api.js (auth header + 422 flatten).
import { api } from "@/lib/api";

const NX = "/nextgen";

// Session / catalog
export const nxHealth = () => api.get(`${NX}/health`).then((r) => r.data);
export const nxMe = () => api.get(`${NX}/me`).then((r) => r.data);
export const nxCatalog = () => api.get(`${NX}/catalog/products`).then((r) => r.data);
export const nxStages = () => api.get(`${NX}/workflow/stages`).then((r) => r.data);
export const nxOverview = () => api.get(`${NX}/workflow/overview`).then((r) => r.data);

// Organization
export const nxOrg = () => api.get(`${NX}/organizations/current`).then((r) => r.data);
export const nxOrgPatch = (body) =>
  api.patch(`${NX}/organizations/current`, body).then((r) => r.data);

// Properties
export const nxResolveProperty = (body) =>
  api.post(`${NX}/properties/resolve`, body).then((r) => r.data);
export const nxCreateProperty = (body) =>
  api.post(`${NX}/properties`, body).then((r) => r.data);
export const nxListProperties = () =>
  api.get(`${NX}/properties`).then((r) => r.data);
export const nxGetProperty = (id) =>
  api.get(`${NX}/properties/${id}`).then((r) => r.data);

// Missions
export const nxCreateMission = (body) =>
  api.post(`${NX}/missions`, body).then((r) => r.data);
export const nxListMissions = (property_id) =>
  api.get(`${NX}/missions`, { params: property_id ? { property_id } : {} })
    .then((r) => r.data);
export const nxGetMission = (id) =>
  api.get(`${NX}/missions/${id}`).then((r) => r.data);
export const nxAdvanceMission = (id, to_stage, note) =>
  api.post(`${NX}/missions/${id}/advance`, { to_stage, note }).then((r) => r.data);

// Passport
export const nxPassportByProperty = (id) =>
  api.get(`${NX}/passports/by-property/${id}`).then((r) => r.data);

// Audit
export const nxAudit = () => api.get(`${NX}/audit/events`).then((r) => r.data);

// ─── Wave 2A · Evidence + Mission Packages ───
const V1 = "/nextgen/v1";
export const nxEvidenceProfile = (product_key) =>
  api.get(`${V1}/evidence-profiles/${product_key}`).then((r) => r.data);
export const nxListEvidence = (missionId) =>
  api.get(`${V1}/missions/${missionId}/evidence`).then((r) => r.data);
export const nxGetEvidence = (id) =>
  api.get(`${V1}/evidence/${id}`).then((r) => r.data);
export const nxDeleteEvidence = (id) =>
  api.delete(`${V1}/evidence/${id}`).then((r) => r.data);
export const nxRetryMetadata = (id) =>
  api.post(`${V1}/evidence/${id}/retry-metadata`).then((r) => r.data);
export const nxValidatePackage = (missionId) =>
  api.post(`${V1}/missions/${missionId}/package/validate`).then((r) => r.data);
export const nxFinalizePackage = (missionId, operator_notes) =>
  api.post(`${V1}/missions/${missionId}/package/finalize`, { operator_notes }).then((r) => r.data);
export const nxListPackages = (missionId) =>
  api.get(`${V1}/missions/${missionId}/packages`).then((r) => r.data);
export const nxManifestJsonUrl = (packageId) => {
  const t = localStorage.getItem("stratex_token");
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
  return `${BACKEND_URL}/api${V1}/packages/${packageId}/manifest.json?_t=${t}`;
};
export const nxUploadEvidence = (missionId, formData, onProgress) =>
  api.post(`${V1}/missions/${missionId}/evidence`, formData, {
    onUploadProgress: onProgress,
    headers: { "Content-Type": "multipart/form-data" },
  }).then((r) => r.data);
