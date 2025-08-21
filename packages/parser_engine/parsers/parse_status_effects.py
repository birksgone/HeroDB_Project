# packages/parser_engine/parsers/parse_status_effects.py

import json
import re
import math
from hero_parser import (
    find_best_lang_id, 
    find_and_calculate_value, 
    _find_and_parse_extra_description,
    generate_description, 
    format_value
)

def parse_status_effects(status_effects_list: list, special_data: dict, hero_stats: dict, lang_db: dict, game_db: dict, hero_id: str, rules: dict, parsers: dict, search_prefix: str = "specials.v2.statuseffect.") -> (list, list):
    if not status_effects_list: return [], []
    parsed_items = []; warnings = []
    main_max_level = special_data.get("maxLevel", 8)
    
    se_lang_subset = [k for k in lang_db if k.startswith(search_prefix)]

    for effect_instance in status_effects_list:
        if not isinstance(effect_instance, dict): continue
        effect_id = effect_instance.get("id"); combined_details = effect_instance
        if not effect_id: continue
        
        lang_id = rules.get("lang_overrides",{}).get("specific",{}).get(hero_id,{}).get(effect_id) or rules.get("lang_overrides",{}).get("common",{}).get(effect_id)
        if not lang_id:
            lang_id, warning = find_best_lang_id(combined_details, se_lang_subset, parsers, parent_block=special_data)
            if warning: warnings.append(warning)
        if not lang_id:
            # Create a standardized failure object.
            failure_text = f"FAIL_LANG_ID: type='{property_type}', id='{prop_id}'"
            parsed_items.append({"id":prop_id, "lang_id":"SEARCH_FAILED", "en":failure_text, "ja":failure_text}); 
            continue
            
        lang_params = {}; search_context = {**combined_details, "maxLevel": main_max_level}
        if (turns := combined_details.get("turns", 0)) > 0: lang_params["TURNS"] = turns
        template_text = lang_db.get(lang_id,{}).get("en","")
        placeholders = set(re.findall(r'\{(\w+)\}', template_text))
        
        for p_holder in placeholders:
            if p_holder in lang_params: continue
            value, found_key = find_and_calculate_value(p_holder, search_context, main_max_level, hero_id, rules, is_modifier='modifier' in combined_details.get('statusEffect','').lower())
            if value is not None:
                if p_holder.upper() == "DAMAGE" and "permil" in (found_key or "").lower():
                    turns_for_calc = combined_details.get("turns",0)
                    damage_per_turn = math.floor((value/100) * hero_stats.get("max_attack",0))
                    lang_params[p_holder] = damage_per_turn * (turns_for_calc or 1) if "over {TURNS} turns" in template_text else damage_per_turn
                else: lang_params[p_holder] = value
                
        main_desc = generate_description(lang_id, {k:format_value(v) for k,v in lang_params.items()}, lang_db)
        
        nested_effects = []
        if 'statusEffectsToAdd' in combined_details:
             parsed_nested_ses, new_warnings = parse_status_effects(combined_details['statusEffectsToAdd'], special_data, hero_stats, lang_db, game_db, hero_id, rules, parsers, search_prefix=search_prefix)
             nested_effects.extend(parsed_nested_ses); warnings.extend(new_warnings)
             
        status_effect_type = combined_details.get("statusEffect","")
        extra_info = {}
        status_effect_lower = status_effect_type.lower()
        if status_effect_lower in game_db.get('extra_description_keys', set()):
             extra_info = _find_and_parse_extra_description(
                 categories=["statuseffect"], skill_name=status_effect_lower,
                 search_context=search_context, main_params=lang_params, 
                 lang_db=lang_db, hero_id=hero_id, rules=rules, parsers=parsers
            )
            
        result_item = {"id":effect_id,"lang_id":lang_id,"params":json.dumps(lang_params),"nested_effects":nested_effects,**main_desc}
        if extra_info: result_item["extra"] = extra_info
        parsed_items.append(result_item)
        
    return parsed_items, warnings