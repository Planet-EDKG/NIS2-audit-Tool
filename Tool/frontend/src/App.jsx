import React, { useEffect, useState, useCallback } from "react";
import { api } from "./api";
import Sidebar from "./components/Sidebar";
import MainPanel from "./components/MainPanel";
import EvidencePanel from "./components/EvidencePanel";
import OscalManagement from "./components/OscalManagement";

const REVIEW_LABELS = {
  draft: "Entwurf",
  review_required: "Review erforderlich",
  approved: "Freigegeben",
  rejected: "Abgelehnt",
};

export default function App() {
  const [activeTab, setActiveTab] = useState("audit"); // 'audit' oder 'oscal'
  
  const [assessment, setAssessment] = useState(null);
  const [assessments, setAssessments] = useState([]);
  const [catalogs, setCatalogs] = useState([]);
  const [catalog, setCatalog] = useState(null);
  const [tree, setTree] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [progress, setProgress] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [settings, setSettings] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [exportOpen, setExportOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [error, setError] = useState(null);
  const [profiles, setProfiles] = useState([]);

  useEffect(() => {
    async function bootstrap() {
      try {
        const allAssessments = await api.listAssessments();
        const allCatalogs = await api.listCatalogs();
        const currentSettings = await api.getSettings();
        const allProfiles = await api.listProfiles().catch(() => []);
        setProfiles(allProfiles);
        setSettings(currentSettings);
        setAssessments(allAssessments);
        setCatalogs(allCatalogs);
        let a = allAssessments[allAssessments.length - 1];
        if (!a) {
          if (!allCatalogs[0]) {
            setError("Kein Katalog vorhanden. Bitte zunächst einen OSCAL-Katalog importieren.");
            return;
          }
          a = await api.createAssessment({
            title: "Neues NIS2-Audit",
            catalog_id: allCatalogs[0].id,
            target_scope: currentSettings.target_scopes?.[0] || "Unbenanntes Zielobjekt",
            responsible: currentSettings.default_actor || "M. Muster",
          });
          setAssessments((prev) => [...prev, a]);
        }
        setAssessment(a);
      } catch (e) {
        setError(String(e.message || e));
      }
    }
    bootstrap();
  }, []);

  const loadTree = useCallback(async () => {
    if (!assessment) return;
    const [c, t, p, d] = await Promise.all([
      api.listCatalogs().then((cs) => cs.find((x) => x.id === assessment.catalog_id)),
      api.getTree(assessment.catalog_id, assessment.id),
      api.getProgress(assessment.id),
      api.getDashboard(),
    ]);
    setCatalog(c);
    setTree(t);
    setProgress(p);
    setDashboard(d);
    if (selectedId === null) {
      const firstLeaf = findFirstLeaf(t);
      if (firstLeaf) setSelectedId(firstLeaf.id);
    }
  }, [assessment, selectedId]);

  useEffect(() => {
    loadTree();
  }, [assessment, refreshKey]); // eslint-disable-line react-hooks/exhaustive-deps

  function findFirstLeaf(nodes) {
    for (const n of nodes) {
      if (!n.is_group) return n;
      const found = findFirstLeaf(n.children);
      if (found) return found;
    }
    return null;
  }

  function handleChanged() {
    setRefreshKey((k) => k + 1);
  }

  async function handleReviewStatus(status) {
    if (!assessment) return;
    const updated = await api.updateAssessment(assessment.id, {
      review_status: status,
      actor: settings?.default_actor || "M. Muster",
    });
    setAssessment(updated);
    handleChanged();
  }

  async function handleSaveSettings(evt) {
    evt.preventDefault();
    const payload = {
      app_name: settings?.app_name || "OSCAL Compliance Suite",
      default_actor: settings?.default_actor || "M. Muster",
      review_workflow: settings?.review_workflow || ["review_required", "approved"],
      target_scopes: settings?.target_scopes || ["IT-Betrieb GmbH"],
    };
    const saved = await api.saveSettings(payload);
    setSettings(saved);
    setSettingsOpen(false);
  }

  async function handleAssessmentSelect(assessmentIdRaw) {
    const assessmentId = Number(assessmentIdRaw);
    const selected = assessments.find((a) => a.id === assessmentId);
    if (!selected) return;
    setAssessment(selected);
    setSelectedId(null);
  }

  async function handleCatalogSelect(catalogIdRaw) {
    const catalogId = Number(catalogIdRaw);
    const existing = assessments.find((a) => a.catalog_id === catalogId);
    if (existing) {
      setAssessment(existing);
      setSelectedId(null);
      return;
    }
    const currentSettings = settings || await api.getSettings();
    const selectedCatalog = catalogs.find((c) => c.id === catalogId);
    const created = await api.createAssessment({
      title: `${selectedCatalog?.title || "Neues Audit"} Audit`,
      catalog_id: catalogId,
      target_scope: currentSettings.target_scopes?.[0] || "Unbenanntes Zielobjekt",
      responsible: currentSettings.default_actor || "M. Muster",
    });
    setAssessments((prev) => [...prev, created]);
    setAssessment(created);
    setSelectedId(null);
  }

  if (error) {
    return <div className="app"><div className="empty">{error}</div></div>;
  }
  if (!assessment) {
    return <div className="app"><div className="loading">Lade Audit-Workspace...</div></div>;
  }

  const reviewOptions = (settings?.review_workflow?.length
    ? settings.review_workflow
    : ["draft", "review_required", "approved", "rejected"]
  ).map((value) => ({ value, label: REVIEW_LABELS[value] || value }));

  return (
    <div className="app">
      <div className="topbar">
        <div className="brandmark">
          <span className="dot"></span>{settings?.app_name || "OSCAL COMPLIANCE SUITE"}
        </div>
        
        {/* NEUE TAB STEUERUNG */}
        <div className="tabs">
          <button 
            className={`tab-btn ${activeTab === "audit" ? "active" : ""}`} 
            onClick={() => setActiveTab("audit")}
          >
            Audit Workspace
          </button>
          <button 
            className={`tab-btn ${activeTab === "oscal" ? "active" : ""}`} 
            onClick={() => setActiveTab("oscal")}
          >
            OSCAL Management
          </button>
        </div>

        <div className="topbar-spacer"></div>

        {activeTab === "audit" && (
          <>
            <div className="topbar-selectors">
              <select
                className="topbar-select"
                value={assessment?.id || ""}
                onChange={(e) => handleAssessmentSelect(e.target.value)}
              >
                {assessments.map((a) => (
                  <option key={a.id} value={a.id}>{a.title} (#{a.id})</option>
                ))}
              </select>
              <select
                className="topbar-select"
                value={assessment?.catalog_id || ""}
                onChange={(e) => handleCatalogSelect(e.target.value)}
              >
                {catalogs.map((c) => (
                  <option key={c.id} value={c.id}>{c.title}</option>
                ))}
              </select>
            </div>
            
            {progress && (
              <div className="progress-wrap">
                Fortschritt
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: `${progress.progress_pct}%` }}></div>
                </div>
                <span className="progress-pct">{progress.progress_pct}%</span>
              </div>
            )}
            
            <div className="export-menu">
              <button className="export-btn" onClick={() => setExportOpen((v) => !v)}>
                  Bericht exportieren
              </button>
              {exportOpen && (
                <div className="export-dropdown" onMouseLeave={() => setExportOpen(false)}>
                  <a href={api.exportPdfUrl(assessment.id)} target="_blank" rel="noreferrer">PDF-Prüfbericht</a>
                  <a href={api.exportHtmlUrl(assessment.id)} target="_blank" rel="noreferrer">HTML-Bericht</a>
                  <a href={api.exportOscalUrl(assessment.id)} target="_blank" rel="noreferrer">OSCAL Assessment Results (JSON)</a>
                </div>
              )}
            </div>
          </>
        )}

        <div className="export-menu">
          <button className="export-btn secondary" onClick={() => setSettingsOpen((v) => !v)}>
              Einstellungen
          </button>
          {settingsOpen && (
            <div className="export-dropdown settings-panel" onMouseLeave={() => setSettingsOpen(false)}>
              <form onSubmit={handleSaveSettings} className="settings-form">
                <label>
                  App-Name
                  <input value={settings?.app_name || ""} onChange={(e) => setSettings((s) => ({ ...s, app_name: e.target.value }))} />
                </label>
                <label>
                  Standard-Benutzer
                  <input value={settings?.default_actor || ""} onChange={(e) => setSettings((s) => ({ ...s, default_actor: e.target.value }))} />
                </label>
                <label>
                  Zielobjekte
                  <textarea value={(settings?.target_scopes || []).join("\n")} onChange={(e) => setSettings((s) => ({ ...s, target_scopes: e.target.value.split(/\n|,/)
                    .map((v) => v.trim()).filter(Boolean) }))} />
                </label>
                <button type="submit" className="save-settings-btn">Speichern</button>
              </form>
            </div>
          )}
        </div>
      </div>

      {/* RENDER LOGIC FÜR TABS */}
      {activeTab === "audit" && (
        <div className="workspace">
          <Sidebar catalog={catalog} tree={tree} selectedId={selectedId} onSelect={setSelectedId} />
          <MainPanel
            assessment={assessment}
            assessmentId={assessment.id}
            controlId={selectedId}
            actor={settings?.default_actor || "M. Muster"}
            onChanged={handleChanged}
            onReviewStatus={handleReviewStatus}
            reviewOptions={reviewOptions}
          />
          <EvidencePanel
            assessmentId={assessment.id}
            controlId={selectedId}
            actor={settings?.default_actor || "M. Muster"}
            refreshKey={refreshKey}
            onChanged={handleChanged}
          />
        </div>
      )}
      {activeTab === "oscal" && (
        <OscalManagement
          catalogs={catalogs}
          profiles={profiles}
          assessments={assessments}
          api={api}
          onCatalogImported={(c) => setCatalogs([...catalogs, c])}
          onProfileCreated={(p) => setProfiles([...profiles, p])}
          onAssessmentCreated={(a) => { 
            setAssessments([...assessments, a]); 
            setActiveTab("audit"); 
            setAssessment(a); 
          }}
        />
      )}
    </div>
  );
}