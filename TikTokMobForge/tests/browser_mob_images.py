"""Exercise the real settings page and new HUD checkbox with isolated configs."""
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import urllib.request
from websockets.sync.client import connect
from browser_settings_smoke import Browser
from test_settings import isolated_settings, web, ROOT

with isolated_settings(), tempfile.TemporaryDirectory(prefix="guard-browser-") as profile, web.ThreadingHTTPServer(("127.0.0.1", 0), web.Handler) as server:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    process = subprocess.Popen([r"C:\Program Files\Google\Chrome\Application\chrome.exe", "--headless=new", "--no-first-run", "--disable-gpu", "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        port_file = Path(profile) / "DevToolsActivePort"
        deadline = time.monotonic() + 20
        while not port_file.exists() and time.monotonic() < deadline: time.sleep(.1)
        port = int(port_file.read_text().splitlines()[0])
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json") as response:
            target = next(x for x in json.load(response) if x["type"] == "page")
        with connect(target["webSocketDebuggerUrl"]) as socket:
            browser = Browser(socket)
            browser.command("Runtime.enable")
            browser.command("Page.enable")
            browser.command("Page.navigate", url=f"http://127.0.0.1:{server.server_port}/?view=settings")
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if browser.evaluate("!!document.querySelector('#show_death_counter') && !document.querySelector('#loading')"): break
                time.sleep(.1)
            browser.evaluate("""(() => {
                const selected = {view:'pig', follow:'enderman', comment:'cow', share:'skeleton', like:'creeper'};
                state.bridge.event_images = {follow:'/assets/custom/event-follow.png', comment:'/assets/custom/event-comment.png', like:'/assets/custom/event-like.png'};
                state.bridge.event_image_targets = {};
                for (const [slot, mob] of Object.entries(selected)) {
                    document.querySelector(`.event-editor[data-prefix=${slot}] .event-mob-dropdown`).dataset.value = `minecraft:${mob}`;
                }
                renderLivePanel(false); showTab('live');
            })()""")
            selected = {'view':'pig', 'follow':'enderman', 'comment':'cow', 'share':'skeleton', 'like':'creeper'}
            for slot, mob in selected.items():
                src = browser.evaluate(f"document.querySelector('#eventCards [data-event-kind={slot}] .mob-stage img').getAttribute('src')")
                assert 'id=minecraft%3A' + mob in src, (slot, src)
            assert browser.evaluate("eventMobImage('follow', {kind:'mob',target:'minecraft:enderman'}).startsWith('/api/icon')")
            browser.evaluate("state.bridge.event_image_targets.follow = 'enderman'")
            assert browser.evaluate("eventMobImage('follow', {kind:'mob',target:'minecraft:enderman'})") == '/assets/custom/event-follow.png'
            assert browser.evaluate("eventMobImage('follow', {kind:'mob',target:'minecraft:cow'}).startsWith('/api/icon')")
            browser.evaluate("state.bridge.event_image_targets = {}; renderLivePanel(false)")
            browser.command("Emulation.setDeviceMetricsOverride", width=1440, height=1000, deviceScaleFactor=1, mobile=False)
            time.sleep(6)
            assert browser.evaluate("[...document.querySelectorAll('#eventCards .mob-stage img')].every(x => x.complete && x.naturalWidth > 0)")
            screenshot = browser.command("Page.captureScreenshot", format="png", captureBeyondViewport=True)
            (ROOT / 'tests/artifacts/mob-images-fixed.png').write_bytes(base64.b64decode(screenshot['data']))
            assert not browser.errors, browser.errors
            print('MOB_IMAGES_OK: selected mob matches image; stale custom ignored; bound custom retained; images loaded')
            browser.command("Browser.close")
    finally:
        if process.poll() is None: process.terminate()
        process.wait(timeout=10)
        server.shutdown()
        thread.join(timeout=5)
