import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Ambil URL dari environment variable Docker, atau gunakan default localhost untuk testing manual
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user_vehicle:password123@localhost:5432/db_fleet_vehicle")

# Buat Engine koneksi
engine = create_engine(DATABASE_URL)

# Buat Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class untuk model
Base = declarative_base()

# Helper agar session database otomatis tertutup setelah request selesai
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()