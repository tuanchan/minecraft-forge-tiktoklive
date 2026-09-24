import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from view_interactions import ViewInteractions

def event(uid=1, name='Alice'):
    return SimpleNamespace(user=SimpleNamespace(id=uid, nickname=name))

class ViewTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.views = ViewInteractions(lambda: self.now)
        self.send = Mock()
        self.config = {'view_enabled': True, 'view_interval_seconds': 10}
    def tick(self):
        self.views.tick(self.config, self.send)
    def test_room_count_never_creates_anonymous_mobs(self):
        self.views.observe(1000)
        self.tick()
        self.send.assert_not_called()
    def test_names_ids_repeat_and_duplicate_join(self):
        self.views.observe_event(event(1, 'Alice'))
        self.views.observe_event(event(2, 'Bình'))
        self.tick()
        self.assertEqual([c.args[2:4] for c in self.send.call_args_list], [('Alice', 'id:1'), ('Bình', 'id:2')])
        self.now = 9
        self.views.observe_event(event(1, 'Alice mới'))
        self.tick()
        self.assertEqual(self.send.call_count, 2)
        self.now = 10
        self.tick()
        self.assertEqual(self.send.call_count, 4)
        self.assertEqual(self.send.call_args_list[2].args[2:4], ('Alice mới', 'id:1'))
    def test_same_nickname_different_users(self):
        for uid in (1, 2): self.views.observe_event(event(uid, 'Same'))
        self.tick()
        self.assertEqual({c.args[3] for c in self.send.call_args_list}, {'id:1', 'id:2'})
    def test_missing_identity_or_name_is_ignored(self):
        self.assertFalse(self.views.observe_event(event(0)))
        self.assertFalse(self.views.observe_event(event(1, '')))
        self.tick()
        self.send.assert_not_called()
    def test_count_does_not_extend_individual_presence(self):
        self.views.observe_event(event())
        self.now = 301
        self.views.observe(20)
        self.tick()
        self.send.assert_not_called()
        self.assertFalse(self.views.viewers)
    def test_long_interval_allows_repeat(self):
        self.config['view_interval_seconds'] = 600
        self.views.observe_event(event())
        self.tick()
        self.now = 600
        self.views.observe(1)
        self.tick()
        self.assertEqual(self.send.call_count, 2)
    def test_zero_disconnect_and_stale_stop(self):
        self.views.observe_event(event())
        self.now = 91
        self.tick()
        self.send.assert_not_called()
        self.views.observe(0)
        self.tick()
        self.send.assert_not_called()
        self.views.observe_event(event())
        self.views.reset()
        self.tick()
        self.send.assert_not_called()
    def test_disabled(self):
        self.views.observe_event(event())
        self.config['view_enabled'] = False
        self.tick()
        self.send.assert_not_called()
    def test_cap_fairness_and_failure(self):
        self.config['view_max_mobs_per_round'] = 1
        for uid in (1, 2, 3): self.views.observe_event(event(uid, str(uid)))
        self.send.side_effect = OSError('offline')
        with self.assertRaises(OSError): self.tick()
        self.assertEqual(self.views.round_sent, 0)
        self.send.side_effect = None
        self.send.reset_mock()
        self.tick()
        self.tick()
        self.assertEqual(self.send.call_count, 1)
        for now in (10, 20):
            self.now = now
            self.tick()
        self.assertEqual([c.args[3] for c in self.send.call_args_list], ['id:1', 'id:2', 'id:3'])
    def test_partial_batch_retries_only_unsent_mobs(self):
        self.config['view_spawn_count'] = 3
        self.views.observe_event(event())
        self.send.side_effect = [None, OSError('offline')]
        with self.assertRaises(OSError): self.tick()
        self.assertEqual(self.views.viewers['id:1'].remaining, 2)
        self.send.side_effect = None
        self.send.reset_mock()
        self.tick()
        self.assertEqual(self.send.call_count, 2)

    def test_live_join_handler_sends_named_mob_and_disconnect_cancels(self):
        import asyncio
        import test_settings as fixture

        async def exercise(handlers):
            await handlers['ConnectEvent'](SimpleNamespace())
            await handlers['JoinEvent'](event(42, 'Named Viewer'))
            await asyncio.sleep(0)
            await handlers['DisconnectEvent'](SimpleNamespace())
            await asyncio.sleep(0)

        sent, _ = fixture.SettingsTests().run_events({}, exercise)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0].args[1:4], ('mob', 'Named Viewer', 'id:42'))

if __name__ == '__main__': unittest.main()
