"""Phrase/GIF selection, alpha layout, and bridge-to-Minecraft readiness protocol."""
import contextlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_settings import config, isolated_settings, web, bridge
import gift_media as media


class GiftMediaTests(unittest.TestCase):
    def test_respawn_heartbeat_preserves_gif_after_long_death(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            clock = [0.0]
            def sleep(seconds):
                clock[0] += 1
                (directory / "paused").write_text("waiting")
                if clock[0] >= 60:
                    (directory / "ready").write_text("respawned")
            with patch.object(media.time, "monotonic", side_effect=lambda: clock[0]), patch.object(media.time, "sleep", side_effect=sleep):
                media.wait_for_hud_marker(directory, "ready", 15)
            self.assertEqual(clock[0], 60)

    def test_missing_minecraft_still_times_out(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = [0.0]
            def sleep(seconds): clock[0] += 1
            with patch.object(media.time, "monotonic", side_effect=lambda: clock[0]), patch.object(media.time, "sleep", side_effect=sleep):
                with self.assertRaises(ValueError):
                    media.wait_for_hud_marker(Path(folder), "finished", 15)
            self.assertEqual(clock[0], 15)

    def test_random_uses_all_discovered_gifs_and_phrases(self):
        gifs = media.catalog()["gifs"]
        self.assertGreaterEqual(len(gifs), 4)
        with patch.object(media.random, "choice", side_effect=lambda values: values[-1]):
            self.assertEqual(media.select_gif({}).name, gifs[-1])
            self.assertEqual(media.select_phrase({"gift_phrase_mode": "random"}), media.PHRASES[-1])
        self.assertEqual(media.select_phrase({"gift_phrase_mode": "custom", "gift_phrase_custom": "ありがとう！"})["text"], "ありがとう！")
        with self.assertRaises(ValueError): media.select_gif({"gift_gif_random": False, "gift_gif_file": "../bad.gif"})

    def test_all_gifs_render_transparent_vertical_layout(self):
        event = {"name": "Tên người tặng", "gift": "Hoa Hồng", "count": 3, "label": media.PHRASES[0]["label"]}
        artifacts = Path(__file__).resolve().parent / "artifacts"
        artifacts.mkdir(exist_ok=True)
        for name in media.catalog()["gifs"]:
            with self.subTest(name=name):
                frames, delays = media.render_frames(event, media.GIF_DIR / name)
                self.assertGreater(len(frames), 1)
                self.assertEqual(len(frames), len(delays))
                image = frames[0]
                self.assertEqual(image.getpixel((0, image.height - 1))[3], 0, "no background panel")
                gif_height = image.height - 166
                self.assertGreater(image.getpixel((160, gif_height + 32))[3], 0, "avatar centered below GIF")
                self.assertEqual(image.getpixel((5, gif_height + 32))[3], 0, "transparent outside avatar")
                image.save(artifacts / (name + ".preview.png"))

    def test_minecraft_manifest_ack_and_cleanup(self):
        event = {"name": "A", "gift": "Rose", "count": 1, "label": "ありがとう！"}
        with tempfile.TemporaryDirectory() as folder, patch.object(media, "EXCHANGE", Path(folder)):
            def send(config, kind, name, key, notification, token, donation):
                self.assertEqual(kind, "gift_alert")
                self.assertEqual(len(token), 32)
                directory = Path(folder) / token
                manifest = json.loads((directory / "manifest.json").read_text())
                self.assertEqual(manifest["x"], 90)
                self.assertTrue((directory / "0.png").is_file())
                (directory / "ready").write_text("ready")
            with patch.object(bridge, "send_interaction", side_effect=send):
                with media.minecraft_alert({"gift_overlay_x": 90}, event, media.GIF_DIR / "kawaiianimegirlGIF.gif", 5):
                    self.assertEqual(len(list(Path(folder).iterdir())), 1)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_settings_roundtrip_and_validation(self):
        with isolated_settings() as gui:
            controller = web.Controller()
            values = {"gift_phrase_mode": "custom", "gift_phrase_custom": "ありがとう！", "gift_phrase_id": "happy",
                      "gift_gif_random": False, "gift_gif_file": "girl GIF.gif"}
            controller.save({"gui": gui, "bridge": values})
            for key, value in values.items(): self.assertEqual(controller.state()["bridge"][key], value)
            for changes in ({"gift_phrase_custom": ""}, {"gift_phrase_mode": "bad"},
                            {"gift_phrase_id": "unknown"}, {"gift_gif_file": "../file.gif"}):
                with self.assertRaises(ValueError): controller.save({"bridge": changes})


if __name__ == "__main__": unittest.main()
