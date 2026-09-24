import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_settings import isolated_settings, web, config, ROOT


class MobImageTests(unittest.TestCase):
    def test_legacy_slot_image_is_not_restored(self):
        with isolated_settings() as gui, tempfile.TemporaryDirectory() as folder, patch.object(web, "CUSTOM_ASSET_DIR", Path(folder)):
            (Path(folder) / "event-comment.png").write_bytes(b"old picture")
            controller = web.Controller()
            controller.save({"gui": gui, "bridge": {"comment_mob_type": "cow", "event_images": {"follow": "/assets/custom/event-follow.png"}}})
            self.assertEqual(controller.state()["bridge"]["event_images"], {})

    def test_upload_binds_image_to_selected_mob(self):
        with isolated_settings() as gui, tempfile.TemporaryDirectory() as folder, patch.object(web, "CUSTOM_ASSET_DIR", Path(folder)):
            controller = web.Controller()
            controller.save({"gui": gui})
            data = base64.b64encode((ROOT / "web/assets/creeper.png").read_bytes()).decode()
            result = controller.upload_image("follow", "data:image/png;base64," + data, "minecraft:creeper")
            self.assertEqual(result["mob_target"], "minecraft:creeper")
            saved = config.load_json(web.BRIDGE_CONFIG_PATH, {})
            self.assertEqual(saved["event_image_targets"]["follow"], "minecraft:creeper")
            self.assertEqual(saved["event_images"]["follow"], result["url"])
