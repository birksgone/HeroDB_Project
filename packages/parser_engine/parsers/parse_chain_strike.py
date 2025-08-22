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
    """
    parsed_items = []
    warnings = []
    prop_id = prop_data.get("id")
    property_type = prop_data.get("propertyType", "")
    main_max_level = special_data.get("maxLevel", 8)
    search_context = {**prop_data, "maxLevel": main_max_level}
    
    # --- Part 1: Parse the initial hit (if it exists) ---
    if "powerMultiplierPerMil" in prop_data:
        initial_hit_prop_type = prop_data.get("chainEffectType", "Damage")
        prop_lang_subset = parsers.get('prop_lang_subset', [k for k in lang_db if k.startswith("specials.v2.property.")])
        initial_hit_lang_id, warning = find_best_lang_id({"propertyType": initial_hit_prop_type}, prop_lang_subset, parsers)
        if warning: 
            warnings.append(f"[parse_chain_strike]: Initial hit warning for '{prop_id}': {warning}")
        
        if initial_hit_lang_id:
            lang_params = {}
            base = search_context.get("powerMultiplierPerMil", 0)
            inc = search_context.get("powerMultiplierIncrementPerLevelPerMil", 0)
            val = (base + inc * (main_max_level - 1)) / 10.0
            lang_params["HEALTH"] = val
            desc = generate_description(initial_hit_lang_id, {k: format_value(v) for k, v in lang_params.items()}, lang_db)
            parsed_items.append({"id": f"{prop_id}_initial", "lang_id": initial_hit_lang_id, "params": json.dumps(lang_params), **desc})
        else:
            # If initial hit fails, create a failure object
            failure_text = f"FAIL_LANG_ID: ChainStrike Initial Hit '{prop_id}'"
            parsed_items.append({"id": f"{prop_id}_initial", "lang_id": "SEARCH_FAILED", "en": failure_text, "ja": failure_text})
            warnings.append(f"[parse_chain_strike]: Could not determine initial hit lang_id for {prop_id}")


    # --- Part 2: Construct and parse the chain hit ---
    base_name = property_type.lower()
    modifiers = []
    if search_context.get("maxExtraHits") == 1: modifiers.append("onehit")
    if "extraHitChancePerMil" in search_context: modifiers.append("with_chance")
    if color := search_context.get("strongAttackElement"): modifiers.append(f"strong_against_{color.lower()}")
    if search_context.get("allowMainTargetInRandomTargets"): modifiers.append("allowmaintargetinrandomtargets")

    constructed_lang_id = None
    if modifiers:
        most_specific_key = f"specials.v2.property.{base_name}.{'.'.join(modifiers)}"
        if most_specific_key in lang_db:
            constructed_lang_id = most_specific_key

    if not constructed_lang_id:
        simple_key = f"specials.v2.property.{base_name}"
        if simple_key in lang_db:
            constructed_lang_id = simple_key
    
    chain_lang_id = constructed_lang_id

    if chain_lang_id:
        lang_params = {}
        placeholders = set(re.findall(r'\{(\w+)\}', lang_db.get(chain_lang_id,{}).get("en","")))
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
        extra_info = _find_and_parse_extra_description(["specialproperty", "property"], base_name, search_context, main_params=lang_params, lang_db=lang_db, hero_id=hero_id, rules=rules, parsers=parsers)
        chain_item = {"id": f"{prop_id}_chain", "lang_id": chain_lang_id, "params": json.dumps(lang_params), **main_desc}
        if extra_info: chain_item["extra"] = extra_info
        parsed_items.append(chain_item)
    else:
        # If chain hit fails, create a failure object
        failure_text = f"FAIL_LANG_ID: ChainStrike Chain Hit '{prop_id}'"
        parsed_items.append({"id": f"{prop_id}_chain", "lang_id": "SEARCH_FAILED", "en": failure_text, "ja": failure_text})
        warnings.append(f"[parse_chain_strike]: Could not construct or find any lang_id for property '{prop_id}'")
        
    return parsed_items, warnings