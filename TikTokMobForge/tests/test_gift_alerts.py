"""Gift routing and audio isolation without TikTok or audio-device side effects."""
import asyncio
import contextlib
import io
import json
import queue
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_settings import ROOT, SettingsTests, isolated_settings, web, config, bridge
import gift_alerts
from audio_playback import PLAYBACK_LOCK
from comment_tts import CommentSpeaker


class GiftAlertTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        cache = patch.object(gift_alerts.gift_audio_cache, "CACHE_DIR", Path(folder.name))
        cache.start()
        self.addCleanup(cache.stop)

    def test_reward_precedes_audio_without_waiting_for_hud(self):
        for failure in (False, True):
            order = []
            @contextlib.contextmanager
            def hud(*args):
                order.append("hud")
                if failure:
                    raise ValueError("HUD unavailable")
                yield
            with patch.object(threading.Thread, "start"):
                alerts = gift_alerts.GiftAlerts({}, log=lambda message: None)
            with patch.object(gift_alerts.voicevox_tts, "synthesize", return_value=b"\0\0" * 24), \
                    patch.object(gift_alerts, "minecraft_alert", side_effect=hud), \
                    patch.object(gift_alerts.time, "sleep"), \
                    patch.object(gift_alerts.winsound, "PlaySound", side_effect=lambda *a: order.append("audio")):
                alerts.play({"name": "A", "gift": "Rose", "count": 1,
                             "on_ready": lambda: order.append("reward")})
            self.assertEqual(order, ["reward", "audio"])
            self.assertEqual(alerts.overlays.qsize(), 1)

    def test_gift_settings_roundtrip_preserves_comment_voice(self):
        with isolated_settings() as gui:
            controller = web.Controller()
            controller.save({"gui": gui, "bridge": {"tts_provider": "edge", "tts_volume": 0.3}})
            controller.save({"bridge": {"gift_voicevox_volume": 0.7, "gift_overlay_x": 90,
                                       "gift_overlay_width": 400, "gift_voicevox_enabled": False}})
            saved = controller.state()["bridge"]
            self.assertEqual(saved["tts_provider"], "edge")
            self.assertEqual(saved["tts_volume"], 0.3)
            self.assertEqual(saved["gift_voicevox_volume"], 0.7)
            self.assertEqual(saved["gift_overlay_x"], 90)
            self.assertEqual(saved["gift_overlay_width"], 400)
            self.assertFalse(saved["gift_voicevox_enabled"])
            for key, value in (("gift_overlay_x", 101), ("gift_overlay_duration_seconds", 0),
                               ("gift_voicevox_volume", 2), ("gift_overlay_width", 300.5),
                               ("gift_alert_queue_size", 0), ("gift_overlay_enabled", "false"),
                               ("tts_provider", "voicevox")):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    controller.save({"bridge": {key: value}})

    def test_legacy_comment_voice_migrates_without_losing_voicevox_tuning(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"tts_provider": "voicevox", "tts_voicevox_pitch": 0.06}), encoding="utf-8")
            saved = config.load_json(path, config.DEFAULT_BRIDGE_CONFIG)
            self.assertEqual(saved["tts_provider"], "elevenlabs")
            self.assertEqual(saved["tts_voicevox_pitch"], 0.06)
            with patch.object(bridge, "CONFIG_PATH", path):
                self.assertEqual(bridge.load_config()["tts_provider"], "elevenlabs")

    def test_avatar_uses_tiktok_thumbnail_and_falls_back(self):
        url = "https://example.com/avatar.jpg"
        self.assertEqual(gift_alerts.avatar_url(SimpleNamespace(avatar_thumb=SimpleNamespace(url_list=[url]))), url)
        self.assertEqual(gift_alerts.avatar_url(SimpleNamespace(avatar_medium={"url_list": [url]})), url)
        self.assertEqual(gift_alerts.avatar_url(None), "")
        self.assertEqual(gift_alerts.avatar_url(SimpleNamespace(avatar="javascript:alert(1)")), "")

    def test_only_completed_combos_enqueue_with_avatar_and_unmapped_gifts(self):
        import TikTokLive
        handlers = {}
        user = SimpleNamespace(unique_id="alice", nickname="Alice", avatar_thumb=SimpleNamespace(url_list=["https://example.com/a.jpg"]))
        event = SimpleNamespace(user=user, gift_id=99, gift=SimpleNamespace(name="Rose", diamond_count=1), repeat_count=3, streaking=True)
        class Client:
            def __init__(self, **_): pass
            def on(self, kind):
                def add(handler): handlers[kind.__name__] = handler; return handler
                return add
            def run(self):
                async def run():
                    await handlers["GiftEvent"](event)
                    event.streaking = False
                    await handlers["GiftEvent"](event)
                    await handlers["CommentEvent"](SimpleNamespace(user=user, comment="Bình luận bình thường"))
                asyncio.run(run())
        with patch.object(TikTokLive, "TikTokLiveClient", Client), patch("gift_alerts.GiftAlerts") as alerts, \
             patch("comment_tts.create_comment_speaker") as comments, patch.object(bridge, "send_interaction") as send, \
             patch.object(bridge, "observed_gift", return_value=None):
            alerts.return_value.enqueue.side_effect = lambda *a, **kw: kw["on_ready"]()
            bridge.run_live({**config.DEFAULT_BRIDGE_CONFIG, "gift_actions": []})
            self.assertEqual(alerts.return_value.enqueue.call_args.args, ("Alice", "Rose", 3, "https://example.com/a.jpg"))
            comments.return_value.enqueue.assert_called_once_with("Alice", "Bình luận bình thường")
            self.assertEqual(send.call_count, 2)

    def test_fifo_overflow_and_disabled(self):
        with patch.object(threading.Thread, "start"):
            alerts = gift_alerts.GiftAlerts({"gift_alert_queue_size": 2})
        for name in ("A", "B", "C"):
            alerts.enqueue(name, "Rose", 1)
        self.assertEqual([alerts.pending.get_nowait()["name"] for _ in range(2)], ["A", "B"])
        alerts.config.update(gift_voicevox_enabled=False, gift_overlay_enabled=False)
        alerts.enqueue("D", "Rose", 1)
        self.assertTrue(alerts.pending.empty())

    def test_gift_speaks_fixed_phrase_with_independent_volume(self):
        with patch.object(threading.Thread, "start"):
            alerts = gift_alerts.GiftAlerts({"tts_enabled": False, "tts_provider": "edge", "tts_volume": 1,
                "gift_overlay_enabled": False, "gift_voicevox_volume": 0.5})
            comments = CommentSpeaker(None, "", {})
        self.assertIs(comments._playback_lock, PLAYBACK_LOCK)
        with patch.object(gift_alerts.voicevox_tts, "synthesize", return_value=b"\x10\x00" * 240) as synth, \
             patch.object(gift_alerts.winsound, "PlaySound") as play:
            self.assertTrue(alerts.play({"name": "Alice", "gift": "Rose", "count": 2}))
            synth.assert_called_once_with(alerts.config, gift_alerts.THANKS_TEXT)
            self.assertIn(b"\x08\x00" * 240, play.call_args.args[0])
            self.assertTrue(alerts.play({"name": "Bob", "gift": "Rose", "count": 1}))
            self.assertEqual(synth.call_count, 1, "fixed phrase should be cached for later gifts")

    def test_engine_failure_still_shows_gif(self):
        with patch.object(threading.Thread, "start"):
            alerts = gift_alerts.GiftAlerts({})
        with patch.object(gift_alerts.voicevox_tts, "synthesize", side_effect=ValueError("Engine unavailable")), \
             patch.object(gift_alerts, "minecraft_alert", return_value=contextlib.nullcontext()) as launch, \
             patch.object(gift_alerts.time, "sleep"), \
             patch.object(gift_alerts.winsound, "PlaySound") as play:
            self.assertFalse(alerts.play({"name": "Alice", "gift": "Rose", "count": 1}))
            launch.assert_not_called()
            self.assertEqual(alerts.overlays.qsize(), 1)
            play.assert_not_called()

    def test_gift_audio_waits_for_current_comment(self):
        with patch.object(threading.Thread, "start"):
            alerts = gift_alerts.GiftAlerts({"gift_overlay_enabled": False})
        started = threading.Event()
        played = threading.Event()
        def synth(*args): started.set(); return b"\0\0" * 24
        with patch.object(gift_alerts.voicevox_tts, "synthesize", side_effect=synth), \
             patch.object(gift_alerts.winsound, "PlaySound", side_effect=lambda *a: played.set()):
            with PLAYBACK_LOCK:
                worker = threading.Thread(target=alerts.play, args=({"name": "A", "gift": "R", "count": 1},))
                worker.start()
                self.assertTrue(started.wait(2))
                self.assertFalse(played.wait(0.1))
            worker.join(2)
            self.assertTrue(played.is_set())


if __name__ == "__main__":
    unittest.main()
