import os
import httpx # Library untuk menembak API lain
from fastapi import FastAPI
from ariadne import make_executable_schema, load_schema_from_path, QueryType, MutationType
from ariadne.asgi import GraphQL
from database import engine, Base, SessionLocal
from models import Schedule

# Buat Tabel
Base.metadata.create_all(bind=engine)

# --- KONFIGURASI URL INTEGRASI ---
# Jika di Docker, pakai nama service. Jika lokal, pakai localhost:8000
VEHICLE_SERVICE_URL = os.getenv("VEHICLE_SERVICE_URL", "http://127.0.0.1:8000/graphql")
# URL Kelompok B (Kita pakai dummy dulu kalau mereka belum siap)
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://kelompok-b-api/graphql")

query = QueryType()
mutation = MutationType()

# --- RESOLVER ---

@query.field("checkAvailability")
def resolve_check_availability(*_, vehicleId, date):
    session = SessionLocal()
    try:
        # Cek di DB lokal kita, ada gak jadwal di tanggal itu?
        existing = session.query(Schedule).filter_by(vehicle_id=vehicleId, date=date).first()
        # Jika existing ada, berarti TIDAK available (False)
        return existing is None 
    finally:
        session.close()

@mutation.field("lockSchedule")
async def resolve_lock_schedule(*_, vehicleId, date, userId):
    # --- LANGKAH 1: INTEGRASI KE VEHICLE SERVICE ---
    # Kita harus tanya: "Eh Service 1, Mobil ID sekian itu ada gak?"
    async with httpx.AsyncClient() as client:
        # Query GraphQL yang mau kita kirim ke Service 1
        query_check_car = {
            "query": f"""
            query {{
                getVehicleById(id: {vehicleId}) {{
                    id
                    model
                    status
                }}
            }}
            """
        }
        
        try:
            response = await client.post(VEHICLE_SERVICE_URL, json=query_check_car)
            result = response.json()
            
            # Cek Error dari API sebelah
            if "data" not in result or result["data"]["getVehicleById"] is None:
                raise Exception(f"Mobil ID {vehicleId} tidak ditemukan di Vehicle Service!")
            
            car_data = result["data"]["getVehicleById"]
            if car_data["status"] != "ACTIVE":
                raise Exception(f"Mobil {car_data['model']} sedang dalam perbaikan (MAINTENANCE).")
                
        except httpx.RequestError:
            raise Exception("Gagal menghubungi Vehicle Service. Pastikan service tersebut nyala.")

    # --- LANGKAH 2: INTEGRASI KE USER SERVICE (KELOMPOK B) ---
    # (Sementara kita skip/pass dulu biar testing lancar, 
    # nanti tinggal uncomment kalau mereka sudah siap)
    # async with httpx.AsyncClient() as client:
    #     ... logic cek reputasi user ...
    
    # --- LANGKAH 3: SIMPAN JADWAL DI DATABASE SENDIRI ---
    session = SessionLocal()
    try:
        # Cek bentrok tanggal
        existing = session.query(Schedule).filter_by(vehicle_id=vehicleId, date=date).first()
        if existing:
            raise Exception("Jadwal pada tanggal tersebut sudah terisi!")

        new_schedule = Schedule(vehicle_id=vehicleId, date=date, user_id=userId)
        session.add(new_schedule)
        session.commit()
        session.refresh(new_schedule)
        return new_schedule
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# Setup App
type_defs = load_schema_from_path("schema.graphql")
schema = make_executable_schema(type_defs, query, mutation)
app = FastAPI(title="Availability Service API")

app.mount("/graphql", GraphQL(schema, debug=True))

@app.get("/")
def health_check():
    return {"status": "Availability Service Running", "docs": "/graphql"}