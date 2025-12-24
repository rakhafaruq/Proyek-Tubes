from sqlalchemy import Column, Integer, String, Float
from database import Base

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String, unique=True, index=True)
    model = Column(String)
    status = Column(String, default="ACTIVE") # ACTIVE / MAINTENANCE
    daily_price = Column(Float, default=0.0)