# packages/parser_engine/parsers/parse_chain_strike.py

import json
import re
from hero_parser import (
    find_best_lang_id, 
    _find_and_parse_extra_description,
    generate_description, 
    format_value
)

def parse_chain_strike(prop_data: dict, special_data: dict, hero_stats: dict, lang_db: dict, game_db: dict, hero_id: str, rules: dict, parsers: dict) -> (list, list):
    """
    A specialized, rule-based parser for all 'ChainStrike' type properties.
    It constructs the lang_id from parts and then parses the initial and chain hits.
    """
    parsed_items = []
    warnings = []
    prop_id = prop_data.get("id")
    property_type = prop_data.get("propertyType", "")
    main_max_level = special_data.get("maxLevel", 8)
    search_context = {**prop_data, "maxLevel": main_max_level}
    
    # --- Part 1: Parse the initial hit (if it exists) ---
    # Some chain strikes only have the chain part, not an initial hit.
    if "powerMultiplierPerMil" in prop_data:
        # The initial hit is usually a simple damage property.
        initial_hit_prop_type = prop_data.get("chainEffectType", "Damage")
        
        # We find its lang_id using a generic search, as it's a standard type.
        prop_lang_subset = parsers.get('prop_lang_subset', [k for k in lang_db if k.startswith("specials.v2.property.")])
        initial_hit_lang_id, warning = find_best_lang_id({"propertyType": initial_hit_prop_type}, prop_lang_subset, parsers)
        if warning: warnings.append(f"ChainStrike initial hit warning for {prop_id}: {warning}")
        
        if initial_hit_lang_id:
            lang_params = {}
            base = search_context.get("powerMultiplierPerMil", 0)
            inc = search_context.get("powerMultiplierIncrementPerLevelPerMil", 0)
            val = (base + inc * (main_max_level - 1)) / 10.0
            # Assume placeholder is {HEALTH} for simple damage. A safe bet.
            lang_params["HEALTH"] = val
            
            desc = generate_description(initial_hit_lang_id, {k: format_value(v) for k, v in lang_params.items()}, lang_db)
            parsed_items.append({"id": f"{prop_id}_initial", "lang_id": initial_hit_lang_id, "params": json.dumps(lang_params), **desc})

    # --- Part 2: Construct and parse the chain hit ---
    base_name = property_type.lower()
    modifiers = []
    
    # Rule 1: Determine hit count modifier
    if search_context.get("maxExtraHits") == 1:
        modifiers.append("onehit")
    # (Future rule: elif search_context.get("maxExtraHits") == 3: modifiers.append("threehits"))

    # Rule 2: Determine chance modifier
    if "extraHitChancePerMil" in search_context:
        modifiers.append("with_chance")
        
    # Rule 3: Determine elemental strength modifier
    if color := search_context.get("strongAttackElement"):
        modifiers.append(f"strong_against_{color.lower()}")
    
    # Rule 4: Determine target modifier
    if search_context.get("allowMainTargetInRandomTargets"):
        modifiers.append("allowmaintargetinrandomtargets")

    # Attempt to construct the most specific lang_id
    constructed_lang_id = None
    if modifiers:
        most_specific_key = f"specials.v2.property.{base_name}.{'.'.join(modifiers)}"
        if most_specific_key in lang_db:
            constructed_lang_id = most_specific_key

    # Fallback to a simpler key if the specific one is not found
    if not constructed_lang_id:
        simple_key = f"specials.v2.property.{base_name}"
        if simple_key in lang_db:
            constructed_lang_id = simple_key
    
    chain_lang_id = constructed_lang_id

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
        
        extra_info = _find_and_parse_extra_description(
            categories=["specialproperty", "property"], 
            skill_name=base_name, 
            search_context=search_context, main_params=lang_params, 
            lang_db=lang_db, hero_id=hero_id, rules=rules, parsers=parsers
        )
        
        chain_item = {"id": f"{prop_id}_chain", "lang_id": chain_lang_id, "params": json.dumps(lang_params), **main_desc}
        if extra_info: chain_item["extra"] = extra_info
        parsed_items.append(chain_item)
    else:
        # Only add a warning if an initial hit was also not found
        if not parsed_items:
            warnings.append(f"Could not construct or find any lang_id for ChainStrike property '{prop_id}'")
        
    return parsed_items, warnings