"""Utility functions"""

import json
import requests
import os
import random


CACHE_FILE = "cache.json"


def get_cat_fact():
    try:
        response = requests.get("https://catfact.ninja/fact", timeout=5)
        response.raise_for_status()
        data = response.json()
        fact = data["fact"]

        cached_facts = []
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                cached_facts = json.load(f)

        if fact and fact not in cached_facts:
            cached_facts.append(data)
            with open(CACHE_FILE, "w") as f:
                json.dump(cached_facts, f, indent=2)

        return data.get("fact", "No fact found.")
    except requests.RequestException as e:
        random_fact = None
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                cached_facts = json.load(f)
                if cached_facts:
                    random_fact = random.choice(cached_facts)["fact"]
                return {"cached": True, "data": random_fact}
        return {"cached": False, "error": f"Error fetching cat fact: {e}"}
