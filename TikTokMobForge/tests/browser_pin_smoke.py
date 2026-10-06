"""Exercise the pinned-comment controls through the real web API in headless Chrome."""
import json
import base64
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch
import urllib.request

from websockets.sync.client import connect
from browser_settings_smoke import Browser
from test_settings import isolated_settings, web


def main():
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    calls = []
    with isolated_settings(), tempfile.TemporaryDirectory(prefix="tiktok-pin-") as profile, \
            web.ThreadingHTTPServer(("127.0.0.1", 0), web.Handler) as server:
        # Stable layout fixture independent of the user's saved default profile.
        web.CONTROLLER.save({"mod": {"pinned_board_scale": 1, "pinned_board_width": 1, "pinned_board_height": 1}})
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        process = subprocess.Popen([str(chrome), "--headless=new", "--no-first-run", "--disable-gpu",
            "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            port_file = Path(profile) / "DevToolsActivePort"
            deadline = time.monotonic() + 15
            while not port_file.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            assert port_file.exists(), "Chrome did not start"
            port = int(port_file.read_text().splitlines()[0])
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json") as response:
                target = next(item for item in json.load(response) if item["type"] == "page")
            with connect(target["webSocketDebuggerUrl"]) as socket:
                browser = Browser(socket)
                browser.command("Runtime.enable")
                browser.command("Page.enable")
                browser.command("Page.navigate", url=f"http://127.0.0.1:{server.server_port}/?view=tests")
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if browser.evaluate("document.querySelector('#testPinBtn') && !document.querySelector('#loading')"):
                        break
                    time.sleep(0.1)
                assert browser.evaluate("document.querySelector('#testPinBtn') !== null")
                assert browser.evaluate("document.querySelector('#tab-settingsPinnedBoard') !== null")
                assert browser.evaluate("document.querySelector('#pinned_board_scale').value") == "1"
                browser.evaluate("""showTab('settings'); showSettingsTab('settingsPinnedBoard');
                    const scale = document.querySelector('#pinned_board_scale');
                    scale.value = '1.25'; scale.dispatchEvent(new Event('input', {bubbles:true}));
                    const border = document.querySelector('#pinned_board_border');
                    border.value = 'magenta'; border.dispatchEvent(new Event('input', {bubbles:true}));
                    document.querySelector('#pinnedBoardAvatar').setPointerCapture = () => {};
                    document.querySelector('#pinnedBoardAvatar').dispatchEvent(new PointerEvent('pointerdown',
                        {bubbles:true, pointerId:1, clientX:100, clientY:100}));
                    const rect = document.querySelector('#pinnedBoardPreview').getBoundingClientRect();
                    document.querySelector('#pinnedBoardAvatar').dispatchEvent(new PointerEvent('pointermove',
                        {bubbles:true, pointerId:1, clientX:rect.left + rect.width * .3,
                        clientY:rect.top + rect.height * .6}));
                    document.querySelector('#pinnedBoardAvatar').dispatchEvent(new PointerEvent('pointerup',
                        {bubbles:true, pointerId:1}));""")
                assert browser.evaluate("document.querySelector('#pinned_board_avatar_x').value") == "30"
                assert browser.evaluate("document.querySelector('#pinned_board_avatar_y').value") == "60"
                browser.evaluate("""{ document.querySelector('#pinnedBoardContent').setPointerCapture = () => {};
                    const rect = document.querySelector('#pinnedBoardPreview').getBoundingClientRect();
                    const content = document.querySelector('#pinnedBoardContent');
                    content.dispatchEvent(new PointerEvent('pointerdown',
                        {bubbles:true, pointerId:2, clientX:rect.left + rect.width / 2,
                        clientY:rect.top + rect.height / 2}));
                    content.dispatchEvent(new PointerEvent('pointermove',
                        {bubbles:true, pointerId:2, clientX:rect.left + rect.width * .6,
                        clientY:rect.top + rect.height * .4}));
                    content.dispatchEvent(new PointerEvent('pointerup', {bubbles:true, pointerId:2})); }""")
                assert browser.evaluate("document.querySelector('#pinned_board_content_x').value") == "60"
                assert browser.evaluate("document.querySelector('#pinned_board_content_y').value") == "40"
                browser.evaluate("""for (const [id, v] of [['pinned_board_width', '1.4'], ['pinned_board_height', '1.6']]) {
                    const input = document.getElementById(id); input.value = v;
                    input.dispatchEvent(new Event('input', {bubbles:true}));
                }""")
                browser.evaluate("""window.resizeBoardTest = (side, dx, dy) => {
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
                assert browser.evaluate("collectPayload().mod.pinned_board_width") == 1.4
                assert browser.evaluate("collectPayload().mod.pinned_board_height") == 1.6
                assert browser.evaluate("document.querySelector('#pinnedBoardPreview').style.width") == "875px"
                assert browser.evaluate("document.querySelector('#pinnedBoardPreview').style.height") == "300px"
                browser.evaluate("""{
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
                assert browser.evaluate("collectPayload().mod.pinned_board_scale") == 1.25
                assert browser.evaluate("collectPayload().mod.pinned_board_border") == "magenta"
                assert browser.evaluate("document.querySelector('#pinnedBoardPreview').style.borderColor") == "rgb(189, 85, 183)"
                if os.environ.get("PIN_BOARD_SCREENSHOT"):
                    rect = browser.evaluate("""(() => { const r = document.querySelector('#pinnedBoardPreview').getBoundingClientRect();
                        return {x:r.left, y:r.top + window.scrollY, width:r.width, height:r.height, scale:1}; })()""")
                    image = browser.command("Page.captureScreenshot", format="png", clip=rect, captureBeyondViewport=True)
                    Path(os.environ["PIN_BOARD_SCREENSHOT"]).write_bytes(base64.b64decode(image["data"]))
                browser.evaluate("save(false)")
                assert web.CONTROLLER.state()["mod"]["pinned_board_width"] == 1.4
                assert web.CONTROLLER.state()["mod"]["pinned_board_rotation_speed"] == 2.5
                assert web.CONTROLLER.state()["mod"]["pinned_board_author_x"] == 70
                assert web.CONTROLLER.state()["mod"]["pinned_board_height"] == 1.6
                assert web.CONTROLLER.state()["mod"]["pinned_board_avatar_x"] == 30
                assert web.CONTROLLER.state()["mod"]["pinned_board_content_y"] == 40

                def start(config, request):
                    calls.append(request)
                    return {"running": False, "sent": 1, "total": 1, "message": "Mock sent"}

                with patch.object(web.CONTROLLER.test_runner, "start", side_effect=start):
                    browser.evaluate("document.querySelector('#testPinAuthor').value = 'Admin'; document.querySelector('#testPinContent').value = 'Bình luận mẫu'; document.querySelector('#testPinBtn').click()")
                    deadline = time.monotonic() + 10
                    while len(calls) < 1 and time.monotonic() < deadline:
                        time.sleep(0.1)
                    assert calls[0]["mode"] == "pin" and calls[0]["pin_text"] == "Bình luận mẫu"
                    browser.evaluate("document.querySelector('#testUnpinBtn').click()")
                    time.sleep(.2)
                    assert len(calls) == 1, "Delete help must not send a global-clear command"
                    assert browser.evaluate("document.querySelector('#toastHost').textContent.includes('nhấn X')")
                    import pinned_overlay
                    from bridge import send_interaction, pin_avatar_png
                    from PIL import Image
                    import io
                    with patch.object(pinned_overlay, "STATE", Path(profile) / "overlay.json"), patch("bridge.socket.create_connection"):

                        picture = pin_avatar_png("", "Admin")
                        assert Image.open(io.BytesIO(picture)).size == (256, 256)
                        send_interaction({"live_comments_only": False, "minecraft_host": "localhost", "minecraft_port": 9876}, "pin_comment", "Admin", "test", "", "<b>Xin chào</b>", avatar_png=picture)
                        browser.command("Page.navigate", url=f"http://127.0.0.1:{server.server_port}/pinned-overlay.html")
                        deadline = time.monotonic() + 10
                        while time.monotonic() < deadline:
                            if browser.evaluate("document.querySelector('#board') && !document.querySelector('#board').hidden && document.querySelector('#avatar').naturalWidth === 256"):
                                break
                            time.sleep(.1)
                        assert browser.evaluate("document.querySelector('#avatar').naturalWidth") == 256
                        assert browser.evaluate("document.querySelector('#comment').textContent") == "<b>Xin chào</b>"
                        assert browser.evaluate("document.querySelector('#comment b') === null")
                        assert browser.evaluate("document.querySelector('#board').style.height") == "300px"
                        browser.evaluate("""window.checkLongPin = () => {
                            const text = 'Bình luận rất dài 😀 '.repeat(24);
                            renderPinnedOverlay({author:'Tên người dùng rất dài 😀',text,style:{}});
                            const rect = id => document.getElementById(id).getBoundingClientRect();
                            const a=rect('initial'), n=rect('author'), c=rect('content'), b=rect('board');
                            return n.top >= a.bottom && n.right < c.left && c.top > b.top && c.bottom < b.bottom
                              && Math.abs((a.left+a.right)-(n.left+n.right)) < 2;
                        };""")
                        assert browser.evaluate("checkLongPin()"), "Long comment overlaps author/avatar or leaves board"
                        if os.environ.get("PIN_LONG_SCREENSHOT"):
                            shot = browser.command("Page.captureScreenshot", format="png")
                            Path(os.environ["PIN_LONG_SCREENSHOT"]).write_bytes(base64.b64decode(shot["data"]))
                        if os.environ.get("PIN_NATIVE_EXE"):
                            frame_root = Path(profile) / "frames"
                            native_env = {**os.environ, "PIN_BOARD_FRAME_ROOT": str(frame_root)}
                            native = subprocess.Popen([os.environ["PIN_NATIVE_EXE"], "--pin-overlay", f"http://127.0.0.1:{server.server_port}"], env=native_env, creationflags=subprocess.CREATE_NO_WINDOW)
                            try:
                                deadline = time.monotonic() + 20
                                while not (frame_root / "frame.json").exists() and time.monotonic() < deadline:
                                    assert native.poll() is None, "Native WebView exited"
                                    time.sleep(.2)
                                manifest = json.loads((frame_root / "frame.json").read_text(encoding="utf-8-sig"))
                                assert manifest["token"] == pinned_overlay.snapshot()["token"]
                                frame = Image.open(frame_root / manifest["file"])
                                assert frame.size == (1400, 480), frame.size
                                assert frame.mode == "RGBA", frame.mode
                                assert frame.getpixel((0,0))[3] == 0, "Rounded corner lost transparency"
                                assert frame.getpixel((700,240))[3] > 200, "Frame is blank"
                                frame.save(os.environ["PIN_NATIVE_SCREENSHOT"])
                                old_file = manifest["file"]
                                web.CONTROLLER.save({"mod": {"pinned_board_width": 1.8, "pinned_board_height": 1.2}})
                                deadline = time.monotonic() + 15
                                while time.monotonic() < deadline:
                                    manifest = json.loads((frame_root / "frame.json").read_text(encoding="utf-8-sig"))
                                    if manifest["file"] != old_file and manifest["width"] == 1800 and manifest["height"] == 360:
                                        break
                                    time.sleep(.2)
                                assert (manifest["width"], manifest["height"]) == (1800, 360), manifest
                                old_file = manifest["file"]
                                send_interaction({"live_comments_only": False, "minecraft_host": "localhost", "minecraft_port": 9876}, "pin_comment", "Tuấn 😀", "test", "", "Bảng 3D sắc nét", avatar_png=picture)
                                deadline = time.monotonic() + 15
                                while time.monotonic() < deadline:
                                    manifest = json.loads((frame_root / "frame.json").read_text(encoding="utf-8-sig"))
                                    if manifest["file"] != old_file and manifest["token"] == pinned_overlay.snapshot()["token"]:
                                        break
                                    time.sleep(.2)
                                assert manifest["token"] == pinned_overlay.snapshot()["token"]
                                assert manifest["file"] != old_file
                                # Rapid updates used to overwrite one frame and remove every older PNG after three captures.
                                tokens = [manifest["token"]]
                                for index in range(5):
                                    send_interaction({"live_comments_only": False, "minecraft_host": "localhost", "minecraft_port": 9876},
                                        "pin_comment", "Board " + str(index), "test", "", "Retained comment " + str(index), avatar_png=picture)
                                    tokens.append(pinned_overlay.snapshot()["token"])
                                deadline = time.monotonic() + 25
                                while time.monotonic() < deadline and not all((frame_root / (token + '.json')).exists() for token in tokens):
                                    time.sleep(.2)
                                files = []
                                for token in tokens:
                                    saved = json.loads((frame_root / (token + '.json')).read_text(encoding='utf-8-sig'))
                                    assert saved['token'] == token
                                    assert (frame_root / saved['file']).is_file(), "Old board PNG was evicted"
                                    files.append(saved['file'])
                                assert len(set(files)) == len(tokens), "Boards share a mutable texture file"
                                print('MULTI_BOARD_FRAMES_OK: rapid pins, six retained token manifests and independent PNGs')

                            finally:
                                native.terminate()
                                native.wait(timeout=5)
                        if os.environ.get("PIN_OVERLAY_SCREENSHOT"):
                            shot = browser.command("Page.captureScreenshot", format="png")
                            Path(os.environ["PIN_OVERLAY_SCREENSHOT"]).write_bytes(base64.b64decode(shot["data"]))
                        send_interaction({"live_comments_only": False, "minecraft_host": "localhost", "minecraft_port": 9876}, "pin_comment", "Admin", "test", "", "")
                        deadline = time.monotonic() + 5
                        while time.monotonic() < deadline and not browser.evaluate("document.querySelector('#board').hidden"):
                            time.sleep(.1)
                        assert browser.evaluate("document.querySelector('#board').hidden")
                    assert not browser.errors, browser.errors
        finally:
            process.terminate()
            process.wait(timeout=5)
            server.shutdown()
            thread.join(timeout=5)
    print("BROWSER_PIN_OK")


if __name__ == "__main__":
    main()

