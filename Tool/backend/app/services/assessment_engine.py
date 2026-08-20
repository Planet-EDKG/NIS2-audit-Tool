"""
Assessment Engine
-----------------
Verwaltet den Zustand laufender Audits: legt fehlende Findings lazy an,
fuehrt Mappings zur Laufzeit mit den Kontrollen zusammen und berechnet
den Gesamtfortschritt eines Audits.
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..models import Control, Finding, AuditLog, Assessment

WEIGHTS = {"fulfilled": 1.0, "partial": 0.5, "open": 0.0}
REVIEW_STATUS_ORDER = ["draft", "review_required", "approved", "rejected"]


def get_or_create_finding(db: Session, assessment_id: int, control_id: int) -> Finding:
    finding = (
        db.query(Finding)
        .filter(Finding.assessment_id == assessment_id, Finding.control_id == control_id)
        .first()
    )
    if finding is None:
        finding = Finding(assessment_id=assessment_id, control_id=control_id, status="open")
        db.add(finding)
        try:
            db.commit()
            db.refresh(finding)
        except IntegrityError:
            # A parallel request inserted the same finding first.
            db.rollback()
            finding = (
                db.query(Finding)
                .filter(Finding.assessment_id == assessment_id, Finding.control_id == control_id)
                .first()
            )
            if finding is None:
                raise
    return finding


def log_action(db: Session, assessment_id: int, control_id: int | None, actor: str, action: str):
    db.add(AuditLog(assessment_id=assessment_id, control_id=control_id, actor=actor, action=action))
    db.commit()


def compute_progress(db: Session, assessment_id: int) -> dict:
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if assessment is None:
        return {"total": 0, "fulfilled": 0, "partial": 0, "open": 0, "na": 0, "progress_pct": 0.0}

    leaf_control_ids = [
        c.id
        for c in db.query(Control)
        .filter(Control.catalog_id == assessment.catalog_id, Control.is_group == False)  # noqa: E712
        .all()
    ]
    findings = (
        db.query(Finding)
        .filter(Finding.assessment_id == assessment_id, Finding.control_id.in_(leaf_control_ids))
        .all()
    )
    by_control = {f.control_id: f.status for f in findings}

    total = len(leaf_control_ids)
    counts = {"fulfilled": 0, "partial": 0, "open": 0, "na": 0}
    considered_weight_sum = 0.0
    considered_count = 0

    for cid in leaf_control_ids:
        status = by_control.get(cid, "open")
        counts[status] = counts.get(status, 0) + 1
        if status != "na":
            considered_weight_sum += WEIGHTS.get(status, 0.0)
            considered_count += 1

    progress_pct = round((considered_weight_sum / considered_count) * 100, 1) if considered_count else 0.0

    return {
        "total": total,
        "fulfilled": counts["fulfilled"],
        "partial": counts["partial"],
        "open": counts["open"],
        "na": counts["na"],
        "progress_pct": progress_pct,
    }


def compute_dashboard(db: Session) -> dict:
    audits = db.query(Assessment).all()
    scopes = sorted({a.target_scope for a in audits if a.target_scope})
    metrics = {"total": 0, "fulfilled": 0, "partial": 0, "open": 0, "na": 0, "review_required": 0, "approved": 0, "draft": 0}

    for assessment in audits:
        progress = compute_progress(db, assessment.id)
        metrics["total"] += progress["total"]
        metrics["fulfilled"] += progress["fulfilled"]
        metrics["partial"] += progress["partial"]
        metrics["open"] += progress["open"]
        metrics["na"] += progress["na"]

        review_key = assessment.review_status or "draft"
        if review_key == "review_required":
            metrics["review_required"] += 1
        elif review_key == "approved":
            metrics["approved"] += 1
        elif review_key == "draft":
            metrics["draft"] += 1

    return {
        "audits": len(audits),
        "scope_count": len(scopes),
        "metrics": metrics,
        "target_scopes": scopes,
    }
