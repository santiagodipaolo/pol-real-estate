from sqlalchemy import Column, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class Barrio(Base):
    __tablename__ = "barrios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    comuna_id = Column(Integer, nullable=False)
    comuna_name = Column(String(50))
    geometry = Column(JSONB)  # GeoJSON geometry stored as JSONB
    area_km2 = Column(Numeric(10, 4))
    centroid_lat = Column(Numeric(10, 7))
    centroid_lon = Column(Numeric(10, 7))

    listings = relationship("Listing", back_populates="barrio")
    snapshots = relationship("BarrioSnapshot", back_populates="barrio")
