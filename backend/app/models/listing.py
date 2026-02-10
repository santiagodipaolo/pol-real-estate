import uuid

from sqlalchemy import Boolean, Column, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(255), nullable=False)
    source = Column(String(50), nullable=False)
    canonical_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True)
    url = Column(Text)
    title = Column(Text)
    operation_type = Column(String(20), nullable=False)
    property_type = Column(String(50), nullable=False)
    price_original = Column(Numeric(14, 2))
    currency_original = Column(String(3))
    price_usd_blue = Column(Numeric(14, 2))
    price_usd_official = Column(Numeric(14, 2))
    price_usd_mep = Column(Numeric(14, 2))
    price_ars = Column(Numeric(14, 2))
    expenses_ars = Column(Numeric(14, 2))
    surface_total_m2 = Column(Numeric(10, 2))
    surface_covered_m2 = Column(Numeric(10, 2))
    rooms = Column(SmallInteger)
    bedrooms = Column(SmallInteger)
    bathrooms = Column(SmallInteger)
    garages = Column(SmallInteger)
    age_years = Column(SmallInteger)
    amenities = Column(JSONB)
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    barrio_id = Column(Integer, ForeignKey("barrios.id"))
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    is_active = Column(Boolean, default=True)
    days_on_market = Column(Integer)

    barrio = relationship("Barrio", back_populates="listings")
