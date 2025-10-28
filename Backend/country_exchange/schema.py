from sqlmodel import Field, SQLModel
from uuid import uuid4, UUID
from typing import Optional, Any
from pydantic import BaseModel
from datetime import datetime, timezone
import random


class BaseSchema(BaseModel):
    class Config:
        json_encoders = {
            datetime: lambda v: (
                v.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                if v
                else None
            )
        }


class Country(SQLModel, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    name: str
    capital: Optional[str]
    region: Optional[str]
    population: int
    currency_code: Optional[str] = None
    exchange_rate: Optional[float] = None
    estimated_gdp: Optional[float] = None
    flag_url: Optional[str]
    last_refreshed_at: datetime


class CountryResponse(BaseSchema):
    id: int
    name: str
    capital: Optional[str]
    region: Optional[str]
    population: int
    currency_code: Optional[str]
    exchange_rate: Optional[float]
    estimated_gdp: Optional[float]
    flag_url: Optional[str]
    last_refreshed_at: datetime


class CountryResponseUUID(BaseSchema):
    id: UUID
    name: str
    capital: Optional[str]
    region: Optional[str]
    population: int
    currency_code: Optional[str]
    exchange_rate: Optional[float]
    estimated_gdp: Optional[float]
    flag_url: Optional[str]
    last_refreshed_at: datetime


class SummaryOut(BaseSchema):
    total_countries: int
    last_refreshed_at: datetime


# estimated_gdp — computed from population × random(1000–2000) ÷ exchange_rate


def calculate_estimated_gdp(population: int, exchange_rate: float):
    """Returns estimated GDP"""
    if exchange_rate == 0:
        raise ValueError("exchange_rate must be non-zero")
    per_capita = random.uniform(1000.0, 2000.0)
    return population * per_capita / exchange_rate
