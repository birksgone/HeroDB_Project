import json
import secrets
import os
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.resolve()))

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Any, List, Dict, Optional

from parser_engine.hero_data_loader import load_languages

# --- Configuration Management ---
dotenv_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=dotenv_path)
API_USERNAME = os.getenv("API_USERNAME", "user")
API_PASSWORD = os.getenv("API_PASSWORD", "password")

# --- Application Setup ---
app = FastAPI(title="HeroDB Parser API", version="1.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- Security Setup ---
security = HTTPBasic()
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    """A dependency that securely checks the username and password."""
    
    print("--- AUTHENTICATION ATTEMPT ---")
    print(f"Username received from browser: '{credentials.username}'")
    print(f"Password received from browser: '{credentials.password}'")
    print(f"Username expected from env:     '{API_USERNAME}'")
    print(f"Password expected from env:     '{API_PASSWORD}'")
    
    correct_username = secrets.compare_digest(credentials.username, API_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, API_PASSWORD)
    
    print(f"User match: {correct_username}, Pass match: {correct_password}")
    print("----------------------------")
    
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
    """
    Recursively searches through a nested data structure to find blocks
    containing a specific key with a matching keyword.
    """
    if isinstance(data, dict):
        # --- DEBUGGING: Print every dictionary it inspects ---
        # print(f"Checking dict: {list(data.keys())}")
        
        if key_to_find in data and isinstance(data[key_to_find], str):
            # --- DEBUGGING: Print every potential match it finds ---
            current_value = data[key_to_find]
            print(f"Found key '{key_to_find}'. Comparing '{keyword.lower()}' with '{current_value.lower()}'")
            
            if keyword.lower() in current_value.lower():
                print(">>> MATCH FOUND! <<<")
                results.append(data)
        
        for value in data.values():
            find_nested_properties(value, key_to_find, keyword, results)
            
    elif isinstance(data, list):
        for item in data:
            find_nested_properties(item, key_to_find, keyword, results)

# --- Protected API Endpoints ---
@app.get("/")
# def read_root(username: str = Depends(get_current_username)):
def read_root():
    return {"message": f"Welcome, {username}!"}

@app.get("/api/heroes")
# def get_all_hero_ids(username: str = Depends(get_current_username)):
def get_all_hero_ids():
    return {"hero_ids": sorted(list(all_hero_data.keys()))}

@app.get("/api/hero/{hero_id}")
# def get_hero_data(hero_id: str, username: str = Depends(get_current_username)):
def get_hero_data(hero_id: str):
    hero_data = all_hero_data.get(hero_id)
    if not hero_data:
        raise HTTPException(status_code=404, detail=f"Hero with ID '{hero_id}' not found.")
    return {"hero_id": hero_id, "data": hero_data}

@app.get("/api/query")
# def query_hero_data(key: str, keyword: str, username: str = Depends(get_current_username)):
def query_hero_data(key: str, keyword: str):
    """
    Searches all heroes for blocks that match a specific key and keyword.
    Can search top-level keys like 'id' or nested keys within skills.
    """
    extracted_data = []
    
    for hero_id, hero_data in all_hero_data.items():
        
        # --- Check top-level keys of the hero data itself ---
        if key in hero_data and isinstance(hero_data[key], str) and keyword.lower() in hero_data[key].lower():
            extracted_data.append({
                "hero_id": hero_id,
                "property_block": hero_data
            })
            continue

        # --- Search within skill details ---
        found_blocks = []
        if special_details := hero_data.get("specialId_details"):
            find_nested_properties(special_details, key, keyword, found_blocks)
        
        if found_blocks:
            for block in found_blocks:
                extracted_data.append({
                    "hero_id": hero_id,
                    "property_block": block
                })
    
    if not extracted_data:
        return {"query": {"key": key, "keyword": keyword}, "count": 0, "results": []}
        
    return {"query": {"key": key, "keyword": keyword}, "count": len(extracted_data), "results": extracted_data}

@app.get("/api/lang/super_search")
def super_search_language_db(
    # id_contains: Optional[str] = Query(None, description="Comma-separated keywords for lang_id"),
    # text_contains: Optional[str] = Query(None, description="Comma-separated keywords for EITHER English OR Japanese text"),
    # username: str = Depends(get_current_username)
    id_contains: Optional[str] = Query(None, description="Comma-separated keywords for lang_id"),
    text_contains: Optional[str] = Query(None, description="Comma-separated keywords for EITHER English OR Japanese text")

):
    """
    Performs a powerful, multi-field, AND-based search on the language database.
    """
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