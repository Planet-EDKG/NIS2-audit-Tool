"""
Laedt beim ersten Start optional Demo-Daten: NIS2-Beispielkatalog inkl.
Cross-Framework-Mappings (ISO 27001 / BSI IT-Grundschutz) sowie ein
Beispiel-Audit mit vorbelegten Findings — ausschliesslich zu Demonstrationszwecken
(gesteuert ueber ENV SEED_DEMO_DATA).
"""
import json
import os
from sqlalchemy.orm import Session

from .models import Catalog, Control, Mapping, Assessment, Finding
from .services.oscal_parser import parse_and_store

SEED_FILE = os.path.join(os.path.dirname(__file__), "seed_data", "nis2_sample_catalog.json")

# code -> [(framework, code, description), ...]
DEMO_MAPPINGS = {
    "21.2a": [("ISO 27001", "A.5.7", "Bedrohungsanalyse")],
    "21.2b": [("ISO 27001", "A.5.19", "Informationssicherheit in Lieferantenbeziehungen")],
    "21.2c": [("BSI IT-GS", "DER.2.1", "Behandlung von Sicherheitsvorfaellen")],
    "21.2d": [
        ("ISO 27001", "A.8.8", "Management technischer Schwachstellen — Patch Management"),
        ("BSI IT-GS", "CON.3", "Regelmaessige Datensicherung & Wiederherstellungstests"),
        ("ISO 27001", "A.5.15", "Zugangssteuerung — Rollenbasierte Berechtigungskonzepte"),
    ],
    "21.2e": [("ISO 27001", "A.8.24", "Verwendung von Kryptografie")],
    "21.2f": [("BSI IT-GS", "ORP.2", "Personal")],
    "21.2g": [("ISO 27001", "A.8.5", "Sichere Authentifizierung")],
    "21.2h": [("BSI IT-GS", "INF.1", "Redundante Kommunikationswege")],
}

DEMO_FINDINGS = {
    "21.2a": ("fulfilled", None),
    "21.2b": ("fulfilled", None),
    "21.2c": ("open", "Meldeprozess an nationale Behoerde noch nicht final abgestimmt."),
    "21.2d": ("partial", "Konzept fuer Schwachstellenmanagement liegt vor (v2.1). Umsetzung des "
                          "Patch-Zyklus fuer Legacy-Systeme (SCADA-Umfeld) noch nicht vollstaendig "
                          "dokumentiert — Nachreichung bis Q1 2027 zugesagt."),
    "21.2e": ("na", "Kein Transport sensibler personenbezogener Daten in diesem Scope."),
    "21.2f": ("open", None),
    "21.2g": ("fulfilled", None),
    "21.2h": ("partial", "Redundanz fuer Sprachkommunikation vorhanden, Video-Backup fehlt."),
}


def seed_if_empty(db: Session):
    if db.query(Catalog).count() > 0:
        return

    with open(SEED_FILE, encoding="utf-8") as f:
        data = json.load(f)

    catalog = parse_and_store(db, data, source_label="NIS2")

    controls_by_code = {
        c.code: c for c in db.query(Control).filter(Control.catalog_id == catalog.id).all()
    }

    for code, mappings in DEMO_MAPPINGS.items():
        control = controls_by_code.get(code)
        if not control:
            continue
        for framework, m_code, desc in mappings:
            db.add(Mapping(control_id=control.id, framework=framework, code=m_code, description=desc))
    db.commit()

    assessment = Assessment(
        title="NIS2 Audit 2026",
        catalog_id=catalog.id,
        target_scope="IT-Betrieb GmbH",
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    for code, (status, comment) in DEMO_FINDINGS.items():
        control = controls_by_code.get(code)
        if not control:
            continue
        db.add(Finding(
            assessment_id=assessment.id, control_id=control.id,
            status=status, comment=comment, updated_by="M. Muster",
        ))
    db.commit()
