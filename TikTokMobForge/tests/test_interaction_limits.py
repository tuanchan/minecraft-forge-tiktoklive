import asyncio
import base64
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))
from interaction_limits import InteractionLimits, user_key
import bridge


class InteractionLimitTests(unittest.TestCase):
    def test_same_nickname_and_missing_handle_keep_numeric_ids_separate(self):
        from TikTokLive.proto.custom_proto import ExtendedUser
        a = SimpleNamespace(user=ExtendedUser(id=101, nickname="Same name"))
        b = SimpleNamespace(user=ExtendedUser(id=202, nickname="Same name"))
        self.assertNotEqual(user_key(a), user_key(b))
        a.user.display_id = "new_handle"
        self.assertEqual(user_key(a), "id:101")

    def test_handle_variations_and_missing_identity(self):
        def event(**fields):
            return SimpleNamespace(user=SimpleNamespace(**fields))
        self.assertEqual(user_key(event(unique_id=" @Alice ")), user_key(event(display_id="alice")))
        self.assertNotEqual(user_key(event(nickname="Same")), user_key(event(nickname="Same")))
        self.assertEqual(user_key(event(id_str="123")), "id:123")

    def test_cooldown_is_per_user_per_event_and_expires_at_ten_seconds(self):
        now = [100.0]
        limits = InteractionLimits(clock=lambda: now[0])
        for kind in ("comment", "share"):
            for key in ("alice", "bob"):
                self.assertTrue(limits.allow(kind, key, 1, 10)[0])
                self.assertEqual(limits.allow(kind, key, 1, 10), (False, 10))
        now[0] = 109.5
        self.assertEqual(limits.allow("comment", "alice", 1, 10), (False, .5))
        now[0] = 110
        for key in ("alice", "bob"):
            self.assertTrue(limits.allow("comment", key, 1, 10)[0])

    def test_limit_two_and_likes_remainders_are_independent(self):
        limits = InteractionLimits(clock=lambda: 1)
        self.assertTrue(limits.allow("comment", "a", 2, 10)[0])
        self.assertTrue(limits.allow("comment", "a", 2, 10)[0])
        self.assertFalse(limits.allow("comment", "a", 2, 10)[0])
        self.assertTrue(limits.allow("comment", "b", 2, 10)[0])
        self.assertEqual(limits.add_likes("a", 199, 200), 0)
        self.assertEqual(limits.add_likes("b", 1, 200), 0)
        self.assertEqual(limits.add_likes("a", 1, 200), 1)
        self.assertEqual(limits.add_likes("b", 599, 200), 3)

    def test_simultaneous_live_handlers_send_both_users_to_minecraft(self):
        from TikTokLive.events import CommentEvent, ShareEvent, FollowEvent, LikeEvent
        packets = []
        now = [100.0]
        a = SimpleNamespace(user=SimpleNamespace(id=101, nickname="Same name"), comment="a", count=200)
        b = SimpleNamespace(user=SimpleNamespace(id=202, nickname="Same name"), comment="b", count=200)

        class Client:
            def __init__(self, **kwargs):
                self.handlers = {}

            def on(self, kind):
                def register(handler):
                    self.handlers[kind] = handler
                    return handler
                return register

            def run(self):
                async def scenario():
                    for kind in (CommentEvent, ShareEvent):
                        await asyncio.gather(self.handlers[kind](a), self.handlers[kind](b))
                        await asyncio.gather(self.handlers[kind](a), self.handlers[kind](b))
                    # Comment cooldown must not block either person's other mobs.
                    for kind in (FollowEvent, LikeEvent):
                        await asyncio.gather(self.handlers[kind](a), self.handlers[kind](b))
                    now[0] += 10
                    await asyncio.gather(self.handlers[CommentEvent](a), self.handlers[CommentEvent](b))
                asyncio.run(scenario())

        class Connection:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def sendall(self, payload): packets.append(payload.decode().strip().split("\t"))

        config = {
            "tiktok_username": "test", "minecraft_host": "127.0.0.1", "minecraft_port": 9876,
            "likes_per_skeleton": 200, "comment_limit": 1, "comment_cooldown_seconds": 10,
            "share_limit": 1, "share_cooldown_seconds": 10, "display_like_enabled": False,
        }
        # Run the actual registered handlers and TCP encoder with no LIVE/world side effects.
        with patch("TikTokLive.TikTokLiveClient", Client), \
             patch("live_connection.install_websocket_url_fix"), \
             patch("comment_tts.create_comment_speaker", return_value=None), \
             patch.object(bridge, "InteractionLimits", lambda: InteractionLimits(clock=lambda: now[0])), \
             patch.object(bridge.socket, "create_connection", return_value=Connection()), \
             patch("builtins.print"):
            bridge.run_live(config)
        self.assertEqual(len(packets), 10)
        decode = lambda value: base64.b64decode(value).decode()
        for key in ("id:101", "id:202"):
            mobs = [decode(p[4]) for p in packets if decode(p[1]) == key]
            self.assertCountEqual(mobs, ["minecraft:zombie", "minecraft:zombie", "minecraft:enderman", "minecraft:creeper", "minecraft:skeleton"])


if __name__ == "__main__":
    unittest.main()
