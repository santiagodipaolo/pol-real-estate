import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class ListingPriceHistory(Base):
    __tablename__ = "listing_price_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False, index=True)
    price_usd_blue = Column(Numeric(14, 2))
    price_ars = Column(Numeric(14, 2))
    currency_original = Column(String(3))
    price_original = Column(Numeric(14, 2))
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    source = Column(String(20), nullable=False, server_default="scrape")
