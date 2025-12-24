from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ariadne import make_executable_schema, load_schema_from_path, QueryType, MutationType
from ariadne.asgi import GraphQL
from database import engine, Base, SessionLocal
from models import Vehicle, Admin
import auth

# 1. Buat Tabel di Database otomatis saat aplikasi start
Base.metadata.create_all(bind=engine)

# 2. Inisialisasi Tipe GraphQL
type_defs = load_schema_from_path("schema.graphql")
query = QueryType()
mutation = MutationType()

# --- RESOLVER QUERY (READ) ---
@query.field("getAllVehicles")
def resolve_get_all_vehicles(*_):
    session = SessionLocal()
    try:
        return session.query(Vehicle).all()
    finally:
        session.close()

@query.field("getVehicleById")
def resolve_get_vehicle_by_id(*_, id):
    session = SessionLocal()
    try:
        return session.query(Vehicle).filter(Vehicle.id == id).first()
    finally:
        session.close()

# --- RESOLVER MUTATION (WRITE) ---

@mutation.field("login")
def resolve_login(*_, username, password):
    session = SessionLocal()
    try:
        # Cari admin berdasarkan username
        admin = session.query(Admin).filter(Admin.username == username).first()
        
        # --- AUTO CREATE ADMIN (Hanya untuk kemudahan Demo Tugas Besar) ---
        if not admin and username == "admin":
            hashed_pw = auth.get_password_hash("admin123")
            admin = Admin(username="admin", password_hash=hashed_pw)
            session.add(admin)
            session.commit()
            session.refresh(admin)
        # ------------------------------------------------------------------

        # Validasi Password
        if not admin or not auth.verify_password(password, admin.password_hash):
            raise Exception("Login Gagal: Username atau Password Salah")

        # Buat Token
        access_token = auth.create_access_token(data={"sub": admin.username})
        return {"access_token": access_token, "token_type": "bearer"}
    finally:
        session.close()

@mutation.field("addVehicle")
def resolve_add_vehicle(_, info, plateNumber, model, price):
    # --- LOGIC PROTEKSI JWT ---
    request = info.context["request"]
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise Exception("Akses Ditolak: Token tidak ditemukan")
    
    token = auth_header.split(" ")[1]
    payload = auth.decode_access_token(token)
    
    if payload is None:
        raise Exception("Akses Ditolak: Token tidak valid atau kadaluarsa")
    # --------------------------

    # Jika lolos, simpan data mobil
    session = SessionLocal()
    try:
        new_vehicle = Vehicle(plate_number=plateNumber, model=model, daily_price=price)
        session.add(new_vehicle)
        session.commit()
        session.refresh(new_vehicle)
        return new_vehicle
    except Exception as e:
        session.rollback()
        raise Exception(f"Gagal menambah kendaraan: {str(e)}")
    finally:
        session.close()

# 3. Setup Aplikasi FastAPI
schema = make_executable_schema(type_defs, query, mutation)
app = FastAPI(title="Vehicle Service API")

# Setup CORS agar bisa diakses dari browser/client lain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pasang GraphQL di endpoint /graphql
app.mount("/graphql", GraphQL(schema, debug=True))

@app.get("/")
def health_check():
    return {"status": "Vehicle Service Running", "docs": "/graphql"}