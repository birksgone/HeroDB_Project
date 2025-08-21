# hero_main.py (Final Architecture Version)
# This is the main entry point for the Hero Skill Data Processor.

import csv
import json
import traceback
from collections import Counter
from pathlib import Path
import pandas as pd
import re
from pprint import pformat

# --- Import custom modules ---
from hero_data_loader import (
    load_rules_from_csvs, load_languages, load_game_data, load_hero_stats_from_csv,
    DATA_DIR, OUTPUT_DIR, SCRIPT_DIR as LOADER_SCRIPT_DIR, HERO_STATS_CSV_PATTERN
)
# Import core tools from the central parser file
from hero_parser import (
    get_full_hero_data, get_hero_final_stats,
    parse_direct_effect # Direct effect is simple enough to stay here
)
# --- NEW: Import all specialized parsers from the 'parsers' package ---
from parsers.parse_clear_buffs import parse_clear_buffs
from parsers.parse_properties import parse_properties
from parsers.parse_status_effects import parse_status_effects
from parsers.parse_familiars import parse_familiars
from parsers.parse_passive_skills import parse_passive_skills
from parsers.parse_chain_strike import parse_chain_strike

# --- Constants & Paths ---
SCRIPT_DIR = Path(__file__).parent
FINAL_CSV_PATH = SCRIPT_DIR / "hero_skill_output.csv"
DEBUG_CSV_PATH = SCRIPT_DIR / "hero_skill_output_debug.csv"
PARAM_LOG_PATH = SCRIPT_DIR / "familiar_parameter_log.csv" 
DEBUG_JSON_PATH = OUTPUT_DIR / "debug_hero_data.json"
FAMILIAR_LOG_PATH = OUTPUT_DIR / "familiar_debug_log.txt"

# (Output functions _format_final_description, write_final_csv, write_debug_csv, write_debug_json are unchanged from your latest version)
# ...
def _format_final_description(skill_descriptions: dict, lang: str, skill_types_to_include: list, special_data: dict) -> (str, list):
    # (No changes here)
    ...
def write_final_csv(processed_data: list, output_path: Path):
    # (No changes here)
    ...
def write_debug_csv(processed_data: list, output_path: Path):
    # (No changes here)
    ...
def write_debug_json(debug_data: dict, output_path: Path):
    # (No changes here)
    ...

# --- Two-Phase Processing Functions (phase_one is unchanged) ---
def phase_one_integrate_data(game_db: dict, output_path: Path):
    # (No changes here)
    ...

# --- REVISED: The final version of the main parsing orchestrator ---
def phase_two_parse_skills(debug_data: dict, lang_db: dict, game_db: dict, hero_stats_db: dict, rules: dict, parsers: dict) -> list:
    print("\n--- Phase 2: Parsing skills from unified data ---")
    processed_heroes_data = []
    
    parsers['warnings_list'] = []; parsers['unique_warnings_set'] = set()
    parsers['familiar_debug_log'] = []; parsers['familiar_parameter_log'] = []

    def collect_warnings(new_warnings):
        if not new_warnings: return
        for w in new_warnings:
            if w not in parsers['unique_warnings_set']:
                parsers['unique_warnings_set'].add(w); parsers['warnings_list'].append(w)

    for i, (hero_id, full_hero_data) in enumerate(debug_data.items()):
        print(f"\r[{i+1}/{len(debug_data)}] Parsing skills for: {hero_id.ljust(40)}", end="")
        hero_final_stats = get_hero_final_stats(hero_id, hero_stats_db)
        processed_hero = full_hero_data.copy()
        processed_hero['name'] = hero_final_stats.get('name')
        skill_descriptions = {}; special_data_for_hero = None

        if special_data := full_hero_data.get("specialId_details"):
            special_data_for_hero = special_data
            parsers["hero_mana_speed_id"] = full_hero_data.get("manaSpeedId")
            
            # --- The New Orchestration Logic ---
            all_properties = special_data.get("properties", [])
            standard_properties = []
            
            # 1. Pre-processing and delegation loop for special properties
            for prop in all_properties:
                prop_type = prop.get("propertyType")
                if prop_type == "DifferentExtraHitPowerChainStrike":
                    parsed_special, new_warnings = parse_chain_strike(prop, special_data, hero_final_stats, lang_db, game_db, hero_id, rules, parsers)
                    skill_descriptions.setdefault('properties', []).extend(parsed_special)
                    collect_warnings(new_warnings)
                else:
                    standard_properties.append(prop)

            # 2. Parse remaining standard items
            skill_descriptions['directEffect'] = parsers['direct_effect'](special_data, hero_final_stats, lang_db, game_db, hero_id, rules, parsers)
            
            parsed_clear_buffs, new_warnings = parsers['clear_buffs'](special_data, lang_db, parsers)
            skill_descriptions['clear_buffs'] = parsed_clear_buffs; collect_warnings(new_warnings)
            
            parsed_properties, new_warnings = parsers['properties'](standard_properties, special_data, hero_final_stats, lang_db, game_db, hero_id, rules, parsers)
            if 'properties' not in skill_descriptions: skill_descriptions['properties'] = []
            skill_descriptions['properties'].extend(parsed_properties); collect_warnings(new_warnings)

            parsed_status_effects, new_warnings = parsers['status_effects'](special_data.get("statusEffects",[]), special_data, hero_final_stats, lang_db, game_db, hero_id, rules, parsers)
            skill_descriptions['statusEffects'] = parsed_status_effects; collect_warnings(new_warnings)
            
            parsed_familiars, new_warnings = parsers['familiars'](special_data.get("summonedFamiliars",[]), special_data, hero_final_stats, lang_db, game_db, hero_id, rules, parsers)
            skill_descriptions['familiars'] = parsed_familiars; collect_warnings(new_warnings)

        # 3. Parse passives (no change)
        passive_list = full_hero_data.get('passiveSkills', [])
        costume_passive_list = []
        if costume_bonuses := full_hero_data.get('costumeBonusesId_details'):
            if isinstance(costume_bonuses, dict):
                 costume_passive_list = costume_bonuses.get('passiveSkills', [])
        all_passives = passive_list + costume_passive_list
        if all_passives:
            parsed_passives, new_warnings = parsers['passive_skills'](all_passives, hero_final_stats, lang_db, game_db, hero_id, rules, parsers)
            skill_descriptions['passiveSkills'] = parsed_passives; collect_warnings(new_warnings)
        
        processed_hero['_special_data_context'] = special_data_for_hero
        processed_hero['skillDescriptions'] = {k: v for k, v in skill_descriptions.items() if v}
        processed_heroes_data.append(processed_hero)
    
    print("\n--- Phase 2 Complete ---")
    return processed_heroes_data

# (analyze_unresolved_placeholders is unchanged)
# ...
def analyze_unresolved_placeholders(final_hero_data: list):
    # (No changes here)
    ...


def main():
    """Main function to run the entire process."""
    try:
        rules = load_rules_from_csvs(LOADER_SCRIPT_DIR)
        language_db = load_languages()
        game_db = load_game_data()
        hero_stats_db = load_hero_stats_from_csv(DATA_DIR, HERO_STATS_CSV_PATTERN)

        phase_one_integrate_data(game_db, DEBUG_JSON_PATH)

        print("\nReloading unified data from file to ensure consistency...")
        with open(DEBUG_JSON_PATH, 'r', encoding='utf-8') as f:
            debug_data_from_file = json.load(f)

        # --- REVISED: The parsers dict now just holds the functions themselves ---
        parsers = {
            'direct_effect': parse_direct_effect, 
            'clear_buffs': parse_clear_buffs,
            'properties': parse_properties, 
            'status_effects': parse_status_effects, # No longer a lambda
            'familiars': parse_familiars, 
            'passive_skills': parse_passive_skills,
            # Subsets are created inside the parsers now, where they are needed.
            'extra_lang_ids': [key for key in language_db if '.extra' in key]
        }
        
        final_hero_data = phase_two_parse_skills(debug_data_from_file, language_db, game_db, hero_stats_db, rules, parsers)
        
        write_final_csv(final_hero_data, FINAL_CSV_PATH)
        write_debug_csv(final_hero_data, DEBUG_CSV_PATH)
        
        param_log = parsers.get('familiar_parameter_log', [])
        if param_log:
            print(f"\n--- 📝 Writing familiar parameter log... ---")
            try:
                param_df = pd.DataFrame(param_log)
                param_df.to_csv(PARAM_LOG_PATH, index=False, encoding='utf-8-sig')
                print(f"Details saved to {PARAM_LOG_PATH.name}")
            except Exception as e:
                print(f"Warning: Could not write familiar parameter log. Error: {e}")
        
        warnings_list = parsers.get('warnings_list', [])
        if warnings_list:
            unique_warnings = parsers.get('unique_warnings_set', set())
            print(f"\n--- 🚨 Found {len(warnings_list)} lang_id search failures ({len(unique_warnings)} unique types) ---")
        
        analyze_unresolved_placeholders(final_hero_data)
        
        print(f"\n✅ Process complete. All files saved.")

    except Exception as e:
        print(f"\n[FATAL ERROR]: {type(e).__name__} - {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()