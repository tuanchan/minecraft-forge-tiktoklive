"""Per-gift configuration roundtrip through real save and dispatch paths."""
import json
import unittest
from unittest.mock import patch
from test_settings import web, bridge, isolated_settings
from reward_options import FIELDS, options_for, reward_payload
from test_runner import build_plan

class RewardOptionTests(unittest.TestCase):
    def test_roundtrip_live_and_test_use_same_payload(self):
        cases = {
            "troll_pumpkin": {"duration_seconds": 2.5},
            "spawn_tnt": {"fuse_seconds": 1.5, "damage_players": False},
            "troll_anvil": {"distance": 7.5},
            "sky_launch": {"height": 150},
            "troll_cobweb": {"radius": 3, "duration_seconds": 12},
        }
        for target, settings in cases.items():
            with self.subTest(target=target), isolated_settings():
                rule = dict(gift_name="Options", gift_id="42", action="special", target=target, amount=2, **settings)
                controller = web.Controller()
                controller.save({"bridge": {"gift_actions": [rule]}})
                saved = controller.state()["bridge"]["gift_actions"][0]
                self.assertEqual(options_for(saved), settings)
                with patch.object(bridge, "send_interaction") as send:
                    bridge.dispatch_gift_action({}, saved, "Donor", "donor", "Gift", 3)
                    self.assertEqual(send.call_count, 6)
                    for call in send.call_args_list:
                        self.assertEqual(json.loads(call.kwargs["payload"]), settings)
                plan, _ = build_plan({"gift_actions": [saved]}, {"mode": "gift", "gift_index": 0})
                self.assertEqual(len(plan), 2)
                self.assertTrue(all(json.loads(event[1]) == settings for event in plan))

    def test_explosion_override_roundtrip(self):
        self.assertIs(options_for({"target": "spawn_tnt"})["damage_players"], True)
        for invalid in ["false", 0, None]:
            with self.assertRaises(ValueError):
                options_for({"target": "spawn_tnt", "damage_players": invalid})
        for target, action in [("spawn_tnt", "special"), ("troll_creeper", "special"), ("minecraft:creeper", "mob")]:
            for enabled in [True, False, None]:
                with self.subTest(target=target, enabled=enabled), isolated_settings():
                    rule = dict(gift_name="Explosion", gift_id="99", action=action, target=target,
                                amount=1, break_blocks=enabled)
                    controller = web.Controller()
                    controller.save({"bridge": {"gift_actions": [rule]},
                                     "mod": {"creeper_break_blocks": True, "tnt_break_blocks": False}})
                    saved = controller.state()["bridge"]["gift_actions"][0]
                    self.assertEqual(saved.get("break_blocks"), enabled)
                    self.assertTrue(controller.state()["mod"]["creeper_break_blocks"])
                    self.assertFalse(controller.state()["mod"]["tnt_break_blocks"])
                    with patch.object(bridge, "send_interaction") as send:
                        bridge.dispatch_gift_action({}, saved, "Donor", "donor", "Gift")
                        call = send.call_args
                        payload = call.kwargs.get("payload", call.args[5] if len(call.args) > 5 else "")
                    plan, _ = build_plan({"gift_actions": [saved]}, {"mode": "gift", "gift_index": 0})
                    self.assertEqual(plan[0][1], payload)
                    if enabled is not None:
                        self.assertIs(json.loads(payload)["break_blocks"], enabled)
                    elif action == "special":
                        self.assertNotIn("break_blocks", json.loads(payload))
                    else:
                        self.assertEqual(payload, "minecraft:creeper")
        for value in ["false", 0, 1, [], {}]:
            with self.assertRaises(ValueError):
                options_for({"target": "troll_creeper", "break_blocks": value})

    def test_defaults_and_validation(self):
        for target, fields in FIELDS.items():
            expected = {k: v[0] for k,v in fields.items()}
            if target == "spawn_tnt":
                expected["damage_players"] = True
            self.assertEqual(json.loads(reward_payload({"target": target})), expected)
            for field, (_, low, high) in fields.items():
                for bad in [low - 1, high + 1, float("nan"), float("inf")]:
                    with self.subTest(target=target, field=field, bad=bad), self.assertRaises(ValueError):
                        options_for({"target": target, field: bad})
        self.assertEqual(reward_payload({"target": "enchant_armor", "level": 255}), "255")
        self.assertEqual(options_for({"target": "troll_anvil", "distance": 0}), {"distance": 0})

if __name__ == "__main__":
    unittest.main()
