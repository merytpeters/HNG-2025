"""String Analyzers Schema"""

from pydantic import BaseModel
from datetime import datetime
from fastapi import HTTPException, Response, Query
from string_analyzers.string_analyzer import (
    palindrome,
    unique_char,
    word_count,
    sha256_hash,
    character_frequency_map,
)
from typing import List, Dict, Any, Optional
import os
import json
import spacy
import re


class StringAnalyzerCreate(BaseModel):
    value: str


class stringAnalyzerProperties(BaseModel):
    length: int
    is_palindrome: bool
    unique_characters: int
    word_count: int
    sha256_hash: str
    character_frequency_map: dict


class StringAnalyzerOut(BaseModel):
    id: str
    value: str
    properties: stringAnalyzerProperties
    created_at: str


class FilterDataOut(BaseModel):
    data: List[StringAnalyzerOut]
    count: int
    filters_applied: Dict[str, Any]


class InterpretedQuery(BaseModel):
    original: str
    parsed_filters: Dict[str, Any]


class NaturalLanguageFilteringOut(BaseModel):
    data: List[str]
    count: int
    interpreted_query: InterpretedQuery


DB_FILE = "DB.json"


def analyse_data(data: str):
    """Analyse string"""
    if not data:
        raise HTTPException(
            status_code=400, detail="Invalid request body or missing 'value' field"
        )
    data_id = sha256_hash(data)
    length = len(data)
    is_palindrome = palindrome(data)
    unique_characters = unique_char(data)
    wordCount = word_count(data)
    hashValue = sha256_hash(data)
    charfreqMap = character_frequency_map(data)

    properties = stringAnalyzerProperties(
        length=length,
        is_palindrome=is_palindrome,
        unique_characters=unique_characters,
        word_count=wordCount,
        sha256_hash=hashValue,
        character_frequency_map=charfreqMap,
    )

    string_data = StringAnalyzerOut(
        id=data_id,
        value=data,
        properties=properties,
        created_at=datetime.now().isoformat(),
    )
    return string_data


def save_to_db(data: str):
    """Save to db"""
    string_data = analyse_data(data)

    db = {}
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try:
                db = json.load(f)
            except json.JSONDecodeError:
                db = {}
    else:
        db = {}

    if string_data.id in db:
        raise HTTPException(
            status_code=409, detail="String already exists in the system"
        )

    db[string_data.id] = string_data.model_dump()
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

    return string_data


def search_db_for_data(data: str):
    """key search from db"""
    if not data:
        raise HTTPException(
            status_code=400, detail="Invalid request body or missing 'value' field"
        )

    if not os.path.exists(DB_FILE):
        raise HTTPException(
            status_code=404, detail="Database file not found. No data stored yet."
        )

    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="Database file is corrupted or empty."
        )

    data_id = sha256_hash(data)

    if data_id not in db:
        raise HTTPException(
            status_code=404, detail="String does not exist in the system"
        )

    return db[data_id]


def search_db():
    """Global search"""
    if not os.path.exists(DB_FILE):
        raise HTTPException(status_code=500, detail="Database file not found.")

    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="Database file is corrupted or empty."
        )

    return db


def del_from_db(data: str):
    """Delete an entry from the database."""
    if not data:
        raise HTTPException(status_code=400, detail="Missing data to delete")

    db = search_db()
    data_id = sha256_hash(data)

    if data_id not in db:
        raise HTTPException(
            status_code=404, detail="String does not exist in the system"
        )

    del db[data_id]

    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

    return Response(status_code=204)


def filter_by_given_params(
    is_palindrome: Optional[bool] = None,
    min_length: Optional[int] = Query(None, ge=0),
    max_length: Optional[int] = Query(None, ge=0),
    word_count: Optional[int] = None,
    contains_character: Optional[str] = Query(None, max_length=1, min_length=1),
):
    """Filter by given params"""
    results = list(search_db().values())
    filters_applied = {}

    if is_palindrome is not None:
        results = [
            r for r in results if r["properties"]["is_palindrome"] == is_palindrome
        ]
        filters_applied["is_palindrome"] = is_palindrome

    if min_length is not None:
        results = [r for r in results if r["properties"]["length"] >= min_length]
        filters_applied["min_length"] = min_length

    if max_length is not None:
        results = [r for r in results if r["properties"]["length"] <= max_length]
        filters_applied["max_length"] = max_length

    if contains_character is not None:
        results = [
            r for r in results if contains_character.lower() in r["value"].lower()
        ]
        filters_applied["contains_character"] = contains_character

    if word_count is not None:
        results = [r for r in results if r["properties"]["word_count"] == word_count]
        filters_applied["word_count"] = word_count

    return results, filters_applied


try:
    nlp = spacy.load("en_core_web_md")
except OSError:
    print("Model 'en_core_web_md' not found — falling back to 'en_core_web_sm'")
    nlp = spacy.load("en_core_web_sm")


def detect_filter_params(data: str) -> dict[str, Any]:
    """Extract NLP-based filter params from a natural language query."""
    text_lower = data.lower()
    doc = nlp(text_lower)

    params: dict[str, Any] = {
        "word_count": None,
        "is_palindrome": None,
        "contains_character": None,
        "min_length": None,
        "max_length": None,
    }

    if any(t.lemma_ in ("palindrome", "palindromic") for t in doc):
        params["is_palindrome"] = True

    word_map = {
        "single": 1,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }

    for ent in doc.ents:
        if (
            ent.label_ == "CARDINAL"
            and "word" in text_lower[text_lower.find(ent.text) :]
        ):
            try:
                params["word_count"] = int(ent.text)
            except ValueError:
                params["word_count"] = word_map.get(ent.text)

    if params["word_count"] is None:
        match = re.search(
            r"\b(single|one|two|three|four|five|six|seven|eight|nine|ten)\s+word",
            text_lower,
        )
        if match:
            params["word_count"] = word_map[match.group(1)]
        else:
            num_match = re.search(r"(\d+)\s+word", text_lower)
            if num_match:
                params["word_count"] = int(num_match.group(1))

    for token in doc:
        if token.lemma_ in ("long", "lengthy", "more"):
            for child in token.children:
                if child.like_num:
                    params["min_length"] = int(child.text) + 1
        elif token.lemma_ in ("short", "less"):
            for child in token.children:
                if child.like_num:
                    params["max_length"] = int(child.text) - 1

    min_match = re.search(r"(?:longer|more)\s+than\s+(\d+)", text_lower)
    if min_match and not params["min_length"]:
        params["min_length"] = int(min_match.group(1)) + 1

    max_match = re.search(r"(?:shorter|less)\s+than\s+(\d+)", text_lower)
    if max_match and not params["max_length"]:
        params["max_length"] = int(max_match.group(1)) - 1

    char_match = re.search(r"(?:letter|character)\s+([a-z])", text_lower)
    if char_match:
        params["contains_character"] = char_match.group(1)
    else:
        alt_match = re.search(r"(?:containing|contains|with)\s+([a-z])\b", text_lower)
        if alt_match:
            params["contains_character"] = alt_match.group(1)
        elif "first vowel" in text_lower:
            params["contains_character"] = "a"
        elif "first consonant" in text_lower:
            params["contains_character"] = "b"

    return params
