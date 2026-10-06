from pathlib import Path
j=Path('TikTokMobForge/src/main/java/vn/deadchan/tiktokmob')
p=j/'PinnedCommentBoard.java';s=p.read_text(encoding='utf-8').replace('private static boolean selecting, selectionReady, keyHeld, pendingPin;', 'private static boolean selecting, selectionReady, keyHeld, pendingPin, pendingGrab;')
s=s.replace('keyHeld = true; select();', 'keyHeld = true; pendingGrab = true; select();')
s=s.replace('keyHeld = grabDown; pendingPin |= pinClicked;', 'keyHeld = grabDown; pendingPin |= pinClicked; pendingGrab |= grabDown;')
s=s.replace('            selectionReady = false;\n            if (pendingScroll', '            selectionReady = false;\n            if (pendingGrab && !grabDown && !pinned) wasGrabDown = true;\n            pendingGrab = false;\n            if (pendingScroll')
s=s.replace('pendingPin = false; pendingScroll = 0;', 'pendingPin = false; pendingGrab = false; pendingScroll = 0;');p.write_text(s,encoding='utf-8')
p=j/'ServerPinnedCommentBoard.java';s=p.read_text(encoding='utf-8').replace('            GiftNetwork.BoardPosition previous = selected == null ? DEFAULT : selected.setting;', '''            if (selected != null && selected.setting.grabbing()) {
                var old = selected.setting;
                selected.setting = new GiftNetwork.BoardPosition(old.side(), old.height(), old.distance(), old.scale(), false, old.pinned(), true);
                selected.relativeOffset = selected.display.position().subtract(player.position());
                persist(selected);
            }
            GiftNetwork.BoardPosition previous = selected == null ? DEFAULT : selected.setting;''')
# Default migration of old frozen untagged boards: resume rotation, retaining their current orbital angle.
s=s.replace('currentSettings.pinned_board_scale, .05, 2.5), false, true, false)', 'currentSettings.pinned_board_scale, .05, 2.5), false, false, false)')
p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/tests/browser_reward_options_smoke.py');s=p.read_text(encoding='utf-8');anchor='                assert not browser.errors, browser.errors';extra='''                browser.evaluate("""window.tntInput = document.querySelector('[data-option=fuse_seconds]');
                    tntInput.focus();tntInput.value='';tntInput.dispatchEvent(new Event('input',{bubbles:true}));""")
                assert browser.evaluate("mappings.find(r=>r.target==='spawn_tnt').fuse_seconds") == 4
                browser.evaluate("tntInput.blur()")
                assert browser.evaluate("tntInput.value") == '4'
                for value in ['0','1.25','0.05']:
                    browser.evaluate(f"tntInput.value='{value}';tntInput.dispatchEvent(new Event('input',{{bubbles:true}}));")
                    assert browser.evaluate("tntInput.checkValidity()")
                    browser.evaluate("save(false)")
                    saved = web.CONTROLLER.state()['bridge']['gift_actions']
                    assert next(r for r in saved if r['target']=='spawn_tnt')['fuse_seconds'] == float(value)
                browser.evaluate("tntInput.value='-1';tntInput.dispatchEvent(new Event('input',{bubbles:true}));")
                assert browser.evaluate("!tntInput.checkValidity()")
                assert browser.evaluate("mappings.find(r=>r.target==='spawn_tnt').fuse_seconds") == .05
                browser.evaluate("window.desktopClosing=true; window.closeEvent=new Event('beforeunload',{cancelable:true});window.dispatchEvent(closeEvent)")
                assert browser.evaluate("!closeEvent.defaultPrevented"), 'Desktop close must bypass browser unload lock'
                print('NUMERIC_INPUT_OK: blank retains value, zero TNT, fractional seconds, invalid draft isolation, desktop close bypass')
''';assert anchor in s;s=s.replace(anchor,extra+anchor);p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/src/test/java/vn/deadchan/tiktokmob/RewardOptionChecks.java');s=p.read_text(encoding='utf-8').replace('        double height = 64;', '        check(RewardOptions.ticks("{\\"fuse_seconds\\":0}", "fuse_seconds", 4) == 0, "Zero fuse means immediate explosion");\n        double height = 64;');p.write_text(s,encoding='utf-8')
