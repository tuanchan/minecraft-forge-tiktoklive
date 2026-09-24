"""Snapshot the user's BAT configuration as installer defaults, without credentials."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def public_settings(value):
    if isinstance(value, dict):
        return {key: public_settings(item) for key, item in value.items()
                if not any(word in key.lower() for word in ("api_key", "apikey", "password", "secret", "token", "cookie"))}
    if isinstance(value, list):
        return [public_settings(item) for item in value]
    return value


gui = read(ROOT / "GUI/gui_state.json")
bridge = read(ROOT / "bridge/config.json")
mod = read(Path(gui["minecraft_directory"]) / "config/tiktokmob.json")
bridge.pop("runtime_settings_path", None)
profile = public_settings({"gui": gui, "bridge": bridge, "mod": mod})
destination = ROOT / "GUI/default_profile.json"
destination.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Default profile: {len(bridge.get('gift_actions', []))} gift mappings; bridge, GUI and mod settings exported.")
