# packages/tools/extract_learning_data.py

import json
import argparse
from pathlib import Path
import sys

# --- Path Setup ---
# This tool is designed to be run from the project root (HeroDB_Project)
# or from within the tools folder itself.
try:
    # Assumes the script is in .../packages/tools/
    TOOLS_DIR = Path(__file__).parent.resolve()
    PROJECT_ROOT = TOOLS_DIR.parent.parent
except NameError:
    # Fallback for interactive environments
    TOOLS_DIR = Path.cwd()
    PROJECT_ROOT = TOOLS_DIR.parent.parent # Adjust if necessary

# Define the source and destination paths based on the project structure
SOURCE_JSON_PATH = PROJECT_ROOT / "data" / "output" / "debug_hero_data.json"
OUTPUT_DIR = TOOLS_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def find_nested_properties(data, key_to_find, keyword, results):
    """
    Recursively searches through a nested data structure (dicts and lists)
    to find dictionaries containing a specific key and keyword.
    """
    if isinstance(data, dict):
        # Check if the current dictionary matches the criteria
        if key_to_find in data and isinstance(data[key_to_find], str) and keyword.lower() in data[key_to_find].lower():
            results.append(data)
        
        # Continue searching in the values of the current dictionary
        for key, value in data.items():
            find_nested_properties(value, key_to_find, keyword, results)
            
    elif isinstance(data, list):
        # Continue searching in each item of the list
        for item in data:
            find_nested_properties(item, key_to_find, keyword, results)


def main():
    """Main function to run the extraction process."""
    parser = argparse.ArgumentParser(
        description="Extract specific property or effect blocks from debug_hero_data.json for analysis.",
        epilog="Example: python extract_learning_data.py --key propertyType --keyword ChainStrike"
    )
    parser.add_argument("--key", required=True, help="The JSON key to search for (e.g., 'propertyType', 'statusEffect').")
    parser.add_argument("--keyword", required=True, help="The keyword to find within the key's value (case-insensitive).")
    
    args = parser.parse_args()

    print(f"--- Starting Extraction ---")
    print(f"Source file: {SOURCE_JSON_PATH}")
    print(f"Searching for blocks where key='{args.key}' contains keyword='{args.keyword}'...")

    if not SOURCE_JSON_PATH.exists():
        print(f"\n[FATAL ERROR]: Source file not found!")
        print(f"Please make sure '{SOURCE_JSON_PATH.name}' exists in the correct directory.")
        sys.exit(1)

    with open(SOURCE_JSON_PATH, 'r', encoding='utf-8') as f:
        all_hero_data = json.load(f)

    extracted_data = []
    total_heroes = len(all_hero_data)

    for i, (hero_id, hero_data) in enumerate(all_hero_data.items()):
        print(f"\rScanning heroes: [{i+1}/{total_heroes}] {hero_id.ljust(40)}", end="")
        
        found_blocks = []
        # Start the recursive search from the hero's special skill details
        if special_details := hero_data.get("specialId_details"):
            find_nested_properties(special_details, args.key, args.keyword, found_blocks)
        
        if found_blocks:
            for block in found_blocks:
                extracted_data.append({
                    "hero_id": hero_id,
                    "property_block": block
                })
    
    print("\n--- Scan Complete ---")

    if not extracted_data:
        print("No matching blocks were found.")
        return

    output_filename = f"{args.keyword.lower()}_data.json"
    output_path = OUTPUT_DIR / output_filename
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Successfully extracted {len(extracted_data)} blocks.")
        print(f"Result saved to: {output_path}")
    except Exception as e:
        print(f"\n[FATAL ERROR]: Could not write output file. Error: {e}")

if __name__ == "__main__":
    main()

# D:\HeroDB_Projectにいる状態で
# python packages/tools/extract_learning_data.py --key propertyType --keyword ChainStrike