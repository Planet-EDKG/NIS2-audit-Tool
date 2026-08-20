from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Assessment, Catalog, Control, Finding
from ..services.assessment_engine import compute_progress
from ..services import export_engine

router = APIRouter(prefix="/api/assessments", tags=["export"])


def _collect_rows(db: Session, assessment: Assessment) -> list[dict]:
    controls = (
        db.query(Control)
        .filter(Control.catalog_id == assessment.catalog_id)
        .order_by(Control.sort_order)
        .all()
    )
    findings = {
        f.control_id: f
        for f in db.query(Finding).filter(Finding.assessment_id == assessment.id).all()
    }

    rows = []
    for c in controls:
        finding = findings.get(c.id)
        rows.append({
            "code": c.code,
            "title": c.title,
            "is_group": c.is_group,
            "status": (finding.status if finding else "open") if not c.is_group else None,
            "comment": finding.comment if finding else None,
        })
    return rows


def _load(db: Session, assessment_id: int):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Audit nicht gefunden")
    catalog = db.query(Catalog).filter(Catalog.id == assessment.catalog_id).first()
    return assessment, catalog


@router.get("/{assessment_id}/export/oscal")
def export_oscal(assessment_id: int, db: Session = Depends(get_db)):
    """Export des vollstaendigen Audit-Ergebnisses als valides OSCAL Assessment Results (JSON)."""
    assessment, catalog = _load(db, assessment_id)
    rows = _collect_rows(db, assessment)
    progress = compute_progress(db, assessment_id)
    return export_engine.build_oscal_assessment_results(assessment, catalog, rows, progress)


@router.get("/{assessment_id}/export/report.html")
def export_report_html(assessment_id: int, db: Session = Depends(get_db)):
    """Human-Readable HTML-Pruefbericht fuer Auditoren, Fuehrungskraefte und Behoerden."""
    assessment, catalog = _load(db, assessment_id)
    rows = _collect_rows(db, assessment)
    progress = compute_progress(db, assessment_id)
    html = export_engine.render_html_report(assessment, catalog, rows, progress)
    return Response(content=html, media_type="text/html")


@router.get("/{assessment_id}/export/report.pdf")
def export_report_pdf(assessment_id: int, db: Session = Depends(get_db)):
    assessment, catalog = _load(db, assessment_id)
    rows = _collect_rows(db, assessment)
    progress = compute_progress(db, assessment_id)
    html = export_engine.render_html_report(assessment, catalog, rows, progress)
    try:
        pdf_bytes = export_engine.html_to_pdf(html)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF-Export fehlgeschlagen: {exc}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="audit-{assessment_id}-bericht.pdf"'},
    )
