"""Offline checks; no TikTok, ElevenLabs, or active Minecraft writes."""
import asyncio
import contextlib
import io
import json
from array import array
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "web"), str(ROOT / "bridge"), str(ROOT / "GUI")]
import main as web
import bridge
import comment_tts
import config_service as config


@contextlib.contextmanager
def isolated_settings():
    with tempfile.TemporaryDirectory(prefix="tiktok-settings-") as directory, contextlib.ExitStack() as stack:
        root = Path(directory)
        gui = {"minecraft_directory": str(root / "minecraft"), "keep_minecraft_running_in_background": True}
        stack.enter_context(patch.object(web, "BRIDGE_CONFIG_PATH", root / "bridge.json"))
        stack.enter_context(patch.object(web, "GUI_STATE_PATH", root / "gui.json"))
        stack.enter_context(patch.object(web, "load_gui_state", lambda: config.load_json(root / "gui.json", gui)))
        stack.enter_context(patch.object(web, "load_api_key", lambda: ""))
        stack.enter_context(patch.object(web, "save_api_key", lambda key: None))
        yield gui


class SettingsTests(unittest.TestCase):
    def test_panel_note_roundtrip_and_removal(self):
        with isolated_settings() as gui:
            controller = web.Controller()
            gift = {**config.DEFAULT_GIFT_ACTIONS[0], "panel_note": "Cấp 5 → +1 <kiếm>"}
            controller.save({"gui": gui, "bridge": {"gift_actions": [gift]}})
            self.assertEqual(controller.state()["bridge"]["gift_actions"][0]["panel_note"], gift["panel_note"])
            gift["panel_note"] = ""
            controller.save({"bridge": {"gift_actions": [gift]}})
            self.assertEqual(controller.state()["bridge"]["gift_actions"][0]["panel_note"], "")

    def test_enchant_levels_and_positions_roundtrip(self):
        with isolated_settings() as gui:
            controller = web.Controller()
            gift = {**config.DEFAULT_GIFT_ACTIONS[0], "target": "enchant_armor", "level": 255}
            positions = {"comment": {"x": 0, "y": 100, "scale": 4}, "gift": {"x": 100, "y": 0, "scale": 0.5}}
            controller.save({"gui": gui, "bridge": {"gift_actions": [gift]}, "mod": {"notification_positions": positions}})
            saved = controller.state()
            self.assertEqual(saved["bridge"]["gift_actions"][0]["level"], 255)
            self.assertEqual(saved["mod"]["notification_positions"]["comment"], positions["comment"])
            for level in (-1, 256, 1.5, True):
                with self.subTest(level=level), self.assertRaises(ValueError):
                    controller.save({"bridge": {"gift_actions": [{**gift, "level": level}]}})
            for position in ({"x": 101}, {"y": -1}, {"scale": 0}, {"x": float("nan")}):
                with self.subTest(position=position), self.assertRaises(ValueError):
                    controller.save({"mod": {"notification_positions": {"gift": position}}})
            with patch.object(bridge, "send_interaction") as send:
                bridge.dispatch_gift_action({}, gift, "Alice", "alice", "Quà", 2)
                self.assertEqual(send.call_count, 2)
                self.assertEqual(send.call_args_list[0].kwargs["payload"], "255")
                self.assertEqual(send.call_args_list[1].args[4], "")
            from test_runner import build_plan
            plan, _ = build_plan({"gift_actions": [gift]}, {"mode": "gift", "gift_index": 0})
            self.assertEqual(plan[0][:2], ("enchant_armor", "255"))

    def test_roundtrip_and_validation(self):
        with isolated_settings() as gui:
            controller = web.Controller()
            controller.save({"gui": gui, "bridge": {"tts_volume": 0.35, "display_comment_text": True,
                "tts_language_code": ""}, "mod": {"notification_title_color": "#123456",
                "notification_gap_seconds": 0.75, "donation_priority_enabled": False}})
            saved = controller.state()
            self.assertEqual(saved["bridge"]["tts_volume"], 0.35)
            self.assertTrue(saved["bridge"]["display_comment_text"])
            self.assertEqual(saved["bridge"]["tts_language_code"], "")
            self.assertEqual(saved["mod"]["notification_title_color"], "#123456")
            self.assertFalse(saved["mod"]["donation_priority_enabled"])
            # Partial saves must preserve unrelated settings.
            controller.save({"mod": {"notification_gap_seconds": 0.5}})
            self.assertEqual(controller.state()["bridge"]["tts_volume"], 0.35)
            for payload in ({"bridge": {"tts_volume": 2}}, {"bridge": {"tts_speed": 1.5}},
                {"bridge": {"comment_spawn_count": 101}}, {"mod": {"notification_queue_size": 1.5}},
                {"mod": {"notification_enabled": "false"}}, {"mod": {"notification_title_color": "orange"}},
                {"mod": {"notification_overflow_policy": "unknown"}}):
                with self.subTest(payload=payload), self.assertRaises(ValueError):
                    controller.save(payload)

    def test_all_config_fields_have_controls(self):
        html = (ROOT / "web/index.html").read_text(encoding="utf-8")
        ids = re.findall(r'id="([^"]+)"', html)
        self.assertEqual(len(ids), len(set(ids)), "duplicate HTML IDs")
        dynamic = {"likes_per_skeleton", "bridge_port"}
        dynamic.update(f"{kind}_mob_type" for kind in ("like", "comment", "share", "follow", "view"))
        dynamic.update(f"{kind}_spawn_count" for kind in ("comment", "share", "follow", "view"))
        self.assertFalse((config.DEFAULT_BRIDGE_CONFIG.keys() | config.DEFAULT_MOD_CONFIG.keys()) - set(ids) - dynamic)

    def test_volume_preserves_samples_and_scales(self):
        pcm = array("h", [-32768, -1000, 0, 1000, 32767]).tobytes()
        self.assertEqual(comment_tts.CommentSpeaker._scale_volume(pcm, 1), pcm)
        self.assertEqual(comment_tts.CommentSpeaker._scale_volume(pcm, 0), b"\0" * len(pcm))
        result = array("h")
        result.frombytes(comment_tts.CommentSpeaker._scale_volume(pcm, 0.5))
        self.assertEqual(list(result), [-16384, -500, 0, 500, 16384])

    def run_events(self, overrides, exercise):
        import TikTokLive
        handlers = {}
        class Client:
            def __init__(self, **kwargs): pass
            def on(self, event_type):
                def register(handler):
                    handlers[event_type.__name__] = handler
                    return handler
                return register
            def run(self): asyncio.run(exercise(handlers))
        settings = {**config.DEFAULT_BRIDGE_CONFIG, **overrides}
        speaker = Mock()
        with patch.object(TikTokLive, "TikTokLiveClient", Client), \
            patch("gift_alerts.GiftAlerts") as alerts, \
            patch.object(comment_tts, "create_comment_speaker", return_value=speaker), \
            patch.object(bridge, "send_interaction") as send, \
            patch.object(bridge, "observed_gift", return_value=None), contextlib.redirect_stdout(io.StringIO()):
            alerts.return_value.enqueue.side_effect = lambda *args, **kwargs: kwargs["on_ready"]()
            bridge.run_live(settings)
        return send.call_args_list, speaker

    def test_comment_text_and_limited_read_policy(self):
        async def exercise(handlers):
            event = SimpleNamespace(user=SimpleNamespace(unique_id="alice", nickname="Alice"), comment="hello world")
            await handlers["CommentEvent"](event)
            await handlers["CommentEvent"](event)
        sent, speaker = self.run_events({"display_comment_text": True, "display_comment_max_characters": 5,
            "display_limited_comments": True, "tts_read_limited_comments": False}, exercise)
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[0].args[1], "mob")
        self.assertEqual(sent[0].args[4], "hello")
        self.assertEqual(sent[1].args[1], "notification")
        speaker.enqueue.assert_called_once_with("Alice", "hello world")

    def test_hiding_comment_does_not_disable_mob(self):
        async def exercise(handlers):
            await handlers["CommentEvent"](SimpleNamespace(
                user=SimpleNamespace(unique_id="bob", nickname="Bob"), comment="hello"))
        sent, _ = self.run_events({"display_comment_enabled": False, "comment_spawn_count": 2}, exercise)
        self.assertEqual(len(sent), 2)
        self.assertTrue(all(call.args[1] == "mob" and call.args[4] == "" for call in sent))

    def test_like_below_threshold_and_unmapped_donation(self):
        async def exercise(handlers):
            user = SimpleNamespace(unique_id="alice", nickname="Alice")
            await handlers["LikeEvent"](SimpleNamespace(user=user, count=1))
            await handlers["GiftEvent"](SimpleNamespace(user=user, gift_id=987654,
                gift=SimpleNamespace(name="Unknown gift", diamond_count=2), repeat_count=3, streaking=False))
        sent, _ = self.run_events({"gift_actions": []}, exercise)
        self.assertEqual(len(sent), 2)
        self.assertTrue(all(call.args[1] == "notification" for call in sent))
        self.assertTrue(sent[1].kwargs["donation"])
        self.assertIn("x3", sent[1].args[4])


if __name__ == "__main__":
    if "--serve" in sys.argv:
        # Isolated real HTTP controller for the browser smoke check.
        with isolated_settings(), web.ThreadingHTTPServer(("127.0.0.1", 0), web.Handler) as server:
            print(f"http://127.0.0.1:{server.server_port}", flush=True)
            server.serve_forever()
    else:
        unittest.main()
