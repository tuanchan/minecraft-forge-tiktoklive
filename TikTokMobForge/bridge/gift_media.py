"""Gift phrase selection, transparent vertical artwork and local Minecraft exchange."""
from contextlib import contextmanager
import json
import io
import os
from pathlib import Path
import random
import shutil
import time
import uuid
import urllib.request


GIF_DIR = Path(__file__).resolve().parents[1] / "web/assets/GIF"
EXCHANGE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "TikTokMobForge/gift-alerts"
PHRASES = [
    {"id": "onichan", "name": "Thank you, onii-chan!", "text": "サンキュー、お兄ちゃーん！", "label": "THANKIU ONICHANN~~"},
    {"id": "arigatou", "name": "Cảm ơn anh nhiều!", "text": "お兄ちゃん、ありがとう！", "label": "お兄ちゃん、ありがとう！"},
    {"id": "gift", "name": "Cảm ơn món quà!", "text": "素敵なプレゼント、ありがとう！", "label": "素敵なプレゼント、ありがとう！"},
    {"id": "happy", "name": "Vui quá! Cảm ơn nhé!", "text": "わあ、うれしい！ありがとう！", "label": "わあ、うれしい！ありがとう！"},
    {"id": "support", "name": "Cảm ơn vì luôn ủng hộ!", "text": "いつも応援してくれて、ありがとう！", "label": "いつも応援してくれて、ありがとう！"},
    {"id": "daisuki", "name": "Yêu anh nhất!", "text": "お兄ちゃん、大好き！ありがとう！", "label": "お兄ちゃん、大好き！ありがとう！"},
    {"id": "yay", "name": "Yay! Cảm ơn nhiều lắm!", "text": "やったー！本当にありがとう！", "label": "やったー！本当にありがとう！"},
]


def catalog():
    return {"phrases": PHRASES, "gifs": [p.name for p in sorted(GIF_DIR.iterdir())
            if p.is_file() and p.suffix.lower() == ".gif"]}


def select_phrase(config):
    mode = config.get("gift_phrase_mode", "fixed")
    if mode == "random":
        return dict(random.choice(PHRASES))
    if mode == "custom":
        text = str(config.get("gift_phrase_custom", "")).strip()
        if not text:
            raise ValueError("Nhập câu cảm ơn tiếng Nhật trước khi chọn Tự nhập.")
        return {"id": "custom", "text": text, "label": text}
    return dict(next((p for p in PHRASES if p["id"] == config.get("gift_phrase_id", "onichan")), PHRASES[0]))


def select_gif(config):
    names = catalog()["gifs"]
    if not names:
        raise ValueError("Thư mục web/assets/GIF chưa có GIF.")
    name = random.choice(names) if config.get("gift_gif_random", True) else config.get("gift_gif_file", "kawaiianimegirlGIF.gif")
    if name not in names:
        raise ValueError("GIF đã chọn không còn trong thư mục. Bấm Nạp lại GIF.")
    return GIF_DIR / name


def render_frames(event, gif_path, width=320):
    """No backing panel. Avatar and all text centered below the original GIF."""
    from PIL import Image, ImageDraw, ImageFont, ImageSequence
    font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    japanese_font = next((p for name in ("YuGothB.ttc", "meiryo.ttc", "msgothic.ttc", "malgun.ttf")
                          if (p := font_dir / name).is_file()), font_dir / "segoeuib.ttf")
    avatar_size = 64
    avatar = load_avatar(event.get("avatar", ""), avatar_size)
    frames, delays = [], []
    with Image.open(gif_path) as source:
        if source.n_frames > 300:
            raise ValueError("GIF quá dài (tối đa 300 khung hình).")
        for frame in ImageSequence.Iterator(source):
            gif = frame.convert("RGBA")
            gif.thumbnail((width, width))
            image = Image.new("RGBA", (width, gif.height + 166), (0, 0, 0, 0))
            image.alpha_composite(gif, ((width - gif.width) // 2, 0))
            draw = ImageDraw.Draw(image)
            ay = gif.height + 8
            ax = (width - avatar_size) // 2
            if avatar:
                image.alpha_composite(avatar, (ax, ay))
            else:
                draw.ellipse((ax, ay, ax + avatar_size, ay + avatar_size), fill="#765280")
                font = ImageFont.truetype(str(font_dir / "segoeuib.ttf"), 26)
                draw.text((width // 2, ay + 32), str(event.get("name", "T"))[:1], anchor="mm", fill="white", font=font)
            def centered(text, y, color, japanese=False):
                size = 18
                filename = japanese_font if japanese else font_dir / "segoeuib.ttf"
                font = ImageFont.truetype(str(filename), size)
                while font.getlength(text) > width - 12 and size > 10:
                    size -= 1
                    font = ImageFont.truetype(str(filename), size)
                # Wrap long custom phrases instead of clipping outside the HUD.
                lines, line = [], ""
                for char in text:
                    if line and font.getlength(line + char) > width - 12:
                        lines.append(line); line = ""
                    line += char
                lines.append(line)
                for index, line in enumerate(lines[:2]):
                    draw.text((width // 2, y + index * 17), line, anchor="mt", fill=color,
                              font=font, stroke_width=1, stroke_fill="#000000")
            centered(str(event["name"])[:64], ay + 72, "#ffd685")
            centered(f"{event['gift']} ×{event['count']}", ay + 96, "#ffd685")
            centered(event["label"], ay + 122, "#ffb0e4", True)
            frames.append(image)
            delays.append(max(20, int(frame.info.get("duration", 80))))
    return frames, delays


def load_avatar(url, size):
    from PIL import Image, ImageDraw, ImageOps
    if not str(url).startswith("https://"):
        return None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "TikTokMobForge/1.0"})
        with urllib.request.urlopen(request, timeout=3) as response:
            data = response.read(4 * 1024 * 1024 + 1)
        if len(data) > 4 * 1024 * 1024:
            return None
        with Image.open(io.BytesIO(data)) as source:
            avatar = ImageOps.fit(source.convert("RGBA"), (size, size))
        mask = Image.new("L", (size, size))
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        avatar.putalpha(mask)
        return avatar
    except Exception as error:
        print(f"Avatar TikTok không tải được: {error}")
        return None


def wait_for_hud_marker(directory, marker, timeout):
    """A fresh Minecraft heartbeat pauses the timeout while waiting for respawn."""
    deadline = time.monotonic() + timeout
    while not (directory / marker).exists():
        if (directory / "error").exists():
            raise ValueError((directory / "error").read_text(encoding="utf-8"))
        try:
            paused = time.time() - (directory / "paused").stat().st_mtime < 3
        except FileNotFoundError:
            paused = False
        if paused:
            deadline = time.monotonic() + timeout
        if time.monotonic() >= deadline:
            raise ValueError("Minecraft chưa hiện/hoàn tất GIF. Kiểm tra world, mod và HUD (F1).")
        time.sleep(0.05)


@contextmanager
def minecraft_alert(config, event, gif_path, duration):
    from bridge import send_interaction
    token = uuid.uuid4().hex
    directory = EXCHANGE / token
    directory.mkdir(parents=True)
    try:
        frames, delays = render_frames(event, gif_path)
        for index, frame in enumerate(frames):
            frame.save(directory / f"{index}.png")
        manifest = {"width": frames[0].width, "height": frames[0].height, "delays": delays,
                    "duration": duration, "display_width": config.get("gift_overlay_width", 320),
                    "x": config.get("gift_overlay_x", 50), "y": config.get("gift_overlay_y", 45)}
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        send_interaction(config, "gift_alert", event["name"], "gift-alert", "", token, True)
        wait_for_hud_marker(directory, "ready", 15)
        print(f"GIFT Minecraft đã hiện GIF: {gif_path.name} — {event['name']}")
        yield directory
    finally:
        # Only this UUID directory belongs to this event. A stopped bridge never
        # asks Minecraft to keep rendering: the client also checks this manifest.
        shutil.rmtree(directory, ignore_errors=True)
