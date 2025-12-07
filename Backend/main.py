"""Main Entry Point"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from medFinder.main import app as medfinder
from AISummarizationExtraction.app import app as ai_documents_app
from AISummarizationExtraction import models as ai_document_models
from myprofile.utils import get_cat_fact
from myprofile.schema import Profile, get_profile
from string_analyzers.schema import (
    StringAnalyzerCreate,
    StringAnalyzerOut,
    FilterDataOut,
    NaturalLanguageFilteringOut,
    InterpretedQuery,
    save_to_db,
    search_db_for_data,
    del_from_db,
    filter_by_given_params,
    detect_filter_params,
)
from typing import Optional
from db import engine, get_session
from sqlmodel import SQLModel, Session, select, func
from sqlalchemy import delete
from country_exchange.schema import (
    Country,
    CountryResponse,
    CountryResponseUUID,
    SummaryOut,
)
from country_exchange.fetch import country_data
from country_exchange.util import generate_image
from datetime import timezone, datetime
from pathlib import Path
import logging
import sys
import os


BASE_DIR = Path(__file__).parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)
logger.propagate = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up: creating database tables...")
    SQLModel.metadata.create_all(engine, checkfirst=True)

    yield
    print("Shutting down...")


app = FastAPI(
    title="HNG Profile API",
    description="Returns user profile and a random cat fact.",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/medfinder", medfinder)
app.mount("/documents", ai_documents_app)


@app.get("/")
def entry_point():
    return {"message": "Welcome to my HNG API endpoint stack"}


@app.get("/health")
def health_check():
    return {"health": "All good, 100%"}


@app.get("/fact")
def get_cat_fact_ninja():
    data = get_cat_fact()
    return data


@app.get("/me")
def me(profile: Profile = Depends(get_profile)):
    if profile is None:
        logger.warning("Profile not found")
        return Profile(
            status="error",
            user={"email": "unknown@example.com", "name": "Unknown", "stack": "None"},
            timestamp=datetime.now(timezone.utc),
            fact="No cat fact available.",
        )
    logger.info("GET /me called successfully")
    return profile


@app.get(
    "/strings/filter-by-natural-language",
    status_code=status.HTTP_200_OK,
    response_model=NaturalLanguageFilteringOut,
)
def nlfiltering(query: str):
    print(f"[DEBUG] Query received: {query}", flush=True)

    response = detect_filter_params(query)
    logger.info(f"NLP Filter Response: {response}")
    print(f"[DEBUG] Parsed response: {response}", flush=True)

    if not any(response.values()):
        raise HTTPException(
            status_code=400, detail="Unable to parse natural language query"
        )

    if (
        response.get("min_length")
        and response.get("max_length")
        and response["min_length"] > response["max_length"]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query parsed but resulted in conflicting filters",
        )

    results, filters_applied = filter_by_given_params(
        is_palindrome=response.get("is_palindrome"),
        min_length=response.get("min_length"),
        max_length=response.get("max_length"),
        word_count=response.get("word_count"),
        contains_character=response.get("contains_character"),
    )
    data = [r["value"] for r in results]
    count = len(data)

    interpreted_query = InterpretedQuery(original=query, parsed_filters=filters_applied)

    nlf_data = NaturalLanguageFilteringOut(
        data=data, count=count, interpreted_query=interpreted_query
    )
    logger.info(f"NLP Filter Response: {nlf_data}")
    print(f"[DEBUG] Final data count: {count}", flush=True)
    return nlf_data


@app.get(
    "/strings/{string_value}",
    status_code=status.HTTP_200_OK,
    response_model=StringAnalyzerOut,
)
def get_string(string_value):
    """get string data"""
    return search_db_for_data(string_value)


@app.post(
    "/strings", status_code=status.HTTP_201_CREATED, response_model=StringAnalyzerOut
)
def post_string(request: StringAnalyzerCreate):
    """post string data"""
    if not isinstance(request.value, str):
        raise HTTPException(
            status_code=422, detail="Invalid data type for 'value' (must be string)"
        )
    return save_to_db(request.value)


@app.get("/strings", status_code=status.HTTP_200_OK, response_model=FilterDataOut)
def filter_string(
    is_palindrome: Optional[bool] = None,
    min_length: Optional[int] = Query(None, ge=0),
    max_length: Optional[int] = Query(None, ge=0),
    word_count: Optional[int] = None,
    contains_character: Optional[str] = Query(None, max_length=1, min_length=1),
):
    """filter string"""

    results, filters_applied = filter_by_given_params(
        is_palindrome=is_palindrome,
        min_length=min_length,
        max_length=max_length,
        word_count=word_count,
        contains_character=contains_character,
    )

    data = list(results)
    count = len(data)

    return {"data": data, "count": count, "filters_applied": filters_applied}


@app.delete("/strings/{string_value}", status_code=status.HTTP_204_NO_CONTENT)
def delete_string(request: StringAnalyzerCreate):
    """Delete string"""
    return del_from_db(request.value)


@app.get("/countries/image", status_code=status.HTTP_200_OK)
def get_image_summary():
    cache_dir = BASE_DIR / "cache"
    file_path = cache_dir / "summary.png"

    print(f"Looking for file at: {file_path}", flush=True)
    if cache_dir.exists():
        print(f"cache dir contents: {list(cache_dir.iterdir())}", flush=True)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No image found"
        )
    print(f"Returning file: {file_path}, exists: {file_path.exists()}", flush=True)
    return FileResponse(str(file_path), media_type="image/png")


@app.delete("/countries/flush")
def flush_countries(db: Session = Depends(get_session)):
    """Delete all countries from the database."""

    total = db.exec(select(func.count()).select_from(Country)).one()

    db.exec(delete(Country))
    db.commit()
    return {"message": f"Deleted {total} countries from database."}


@app.post("/countries/refresh", status_code=status.HTTP_200_OK)
def refresh_country_data_in_db(db: Session = Depends(get_session)):
    countries = country_data()

    if not countries:
        raise HTTPException(status_code=204, detail="No country data to refresh")

    updated_count = 0
    inserted_count = 0
    merged_countries = []

    for new_country in countries:
        existing = db.exec(
            select(Country).where(Country.name == new_country.name)
        ).first()

        if existing:
            existing.capital = new_country.capital
            existing.region = new_country.region
            existing.population = new_country.population
            existing.currency_code = new_country.currency_code
            existing.exchange_rate = new_country.exchange_rate
            existing.estimated_gdp = new_country.estimated_gdp
            existing.flag_url = new_country.flag_url
            existing.last_refreshed_at = datetime.now(timezone.utc)
            updated_count += 1
            merged_countries.append(existing)
        else:
            new_country.last_refreshed_at = datetime.now(timezone.utc)
            db.add(new_country)
            inserted_count += 1
            merged_countries.append(new_country)

    db.commit()

    for c in merged_countries:
        db.refresh(c)

    generate_image(db)

    total_in_db = db.exec(select(func.count()).select_from(Country)).one()

    return {
        "message": "Country data refreshed successfully",
        "updated": updated_count,
        "inserted": inserted_count,
        "total_in_db": total_in_db,
    }


@app.get(
    "/countries",
    status_code=status.HTTP_200_OK,
    response_model=list[CountryResponse],
)
def get_countries(
    name: Optional[str] = Query(None, description="Filter by country name"),
    region: Optional[str] = Query(None, description="Filter by region"),
    capital: Optional[str] = Query(None, description="Filter by capital"),
    currency_code: Optional[str] = Query(None, description="Filter by currency code"),
    population: Optional[float] = Query(None, description="Filter by population"),
    estimated_gdp: Optional[float] = Query(None, description="Filter by estimated GDP"),
    exchange_rate: Optional[float] = Query(None, description="Filter by exchange rate"),
    db: Session = Depends(get_session),
):
    """
    Get countries filtered by any attribute.
    Examples:
      /countries?region=Africa
      /countries?name=Kenya
      /countries?currency_code=USD
    """

    countries = db.exec(select(Country)).all()

    def match(country):
        if name and name.lower() not in (country.name or "").lower():
            return False
        if region and region.lower() not in (country.region or "").lower():
            return False
        if capital and capital.lower() not in (country.capital or "").lower():
            return False
        if (
            currency_code
            and currency_code.lower() not in (country.currency_code or "").lower()
        ):
            return False
        if population and country.population != population:
            return False
        if estimated_gdp and country.estimated_gdp != estimated_gdp:
            return False
        if exchange_rate and country.exchange_rate != exchange_rate:
            return False
        return True

    filtered = [c for c in countries if match(c)]

    if not filtered:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No countries found matching search criteria.",
        )

    response = [
        CountryResponse(
            id=i + 1,
            **{k: getattr(c, k) for k in Country.__fields__ if k != "id"},
        )
        for i, c in enumerate(filtered)
    ]

    return response


@app.get(
    "/countries/{name}",
    status_code=status.HTTP_200_OK,
    response_model=CountryResponseUUID,
)
def get_country_by_name(name: str, db: Session = Depends(get_session)):
    """Get country by name"""
    country = db.exec(select(Country).where(Country.name == name)).first()
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found"
        )

    return country


@app.delete("/countries/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_country_by_name(name: str, db: Session = Depends(get_session)):
    """country by name"""
    country = db.exec(select(Country).where(Country.name == name)).first()

    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found"
        )
    db.delete(country)
    db.commit()
    return


@app.get("/status", status_code=status.HTTP_200_OK, response_model=SummaryOut)
def get_status(db: Session = Depends(get_session)):
    """Get db status"""
    countries = db.exec(select(Country)).all()
    if countries:
        latest_country = max(countries, key=lambda c: c.last_refreshed_at)
        last_refreshed_at = latest_country.last_refreshed_at

    else:
        last_refreshed_at = None

    return {"total_countries": len(countries), "last_refreshed_at": last_refreshed_at}
