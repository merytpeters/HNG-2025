"""Main Entry Point"""

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
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
    search_db,
    del_from_db,
    filter_by_given_params,
    detect_filter_params,
)
from typing import Optional
import logging
import sys


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HNG Profile API",
    description="Returns user profile and a random cat fact.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
