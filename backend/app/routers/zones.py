from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.models.geospatial import DisasterZone
from app.models.inventory import ResourceDepot
from app.models.volunteer import Volunteer
from app.schemas.disaster import DisasterZoneResponse, DisasterZoneCreate
from app.services.ingestion import DisasterDataIngestion

router = APIRouter(prefix="/zones", tags=["Disaster Zones"])

def ensure_nepal_and_global_zones(db: Session):
    nepal_zones = [
        DisasterZone(id="Z-NEP-01", name="Kathmandu Valley & Bagmati Basin, Nepal", disaster_type="Severe Riverine Inundation & Mudslides", severity_score=9.7, population=165000, latitude=27.7172, longitude=85.3240),
        DisasterZone(id="Z-NEP-02", name="Koshi River & Eastern Terai Basin (Nepal-India Border)", disaster_type="High-Discharge Transboundary Flood Surge (>450k Cusecs)", severity_score=9.5, population=230000, latitude=26.8124, longitude=87.1834),
        DisasterZone(id="Z-NEP-03", name="Gandaki & Narayanghat-Mugling Corridor, Nepal", disaster_type="Hill-Slope Landslides & Highway Severance", severity_score=8.9, population=95000, latitude=28.2096, longitude=83.9856),
        DisasterZone(id="Z-GLOBAL-01", name="Tokyo Bay Megalopolis, Japan", disaster_type="Catastrophic 8.2 Earthquake & Tsunami", severity_score=9.6, population=145000, latitude=35.6762, longitude=139.6503),
        DisasterZone(id="Z-GLOBAL-02", name="Kahramanmaraş Fault Zone, Turkey", disaster_type="Major Seismicity & Structural Collapse", severity_score=9.3, population=92000, latitude=37.5753, longitude=36.9228),
        DisasterZone(id="Z-GLOBAL-03", name="Sumatra Trench, Indonesia", disaster_type="Tsunami Surge & Subduction Hazard", severity_score=8.9, population=110000, latitude=-0.5897, longitude=101.3431)
    ]
    for z in nepal_zones:
        existing = db.query(DisasterZone).filter(DisasterZone.id == z.id).first()
        if not existing:
            db.add(z)
    
    if db.query(ResourceDepot).filter(ResourceDepot.id == "DEPOT-KATHMANDU").first() is None:
        db.add(ResourceDepot(id="DEPOT-KATHMANDU", name="Nepal NEOC & TIA Emergency Airbase (Kathmandu, Nepal)", food_packets=120000, water_liters=350000, medical_kits=8500, available_vehicles=40, latitude=27.6966, longitude=85.3591))
    
    if db.query(Volunteer).filter(Volunteer.id == "VOL-NEP-101").first() is None:
        db.add_all([
            Volunteer(id="VOL-NEP-101", name="Capt. Bikram Thapa (Airborne Search & Rescue)", email="bikram.thapa@nepalarmy.mil.np", phone="+977 9841234567", skills="High-Altitude Swiftwater Rescue, Rope Access", status="DEPLOYED", latitude=27.7172, longitude=85.3240, created_by_email="commander@ndma.gov.in"),
            Volunteer(id="VOL-NEP-102", name="Dr. Sunita Shrestha (Nepal Red Cross)", email="sunita.shrestha@nrcs.org", phone="+977 9851098765", skills="Epidemic Prevention, Trauma Triage, Water Purification", status="AVAILABLE", latitude=27.6966, longitude=85.3591, created_by_email="commander@ndma.gov.in"),
            Volunteer(id="VOL-NEP-103", name="Rajeshwor Yadav (Indo-Nepal Transboundary Liaison)", email="rajeshwor.yadav@disaster-mgmt.in", phone="+91 9835012345", skills="Koshi Embankment Monitoring, Boat Evacuation", status="DEPLOYED", latitude=26.8124, longitude=87.1834, created_by_email="commander@ndma.gov.in")
        ])
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()

@router.get("", response_model=List[DisasterZoneResponse])
def list_zones(db: Session = Depends(get_db)):
    ensure_nepal_and_global_zones(db)
    return db.query(DisasterZone).order_by(DisasterZone.severity_score.desc()).all()

@router.post("/sync-nepal-data")
def sync_nepal_data(db: Session = Depends(get_db)):
    ensure_nepal_and_global_zones(db)
    return {
        "status": "SUCCESS",
        "message": "Nepal Flood Zones and Aid Hubs synchronized successfully!"
    }

@router.get("/global-disasters")
async def get_global_disasters():
    return await DisasterDataIngestion.fetch_usgs_earthquakes()

@router.post("", response_model=DisasterZoneResponse)
def create_zone(payload: DisasterZoneCreate, db: Session = Depends(get_db)):
    existing = db.query(DisasterZone).filter(DisasterZone.id == payload.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Zone ID already exists")
    new_zone = DisasterZone(**payload.dict())
    db.add(new_zone)
    db.commit()
    db.refresh(new_zone)
    return new_zone
