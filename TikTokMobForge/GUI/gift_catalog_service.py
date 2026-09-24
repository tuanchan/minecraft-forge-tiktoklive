"""Incremental gift sync using the downloader shipped in tooltt."""
from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
import threading
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
TOOL_DIR = ROOT / "tooltt/TikTokGiftDownloader_v2/TikTokGiftDownloader"
ASSET_DIR = ROOT / "web/assets/imagegift"
DISCOVERED = ROOT / "bridge/discovered_gifts.json"


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def image_path(directory, relative):
    if not relative:
        return None
    path = (directory / str(relative)).resolve()
    return path if path.is_relative_to(directory.resolve()) and path.is_file() else None


def catalog():
    merged = {}
    for record in read_json(ASSET_DIR / "gifts.json", {}).get("gifts", []):
        gid = str(record.get("id") or "")
        if not gid:
            continue
        local = image_path(ASSET_DIR, record.get("image_file"))
        merged[gid] = {"gift_id": gid, "name": record.get("name", gid),
                       "diamond_count": int(record.get("diamond_count") or 0),
                       "image_url": record.get("image_url", ""),
                       "asset_image": "/assets/imagegift/" + local.relative_to(ASSET_DIR.resolve()).as_posix()
                       + f"?v={local.stat().st_mtime_ns}" if local else ""}
    for record in read_json(DISCOVERED, []):
        gid = str(record.get("gift_id") or "")
        if gid:
            previous = merged.get(gid, {})
            merged[gid] = {**previous, **{k: v for k, v in record.items() if v not in (None, "")}}
    return sorted(merged.values(), key=lambda g: (int(g.get("diamond_count") or 0), g.get("name", ""), g["gift_id"]))


def load_downloader():
    spec = importlib.util.spec_from_file_location("tiktok_gift_downloader", TOOL_DIR / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GiftCatalogUpdater:
    def __init__(self, log):
        self.log = log
        self.lock = threading.Lock()
        self.status = {"running": False, "message": "Sẵn sàng cập nhật quà và ảnh", "revision": 0}

    def snapshot(self):
        with self.lock:
            return dict(self.status)

    def report(self, message, **values):
        with self.lock:
            self.status.update(message=message, **values)

    def start(self, username):
        with self.lock:
            if self.status["running"]:
                return dict(self.status)
            self.status.update(running=True, error="", current=0, total=0, message="Đang lấy danh sách quà TikTok…")
        threading.Thread(target=self._worker, args=(username,), daemon=True).start()
        return self.snapshot()

    def _worker(self, username):
        try:
            result = asyncio.run(self.sync(username))
            self.report(result, running=False, revision=self.snapshot()["revision"] + 1)
            self.log("INFO", result)
        except Exception as error:
            message = f"Cập nhật quà thất bại: {error}. Kho quà và phần thưởng đã gán vẫn được giữ."
            self.report(message, running=False, error=str(error))
            self.log("ERROR", message)

    async def sync(self, username, *, local_only=False, refresh_ids=()):
        downloader = load_downloader()
        old = read_json(ASSET_DIR / "gifts.json", {})
        records = {str(g["id"]): dict(g) for g in old.get("gifts", []) if g.get("id")}
        refresh_ids = set(refresh_ids)
        if local_only:
            raw = read_json(TOOL_DIR / "output/imagegift/gifts.json", {})
            incoming = raw.get("gifts", [])
            room_id = raw.get("room_id", "")
        else:
            raw, room_id = await downloader.get_room_gift_info(username, self.report)
            incoming, _ = downloader.parse_gifts(raw)
            if not incoming:
                raise ValueError("TikTok trả danh sách trống; chưa cập nhật kho quà")
        for record in incoming:
            gid = str(record["id"])
            previous = records.get(gid, {})
            if previous.get("image_url") and record.get("image_url") and previous["image_url"] != record["image_url"]:
                refresh_ids.add(gid)
            records[gid] = {**previous, **record, "image_file": previous.get("image_file", "")}
        for record in read_json(DISCOVERED, []):
            gid = str(record.get("gift_id") or "")
            if gid and gid not in records:
                records[gid] = {**record, "id": gid, "all_image_urls": [record["image_url"]] if record.get("image_url") else []}
        pending = [dict(g) for g in records.values() if not image_path(ASSET_DIR, g.get("image_file")) or str(g["id"]) in refresh_ids]
        self.report(f"Có {len(records)} quà · cần tải {len(pending)} ảnh", current=0, total=len(pending))
        def progress(current, total, gift):
            self.report(f"Tải ảnh {current}/{total}: {gift['name']}", current=current, total=total)
        await downloader.download_images(pending, ASSET_DIR / "images", progress)
        for record in pending:
            if record.get("image_file"):
                records[str(record["id"])] = record
        gifts = sorted(records.values(), key=lambda g: (int(g.get("diamond_count") or 0), str(g["id"])))
        payload = {"username": username, "room_id": room_id, "count": len(gifts),
                   "updated_at": datetime.now(timezone.utc).isoformat(), "gifts": gifts}
        ASSET_DIR.mkdir(parents=True, exist_ok=True)
        temporary = ASSET_DIR / "gifts.json.tmp"
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(ASSET_DIR / "gifts.json")
        missing = sum(not image_path(ASSET_DIR, g.get("image_file")) for g in gifts)
        return f"Đã cập nhật {len(gifts)} quà ({len(records) - len(old.get('gifts', []))} quà mới), {len(gifts) - missing} ảnh; còn thiếu {missing} ảnh."
