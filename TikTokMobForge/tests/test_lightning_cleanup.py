import json
import unittest
from unittest.mock import patch
from test_settings import web, bridge, isolated_settings
from reward_options import options_for
from test_runner import build_plan
from catalog_service import SPECIAL_REWARDS


class LightningCleanupTests(unittest.TestCase):
    def test_catalog_and_live_test_payload(self):
        for target in ('lightning_player', 'clear_tool_mobs'):
            self.assertTrue(any(r.target == target for r in SPECIAL_REWARDS))
            rule = {'gift_name': 'Test lightning', 'action': 'special', 'target': target,
                    'amount': 2, 'strike_count': 7, 'interval_seconds': 0.25}
            with isolated_settings() as gui:
                controller = web.Controller()
                controller.save({'gui': gui, 'bridge': {'gift_actions': [rule]}})
                saved = controller.state()['bridge']['gift_actions'][0]
                if target == 'lightning_player':
                    self.assertEqual(saved['strike_count'], 7)
                    self.assertEqual(saved['interval_seconds'], 0.25)
                with patch.object(bridge, 'send_interaction') as send:
                    bridge.dispatch_gift_action({}, saved, 'Tuấn', 'uid', 'Quà', 3)
                    self.assertEqual(send.call_count, 6)  # amount × combo, each has its own strike settings
                    self.assertEqual(send.call_args.args[1:4], (target, 'Tuấn', 'uid'))
                    payload = send.call_args.kwargs['payload']
                    if target == 'lightning_player':
                        self.assertEqual(json.loads(payload), {'strike_count': 7, 'interval_seconds': 0.25})
                plan, _ = build_plan({'gift_actions': [saved]}, {'mode': 'gift', 'gift_index': 0})
                self.assertEqual(plan[0][0:2], (target, payload))

    def test_validation(self):
        for value in (0, -1, 1.5, True, 2147483648, float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                options_for({'target': 'lightning_player', 'strike_count': value})
        for value in (-0.1, True, float('inf'), 107374183):
            with self.subTest(value=value), self.assertRaises(ValueError):
                options_for({'target': 'lightning_player', 'interval_seconds': value})
        self.assertEqual(options_for({'target': 'lightning_player', 'interval_seconds': 0})['interval_seconds'], 0)


if __name__ == '__main__': unittest.main()
