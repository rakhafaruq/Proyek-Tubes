import os
import httpx # Library untuk menembak API lain
from fastapi import FastAPI
from ariadne import make_executable_schema, load_schema_from_path, QueryType, MutationType, snake_case_fallback_resolvers
from ariadne.asgi import GraphQL
from database import engine, Base, SessionLocal
from models import Schedule

# Buat Tabel
Base.metadata.create_all(bind=engine)

# --- KONFIGURASI URL INTEGRASI ---
# Jika di Docker, pakai nama service. Jika lokal, pakai localhost:8000
VEHICLE_SERVICE_URL = os.getenv("VEHICLE_SERVICE_URL", "http://vehicle-service:8000/graphql/")
# URL Kelompok B (Kita pakai dummy dulu kalau mereka belum siap)
USER_SERVICE_URL = os.getenv("EXTERNAL_USER_URL", "https://nonchallenging-amira-cercarial.ngrok-free.dev/graphql/")

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
        if existing:
            return "BOOKED"
        else:
            return "AVAILABLE"
    finally:
        session.close()

@query.field("getAllSchedules")
def resolve_get_all_schedules(*_):
    session = SessionLocal()
    try:
        # Mengambil semua data dari tabel schedules
        return session.query(Schedule).all()
    finally:
        session.close()

@mutation.field("lockSchedule")
async def resolve_lock_schedule(*_, vehicleId, date, userId):
    
    # === LANGKAH 1: VALIDASI MOBIL (KE VEHICLE SERVICE) ===
    async with httpx.AsyncClient() as client:
        query_check_car = {
            "query": """
            query($vid: ID!) {
                getVehicleById(id: $vid) {
                    id
                    model
                    status
                }
            }
            """,
            "variables": {"vid": str(vehicleId)}
        }
        
        try:
            response = await client.post(VEHICLE_SERVICE_URL, json=query_check_car, timeout=10.0)
            if response.status_code != 200:
                raise Exception(f"Vehicle Service Error: {response.status_code}")
            
            result = response.json()
            data = result.get("data", {})
            
            if not data or data.get("getVehicleById") is None:
                raise Exception(f"Mobil ID {vehicleId} tidak ditemukan!")
            
            if data["getVehicleById"]["status"] != "ACTIVE":
                raise Exception(f"Mobil sedang MAINTENANCE.")
                
        except httpx.RequestError:
            raise Exception("Gagal menghubungi Vehicle Service.")


    # === LANGKAH 2: VALIDASI USER & REPUTASI (SESUAI SCHEMA BARU) ===
    async with httpx.AsyncClient() as client:
        # UPDATED: Menggunakan query 'checkUserReputation' milik Kelompok Sebelah
        query_check_reputation = {
            "query": """
            query($uid: ID!) {
                checkUserReputation(userId: $uid) {
                    score
                    isBlacklisted
                }
            }
            """,
            "variables": {"uid": str(userId)}
        }

        try:
            # 1. Tembak API User
            response = await client.post(USER_SERVICE_URL, json=query_check_reputation, timeout=15.0)

            if response.status_code != 200:
                raise Exception(f"Gagal Validasi User: Server Kelompok B Error ({response.status_code})")

            # 2. Cek Data
            result = response.json()
            data = result.get("data", {})
            
            # Jika 'checkUserReputation' null -> Artinya User ID mungkin tidak ada di DB mereka
            if not data or data.get("checkUserReputation") is None:
                raise Exception(f"Booking Ditolak: User ID {userId} TIDAK VALID atau tidak ditemukan di User Service!")
            
            reputation = data["checkUserReputation"]

            # 3. Cek Blacklist (Boolean)
            if reputation.get("isBlacklisted") is True:
                raise Exception(f"Booking Ditolak: User ini masuk daftar BLACKLIST! (Skor: {reputation.get('score')})")

        except httpx.RequestError:
            raise Exception("Booking Gagal: Tidak dapat menghubungi User Service (Server Offline/Link Mati).")


    # === LANGKAH 3: SIMPAN JADWAL ===
    session = SessionLocal()
    try:
        existing = session.query(Schedule).filter_by(vehicle_id=vehicleId, date=date).first()
        if existing:
            raise Exception("Gagal: Mobil sudah dipesan orang lain pada tanggal ini!")

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
schema = make_executable_schema(type_defs, query, mutation, snake_case_fallback_resolvers)
app = FastAPI(title="Availability Service API")

app.mount("/graphql", GraphQL(schema, debug=True))

@app.get("/")
def health_check():
    return {"status": "Availability Service Running", "docs": "/graphql"}