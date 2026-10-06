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
                browser.evaluate("showTab('gifts'); mappings = ['troll_pumpkin','spawn_tnt','troll_anvil','sky_launch','troll_cobweb'].map((target,i) => ({gift_name:'Test '+i, gift_id:String(900+i), action:'special', target, amount:1})); renderMappings(); renderLivePanel();")
                assert browser.evaluate("document.querySelectorAll('.reward-option').length") == 6
                assert browser.evaluate("document.querySelectorAll('.reward-player-damage').length") == 1
                assert browser.evaluate("document.querySelector('.reward-player-damage').value") == 'true'
                browser.evaluate("const damage = document.querySelector('.reward-player-damage'); damage.value = 'false'; damage.dispatchEvent(new Event('change', {bubbles:true}));")
                browser.evaluate("document.querySelectorAll('.reward-option').forEach(input => { input.value = '3'; input.dispatchEvent(new Event('input', {bubbles:true})); }); scheduleAutoSave();")
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    saved = browser.evaluate("(async () => (await (await fetch('/api/state')).json()).bridge.gift_actions)()")
                    if len(saved) == 5 and saved[4].get('radius') == 3: break
                    time.sleep(0.1)
                assert len(saved) == 5 and saved[4]['radius'] == 3 and saved[4]['duration_seconds'] == 3, saved
                assert saved[0]['duration_seconds'] == 3 and saved[1]['fuse_seconds'] == 3
                assert saved[2]['distance'] == 3 and saved[3]['height'] == 3
                assert saved[1]['damage_players'] is False
                shot = browser.command('Page.captureScreenshot', format='png', captureBeyondViewport=True)
                (screenshots / 'reward-options.png').write_bytes(base64.b64decode(shot['data']))
                browser.command('Page.reload')
                time.sleep(.75)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if browser.evaluate("typeof state !== 'undefined' && !!state && !document.querySelector('#loading')"): break
                    time.sleep(.1)
                assert browser.evaluate("[...document.querySelectorAll('.reward-option')].every(i => Number(i.value) === 3)")
                assert browser.evaluate("document.querySelector('.reward-player-damage').value") == 'false'
                browser.evaluate("""mappings = [{gift_name:'Creeper',action:'mob',target:'minecraft:creeper',amount:1},
                    {gift_name:'Troll Creeper',action:'special',target:'troll_creeper',amount:1},
                    {gift_name:'TNT',action:'special',target:'spawn_tnt',amount:1}]; renderMappings();
                    document.querySelectorAll('.reward-blocks').forEach((input,i) => {
                        input.value = i === 1 ? 'false' : 'true'; input.dispatchEvent(new Event('change',{bubbles:true}));
                    });
                    document.querySelector('#creeper_break_blocks').checked = true;
                    document.querySelector('#tnt_break_blocks').checked = false;""")
                assert browser.evaluate("collectPayload().bridge.gift_actions.map(r=>r.break_blocks)") == [True,False,True]
                browser.evaluate("save(false)")
                saved = web.CONTROLLER.state()
                assert saved['mod']['creeper_break_blocks'] is True and saved['mod']['tnt_break_blocks'] is False
                assert [r['break_blocks'] for r in saved['bridge']['gift_actions']] == [True,False,True]
                browser.command('Page.reload')
                time.sleep(.75)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if browser.evaluate("typeof state !== 'undefined' && !!state && !document.querySelector('#loading')"): break
                    time.sleep(.1)
                assert browser.evaluate("[...document.querySelectorAll('.reward-blocks')].map(i=>i.value)") == ['true','false','true']
                assert browser.evaluate("document.querySelector('#creeper_break_blocks').checked") is True
                assert browser.evaluate("document.querySelector('#tnt_break_blocks').checked") is False
                browser.evaluate("""showTab('gifts');window.tntInput = document.querySelector('[data-option=fuse_seconds]');
                    tntInput.focus();tntInput.value='';tntInput.dispatchEvent(new Event('input',{bubbles:true}));""")
                assert browser.evaluate("mappings.find(r=>r.target==='spawn_tnt').fuse_seconds") == 4
                browser.evaluate("tntInput.dispatchEvent(new Event('blur'))")
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
                from browser_enchant_controls import check_enchant_controls
                check_enchant_controls(browser)
                assert not browser.errors, browser.errors
                print('REWARD_OPTIONS_BROWSER_OK: six controls, edit, autosave, reload')
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)
            server.shutdown()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
