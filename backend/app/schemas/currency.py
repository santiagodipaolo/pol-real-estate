from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Single rate
# ---------------------------------------------------------------------------

class CurrencyRateResponse(BaseModel):
    """A single currency rate reading."""

    rate_type: str
    buy: Optional[Decimal] = None
    sell: Optional[Decimal] = None
    source: Optional[str] = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# All rates at once
# ---------------------------------------------------------------------------

class CurrencyRatesAll(BaseModel):
    """Latest snapshot of every tracked rate type."""

    blue: Optional[CurrencyRateResponse] = None
    official: Optional[CurrencyRateResponse] = None
    mep: Optional[CurrencyRateResponse] = None
    ccl: Optional[CurrencyRateResponse] = None
    retrieved_at: datetime


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

class CurrencyHistoryPoint(BaseModel):
    """One data-point in a rate's time series."""

    date: date
    buy: Optional[Decimal] = None
    sell: Optional[Decimal] = None


class CurrencyHistory(BaseModel):
    """Full time-series response for a given rate type."""

    rate_type: str
    points: list[CurrencyHistoryPoint]
