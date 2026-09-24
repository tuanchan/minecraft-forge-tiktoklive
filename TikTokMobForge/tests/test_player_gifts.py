"""Offline roundtrip and dispatch checks; do not trigger actions in a real world."""
import unittest
from unittest.mock import patch
from test_settings import web, bridge, isolated_settings
from catalog_service import SPECIAL_REWARDS
from test_runner import build_plan


class PlayerGiftTests(unittest.TestCase):
    def test_new_rewards_roundtrip_live_and_test_dispatch(self):
        targets = ("keep_inventory_on", "keep_inventory_off", "set_respawn",
                   "kill_player", "sky_launch", "spawn_tnt")
        catalog = {entry.target for entry in SPECIAL_REWARDS}
        for target in targets:
            with self.subTest(target=target):
                self.assertIn(target, catalog)
                rule = dict(gift_name="Player gift", gift_id="42", action="special",
                            target=target, amount=2)
                with isolated_settings():
                    controller = web.Controller()
                    controller.save({"bridge": {"gift_actions": [rule]}})
                    saved = controller.state()["bridge"]["gift_actions"][0]
                self.assertEqual(saved["target"], target)
                with patch.object(bridge, "send_interaction") as send:
                    bridge.dispatch_gift_action({}, saved, "Donor", "donor", "Gift", 3)
                    self.assertEqual(send.call_count, 6)
                    for i, call in enumerate(send.call_args_list):
                        self.assertEqual(call.args[1], target)
                        self.assertTrue(call.kwargs["donation"])
                        self.assertEqual(call.args[4], "Gift" if i == 0 else "")
                plan, _ = build_plan({"gift_actions": [saved]}, {"mode": "gift", "gift_index": 0})
                self.assertEqual(len(plan), 2)
                self.assertTrue(all(event[0] == target for event in plan))


if __name__ == "__main__":
    unittest.main()
