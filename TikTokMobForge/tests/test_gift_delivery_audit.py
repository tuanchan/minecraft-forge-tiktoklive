"""Offline donation audit: tests document both successful paths and current limitations."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_settings as settings_tests

bridge = settings_tests.bridge


def gift_event(user, count=1, streaking=False):
    return SimpleNamespace(user=SimpleNamespace(id=user, nickname=f"Donor {user}"),
        gift_id=12345, gift=SimpleNamespace(id=12345, name="Audit gift", diamond_count=1),
        repeat_count=count, streaking=streaking)


class GiftDeliveryAuditTests(unittest.TestCase):
    rule = {"gift_id": "12345", "gift_name": "Audit gift", "action": "mob",
            "target": "minecraft:piglin_brute", "amount": 20}

    def exercise(self, scenario):
        return settings_tests.SettingsTests().run_events({"gift_actions": [self.rule]}, scenario)[0]

    def test_concurrent_donors_keep_all_repeat_times_amount_actions(self):
        async def scenario(handlers):
            for _ in range(20):
                await asyncio.gather(*(handlers["GiftEvent"](gift_event(user, 3)) for user in (101, 202, 303)))
        sent = self.exercise(scenario)
        self.assertEqual(len(sent), 3 * 20 * 3 * 20)
        for user in (101, 202, 303):
            self.assertEqual(sum(call.args[3] == f"id:{user}" for call in sent), 1200)
        self.assertTrue(all(call.args[1] == "mob" and call.args[5] == "minecraft:piglin_brute"
                            and call.args[6] is True for call in sent))
        self.assertEqual(sum(bool(call.args[4]) for call in sent), 60)

    def test_combo_updates_wait_for_final_totals_for_each_donor(self):
        async def scenario(handlers):
            for count in (1, 2, 3):
                await asyncio.gather(*(handlers["GiftEvent"](gift_event(user, count, True)) for user in (101, 202)))
            await handlers["GiftEvent"](gift_event(101, 5))
            await handlers["GiftEvent"](gift_event(202, 7))
        sent = self.exercise(scenario)
        self.assertEqual(len(sent), (5 + 7) * 20)
        self.assertEqual(sum(call.args[3] == "id:101" for call in sent), 100)
        self.assertEqual(sum(call.args[3] == "id:202" for call in sent), 140)

    def test_audit_unfinished_combo_has_no_reward_until_final_packet(self):
        async def scenario(handlers):
            await handlers["GiftEvent"](gift_event(101, 9, True))
        self.assertEqual(self.exercise(scenario), [])

    def test_audit_replayed_final_event_is_not_deduplicated(self):
        async def scenario(handlers):
            event = gift_event(101, 2)
            event.group_id = 123
            event.common = SimpleNamespace(msg_id=987)
            await handlers["GiftEvent"](event)
            await handlers["GiftEvent"](event)
        self.assertEqual(len(self.exercise(scenario)), 80)

    def test_audit_socket_failure_interrupts_remaining_rewards_without_retry(self):
        delivered = []
        attempts = []
        class Connection:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def sendall(self, payload):
                attempts.append(payload)
                if len(attempts) == 4:
                    raise OSError("Simulated Minecraft disconnect")
                delivered.append(payload)
        with patch.object(bridge.socket, "create_connection", return_value=Connection()):
            with self.assertRaisesRegex(OSError, "Simulated"):
                bridge.dispatch_gift_action({"minecraft_host": "127.0.0.1", "minecraft_port": 9876},
                    {"action": "item", "target": "minecraft:golden_apple", "amount": 10},
                    "Donor", "audit-user", "Gift")
        self.assertEqual(len(delivered), 3)
        self.assertEqual(len(attempts), 4)


if __name__ == "__main__":
    unittest.main()
