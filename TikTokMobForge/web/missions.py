"""Mission editor configuration; Minecraft owns the world/player progress."""
import copy
import json
import math
import re
import threading
import time
from pathlib import Path

LOCK = threading.Lock()
DEFAULT = {"enabled": False, "rules": []}


def number(value, low, high, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Cần nhập số hợp lệ")
    if not low <= value <= high or integer and int(value) != value:
        raise ValueError(f"Giá trị phải từ {low} đến {high}" + (" và là số nguyên" if integer else ""))
    return int(value) if integer else value


def validate(data):
    if not isinstance(data, dict) or not isinstance(data.get("enabled"), bool):
        raise ValueError("Cấu hình nhiệm vụ không hợp lệ")
    rows = data.get("rules")
    if not isinstance(rows, list) or len(rows) > 32:
        raise ValueError("Tối đa 32 nhiệm vụ")
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Nhiệm vụ không hợp lệ")
        identifier = row.get("id", "")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,48}", identifier) or identifier in seen:
            raise ValueError("Mã nhiệm vụ bị trùng hoặc không hợp lệ")
        seen.add(identifier)
        title = row.get("title", "").strip()
        if not title or len(title) > 64:
            raise ValueError("Tên nhiệm vụ cần từ 1 đến 64 ký tự")
        kind, mob = row.get("kind"), row.get("mob", "*")
        if kind not in {"diamond", "kill"} or not isinstance(mob, str) or not re.fullmatch(r"\*|[a-z0-9_.-]+:[a-z0-9_./-]+", mob):
            raise ValueError("Loại nhiệm vụ hoặc mob không hợp lệ")
        if row.get("mode") not in {"2d", "3d"} or row.get("death_mode", "points") not in {"points", "percent"}:
            raise ValueError("Chế độ hiển thị hoặc trừ tiến độ không hợp lệ")
        if not isinstance(row.get("enabled"), bool) or not isinstance(row.get("summoned_only", False), bool):
            raise ValueError("Cần bật hoặc tắt nhiệm vụ")
        result.append(dict(id=identifier, title=title, kind=kind, mob=mob, enabled=row["enabled"],
            summoned_only=row.get("summoned_only", False), target=number(row.get("target"), 1, 2147483647, True),
            milestones=number(row.get("milestones", 10), 1, 100, True),
            death_penalty=number(row.get("death_penalty", 0), 0, 100 if row.get("death_mode") == "percent" else 2147483647, True),
            death_mode=row.get("death_mode", "points"), mode=row["mode"],
            x=number(row.get("x", 50), 0, 100), y=number(row.get("y", 15), 0, 100),
            scale=number(row.get("scale", 1), .25, 3), reset=number(row.get("reset", 0), 0, 2147483647, True)))
    return {"enabled": data["enabled"], "rules": result}


def path(directory):
    return Path(directory) / "config" / "tiktokmob-missions.json"


def load(directory):
    file = path(directory)
    return validate(json.loads(file.read_text(encoding="utf-8"))) if file.exists() else copy.deepcopy(DEFAULT)


def snapshot(directory):
    with LOCK:
        config = load(directory)
        try:
            progress = json.loads(path(directory).with_name("tiktokmob-missions-state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            progress = {"players": [], "updated": 0}
        return {"config": config, "progress": progress, "online": time.time() * 1000 - progress.get("updated", 0) < 5000}


def save(directory, payload):
    from config_service import save_json
    with LOCK:
        previous = load(directory)
        if payload.get("base") != previous:
            raise ValueError("Nhiệm vụ đã được sửa ở cửa sổ khác. Tải lại tab trước khi lưu.")
        config = validate(payload.get("config"))
        save_json(path(directory), config)
        return {"config": config}
