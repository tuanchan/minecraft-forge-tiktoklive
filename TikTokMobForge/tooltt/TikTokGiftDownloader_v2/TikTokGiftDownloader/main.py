
import asyncio
import copy
import csv
import json
import io
from PIL import Image
import os
import re
import threading
import traceback
from pathlib import Path
from urllib.parse import urlparse

import httpx
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from TikTokLive import TikTokLiveClient


APP_TITLE = "TikTok LIVE Gift Downloader"


def safe_filename(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", str(value or "").strip())
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:120] or "unknown"


def scalar(value):
    return isinstance(value, (str, int, float, bool)) or value is None


def normalize_obj(obj):
    """Convert protobuf/model-like objects to plain Python structures when possible."""
    if obj is None:
        return None

    if isinstance(obj, dict):
        return {str(k): normalize_obj(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [normalize_obj(x) for x in obj]

    # Pydantic v2
    if hasattr(obj, "model_dump"):
        try:
            return normalize_obj(obj.model_dump())
        except Exception:
            pass

    # Pydantic v1
    if hasattr(obj, "dict"):
        try:
            return normalize_obj(obj.dict())
        except Exception:
            pass

    # Protobuf
    if hasattr(obj, "ListFields"):
        try:
            out = {}
            for field, value in obj.ListFields():
                out[field.name] = normalize_obj(value)
            return out
        except Exception:
            pass

    if scalar(obj):
        return obj

    # Last resort: public attributes only
    try:
        data = {}
        for name in dir(obj):
            if name.startswith("_"):
                continue
            try:
                value = getattr(obj, name)
            except Exception:
                continue
            if callable(value):
                continue
            if scalar(value) or isinstance(value, (dict, list, tuple, set)):
                data[name] = normalize_obj(value)
        if data:
            return data
    except Exception:
        pass

    return str(obj)


def first_value(d: dict, keys):
    for key in keys:
        if key in d and d[key] not in (None, "", [], {}):
            return d[key]
    return None


def find_urls(value):
    urls = []

    def walk(x):
        if isinstance(x, str):
            if x.startswith("http://") or x.startswith("https://"):
                urls.append(x)
        elif isinstance(x, dict):
            # Favor URL-ish fields, but recurse everything for compatibility.
            priority = [
                "url_list", "urlList", "url_list_list", "urlListList",
                "icon_url", "iconUrl", "image_url", "imageUrl", "url"
            ]
            for k in priority:
                if k in x:
                    walk(x[k])
            for k, v in x.items():
                if k not in priority:
                    walk(v)
        elif isinstance(x, (list, tuple, set)):
            for item in x:
                walk(item)

    walk(value)

    seen = set()
    result = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


def looks_like_gift(d: dict) -> bool:
    if not isinstance(d, dict):
        return False

    gift_id = first_value(d, ["id", "gift_id", "giftId"])
    name = first_value(d, ["name", "gift_name", "giftName"])

    if gift_id is None or name is None:
        return False

    keys = set(d.keys())
    gift_signals = {
        "diamond_count", "diamondCount", "coin_price", "coinPrice",
        "image", "icon", "icon_url", "iconUrl", "image_url", "imageUrl",
        "type", "combo", "streakable", "is_displayed_on_panel",
        "primary_effect_id", "describe"
    }
    return bool(keys & gift_signals)


def collect_gift_nodes(data):
    found = []

    def walk(x):
        if isinstance(x, dict):
            if looks_like_gift(x):
                found.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(data)
    return found


def parse_gifts(raw_data):
    data = normalize_obj(raw_data)
    nodes = collect_gift_nodes(data)

    gifts_by_id = {}

    for g in nodes:
        gift_id = str(first_value(g, ["id", "gift_id", "giftId"]))
        name = str(first_value(g, ["name", "gift_name", "giftName"]))

        diamond_count = first_value(
            g, ["diamond_count", "diamondCount", "coin_price", "coinPrice", "price"]
        )
        gift_type = first_value(g, ["type", "gift_type", "giftType"])
        combo = first_value(g, ["combo", "streakable"])

        # Prefer image/icon subtree instead of any unrelated URLs inside the gift.
        image_source = first_value(
            g, ["image", "icon", "icon_url", "iconUrl", "image_url", "imageUrl"]
        )
        urls = find_urls(image_source)
        if not urls:
            urls = find_urls(g)

        record = {
            "id": gift_id,
            "name": name,
            "diamond_count": diamond_count,
            "type": gift_type,
            "combo": combo,
            "image_url": urls[0] if urls else "",
            "all_image_urls": urls,
        }

        old = gifts_by_id.get(gift_id)
        if old is None:
            gifts_by_id[gift_id] = record
        else:
            # Keep the richer duplicate.
            score_old = sum(bool(old.get(k)) for k in ("name", "diamond_count", "image_url"))
            score_new = sum(bool(record.get(k)) for k in ("name", "diamond_count", "image_url"))
            if score_new > score_old:
                gifts_by_id[gift_id] = record

    gifts = list(gifts_by_id.values())

    def sort_key(x):
        try:
            price = int(x["diamond_count"])
        except Exception:
            price = 10**12
        try:
            gid = int(x["id"])
        except Exception:
            gid = 10**12
        return (price, gid, x["name"].lower())

    gifts.sort(key=sort_key)
    return gifts, data


async def get_room_gift_info(username: str, on_status=None):
    username = username.strip()
    if not username:
        raise ValueError("Chưa nhập TikTok username.")
    if not username.startswith("@"):
        username = "@" + username

    client = TikTokLiveClient(unique_id=username)

    try:
        # Không mở WebSocket vì chỉ cần gift catalog. Cách cũ có thể đứng ở
        # is_live()/client.start() khi TikTok chặn hoặc endpoint phản hồi chậm.
        if on_status:
            on_status("Đang lấy Room ID...")

        room_id = None
        html_error = None
        try:
            room_id = await asyncio.wait_for(
                client.web.fetch_room_id_from_html(client.unique_id),
                timeout=12,
            )
        except Exception as ex:
            html_error = ex

        if not room_id:
            if on_status:
                on_status("HTML không trả Room ID, đang thử API dự phòng...")
            try:
                room_id = await asyncio.wait_for(
                    client.web.fetch_room_id_from_api(client.unique_id),
                    timeout=12,
                )
            except asyncio.TimeoutError:
                raise RuntimeError("TikTok phản hồi quá chậm khi lấy Room ID (>12 giây).")
            except Exception as ex:
                raise RuntimeError(
                    f"Không lấy được Room ID của {username}. "
                    f"HTML: {html_error}; API: {ex}"
                )

        client.web.params["room_id"] = str(room_id)

        if on_status:
            on_status(f"Room ID {room_id} - đang lấy danh sách quà...")

        try:
            gift_info = await asyncio.wait_for(
                client.web.fetch_gift_list(),
                timeout=20,
            )
        except asyncio.TimeoutError:
            raise RuntimeError("TikTok phản hồi quá chậm khi lấy danh sách quà (>20 giây).")

        if not gift_info:
            raise RuntimeError("TikTok không trả về danh sách quà cho phòng này.")

        return copy.deepcopy(gift_info), str(room_id)
    finally:
        try:
            await client.web.close()
        except Exception:
            pass


def guess_extension(url: str, content_type: str) -> str:
    path = urlparse(url).path.lower()
    for ext in (".webp", ".png", ".jpg", ".jpeg", ".gif", ".avif"):
        if path.endswith(ext):
            return ext

    content_type = (content_type or "").lower()
    mapping = {
        "image/webp": ".webp",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/avif": ".avif",
    }
    return mapping.get(content_type.split(";")[0], ".webp")


async def download_images(gifts, images_dir: Path, progress=None):
    images_dir.mkdir(parents=True, exist_ok=True)

    timeout = httpx.Timeout(30.0)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/152 Safari/537.36"
        ),
        "Referer": "https://www.tiktok.com/",
    }

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
        http2=False,
    ) as http:
        for index, gift in enumerate(gifts, 1):
            gift["image_file"] = ""
            urls = gift.get("all_image_urls") or []
            if not urls and gift.get("image_url"):
                urls = [gift["image_url"]]

            for url in urls:
                try:
                    r = await http.get(url)
                    if r.status_code != 200 or not r.content:
                        continue

                    if len(r.content) > 10 * 1024 * 1024:
                        continue
                    with Image.open(io.BytesIO(r.content)) as decoded:
                        decoded.verify()
                    ext = guess_extension(url, r.headers.get("content-type", ""))
                    filename = f'{gift["id"]}_{safe_filename(gift["name"])}{ext}'
                    path = images_dir / filename
                    temporary = path.with_suffix(path.suffix + ".tmp")
                    temporary.write_bytes(r.content)
                    temporary.replace(path)
                    gift["image_file"] = f"images/{filename}"
                    gift["image_url"] = url
                    break
                except Exception:
                    continue

            if progress:
                progress(index, len(gifts), gift)


def write_outputs(base_dir: Path, username: str, room_id: str, gifts, raw_data):
    base_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "username": username.lstrip("@"),
        "room_id": room_id,
        "count": len(gifts),
        "gifts": gifts,
    }

    (base_dir / "gifts.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (base_dir / "gifts.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id", "name", "diamond_count", "type", "combo",
                "image_file", "image_url"
            ],
        )
        writer.writeheader()
        for gift in gifts:
            writer.writerow({
                "id": gift.get("id", ""),
                "name": gift.get("name", ""),
                "diamond_count": gift.get("diamond_count", ""),
                "type": gift.get("type", ""),
                "combo": gift.get("combo", ""),
                "image_file": gift.get("image_file", ""),
                "image_url": gift.get("image_url", ""),
            })

    (base_dir / "raw_gift_info.json").write_text(
        json.dumps(normalize_obj(raw_data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def run_download(username, output_dir, on_status, on_progress):
    on_status("Đang kết nối TikTok LIVE...")
    raw_data, room_id = await get_room_gift_info(username, on_status)

    gifts, normalized = parse_gifts(raw_data)
    if not gifts:
        # Save raw payload to help diagnose future schema changes.
        debug_dir = Path(output_dir) / safe_filename(username.lstrip("@"))
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / "raw_gift_info.json").write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        raise RuntimeError(
            "Đã nhận gift_info nhưng chưa parse được gift. "
            "File raw_gift_info.json đã được lưu."
        )

    account_dir = Path(output_dir) / safe_filename(username.lstrip("@"))
    images_dir = account_dir / "images"

    on_status(f"Tìm thấy {len(gifts)} quà. Đang tải ảnh...")
    await download_images(gifts, images_dir, on_progress)

    write_outputs(account_dir, username, room_id, gifts, raw_data)

    ok_images = sum(1 for x in gifts if x.get("image_file"))
    on_status(f"Xong: {len(gifts)} quà, tải được {ok_images} ảnh.")
    return account_dir, len(gifts), ok_images


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("700x420")
        self.minsize(700, 420)

        self.username = tk.StringVar(value="_deadchan")
        self.output = tk.StringVar(value=str(Path.cwd() / "output"))
        self.status = tk.StringVar(value="Sẵn sàng.")
        self.progress_text = tk.StringVar(value="0 / 0")

        self._build()

    def _build(self):
        pad = {"padx": 12, "pady": 8}

        title = ttk.Label(self, text="TikTok LIVE Gift Downloader", font=("Segoe UI", 18, "bold"))
        title.pack(pady=(20, 10))

        form = ttk.Frame(self)
        form.pack(fill="x", padx=28)

        ttk.Label(form, text="TikTok username đang LIVE:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(form, textvariable=self.username, width=42).grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(form, text="Thư mục lưu:").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(form, textvariable=self.output).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(form, text="Chọn...", command=self.choose_output).grid(row=1, column=2, **pad)

        form.columnconfigure(1, weight=1)

        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=40, pady=(25, 4))

        ttk.Label(self, textvariable=self.progress_text).pack()
        ttk.Label(self, textvariable=self.status, wraplength=640).pack(pady=12)

        self.btn = ttk.Button(self, text="TẢI TOÀN BỘ QUÀ", command=self.start_download)
        self.btn.pack(pady=8, ipadx=18, ipady=6)

        ttk.Label(
            self,
            text="Kết quả: images/ + gifts.json + gifts.csv + raw_gift_info.json",
        ).pack(pady=(8, 0))

    def choose_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output.set(path)

    def set_status(self, text):
        self.after(0, lambda: self.status.set(text))

    def set_progress(self, current, total, gift):
        def update():
            percent = (current / total * 100) if total else 0
            self.progress["value"] = percent
            self.progress_text.set(
                f'{current} / {total}  |  {gift.get("id")} - {gift.get("name")}'
            )
        self.after(0, update)

    def start_download(self):
        username = self.username.get().strip()
        output = self.output.get().strip()

        if not username:
            messagebox.showerror(APP_TITLE, "Nhập TikTok username.")
            return
        if not output:
            messagebox.showerror(APP_TITLE, "Chọn thư mục lưu.")
            return

        self.btn.config(state="disabled")
        self.progress["value"] = 0
        self.progress_text.set("0 / 0")
        self.status.set("Đang bắt đầu...")

        threading.Thread(
            target=self.worker,
            args=(username, output),
            daemon=True,
        ).start()

    def worker(self, username, output):
        try:
            result_dir, gift_count, image_count = asyncio.run(
                run_download(
                    username,
                    output,
                    self.set_status,
                    self.set_progress,
                )
            )
            self.after(
                0,
                lambda: messagebox.showinfo(
                    APP_TITLE,
                    f"Hoàn tất!\n\nQuà: {gift_count}\nẢnh: {image_count}\n\n{result_dir}",
                ),
            )
        except Exception as e:
            traceback.print_exc()
            self.set_status(f"Lỗi: {e}")
            self.after(
                0,
                lambda err=str(e): messagebox.showerror(APP_TITLE, err),
            )
        finally:
            self.after(0, lambda: self.btn.config(state="normal"))


if __name__ == "__main__":
    App().mainloop()
