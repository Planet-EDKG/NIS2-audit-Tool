from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Assessment, Control, Finding, AuditLog, Mapping, Catalog
from ..schemas import (
    AssessmentCreate, AssessmentOut, AssessmentProgress, ControlDetail,
    StatusUpdate, CommentUpdate, AssessmentUpdate, FindingUpdate, DashboardOut,
    AuditLogOut, MappingOut,
)
from ..services.assessment_engine import get_or_create_finding, log_action, compute_progress, compute_dashboard
from ..config import get_settings

router = APIRouter(prefix="/api/assessments", tags=["assessments"])

VALID_STATUSES = {"open", "partial", "fulfilled", "na"}
VALID_REVIEW_STATUSES = {"draft", "review_required", "approved", "rejected"}


@router.get("", response_model=list[AssessmentOut])
def list_assessments(db: Session = Depends(get_db)):
    return db.query(Assessment).order_by(Assessment.id).all()


@router.post("", response_model=AssessmentOut)
def create_assessment(payload: AssessmentCreate, db: Session = Depends(get_db)):
    catalog = db.query(Catalog).filter(Catalog.id == payload.catalog_id).first()
    if catalog is None:
        raise HTTPException(status_code=404, detail="Katalog nicht gefunden")

    assessment = Assessment(
        title=payload.title,
        catalog_id=payload.catalog_id,
        target_scope=payload.target_scope,
        responsible=payload.responsible or get_settings().get("default_actor"),
        due_date=payload.due_date,
        review_status=payload.review_status or "draft",
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    log_action(db, assessment.id, None, "system", f"Audit '{assessment.title}' angelegt")
    return assessment


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    return compute_dashboard(db)


@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment(assessment_id: int, db: Session = Depends(get_db)):
    a = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if a is None:
        raise HTTPException(status_code=404, detail="Audit nicht gefunden")
    return a


@router.get("/{assessment_id}/progress", response_model=AssessmentProgress)
def get_progress(assessment_id: int, db: Session = Depends(get_db)):
    return compute_progress(db, assessment_id)


@router.put("/{assessment_id}", response_model=AssessmentOut)
def update_assessment(assessment_id: int, payload: AssessmentUpdate, db: Session = Depends(get_db)):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Audit nicht gefunden")

    if payload.review_status is not None:
        if payload.review_status not in VALID_REVIEW_STATUSES:
            raise HTTPException(status_code=400, detail=f"Ungueltiger Review-Status. Erlaubt: {sorted(VALID_REVIEW_STATUSES)}")
        assessment.review_status = payload.review_status
    if payload.title is not None:
        assessment.title = payload.title
    if payload.target_scope is not None:
        assessment.target_scope = payload.target_scope
    if payload.responsible is not None:
        assessment.responsible = payload.responsible
    if payload.due_date is not None:
        assessment.due_date = payload.due_date

    db.commit()
    db.refresh(assessment)
    log_action(db, assessment.id, None, payload.actor, f"Audit '{assessment.title}' aktualisiert")
    return assessment


@router.get("/{assessment_id}/controls/{control_id}", response_model=ControlDetail)
def get_control_detail(assessment_id: int, control_id: int, db: Session = Depends(get_db)):
    control = db.query(Control).filter(Control.id == control_id).first()
    if control is None or control.is_group:
        raise HTTPException(status_code=404, detail="Kontrolle nicht gefunden")

    finding = get_or_create_finding(db, assessment_id, control_id)
    mappings = db.query(Mapping).filter(Mapping.control_id == control_id).all()

    return ControlDetail(
        id=control.id,
        code=control.code,
        title=control.title,
        prose=control.prose,
        status=finding.status,
        comment=finding.comment,
        deviation=finding.deviation,
        corrective_action=finding.corrective_action,
        evidence_reference=finding.evidence_reference,
        finding_id=finding.id,
        mappings=[MappingOut.model_validate(m) for m in mappings],
    )


@router.put("/{assessment_id}/controls/{control_id}/status", response_model=ControlDetail)
def update_status(assessment_id: int, control_id: int, payload: StatusUpdate, db: Session = Depends(get_db)):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Ungueltiger Status. Erlaubt: {VALID_STATUSES}")

    finding = get_or_create_finding(db, assessment_id, control_id)
    old_status = finding.status
    finding.status = payload.status
    finding.updated_by = payload.actor
    db.commit()

    control = db.query(Control).filter(Control.id == control_id).first()
    log_action(
        db, assessment_id, control_id, payload.actor,
        f"Status von '{control.code}' geaendert: {old_status} -> {payload.status}",
    )
    return get_control_detail(assessment_id, control_id, db)


@router.put("/{assessment_id}/controls/{control_id}/comment", response_model=ControlDetail)
def update_comment(assessment_id: int, control_id: int, payload: CommentUpdate, db: Session = Depends(get_db)):
    finding = get_or_create_finding(db, assessment_id, control_id)
    finding.comment = payload.comment
    finding.updated_by = payload.actor
    db.commit()

    control = db.query(Control).filter(Control.id == control_id).first()
    log_action(db, assessment_id, control_id, payload.actor, f"Kommentar zu '{control.code}' aktualisiert")
    return get_control_detail(assessment_id, control_id, db)


@router.put("/{assessment_id}/controls/{control_id}/finding", response_model=ControlDetail)
def update_finding(assessment_id: int, control_id: int, payload: FindingUpdate, db: Session = Depends(get_db)):
    finding = get_or_create_finding(db, assessment_id, control_id)
    if payload.comment is not None:
        finding.comment = payload.comment
    if payload.deviation is not None:
        finding.deviation = payload.deviation
    if payload.corrective_action is not None:
        finding.corrective_action = payload.corrective_action
    if payload.evidence_reference is not None:
        finding.evidence_reference = payload.evidence_reference
    finding.updated_by = payload.actor
    db.commit()

    control = db.query(Control).filter(Control.id == control_id).first()
    log_action(db, assessment_id, control_id, payload.actor, f"Mangel zu '{control.code}' aktualisiert")
    return get_control_detail(assessment_id, control_id, db)


@router.get("/{assessment_id}/audit-trail", response_model=list[AuditLogOut])
def get_audit_trail(assessment_id: int, control_id: int | None = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(AuditLog).filter(AuditLog.assessment_id == assessment_id)
    if control_id is not None:
        q = q.filter(AuditLog.control_id == control_id)
    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()

@router.put("/{assessment_id}/phase", response_model=AssessmentOut)
def update_phase(assessment_id: int, phase: str, db: Session = Depends(get_db)):
    valid_phases = ["plan", "execution", "result"]
    if phase not in valid_phases:
        raise HTTPException(status_code=400, detail="Ungültige Phase")
    
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404)
        
    assessment.phase = phase
    db.commit()
    db.refresh(assessment)
    return assessment