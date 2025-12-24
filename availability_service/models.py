from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, index=True) # Referensi ke ID Mobil di Service sebelah
    date = Column(String)     # Format: YYYY-MM-DD
    user_id = Column(String)  # ID User dari Kelompok B
    is_locked = Column(Boolean, default=True)