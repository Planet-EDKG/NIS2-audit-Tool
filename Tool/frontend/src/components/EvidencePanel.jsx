import React, { useEffect, useState, useRef } from "react";
import { api } from "../api";

function timeAgo(iso) {
  if (!iso) return "gerade eben";
  const raw = typeof iso === "string" ? iso : String(iso);
  const normalized = raw.endsWith("Z") ? raw : `${raw}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return "gerade eben";

  const diffMs = Date.now() - date.getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "gerade eben";
  if (mins < 60) return `vor ${mins} Min.`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `vor ${hrs} Std.`;
  return date.toLocaleDateString("de-DE");
}

export default function EvidencePanel({ assessmentId, controlId, actor = "M. Muster", refreshKey, onChanged }) {
  const [evidence, setEvidence] = useState([]);
  const [trail, setTrail] = useState([]);
  const [linkUrl, setLinkUrl] = useState("");
  const [linkName, setLinkName] = useState("");
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!controlId) return;
    api.listEvidence(assessmentId, controlId).then(setEvidence).catch(console.error);
    api.getAuditTrail(assessmentId, controlId).then(setTrail).catch(console.error);
  }, [assessmentId, controlId, refreshKey]);

  async function handleFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    await api.uploadEvidenceFile(assessmentId, controlId, file, actor);
    e.target.value = "";
    onChanged();
  }

  async function handleAddLink() {
    if (!linkUrl.trim() || !linkName.trim()) return;
    await api.addEvidenceLink(assessmentId, controlId, linkUrl.trim(), linkName.trim(), actor);
    setLinkUrl("");
    setLinkName("");
    onChanged();
  }

  async function handleDelete(evId) {
    if (!window.confirm("Nachweis wirklich löschen?")) return;
    await api.deleteEvidence(assessmentId, controlId, evId);
    onChanged();
  }

  return (
    <div className="col col-side">
      <div className="side-section">
        <div className="col-eyebrow">Nachweise</div>
        <label className="dropzone">
          <span style={{ fontSize: 24, marginBottom: 8 }}>📁</span>
          <span>Datei hierher ziehen<br />oder <b style={{ color: "var(--fh-green-dark)" }}>Nachweis hochladen</b></span>
          <input ref={fileInputRef} type="file" onChange={handleFile} />
        </label>
        <div className="link-form">
          <input placeholder="Bezeichnung" value={linkName} onChange={(e) => setLinkName(e.target.value)} />
          <input placeholder="URL" value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} />
          <button type="button" onClick={handleAddLink}>+</button>
        </div>

        <div style={{ marginTop: 10 }}>
          {evidence.length === 0 && <div style={{ fontSize: 11.5, color: "#9CA39E" }}>Noch keine Nachweise.</div>}
          {evidence.map((ev) => (
            <div className="evidence-item" key={ev.id}>
              <div className="evidence-icon">{ev.kind === "file" ? "📄" : "🔗"}</div>
              <div className="evidence-item-main">
                <div className="evidence-name">{ev.filename}</div>
                <div className="evidence-meta">
                  {ev.kind === "file" ? "Hochgeladen" : "Extern verlinkt"} · {timeAgo(ev.uploaded_at)}
                </div>
              </div>
              <div className="evidence-actions">
                <button type="button" className="small-btn" onClick={() => window.open(api.openEvidenceUrl(assessmentId, controlId, ev.id), "_blank", "noopener,noreferrer")}>Öffnen</button>
                <button type="button" className="small-btn danger" onClick={() => handleDelete(ev.id)}>Löschen</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="side-section" style={{ flex: 1 }}>
        <div className="col-eyebrow">Audit Trail</div>
        {trail.length === 0 && <div style={{ fontSize: 11.5, color: "#9CA39E" }}>Keine Aktivitäten.</div>}
        {trail.map((t) => (
          <div className="trail-item" key={t.id}>
            <div className="trail-avatar">{t.actor.split(" ").map((p) => p[0]).join("").slice(0, 2).toUpperCase()}</div>
            <div>
              <div className="trail-text"><b>{t.actor}</b> {t.action}</div>
              <div className="trail-time">{timeAgo(t.created_at)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
