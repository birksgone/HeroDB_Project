# packages/api_server/main.py

import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from typing import Any, List, Dict, Optional

# --- Custom Module Imports ---
# To reuse our robust data loading logic, we need to add the parser_engine directory to the path
import sys
# Add the parent directory of 'api_server' ('packages') to the system path
sys.path.append(str(Path(__file__).parent.parent.resolve()))
# Now we can import from hero_data_loader
from parser_engine.hero_data_loader import load_languages

# --- Application Setup ---
app = FastAPI(
    title="HeroDB Parser API",
    description="An API to serve and query hero data.",
    version="1.1.0"
)

# --- Path Setup ---
API_SERVER_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = API_SERVER_DIR.parent.parent
DEBUG_JSON_PATH = PROJECT_ROOT / "data" / "output" / "debug_hero_data.json"

# --- Data Loading (In-Memory Database) ---
all_hero_data = {}
language_db = {}

@app.on_event("startup")
def load_data():
    """This function runs once when the FastAPI server starts."""
    global all_hero_data, language_db
    
    # Load hero data
    print("--- Loading hero data from JSON... ---")
    if DEBUG_JSON_PATH.exists():
        with open(DEBUG_JSON_PATH, 'r', encoding='utf-8') as f:
            all_hero_data = json.load(f)
        print(f"✅ Successfully loaded data for {len(all_hero_data)} heroes into memory.")
    else:
        print(f"🚨 WARNING: '{DEBUG_JSON_PATH.name}' not found. API will have partial data.")

    # Load language data
    print("--- Loading language data... ---")
    try:
        # We can reuse the function from our parser engine!
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

# --- API Endpoints ---

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
        found_blocks = []
        if special_details := hero_data.get("specialId_details"):
            find_nested_properties(special_details, key, keyword, found_blocks)
        if found_blocks:
            for block in found_blocks:
                extracted_data.append({"hero_id": hero_id, "property_block": block})
    if not extracted_data:
        raise HTTPException(status_code=404, detail=f"No blocks found matching key='{key}' and keyword='{keyword}'")
    return {"query": {"key": key, "keyword": keyword}, "count": len(extracted_data), "results": extracted_data}

@app.get("/api/lang/super_search")
def super_search_language_db(
    id_contains: Optional[str] = Query(None, description="Comma-separated keywords for lang_id"),
    en_contains: Optional[str] = Query(None, description="Comma-separated keywords for English text"),
    ja_contains: Optional[str] = Query(None, description="Comma-separated keywords for Japanese text")
):
    """
    Performs a powerful, multi-field, AND-based search on the language database.
    """
    candidate_keys = list(language_db.keys())
    
    if id_contains:
        keywords = [k.strip().lower() for k in id_contains.split(',') if k.strip()]
        candidate_keys = [key for key in candidate_keys if all(kw in key.lower() for kw in keywords)]

    if en_contains:
        keywords = [k.strip().lower() for k in en_contains.split(',') if k.strip()]
        candidate_keys = [key for key in candidate_keys if all(kw in language_db[key].get("en", "").lower() for kw in keywords)]

    if ja_contains:
        keywords = [k.strip().lower() for k in ja_contains.split(',') if k.strip()]
        candidate_keys = [key for key in candidate_keys if all(kw in language_db[key].get("ja", "").lower() for kw in keywords)]
        
    if not candidate_keys:
        raise HTTPException(status_code=404, detail="No language keys found matching all criteria.")
        
    results = {key: language_db[key] for key in candidate_keys}
    return {"query": {"id": id_contains, "en": en_contains, "ja": ja_contains}, "count": len(results), "results": results}