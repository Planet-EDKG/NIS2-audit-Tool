const BASE = "/api";

async function req(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API-Fehler ${res.status}: ${detail}`);
  }
  return res.json();
}

export const api = {
  listCatalogs: () => req("/catalogs"),
  getTree: (catalogId, assessmentId) =>
    req(`/catalogs/${catalogId}/tree?assessment_id=${assessmentId}`),

  listAssessments: () => req("/assessments"),
  createAssessment: (payload) =>
    req("/assessments", { method: "POST", body: JSON.stringify(payload) }),
  updateAssessment: (id, payload) =>
    req(`/assessments/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  getAssessment: (id) => req(`/assessments/${id}`),
  getProgress: (id) => req(`/assessments/${id}/progress`),
  getDashboard: () => req("/assessments/dashboard"),
  getSettings: () => req("/settings"),
  saveSettings: (payload) => req("/settings", { method: "PUT", body: JSON.stringify(payload) }),

  getControl: (assessmentId, controlId) =>
    req(`/assessments/${assessmentId}/controls/${controlId}`),
  updateStatus: (assessmentId, controlId, status, actor) =>
    req(`/assessments/${assessmentId}/controls/${controlId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status, actor }),
    }),
  updateComment: (assessmentId, controlId, comment, actor) =>
    req(`/assessments/${assessmentId}/controls/${controlId}/comment`, {
      method: "PUT",
      body: JSON.stringify({ comment, actor }),
    }),
  updateFinding: (assessmentId, controlId, fields, actor) =>
    req(`/assessments/${assessmentId}/controls/${controlId}/finding`, {
      method: "PUT",
      body: JSON.stringify({ ...fields, actor }),
    }),

  listEvidence: (assessmentId, controlId) =>
    req(`/assessments/${assessmentId}/controls/${controlId}/evidence`),
  addEvidenceLink: (assessmentId, controlId, url, filename, actor) =>
    req(`/assessments/${assessmentId}/controls/${controlId}/evidence/link`, {
      method: "POST",
      body: JSON.stringify({ url, filename, actor }),
    }),
  deleteEvidence: (assessmentId, controlId, evidenceId) =>
    req(`/assessments/${assessmentId}/controls/${controlId}/evidence/${evidenceId}`, {
      method: "DELETE",
    }),
  openEvidenceUrl: (assessmentId, controlId, evidenceId) =>
    `${BASE}/assessments/${assessmentId}/controls/${controlId}/evidence/${evidenceId}/open`,
  uploadEvidenceFile: async (assessmentId, controlId, file, actor) => {
    const form = new FormData();
    form.append("file", file);
    form.append("actor", actor);
    const res = await fetch(
      `${BASE}/assessments/${assessmentId}/controls/${controlId}/evidence/file`,
      { method: "POST", body: form }
    );
    if (!res.ok) throw new Error(`Upload fehlgeschlagen: ${res.status}`);
    return res.json();
  },

  getAuditTrail: (assessmentId, controlId) =>
    req(`/assessments/${assessmentId}/audit-trail?control_id=${controlId}&limit=20`),

  exportOscalUrl: (assessmentId) => `${BASE}/assessments/${assessmentId}/export/oscal`,
  exportHtmlUrl: (assessmentId) => `${BASE}/assessments/${assessmentId}/export/report.html`,
  exportPdfUrl: (assessmentId) => `${BASE}/assessments/${assessmentId}/export/report.pdf`,
  importCatalog: async (file, source = "NIS2") => {
    const form = new FormData();
    form.append("file", file);
    form.append("source", source);
    const res = await fetch(`${BASE}/catalogs/import`, { method: "POST", body: form });
    if (!res.ok) throw new Error("Import fehlgeschlagen");
    return res.json();
  },
  listProfiles: () => req("/profiles"),
  createProfile: (payload) => req("/profiles", { method: "POST", body: JSON.stringify(payload) }),
  updatePhase: (assessmentId, phase) => req(`/assessments/${assessmentId}/phase?phase=${phase}`, { method: "PUT" }),
};
