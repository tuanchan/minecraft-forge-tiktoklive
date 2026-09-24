from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import base64
import binascii
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.error
import urllib.request
import webbrowser
import zipfile


WEB_DIR = Path(__file__).resolve().parent
PROJECT_DIR = WEB_DIR.parent
GUI_DIR = PROJECT_DIR / "GUI"
BRIDGE_DIR = PROJECT_DIR / "bridge"
# Gift tests use the same Pillow/audio dependencies as the LIVE bridge.
if __name__ == "__main__":
    bridge_python = BRIDGE_DIR / ".venv" / "Scripts" / "pythonw.exe"
    if bridge_python.is_file() and Path(sys.prefix).resolve() != (BRIDGE_DIR / ".venv").resolve():
        subprocess.Popen([str(bridge_python), str(Path(__file__).resolve()), *sys.argv[1:]])
        raise SystemExit(0)
CUSTOM_ASSET_DIR = WEB_DIR / "assets" / "custom"
GUI_INSTANCE = hashlib.sha256((str(PROJECT_DIR).casefold() + "-troll-rewards-v1" + ("-desktop-v3-inventory" if "--desktop" in sys.argv else "")).encode()).hexdigest()
GUI_PORT = 49152 + int(GUI_INSTANCE[:8], 16) % 10000
GIFT_ASSET_INDEX = WEB_DIR / "assets" / "imagegift" / "gifts.json"
sys.path.insert(0, str(GUI_DIR))
sys.path.insert(0, str(BRIDGE_DIR))

from test_runner import TestRunner  # noqa: E402
from minecraft_window import minecraft_viewport
import voicevox_tts
import gift_media
import gift_catalog_service
from bridge import normalize_gift_name
from runtime_settings import EVENT_KEYS, MOD_KEYS, config_file_lock
from vietnamese_tts import VOICES as VIETNAMESE_VOICES

from catalog_service import SPECIAL_REWARDS, _candidate_asset_directories, load_minecraft_catalog  # noqa: E402
from config_service import (  # noqa: E402
    BRIDGE_CONFIG_PATH,
    DEFAULT_BRIDGE_CONFIG,
    DEFAULT_GIFT_ACTIONS,
    DEFAULT_MOD_CONFIG,
    DISCOVERED_GIFTS_PATH,
    GUI_STATE_PATH,
    load_api_key,
    load_gui_state,
    load_json,
    load_json_list,
    mod_config_path,
    save_api_key,
    save_json,
    set_pause_on_lost_focus,
)


class Controller:
    def __init__(self) -> None:
        self.live_process: subprocess.Popen[str] | None = None
        self.processes: set[subprocess.Popen[str]] = set()
        self.logs: list[str] = []
        self.log_sequence = 0
        self.lock = threading.Lock()
        self.config_lock = threading.Lock()
        self.test_runner = TestRunner(self.log)
        self.gift_updater = gift_catalog_service.GiftCatalogUpdater(self.log)
        self._jar_cache: dict[str, Path | None] = {}
        self._catalog_cache: dict[str, tuple[tuple, list, list]] = {}

    def log(self, level: str, message: str) -> None:
        line = f"[{datetime.now():%H:%M:%S}] [{level}] {message}"
        with self.lock:
            self.logs.append(line)
            self.log_sequence += 1
            self.logs = self.logs[-1000:]

    def state(self) -> dict:
        gui = load_gui_state()
        directory = str(gui["minecraft_directory"])
        runtime = self.runtime_state(directory)
        bridge = load_json(BRIDGE_CONFIG_PATH, DEFAULT_BRIDGE_CONFIG)
        bridge.update(runtime["bridge"])
        bridge.setdefault("gift_actions", [dict(item) for item in DEFAULT_GIFT_ACTIONS])
        # Old slot-only images cannot identify which mob they depict.
        # Keep files on disk, but only display explicitly bound artwork.
        bindings = bridge.get("event_image_targets") or {}
        bridge["event_images"] = {
            slot: url for slot, url in (bridge.get("event_images") or {}).items()
            if bindings.get(slot)
        }
        mod = load_json(mod_config_path(directory), DEFAULT_MOD_CONFIG)
        gifts = gift_catalog_service.catalog()
        mobs, items = self.minecraft_catalog(directory)
        return {
            "bridge": bridge,
            "mod": mod,
            "gui": gui,
            "api_key": load_api_key(),
            "gifts": gifts,
            "catalog": {
                "special": [asdict(item) for item in SPECIAL_REWARDS],
                "mobs": [asdict(item) for item in mobs],
                "items": [asdict(item) for item in items],
            },
            "live_running": self.is_live_running(),
            "minecraft_viewport": minecraft_viewport(),
        }

    def minecraft_catalog(self, directory: str) -> tuple[list, list]:
        mods_directory = Path(directory) / "mods"
        signature: tuple = tuple()
        try:
            signature = tuple(sorted(
                (path.name, path.stat().st_mtime_ns, path.stat().st_size)
                for path in mods_directory.glob("*.jar")
                if path.is_file()
            ))
        except OSError:
            pass
        cached = self._catalog_cache.get(directory)
        if cached and cached[0] == signature:
            return cached[1], cached[2]
        mobs, items = load_minecraft_catalog(directory)
        self._catalog_cache[directory] = (signature, mobs, items)
        return mobs, items

    @staticmethod
    def _number(value, label: str, minimum: float, maximum: float, integer: bool = False):
        try:
            if isinstance(value, bool):
                raise ValueError("boolean is not a number")
            parsed = float(value)
            if integer and not parsed.is_integer():
                raise ValueError("not an integer")
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label} không phải số hợp lệ") from error
        if not minimum <= parsed <= maximum:
            raise ValueError(f"{label} phải từ {minimum} đến {maximum}")
        return int(parsed) if integer else parsed

    def save(self, payload: dict) -> dict:
        with self.config_lock:
            # Browser sends the values it originally read. Merge only edited fields,
            # so another editor's changes survive a stale autosave.
            baseline = payload.get("base")
            if isinstance(baseline, dict):
                payload = {**payload, **{section: {key: value for key, value in (payload.get(section) or {}).items()
                    if value != (baseline.get(section) or {}).get(key)} for section in ("bridge", "mod", "gui")}}
            directory = (payload.get("gui") or {}).get("minecraft_directory", load_gui_state()["minecraft_directory"])
            with config_file_lock(mod_config_path(directory)):
                return self._save(payload)

    def runtime_state(self, directory=None) -> dict:
        directory = directory or load_gui_state()["minecraft_directory"]
        path = mod_config_path(directory)
        with self.config_lock, config_file_lock(path):
            bridge = load_json(BRIDGE_CONFIG_PATH, DEFAULT_BRIDGE_CONFIG)
            mod = load_json(path, DEFAULT_MOD_CONFIG)
            missing = [key for key in EVENT_KEYS if key not in mod]
            for key in missing:
                mod[key] = bridge[key]
            if missing or not path.exists():
                save_json(path, mod)
            changed = bridge.get("runtime_settings_path") != str(path.resolve())
            bridge["runtime_settings_path"] = str(path.resolve())
            for key in EVENT_KEYS:
                if bridge[key] != mod[key]: changed = True
                bridge[key] = mod[key]
            if changed:
                save_json(BRIDGE_CONFIG_PATH, bridge)
            return {"bridge": {key: mod[key] for key in EVENT_KEYS},
                    "mod": {key: mod[key] for key in MOD_KEYS}}

    def _save(self, payload: dict) -> dict:
        gui = {**load_gui_state(), **dict(payload.get("gui") or {})}
        bridge = {**load_json(BRIDGE_CONFIG_PATH, DEFAULT_BRIDGE_CONFIG), **dict(payload.get("bridge") or {})}
        bridge.setdefault("gift_actions", [dict(rule) for rule in DEFAULT_GIFT_ACTIONS])
        mod = {**load_json(mod_config_path(gui["minecraft_directory"]), DEFAULT_MOD_CONFIG), **dict(payload.get("mod") or {})}
        for key in EVENT_KEYS:
            if key not in (payload.get("bridge") or {}) and key in mod:
                bridge[key] = mod[key]
        actions = bridge.get("gift_actions")
        if not isinstance(actions, list):
            raise ValueError("Danh sách quà không hợp lệ")
        cleaned_actions = []
        used: set[str] = set()
        for index, rule in enumerate(actions, 1):
            gift_name = str(rule.get("gift_name", "")).strip()
            gift_id = str(rule.get("gift_id", "")).strip()
            action = str(rule.get("action", "")).strip().lower()
            target = str(rule.get("target", "")).strip().lower()
            if not gift_name or action not in {"special", "item", "mob"} or not target:
                raise ValueError(f"Quà dòng {index} chưa đủ tên hoặc phần thưởng")
            key = f"id:{gift_id}" if gift_id else f"name:{normalize_gift_name(gift_name)}"
            if key in used:
                raise ValueError(f"Quà '{gift_name}' đang bị gán trùng")
            used.add(key)
            cleaned_actions.append({
                "gift_name": gift_name,
                "gift_id": gift_id,
                "panel_note": str(rule.get("panel_note") or "").strip()[:160],
                "vietnamese_name": str(rule.get("vietnamese_name") or gift_name).strip(),
                "coin_value": self._number(rule.get("coin_value", 0), "Giá xu", 0, 1_000_000, True),
                "action": action,
                "target": target,
                "amount": self._number(rule.get("amount", 1), "Số lượng", 1, 100, True),
                "level": self._number(rule.get("level", 0 if target.startswith("enchant_") else 1), "Cấp phần thưởng", 0 if target.startswith("enchant_") else 1, 255, True),
            })
        bridge["gift_actions"] = cleaned_actions
        if bridge["unmapped_gift_mode"] not in {"thanks", "reward"}:
            raise ValueError("Chọn cách xử lý quà chưa gán hợp lệ")
        if bridge["unmapped_gift_action"] not in {"item", "mob", "special"}:
            raise ValueError("Loại phần thưởng mặc định không hợp lệ")
        bridge["unmapped_gift_target"] = str(bridge["unmapped_gift_target"]).strip().lower()
        if not bridge["unmapped_gift_target"]:
            raise ValueError("Chọn phần thưởng cho quà chưa gán")
        bridge["unmapped_gift_amount"] = self._number(bridge["unmapped_gift_amount"], "Số phần thưởng mặc định", 1, 100, True)
        bridge["unmapped_gift_level"] = self._number(bridge["unmapped_gift_level"], "Cấp phần thưởng mặc định", 0 if bridge["unmapped_gift_target"].startswith("enchant_") else 1, 255, True)
        if not isinstance(bridge["view_enabled"], bool):
            raise ValueError("Bật View phải là true/false")
        bridge["view_max_mobs_per_round"] = self._number(bridge["view_max_mobs_per_round"], "Mob tối đa mỗi đợt View", 1, 1000, True)
        bridge["view_mob_type"] = str(bridge["view_mob_type"]).strip().lower()
        if not bridge["view_mob_type"]:
            raise ValueError("Chọn mob cho View")
        configured_images = bridge.get("event_images") or {}
        bridge["event_images"] = {
            key: str(configured_images.get(key) or "").strip()
            for key in ("follow", "comment", "share", "like", "view")
            if str(configured_images.get(key) or "").strip()
        }
        bridge["tiktok_username"] = str(bridge.get("tiktok_username", "")).strip().lstrip("@")
        if not bridge["tiktok_username"]:
            raise ValueError("Tên tài khoản TikTok không được để trống")
        bridge["minecraft_port"] = self._number(bridge.get("minecraft_port", 9876), "Cổng", 1024, 65535, True)
        bridge["minecraft_host"] = str(bridge.get("minecraft_host") or "localhost").strip()
        for key in ("likes_per_skeleton", "like_spawn_count", "comment_spawn_count", "share_spawn_count", "follow_spawn_count", "view_spawn_count", "comment_limit", "share_limit"):
            maximum = 100 if key.endswith("_spawn_count") else 100_000
            bridge[key] = self._number(bridge.get(key, 1), key, 1, maximum, True)
        for key in ("comment_cooldown_seconds", "share_cooldown_seconds", "view_interval_seconds"):
            bridge[key] = self._number(bridge.get(key, 10), key, 1, 86_400)
        for key, maximum in (("tts_max_characters", 5_000), ("tts_queue_size", 10_000)):
            bridge[key] = self._number(bridge.get(key, DEFAULT_BRIDGE_CONFIG[key]), key, 1, maximum, True)
        for key, minimum, maximum in (
            ("gift_voicevox_volume", 0, 1),
            ("gift_overlay_duration_seconds", 1, 60),
            ("gift_overlay_x", 0, 100),
            ("gift_overlay_y", 0, 100),
            ("tts_voicevox_speed", 0.5, 2),
            ("tts_voicevox_pitch", -0.15, 0.15),
            ("tts_voicevox_intonation", 0, 2),
            ("tts_pause_between_comments_seconds", 0, 3_600),
            ("tts_trailing_silence_seconds", 0, 30),
            ("tts_stability", 0, 1),
            ("tts_similarity_boost", 0, 1),
            ("tts_style", 0, 1),
            ("tts_speed", 0.7, 1.2),
            ("tts_volume", 0, 1),
        ):
            bridge[key] = self._number(bridge.get(key, DEFAULT_BRIDGE_CONFIG[key]), key, minimum, maximum)
        for key, default in DEFAULT_BRIDGE_CONFIG.items():
            if isinstance(default, bool) and not isinstance(bridge[key], bool):
                raise ValueError(f"{key} phải là bật hoặc tắt")
        bridge["tts_language_code"] = str(bridge.get("tts_language_code") or "").strip()
        bridge["gift_overlay_width"] = self._number(bridge["gift_overlay_width"], "Cỡ GIF", 160, 800, True)
        bridge["gift_alert_queue_size"] = self._number(bridge["gift_alert_queue_size"], "Hàng quà cảm ơn", 1, 10000, True)
        if bridge["gift_phrase_mode"] not in ("fixed", "random", "custom"):
            raise ValueError("Chọn cách phát câu cảm ơn hợp lệ")
        if bridge["gift_phrase_id"] not in {p["id"] for p in gift_media.PHRASES}:
            raise ValueError("Câu cảm ơn không có trong danh sách")
        bridge["gift_phrase_custom"] = str(bridge.get("gift_phrase_custom") or "").strip()
        if len(bridge["gift_phrase_custom"]) > 160:
            raise ValueError("Câu cảm ơn tự nhập tối đa 160 ký tự")
        if bridge["gift_phrase_mode"] == "custom" and not bridge["gift_phrase_custom"]:
            raise ValueError("Nhập câu tiếng Nhật để dùng chế độ Tự nhập")
        if not bridge["gift_gif_random"] and bridge["gift_gif_file"] not in gift_media.catalog()["gifs"]:
            raise ValueError("GIF đã chọn không còn trong thư mục; hãy chọn lại")
        if bridge["tts_provider"] not in ("elevenlabs", "edge"):
            raise ValueError("Dịch vụ giọng đọc không hợp lệ")
        if bridge["tts_edge_voice"] not in VIETNAMESE_VOICES:
            raise ValueError("Chọn giọng tiếng Việt Hoài My hoặc Nam Minh")
        bridge["tts_edge_rate"] = self._number(bridge["tts_edge_rate"], "Tốc độ giọng Việt", -50, 100, True)
        bridge["tts_edge_pitch"] = self._number(bridge["tts_edge_pitch"], "Cao độ giọng Việt", -100, 100, True)
        bridge["tts_voicevox_url"] = voicevox_tts.validate_url(bridge["tts_voicevox_url"])
        bridge["tts_voicevox_speaker_id"] = self._number(bridge["tts_voicevox_speaker_id"], "ID giọng VOICEVOX", 0, 1_000_000, True)
        bridge["tts_test_text"] = str(bridge.get("tts_test_text") or "").strip()
        if len(bridge["tts_test_text"]) > 1000:
            raise ValueError("Câu nghe thử tối đa 1000 ký tự")
        if bridge["tts_language_code"] and not re.fullmatch(r"[a-z]{2,3}", bridge["tts_language_code"]):
            raise ValueError("Mã ngôn ngữ dùng 2–3 chữ thường (vi, en…), để trống để tự nhận diện")
        for key in ("tts_voice_name", "tts_voice_id", "tts_model_id"):
            bridge[key] = str(bridge.get(key) or "").strip()
        if not bridge["tts_model_id"]:
            raise ValueError("Model ID giọng đọc không được để trống")
        bridge["display_comment_max_characters"] = self._number(
            bridge["display_comment_max_characters"], "Độ dài comment hiển thị", 1, 96, True)

        directory = str(gui.get("minecraft_directory", "")).strip()
        if not directory:
            raise ValueError("Thư mục Minecraft không được để trống")
        mod["bridge_port"] = bridge["minecraft_port"]
        for key in ("golem_teleport_distance", "wolf_teleport_distance"):
            mod[key] = self._number(mod.get(key, 20), key, 5, 128)
        for key, minimum, maximum in (("max_pending_events", 10, 100_000), ("max_interactions_per_tick", 1, 1000), ("notification_queue_size", 1, 10_000), ("max_mobs_per_user", 1, 1000), ("max_mobs_total", 1, 10_000), ("money_gun_arrow_count", 1, 64), ("universe_effect_level", 1, 10)):
            mod[key] = self._number(mod.get(key, DEFAULT_MOD_CONFIG[key]), key, minimum, maximum, True)
        for key in ("mob_lifetime_seconds", "spawn_min_distance", "spawn_max_distance"):
            mod[key] = self._number(mod.get(key, DEFAULT_MOD_CONFIG[key]), key, 0 if key.startswith("spawn") else 1, 86_400 if key == "mob_lifetime_seconds" else 128)
        if mod.get("spawn_direction", "front") not in ("front", "right", "left", "back", "random"):
            raise ValueError("Vị trí triệu hồi không hợp lệ")
        mod["spawn_height_offset"] = self._number(mod.get("spawn_height_offset", 0), "spawn_height_offset", -64, 64)
        for key, minimum, maximum in (("notification_duration_seconds", 0.05, 300), ("donation_notification_duration_seconds", 0.05, 300), ("effect_duration_seconds", 0.05, 3_600), ("absorption_hearts_per_rose", 0.5, 100)):
            mod[key] = self._number(mod.get(key, DEFAULT_MOD_CONFIG[key]), key, minimum, maximum)
        for key in ("enderman_targets_player", "mobs_persistent", "show_countdown_in_name"):
            if not isinstance(mod[key], bool):
                raise ValueError(f"{key} phải là bật hoặc tắt")
        for key, default in DEFAULT_MOD_CONFIG.items():
            if isinstance(default, bool) and not isinstance(mod[key], bool):
                raise ValueError(f"{key} phải là bật hoặc tắt")
        for key, maximum in (("notification_fade_in_seconds", 30), ("notification_fade_out_seconds", 30), ("notification_gap_seconds", 300)):
            mod[key] = self._number(mod[key], key, 0, maximum)
        for key in ("notification_title_color", "notification_username_color", "donation_notification_color"):
            if not isinstance(mod[key], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", mod[key]):
                raise ValueError(f"{key} phải là màu #RRGGBB")
        if mod["notification_overflow_policy"] not in ("drop_newest", "drop_oldest"):
            raise ValueError("Chính sách hàng đợi hiển thị không hợp lệ")
        positions = mod.get("notification_positions")
        if not isinstance(positions, dict):
            raise ValueError("Vị trí thông báo không hợp lệ")
        normalized_positions = {}
        for kind in ("like", "comment", "share", "follow", "view", "gift"):
            position = positions.get(kind, {})
            if not isinstance(position, dict):
                raise ValueError(f"Vị trí {kind} không hợp lệ")
            normalized_positions[kind] = {
                "x": self._number(position.get("x", 50), f"{kind}: ngang (%)", 0, 100),
                "y": self._number(position.get("y", 40), f"{kind}: dọc (%)", 0, 100),
                "scale": self._number(position.get("scale", 1), f"{kind}: cỡ chữ", 0.5, 4),
            }
        mod["notification_positions"] = normalized_positions
        modes = mod.get("notification_display_modes", {})
        if not isinstance(modes, dict):
            raise ValueError("Kiểu hiển thị tương tác không hợp lệ")
        normalized_modes = {}
        for kind in ("like", "comment", "share", "follow", "view", "gift"):
            mode = modes.get(kind, "legacy")
            if mode not in ("legacy", "center", "chat"):
                raise ValueError(f"Kiểu hiển thị {kind} không hợp lệ")
            normalized_modes[kind] = mode
        mod["notification_display_modes"] = normalized_modes
        if mod["spawn_max_distance"] < mod["spawn_min_distance"]:
            raise ValueError("Khoảng cách tối đa phải lớn hơn khoảng cách tối thiểu")

        for key in EVENT_KEYS:
            mod[key] = bridge[key]
        bridge["runtime_settings_path"] = str(mod_config_path(directory).resolve())
        save_json(BRIDGE_CONFIG_PATH, bridge)
        save_json(mod_config_path(directory), mod)
        keep_running = bool(gui.get("keep_minecraft_running_in_background", True))
        save_json(GUI_STATE_PATH, {"minecraft_directory": directory, "keep_minecraft_running_in_background": keep_running})
        set_pause_on_lost_focus(directory, pause=not keep_running)
        if "api_key" in payload:
            save_api_key(str(payload["api_key"]))
        self.log("INFO", f"Đã lưu bridge và mod config tại {mod_config_path(directory)}")
        return {"message": "Đã lưu toàn bộ cấu hình", "restart_live": self.is_live_running()}

    def is_live_running(self) -> bool:
        return self.live_process is not None and self.live_process.poll() is None

    def spawn_bridge(self, arguments: list[str], label: str, live: bool = False) -> dict:
        if live and self.is_live_running():
            return {"message": "Bridge LIVE đang chạy", "running": True}
        launcher = BRIDGE_DIR / "RUN_BRIDGE.bat"
        environment = os.environ.copy()
        environment.update(PYTHONUTF8="1", PYTHONUNBUFFERED="1")
        command = subprocess.list2cmdline([str(launcher), *arguments])
        process = subprocess.Popen(
            command,
            cwd=BRIDGE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.processes.add(process)
        if live:
            self.live_process = process
        self.log("INFO", f"Đã chạy {label} (PID {process.pid})")
        threading.Thread(target=self._read_process, args=(process, label), daemon=True).start()
        return {"message": f"Đã chạy {label}", "running": live}

    def _read_process(self, process: subprocess.Popen[str], label: str) -> None:
        if process.stdout:
            for line in process.stdout:
                self.log("LIVE" if label == "LIVE" else "PROCESS", line.rstrip())
        code = process.wait()
        self.processes.discard(process)
        if self.live_process is process:
            self.live_process = None
        self.log("INFO" if code == 0 else "ERROR", f"{label} đã kết thúc với mã {code}")

    def action(self, name: str) -> dict:
        if name == "update_gifts":
            config = load_json(BRIDGE_CONFIG_PATH, DEFAULT_BRIDGE_CONFIG)
            return self.gift_updater.start(config["tiktok_username"])
        if name == "start_live":
            return self.spawn_bridge([], "LIVE", True)
        if name == "stop_live":
            if not self.is_live_running():
                return {"message": "Bridge LIVE chưa chạy", "running": False}
            process = self.live_process
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                process.terminate()
            self.log("WARN", "Đã gửi lệnh dừng bridge LIVE")
            return {"message": "Đã dừng bridge LIVE", "running": False}
        if name == "test_mobs":
            return self.spawn_bridge(["--test", "mobs"], "TEST MOB")
        if name == "test_gifts":
            return self.spawn_bridge(["--test", "gifts"], "TEST QUÀ")
        if name == "test_tts":
            return self.spawn_bridge(["--test-tts"], "TEST GIỌNG")
        if name == "test_gift_alert":
            if self.is_live_running():
                raise ValueError("Dừng LIVE trước khi test lời cảm ơn để tránh phát trùng âm thanh với LIVE.")
            return self.spawn_bridge(["--test-gift-alert"], "TEST CẢM ƠN QUÀ")
        if name == "install_mod":
            state = load_gui_state()
            source = PROJECT_DIR / "release" / "tiktokmob-1.0.0.jar"
            destination = Path(state["minecraft_directory"]) / "mods" / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            self.log("INFO", f"Đã cài mod vào {destination}")
            return {"message": "Đã cài mod; hãy khởi động lại Minecraft"}
        raise ValueError("Thao tác không được hỗ trợ")

    def shutdown(self) -> None:
        self.test_runner.stop()
        if self.is_live_running():
            try:
                self.action("stop_live")
            except OSError:
                pass

    def log_state(self, offset: int) -> dict:
        with self.lock:
            first = self.log_sequence - len(self.logs)
            if offset > self.log_sequence:
                offset = 0
            lines = self.logs[max(0, offset - first):]
            next_offset = self.log_sequence
        return {"lines": lines, "offset": next_offset, "live_running": self.is_live_running(), "test": self.test_runner.state()}

    def start_test(self, request: dict) -> dict:
        self.runtime_state()
        with self.config_lock:
            config = load_json(BRIDGE_CONFIG_PATH, DEFAULT_BRIDGE_CONFIG)
            config.setdefault("gift_actions", [dict(rule) for rule in DEFAULT_GIFT_ACTIONS])
        return self.test_runner.start(config, request)

    def minecraft_jar(self, directory: str) -> Path | None:
        if directory in self._jar_cache:
            return self._jar_cache[directory]
        selected = Path(directory)
        root = selected.parent.parent if selected.parent.name.casefold() == "instances" else selected
        version = "26.2"
        metadata = selected / "minecraftinstance.json"
        try:
            data = json.loads(metadata.read_text(encoding="utf-8-sig"))
            version_json = json.loads(data.get("baseModLoader", {}).get("versionJson", "{}"))
            version = str(version_json.get("inheritsFrom") or version)
        except (OSError, ValueError, TypeError):
            pass
        candidate = root / "Install" / "versions" / version / f"{version}.jar"
        self._jar_cache[directory] = candidate if candidate.is_file() else None
        return self._jar_cache[directory]

    def icon(self, kind: str, target: str) -> tuple[bytes, str]:
        state = load_gui_state()
        jar_path = self.minecraft_jar(str(state["minecraft_directory"]))
        item_id = target.split(":", 1)[-1]

        def placeholder(identifier: str) -> tuple[bytes, str]:
            label = identifier[:2].upper()
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" rx="12" fill="#17233a"/><text x="32" y="39" text-anchor="middle" fill="#7cf6d2" font-family="sans-serif" font-size="20">{label}</text></svg>'
            return svg.encode(), "image/svg+xml"

        if kind == "mob":
            # Prefer the bundled artwork over old, thin full-body CDN renders.
            if item_id in {"enderman", "zombie", "skeleton", "creeper", "spider"}:
                bundled = WEB_DIR / "assets" / f"{item_id}.png"
                if bundled.is_file():
                    return bundled.read_bytes(), "image/png"
            cache_directory = Path(os.environ.get("LOCALAPPDATA", str(WEB_DIR))) / "TikTokMobForge" / "mob_icons"
            cache_path = cache_directory / f"{item_id}.png"
            if cache_path.is_file():
                return cache_path.read_bytes(), "image/png"
            try:
                url = (
                    "https://cdn.jsdelivr.net/gh/IsaiahPapa/"
                    f"minecraft-render-pipeline@main/dist/latest/{urllib.parse.quote(item_id)}/headshot.png"
                )
                request = urllib.request.Request(url, headers={"User-Agent": "TikTokMobForge/1.0"})
                with urllib.request.urlopen(request, timeout=5) as response:
                    rendered = response.read(3_000_000)
                if rendered.startswith(b"\x89PNG"):
                    cache_directory.mkdir(parents=True, exist_ok=True)
                    cache_path.write_bytes(rendered)
                    return rendered, "image/png"
            except (OSError, urllib.error.URLError, ValueError):
                pass
            return placeholder(item_id)
        special_icons = {
            "keep_inventory_on": "totem_of_undying", "keep_inventory_off": "bone",
            "set_respawn": "red_bed", "kill_player": "netherite_sword",
            "sky_launch": "firework_rocket", "spawn_tnt": "tnt",
            "armored_wolf": "wolf_armor",
            "divine_cat": "cat_spawn_egg",
            "netherite_armor_full4": "netherite_chestplate",
            "diamond_armor_full4": "diamond_chestplate",
            "clear_inventory": "barrier",
            "troll_chicken": "egg", "troll_cobweb": "cobweb",
            "troll_pumpkin": "carved_pumpkin", "troll_slowness": "soul_sand",
            "troll_teleport": "ender_pearl", "troll_creeper": "creeper_head",
            "troll_anvil": "anvil", "troll_hotbar": "chest",
            "troll_warden": "sculk_shrieker", "troll_box": "ender_chest",
            "absorption": "golden_apple", "iron_armor": "iron_chestplate",
            "netherite_armor": "netherite_chestplate", "golden_apple": "golden_apple",
            "regeneration": "potion", "shield": "shield", "money_gun": "bow",
            "diamond_sword": "diamond_sword", "diamond_armor": "diamond_chestplate",
            "netherite_power": "netherite_sword",
            "enchant_armor": "enchanted_book", "enchant_weapon": "enchanted_book",
            "repair_armor": "anvil", "repair_hand": "anvil", "full_heal": "golden_apple",
            "experience": "experience_bottle",
        }
        if kind == "special":
            item_id = special_icons.get(item_id, "chest")
        # Inventory renders are matched to exact registry IDs, including model
        # inheritance, multi-layer sprites, enchanted glint and entity items.
        namespace = target.split(":", 1)[0] if ":" in target else "minecraft"
        if (kind == "special" or namespace == "minecraft") and re.fullmatch(r"[a-z0-9_]+", item_id):
            inventory_icon = WEB_DIR / "assets/minecraft-inventory" / f"{item_id}.png"
            if inventory_icon.is_file():
                return inventory_icon.read_bytes(), "image/png"
        if item_id == "shield":
            rendered_icon = WEB_DIR / "assets/minecraft-items/shield.png"
            if rendered_icon.is_file():
                return rendered_icon.read_bytes(), "image/png"
        if jar_path:
            try:
                with zipfile.ZipFile(jar_path) as archive:
                    for path in (
                        f"assets/minecraft/textures/item/{item_id}.png",
                        f"assets/minecraft/textures/block/{item_id}.png",
                    ):
                        try:
                            return archive.read(path), "image/png"
                        except KeyError:
                            continue
            except (OSError, KeyError, zipfile.BadZipFile):
                pass
        return placeholder(item_id)

    def panorama(self) -> tuple[bytes, str]:
        state = load_gui_state()
        directory = str(state["minecraft_directory"])
        asset_key = "minecraft/textures/gui/title/background/panorama_0.png"
        for assets in _candidate_asset_directories(directory):
            indexes = sorted((assets / "indexes").glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
            for index_path in indexes:
                try:
                    index = json.loads(index_path.read_text(encoding="utf-8-sig"))
                    entry = index.get("objects", {}).get(asset_key)
                    if not entry:
                        continue
                    digest = str(entry["hash"])
                    image = assets / "objects" / digest[:2] / digest
                    if image.is_file() and image.stat().st_size > 1000:
                        return image.read_bytes(), "image/png"
                except (OSError, ValueError, KeyError):
                    continue
        jar_path = self.minecraft_jar(directory)
        if jar_path:
            try:
                with zipfile.ZipFile(jar_path) as archive:
                    return archive.read("assets/minecraft/textures/gui/title/background/panorama_0.png"), "image/png"
            except (OSError, KeyError, zipfile.BadZipFile):
                pass
        return b"", "image/png"

    @staticmethod
    def upload_image(slot: str, data_url: str, mob_target: str = "") -> dict:
        if slot not in {"follow", "comment", "share", "like", "view"}:
            raise ValueError("Vị trí ảnh mob không hợp lệ")
        match = re.fullmatch(r"data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=\r\n]+)", data_url or "")
        if not match:
            raise ValueError("Chỉ nhận ảnh PNG, JPG hoặc WebP")
        try:
            content = base64.b64decode(match.group(2), validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError("Dữ liệu ảnh không hợp lệ") from error
        if not content or len(content) > 5 * 1024 * 1024:
            raise ValueError("Ảnh mob phải từ 1 byte đến 5 MB")
        valid_signature = {
            "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/jpeg": content.startswith(b"\xff\xd8\xff"),
            "image/webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP",
        }[match.group(1)]
        if not valid_signature:
            raise ValueError("Nội dung tệp không đúng định dạng ảnh đã chọn")
        extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[match.group(1)]
        CUSTOM_ASSET_DIR.mkdir(parents=True, exist_ok=True)
        path = CUSTOM_ASSET_DIR / f"event-{slot}.{extension}"
        path.write_bytes(content)
        url = f"/assets/custom/{path.name}?v={int(path.stat().st_mtime_ns)}"
        bridge = load_json(BRIDGE_CONFIG_PATH, DEFAULT_BRIDGE_CONFIG)
        bridge["event_images"] = {**(bridge.get("event_images") or {}), slot: url}
        target = str(mob_target or bridge.get(f"{slot}_mob_type", "")).strip()
        bridge["event_image_targets"] = {**(bridge.get("event_image_targets") or {}), slot: target}
        save_json(BRIDGE_CONFIG_PATH, bridge)
        return {"url": url, "mob_target": target}

    def elevenlabs_catalog(self, api_key: str) -> dict:
        key = api_key.strip() or load_api_key()
        def fetch(url: str, authenticated: bool = True):
            headers = {"Accept": "application/json"}
            if authenticated and key:
                headers["xi-api-key"] = key
            request = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                try:
                    detail = json.loads(error.read().decode("utf-8")).get("detail", {})
                    message = detail.get("message") if isinstance(detail, dict) else str(detail)
                except (ValueError, OSError):
                    message = ""
                finally:
                    error.close()
                raise ValueError(message or f"ElevenLabs trả về HTTP {error.code}") from error
            except (TimeoutError, json.JSONDecodeError) as error:
                raise ValueError("ElevenLabs phản hồi quá lâu hoặc trả dữ liệu không hợp lệ") from error
            except urllib.error.URLError as error:
                raise ValueError(f"Không kết nối được ElevenLabs: {error.reason}") from error

        warnings: list[str] = []
        voice_data = {"voices": []}
        try:
            if not key:
                raise ValueError("Chưa nhập API key; dùng giọng công khai. Cần API key để đọc bình luận.")
            tokens = set()
            url = "https://api.elevenlabs.io/v2/voices?page_size=100&include_total_count=false"
            while True:
                page = fetch(url)
                voice_data["voices"].extend(page.get("voices", []))
                token = page.get("next_page_token")
                if not page.get("has_more") or not token or token in tokens:
                    break
                tokens.add(token)
                url = "https://api.elevenlabs.io/v2/voices?" + urllib.parse.urlencode({
                    "page_size": 100, "include_total_count": "false", "next_page_token": token})
        except ValueError as error:
            warnings.append(f"Không tải được voice: {error}")
        if not voice_data["voices"]:
            try:
                # Public default voices only; never claims access to private account voices.
                voice_data = fetch("https://api.elevenlabs.io/v1/voices", authenticated=False)
                warnings.append("Đang hiển thị giọng công khai. Bật quyền voices_read trên API key để tải giọng riêng của tài khoản.")
            except ValueError as error:
                warnings.append(f"Không tải được giọng công khai: {error}")
        try:
            if not key:
                raise ValueError("Chưa nhập API key")
            model_data = fetch("https://api.elevenlabs.io/v1/models")
        except ValueError as error:
            model_data = [
                {"model_id": "eleven_flash_v2_5", "name": "Flash v2.5", "description": "Nhanh, độ trễ thấp", "can_do_text_to_speech": True},
                {"model_id": "eleven_turbo_v2_5", "name": "Turbo v2.5", "description": "Cân bằng tốc độ và chất lượng", "can_do_text_to_speech": True},
                {"model_id": "eleven_multilingual_v2", "name": "Multilingual v2", "description": "Giọng đa ngôn ngữ", "can_do_text_to_speech": True},
                {"model_id": "eleven_v3", "name": "Eleven v3", "description": "Biểu cảm cao", "can_do_text_to_speech": True},
            ]
            warnings.append(f"Không tải được model theo tài khoản: {error}. Đang dùng danh sách thay thế tích hợp.")
        voices = [
            {
                "voice_id": str(voice.get("voice_id", "")),
                "name": str(voice.get("name", "Không tên")),
                "category": str(voice.get("category") or ""),
            }
            for voice in voice_data.get("voices", [])
            if voice.get("voice_id")
        ]
        models = [
            {
                "model_id": str(model.get("model_id", "")),
                "name": str(model.get("name") or model.get("model_id", "")),
                "description": str(model.get("description") or ""),
            }
            for model in model_data
            if model.get("model_id") and model.get("can_do_text_to_speech", True)
        ]
        current = load_json(BRIDGE_CONFIG_PATH, DEFAULT_BRIDGE_CONFIG)
        current_voice_id = str(current.get("tts_voice_id", ""))
        if current_voice_id and not any(voice["voice_id"] == current_voice_id for voice in voices):
            voices.insert(0, {"voice_id": current_voice_id,
                "name": str(current.get("tts_voice_name") or "Giọng hiện tại"), "category": "current"})
        voices = list({voice["voice_id"]: voice for voice in voices}.values())
        return {"voices": voices, "models": models, "warnings": warnings}


CONTROLLER = Controller()


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/" or path.endswith((".html", ".js", ".css")):
            self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, _format: str, *_args) -> None:
        pass

    def json_response(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self.server.last_activity = time.monotonic()
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/api/health":
                return self.json_response({"instance": GUI_INSTANCE, "runtime_sync": True})
            if parsed.path == "/api/state":
                return self.json_response(CONTROLLER.state())
            if parsed.path == "/api/runtime-settings":
                return self.json_response(CONTROLLER.runtime_state())
            if parsed.path == "/api/test/catalog":
                config = load_json(BRIDGE_CONFIG_PATH, DEFAULT_BRIDGE_CONFIG)
                return self.json_response({"gifts": config.get("gift_actions", DEFAULT_GIFT_ACTIONS)})
            if parsed.path == "/api/gift-media":
                return self.json_response(gift_media.catalog())
            if parsed.path == "/api/gifts":
                return self.json_response({"gifts": gift_catalog_service.catalog(), "update": CONTROLLER.gift_updater.snapshot()})
            if parsed.path == "/api/minecraft-viewport":
                return self.json_response(minecraft_viewport())
            if parsed.path == "/api/logs":
                return self.json_response(CONTROLLER.log_state(int(query.get("offset", [0])[0])))
            if parsed.path == "/api/icon":
                data, mime = CONTROLLER.icon(query.get("kind", ["item"])[0], query.get("id", [""])[0])
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                return self.wfile.write(data)
            if parsed.path == "/api/panorama":
                data, mime = CONTROLLER.panorama()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                return self.wfile.write(data)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return None
        except Exception as error:
            return self.json_response({"error": str(error)}, 500)
        return super().do_GET()

    def do_POST(self) -> None:
        self.server.last_activity = time.monotonic()
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/save":
                return self.json_response(CONTROLLER.save(payload))
            if self.path == "/api/action":
                return self.json_response(CONTROLLER.action(str(payload.get("name", ""))))
            if self.path == "/api/test":
                return self.json_response(CONTROLLER.start_test(payload))
            if self.path == "/api/test/stop":
                return self.json_response(CONTROLLER.test_runner.stop())
            if self.path == "/api/elevenlabs":
                return self.json_response(CONTROLLER.elevenlabs_catalog(str(payload.get("api_key", ""))))
            if self.path == "/api/voicevox":
                return self.json_response(voicevox_tts.list_voices(str(payload.get("url", "http://127.0.0.1:50021"))))
            if self.path == "/api/upload-image":
                return self.json_response(CONTROLLER.upload_image(
                    str(payload.get("slot", "")), str(payload.get("data_url", "")), str(payload.get("mob_target", ""))
                ))
            return self.json_response({"error": "Không tìm thấy API"}, 404)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return None
        except Exception as error:
            CONTROLLER.log("ERROR", str(error))
            try:
                return self.json_response({"error": str(error)}, 400)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                return None


def focus_gui_window() -> None:
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def visit(handle, _):
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(handle, title, len(title))
        if title.value == "Bảng điều khiển LIVE":
            user32.ShowWindow(handle, 9)  # Restore if minimized.
            user32.SetForegroundWindow(handle)
        return True

    user32.EnumWindows(visit, 0)


def open_window(url: str) -> None:
    # A restored Edge app window can retain its old document even after files
    # and HTTP cache headers change. Version both the app URL and its profile.
    revision = hashlib.sha256((WEB_DIR / "app.js").read_bytes()).hexdigest()[:12]
    url = url + ("&" if "?" in url else "?") + f"view=events&ui={revision}"
    edge_candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
    ]
    edge = next((path for path in edge_candidates if path.is_file()), None)
    if edge:
        profile = (Path(os.environ.get("LOCALAPPDATA", str(WEB_DIR))) / "TikTokMobForge"
                   / f"WebViewProfile-{GUI_INSTANCE[:8]}-named-view")
        profile.mkdir(parents=True, exist_ok=True)
        subprocess.Popen([
            str(edge), f"--app={url}", "--start-maximized", "--no-first-run",
            "--disable-background-mode", f"--user-data-dir={profile}",
        ])
        # Edge can hand the URL to an existing process and exit immediately.
        # Its launcher lifetime does not represent the app window lifetime.
    else:
        webbrowser.open(url)
    # Do not focus every window with this title: that can bring an old,
    # already-loaded four-card window in front of the newly opened app.


def existing_gui(url: str) -> bool:
    try:
        with urllib.request.urlopen(url + "api/health", timeout=1) as response:
            return json.load(response).get("instance") == GUI_INSTANCE
    except (OSError, ValueError):
        return False


def stop_when_idle(server: ThreadingHTTPServer, stopped: threading.Event) -> None:
    # Polling in the GUI keeps the server alive even when another app window closes.
    # Keep active LIVE/test processes alive if the user closes the control window.
    while not stopped.wait(10):
        if time.monotonic() - server.last_activity < 180:
            continue
        busy = any(process.poll() is None for process in CONTROLLER.processes.copy())
        if not busy and not CONTROLLER.test_runner.state()["running"]:
            server.shutdown()
            return


def gui_server() -> tuple[ThreadingHTTPServer | None, str]:
    # Windows can reserve the original port for Hyper-V/WSL. Use stable,
    # widely spaced alternatives so subsequent launches find the same GUI.
    ports = [GUI_PORT] + [12000 + (int(GUI_INSTANCE[:8], 16) + i * 997) % 30000
                          for i in range(16)]
    last_error = None
    for port in dict.fromkeys(ports):
        url = f"http://127.0.0.1:{port}/"
        if existing_gui(url):
            return None, url
        try:
            return ThreadingHTTPServer(("127.0.0.1", port), Handler), url
        except OSError as error:
            if error.errno not in (13, 48, 98, 10013, 10048) and getattr(error, "winerror", None) not in (10013, 10048):
                raise
            last_error = error
            # A concurrent launch may have bound the port before serving health.
            if getattr(error, "winerror", error.errno) in (48, 98, 10048):
                for _ in range(20):
                    if existing_gui(url):
                        return None, url
                    time.sleep(0.1)
    raise OSError("Khong tim duoc cong cho GUI; hay kiem tra phan mem chan ket noi localhost.") from last_error


def main() -> None:
    server, url = gui_server()
    desktop = "--desktop" in sys.argv
    if "--url-file" in sys.argv:
        destination = Path(sys.argv[sys.argv.index("--url-file") + 1])
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(url, encoding="utf-8")
        temporary.replace(destination)
    if server is None:
        if not desktop:
            open_window(url)
        return
    print(f"LIVE Control: {url}", flush=True)
    server.last_activity = time.monotonic()
    stopped = threading.Event()
    threading.Thread(target=stop_when_idle, args=(server, stopped), daemon=True).start()
    if not desktop:
        threading.Timer(0.35, open_window, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stopped.set()
        CONTROLLER.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
