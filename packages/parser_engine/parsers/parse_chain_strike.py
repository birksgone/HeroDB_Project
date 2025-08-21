# packages/parser_engine/parsers/parse_chain_strike.py

import json
import re
from hero_parser import find_best_lang_id, _find_and_parse_extra_description, generate_description, format_value

def parse_chain_strike(prop_data: dict, special_data: dict, hero_stats: dict, lang_db: dict, game_db: dict, hero_id: str, rules: dict, parsers: dict) -> (list, list):
    """
    A specialized parser for the 'DifferentExtraHitPowerChainStrike' property.
    This property is complex as it describes two distinct attacks in one block.
    """
    parsed_items = []
    warnings = []
    prop_id = prop_data.get("id")
    main_max_level = special_data.get("maxLevel", 8)
    search_context = {**prop_data, "maxLevel": main_max_level}
    
    # --- Part 1: Parse the initial hit ---
    # The initial hit is a simple damage property. We create a mock prop_data for it.
    initial_hit_prop = {"propertyType": prop_data.get("chainEffectType", "Damage")}
    prop_lang_subset = parsers.get('prop_lang_subset', [])
    initial_hit_lang_id, warning = find_best_lang_id(initial_hit_prop, prop_lang_subset, parsers)
    if warning: warnings.append(f"ChainStrike initial hit warning for {prop_id}: {warning}")
    
    if initial_hit_lang_id:
        lang_params = {}
        base = search_context.get("powerMultiplierPerMil", 0)
        inc = search_context.get("powerMultiplierIncrementPerLevelPerMil", 0)
        val = (base + inc * (main_max_level - 1)) / 10.0
        # Assume the placeholder is {HEALTH} for simple damage, which is a safe bet for now.
        lang_params["HEALTH"] = val
        
        desc = generate_description(initial_hit_lang_id, {k: format_value(v) for k, v in lang_params.items()}, lang_db)
        parsed_items.append({"id": f"{prop_id}_initial", "lang_id": initial_hit_lang_id, "params": json.dumps(lang_params), **desc})
    else:
        warnings.append(f"Could not determine initial hit lang_id for {prop_id}")

    # --- Part 2: Parse the chain hit ---
    # The chain hit has its own unique lang_id pattern.
    chain_search_key = "differentextrahitpowerchainstrike"
    if "extraHitChancePerMil" in prop_data:
        chain_search_key += ".with_chance"

    chain_candidates = [k for k in prop_lang_subset if chain_search_key in k]
    chain_lang_id, warning = find_best_lang_id(prop_data, chain_candidates, parsers, parent_block=special_data)
    if warning: warnings.append(f"ChainStrike chain hit warning for {prop_id}: {warning}")
    
    if chain_lang_id:
        lang_params = {}
        placeholders = set(re.findall(r'\{(\w+)\}', lang_db.get(chain_lang_id,{}).get("en","")))
        # Manually map placeholders to the correct JSON keys for precision
        for p_holder in placeholders:
            base_val, inc_val, is_permil = 0, 0, False
            if p_holder == "CHANCE":
                base_val = search_context.get("extraHitChancePerMil", 0); is_permil = True
            elif p_holder == "DAMAGE":
                base_val = search_context.get("additionalHitDamagePerMil", 0)
                inc_val = search_context.get("additionalHitDamageIncrementPerLevelPerMil", 0)
                is_permil = True
            
            calculated_val = base_val + inc_val * (main_max_level - 1)
            if is_permil: calculated_val /= 10.0
            lang_params[p_holder] = calculated_val

        main_desc = generate_description(chain_lang_id, {k:format_value(v) for k,v in lang_params.items()}, lang_db)
        
        # Tooltip parsing for the chain hit
        extra_info = _find_and_parse_extra_description(
            categories=["specialproperty", "property"], 
            skill_name="differentextrahitpowerchainstrike", 
            search_context=search_context, main_params=lang_params, 
            lang_db=lang_db, hero_id=hero_id, rules=rules, parsers=parsers
        )
        
        chain_item = {"id": f"{prop_id}_chain", "lang_id": chain_lang_id, "params": json.dumps(lang_params), **main_desc}
        if extra_info: chain_item["extra"] = extra_info
        parsed_items.append(chain_item)
    else:
        warnings.append(f"Could not determine chain hit lang_id for {prop_id}")
        
    return parsed_items, warnings