# packages/parser_engine/hero_parser.py

import json
import re
import math
import pandas as pd

# --- Helper Functions (used by all parsers) ---

def flatten_json(y):
    """ Flattens a nested dictionary and list structure. """
    out = {}
    def flatten(x, name=''):
        if type(x) is dict:
            for a in x: flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else: out[name[:-1]] = x
    flatten(y)
    return out

def generate_description(lang_id: str, lang_params: dict, lang_db: dict) -> dict:
    """Generates a description string by filling a template with parameters."""
    template = lang_db.get(lang_id, {"en": f"NO_TEMPLATE_FOR_{lang_id}", "ja": f"NO_TEMPLATE_FOR_{lang_id}"})
    desc_en, desc_ja = template.get("en", ""), template.get("ja", "")
    for key, value in lang_params.items():
        desc_en = desc_en.replace(f"{{{key}}}", str(value))
        desc_ja = desc_ja.replace(f"{{{key}}}", str(value))
    return {"en": desc_en, "ja": desc_ja}

def format_value(value):
    """Formats numbers for display, removing trailing .0"""
    if isinstance(value, float) and value.is_integer(): return int(value)
    if isinstance(value, float): return f"{value:.1f}"
    return value

# --- Centralized Tooltip Parsing Helper ---
def _find_and_parse_extra_description(
    categories: list, skill_name: str, search_context: dict, main_params: dict,
    lang_db: dict, hero_id: str, rules: dict, parsers: dict
) -> dict:
    if not skill_name or not categories: return {}
    skill_name_lower = skill_name.lower()
    candidates = [key for key in parsers['extra_lang_ids'] if skill_name_lower in key and '.extra' in key]
    extra_lang_id = None
    for key in candidates:
        if any(cat in key for cat in categories):
            extra_lang_id = key
            break
    if extra_lang_id and extra_lang_id in lang_db:
        extra_params = {}
        extra_template_text = lang_db.get(extra_lang_id, {}).get("en", "")
        extra_placeholders = set(re.findall(r'\{(\w+)\}', extra_template_text))
        for p in extra_placeholders:
            if p in main_params: extra_params[p] = main_params[p]
        remaining_placeholders = extra_placeholders - set(extra_params.keys())
        for p_holder in remaining_placeholders:
            value, _ = find_and_calculate_value(
                p_holder, search_context, search_context.get("maxLevel", 8),
                hero_id, rules, is_modifier=False
            )
            if value is not None: extra_params[p_holder] = value
        formatted_extra_params = {k: format_value(v) for k, v in extra_params.items()}
        extra_desc = generate_description(extra_lang_id, formatted_extra_params, lang_db)
        return {
            "lang_id": extra_lang_id,
            "params": json.dumps(extra_params),
            "en": re.sub(r'\[\*\]|\n\s*\n', '\n・', extra_desc.get("en", "")).strip(),
            "ja": re.sub(r'\[\*\]|\n\s*\n', '\n・', extra_desc.get("ja", "")).strip()
        }
    return {}

# --- Core Data Integration Logic ---
def get_full_hero_data(base_data: dict, game_db: dict) -> dict:
    resolved_data = json.loads(json.dumps(base_data))
    processed_ids = set()
    _resolve_recursive(resolved_data, game_db['master_db'], processed_ids)
    return resolved_data

def _resolve_recursive(current_data, master_db, processed_ids):
    if id(current_data) in processed_ids: return
    processed_ids.add(id(current_data))
    ID_KEYS_FOR_LISTS = ['properties','statusEffects','statusEffectsPerHit','summonedFamiliars','effects','passiveSkills','costumeBonusPassiveSkillIds','statusEffectsToAdd','statusEffectCollections']
    if isinstance(current_data, dict):
        for key, value in list(current_data.items()):
            if key.lower().endswith('id') and isinstance(value, str):
                if value in master_db and value not in processed_ids:
                    processed_ids.add(value)
                    new_data = json.loads(json.dumps(master_db[value]))
                    _resolve_recursive(new_data, master_db, processed_ids)
                    current_data[f"{key}_details"] = new_data
            elif key in ID_KEYS_FOR_LISTS and isinstance(value, list):
                _resolve_recursive(value, master_db, processed_ids)
            elif isinstance(value, (dict, list)):
                _resolve_recursive(value, master_db, processed_ids)
    elif isinstance(current_data, list):
        for i, item in enumerate(current_data):
            item_id_to_resolve = item if isinstance(item, str) else (item.get('id') if isinstance(item, dict) else None)
            if item_id_to_resolve and item_id_to_resolve in master_db and item_id_to_resolve not in processed_ids:
                processed_ids.add(item_id_to_resolve)
                new_data = json.loads(json.dumps(master_db[item_id_to_resolve]))
                _resolve_recursive(new_data, master_db, processed_ids)
                if isinstance(current_data[i], str): current_data[i] = new_data
                else: current_data[i].update(new_data)
            elif isinstance(item, (dict, list)):
                 _resolve_recursive(item, master_db, processed_ids)

# --- Core Analysis Tools ---
def get_hero_final_stats(hero_id: str, hero_stats_db: dict) -> dict:
    hero_data = hero_stats_db.get(hero_id)
    if not hero_data: return {"max_attack": 0, "name": "N/A"}
    attack_col = 'Max level: Attack'
    for i in range(4, 0, -1):
        col_name = f'Max level CB{i}: Attack'
        if col_name in hero_data and pd.notna(hero_data[col_name]):
            attack_col = col_name; break
    return {"max_attack": int(hero_data.get(attack_col, 0)), "name": hero_data.get('Name', 'N/A')}

def find_and_calculate_value(p_holder: str, data_block: dict, max_level: int, hero_id: str, rules: dict, is_modifier: bool = False, ignore_keywords: list = None) -> (any, str):
    p_holder_upper = p_holder.upper()
    rule = rules.get("hero_rules", {}).get("specific", {}).get(hero_id, {}).get(p_holder_upper)
    if not rule: rule = rules.get("hero_rules", {}).get("common", {}).get(p_holder_upper)
    if rule:
        if rule.get("calc") == "fixed":
            value_str = rule.get("value")
            try: return int(value_str), "Fixed Rule"
            except (ValueError, TypeError):
                try: return float(value_str), "Fixed Rule"
                except (ValueError, TypeError): return value_str, "Fixed Rule"
        if key_to_find := rule.get("key"):
            flat_data = flatten_json(data_block)
            matching_keys = [k for k in flat_data if k.endswith(key_to_find)]
            if len(matching_keys) == 1:
                found_key = matching_keys[0]; value = flat_data[found_key]
                if isinstance(value, (int, float)):
                    if 'permil' in found_key.lower(): return value / 10, f"Exception Rule: {found_key}"
                    return int(value), f"Exception Rule: {found_key}"
        return None, f"Exception rule key '{key_to_find}' not found or ambiguous"
    if not isinstance(data_block, dict): return None, None
    flat_data = flatten_json(data_block)
    if ignore_keywords:
        keys_to_remove = {k for k in flat_data if any(ik in k.lower() for ik in ignore_keywords)}
        for k in keys_to_remove: del flat_data[k]
    ph_keywords = [s.lower() for s in re.findall('[A-Z][^A-Z]*', p_holder)] or [p_holder.lower()]
    candidates = []
    for key, value in flat_data.items():
        if not isinstance(value, (int, float)): continue
        key_lower = key.lower()
        matched_keywords = sum(1 for kw in ph_keywords if kw in key_lower)
        if matched_keywords > 0:
            score = matched_keywords * 10
            if 'power' in key_lower or 'modifier' in key_lower: score += 5
            if 'permil' in key_lower: score += 3
            candidates.append({'key': key, 'score': score})
    if not candidates: return None, None
    best_candidate = sorted(candidates, key=lambda x: (-x['score'], len(x['key'])))[0]
    found_key = best_candidate['key']; base_val = flat_data.get(found_key, 0)
    inc_key = None
    if found_key.endswith("PerMil"):
        potential_inc_key = found_key.replace("PerMil", "PerLevelPerMil")
        if potential_inc_key in flat_data: inc_key = potential_inc_key
    if not inc_key:
        potential_inc_key = found_key.replace("PerMil", "IncrementPerLevelPerMil")
        if potential_inc_key in flat_data: inc_key = potential_inc_key
    if not inc_key:
        if found_key.islower(): potential_inc_key = found_key + "incrementperlevel"
        else: potential_inc_key = re.sub(r'([a-z])([A-Z])', r'\1IncrementPerLevel\2', found_key)
        if potential_inc_key in flat_data: inc_key = potential_inc_key
    inc_val = flat_data.get(inc_key, 0)
    if not isinstance(inc_val, (int, float)): inc_val = 0
    calculated_val = base_val + inc_val * (max_level - 1)
    if is_modifier or 'modifier' in found_key.lower():
        return ((base_val - 1000) + (inc_val * (max_level - 1))) / 10, found_key
    if 'permil' in found_key.lower(): return calculated_val / 10, found_key
    return int(calculated_val), found_key

def _collect_keywords_recursively(data_block, depth=0, max_depth=3) -> list:
    if depth > max_depth: return []
    keywords = []
    if isinstance(data_block, dict):
        for key, value in data_block.items():
            processed_key = key.lower().replace("id", "").replace("type", "")
            keywords.append((processed_key, depth + 1))
            if isinstance(value, str):
                keywords.append((value.lower(), depth))
            elif isinstance(value, list):
                for item in value:
                    keywords.extend(_collect_keywords_recursively(item, depth + 1, max_depth))
    elif isinstance(data_block, list):
        for item in data_block:
            keywords.extend(_collect_keywords_recursively(item, depth, max_depth))
    return keywords

def find_best_lang_id(data_block: dict, lang_key_subset: list, parsers: dict, parent_block: dict = None) -> (str, str):
    if 'statusEffect' in data_block:
        buff_map = {"MinorDebuff":"minor","MajorDebuff":"major","MinorBuff":"minor","MajorBuff":"major","PermanentDebuff":"permanent","PermanentBuff":"permanent"}
        intensity = buff_map.get(data_block.get('buff'))
        status_effect_val = data_block.get('statusEffect'); effect_name = status_effect_val.lower() if isinstance(status_effect_val, str) else None
        target_from_data = (parent_block or data_block).get('statusTargetType', ''); target = target_from_data.lower() if isinstance(target_from_data, str) else ''
        side_from_data = (parent_block or data_block).get('sideAffected', ''); side = side_from_data.lower() if isinstance(side_from_data, str) else ''
        if all([intensity, effect_name, target, side]):
            constructed_id = f"specials.v2.statuseffect.{intensity}.{effect_name}.{target}.{side}"
            if constructed_id in lang_key_subset: return constructed_id, None
    contextual_block = {**data_block, "parent": parent_block}
    all_keywords_with_depth = _collect_keywords_recursively(contextual_block, depth=0)
    seen_keywords = {}
    for kw, depth in all_keywords_with_depth:
        if kw not in seen_keywords or depth < seen_keywords[kw]: seen_keywords[kw] = depth
    potential_matches = []
    for lang_key in lang_key_subset:
        score = 0; lang_key_parts = lang_key.lower().split('.')
        for kw, depth in seen_keywords.items():
            if kw in lang_key_parts: score += 100 / (2 ** depth)
        familiar_type = data_block.get("familiarType", "").lower()
        if familiar_type:
            if ("minion" in familiar_type and "allies" in lang_key_parts): score += 20
            if ("parasite" in familiar_type and "enemies" in lang_key_parts): score += 20
        if 'fixedpower' in lang_key_parts and 'hasfixedpower' in seen_keywords: score += 3
        if 'decrement' in lang_key_parts and any(isinstance(v, (int, float)) and v < 0 for v in data_block.values()): score += 2
        if score > 0: potential_matches.append({'key': lang_key, 'score': score, 'parts': lang_key_parts})
    if not potential_matches:
        primary_keyword = (data_block.get('propertyType') or data_block.get('statusEffect') or data_block.get('familiarType') or 'N/A')
        return None, f"Could not find lang_id for skill '{data_block.get('id', 'UNKNOWN')}' (type: {primary_keyword})"
    potential_matches.sort(key=lambda x: (-x['score'], len(x['key'])))
    if "familiar_debug_log" in parsers and data_block.get('familiarType'):
        log_entry = {"familiar_id":data_block.get('id'),"familiar_instance":data_block,"top_candidates":[{'score':f"{m['score']:.2f}",'key':m['key']} for m in potential_matches[:5]]}
        parsers["familiar_debug_log"].append(log_entry)
    return potential_matches[0]['key'], None

# --- Main Skill Parsers ---
# Note: The main `parse_*` functions have been moved to the `parsers/` package.
# This file now only contains the core tools and data integration logic.
# The only exception is `parse_direct_effect` which is simple and widely used.

def parse_direct_effect(special_data, hero_stats, lang_db, game_db, hero_id: str, rules: dict, parsers: dict):
    effect_data = special_data.get("directEffect") if isinstance(special_data, dict) else None
    if not effect_data or not effect_data.get("effectType"): return {"id": "direct_effect_no_type", "lang_id": "N/A", "params": "{}", "en": "", "ja": ""}
    try:
        effect_type_str = effect_data.get('effectType', '')
        parts = ["specials.v2.directeffect", effect_type_str.lower()]
        if t := effect_data.get('typeOfTarget'): parts.append(t.lower())
        if s := effect_data.get('sideAffected'): parts.append(s.lower())
        lang_id = ".".join(parts)
        if effect_type_str == "AddMana":
            power_value = effect_data.get('powerMultiplierPerMil', 0)
            if power_value > 0: lang_id += ".increment"
            elif power_value < 0: lang_id += ".decrement"
        if effect_data.get("hasFixedPower"): lang_id += ".fixedpower"
    except AttributeError: return {"id": "direct_effect_error", "lang_id": "N/A", "params": "{}", "en": "Error parsing", "ja": "解析エラー"}
    params = {}
    max_level = special_data.get("maxLevel", parsers.get("main_max_level", 8))
    base = effect_data.get('powerMultiplierPerMil', 0); inc = effect_data.get('powerMultiplierIncrementPerLevelPerMil', 0)
    p_map = {"Damage":"HEALTH","Heal":"HEALTH","HealthBoost":"HEALTHBOOST","AddMana":"MANA"}
    placeholder = p_map.get(effect_type_str, "VALUE")
    total_per_mil = base + inc * (max_level - 1)
    if base > 0 or inc > 0:
        final_val = round(total_per_mil) if effect_data.get("hasFixedPower") else (round(total_per_mil/100) if effect_type_str=="AddMana" else round(total_per_mil/10))
        params[placeholder] = final_val
    elif base < 0 or inc < 0:
        params[placeholder] = abs(round(total_per_mil / 100))
    desc = generate_description(lang_id, params, lang_db)
    return {"lang_id": lang_id, "params": json.dumps(params), **desc}