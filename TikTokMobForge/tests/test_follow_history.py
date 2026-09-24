import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from test_settings import comment_tts, isolated_settings, web
from follow_history import FollowHistory


class FollowHistoryTests(unittest.TestCase):
    def test_real_follow_handlers_award_once_across_restarts(self):
        import test_settings as fixture
        import live_connection
        async def exercise(handlers):
            event = SimpleNamespace(user=SimpleNamespace(id=731, nickname="Tester"))
            await handlers["FollowEvent"](event)
            await handlers["FollowEvent"](event)
            old = SimpleNamespace(user=SimpleNamespace(id=732, nickname="Old", follow_info=SimpleNamespace(follow_status=1)))
            await handlers["JoinEvent"](old)
            await handlers["FollowEvent"](old)
        with tempfile.TemporaryDirectory() as root, patch.object(fixture.bridge, "ROOT", Path(root)), patch.object(live_connection, "run_client_with_cleanup", side_effect=lambda client: client.run()):
            sent, _ = fixture.SettingsTests().run_events({"follow_spawn_count": 3}, exercise)
            self.assertEqual(len(sent), 3)
            sent, _ = fixture.SettingsTests().run_events({"follow_spawn_count": 3}, exercise)
            self.assertEqual(len(sent), 0)

    def test_restart_and_channel_isolation(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "history.db"
            self.assertTrue(FollowHistory(path, "@Host").claim("id:123"))
            self.assertFalse(FollowHistory(path, "host").claim("id:123"))
            self.assertTrue(FollowHistory(path, "other").claim("id:123"))
            self.assertFalse(FollowHistory(path, "host").claim("anonymous:123"))

    def test_existing_follower_seen_in_room_cannot_claim(self):
        with tempfile.TemporaryDirectory() as root:
            history = FollowHistory(Path(root) / "history.db", "host")
            for status in (1, 2):
                history.observe(SimpleNamespace(user=SimpleNamespace(follow_info=SimpleNamespace(follow_status=status))), f"id:{status}")
                self.assertFalse(history.claim(f"id:{status}"))
            history.observe(SimpleNamespace(user=SimpleNamespace(follow_info=None)), "id:3")
            self.assertTrue(history.claim("id:3"))

    def test_missing_key_uses_vietnamese_and_disabled_stays_disabled(self):
        with patch.object(comment_tts, "load_dotenv"), patch.dict(comment_tts.os.environ, {"ELEVENLABS_API_KEY": ""}), patch.object(comment_tts, "CommentSpeaker") as speaker:
            comment_tts.create_comment_speaker({"tts_enabled": True, "tts_provider": "elevenlabs"})
            self.assertEqual(speaker.call_args.args[2]["tts_provider"], "edge")
            speaker.reset_mock()
            self.assertIsNone(comment_tts.create_comment_speaker({"tts_enabled": False}))
            speaker.assert_not_called()

    def test_death_counter_roundtrip(self):
        with isolated_settings() as gui:
            controller = web.Controller()
            for enabled in (False, True):
                controller.save({"gui": gui, "mod": {"show_death_counter": enabled}})
                self.assertEqual(controller.runtime_state()["mod"]["show_death_counter"], enabled)
