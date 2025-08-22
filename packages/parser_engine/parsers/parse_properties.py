# packages/parser_engine/parsers/parse_properties.py

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
# Import other parsers for recursive calls
from .parse_status_effects import parse_status_effects

def parse_properties(properties_list: list, special_data: dict, hero_stats: dict, lang_db: dict, game_db: dict, hero_id: str, rules: dict, parsers: dict) -> (list, list):
    if not properties_list: return [], []
    parsed_items = []; warnings = []
    main_max_level = special_data.get("maxLevel", 8)
    parsers["main_max_level"] = main_max_level
    prop_lang_subset = parsers.get('prop_lang_subset', [])
    
    for prop_data in properties_list:
        if not isinstance(prop_data, dict): continue
        prop_id = prop_data.get("id")
        property_type = prop_data.get("propertyType", "")

        container_types = {"changing_tides":"RotatingSpecial","charge_ninja":"ChargedSpecial","charge_magic":"ChargedSpecial"}
        if parsers.get("hero_mana_speed_id") in container_types and property_type == container_types[parsers.get("hero_mana_speed_id")]:
            container_lang_ids = {"changing_tides":"specials.v2.property.evolving_special","charge_ninja":"specials.v2.property.chargedspecial.3","charge_magic":"specials.v2.property.chargedspecial.2"}
            container_headings = {"changing_tides":{"en":["1st:","2nd:"],"ja":["第1:","第2:"]},"charge_ninja":{"en":["x1 Mana Charge:","x2 Mana Charge:","x3 Mana Charge:"],"ja":["x1マナチャージ:","x2マナチャージ:","x3マナチャージ:"]},"charge_magic":{"en":["x1 Mana Charge:","x2 Mana Charge:"],"ja":["x1マナチャージ:","x2マナチャージ:"]}}
            container_lang_id = container_lang_ids.get(parsers.get("hero_mana_speed_id"))
            container_desc = generate_description(container_lang_id, {}, lang_db)
            nested_effects = []
            sub_specials_list = prop_data.get("specialIds", [])
            headings = container_headings.get(parsers.get("hero_mana_speed_id"), {})
            for i, sub_special_data in enumerate(sub_specials_list):
                if not isinstance(sub_special_data, dict) or not sub_special_data: continue
                heading_en = headings.get("en", [])[i] if i < len(headings.get("en", [])) else f"Level {i+1}:"
                heading_ja = headings.get("ja", [])[i] if i < len(headings.get("ja", [])) else f"レベル {i+1}:"
                nested_effects.append({"id":"heading","description_en":heading_en,"description_ja":heading_ja})
                if "directEffect" in sub_special_data:
                    nested_effects.append(parsers['direct_effect'](sub_special_data, hero_stats, lang_db, game_db, hero_id, rules, parsers))
                if "properties" in sub_special_data:
                    # Recursive call to self
                    parsed_props, new_warnings = parse_properties(sub_special_data.get("properties",[]), sub_special_data, hero_stats, lang_db, game_db, hero_id, rules, parsers)
                    nested_effects.extend(parsed_props); warnings.extend(new_warnings)
                if "statusEffects" in sub_special_data:
                    parsed_ses, new_warnings = parse_status_effects(sub_special_data.get("statusEffects",[]), sub_special_data, hero_stats, lang_db, game_db, hero_id, rules, parsers)
                    nested_effects.extend(parsed_ses); warnings.extend(new_warnings)
            parsed_items.append({"id":prop_id,"lang_id":container_lang_id,"description_en":container_desc["en"],"description_ja":container_desc["ja"],"params":"{}","nested_effects":nested_effects})
            continue
            
        lang_id = rules.get("lang_overrides",{}).get("specific",{}).get(hero_id,{}).get(prop_id) or rules.get("lang_overrides",{}).get("common",{}).get(prop_id)
        if not lang_id:
            lang_id, warning = find_best_lang_id(prop_data, prop_lang_subset, parsers, parent_block=special_data)
            if warning:
                # Add the source parser's name to the warning
                warnings.append(f"[parse_properties]: {warning}")
        
        if not lang_id:
            failure_text = f"FAIL_LANG_ID: type='{property_type}', id='{prop_id}'"
            parsed_items.append({"id":prop_id, "lang_id":"SEARCH_FAILED", "en":failure_text, "ja":failure_text}); 
            continue
        
        lang_params = {}; search_context = {**prop_data, "maxLevel": main_max_level}
        placeholders = set(re.findall(r'\{(\w+)\}', lang_db.get(lang_id,{}).get("en","")))
        for p_holder in placeholders:
            value, _ = find_and_calculate_value(p_holder, search_context, main_max_level, hero_id, rules, is_modifier='modifier' in property_type.lower())
            if value is not None: lang_params[p_holder] = value
        
        main_desc = generate_description(lang_id, {k:format_value(v) for k,v in lang_params.items()}, lang_db)
        
        nested_effects = []
        if 'statusEffects' in prop_data:
            parsed_ses, new_warnings = parse_status_effects(prop_data['statusEffects'], special_data, hero_stats, lang_db, game_db, hero_id, rules, parsers)
            nested_effects.extend(parsed_ses); warnings.extend(new_warnings)
        
        extra_info = {}
        prop_type_lower = property_type.lower()
        if prop_type_lower in game_db.get('extra_description_keys', set()):
            extra_info = _find_and_parse_extra_description(
                categories=["specialproperty", "property"], skill_name=prop_type_lower, 
                search_context=search_context, main_params=lang_params, 
                lang_db=lang_db, hero_id=hero_id, rules=rules, parsers=parsers
            )
        
        result_item = {"id":prop_id,"lang_id":lang_id,"params":json.dumps(lang_params),"nested_effects":nested_effects,**main_desc}
        if extra_info: result_item["extra"] = extra_info
        parsed_items.append(result_item)
        
    return parsed_items, warnings