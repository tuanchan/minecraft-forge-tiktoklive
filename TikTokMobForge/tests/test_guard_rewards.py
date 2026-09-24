import unittest
from unittest.mock import patch
from test_settings import web, bridge, isolated_settings
from catalog_service import SPECIAL_REWARDS
from runtime_settings import MOD_KEYS


class GuardRewardTests(unittest.TestCase):
    def test_new_rewards_catalog_save_and_dispatch(self):
        for target in ("divine_cat", "netherite_armor_full4", "diamond_armor_full4"):
            with self.subTest(target=target):
                self.assertTrue(any(entry.target == target for entry in SPECIAL_REWARDS))
                rule = dict(gift_name="New gift", gift_id="43", action="special", target=target, amount=2)
                with isolated_settings():
                    controller = web.Controller()
                    controller.save({"bridge": {"gift_actions": [rule]}})
                    saved = controller.state()["bridge"]["gift_actions"][0]
                with patch.object(bridge, "send_interaction") as send:
                    bridge.dispatch_gift_action({}, saved, "Donor", "donor", "New gift", repeat_count=3)
                    self.assertEqual(send.call_count, 6)
                    for call in send.call_args_list:
                        self.assertEqual(call.args[1], target)
                        self.assertTrue(call.kwargs["donation"])

    def test_armored_wolf_catalog_save_and_dispatch(self):
        self.assertTrue(any(entry.target == "armored_wolf" for entry in SPECIAL_REWARDS))
        rule = dict(gift_name="Guard gift", gift_id="42", action="special", target="armored_wolf", amount=2)
        with isolated_settings():
            controller = web.Controller()
            controller.save({"bridge": {"gift_actions": [rule]}})
            saved = controller.state()["bridge"]["gift_actions"][0]
        with patch.object(bridge, "send_interaction") as send:
            bridge.dispatch_gift_action({}, saved, "Donor", "donor", "Guard gift")
            self.assertEqual(send.call_count, 2)
            for call in send.call_args_list:
                self.assertEqual(call.args[1], "armored_wolf")
                self.assertTrue(call.kwargs["donation"])

    def test_distances_save_independently_and_reject_invalid(self):
        with isolated_settings():
            controller = web.Controller()
            controller.save({"mod": {"golem_teleport_distance": 35, "wolf_teleport_distance": 12}})
            controller.save({"mod": {"wolf_teleport_distance": 25}})
            saved = controller.state()["mod"]
            self.assertEqual(saved["golem_teleport_distance"], 35)
            self.assertEqual(saved["wolf_teleport_distance"], 25)
            for key in ("golem_teleport_distance", "wolf_teleport_distance"):
                self.assertIn(key, MOD_KEYS)
                for value in (0, 4, 129, True, float("nan")):
                    with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                        controller.save({"mod": {key: value}})


if __name__ == "__main__":
    unittest.main()
