from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import uuid
from app.database import get_db, engine
from app.models.volunteer import Volunteer
from app.schemas.volunteer import VolunteerCreate, VolunteerUpdate, VolunteerResponse

router = APIRouter(prefix="/volunteers", tags=["Volunteer CRUD"])

def ensure_columns():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE volunteers ADD COLUMN IF NOT EXISTS created_by_email VARCHAR DEFAULT 'commander@ndma.gov.in';"))
            conn.execute(text("ALTER TABLE volunteers ADD COLUMN IF NOT EXISTS phone VARCHAR DEFAULT '+91 9876543210';"))
            conn.execute(text("ALTER TABLE volunteers ADD COLUMN IF NOT EXISTS skills VARCHAR DEFAULT 'General Relief, First Aid';"))
            conn.execute(text("ALTER TABLE volunteers ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'AVAILABLE';"))
            conn.execute(text("ALTER TABLE volunteers ADD COLUMN IF NOT EXISTS assigned_zone_id VARCHAR;"))
            conn.execute(text("ALTER TABLE volunteers ADD COLUMN IF NOT EXISTS latitude FLOAT DEFAULT 27.7172;"))
            conn.execute(text("ALTER TABLE volunteers ADD COLUMN IF NOT EXISTS longitude FLOAT DEFAULT 85.3240;"))
            conn.commit()
    except Exception as e:
        print(f"[WARN] Column migration: {e}")

ensure_columns()

@router.get("", response_model=List[VolunteerResponse])
def get_volunteers(db: Session = Depends(get_db)):
    ensure_columns()
    return db.query(Volunteer).order_by(Volunteer.created_at.desc()).all()

@router.post("", response_model=VolunteerResponse)
def create_volunteer(payload: VolunteerCreate, db: Session = Depends(get_db)):
    ensure_columns()
    vol_id = payload.id or f"VOL-{uuid.uuid4().hex[:6].upper()}"
    
    clean_email = (payload.email or "").strip().lower()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    existing = db.query(Volunteer).filter(Volunteer.email == clean_email).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"A volunteer with email {clean_email} already exists.")

    creator = (payload.created_by_email or "").strip().lower()
    if not creator or "@" not in creator:
        raise HTTPException(status_code=401, detail="Authentication required: You must be logged in to register a volunteer.")

    new_vol = Volunteer(
        id=vol_id,
        name=(payload.name or "Field Volunteer").strip(),
        email=clean_email,
        phone=(payload.phone or "").strip(),
        skills=payload.skills or "First Aid, Search & Rescue",
        status=(payload.status or "AVAILABLE").upper(),
        assigned_zone_id=payload.assigned_zone_id or "Z-NEP-01",
        latitude=payload.latitude if payload.latitude is not None else 27.7172,
        longitude=payload.longitude if payload.longitude is not None else 85.3240,
        created_by_email=creator
    )

    try:
        db.add(new_vol)
        db.commit()
        db.refresh(new_vol)
        return new_vol
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database insertion failed: {str(e)}")

@router.put("/{vol_id}", response_model=VolunteerResponse)
def update_volunteer(
    vol_id: str, 
    payload: VolunteerUpdate, 
    requester_email: Optional[str] = Query(None),
    requester_role: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    ensure_columns()
    vol = db.query(Volunteer).filter(Volunteer.id == vol_id).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer record not found.")

    user_email = (payload.requester_email or requester_email or "").strip().lower()
    user_role = (payload.requester_role or requester_role or "").strip().upper()
    owner_email = (vol.created_by_email or "").strip().lower()

    if not user_email:
        raise HTTPException(status_code=401, detail="Authentication Required: You must be logged in to modify volunteer records.")

    is_owner = (user_email == owner_email)
    is_commander = (user_role == "COMMANDER" and user_email == "commander@ndma.gov.in")

    if not is_owner and not is_commander:
        raise HTTPException(
            status_code=403,
            detail=f"Permission Denied: You cannot modify volunteers registered by another user ({vol.created_by_email})."
        )

    for k, v in payload.dict(exclude_unset=True).items():
        if k not in ["requester_email", "requester_role", "id", "created_by_email"]:
            setattr(vol, k, v)

    try:
        db.commit()
        db.refresh(vol)
        return vol
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")

@router.delete("/{vol_id}")
def delete_volunteer(
    vol_id: str, 
    requester_email: Optional[str] = Query(None),
    requester_role: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    ensure_columns()
    vol = db.query(Volunteer).filter(Volunteer.id == vol_id).first()
    if not vol:
        raise HTTPException(status_code=404, detail="Volunteer record not found.")

    user_email = (requester_email or "").strip().lower()
    user_role = (requester_role or "").strip().upper()
    owner_email = (vol.created_by_email or "").strip().lower()

    if not user_email:
        raise HTTPException(status_code=401, detail="Authentication Required: You must be logged in to delete volunteer records.")

    is_owner = (user_email == owner_email)
    is_commander = (user_role == "COMMANDER" and user_email == "commander@ndma.gov.in")

    if not is_owner and not is_commander:
        raise HTTPException(
            status_code=403,
            detail=f"Permission Denied: You cannot delete volunteers created by another user ({vol.created_by_email})."
        )

    try:
        db.delete(vol)
        db.commit()
        return {"status": "DELETED", "id": vol_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Delete failed: {str(e)}")
