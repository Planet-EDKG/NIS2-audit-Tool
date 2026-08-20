from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings, save_settings
from ..database import get_db

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings")
def read_settings(db: Session = Depends(get_db)):
    del db
    return get_settings()


@router.put("/settings")
def write_settings(payload: dict, db: Session = Depends(get_db)):
    del db
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Einstellungen müssen als Objekt übergeben werden.")
    return save_settings(payload)
