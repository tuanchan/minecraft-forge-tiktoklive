"""Run the real settings page against temporary configs, using headless Chrome."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch
import urllib.request

from websockets.sync.client import connect
from test_settings import isolated_settings, web, ROOT


class Browser:
    def __init__(self, socket):
        self.socket = socket
        self.sequence = 0
        self.errors = []

    def command(self, method, **params):
        self.sequence += 1
        self.socket.send(json.dumps({"id": self.sequence, "method": method, "params": params}))
        while True:
            message = json.loads(self.socket.recv(timeout=15))
            if message.get("method") == "Runtime.exceptionThrown":
                self.errors.append(message["params"])
            if message.get("id") == self.sequence:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message.get("result", {})

    def evaluate(self, expression):
        result = self.command("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in result:
            raise AssertionError(result["exceptionDetails"])
        return result.get("result", {}).get("value")


def main():
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    screenshots = ROOT / "tests" / "artifacts"
    screenshots.mkdir(exist_ok=True)
    with isolated_settings(), tempfile.TemporaryDirectory(prefix="tiktok-browser-") as profile, \
        web.ThreadingHTTPServer(("127.0.0.1", 0), web.Handler) as server:
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
            port = int(port_file.read_text().splitlines()[0])
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json") as response:
                target = next(item for item in json.load(response) if item["type"] == "page")
            with connect(target["webSocketDebuggerUrl"]) as socket:
                browser = Browser(socket)
                browser.command("Runtime.enable")
                browser.command("Page.enable")
                browser.command("Emulation.setDeviceMetricsOverride", width=1440, height=1100, deviceScaleFactor=1, mobile=False)
                browser.command("Page.navigate", url=f"http://127.0.0.1:{server.server_port}/?view=settings")
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if browser.evaluate("document.querySelector('#notification_enabled') && !document.querySelector('#loading')"):
                        break
                    time.sleep(0.1)
                assert browser.evaluate("!document.querySelector('#loading')"), "page initialization failed"
                browser.evaluate("showTab('live'); document.querySelector('#giftPreview .gift-card').dispatchEvent(new MouseEvent('contextmenu', {bubbles:true, cancelable:true}))")
                assert browser.evaluate("document.querySelector('.gift-note-dialog').open")
                browser.evaluate("document.querySelector('.gift-note-dialog input').value = 'Enchant 5 +1 <test>'; document.querySelector('.gift-note-dialog button[value=save]').click()")
                time.sleep(2)
                assert browser.evaluate("document.querySelector('.gift-panel-note').textContent") == 'Enchant 5 +1 <test>'
                assert browser.evaluate("document.querySelector('.gift-panel-note test') === null")
                saved = browser.evaluate("(async () => (await (await fetch('/api/state')).json()).bridge.gift_actions[0].panel_note)()")
                assert saved == 'Enchant 5 +1 <test>', saved
                shot = browser.command('Page.captureScreenshot', format='png', captureBeyondViewport=True)
                (screenshots / 'gift-panel-note.png').write_bytes(base64.b64decode(shot['data']))
                browser.command('Page.reload')
                time.sleep(2)
                assert browser.evaluate("document.querySelector('.gift-panel-note').textContent") == saved
                browser.evaluate("document.querySelector('#giftPreview .gift-card').dispatchEvent(new MouseEvent('contextmenu', {bubbles:true})); document.querySelector('.gift-note-dialog input').value = ''; document.querySelector('.gift-note-dialog button[value=save]').click()")
                time.sleep(2)
                assert browser.evaluate("document.querySelector('.gift-panel-note') === null")
                assert browser.evaluate("(async () => (await (await fetch('/api/state')).json()).bridge.gift_actions[0].panel_note)()") == ''
                print('GIFT_PANEL_NOTE_BROWSER_OK: edit, safe text, autosave, reload, removal')
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)
            server.shutdown()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
