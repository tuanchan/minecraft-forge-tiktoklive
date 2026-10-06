import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
from milestones import Milestones, settings


class MilestoneTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config = {'milestones': {'like': {'enabled': True, 'rules': [
            {'id': 'a', 'threshold': 10, 'reward': 'minecraft:zombie', 'amount': 2},
            {'id': 'b', 'threshold': 25, 'reward': 'minecraft:creeper', 'amount': 1}]}}}
        self.send = Mock()
        self.path = Path(self.folder.name) / 'progress.json'
        self.engine = Milestones(self.config, self.send, path=self.path)

    def test_session_restart_and_remember(self):
        self.engine.start_session('room-1')
        self.engine.add('like', 7, 'A', 'a')
        self.engine.start_session('room-1')
        self.assertEqual(self.engine.counters['like'], 7)
        restarted = Milestones(self.config, self.send, path=self.path)
        restarted.start_session('room-1')
        self.assertEqual(restarted.counters['like'], 0)
        restarted.add('like', 7, 'A', 'a')
        self.config['milestones']['like']['remember'] = True
        restarted.refresh()
        self.assertEqual(restarted.counters['like'], 7)
        restarted = Milestones(self.config, self.send, path=self.path)
        restarted.start_session('room-2')
        restarted.add('like', 3, 'A', 'a')
        self.assertEqual(restarted.counters['like'], 10)
        self.assertEqual(self.send.call_count, 2)
        self.config['milestones']['like']['remember'] = False
        restarted.refresh()
        self.assertEqual(restarted.counters['like'], 10)
        restarted.start_session('room-3')
        self.assertEqual(restarted.counters['like'], 0)

    def test_remember_validation(self):
        self.config['milestones']['like']['remember'] = 'false'
        with self.assertRaises(ValueError):
            settings(self.config)

    def test_stopped_snapshot_clears_only_non_remembered_groups(self):
        import milestones
        self.engine.add('like', 7, 'A', 'a')
        self.config['milestones']['comment'] = {'enabled': True, 'remember': True,
            'rules': [{'id': 'c', 'threshold': 10, 'reward': 'minecraft:cow', 'amount': 1}]}
        self.engine.add('comment', 4, 'A', 'a')
        with patch.object(milestones, 'PATH', self.path):
            stopped = milestones.snapshot(self.config, active=False)
            self.assertEqual(stopped['groups']['like']['total'], 0)
            self.assertEqual(stopped['groups']['like']['rules'][0]['current'], 0)
            self.assertEqual(stopped['groups']['comment']['total'], 4)
            self.assertEqual(milestones.snapshot()['groups']['like']['total'], 7)
            self.config['milestones']['comment']['remember'] = False
            self.assertEqual(milestones.snapshot(self.config, active=False)['groups']['comment']['total'], 0)

    def test_room_sum_multiple_crossings_and_remainder(self):
        self.engine.add('like', 7, 'Alice', 'a')
        self.engine.add('like', 26, 'Bob', 'b')
        self.assertEqual(self.send.call_count, 7)
        rules = json.loads(self.path.read_text())['groups']['like']['rules']
        self.assertEqual([(r['current'], r['completed']) for r in rules], [(3, 3), (8, 1)])
        self.assertEqual(self.send.call_args.args[2:4], ('Bob', 'b'))

    def test_disabled_and_edit_reset_only_one_kind(self):
        self.engine.add('like', 7, 'A', 'a')
        self.engine.add('comment', 3, 'A', 'a')
        self.config['milestones']['like']['enabled'] = False
        self.engine.add('like', 100, 'A', 'a')
        self.assertEqual(self.engine.counters['like'], 0)
        self.assertEqual(self.engine.counters['comment'], 3)
        self.config['milestones']['like']['enabled'] = True
        self.engine.add('like', 2, 'A', 'a')
        self.assertEqual(self.engine.counters['like'], 2)

    def test_failure_retries_remaining_only(self):
        self.send.side_effect = [None, OSError('offline')]
        self.engine.add('like', 10, 'A', 'a')
        self.assertEqual(self.engine.pending[0]['remaining'], 1)
        self.send.side_effect = None
        self.engine.flush()
        self.assertEqual(self.send.call_count, 3)
        self.assertFalse(self.engine.pending)

    def test_large_combo_is_queued_not_capped(self):
        self.engine.add('like', 1000, 'A', 'a')
        self.assertEqual(self.send.call_count, 100)
        self.engine.flush(); self.engine.flush()
        self.assertEqual(self.send.call_count, 240)
        self.assertFalse(self.engine.pending)

    def test_coins_independent_and_live_config_refresh(self):
        config_path = Path(self.folder.name) / 'config.json'
        coins = {'enabled': True, 'rules': [{'id': 'c', 'threshold': 100, 'reward': 'minecraft:iron_golem', 'amount': 1}]}
        config_path.write_text(json.dumps({'milestones': {'coins': coins}}))
        self.engine.config_path = config_path
        self.engine.add('coins', 250, 'A', 'a')
        self.assertEqual(self.send.call_count, 2)
        self.assertTrue(self.send.call_args.kwargs['donation'])
        self.assertEqual(json.loads(self.path.read_text())['groups']['coins']['rules'][0]['current'], 50)

    def test_validation_and_save_roundtrip(self):
        from test_settings import isolated_settings, web
        with isolated_settings() as gui:
            controller = web.Controller()
            controller.save({'gui': gui, 'bridge': self.config})
            self.assertEqual(controller.state()['bridge']['milestones']['like'], self.config['milestones']['like'])
        for value in (0, -1, True, 1.5, float('nan'), 9007199254740992):
            self.config['milestones']['like']['rules'][0]['threshold'] = value
            with self.assertRaises(ValueError):
                settings(self.config)

    def test_real_handlers_room_totals_and_completed_gift_combo(self):
        from types import SimpleNamespace as NS
        from test_settings import SettingsTests, bridge
        import milestones
        groups = {kind: {'enabled': True, 'rules': [{'id': kind, 'threshold': 10 if kind != 'coins' else 100,
                   'reward': 'minecraft:cow', 'amount': 1}]} for kind in milestones.KINDS}
        async def exercise(handlers):
            alice, bob = NS(unique_id='a', nickname='Alice'), NS(unique_id='b', nickname='Bob')
            await handlers['LikeEvent'](NS(user=alice, count=7))
            await handlers['LikeEvent'](NS(user=bob, count=8))
            await handlers['CommentEvent'](NS(user=alice, comment='one'))
            await handlers['CommentEvent'](NS(user=bob, comment='two'))
            await handlers['ShareEvent'](NS(user=alice))
            await handlers['FollowEvent'](NS(user=bob))
            gift = NS(user=alice, gift_id=123, gift=NS(name='Unknown', diamond_count=50), repeat_count=5, streaking=True)
            await handlers['GiftEvent'](gift)
            self.assertEqual(milestones.snapshot()['groups']['coins']['total'], 0)
            gift.streaking = False
            await handlers['GiftEvent'](gift)
        with patch.object(milestones, 'PATH', self.path), patch.object(bridge, 'CONFIG_PATH', self.path.with_name('missing.json')), \
             patch.object(bridge, 'FollowHistory'), patch('live_connection.run_client_with_cleanup', lambda client: client.run()):
            sent, _ = SettingsTests().run_events({'milestones': groups, 'gift_actions': [], 'unmapped_gift_mode': 'thanks',
                'comment_spawn_count': 1, 'share_spawn_count': 1, 'follow_spawn_count': 1, 'likes_per_skeleton': 50,
                'display_like_enabled': False, 'display_comment_enabled': False, 'display_share_enabled': False,
                'display_follow_enabled': False, 'display_gift_enabled': False}, exercise)
            snapshot = milestones.snapshot()['groups']
        self.assertEqual([snapshot[k]['total'] for k in milestones.KINDS], [15, 1, 2, 1, 250])
        self.assertEqual(len(sent), 7)  # 3 room rewards + 2 comments + share + follow

    def test_personal_rewards_and_room_goals_are_independent(self):
        from types import SimpleNamespace as NS
        from test_settings import SettingsTests, bridge
        import milestones
        for enabled in (True, False):
            groups = {kind: {'enabled': enabled, 'rules': [{'id': kind,
                'threshold': 10 if kind == 'like' else 100 if kind == 'coins' else 1,
                'reward': 'minecraft:cow', 'amount': 1}]} for kind in milestones.KINDS}
            async def exercise(handlers):
                alice, bob = NS(unique_id='a', nickname='Alice'), NS(unique_id='b', nickname='Bob')
                for user, count in ((alice, 6), (bob, 6), (alice, 4)):
                    await handlers['LikeEvent'](NS(user=user, count=count))
                for user in (alice, alice, bob):
                    await handlers['CommentEvent'](NS(user=user, comment='hello'))
                    await handlers['ShareEvent'](NS(user=user))
                await handlers['FollowEvent'](NS(user=alice))
                await handlers['GiftEvent'](NS(user=bob, gift_id=123,
                    gift=NS(name='Test', diamond_count=50), repeat_count=2, streaking=False))
            overrides = {'milestones': groups, 'likes_per_skeleton': 10, 'comment_limit': 1, 'share_limit': 1,
                'comment_cooldown_seconds': 100, 'share_cooldown_seconds': 100,
                'gift_actions': [{'gift_name': 'Test', 'gift_id': '123', 'action': 'mob', 'target': 'minecraft:pig', 'amount': 1}]}
            for kind in ('like', 'comment', 'share', 'follow'):
                overrides.update({kind + '_mob_type': 'pig', kind + '_spawn_count': 1, 'display_' + kind + '_enabled': False})
            with patch.object(milestones, 'PATH', self.path), patch.object(bridge, 'CONFIG_PATH', self.path.with_name('missing.json')), \
                 patch.object(bridge, 'FollowHistory'), patch('live_connection.run_client_with_cleanup', lambda client: client.run()):
                sent, _ = SettingsTests().run_events(overrides, exercise)
            personal = [call for call in sent if call.args[1] == 'mob' and call.args[5] == 'minecraft:pig']
            room = [call for call in sent if call.args[1] == 'mob' and call.args[5] == 'minecraft:cow']
            self.assertEqual(len(personal), 8)  # like Alice only + 2 comment + 2 share + follow + 2 gifts
            self.assertEqual(len(room), 9 if enabled else 0)  # all comments/shares count toward room goals
            likes = [call for call in personal if call.args[7] == 'like']
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].args[2], 'Alice')


if __name__ == '__main__':
    unittest.main()
