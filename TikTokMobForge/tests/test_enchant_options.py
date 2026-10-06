import json
import unittest
from unittest.mock import patch
from test_settings import web, bridge, isolated_settings
from reward_options import ENCHANTMENTS, options_for, reward_payload
from test_runner import build_plan


class EnchantOptionTests(unittest.TestCase):
    def test_catalog_and_all_enchants_roundtrip(self):
        self.assertEqual(len(ENCHANTMENTS), 43)
        ids = {entry['id'] for entry in ENCHANTMENTS}
        self.assertTrue({'minecraft:binding_curse', 'minecraft:vanishing_curse', 'minecraft:lunge'} <= ids)
        for target in ('enchant_armor', 'enchant_weapon'):
            with self.subTest(target=target), isolated_settings():
                selected = [{'id': entry['id'], 'level': (index % 255) + 1} for index, entry in enumerate(ENCHANTMENTS)]
                rule = dict(gift_name='Enchant', gift_id='9001', action='special', target=target,
                            amount=2, enchant_mode='selected', enchantments=selected)
                controller = web.Controller()
                controller.save({'bridge': {'gift_actions': [rule]}})
                saved = controller.state()['bridge']['gift_actions'][0]
                self.assertEqual(saved['enchantments'], selected)
                expected = {'enchant_mode': 'selected', 'enchantments': selected}
                self.assertEqual(json.loads(reward_payload(saved)), expected)
                with patch.object(bridge, 'send_interaction') as send:
                    bridge.dispatch_gift_action({}, saved, 'Donor', 'donor', 'Gift', 3)
                    self.assertEqual(send.call_count, 6)
                    self.assertTrue(all(json.loads(call.kwargs['payload']) == expected for call in send.call_args_list))
                plan, _ = build_plan({'gift_actions': [saved]}, {'mode': 'gift', 'gift_index': 0})
                self.assertEqual(len(plan), 2)
                self.assertTrue(all(json.loads(event[1]) == expected for event in plan))

    def test_invalid_selection_is_rejected(self):
        rule = dict(target='enchant_weapon', enchant_mode='selected')
        for entries in ([], None, {}, [{'id': 'minecraft:fake', 'level': 1}],
                        [{'id': 'minecraft:mending', 'level': 1}] * 2):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                options_for(dict(rule, enchantments=entries))
        for level in (0, 256, -1, True, 1.5, float('nan'), '5'):
            with self.subTest(level=level), self.assertRaises(ValueError):
                options_for(dict(rule, enchantments=[{'id': 'minecraft:mending', 'level': level}]))
        for level in (1, 255):
            self.assertEqual(options_for(dict(rule, enchantments=[{'id': 'minecraft:mending', 'level': level}]))['enchantments'][0]['level'], level)

    def test_legacy_full_payload(self):
        for target in ('enchant_armor', 'enchant_weapon'):
            self.assertEqual(reward_payload({'target': target}), '0')
            self.assertEqual(reward_payload({'target': target, 'level': 5}), '5')
            self.assertEqual(options_for({'target': target, 'enchant_mode': 'full', 'enchantments': []}), {})


if __name__ == '__main__':
    unittest.main()
