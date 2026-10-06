"""Per-gift settings shared by live dispatch, tests, and the settings API."""
import json
import math
import re
from pathlib import Path

ENCHANTMENTS = json.loads(Path(__file__).with_name("enchantments.json").read_text(encoding="utf-8"))["enchantments"]
ENCHANTMENT_IDS = {entry["id"] for entry in ENCHANTMENTS}


def enchant_options(rule):
    mode = rule.get("enchant_mode", "full")
    if mode not in {"full", "selected"}:
        raise ValueError("Chế độ phù phép không hợp lệ")
    if mode == "full":
        return {}  # Preserve legacy numeric payloads and saved mappings.
    entries = rule.get("enchantments")
    if not isinstance(entries, list) or not 1 <= len(entries) <= len(ENCHANTMENT_IDS):
        raise ValueError("Hãy chọn ít nhất một loại phù phép")
    result, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("id") not in ENCHANTMENT_IDS:
            raise ValueError("Loại phù phép không có trong Minecraft 26.2")
        identifier, level = entry["id"], entry.get("level", 1)
        if identifier in seen:
            raise ValueError("Mỗi loại phù phép chỉ được chọn một lần")
        if isinstance(level, bool) or not isinstance(level, (int, float)) or not math.isfinite(level) or not 1 <= level <= 255 or int(level) != level:
            raise ValueError("Cấp phù phép phải là số nguyên từ 1 đến 255")
        seen.add(identifier)
        result.append({"id": identifier, "level": int(level)})
    return {"enchant_mode": "selected", "enchantments": result}

FIELDS = {
    "lightning_player": {"strike_count": (5, 1, 2147483647), "interval_seconds": (1, 0, 2147483647 / 20)},
    "troll_pumpkin": {"duration_seconds": (10, 0.1, 3600)},
    "spawn_tnt": {"fuse_seconds": (4, 0, 3600)},
    "troll_anvil": {"distance": (0, 0, 64)},
    "sky_launch": {"height": (96, 1, 2048)},
    "troll_cobweb": {"radius": (0, 0, 16), "duration_seconds": (5, 0.1, 3600)},
}

def explosion_target(rule):
    return rule.get("target") in {"creeper", "minecraft:creeper", "troll_creeper", "spawn_tnt"}


def mob_payload(rule):
    if explosion_target(rule) and "break_blocks" in options_for(rule):
        return json.dumps({"mob": rule["target"], **options_for(rule)}, separators=(",", ":"))
    return rule["target"]


def options_for(rule):
    if rule.get("target") == "mission_penalty":
        mission = rule.get("mission_id", "*")
        points = rule.get("penalty", 1)
        if not isinstance(mission, str) or not re.fullmatch(r"\*|[a-zA-Z0-9_-]{1,48}", mission):
            raise ValueError("Mã nhiệm vụ không hợp lệ")
        if isinstance(points, bool) or not isinstance(points, (int, float)) or not math.isfinite(points) or int(points) != points or not 1 <= points <= 2147483647:
            raise ValueError("Số điểm trừ cần là số nguyên từ 1 đến 2147483647")
        return {"mission_id": mission, "penalty": int(points)}
    if rule.get("target") in {"enchant_armor", "enchant_weapon"}:
        return enchant_options(rule)
    result = {}
    if rule.get("target") == "spawn_tnt":
        damage = rule.get("damage_players", True)
        if not isinstance(damage, bool):
            raise ValueError("damage_players: cần bật hoặc tắt")
        result["damage_players"] = damage
    for key, (default, minimum, maximum) in FIELDS.get(rule.get("target"), {}).items():
        raw = rule.get(key, default)
        if isinstance(raw, bool):
            raise ValueError(f"{key}: cần nhập số")
        value = float(raw)
        if key == "strike_count" and not value.is_integer():
            raise ValueError("Số tia sét phải là số nguyên")
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f"{key}: giá trị phải từ {minimum} đến {maximum}")
        result[key] = value
    if explosion_target(rule) and rule.get("break_blocks") is not None:
        if not isinstance(rule["break_blocks"], bool):
            raise ValueError("break_blocks: cần bật, tắt hoặc theo cài đặt")
        result["break_blocks"] = rule["break_blocks"]
    return result

def reward_payload(rule):
    if rule.get("target") in {"enchant_armor", "enchant_weapon"} and rule.get("enchant_mode", "full") != "full":
        return json.dumps(enchant_options(rule), separators=(",", ":"))
    if rule.get("target") in FIELDS or explosion_target(rule) or rule.get("target") == "mission_penalty":
        return json.dumps(options_for(rule), separators=(",", ":"))
    return str(max(0, min(255, int(rule.get("level", 0 if str(rule.get("target", "")).startswith("enchant_") else 1)))))
