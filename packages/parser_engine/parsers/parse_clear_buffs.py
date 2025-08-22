# packages/parser_engine/parsers/parse_clear_buffs.py

from hero_parser import generate_description

def parse_clear_buffs(special_data: dict, lang_db: dict, parsers: dict) -> (dict, list):
    """
    Parses buff removal effects defined at the top level of a special.
    Returns a tuple of (result_dict, warnings_list).
    """
    if "buffToRemove" not in special_data:
        return None, []
    
    warnings = []
    try:
        buff_to_remove = special_data.get("buffToRemove", "").lower()
        target_type = special_data.get("buffToRemoveTargetType", "all").lower()
        
        side_affected = ""
        if "debuff" in buff_to_remove: side_affected = "allies"
        elif "buff" in buff_to_remove: side_affected = "enemies"

        if not side_affected: side_affected = special_data.get("buffToRemoveSideAffected", "").lower()
        if not side_affected: side_affected = special_data.get("sideAffected", "").lower()
        if not side_affected: side_affected = special_data.get("directEffect", {}).get("sideAffected", "").lower()
        if not side_affected: side_affected = "allies" if "debuff" in buff_to_remove else "enemies"

        lang_id = f"specials.v2.clearbuffs.{buff_to_remove}.{target_type}.{side_affected}"
        
        found_in_db = True
        if lang_id not in lang_db:
            if lang_id + ".latest" in lang_db:
                lang_id += ".latest"
            else:
                found_in_db = False

        if not found_in_db:
            warning_msg = f"[parse_clear_buffs]: lang_id '{lang_id}' not found in lang_db."
            warnings.append(warning_msg)
            # Return a standardized failure object
            return {"id": "clear_buffs_effect", "lang_id": "SEARCH_FAILED", "en": warning_msg, "ja": warning_msg}, warnings

        description = generate_description(lang_id, {}, lang_db)
        
        result = {
            "id": "clear_buffs_effect",
            "lang_id": lang_id,
            "params": "{}",
            "nested_effects": [],
            **description
        }
        return result, warnings

    except Exception as e:
        warnings.append(f"Error parsing clear_buffs for '{special_data.get('id', 'Unknown Special')}': {e}")
        return None, warnings