"""
Export Engine
-------------
Wandelt den Audit-Zustand beim Abschluss zurueck in ein OSCAL-Assessment-Result
(JSON) um und rendert daraus einen menschenlesbaren HTML/PDF-Pruefbericht
(Corporate Design angelehnt an Fraunhofer-Gruen).
"""
import datetime as dt
import uuid
from jinja2 import Template

REPORT_TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{{ assessment.title }} — Pruefbericht</title>
<style>
  @page { size: A4; margin: 22mm 18mm; }
  body { font-family: 'Helvetica Neue', Arial, sans-serif; color:#1D2321; font-size:11pt; }
  h1 { color:#0E7A62; font-size:20pt; margin-bottom:2pt; }
  .meta { color:#545B58; font-size:9.5pt; margin-bottom:22pt; }
  .summary { display:flex; gap:14pt; margin-bottom:22pt; }
  .stat { border:1px solid #E1E4E2; border-left:3px solid #179C7D; padding:8pt 12pt; flex:1; }
  .stat b { display:block; font-size:16pt; color:#0E7A62; }
  .stat span { font-size:8.5pt; color:#545B58; text-transform:uppercase; letter-spacing:.05em; }
  table { width:100%; border-collapse:collapse; margin-bottom:16pt; }
  th, td { text-align:left; padding:6pt 8pt; border-bottom:1px solid #E1E4E2; font-size:9.5pt; vertical-align:top; }
  th { background:#E6F5F1; color:#0E7A62; font-size:8.5pt; text-transform:uppercase; letter-spacing:.04em; }
  .status-fulfilled { color:#0E7A62; font-weight:bold; }
  .status-partial { color:#8A5A1F; font-weight:bold; }
  .status-open { color:#8E3129; font-weight:bold; }
  .status-na { color:#9CA39E; font-weight:bold; }
  .group-row td { background:#FBFBFA; font-weight:bold; color:#1D2321; }
  .footer { margin-top:28pt; font-size:8pt; color:#9CA39E; }
</style>
</head>
<body>
  <h1>{{ assessment.title }}</h1>
  <div class="meta">
    Katalog: {{ catalog.title }} ({{ catalog.source }}) &middot;
    Zielobjekt: {{ assessment.target_scope or '—' }} &middot;
    Erstellt: {{ generated_at }}
  </div>

  <div class="summary">
    <div class="stat"><b>{{ progress.progress_pct }}%</b><span>Gesamtfortschritt</span></div>
    <div class="stat"><b>{{ progress.fulfilled }}</b><span>Erfuellt</span></div>
    <div class="stat"><b>{{ progress.partial }}</b><span>Teilweise erfuellt</span></div>
    <div class="stat"><b>{{ progress.open }}</b><span>Nicht erfuellt</span></div>
  </div>

  <table>
    <thead>
      <tr><th>Code</th><th>Anforderung</th><th>Status</th><th>Kommentar</th></tr>
    </thead>
    <tbody>
      {% for row in rows %}
        {% if row.is_group %}
        <tr class="group-row"><td colspan="4">{{ row.code }} — {{ row.title }}</td></tr>
        {% else %}
        <tr>
          <td>{{ row.code }}</td>
          <td>{{ row.title }}</td>
          <td class="status-{{ row.status }}">{{ row.status_label }}</td>
          <td>{{ row.comment or '—' }}</td>
        </tr>
        {% endif %}
      {% endfor %}
    </tbody>
  </table>

  <div class="footer">
    Generiert von OSCAL Compliance Suite &middot; Export-Format: Human-Readable Report &middot;
    Referenz-Standard: NIST OSCAL 1.1.0
  </div>
</body>
</html>
""")

STATUS_LABELS = {
    "fulfilled": "Fulfilled",
    "partial": "Partially Fulfilled",
    "open": "Non-Compliant",
    "na": "Not Applicable",
}


def build_oscal_assessment_results(assessment, catalog, rows: list[dict], progress: dict) -> dict:
    """Erzeugt ein valides OSCAL 'assessment-results'-Dokument aus dem internen Audit-Zustand."""
    now = dt.datetime.utcnow().isoformat() + "Z"
    findings = [
        {
            "uuid": str(uuid.uuid4()),
            "title": row["title"],
            "target": {"control-id": row["code"]},
            "status": {"state": row["status"]},
            "description": row.get("comment") or "",
        }
        for row in rows
        if not row["is_group"]
    ]

    return {
        "assessment-results": {
            "uuid": str(uuid.uuid4()),
            "metadata": {
                "title": assessment.title,
                "version": "1.0",
                "oscal-version": "1.1.0",
                "last-modified": now,
            },
            "import-ap": {"href": f"#assessment-plan-{assessment.id}"},
            "local-definitions": {
                "target-scope": assessment.target_scope,
                "catalog": catalog.title,
                "catalog-source": catalog.source,
            },
            "results": [
                {
                    "uuid": str(uuid.uuid4()),
                    "title": f"{assessment.title} — Ergebnis",
                    "start": now,
                    "reviewed-controls": {"control-selections": [{"include-all": {}}]},
                    "findings": findings,
                    "statistics": progress,
                }
            ],
        }
    }


def render_html_report(assessment, catalog, rows: list[dict], progress: dict) -> str:
    enriched_rows = [
        {**row, "status_label": STATUS_LABELS.get(row["status"], row["status"])}
        for row in rows
    ]
    return REPORT_TEMPLATE.render(
        assessment=assessment,
        catalog=catalog,
        rows=enriched_rows,
        progress=progress,
        generated_at=dt.datetime.now().strftime("%d.%m.%Y %H:%M"),
    )


def html_to_pdf(html: str) -> bytes:
    from weasyprint import HTML  # imported lazily: heavy native deps
    return HTML(string=html).write_pdf()
