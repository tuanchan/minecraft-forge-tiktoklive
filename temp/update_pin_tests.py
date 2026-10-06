from pathlib import Path
p=Path('TikTokMobForge/src/test/java/vn/deadchan/tiktokmob/RuntimeSettingsChecks.java');s=p.read_text(encoding='utf-8').replace('FIELDS.size() == 33','FIELDS.size() == 35');s=s.replace('            JsonObject toggle = new JsonObject();','''            for (String key : new String[]{"creeper_break_blocks", "tnt_break_blocks"}) {
                for (boolean enabled : new boolean[]{true, false}) {
                    JsonObject patch = new JsonObject(); patch.addProperty(key, enabled);
                    RuntimeSettings.savePatch(path, patch);
                    check(RuntimeSettings.read(path).get(key).getAsBoolean() == enabled, "explosion toggle persists");
                }
            }
            JsonObject toggle = new JsonObject();''');p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/src/test/java/vn/deadchan/tiktokmob/RewardOptionChecks.java');s=p.read_text(encoding='utf-8').replace('        double height = 64;', '''        check(RewardOptions.blockOverride("1") == null, "Legacy gifts inherit global explosion settings");
        check(Boolean.TRUE.equals(RewardOptions.blockOverride("{\\"break_blocks\\":true}")), "Gift enables terrain damage");
        check(Boolean.FALSE.equals(RewardOptions.blockOverride("{\\"break_blocks\\":false}")), "Gift disables terrain damage");
        check(RewardOptions.blockOverride("{\\"break_blocks\\":\\"false\\"}") == null, "Reject string boolean override");
        check(RewardOptions.mobId("{\\"mob\\":\\"minecraft:creeper\\",\\"break_blocks\\":true}").equals("minecraft:creeper"), "Creeper ID survives options payload");
        double height = 64;''');p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/tests/test_reward_options.py');s=p.read_text(encoding='utf-8');s=s.replace('    def test_defaults_and_validation(self):','''    def test_explosion_override_roundtrip(self):
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

    def test_defaults_and_validation(self):''');p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/tests/browser_pin_smoke.py');s=p.read_text(encoding='utf-8');s=s.replace('        thread = threading.Thread', '''        # Stable layout fixture independent of the user's saved default profile.
        web.CONTROLLER.save({"mod": {"pinned_board_scale": 1, "pinned_board_width": 1, "pinned_board_height": 1}})
        thread = threading.Thread''');anchor='                        if os.environ.get("PIN_NATIVE_EXE"):';s=s.replace(anchor,'''                        browser.evaluate("""window.checkLongPin = () => {
                            const text = 'Bình luận rất dài 😀 '.repeat(24);
                            renderPinnedOverlay({author:'Tên người dùng rất dài 😀',text,style:{}});
                            const rect = id => document.getElementById(id).getBoundingClientRect();
                            const a=rect('avatar'), n=rect('author'), c=rect('content'), b=rect('board');
                            return n.top >= a.bottom && n.right < c.left && c.top > b.top && c.bottom < b.bottom
                              && Math.abs((a.left+a.right)-(n.left+n.right)) < 2;
                        };""")
                        assert browser.evaluate("checkLongPin()"), "Long comment overlaps author/avatar or leaves board"
                        if os.environ.get("PIN_LONG_SCREENSHOT"):
                            shot = browser.command("Page.captureScreenshot", format="png")
                            Path(os.environ["PIN_LONG_SCREENSHOT"]).write_bytes(base64.b64decode(shot["data"]))
                        if os.environ.get("PIN_NATIVE_EXE"):''');p.write_text(s,encoding='utf-8')
print('TESTS_UPDATED')
