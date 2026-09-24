import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from test_settings import bridge, config, isolated_settings, web
import gift_alerts
import gift_audio_cache as cache


class FastGiftTests(unittest.TestCase):
    def test_mp4_survives_restart_and_voice_changes_invalidate_cache(self):
        pcm = b"\x10\x00" * 2400
        with tempfile.TemporaryDirectory() as folder, patch.object(cache, "CACHE_DIR", Path(folder)), \
                patch.object(cache.voicevox_tts, "synthesize", return_value=pcm) as engine:
            self.assertEqual(cache.synthesize({}, "thank you"), pcm)
            engine.assert_called_once()
            self.assertEqual(len(list(Path(folder).glob("*.mp4"))), 1)
            self.assertEqual(cache.synthesize({}, "thank you"), pcm)
            self.assertEqual(engine.call_count, 1)
            cache.synthesize({"tts_voicevox_pitch": 0.1}, "thank you")
            self.assertEqual(engine.call_count, 2)
            next(Path(folder).glob("*.mp4")).write_bytes(b"broken")
            cache.synthesize({}, "thank you")

    def test_disabled_gifts_do_not_start_engine_or_prepare_audio(self):
        with patch.object(threading.Thread, "start"), patch.object(cache, "synthesize") as engine:
            alerts = gift_alerts.GiftAlerts({"gift_voicevox_enabled": False, "gift_overlay_enabled": False})
            alerts._warm_cache()
            reward = Mock()
            alerts.enqueue("A", "Rose", 1, on_ready=reward)
            reward.assert_called_once()
            engine.assert_not_called()
            self.assertTrue(alerts.pending.empty())

    def test_rewards_do_not_wait_for_full_audio_queue(self):
        with patch.object(threading.Thread, "start"):
            alerts = gift_alerts.GiftAlerts({"gift_alert_queue_size": 1})
        reward = Mock()
        alerts.enqueue("A", "Rose", 1, on_ready=reward)
        alerts.enqueue("B", "Rose", 1, on_ready=reward)
        self.assertEqual(reward.call_count, 2)
        self.assertIsNone(alerts.pending.get_nowait()["on_ready"])

    def test_comments_only_never_opens_minecraft_socket(self):
        with patch.object(bridge.socket, "create_connection", side_effect=AssertionError("Minecraft used")):
            bridge.send_interaction({"live_comments_only": True}, "mob", "Alice")

    def test_settings_roundtrip(self):
        with isolated_settings() as gui:
            controller = web.Controller()
            for direction in ("front", "right", "left", "back", "random"):
                controller.save({"gui": gui, "mod": {"spawn_direction": direction},
                                 "bridge": {"live_comments_only": True}})
                self.assertEqual(controller.state()["mod"]["spawn_direction"], direction)
                self.assertTrue(controller.state()["bridge"]["live_comments_only"])
            with self.assertRaises(ValueError):
                controller.save({"mod": {"spawn_direction": "invalid"}})
