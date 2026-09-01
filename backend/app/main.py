from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.database import Base, engine, SessionLocal, init_neon_extensions
from app.routers import auth, volunteers, zones, inventory, predictions, logistics
from app.models.geospatial import DisasterZone
from app.models.inventory import ResourceDepot
from app.models.volunteer import Volunteer
from app.models.user import User

init_neon_extensions()
Base.metadata.create_all(bind=engine)

def auto_seed_if_empty():
    db = SessionLocal()
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    email VARCHAR UNIQUE NOT NULL,
                    password VARCHAR NOT NULL,
                    role VARCHAR DEFAULT 'COMMANDER',
                    agency VARCHAR DEFAULT 'National Disaster Response Authority',
                    phone VARCHAR,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS volunteers (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    email VARCHAR UNIQUE NOT NULL,
                    phone VARCHAR DEFAULT '+91 9876543210',
                    skills VARCHAR DEFAULT 'First Aid, Rescue',
                    status VARCHAR DEFAULT 'AVAILABLE',
                    assigned_zone_id VARCHAR,
                    latitude FLOAT DEFAULT 27.7172,
                    longitude FLOAT DEFAULT 85.3240,
                    created_by_email VARCHAR DEFAULT 'commander@ndma.gov.in',
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS disaster_zones (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    disaster_type VARCHAR NOT NULL,
                    severity_score FLOAT NOT NULL,
                    population INTEGER NOT NULL,
                    latitude FLOAT NOT NULL,
                    longitude FLOAT NOT NULL
                );
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS resource_depots (
                    id VARCHAR PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    food_packets INTEGER DEFAULT 50000,
                    water_liters INTEGER DEFAULT 100000,
                    medical_kits INTEGER DEFAULT 2500,
                    available_vehicles INTEGER DEFAULT 30,
                    latitude FLOAT NOT NULL,
                    longitude FLOAT NOT NULL
                );
            """))
            conn.commit()

        if db.query(DisasterZone).filter(DisasterZone.id == "Z-NEP-01").first() is None:
            world_zones = [
                DisasterZone(id="Z-NEP-01", name="Kathmandu Valley & Bagmati Basin, Nepal", disaster_type="Severe Riverine Inundation & Mudslides", severity_score=9.7, population=165000, latitude=27.7172, longitude=85.3240),
                DisasterZone(id="Z-NEP-02", name="Koshi River & Eastern Terai Basin (Nepal-India Border)", disaster_type="High-Discharge Transboundary Flood Surge (>450k Cusecs)", severity_score=9.5, population=230000, latitude=26.8124, longitude=87.1834),
                DisasterZone(id="Z-NEP-03", name="Gandaki & Narayanghat-Mugling Corridor, Nepal", disaster_type="Hill-Slope Landslides & Highway Severance", severity_score=8.9, population=95000, latitude=28.2096, longitude=83.9856),
                DisasterZone(id="Z-GLOBAL-01", name="Tokyo Bay Megalopolis, Japan", disaster_type="Catastrophic 8.2 Earthquake & Tsunami", severity_score=9.6, population=145000, latitude=35.6762, longitude=139.6503),
                DisasterZone(id="Z-GLOBAL-02", name="Kahramanmaraş Fault Zone, Turkey", disaster_type="Major Seismicity & Structural Collapse", severity_score=9.3, population=92000, latitude=37.5753, longitude=36.9228),
                DisasterZone(id="Z-GLOBAL-03", name="Sumatra Trench, Indonesia", disaster_type="Tsunami Surge & Subduction Hazard", severity_score=8.9, population=110000, latitude=-0.5897, longitude=101.3431)
            ]
            for z in world_zones:
                if db.query(DisasterZone).filter(DisasterZone.id == z.id).first() is None:
                    db.add(z)
            db.commit()

        if db.query(ResourceDepot).filter(ResourceDepot.id == "DEPOT-KATHMANDU").first() is None:
            world_depots = [
                ResourceDepot(id="DEPOT-KATHMANDU", name="Nepal NEOC & TIA Emergency Airbase (Kathmandu, Nepal)", food_packets=120000, water_liters=350000, medical_kits=8500, available_vehicles=40, latitude=27.6966, longitude=85.3591),
                ResourceDepot(id="DEPOT-DELHI", name="UNHRD Regional Command & Transboundary Airlift Hub (New Delhi, India)", food_packets=300000, water_liters=750000, medical_kits=22000, available_vehicles=95, latitude=28.6139, longitude=77.2090),
                ResourceDepot(id="DEPOT-EUROPE", name="European Humanitarian Logistics Base (Geneva, Switzerland)", food_packets=180000, water_liters=450000, medical_kits=12000, available_vehicles=60, latitude=46.2044, longitude=6.1432),
                ResourceDepot(id="DEPOT-PACIFIC", name="Asia-Pacific Rapid Deployment Base (Tokyo, Japan)", food_packets=140000, water_liters=380000, medical_kits=9500, available_vehicles=45, latitude=35.5494, longitude=139.7798)
            ]
            for d in world_depots:
                if db.query(ResourceDepot).filter(ResourceDepot.id == d.id).first() is None:
                    db.add(d)
            db.commit()

        if db.query(Volunteer).filter(Volunteer.id == "VOL-NEP-101").first() is None:
            db.add_all([
                Volunteer(id="VOL-NEP-101", name="Capt. Bikram Thapa (Airborne Search & Rescue)", email="bikram.thapa@nepalarmy.mil.np", phone="+977 9841234567", skills="High-Altitude Swiftwater Rescue, Rope Access", status="DEPLOYED", latitude=27.7172, longitude=85.3240, created_by_email="commander@ndma.gov.in"),
                Volunteer(id="VOL-NEP-102", name="Dr. Sunita Shrestha (Nepal Red Cross)", email="sunita.shrestha@nrcs.org", phone="+977 9851098765", skills="Epidemic Prevention, Trauma Triage, Water Purification", status="AVAILABLE", latitude=27.6966, longitude=85.3591, created_by_email="commander@ndma.gov.in"),
                Volunteer(id="VOL-NEP-103", name="Rajeshwor Yadav (Indo-Nepal Transboundary Liaison)", email="rajeshwor.yadav@disaster-mgmt.in", phone="+91 9835012345", skills="Koshi Embankment Monitoring, Boat Evacuation", status="DEPLOYED", latitude=26.8124, longitude=87.1834, created_by_email="commander@ndma.gov.in")
            ])
            db.commit()

        if db.query(User).filter(User.email == 'commander@ndma.gov.in').first() is None:
            db.add(User(name="Col. Raviranjan Kumar", email="commander@ndma.gov.in", password="admin", role="COMMANDER", agency="National Disaster Operations Command", phone="+91 9876543210"))
            db.commit()

    except Exception as e:
        print(f"[AUTO-SEED NOTICE]: {e}")
        db.rollback()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    auto_seed_if_empty()
    yield

app = FastAPI(
    title="RakshaGrid - Disaster Operations Command Platform",
    version="2.2.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(volunteers.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(zones.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(logistics.router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "status": "ONLINE",
        "system": "RakshaGrid - Disaster Operations Command Platform",
        "endpoints": [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/zones",
            "/api/v1/depots",
            "/api/v1/volunteers",
            "/api/v1/predict/demand/{zone_id}",
            "/api/v1/optimize/allocation"
        ],
        "docs_url": "/docs"
    }
