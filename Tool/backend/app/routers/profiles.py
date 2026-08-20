from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Profile, ProfileSelection, Catalog, Control
from ..schemas import ProfileCreate, ProfileOut

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

@router.get("", response_model=list[ProfileOut])
def list_profiles(db: Session = Depends(get_db)):
    return db.query(Profile).order_by(Profile.id).all()

@router.post("", response_model=ProfileOut)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    catalog = db.query(Catalog).filter(Catalog.id == payload.catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Katalog nicht gefunden")

    profile = Profile(
        title=payload.title,
        description=payload.description,
        catalog_id=payload.catalog_id
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    control_ids = payload.included_control_ids
    if not control_ids:
        controls = db.query(Control).filter(Control.catalog_id == catalog.id, Control.is_group == False).all()
        control_ids = [c.id for c in controls]

    for ctrl_id in control_ids:
        selection = ProfileSelection(profile_id=profile.id, control_id=ctrl_id, is_included=True)
        db.add(selection)
    
    db.commit()
    return profile