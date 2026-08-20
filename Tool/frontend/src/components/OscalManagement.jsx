import React, { useState } from "react";

export default function OscalManagement({ catalogs, profiles, assessments, onCatalogImported, onProfileCreated, onAssessmentCreated, api }) {
  const [modal, setModal] = useState(null); // 'import', 'profile', 'plan', 'results'
  const [file, setFile] = useState(null);
  const [form, setForm] = useState({ title: "", catalogId: "", profileId: "", targetScope: "", responsible: "" });

  const resetForm = () => setForm({ title: "", catalogId: "", profileId: "", targetScope: "", responsible: "" });

  async function handleImport(e) {
    e.preventDefault();
    if (!file) return;
    const c = await api.importCatalog(file, "CUSTOM");
    onCatalogImported(c);
    setModal(null);
  }

  async function handleProfile(e) {
    e.preventDefault();
    const p = await api.createProfile({
      title: form.title,
      catalog_id: Number(form.catalogId),
      included_control_ids: [] // Leeres Array bedeutet: Backend übernimmt alle Controls
    });
    onProfileCreated(p);
    setModal(null);
    resetForm();
  }

  async function handlePlan(e) {
    e.preventDefault();
    const a = await api.createAssessment({
      title: form.title,
      catalog_id: Number(form.catalogId),
      profile_id: form.profileId ? Number(form.profileId) : null,
      target_scope: form.targetScope,
      responsible: form.responsible,
      phase: "plan"
    });
    onAssessmentCreated(a);
    setModal(null);
    resetForm();
  }

  return (
    <div className="oscal-mgmt-wrap">
      <h1 style={{ marginTop: 0 }}>OSCAL Management Zentrale</h1>
      <p style={{ color: "var(--ink-soft)" }}>
        Steuere hier die Kernkomponenten des OSCAL-Frameworks unabhängig vom aktiven Audit.
      </p>
      
      <div className="oscal-grid">
        <div className="oscal-card">
          <h3>OSCAL Catalogs</h3>
          <p>Importiere neue Compliance-Kataloge (JSON), wie BSI IT-Grundschutz, NIS2 oder ISO 27001.</p>
          <button onClick={() => setModal('import')}>+ Katalog importieren</button>
        </div>
        
        <div className="oscal-card">
          <h3>OSCAL Profiles</h3>
          <p>Lege individuelle Profile an, um Kataloge für spezifische Unternehmensbereiche oder Baselines anzupassen (Tailoring).</p>
          <button onClick={() => setModal('profile')}>+ Profil erstellen</button>
        </div>
        
        <div className="oscal-card">
          <h3>Assessment Plans</h3>
          <p>Plane neue Audits. Definiere Zielobjekte (Scopes), weise Profile zu und bestimme Verantwortliche vor Audit-Start.</p>
          <button onClick={() => setModal('plan')}>+ Plan erstellen</button>
        </div>
        
        <div className="oscal-card">
          <h3>Assessment Results</h3>
          <p>Übersicht aller abgeschlossenen Assessments. (Zeigt aktuell alle Audits an).</p>
          <button onClick={() => setModal('results')}>Ergebnisse ansehen</button>
        </div>
      </div>

      {/* --- MODALS --- */}
      {modal && (
        <div className="modal-overlay">
          <div className="modal-content">
            {modal === 'import' && (
              <form onSubmit={handleImport} className="modal-form">
                <h2>Katalog importieren</h2>
                <label>
                  OSCAL JSON Datei
                  <input type="file" accept=".json" onChange={(e) => setFile(e.target.files[0])} required />
                </label>
                <div className="modal-actions">
                  <button type="button" className="modal-btn cancel" onClick={() => setModal(null)}>Abbrechen</button>
                  <button type="submit" className="modal-btn submit">Importieren</button>
                </div>
              </form>
            )}

            {modal === 'profile' && (
              <form onSubmit={handleProfile} className="modal-form">
                <h2>Neues Profil anlegen</h2>
                <label>Profil-Name <input required value={form.title} onChange={e => setForm({...form, title: e.target.value})} /></label>
                <label>Basis-Katalog 
                  <select required value={form.catalogId} onChange={e => setForm({...form, catalogId: e.target.value})}>
                    <option value="">Bitte wählen...</option>
                    {catalogs.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
                  </select>
                </label>
                <div className="modal-actions">
                  <button type="button" className="modal-btn cancel" onClick={() => setModal(null)}>Abbrechen</button>
                  <button type="submit" className="modal-btn submit">Profil speichern</button>
                </div>
              </form>
            )}

            {modal === 'plan' && (
              <form onSubmit={handlePlan} className="modal-form">
                <h2>Assessment Plan erstellen</h2>
                <label>Audit-Titel <input required value={form.title} onChange={e => setForm({...form, title: e.target.value})} /></label>
                <label>Scope (Zielobjekt) <input required value={form.targetScope} onChange={e => setForm({...form, targetScope: e.target.value})} /></label>
                <label>Katalog
                  <select required value={form.catalogId} onChange={e => setForm({...form, catalogId: e.target.value})}>
                    <option value="">Bitte wählen...</option>
                    {catalogs.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
                  </select>
                </label>
                <label>Profil (Optional)
                  <select value={form.profileId} onChange={e => setForm({...form, profileId: e.target.value})}>
                    <option value="">Kein Profil (Gesamter Katalog)</option>
                    {profiles.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
                  </select>
                </label>
                <div className="modal-actions">
                  <button type="button" className="modal-btn cancel" onClick={() => setModal(null)}>Abbrechen</button>
                  <button type="submit" className="modal-btn submit">Audit starten</button>
                </div>
              </form>
            )}

            {modal === 'results' && (
              <div className="modal-form">
                <h2>Assessment Results</h2>
                <ul style={{ paddingLeft: 20 }}>
                  {assessments.map(a => (
                    <li key={a.id} style={{ marginBottom: 10 }}>
                      <strong>{a.title}</strong> (Scope: {a.target_scope})<br/>
                      <a href={api.exportOscalUrl(a.id)} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: 'var(--fh-green-dark)' }}>OSCAL JSON Download</a>
                    </li>
                  ))}
                </ul>
                <div className="modal-actions">
                  <button type="button" className="modal-btn cancel" onClick={() => setModal(null)}>Schließen</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}