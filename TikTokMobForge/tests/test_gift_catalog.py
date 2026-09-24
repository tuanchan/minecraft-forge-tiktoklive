"""Gift identity, default rewards and incremental catalog regression checks."""
import json
import asyncio
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from test_settings import bridge, web, isolated_settings, SettingsTests
import gift_catalog_service as catalog


class GiftRoutingTests(unittest.TestCase):
    rule = {"gift_id": "42", "gift_name": "Rose", "coin_value": 1,
            "action": "item", "target": "minecraft:diamond", "amount": 2}

    def event(self, gid=99, name="New gift", count=3, streaking=False):
        return SimpleNamespace(user=SimpleNamespace(unique_id="donor", nickname="Donor"),
            gift_id=gid, gift=SimpleNamespace(id=gid, name=name, diamond_count=1),
            repeat_count=count, streaking=streaking)

    def exercise(self, config, event):
        async def scenario(handlers):
            await handlers["GiftEvent"](event)
        with patch("live_connection.run_client_with_cleanup", side_effect=lambda client: client.run()):
            return SettingsTests().run_events({"gift_actions": [self.rule], **config}, scenario)[0]

    def test_unknown_same_price_does_not_get_mapped_reward(self):
        sent = self.exercise({}, self.event())
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0].args[1], "notification")
        self.assertTrue(sent[0].kwargs["donation"])

    def test_clear_inventory_mapping_roundtrip_and_gift_dispatch(self):
        rule = {**self.rule, "action": "special", "target": "clear_inventory", "amount": 1}
        with isolated_settings():
            controller = web.Controller()
            controller.save({"bridge": {"gift_actions": [rule]}})
            saved = controller.state()["bridge"]["gift_actions"][0]
            self.assertEqual(saved["target"], "clear_inventory")
        sent = self.exercise({"gift_actions": [saved]}, self.event(42, "Rose", count=1))
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0].args[1], "clear_inventory")
        self.assertTrue(sent[0].kwargs["donation"])
        self.assertEqual(self.exercise({"gift_actions": [saved]}, self.event(42, "Rose", streaking=True)), [])

    def test_id_wins_and_same_name_different_id_is_unknown(self):
        self.assertIs(bridge.find_gift_action([self.rule], "42", "Renamed", 1), self.rule)
        self.assertIsNone(bridge.find_gift_action([self.rule], "99", "Rose", 1))
        legacy = {**self.rule, "gift_id": ""}
        self.assertIs(bridge.find_gift_action([legacy], "99", "rose", 1), legacy)

    def test_default_reward_count_and_no_double_reward_for_mapped_gift(self):
        config = dict(unmapped_gift_mode="reward", unmapped_gift_action="item",
                      unmapped_gift_target="minecraft:bread", unmapped_gift_amount=4)
        sent = self.exercise(config, self.event())
        self.assertEqual(len(sent), 12)
        self.assertTrue(all(call.args[5] == "minecraft:bread" for call in sent))
        mapped = self.exercise(config, self.event(42, "Rose"))
        self.assertEqual(len(mapped), 6)
        self.assertTrue(all(call.args[5] == "minecraft:diamond" for call in mapped))
        self.assertEqual(self.exercise(config, self.event(streaking=True)), [])

    def test_default_reward_roundtrip_and_invalid_values(self):
        with isolated_settings():
            controller = web.Controller()
            settings = dict(unmapped_gift_mode="reward", unmapped_gift_action="special",
                            unmapped_gift_target="enchant_armor", unmapped_gift_level=0, unmapped_gift_amount=3)
            controller.save({"bridge": settings})
            saved = controller.state()["bridge"]
            for key, value in settings.items():
                self.assertEqual(saved[key], value)
            for invalid in ({"unmapped_gift_amount": 0}, {"unmapped_gift_level": 256},
                            {"unmapped_gift_mode": "all"}, {"unmapped_gift_action": "bad"}):
                with self.assertRaises(ValueError):
                    controller.save({"bridge": invalid})


class GiftCatalogTests(unittest.TestCase):
    def test_merge_download_failure_keeps_existing_and_new_gifts_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            (assets / "images").mkdir(parents=True)
            (assets / "images/old.png").write_bytes(b"old image")
            index = {"gifts": [{"id": "1", "name": "Old", "diamond_count": 1,
                                "image_file": "images/old.png"}]}
            (assets / "gifts.json").write_text(json.dumps(index))
            discovered = root / "discovered.json"
            discovered.write_text(json.dumps([{"gift_id": "3", "name": "Observed", "diamond_count": 1}]))
            downloader = SimpleNamespace(get_room_gift_info=AsyncMock(return_value=({}, "room")),
                parse_gifts=lambda raw: ([{"id": "2", "name": "New", "diamond_count": 1,
                                          "image_url": "https://example.com/new.png"}], {}),
                download_images=AsyncMock())
            with patch.object(catalog, "ASSET_DIR", assets), patch.object(catalog, "DISCOVERED", discovered), \
                 patch.object(catalog, "load_downloader", return_value=downloader):
                updater = catalog.GiftCatalogUpdater(lambda *_: None)
                asyncio.run(updater.sync("test"))
                gifts = {g["gift_id"]: g for g in catalog.catalog()}
                self.assertEqual(set(gifts), {"1", "2", "3"})
                self.assertIn("/assets/imagegift/images/old.png", gifts["1"]["asset_image"])
                self.assertEqual(gifts["2"]["image_url"], "https://example.com/new.png")
                pending = downloader.download_images.call_args.args[0]
                self.assertEqual({g["id"] for g in pending}, {"2", "3"})
                before = (assets / "gifts.json").read_bytes()
                downloader.get_room_gift_info.side_effect = RuntimeError("offline")
                updater._worker("test")
                self.assertFalse(updater.snapshot()["running"])
                self.assertEqual(updater.snapshot()["error"], "offline")
                self.assertEqual((assets / "gifts.json").read_bytes(), before)

    def test_common_presets_have_correct_catalog_ids_and_real_images(self):
        from PIL import Image
        source = {str(g["id"]): g for g in catalog.read_json(catalog.ASSET_DIR / "gifts.json", {})["gifts"]}
        presets = catalog.read_json(catalog.ROOT / "bridge/common_gifts.json", [])
        self.assertGreaterEqual(len(presets), 20)
        self.assertEqual(len({g["gift_id"] for g in presets}), len(presets))
        for preset in presets:
            gift = source[preset["gift_id"]]
            self.assertEqual(preset["gift_name"], gift["name"])
            with Image.open(catalog.ASSET_DIR / gift["image_file"]) as image:
                image.verify()


if __name__ == "__main__":
    unittest.main()
