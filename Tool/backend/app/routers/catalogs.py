import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
# WICHTIG: Assessment und ProfileSelection importieren!
from ..models import Catalog, Control, Finding, Assessment, ProfileSelection 
from ..schemas import CatalogOut, ControlTreeNode
from ..services.oscal_parser import parse_and_store, OscalValidationError

router = APIRouter(prefix="/api/catalogs", tags=["catalogs"])


@router.get("", response_model=list[CatalogOut])
def list_catalogs(db: Session = Depends(get_db)):
    return db.query(Catalog).order_by(Catalog.id).all()


@router.post("/import", response_model=CatalogOut)
async def import_catalog(
    file: UploadFile = File(...),
    source: str = Form("NIS2"),
    db: Session = Depends(get_db),
):
    """Importiert einen OSCAL-Catalog (JSON) — validiert Schema, persistiert Gruppen/Kontrollen."""
    raw = await file.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Ungueltiges JSON: {e}")

    try:
        catalog = parse_and_store(db, data, source_label=source)
    except OscalValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return catalog


def _build_tree(controls: list[Control], findings_by_control: dict[int, str], allowed_ids: set[int] | None = None) -> list[ControlTreeNode]:
    by_parent: dict[int | None, list[Control]] = {}
    for c in controls:
        # Wenn wir ein Profil haben (allowed_ids ist nicht None), ignorieren wir Blatt-Kontrollen, 
        # die nicht im Profil ausgewählt wurden.
        if allowed_ids is not None and not c.is_group and c.id not in allowed_ids:
            continue
        by_parent.setdefault(c.parent_id, []).append(c)
        
    for siblings in by_parent.values():
        siblings.sort(key=lambda c: c.sort_order)

    def build(parent_id):
        nodes = []
        for c in by_parent.get(parent_id, []):
            children = build(c.id)
            
            # Leere Gruppen verstecken: Wenn eine Gruppe nach dem Filtern keine Kinder mehr hat, 
            # wird sie nicht im Baum angezeigt (verhindert leere Ordner in der UI).
            if allowed_ids is not None and c.is_group and not children:
                continue
                
            nodes.append(
                ControlTreeNode(
                    id=c.id,
                    code=c.code,
                    title=c.title,
                    is_group=c.is_group,
                    status=None if c.is_group else findings_by_control.get(c.id, "open"),
                    children=children,
                )
            )
        return nodes

    return build(None)


@router.get("/{catalog_id}/tree", response_model=list[ControlTreeNode])
def get_catalog_tree(
    catalog_id: int,
    assessment_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    catalog = db.query(Catalog).filter(Catalog.id == catalog_id).first()
    if catalog is None:
        raise HTTPException(status_code=404, detail="Katalog nicht gefunden")

    controls = db.query(Control).filter(Control.catalog_id == catalog_id).all()

    findings_by_control = {}
    allowed_ids = None

    if assessment_id is not None:
        # 1. Bestehende Findings laden
        findings = db.query(Finding).filter(Finding.assessment_id == assessment_id).all()
        findings_by_control = {f.control_id: f.status for f in findings}
        
        # 2. OSCAL Profile-Check: Hat das Assessment ein Tailoring-Profil?
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if assessment and getattr(assessment, "profile_id", None):
            selections = db.query(ProfileSelection).filter(
                ProfileSelection.profile_id == assessment.profile_id,
                ProfileSelection.is_included == True
            ).all()
            allowed_ids = {sel.control_id for sel in selections}

    return _build_tree(controls, findings_by_control, allowed_ids)