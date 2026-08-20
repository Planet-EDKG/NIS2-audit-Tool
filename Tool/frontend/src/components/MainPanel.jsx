import React, { useEffect, useState, useRef } from "react";
import { api } from "../api";

const STATUS_OPTIONS = [
  { key: "fulfilled", label: "Fulfilled", color: "var(--fh-green)" },
  { key: "partial", label: "Partially Fulfilled", color: "var(--amber)" },
  { key: "open", label: "Non-Compliant", color: "var(--red)" },
  { key: "na", label: "Not Applicable", color: "#CBD0CD" },
];

export default function MainPanel({ assessment, assessmentId, controlId, actor = "M. Muster", onChanged, onReviewStatus, reviewOptions }) {
  const [control, setControl] = useState(null);
  const [comment, setComment] = useState("");
  const [deviation, setDeviation] = useState("");
  const [correctiveAction, setCorrectiveAction] = useState("");
  const [evidenceReference, setEvidenceReference] = useState("");
  const [savedNote, setSavedNote] = useState("");
  const saveTimer = useRef(null);

  useEffect(() => {
    if (!controlId) return;
    setControl(null);
    api.getControl(assessmentId, controlId).then((c) => {
      setControl(c);
      setComment(c.comment || "");
      setDeviation(c.deviation || "");
      setCorrectiveAction(c.corrective_action || "");
      setEvidenceReference(c.evidence_reference || "");
    });
  }, [assessmentId, controlId]);

  async function handleStatus(status) {
    const updated = await api.updateStatus(assessmentId, controlId, status, actor);
    setControl(updated);
    onChanged();
  }

  function persistFindingExtra(fields) {
    if (!controlId) return;
    api.updateFinding(assessmentId, controlId, fields, actor)
      .then((updated) => {
        setControl(updated);
        setSavedNote(new Date().toLocaleTimeString("de-DE"));
        onChanged();
      })
      .catch(console.error);
  }

  function handleCommentChange(e) {
    const value = e.target.value;
    setComment(value);
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      await api.updateComment(assessmentId, controlId, value, actor);
      setSavedNote(new Date().toLocaleTimeString("de-DE"));
      onChanged();
    }, 900);
  }

  function scheduleFindingFieldUpdate(field, value) {
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      api.updateFinding(assessmentId, controlId, { [field]: value }, actor)
        .then((updated) => {
          setControl(updated);
          setSavedNote(new Date().toLocaleTimeString("de-DE"));
          onChanged();
        })
        .catch(console.error);
    }, 700);
  }

  function updateFindingField(field, value) {
    if (field === "comment") {
      setComment(value);
      clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => {
        api.updateComment(assessmentId, controlId, value, actor)
          .then(() => {
            setSavedNote(new Date().toLocaleTimeString("de-DE"));
            onChanged();
          })
          .catch(console.error);
      }, 900);
      return;
    }
    if (field === "deviation") setDeviation(value);
    if (field === "corrective_action") setCorrectiveAction(value);
    if (field === "evidence_reference") setEvidenceReference(value);
    scheduleFindingFieldUpdate(field, value);
  }

  if (!controlId) {
    return <div className="col col-main"><div className="empty">Wähle links eine Anforderung aus.</div></div>;
  }
  if (!control) {
    return <div className="col col-main"><div className="loading">Lade Anforderung…</div></div>;
  }

  return (
    <div className="col col-main">
      <div className="main-inner">
        <div className="req-eyebrow">
          <span className="req-code">Art. {control.code}</span>
        </div>
        <h1 className="req-title">{control.title}</h1>
        {control.prose && <p className="req-body">{control.prose}</p>}

        <div className="audit-meta-grid">
          <div className="meta-card">
            <span className="meta-label">Zuständiger Prüfer</span>
            <div className="meta-value">{assessment?.responsible || "M. Muster"}</div>
          </div>
          <div className="meta-card">
            <span className="meta-label">Fälligkeitsdatum</span>
            <div className="meta-value">{assessment?.due_date || "—"}</div>
          </div>
        </div>

        <div className="section-label">Review-Status</div>
        <div className="review-row">
          {reviewOptions?.map((opt) => (
            <button
              key={opt.value}
              className={`review-chip ${assessment?.review_status === opt.value ? "active" : ""}`}
              onClick={() => onReviewStatus(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="status-row">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              className={`status-btn ${control.status === opt.key ? "sel-" + opt.key : ""}`}
              onClick={() => handleStatus(opt.key)}
            >
              <span className="dot" style={{ background: opt.color }}></span>
              {opt.label}
            </button>
          ))}
        </div>

        <div className="section-label">Gemappte Kontrollen (Cross-Framework)</div>
        {control.mappings.length === 0 && (
          <div style={{ fontSize: 12.5, color: "#9CA39E" }}>Keine Mappings hinterlegt.</div>
        )}
        {control.mappings.map((m) => (
          <div className="mapping-chip" key={m.id}>
            <span className={`mapping-src ${m.framework.startsWith("BSI") ? "bsi" : ""}`}>
              {m.framework}
            </span>
            <span className="mapping-code">{m.code}</span>
            <span className="mapping-desc">{m.description}</span>
          </div>
        ))}

        <div className="section-label">Mängel- / CAPA-Management</div>
        <textarea
          className="field-box"
          value={deviation}
          placeholder="Abweichung / Mangelbeschreibung"
          onChange={(e) => updateFindingField("deviation", e.target.value)}
        />
        <div style={{ height: 10 }} />
        <textarea
          className="field-box"
          value={correctiveAction}
          placeholder="Abhilfemaßnahme / CAPA"
          onChange={(e) => updateFindingField("corrective_action", e.target.value)}
        />
        <div style={{ height: 10 }} />
        <input
          className="mini-field"
          value={evidenceReference}
          placeholder="Nachweisverweis, z. B. 'Siehe Dokumentation S. 12, Evidenz 1'"
          onChange={(e) => updateFindingField("evidence_reference", e.target.value)}
        />

        <div className="section-label">Prüfer-Kommentar</div>
        <textarea className="comment-box" value={comment} onChange={handleCommentChange} />
        <div className="autosave-note">
          <span className="dot"></span>
          {savedNote ? `Automatisch gespeichert · ${savedNote}` : "Änderungen werden automatisch gespeichert"}
        </div>
      </div>
    </div>
  );
}
