"""Shared game/GUI interaction settings; no LIVE restart needed."""
import json
import os
from pathlib import Path
import time
from contextlib import contextmanager

EVENT_KEYS = tuple(f"{kind}_{suffix}" for kind in ("follow", "comment", "share", "like", "view")
                   for suffix in ("mob_type", "spawn_count")) + (
    "view_enabled", "view_interval_seconds", "view_max_mobs_per_round",
    "likes_per_skeleton", "comment_limit", "comment_cooldown_seconds", "share_limit", "share_cooldown_seconds")
MOD_KEYS = ("golem_teleport_distance", "wolf_teleport_distance", "max_mobs_per_user", "max_mobs_total", "mob_lifetime_seconds", "max_interactions_per_tick",
            "spawn_min_distance", "spawn_max_distance", "spawn_height_offset", "spawn_direction", "max_pending_events",
            "enderman_targets_player", "mobs_persistent", "show_countdown_in_name", "show_death_counter")


@contextmanager
def config_file_lock(path):
    """Byte 0 also locked by Java FileChannel: protect read/merge/replace."""
    path = Path(str(path) + ".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if path.stat().st_size == 0:
            handle.write(b"\0"); handle.flush()
        if os.name == "nt":
            import msvcrt
            deadline = time.monotonic() + 5
            while True:
                try:
                    handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1); break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Cấu hình đang được Minecraft lưu; vui lòng thử lại")
                    time.sleep(0.025)
        else:
            import fcntl
            fcntl.lockf(handle, fcntl.LOCK_EX, 1, 0)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.lockf(handle, fcntl.LOCK_UN, 1, 0)


def settings_path(config):
    if config.get("runtime_settings_path"):
        return Path(config["runtime_settings_path"])
    return None


class LiveSettings:
    def __init__(self, config):
        self.config = config
        self.path = settings_path(config)
        self.modified = None

    def refresh(self):
        if self.path is None:
            return
        try:
            stamp = self.path.stat().st_mtime_ns
            if stamp == self.modified:
                return
            data = json.loads(self.path.read_text(encoding="utf-8-sig"))
            updates = {}
            for key in EVENT_KEYS:
                if key not in data:
                    continue
                value = data[key]
                if key == "view_enabled":
                    if not isinstance(value, bool): raise ValueError(key)
                elif key.endswith("_mob_type"):
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(key)
                else:
                    value = float(value)
                    maximum = 100 if key.endswith("_spawn_count") else 86400 if key.endswith("_seconds") else 1000 if key == "view_max_mobs_per_round" else 100000
                    if isinstance(data[key], bool) or not 1 <= value <= maximum:
                        raise ValueError(key)
                    if not key.endswith("_seconds"):
                        if not value.is_integer(): raise ValueError(key)
                        value = int(value)
                updates[key] = value
            self.config.update(updates)
            self.modified = stamp
        except (OSError, ValueError, TypeError):
            # Atomic writers normally prevent incomplete input; keep last good rules.
            return
