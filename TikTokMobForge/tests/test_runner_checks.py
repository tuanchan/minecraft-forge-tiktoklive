"""Test real packet delivery and cancellation against a local capture socket."""
import base64
import socket
import threading
import unittest
from unittest.mock import patch
import sys
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "bridge"), str(Path(__file__).resolve().parents[1] / "GUI")]
from test_runner import TestRunner, build_plan
from config_service import DEFAULT_BRIDGE_CONFIG


class RunnerTests(unittest.TestCase):
    def test_gift_thanks_once_per_gift_not_per_spawn(self):
        config = {**DEFAULT_BRIDGE_CONFIG, "gift_actions": [
            {"gift_name": "Rose", "action": "mob", "target": "minecraft:zombie", "amount": 10}]}
        runner = TestRunner(lambda *args: None)
        with patch("test_runner.send_mob_interaction") as send, patch("gift_alerts.GiftAlerts") as factory:
            alerts = factory.return_value
            alerts.pending.unfinished_tasks = 0
            alerts.enqueue.side_effect = lambda *args, **kwargs: kwargs["on_ready"]()
            runner.start(config, {"mode": "gift", "gift_index": 0, "count": 2, "interval": 0})
            runner.thread.join(3)
            self.assertFalse(runner.state()["running"])
            self.assertEqual(send.call_count, 20)
            self.assertEqual(alerts.enqueue.call_count, 2)
            self.assertEqual(alerts.enqueue.call_args.args, ("Test User 1", "Rose", 1))
            alerts.close.assert_called_once_with(discard_pending=False)

    def test_plan_counts_identity_and_gifts(self):
        config = {**DEFAULT_BRIDGE_CONFIG, "follow_spawn_count": 3, "gift_actions": [
            {"gift_name": "Test", "action": "mob", "target": "minecraft:skeleton", "amount": 2},
            {"gift_name": "Rose", "action": "special", "target": "absorption", "amount": 1}]}
        full, _ = build_plan(config, {"mode": "all_mobs", "users": 2, "count": 2})
        self.assertEqual(len(full), 28)
        self.assertEqual(sum(packet[4] == "+ View" for packet in full), 4)
        self.assertEqual(len({packet[3] for packet in full}), 2)
        gift, _ = build_plan(config, {"mode": "gift", "gift_index": 1})
        self.assertEqual(gift[0][0], "absorption")
        self.assertTrue(gift[0][-1])
        gifts, _ = build_plan(config, {"mode": "all_gifts"})
        self.assertEqual(len(gifts), 3)
        self.assertEqual(sum(bool(packet[4]) for packet in gifts), 2)
        another, _ = build_plan(config, {"mode": "all_mobs"})
        self.assertNotEqual(another[0][3], full[0][3])
        for request in ({"mode": "gift", "gift_index": 99}, {"mode": "mob", "users": 1.5},
            {"mode": "spam", "event": "unknown"}, {"mode": "all_mobs", "users": 50, "count": 100}):
            with self.subTest(request=request), self.assertRaises(ValueError): build_plan(config, request)

    def test_socket_delivery_and_interruptible_stop(self):
        received = []
        ready = threading.Event()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            listener.settimeout(4)
            def capture():
                with listener.accept()[0] as client:
                    data = b""
                    while True:
                        part = client.recv(4096)
                        if not part: break
                        data += part
                    received.append(data.decode().strip().split("\t"))
                    ready.set()
            thread = threading.Thread(target=capture)
            thread.start()
            runner = TestRunner(lambda *args: None)
            config = {**DEFAULT_BRIDGE_CONFIG, "minecraft_host": "127.0.0.1", "minecraft_port": listener.getsockname()[1]}
            runner.start(config, {"mode": "mob", "count": 10, "interval": 10, "name": "Người thử"})
            self.assertTrue(ready.wait(3))
            with self.assertRaises(ValueError): runner.start(config, {"mode": "mob"})
            runner.stop()
            runner.thread.join(2)
            thread.join(2)
            self.assertFalse(runner.state()["running"])
            self.assertEqual(runner.state()["sent"], 1)
            self.assertEqual(received[0][0], "mob")
            self.assertEqual(base64.b64decode(received[0][2]).decode(), "Người thử 1")
            self.assertEqual(base64.b64decode(received[0][4]).decode(), "minecraft:zombie")


if __name__ == "__main__": unittest.main()
