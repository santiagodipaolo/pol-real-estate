from sqlalchemy import Column, BigInteger, Numeric, String, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class CurrencyRate(Base):
    __tablename__ = "currency_rates"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    rate_type = Column(String(20), nullable=False)
    buy = Column(Numeric(12, 4))
    sell = Column(Numeric(12, 4))
    source = Column(String(50))
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
