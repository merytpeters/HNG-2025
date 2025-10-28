"""Fetch data from external API"""

import requests
from fastapi import HTTPException
from .schema import Country, calculate_estimated_gdp
from datetime import datetime, timezone


def country_data():
    """Fetch country data"""
    COUNTRY_URL = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
    RATE_URL = "https://open.er-api.com/v6/latest/USD"

    country_response = requests.get(COUNTRY_URL)
    exchange_rate_response = requests.get(RATE_URL)

    if country_response.status_code != 200:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "External data source unavailable",
                "details": "Could not fetch data from {COUNTRY_URL}",
            },
        )
    if exchange_rate_response.status_code != 200:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "External data source unavailable",
                "details": "Could not fetch data from {RATE_URL}",
            },
        )

    countries = country_response.json()
    exchange_rate_data = exchange_rate_response.json()["rates"]

    all_countries = []
    error_log = []
    for country in countries:
        errors = {}

        name = country.get("name")
        population = country.get("population")
        currencies = country.get("currencies", [])

        if not name:
            errors["name"] = "is required"
        if not population or not isinstance(population, int) or population <= 0:
            errors["population"] = "must be a positive integer"

        currency_code = None
        exchange_rate = None
        estimated_gdp = 0

        if isinstance(currencies, list) and len(currencies) > 0:
            first_currency = currencies[0] or {}
            currency_code = first_currency.get("code")

        if not currency_code:
            errors["currency_code"] = "is required"
        exchange_rate = exchange_rate_data.get(currency_code)
        if exchange_rate is not None:
            estimated_gdp = calculate_estimated_gdp(population, exchange_rate)
        else:
            exchange_rate = None
            estimated_gdp = None

        if errors:
            error_log.append({"country": name, "details": errors})
            print({"error": "Validation failed", "details": errors, "country": name})
            continue

        new_country = Country(
            name=country.get("name"),
            capital=country.get("capital"),
            region=country.get("region"),
            population=population,
            currency_code=currency_code,
            exchange_rate=exchange_rate,
            estimated_gdp=estimated_gdp,
            flag_url=country.get("flag"),
            last_refreshed_at=datetime.now(timezone.utc),
        )

        all_countries.append(new_country)

    return all_countries
