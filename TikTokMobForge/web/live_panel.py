"""Display-only panel snapshots shared across independent browser profiles."""
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
import threading

PATH = Path(__file__).resolve().parents[1] / "GUI" / "live-panel.json"
LOCK = threading.Lock()
ALLOWED = {"div", "article", "span", "strong", "small", "b", "img", "p", "progress"}

class PanelMarkup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED:
            return
        clean = []
        for key, value in attrs:
            if key not in {"class", "id", "src", "alt", "title", "data-goal-kind", "data-goal-id", "data-goal-config", "value", "max", "aria-label"} or value is None:
                continue
            if key == "src" and not (value.startswith(("/", "assets/", "https://", "http://")) or re.fullmatch(r"data:image/(?:png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+", value)):
                continue
            clean.append(f' {key}="{html.escape(value, quote=True)}"')
        self.output.append("<" + tag + "".join(clean) + ">")
    def handle_endtag(self, tag):
        if tag in ALLOWED and tag != "img":
            self.output.append("</" + tag + ">")
    def handle_data(self, data):
        self.output.append(html.escape(data))

def publish(data):
    markup = data.get("html", "")
    if not isinstance(markup, str) or len(markup) > 1_000_000:
        raise ValueError("Panel vượt kích thước cho phép")
    parser = PanelMarkup()
    parser.feed(markup)
    appearance = {key: value for key, value in data.get("appearance", {}).items()
                  if re.fullmatch(r"--panel-(text|small|title|mob|gift|event|gap|width|split)", key)
                  and isinstance(value, str) and re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]+)?(?:px|%)", value)}
    width = data.get("width", 1200)
    if not isinstance(width, (int, float)) or not 100 <= width <= 5000:
        raise ValueError("Chiều rộng panel không hợp lệ")
    result = {"html": "".join(parser.output), "appearance": appearance, "width": width}
    result["revision"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    with LOCK:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=PATH.parent, delete=False) as out:
            json.dump(result, out, ensure_ascii=False)
        os.replace(out.name, PATH)
    return {"revision": result["revision"]}

def snapshot():
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"html": "", "appearance": {}, "revision": ""}
