# packages/parser_engine/parsers/parse_familiars.py

import json
import re
from hero_parser import (
    find_best_lang_id, 
    find_and_calculate_value, 
    _find_and_parse_extra_description,
    generate_description, 
    format_value
)
# We need to import the status_effects parser to delegate tasks to it.
from .parse_status_effects import parse_status_effects

# In parsers/parse_familiars.py

def parse_familiars(familiars_list: list, special_data: dict, hero_stats: dict, lang_db: dict, game_db: dict, hero_id: str, rules: dict, parsers: dict) -> (list, list):
    if not familiars_list: return [], []
    parsed_items = []; warnings = []
    main_max_level = special_data.get("maxLevel", 8)

    for familiar_instance in familiars_list:
        familiar_id = familiar_instance.get("id")
        if not familiar_id: continue
        
        lang_id = None
        familiar_type = familiar_instance.get("familiarType","")
        familiar_type_lower = familiar_type.lower()
        target_type_lower = familiar_instance.get("familiarTargetType", "single").lower()
        if familiar_type_lower and familiar_id:
            potential_patterns = [
                f"specials.v2.{familiar_type_lower}.{familiar_id}.{target_type_lower}",
                f"specials.v2.familiar.{familiar_type_lower}.{familiar_id}.{target_type_lower}",
                f"specials.v2.familiar.{familiar_id}"
            ]
            for pattern in potential_patterns:
                if pattern in lang_db:
                    lang_id = pattern; break
        if not lang_id:
            all_familiar_lang_ids = [k for k in lang_db if k.startswith("specials.v2.familiar.")]
            primary_candidates = [k for k in all_familiar_lang_ids if familiar_id in k]
            lang_id, warning = (find_best_lang_id(familiar_instance, primary_candidates, parsers) if primary_candidates 
                              else find_best_lang_id(familiar_instance, all_familiar_lang_ids, parsers))
            if warning: warnings.append(warning)

        # --- THIS IS THE KEY FIX ---
        if not lang_id:
            warnings.append(f"Could not find summon description for familiar '{familiar_id}'")
            failure_text = f"FAIL_LANG_ID: Familiar '{familiar_id}'"
            parsed_items.append({"id": familiar_id, "lang_id": "SEARCH_FAILED", "en": failure_text, "ja": failure_text})
            continue

        # --- If successful, proceed with parsing ---
        lang_params = {}; search_context = {**familiar_instance, "maxLevel": main_max_level}
        placeholders = set(re.findall(r'\{(\w+)\}', lang_db.get(lang_id,{}).get("en","")))
        health_val = familiar_instance.get('healthPerMil',0); inc_val_health = familiar_instance.get('healthPerLevelPerMil',0)
        lang_params['FAMILIARHEALTHPERCENT'] = (health_val + inc_val_health * (main_max_level - 1)) / 10.0
        attack_found = False
        if effects_for_attack := familiar_instance.get('effects'):
            for effect in effects_for_attack:
                if isinstance(effect,dict) and effect.get('effectType') == 'Damage' and 'attackPercentPerMil' in effect:
                    attack_val = effect.get('attackPercentPerMil',0)
                    inc_val_attack = effect.get('attackPercentIncrementPerLevelPerMil', 0)
                    lang_params['FAMILIARATTACK'] = (attack_val + inc_val_attack * (main_max_level - 1)) / 10.0
                    attack_found = True; break
        for p_holder in placeholders - set(lang_params.keys()):
            value, _ = find_and_calculate_value(p_holder, familiar_instance, main_max_level, hero_id, rules, is_modifier=False, ignore_keywords=['monster'])
            if value is not None: lang_params[p_holder] = value
        main_desc = generate_description(lang_id, {k:format_value(v) for k,v in lang_params.items()}, lang_db)
        
        extra_info = {}
        if familiar_type_lower in game_db.get('extra_description_keys', set()):
            extra_info = _find_and_parse_extra_description(["familiartype"], familiar_type_lower, search_context, lang_params, lang_db, hero_id, rules, parsers)
        
        # 1. Create the parent summon item first
        summon_item = {"id":familiar_id,"lang_id":lang_id,"params":json.dumps(lang_params),**main_desc}
        if extra_info: summon_item["extra"] = extra_info
        
        # 2. Create a list to hold all child effects
        nested_effects = []
        if effects := familiar_instance.get('effects'):
            for effect in effects:
                if not isinstance(effect, dict): continue
                effect_type = effect.get("effectType", "")

                if effect_type == "AddStatusEffects":
                    status_effects_to_add = effect.get("statusEffects", [])
                    if not status_effects_to_add: continue
                    # Parse the effects
                    parsed_effects, new_warnings = parse_status_effects(status_effects_to_add, special_data, hero_stats, lang_db, game_db, hero_id, rules, parsers, search_prefix="familiar.statuseffect.")
                    # Add them to the NESTED list
                    nested_effects.extend(parsed_effects)
                    warnings.extend(new_warnings)
                
                elif effect_type: # e.g., "Damage"
                    # The simple damage text is part of the summon description, so we don't need to parse it again as a separate line.
                    # This could be used for other simple effects in the future.
                    pass
        
        # 3. Attach the nested effects to the parent
        if nested_effects:
            summon_item["nested_effects"] = nested_effects
            
        # 4. Append the single, complete familiar object to the main list
        parsed_items.append(summon_item)

    return parsed_items, warnings


def parse_simple_familiar_effect(effect_data: dict, familiar_instance: dict, lang_db: dict, hero_stats: dict, game_db: dict, hero_id: str, rules: dict, parsers: dict) -> (dict, list):
    """Parses a single, simple familiar effect (like Damage). It's a sub-function for parse_familiars."""
    warnings = []
    main_max_level = parsers.get("main_max_level", 8)
    effect_id = effect_data.get("id")
    if not effect_id: return None, warnings

    context_block = {**familiar_instance, **effect_data}
    effect_type_keyword = effect_data.get('effectType',"").lower()
    
    all_effect_lang_ids = [k for k in lang_db if k.startswith("familiar.effect.")]
    
    primary_candidates = [k for k in all_effect_lang_ids if effect_type_keyword in k]
    lang_id, warning = (find_best_lang_id(context_block, primary_candidates, parsers) if primary_candidates else find_best_lang_id(context_block, all_effect_lang_ids, parsers))
    if warning: warnings.append(warning)
    
    # --- MODIFIED: Return a proper failure object instead of None ---
    if not lang_id:
        failure_text = f"FAIL_LANG_ID: FamiliarEffect '{effect_id}'"
        # Return a dictionary that can be appended to the parsed_items list
        return {"id": effect_id, "lang_id": "SEARCH_FAILED", "en": failure_text, "ja": failure_text}, warnings

    lang_params = {}; search_context = {**context_block, "maxLevel": main_max_level}
    placeholders = set(re.findall(r'\{(\w+)\}', lang_db.get(lang_id,{}).get("en","")))
    for p_holder in placeholders:
        value, _ = find_and_calculate_value(p_holder, context_block, main_max_level, hero_id, rules, is_modifier=False)
        if value is not None: lang_params[p_holder] = value
    if 'FAMILIAREFFECTFREQUENCY' in placeholders and 'turnsBetweenNonDamageEffects' in familiar_instance:
         lang_params['FAMILIAREFFECTFREQUENCY'] = familiar_instance['turnsBetweenNonDamageEffects'] + 1
    
    main_desc = generate_description(lang_id, {k:format_value(v) for k,v in lang_params.items()}, lang_db)
    
    extra_info = {}
    if effect_type_keyword in game_db.get('extra_description_keys', set()):
        extra_info = _find_and_parse_extra_description(["familiareffect"], effect_type_keyword, search_context, lang_params, lang_db, hero_id, rules, parsers)
    
    result_item = {"id":effect_id,"lang_id":lang_id,"params":json.dumps(lang_params),**main_desc}
    if extra_info: result_item["extra"] = extra_info
    
    return result_item, warnings