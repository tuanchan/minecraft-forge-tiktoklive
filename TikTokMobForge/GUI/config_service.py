from __future__ import annotations

import json
import os
from pathlib import Path


GUI_DIR = Path(__file__).resolve().parent
PROJECT_DIR = GUI_DIR.parent
BRIDGE_DIR = PROJECT_DIR / "bridge"
BRIDGE_CONFIG_PATH = BRIDGE_DIR / "config.json"
DISCOVERED_GIFTS_PATH = BRIDGE_DIR / "discovered_gifts.json"
ENV_PATH = BRIDGE_DIR / ".env"
GUI_STATE_PATH = GUI_DIR / "gui_state.json"

DEFAULT_BRIDGE_CONFIG = {
    "unmapped_gift_mode": "thanks",
    "unmapped_gift_action": "item",
    "unmapped_gift_target": "minecraft:bread",
    "unmapped_gift_amount": 1,
    "unmapped_gift_level": 1,
    "tiktok_username": "_deadchan",
    "likes_per_skeleton": 50,
    "like_mob_type": "skeleton",
    "like_spawn_count": 1,
    "comment_mob_type": "zombie",
    "comment_spawn_count": 1,
    "share_mob_type": "enderman",
    "share_spawn_count": 1,
    "share_limit": 1,
    "share_cooldown_seconds": 10.0,
    "follow_mob_type": "creeper",
    "follow_spawn_count": 1,
    "view_enabled": True,
    "view_mob_type": "zombie",
    "view_spawn_count": 1,
    "view_interval_seconds": 60,
    "view_max_mobs_per_round": 20,
    "comment_limit": 1,
    "comment_cooldown_seconds": 10.0,
    "tts_enabled": True,
    "live_comments_only": False,
    "tts_provider": "elevenlabs",
    "tts_edge_voice": "vi-VN-HoaiMyNeural",
    "tts_edge_rate": 5,
    "tts_edge_pitch": 40,
    "tts_voicevox_url": "http://127.0.0.1:50021",
    "tts_voicevox_speaker_id": 3,
    "tts_voicevox_speed": 1.0,
    "tts_voicevox_pitch": 0.0,
    "tts_voicevox_intonation": 1.0,
    "gift_voicevox_enabled": True,
    "gift_voicevox_volume": 1.0,
    "gift_overlay_enabled": True,
    "gift_overlay_duration_seconds": 5.0,
    "gift_overlay_x": 50,
    "gift_overlay_y": 45,
    "gift_overlay_width": 320,
    "gift_alert_queue_size": 200,
    "gift_phrase_mode": "fixed",
    "gift_phrase_id": "onichan",
    "gift_phrase_custom": "",
    "gift_gif_random": True,
    "gift_gif_file": "kawaiianimegirlGIF.gif",
    "tts_test_text": "",
    "tts_voice_name": "Adam",
    "tts_voice_id": "pNInz6obpgDQGcFmaJgB",
    "tts_model_id": "eleven_flash_v2_5",
    "tts_read_username": True,
    "tts_read_limited_comments": True,
    "tts_volume": 1.0,
    "tts_max_characters": 500,
    "tts_queue_size": 20,
    "tts_keep_latest_comment": True,
    "tts_pause_between_comments_seconds": 1.0,
    "tts_trailing_silence_seconds": 0.3,
    "tts_stability": 0.5,
    "tts_similarity_boost": 0.75,
    "tts_style": 0.0,
    "tts_use_speaker_boost": True,
    "tts_speed": 1.0,
    "tts_language_code": "vi",
    "minecraft_host": "localhost",
    "minecraft_port": 9876,
    "display_comment_enabled": True,
    "display_share_enabled": True,
    "display_like_enabled": True,
    "display_follow_enabled": True,
    "display_view_enabled": True,
    "display_gift_enabled": True,
    "display_unmapped_gifts": True,
    "display_limited_comments": False,
    "display_limited_shares": False,
    "display_comment_text": False,
    "display_comment_max_characters": 80,
}

DEFAULT_MOD_CONFIG = {
    "creeper_break_blocks": False,
    "tnt_break_blocks": True,
    "pinned_board_background": "black",
    "pinned_board_border": "light_blue",
    "pinned_board_author_color": "#ffd99b",
    "pinned_board_comment_color": "#f4f7fb",
    "pinned_board_scale": 1.0,
    "pinned_board_width": 1.0,
    "pinned_board_height": 1.0,
    "pinned_board_text_scale": 1.0,
    "pinned_board_avatar_scale": 1.0,
    "pinned_board_corner_radius": 0.16,
    "pinned_board_avatar_x": 17.0,
    "pinned_board_avatar_y": 50.0,
    "pinned_board_rotation_speed": 1.0,
    "pinned_board_author_x": 17.0,
    "pinned_board_author_y": 82.0,
    "pinned_board_content_x": 66.0,
    "pinned_board_content_y": 60.0,
    "notification_display_modes": {kind: "legacy" for kind in ("like", "comment", "share", "follow", "view", "gift")},
    "notification_positions": {kind: {"x": 50, "y": 40, "scale": 1} for kind in ("like", "comment", "share", "follow", "view", "gift")},
    "bridge_port": 9876,
    "max_pending_events": 1000,
    "max_interactions_per_tick": 5,
    "notification_queue_size": 100,
    "max_mobs_per_user": 4,
    "max_mobs_total": 4,
    "mob_lifetime_seconds": 180.0,
    "golem_teleport_distance": 20.0,
    "wolf_teleport_distance": 20.0,
    "spawn_min_distance": 3.0,
    "spawn_max_distance": 6.0,
    "spawn_height_offset": 0.0,
    "spawn_direction": "front",
    "enderman_targets_player": True,
    "mobs_persistent": True,
    "show_countdown_in_name": True,
    "show_death_counter": True,
    "notification_duration_seconds": 1.5,
    "donation_notification_duration_seconds": 4.0,
    "notification_enabled": True,
    "notification_show_username": True,
    "notification_fade_in_seconds": 0.0,
    "notification_fade_out_seconds": 0.0,
    "notification_gap_seconds": 0.0,
    "notification_title_color": "#55ff55",
    "notification_username_color": "#ffffff",
    "donation_notification_color": "#ffaa00",
    "donation_notification_bold": True,
    "donation_priority_enabled": True,
    "notification_overflow_policy": "drop_newest",
    "effect_duration_seconds": 30.0,
    "absorption_hearts_per_rose": 1.0,
    "money_gun_arrow_count": 32,
    "universe_effect_level": 2,
}

DEFAULT_GIFT_ACTIONS = [
    {"gift_name": "Rose", "gift_id": "", "vietnamese_name": "Hoa Hồng", "coin_value": 1, "action": "special", "target": "absorption", "amount": 1},
    {"gift_name": "TikTok", "gift_id": "", "vietnamese_name": "TikTok", "coin_value": 1, "action": "item", "target": "minecraft:iron_sword", "amount": 1},
    {"gift_name": "Heart Me", "gift_id": "", "vietnamese_name": "Thả Tim", "coin_value": 1, "action": "item", "target": "minecraft:iron_pickaxe", "amount": 1},
    {"gift_name": "GG", "gift_id": "", "vietnamese_name": "GG", "coin_value": 1, "action": "special", "target": "iron_armor", "amount": 1},
    {"gift_name": "Ice Cream Cone", "gift_id": "", "vietnamese_name": "Kem Ốc Quế", "coin_value": 1, "action": "item", "target": "minecraft:arrow", "amount": 16},
    {"gift_name": "Confetti", "gift_id": "", "vietnamese_name": "Pháo Giấy", "coin_value": 100, "action": "item", "target": "minecraft:golden_apple", "amount": 64},
    {"gift_name": "Galaxy", "gift_id": "", "vietnamese_name": "Dải Ngân Hà", "coin_value": 1000, "action": "special", "target": "netherite_armor", "amount": 1},
]
for _common_gift in json.loads((BRIDGE_DIR / "common_gifts.json").read_text(encoding="utf-8")):
    if not any(rule["gift_name"].casefold() == _common_gift["gift_name"].casefold() for rule in DEFAULT_GIFT_ACTIONS):
        DEFAULT_GIFT_ACTIONS.append(_common_gift)



PROFILE_PATH = GUI_DIR / "default_profile.json"
DEFAULT_PROFILE = json.loads(PROFILE_PATH.read_text(encoding="utf-8")) if PROFILE_PATH.is_file() else {}
DEFAULT_BRIDGE_CONFIG.update(DEFAULT_PROFILE.get("bridge", {}))
DEFAULT_MOD_CONFIG.update(DEFAULT_PROFILE.get("mod", {}))
if "gift_actions" in DEFAULT_BRIDGE_CONFIG:
    DEFAULT_GIFT_ACTIONS = DEFAULT_BRIDGE_CONFIG["gift_actions"]


def default_minecraft_dir() -> Path:
    configured = DEFAULT_PROFILE.get("gui", {}).get("minecraft_directory")
    if configured and Path(configured).is_dir():
        return Path(configured)
    curseforge_instance = Path.home() / "curseforge" / "minecraft" / "Instances" / "live stream"
    if curseforge_instance.is_dir():
        return curseforge_instance
    app_data = os.environ.get("APPDATA")
    return Path(app_data) / ".minecraft" if app_data else Path.home() / ".minecraft"


def load_json(path: Path, defaults: dict) -> dict:
    result = dict(defaults)
    if path.is_file():
        with path.open("r", encoding="utf-8-sig") as file:
            loaded = json.load(file)
        if isinstance(loaded, dict):
            result.update(loaded)
    if defaults is DEFAULT_BRIDGE_CONFIG and result.get("tts_provider") == "voicevox":
        result["tts_provider"] = "elevenlabs"
    return result


def load_json_list(path: Path) -> list:
    with path.open("r", encoding="utf-8-sig") as file:
        loaded = json.load(file)
    if not isinstance(loaded, list):
        raise ValueError(f"{path} phải chứa một danh sách JSON")
    return loaded


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temporary_path.replace(path)


def load_gui_state() -> dict:
    return load_json(
        GUI_STATE_PATH,
        {
            **DEFAULT_PROFILE.get("gui", {}),
            "minecraft_directory": str(default_minecraft_dir()),
            "keep_minecraft_running_in_background": DEFAULT_PROFILE.get("gui", {}).get("keep_minecraft_running_in_background", True),
        },
    )


def set_pause_on_lost_focus(minecraft_directory: str | Path, pause: bool) -> Path:
    """Đồng bộ tùy chọn pause của Minecraft mà không thay đổi các dòng khác."""
    options_path = Path(minecraft_directory).expanduser() / "options.txt"
    lines = options_path.read_text(encoding="utf-8-sig").splitlines() if options_path.is_file() else []
    setting = f"pauseOnLostFocus:{str(pause).lower()}"
    replaced = False
    updated: list[str] = []
    for line in lines:
        if line.startswith("pauseOnLostFocus:"):
            if not replaced:
                updated.append(setting)
                replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.append(setting)
    options_path.parent.mkdir(parents=True, exist_ok=True)
    options_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    return options_path


def mod_config_path(minecraft_directory: str | Path) -> Path:
    return Path(minecraft_directory).expanduser() / "config" / "tiktokmob.json"


def load_api_key() -> str:
    if not ENV_PATH.is_file():
        return ""
    for raw_line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if line.startswith("ELEVENLABS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def save_api_key(api_key: str) -> None:
    preserved_lines: list[str] = []
    if ENV_PATH.is_file():
        preserved_lines = [
            line
            for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines()
            if not line.strip().startswith("ELEVENLABS_API_KEY=")
        ]
    preserved_lines.append(f"ELEVENLABS_API_KEY={api_key.strip()}")
    ENV_PATH.write_text("\n".join(preserved_lines) + "\n", encoding="utf-8")
