# packages/api_server/main.py

import json
import secrets
from pathlib import Path
import sys

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic_settings import BaseSettings
from typing import Any, List, Dict, Optional

# --- Custom Module Imports ---
# To reuse our robust data loading logic, we need to add the parser_engine directory to the path
sys.path.append(str(Path(__file__).parent.parent.resolve()))
from parser_engine.hero_data_loader import load_languages

# --- Configuration Management ---
# This class will automatically read variables from a .env file or environment variables.
class Settings(BaseSettings):
    API_USERNAME: str = "user"
    API_PASSWORD: str = "password"

    class Config:
        env_file = ".env"

settings = Settings()

# --- Application Setup ---
app = FastAPI(
    title="HeroDB Parser API",
    description="An API to serve and query hero data.",
    version="1.1.0"
)

# --- Security Setup ---
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """A dependency that securely checks the username and password."""
    correct_username = secrets.compare_digest(credentials.username, settings.API_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.API_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- Path Setup & Data Loading ---
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
DEBUG_JSON_PATH = PROJECT_ROOT / "data" / "output" / "debug_hero_data.json"
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

# --- Protected API Endpoints ---
# Add `username: str = Depends(get_current_username)` to protect an endpoint.

@app.get("/")
def read_root(username: str = Depends(get_current_username)):
    return {"message": f"Welcome, {username}!"}

@app.get("/api/heroes")
def get_all_hero_ids(username: str = Depends(get_current_username)):
    return {"hero_ids": sorted(list(all_hero_data.keys()))}

@app.get("/api/hero/{hero_id}")
def get_hero_data(hero_id: str, username: str = Depends(get_current_username)):
    hero_data = all_hero_data.get(hero_id)
    if not hero_data:
        raise HTTPException(status_code=404, detail=f"Hero with ID '{hero_id}' not found.")
    return {"hero_id": hero_id, "data": hero_data}

@app.get("/api/query")
def query_hero_data(key: str, keyword: str, username: str = Depends(get_current_username)):
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
    ja_contains: Optional[str] = Query(None, description="Comma-separated keywords for Japanese text"),
    username: str = Depends(get_current_username)
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