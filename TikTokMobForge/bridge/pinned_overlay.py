"""Atomic pinned-comment handoff shared by the LIVE bridge and desktop WebView."""
import base64
import json
import hashlib
import os
from pathlib import Path
import tempfile
import time

STATE = Path(__file__).resolve().parent / "cache" / "pinned-overlay.json"


def publish(author, text, avatar=b""):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    data = {"author": str(author)[:64], "text": str(text)[:4096],
            "avatar": "data:image/png;base64," + base64.b64encode(avatar).decode() if avatar else "",
            "token": hashlib.sha256((str(author)[:64].strip() + "\n" + str(text)[:200].strip()).encode("utf-8")).hexdigest()[:32],
            "updated": time.time()}
    if data["text"].strip():
        history = STATE.parent / "pinned-history"
        history.mkdir(parents=True, exist_ok=True)
        entry = history / (data["token"] + ".json")
        # Keep each content frame available even if several comments arrive before WebView captures.
        if not entry.exists():
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=history, delete=False) as saved:
                json.dump(data, saved, ensure_ascii=False)
            os.replace(saved.name, entry)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=STATE.parent, delete=False) as out:
            name = out.name
            json.dump(data, out, ensure_ascii=False)
        os.replace(name, STATE)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def snapshot():
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        data["token"] = hashlib.sha256((str(data.get("author", ""))[:64].strip() + "\n" + str(data.get("text", ""))[:200].strip()).encode("utf-8")).hexdigest()[:32]
        data["boards"] = []
        for entry in sorted((STATE.parent / "pinned-history").glob("*.json")):
            try:
                board = json.loads(entry.read_text(encoding="utf-8"))
                if board.get("text") and board.get("token") == entry.stem:
                    data["boards"].append(board)
            except (OSError, ValueError):
                continue
        if data.get("text") and not any(board["token"] == data["token"] for board in data["boards"]):
            data["boards"].append({key: value for key, value in data.items() if key != "boards"})
        return data
    except (OSError, ValueError):
        return {"author": "", "text": "", "avatar": ""}
