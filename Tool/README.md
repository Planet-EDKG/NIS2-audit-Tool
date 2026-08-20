# NIS2 Audit Workspace — OSCAL Compliance Suite

Lauffähige Docker-Umsetzung der in `Systemarchitektur & Datenfluss` beschriebenen
3-Schichten-Architektur: React-Frontend, FastAPI-Backend mit OSCAL Parser-,
Assessment- und Export-Engine, PostgreSQL als relationaler Caching-Layer sowie
lokaler Datei-Storage für Nachweise (kein Cloud-Zwang, siehe N3).

## Architektur (wie umgesetzt)

```
┌────────────────────────┐   REST/JSON   ┌──────────────────────────────┐
│  frontend (React+Vite) │ ───────────►  │  backend (FastAPI)           │
│  Katalog/Mapper · Prüf-│               │  ├─ OSCAL Parser Engine      │
│  Workspace · Reports   │ ◄───────────  │  ├─ Assessment Engine        │
│  → Docker: nginx:alpine│               │  └─ Export Engine (Jinja2/   │
└────────────────────────┘               │     WeasyPrint)              │
                                          └──────────┬────────┬─────────┘
                                                      │        │
                                     ┌────────────────▼──┐  ┌──▼─────────────────┐
                                     │ PostgreSQL 16      │  │ Docker Volume      │
                                     │ (Kataloge, Mappings,│  │ /data/evidence     │
                                     │ Findings, Audit-Log)│  │ (Nachweis-Dateien) │
                                     └─────────────────────┘  └─────────────────────┘
```

Jeder Dienst läuft in einem eigenen Container (`docker-compose.yml`):

| Service    | Image/Build         | Zweck                                              |
|------------|----------------------|-----------------------------------------------------|
| `db`       | `postgres:16-alpine` | Relationaler Caching-Layer für Kataloge/Findings    |
| `backend`  | `./backend`           | FastAPI: Parser-, Assessment- und Export-Engine     |
| `frontend` | `./frontend`          | React-UI, per nginx ausgeliefert, proxied `/api`    |

## Start

```bash
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend / API-Docs (Swagger): http://localhost:8000/docs
- Beim ersten Start lädt das Backend automatisch einen Demo-NIS2-Katalog
  (Art. 21.2 a–h) inkl. ISO-27001/BSI-Mappings und ein Beispiel-Audit
  (steuerbar über `SEED_DEMO_DATA` in `docker-compose.yml`).

## Wichtige Endpunkte

| Methode | Pfad                                                              | Zweck |
|---------|--------------------------------------------------------------------|-------|
| POST    | `/api/catalogs/import`                                             | OSCAL-Catalog-JSON importieren & validieren |
| GET     | `/api/catalogs/{id}/tree?assessment_id=`                           | Katalogbaum inkl. Status pro Audit |
| POST    | `/api/assessments`                                                 | Neues Audit anlegen |
| GET     | `/api/assessments/{id}/controls/{control_id}`                      | Anforderung + Mappings + Finding |
| PUT     | `/api/assessments/{id}/controls/{control_id}/status`                | Erfüllungsgrad setzen (→ Audit-Log) |
| PUT     | `/api/assessments/{id}/controls/{control_id}/comment`                | Prüfer-Kommentar (Auto-Save) |
| POST    | `/api/assessments/{id}/controls/{control_id}/evidence/file`          | Nachweis-Datei hochladen |
| POST    | `/api/assessments/{id}/controls/{control_id}/evidence/link`          | Externen Nachweis verlinken |
| GET     | `/api/assessments/{id}/audit-trail`                                 | Historisierung (N2: Fälschungssicherheit) |
| GET     | `/api/assessments/{id}/export/oscal`                                | OSCAL Assessment Results (JSON) |
| GET     | `/api/assessments/{id}/export/report.html`                          | Human-Readable HTML-Bericht |
| GET     | `/api/assessments/{id}/export/report.pdf`                           | PDF-Bericht (WeasyPrint) |

## Eigenen Katalog importieren

```bash
curl -F "file=@mein-iso27001-katalog.json" -F "source=ISO27001" \
     http://localhost:8000/api/catalogs/import
```

Das JSON muss dem vereinfachten OSCAL-1.1.0-Catalog-Schema folgen
(`catalog.metadata.title`, `catalog.groups[].controls[]`, siehe
`backend/app/seed_data/nis2_sample_catalog.json` als Referenz).

## Nicht-funktionale Anforderungen — Umsetzung

- **N1 (Standard-Konformität):** Parser validiert gegen das OSCAL-1.1.0-Grundschema
  vor dem Import; Export erzeugt ein `assessment-results`-Dokument.
- **N2 (Audit-Trails):** jede Status-/Kommentar-/Nachweis-Änderung schreibt einen
  `AuditLog`-Eintrag (wer, was, wann).
- **N3 (Governance):** vollständig On-Premise via `docker compose`, keine
  Cloud-Abhängigkeit; Nachweise liegen in einem lokalen Docker-Volume.
- **N4 (Performance):** Katalogbaum wird serverseitig relational aus PostgreSQL
  aggregiert und als flaches JSON an die UI geliefert (kein Parsen tief
  verschachtelter OSCAL-Dateien im Browser).

## Projektstruktur

```
nis2-audit-tool/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py              # FastAPI App, CORS, Startup/Seed
│       ├── database.py          # SQLAlchemy Engine/Session
│       ├── models.py            # Catalog, Control, Mapping, Assessment, Finding, Evidence, AuditLog
│       ├── schemas.py           # Pydantic Ein-/Ausgabemodelle
│       ├── seed.py              # Demo-Daten (NIS2 + Mappings + Beispiel-Audit)
│       ├── seed_data/
│       │   └── nis2_sample_catalog.json
│       ├── routers/
│       │   ├── catalogs.py      # Import + Baum-Endpunkt
│       │   ├── assessments.py   # Audits, Findings, Status/Kommentar, Audit-Trail
│       │   ├── evidence.py      # Datei-Upload / externe Links
│       │   └── export.py        # OSCAL-JSON / HTML / PDF
│       └── services/
│           ├── oscal_parser.py      # OSCAL Parser & Validation Engine
│           ├── assessment_engine.py # Findings, Fortschrittsberechnung, Audit-Log
│           └── export_engine.py     # OSCAL-Result-Builder + Jinja2/WeasyPrint-Report
└── frontend/
    ├── Dockerfile
    ├── nginx.conf                # /api-Proxy zum Backend-Container
    ├── vite.config.js
    └── src/
        ├── App.jsx               # Bootstrap, Topbar, Fortschritt, Export-Menü
        ├── api.js                # API-Client
        ├── index.css             # Fraunhofer-Grün Design-Tokens
        └── components/
            ├── Sidebar.jsx        # Spalte 1: Baumnavigation
            ├── MainPanel.jsx      # Spalte 2: Prüfbereich, Status, Mappings, Kommentar
            └── EvidencePanel.jsx  # Spalte 3: Nachweise, Audit-Trail
```
