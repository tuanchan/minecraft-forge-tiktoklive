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
            for value in (False, True):
                result = browser.evaluate("""(async () => {
                    document.querySelector('#show_death_counter').checked = VALUE;
                    await save(false);
                    return (await (await fetch('/api/runtime-settings')).json()).mod.show_death_counter;
                })()""".replace("VALUE", str(value).lower()))
                assert result is value
            browser.command("Page.reload")
            time.sleep(1)
            assert browser.evaluate("document.querySelector('#show_death_counter').checked")
            for width, height, name in ((1440, 1100, "desktop"), (390, 844, "mobile")):
                browser.command("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=width < 600)
                browser.evaluate("showTab('settings'); showSettingsTab('settingsMobs')")
                time.sleep(.2)
                assert browser.evaluate("document.querySelector('#show_death_counter').offsetParent !== null")
                assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth")
                screenshot = browser.command("Page.captureScreenshot", format="png", captureBeyondViewport=True)
                (ROOT / "tests/artifacts" / f"guard-settings-{name}.png").write_bytes(base64.b64decode(screenshot["data"]))
            assert not browser.errors, browser.errors
            print("GUARD_SETTINGS_UI_OK: toggle persisted and reloaded; desktop/mobile; no JS errors")
            browser.command("Browser.close")
    finally:
        if process.poll() is None: process.terminate()
        process.wait(timeout=10)
        server.shutdown()
        thread.join(timeout=5)
