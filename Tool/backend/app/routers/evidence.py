import os
import shutil
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Evidence
from ..schemas import EvidenceOut, EvidenceLinkCreate
from ..services.assessment_engine import get_or_create_finding, log_action

router = APIRouter(prefix="/api/assessments", tags=["evidence"])

STORAGE_ROOT = os.getenv("EVIDENCE_STORAGE_PATH", "/data/evidence")


@router.get("/{assessment_id}/controls/{control_id}/evidence", response_model=list[EvidenceOut])
def list_evidence(assessment_id: int, control_id: int, db: Session = Depends(get_db)):
    finding = get_or_create_finding(db, assessment_id, control_id)
    return db.query(Evidence).filter(Evidence.finding_id == finding.id).order_by(Evidence.uploaded_at.desc()).all()


@router.post("/{assessment_id}/controls/{control_id}/evidence/file", response_model=EvidenceOut)
async def upload_evidence_file(
    assessment_id: int, control_id: int,
    file: UploadFile = File(...), actor: str = Form("unknown"),
    db: Session = Depends(get_db),
):
    finding = get_or_create_finding(db, assessment_id, control_id)

    target_dir = os.path.join(STORAGE_ROOT, str(assessment_id), str(control_id))
    os.makedirs(target_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    target_path = os.path.join(target_dir, safe_name)

    with open(target_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    ev = Evidence(
        finding_id=finding.id, kind="file", filename=file.filename,
        filepath=target_path, uploaded_by=actor,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    log_action(db, assessment_id, control_id, actor, f"Nachweis '{file.filename}' hochgeladen")
    return ev


@router.get("/{assessment_id}/controls/{control_id}/evidence/{evidence_id}/open")
def open_evidence(assessment_id: int, control_id: int, evidence_id: int, db: Session = Depends(get_db)):
    finding = get_or_create_finding(db, assessment_id, control_id)
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id, Evidence.finding_id == finding.id).first()
    if evidence is None:
        raise HTTPException(status_code=404, detail="Nachweis nicht gefunden")

    if evidence.kind == "link" and evidence.url:
        return RedirectResponse(url=evidence.url)

    if evidence.kind == "file":
        if not evidence.filepath or not os.path.exists(evidence.filepath):
            raise HTTPException(status_code=404, detail="Datei nicht mehr vorhanden")
        return FileResponse(evidence.filepath, filename=evidence.filename)

    raise HTTPException(status_code=400, detail="Unbekannter Nachweistyps")


@router.delete("/{assessment_id}/controls/{control_id}/evidence/{evidence_id}")
def delete_evidence(assessment_id: int, control_id: int, evidence_id: int, db: Session = Depends(get_db)):
    finding = get_or_create_finding(db, assessment_id, control_id)
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id, Evidence.finding_id == finding.id).first()
    if evidence is None:
        raise HTTPException(status_code=404, detail="Nachweis nicht gefunden")

    if evidence.kind == "file" and evidence.filepath and os.path.exists(evidence.filepath):
        try:
            os.remove(evidence.filepath)
        except OSError:
            pass

    db.delete(evidence)
    db.commit()

    log_action(db, assessment_id, control_id, "system", f"Nachweis '{evidence.filename}' entfernt")
    return {"ok": True}


@router.post("/{assessment_id}/controls/{control_id}/evidence/link", response_model=EvidenceOut)
def add_evidence_link(assessment_id: int, control_id: int, payload: EvidenceLinkCreate, db: Session = Depends(get_db)):
    finding = get_or_create_finding(db, assessment_id, control_id)

    ev = Evidence(
        finding_id=finding.id, kind="link", filename=payload.filename,
        url=payload.url, uploaded_by=payload.actor,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    log_action(db, assessment_id, control_id, payload.actor, f"Externer Nachweis '{payload.filename}' verknuepft")
    return ev
