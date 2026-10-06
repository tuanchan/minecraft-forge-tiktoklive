from pathlib import Path
p=Path('TikTokMobForge/tests/browser_pin_smoke.py');s=p.read_text(encoding='utf-8');a='                assert browser.evaluate("collectPayload().mod.pinned_board_scale") == 1.25';b='''                browser.evaluate("""{
                    const author=document.querySelector('#pinnedBoardAuthor');
                    author.setPointerCapture=()=>{};
                    const r=document.querySelector('#pinnedBoardPreview').getBoundingClientRect();
                    author.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:9}));
                    author.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerId:9,clientX:r.left+r.width*.7,clientY:r.top+r.height*.2}));
                    author.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:9}));
                    const speed=document.querySelector('#pinned_board_rotation_speed');speed.value='2.5';
                    speed.dispatchEvent(new Event('input',{bubbles:true}));
                }""")
                assert browser.evaluate("collectPayload().mod.pinned_board_author_x") == 70
                assert browser.evaluate("collectPayload().mod.pinned_board_author_y") == 20
                assert browser.evaluate("collectPayload().mod.pinned_board_content_x") == 60
                assert browser.evaluate("collectPayload().mod.pinned_board_content_y") == 40
'''+a
assert a in s;s=s.replace(a,b,1);a='                assert web.CONTROLLER.state()["mod"]["pinned_board_width"] == 1.4';s=s.replace(a,a+'\n                assert web.CONTROLLER.state()["mod"]["pinned_board_rotation_speed"] == 2.5\n                assert web.CONTROLLER.state()["mod"]["pinned_board_author_x"] == 70');p.write_text(s,encoding='utf-8')
