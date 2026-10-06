from pathlib import Path
p=Path('TikTokMobForge/tests/browser_pin_smoke.py');s=p.read_text(encoding='utf-8');a='                assert browser.evaluate("collectPayload().mod.pinned_board_width") == 1.4';b='''                browser.evaluate("""window.resizeBoardTest = (side, dx, dy) => {
                    const h = document.querySelector(`[data-board-resize="${side}"]`);
                    h.setPointerCapture = () => {};
                    h.dispatchEvent(new PointerEvent('pointerdown', {bubbles:true,pointerId:7,clientX:100,clientY:100}));
                    h.dispatchEvent(new PointerEvent('pointermove', {bubbles:true,pointerId:7,clientX:100+dx,clientY:100+dy}));
                    h.dispatchEvent(new PointerEvent('pointerup', {bubbles:true,pointerId:7}));
                }; resizeBoardTest('e', 30, 0);""")
                assert browser.evaluate("collectPayload().mod.pinned_board_width") > 1.4
                browser.evaluate("resizeBoardTest('s', 0, 20)")
                assert browser.evaluate("collectPayload().mod.pinned_board_height") > 1.6
                browser.evaluate("resizeBoardTest('se', -30, -20)")
                assert browser.evaluate("collectPayload().mod.pinned_board_scale") < 1.25
                browser.evaluate("""for (const [id,v] of [['scale','1.25'],['width','1.4'],['height','1.6']]) {
                    const el=document.getElementById('pinned_board_'+id); el.value=v;
                    el.dispatchEvent(new Event('input',{bubbles:true}));
                }""")
'''+a
assert a in s;s=s.replace(a,b,1);p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/src/test/java/vn/deadchan/tiktokmob/BoardTextChecks.java');s=p.read_text(encoding='utf-8');a='    static void run() {';b=a+'''
        var caption = new BoardCaption("Tuấn 😀", "Xin chào: bảng\\nhai mặt", "#ffd99b", "#f4f7fb", .05, 50, 40);
        if (!caption.equals(BoardCaption.decode(BoardCaption.encode(caption))))
            throw new AssertionError("Hologram caption lost Unicode, newline or layout");
        if (BoardCaption.decode("bad!") != null) throw new AssertionError("Invalid caption accepted");
''';s=s.replace(a,b);p.write_text(s,encoding='utf-8')
