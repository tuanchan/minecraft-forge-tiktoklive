"""Two-way game/GUI persistence and live event reload without external services."""
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

import test_settings as fixture
from runtime_settings import LiveSettings, EVENT_KEYS


class RuntimeSettingsTests(unittest.TestCase):
    def test_log_cursor_survives_buffer_rollover(self):
        controller = fixture.web.Controller()
        for i in range(1005):
            controller.log("TEST", str(i))
        first = controller.log_state(0)
        self.assertEqual(len(first["lines"]), 1000)
        controller.log("TEST", "new-after-full")
        second = controller.log_state(first["offset"])
        self.assertEqual(len(second["lines"]), 1)
        self.assertIn("new-after-full", second["lines"][0])
        self.assertEqual(second["offset"], 1006)

    def test_game_test_refreshes_settings_before_building_plan(self):
        from unittest.mock import patch
        with fixture.isolated_settings() as gui:
            controller = fixture.web.Controller()
            controller.save({"gui": gui})
            path = Path(controller.state()["bridge"]["runtime_settings_path"])
            data = fixture.config.load_json(path, {})
            data.update(follow_spawn_count=7, follow_mob_type="minecraft:blaze")
            fixture.config.save_json(path, data)
            with patch.object(controller.test_runner, "start") as start:
                controller.start_test({"mode": "event", "event": "follow"})
            self.assertEqual(start.call_args.args[0]["follow_spawn_count"], 7)
            self.assertEqual(start.call_args.args[0]["follow_mob_type"], "minecraft:blaze")

    def test_seed_from_existing_bridge_and_game_changes_reach_gui(self):
        with fixture.isolated_settings() as gui:
            controller = fixture.web.Controller()
            controller.save({"gui": gui, "bridge": {"follow_spawn_count": 7}})
            state = controller.state()
            path = Path(state["bridge"]["runtime_settings_path"])
            self.assertEqual(json.loads(path.read_text())["follow_spawn_count"], 7)
            data = json.loads(path.read_text())
            data.update(follow_spawn_count=3, follow_mob_type="blaze", max_mobs_total=500)
            fixture.config.save_json(path, data)
            updated = controller.state()
            self.assertEqual(updated["bridge"]["follow_spawn_count"], 3)
            self.assertEqual(updated["bridge"]["follow_mob_type"], "blaze")
            self.assertEqual(updated["mod"]["max_mobs_total"], 500)
            persisted = fixture.config.load_json(fixture.web.BRIDGE_CONFIG_PATH, {})
            self.assertEqual(persisted["follow_spawn_count"], 3)

    def test_stale_gui_save_merges_only_user_edits(self):
        with fixture.isolated_settings():
            controller = fixture.web.Controller()
            state = controller.state()
            base = {key: state[key] for key in ("gui", "bridge", "mod")}
            payload = json.loads(json.dumps(base))
            path = Path(state["bridge"]["runtime_settings_path"])
            data = json.loads(path.read_text())
            data.update(max_mobs_total=777, share_spawn_count=9)
            fixture.config.save_json(path, data)
            payload["bridge"]["like_spawn_count"] = 4
            payload["mod"]["max_mobs_per_user"] = 15
            controller.save({**payload, "base": base})
            current = controller.state()
            self.assertEqual(current["mod"]["max_mobs_total"], 777)
            self.assertEqual(current["mod"]["max_mobs_per_user"], 15)
            self.assertEqual(current["bridge"]["share_spawn_count"], 9)
            self.assertEqual(current["bridge"]["like_spawn_count"], 4)

    def test_running_bridge_updates_rules_without_reconnecting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            fixture.config.save_json(path, {"follow_spawn_count": 2, "follow_mob_type": "zombie"})
            async def exercise(handlers):
                event = SimpleNamespace(user=SimpleNamespace(unique_id="alice", nickname="Alice"))
                await handlers["FollowEvent"](event)
                fixture.config.save_json(path, {"follow_spawn_count": 3, "follow_mob_type": "skeleton"})
                await handlers["FollowEvent"](event)
            sent, _ = fixture.SettingsTests().run_events({"runtime_settings_path": str(path)}, exercise)
            self.assertEqual(len(sent), 5)
            self.assertEqual([call.args[5] for call in sent], ["minecraft:zombie"] * 2 + ["minecraft:skeleton"] * 3)

    def test_invalid_or_partial_file_retains_last_good_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            config = {"runtime_settings_path": str(path), "share_spawn_count": 1}
            live = LiveSettings(config)
            fixture.config.save_json(path, {"share_spawn_count": 4})
            live.refresh(); self.assertEqual(config["share_spawn_count"], 4)
            for content in ('{', '{"share_spawn_count": 0}', '{"share_spawn_count": 1.5}'):
                path.write_text(content); live.refresh()
                self.assertEqual(config["share_spawn_count"], 4)

    def test_runtime_keys_are_all_exposed_by_game_screen_schema(self):
        source = (fixture.ROOT / "src/main/java/vn/deadchan/tiktokmob/RuntimeSettings.java").read_text(encoding="utf-8")
        for key in EVENT_KEYS:
            self.assertIn(f'new Field("{key}"', source)


if __name__ == "__main__":
    unittest.main()
