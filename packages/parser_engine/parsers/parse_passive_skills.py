# packages/parser_engine/parsers/parse_passive_skills.py

import json
import re
import math
from hero_parser import (
    _collect_keywords_recursively,
    find_and_calculate_value,
    generate_description, 
    format_value
)

def parse_passive_skills(passive_skills_list: list, hero_stats: dict, lang_db: dict, game_db: dict, hero_id: str, rules: dict, parsers: dict) -> (list, list):
    if not passive_skills_list: return [], []
    parsed_items = []; warnings = []
    main_max_level = parsers.get("main_max_level", 8)
    title_lang_subset = [k for k in lang_db if k.startswith("herocard.passive_skill.title.")]
    desc_lang_subset = [k for k in lang_db if k.startswith("herocard.passive_skill.description.")]
    
    for skill_data in passive_skills_list:
        if not isinstance(skill_data, dict): continue
        skill_id = skill_data.get("id"); skill_type = skill_data.get("passiveSkillType","").lower()
        if not (skill_id and skill_type): continue
        
        title_lang_id = None
        prefix = f"herocard.passive_skill.title.{skill_type}"
        title_candidates = [k for k in title_lang_subset if k.startswith(prefix)]
        if title_candidates:
            skill_keywords = {kw for kw, depth in _collect_keywords_recursively(skill_data)}
            title_scores = [{'key':c,'score':sum(1 for kw in skill_keywords if kw in c.split('.'))} for c in title_candidates]
            if title_scores: title_lang_id = sorted(title_scores, key=lambda x:(-x['score'],len(x['key'])))[0]['key']
            
        desc_lang_id = None
        if title_lang_id:
            ideal_desc_id = title_lang_id.replace('.title.','.description.',1)
            if ideal_desc_id in lang_db: desc_lang_id = ideal_desc_id
            else:
                prefix = f"herocard.passive_skill.description.{skill_type}"
                desc_candidates = [k for k in desc_lang_subset if k.startswith(prefix)]
                if desc_candidates:
                    skill_keywords = {kw for kw, depth in _collect_keywords_recursively(skill_data)}
                    refined_candidates = [c for c in desc_candidates if any(kw in c.split('.') for kw in skill_keywords)]
                    if refined_candidates: desc_lang_id = min(refined_candidates, key=len)
                    elif desc_candidates: desc_lang_id = min(desc_candidates, key=len)
                    
        if title_lang_id and desc_lang_id:
            all_placeholders = set(re.findall(r'\{(\w+)\}', lang_db.get(title_lang_id,{}).get("en","") + lang_db.get(desc_lang_id,{}).get("en","")))
            lang_params = {}
            search_context = {**skill_data, "maxLevel": main_max_level}
            for p_holder in all_placeholders:
                value, found_key = find_and_calculate_value(p_holder, search_context, main_max_level, hero_id, rules, is_modifier=False)
                if value is not None:
                    if p_holder.upper() == "DAMAGE" and "permil" in (found_key or "").lower():
                         lang_params[p_holder] = math.floor((value/100) * hero_stats.get("max_attack",0))
                    else: lang_params[p_holder] = value
            
            formatted_params = {k:format_value(v) for k,v in lang_params.items()}
            title_texts = generate_description(title_lang_id, formatted_params, lang_db)
            desc_texts = generate_description(desc_lang_id, formatted_params, lang_db)
            
            parsed_items.append({
                "id": skill_id,
                "title_en": title_texts.get("en",""), "title_ja": title_texts.get("ja",""),
                "description_en": desc_texts.get("en",""), "description_ja": desc_texts.get("ja",""),
                "params": json.dumps(lang_params)
            })
        else:
            warnings.append(f"Could not resolve passive lang_ids for skill '{skill_id}'")
            parsed_items.append({"id":skill_id,"title_en":f"FAILED: {skill_id}","description_en":"lang_id resolution failed."})
            
    return parsed_items, warnings