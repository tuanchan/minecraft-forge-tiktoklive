import base64
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
import bridge


class InteractionRewardsTests(unittest.TestCase):
    def test_settings_roundtrip(self):
        from test_settings import isolated_settings, web
        with isolated_settings() as gui:
            controller = web.Controller()
            rules = {f"{kind}_mob_type": "item:minecraft:totem_of_undying"
                     for kind in ("view", "follow", "comment", "share", "like")}
            controller.save({"gui": gui, "bridge": rules})
            current = controller.runtime_state()["bridge"]
            for key, value in rules.items():
                self.assertEqual(current[key], value)

    def test_wire_rewards_preserve_identity_and_event_kind(self):
        config = {'minecraft_host': 'localhost', 'minecraft_port': 9876}
        for selected, action, payload in (
            ('cow', 'mob', 'minecraft:cow'),
            ('minecraft:cow', 'mob', 'minecraft:cow'),
            ('item:minecraft:totem_of_undying', 'item', 'minecraft:totem_of_undying'),
            ('special:absorption', 'absorption', '1'),
        ):
            for kind in ('view', 'follow', 'comment', 'share', 'like'):
                with self.subTest(selected=selected, kind=kind), patch.object(bridge.socket, 'create_connection') as connection:
                    bridge.send_mob_interaction(config, selected, 'Alice', 'user-123', '+ Event', notification_kind=kind)
                    wire = connection.return_value.__enter__.return_value.sendall.call_args.args[0].decode().rstrip('\n').split('\t')
                    self.assertEqual(wire[0], action)
                    self.assertEqual([base64.b64decode(value).decode() for value in wire[1:5]], ['user-123', 'Alice', '+ Event', payload])
                    self.assertEqual(wire[5:7], ['normal', kind])


if __name__ == '__main__':
    unittest.main()
