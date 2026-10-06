from pathlib import Path
p=Path('TikTokMobForge/tests/check_interaction_ui.py');s=p.read_text().replace('"mod": saves[-1]["mod"]','"mod": {key: saves[-1]["mod"][key] for key in web.MOD_KEYS}');p.write_text(s)
p=Path('TikTokMobForge/tests/test_interaction_rewards.py');s=p.read_text();s=s.replace('    def test_wire_rewards_preserve_identity_and_event_kind(self):','''    def test_settings_roundtrip(self):
        from test_settings import isolated_settings, web
        with isolated_settings() as gui:
            controller = web.Controller()
            rules = {f"{kind}_mob_type": "item:minecraft:totem_of_undying"
                     for kind in ("view", "follow", "comment", "share", "like")}
            controller.save({"gui": gui, "bridge": rules})
            current = controller.runtime_state()["bridge"]
            for key, value in rules.items():
                self.assertEqual(current[key], value)

    def test_wire_rewards_preserve_identity_and_event_kind(self):''');p.write_text(s)
