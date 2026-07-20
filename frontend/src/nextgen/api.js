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
const BLOB_REVOKE_DELAY_MS = 120000;

export const nxOpenManifestJson = async (packageId) => {
  const r = await api.get(`${V1}/packages/${packageId}/manifest.json`, {
    responseType: "blob",
  });
  const blob = new Blob([r.data], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const w = window.open(url, "_blank", "noopener,noreferrer");
  if (!w) {
    URL.revokeObjectURL(url);
  } else {
    setTimeout(() => URL.revokeObjectURL(url), BLOB_REVOKE_DELAY_MS);
  }
  return w;
};
export const nxUploadEvidence = (missionId, formData, onProgress) =>
  api.post(`${V1}/missions/${missionId}/evidence`, formData, {
    onUploadProgress: onProgress,
    headers: { "Content-Type": "multipart/form-data" },
  }).then((r) => r.data);

// ─── Wave 2B · Property Intelligence Engine (Directive 007) ───
export const nxTaxonomy = () =>
  api.get(`${V1}/taxonomy/building-systems`).then((r) => r.data);
export const nxCreateIntelligence = (body) =>
  api.post(`${V1}/intelligence`, body).then((r) => r.data);
export const nxListIntelligence = (missionId) =>
  api.get(`${V1}/missions/${missionId}/intelligence`).then((r) => r.data);
export const nxGetIntelligence = (id) =>
  api.get(`${V1}/intelligence/${id}`).then((r) => r.data);
export const nxReviewIntelligence = (id, body) =>
  api.post(`${V1}/intelligence/${id}/review`, body).then((r) => r.data);
export const nxPropertyTimeline = (propertyId) =>
  api.get(`${V1}/properties/${propertyId}/timeline`).then((r) => r.data);
export const nxPropertyPassport = (propertyId, audience = "internal") =>
  api.get(`${V1}/properties/${propertyId}/passport`, { params: { audience } }).then((r) => r.data);
export const nxPropertyReport = (propertyId, template) =>
  api.get(`${V1}/properties/${propertyId}/report/${template}`).then((r) => r.data);
export const nxReportTemplates = () =>
  api.get(`${V1}/report-templates`).then((r) => r.data);

// ─── Directive 008 · Wave 2C · AWE + Habitat + HTML report ───
export const nxPropertyAwe = (propertyId) =>
  api.get(`${V1}/properties/${propertyId}/awe`).then((r) => r.data);
export const nxIssueHabitatLink = (propertyId, ttl_hours = 168, audience = "homeowner") =>
  api.post(`${V1}/properties/${propertyId}/habitat-link`,
    { ttl_hours, audience }).then((r) => r.data);
export const nxListHabitatGrants = (propertyId) =>
  api.get(`${V1}/properties/${propertyId}/habitat-grants`).then((r) => r.data);
export const nxRevokeGrant = (grantId) =>
  api.post(`${V1}/habitat-grants/${grantId}/revoke`).then((r) => r.data);
// Directive 009: fetch HTML with Authorization header (no bearer in URL/history/referer),
// then open the resulting blob in a new tab.
export const nxOpenReportHtml = async (propertyId, template) => {
  const r = await api.get(`${V1}/properties/${propertyId}/report/${template}/html`, {
    responseType: "text",
    headers: { Accept: "text/html" },
  });
  const blob = new Blob([r.data], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const w = window.open(url, "_blank", "noopener,noreferrer");
  // Best-effort cleanup — revoke after tab loads (or ~2 min max).
  setTimeout(() => URL.revokeObjectURL(url), 120000);
  return w;
};
// Public — no auth
export const nxHabitatPublicRead = (token) => {
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
  return fetch(`${BACKEND_URL}/api${V1}/habitat/${token}`).then((r) => r.json());
};

// ─── Phase 3 · Property Intelligence Engine — Findings ───
export const nxCreateFinding = (body) =>
  api.post(`${V1}/findings`, body).then((r) => r.data);
export const nxUpdateFinding = (id, body) =>
  api.patch(`${V1}/findings/${id}`, body).then((r) => r.data);
export const nxSubmitFinding = (id, notes) =>
  api.post(`${V1}/findings/${id}/submit`, { notes }).then((r) => r.data);
export const nxApproveFinding = (id, notes) =>
  api.post(`${V1}/findings/${id}/approve`, { notes }).then((r) => r.data);
export const nxRejectFinding = (id, notes) =>
  api.post(`${V1}/findings/${id}/reject`, { notes }).then((r) => r.data);
export const nxResolveFinding = (id, notes) =>
  api.post(`${V1}/findings/${id}/resolve`, { notes }).then((r) => r.data);
export const nxSupersedeFinding = (id, new_finding, reason) =>
  api.post(`${V1}/findings/${id}/supersede`, { new_finding, reason }).then((r) => r.data);
export const nxGetFinding = (id) =>
  api.get(`${V1}/findings/${id}`).then((r) => r.data);
export const nxListFindings = (propertyId, params = {}) =>
  api.get(`${V1}/properties/${propertyId}/findings`, { params }).then((r) => r.data);
export const nxIntelligenceSummary = (propertyId, audience = "internal") =>
  api.get(`${V1}/properties/${propertyId}/intelligence-summary`, { params: { audience } })
    .then((r) => r.data);
export const nxHabitatFindings = (propertyId) =>
  api.get(`${V1}/properties/${propertyId}/findings/habitat-projection`).then((r) => r.data);
