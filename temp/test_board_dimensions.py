from pathlib import Path
p=Path('TikTokMobForge/tests/browser_pin_smoke.py');s=p.read_text(encoding='utf-8');a='                assert browser.evaluate("collectPayload().mod.pinned_board_scale") == 1.25';b='''                browser.evaluate("""for (const [id, v] of [['pinned_board_width', '1.4'], ['pinned_board_height', '1.6']]) {
                    const input = document.getElementById(id); input.value = v;
                    input.dispatchEvent(new Event('input', {bubbles:true}));
                }""")
                assert browser.evaluate("collectPayload().mod.pinned_board_width") == 1.4
                assert browser.evaluate("collectPayload().mod.pinned_board_height") == 1.6
                assert browser.evaluate("document.querySelector('#pinnedBoardPreview').style.width") == "875px"
                assert browser.evaluate("document.querySelector('#pinnedBoardPreview').style.height") == "300px"
'''+a
assert a in s;s=s.replace(a,b);a='                assert web.CONTROLLER.state()["mod"]["pinned_board_avatar_x"] == 30';s=s.replace(a,'                assert web.CONTROLLER.state()["mod"]["pinned_board_width"] == 1.4\n                assert web.CONTROLLER.state()["mod"]["pinned_board_height"] == 1.6\n'+a);p.write_text(s,encoding='utf-8')
