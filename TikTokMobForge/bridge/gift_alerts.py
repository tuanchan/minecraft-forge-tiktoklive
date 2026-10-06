"""Deliver rewards immediately; independent cached speech and HUD queues."""
import queue
import threading
import time
import winsound

from audio_playback import PLAYBACK_LOCK
from comment_tts import CommentSpeaker
import voicevox_tts  # Kept for existing integrations that patch the engine adapter.
import gift_audio_cache
from gift_media import select_phrase, select_gif, minecraft_alert, wait_for_hud_marker

THANKS_LABEL = "THANKIU ONICHANN~~"
# Japanese phonetics for the requested phrase; VOICEVOX is a Japanese engine.
THANKS_TEXT = "サンキュー、お兄ちゃーん！"


def avatar_url(user) -> str:
    for field in ("avatar_large", "avatar_medium", "avatar", "avatar_thumb"):
        image = getattr(user, field, None)
        urls = image.get("url_list", []) if isinstance(image, dict) else getattr(image, "url_list", [])
        candidates = [image] if isinstance(image, str) else list(urls or [])
        for url in candidates:
            if isinstance(url, str) and url.startswith("https://"):
                return url
    return ""


class GiftAlerts:
    def __init__(self, config: dict, log=print):
        self.log = log
        self.config = config
        self._cached_pcm = {}
        self.pending = queue.Queue(maxsize=int(config.get("gift_alert_queue_size", 200)))
        self.overlays = queue.Queue(maxsize=int(config.get("gift_alert_queue_size", 200)))
        self._cache_lock = threading.Lock()
        threading.Thread(target=self._warm_cache, name="gift-cache", daemon=True).start()
        threading.Thread(target=self._run, name="gift-thanks", daemon=True).start()
        threading.Thread(target=self._run_overlays, name="gift-hud", daemon=True).start()

    def _run_overlays(self):
        while True:
            event = self.overlays.get()
            try:
                if event is None:
                    return
                duration = float(self.config.get("gift_overlay_duration_seconds", 5))
                with minecraft_alert(self.config, event, select_gif(self.config), duration) as directory:
                    wait_for_hud_marker(directory, "finished", duration + 15)
            except Exception as error:
                self.log(f"GIFT không hiện được HUD: {error}")
            finally:
                self.overlays.task_done()

    def _audio(self, text):
        with self._cache_lock:
            if text not in self._cached_pcm:
                self._cached_pcm[text] = gift_audio_cache.synthesize(self.config, text)
            return self._cached_pcm[text]

    def _warm_cache(self):
        if not self.config.get("gift_voicevox_enabled", True):
            return
        from gift_media import PHRASES
        try:
            phrases = PHRASES if self.config.get("gift_phrase_mode") == "random" else [select_phrase(self.config)]
            for phrase in phrases:
                if not self.config.get("gift_voicevox_enabled", True):
                    break
                self._audio(phrase["text"])
        except Exception as error:
            self.log(f"GIFT chưa chuẩn bị được cache cảm ơn: {error}")

    def close(self, discard_pending=False):
        if discard_pending:
            while True:
                try:
                    self.pending.get_nowait()
                    self.pending.task_done()
                except queue.Empty:
                    break
        self.pending.put(None)
        self.overlays.put(None)

    def enqueue(self, name, gift, count, avatar="", on_ready=None):
        if on_ready:
            on_ready()
            on_ready = None
        if not (self.config.get("gift_voicevox_enabled", True) or self.config.get("gift_overlay_enabled", True)):
            return
        try:
            self.pending.put_nowait({"name": str(name)[:100], "gift": str(gift)[:100],
                                     "count": int(count), "avatar": avatar, "on_ready": on_ready})
            self.log(f"GIFT cảm ơn đã xếp hàng: {name}, {gift} x{count}")
        except queue.Full:
            self.log(f"GIFT hàng cảm ơn đầy, bỏ hiển thị của {name}; phần thưởng vẫn xử lý.")

    def _run(self):
        while True:
            event = self.pending.get()
            try:
                if event is None:
                    return
                self.play(event)
            except Exception as error:
                self.log(f"GIFT lỗi cảm ơn: {error}")
            finally:
                self.pending.task_done()

    def play(self, event):
        if event.get("on_ready"):
            event["on_ready"]()
            event = {**event, "on_ready": None}
        phrase = select_phrase(self.config)
        event = {**event, "label": phrase["label"]}
        if self.config.get("gift_overlay_enabled", True) and not self.config.get("live_comments_only", False):
            try:
                self.overlays.put_nowait(event)
            except queue.Full:
                self.log("GIFT hàng HUD đầy; vẫn đọc cảm ơn và giao thưởng.")
        pcm = b""
        success = True
        if self.config.get("gift_voicevox_enabled", True):
            try:
                text = phrase["text"]
                pcm = CommentSpeaker._scale_volume(self._audio(text), float(self.config.get("gift_voicevox_volume", 1)))
            except Exception as error:
                success = False
                self.log(f"GIFT VOICEVOX không đọc được; vẫn hiện quà: {error}")
        self.log(f"GIFT câu cảm ơn: {phrase['text']}")
        with PLAYBACK_LOCK:
            try:
                if pcm:
                    winsound.PlaySound(CommentSpeaker._to_wav(pcm),
                        winsound.SND_MEMORY | winsound.SND_NODEFAULT | winsound.SND_SYNC)
                self.log(f"GIFT đã xử lý cảm ơn: {event['name']} — {event['gift']} x{event['count']}")
            except Exception as error:
                self.log(f"GIFT không phát được âm thanh: {error}")
                success = False
        return success
