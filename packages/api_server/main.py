# packages/api_server/main.py

import json
from pathlib import Path
import sys

# We must add the parent 'packages' directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.resolve()))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, List, Dict, Optional

# Custom module import
from parser_engine.hero_data_loader import load_languages

# --- Application Setup ---
app = FastAPI(
    title="HeroDB Parser API",
    description="An API to serve and query hero data.",
    version="1.3.0" # Version bump for auth removal
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- Path Setup & Data Loading ---
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEBUG_JSON_PATH = PROJECT_ROOT / "data" / "output" / "debug_hero_data.json"
all_hero_data = {}
language_db = {}

@app.on_event("startup")
def load_data():
    global all_hero_data, language_db
    print("--- Loading hero data from JSON... ---")
    if DEBUG_JSON_PATH.exists():
        with open(DEBUG_JSON_PATH, 'r', encoding='utf-8') as f:
            all_hero_data = json.load(f)
        print(f"✅ Successfully loaded data for {len(all_hero_data)} heroes into memory.")
    else:
        print(f"🚨 WARNING: '{DEBUG_JSON_PATH.name}' not found. API will have partial data.")
    print("--- Loading language data... ---")
    try:
        language_db = load_languages()
        print(f"✅ Successfully loaded {len(language_db)} language keys.")
    except Exception as e:
        print(f"🚨 WARNING: Could not load language files. Language API will not work. Error: {e}")

# --- Helper Logic for Querying ---
def find_nested_properties(data: Any, key_to_find: str, keyword: str, results: List[Dict]):
    if isinstance(data, dict):
        if key_to_find in data and isinstance(data[key_to_find], str) and keyword.lower() in data[key_to_find].lower():
            results.append(data)
        for value in data.values():
            find_nested_properties(value, key_to_find, keyword, results)
    elif isinstance(data, list):
        for item in data:
            find_nested_properties(item, key_to_find, keyword, results)

# --- Public API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to the HeroDB Parser API!"}

@app.get("/api/heroes")
def get_all_hero_ids():
    return {"hero_ids": sorted(list(all_hero_data.keys()))}

@app.get("/api/hero/{hero_id}")
def get_hero_data(hero_id: str):
    hero_data = all_hero_data.get(hero_id)
    if not hero_data:
        raise HTTPException(status_code=404, detail=f"Hero with ID '{hero_id}' not found.")
    return {"hero_id": hero_id, "data": hero_data}

@app.get("/api/query")
def query_hero_data(key: str, keyword: str):
    extracted_data = []
    for hero_id, hero_data in all_hero_data.items():
        if key in hero_data and isinstance(hero_data[key], str) and keyword.lower() in hero_data[key].lower():
            extracted_data.append({"hero_id": hero_id, "property_block": hero_data})
            continue
        found_blocks = []
        if special_details := hero_data.get("specialId_details"):
            find_nested_properties(special_details, key, keyword, found_blocks)
        if found_blocks:
            for block in found_blocks:
                extracted_data.append({"hero_id": hero_id, "property_block": block})
    if not extracted_data:
        return {"query": {"key": key, "keyword": keyword}, "count": 0, "results": []}
    return {"query": {"key": key, "keyword": keyword}, "count": len(extracted_data), "results": extracted_data}

@app.get("/api/lang/super_search")
def super_search_language_db(
    id_contains: Optional[str] = Query(None, description="Comma-separated keywords for lang_id"),
    text_contains: Optional[str] = Query(None, description="Comma-separated keywords for EITHER English OR Japanese text")
):
    candidate_keys = list(language_db.keys())
    if id_contains:
        keywords = [k.strip().lower() for k in id_contains.split(',') if k.strip()]
        candidate_keys = [key for key in candidate_keys if all(kw in key.lower() for kw in keywords)]
    if text_contains:
        keywords = [k.strip().lower() for k in text_contains.split(',') if k.strip()]
        candidate_keys = [
            key for key in candidate_keys 
            if all(
                kw in language_db[key].get("en", "").lower() or 
                kw in language_db[key].get("ja", "").lower() 
                for kw in keywords
            )
        ]
    if not candidate_keys:
        raise HTTPException(status_code=404, detail="No language keys found matching all criteria.")
    results = {key: language_db[key] for key in candidate_keys}
    return {"query": {"id": id_contains, "text": text_contains}, "count": len(results), "results": results}