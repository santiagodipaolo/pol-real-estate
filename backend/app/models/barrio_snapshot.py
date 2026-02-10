from sqlalchemy import Column, BigInteger, Date, Integer, Numeric, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class BarrioSnapshot(Base):
    __tablename__ = "barrio_snapshots"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    barrio_id = Column(Integer, ForeignKey("barrios.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    operation_type = Column(String(20), nullable=False)
    property_type = Column(String(50), nullable=True)
    listing_count = Column(Integer)
    median_price_usd_m2 = Column(Numeric(10, 2))
    avg_price_usd_m2 = Column(Numeric(10, 2))
    p25_price_usd_m2 = Column(Numeric(10, 2))
    p75_price_usd_m2 = Column(Numeric(10, 2))
    avg_days_on_market = Column(Numeric(10, 1))
    new_listings_7d = Column(Integer)
    removed_listings_7d = Column(Integer)
    rental_yield_estimate = Column(Numeric(6, 4))
    usd_blue_rate = Column(Numeric(12, 4))

    barrio = relationship("Barrio", back_populates="snapshots")

    __table_args__ = (
        UniqueConstraint(
            "barrio_id", "snapshot_date", "operation_type", "property_type",
            name="uq_barrio_snapshot"
        ),
    )
