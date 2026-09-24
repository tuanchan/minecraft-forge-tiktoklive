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
                saved = browser.evaluate("""(async () => {
                    document.querySelector('#spawn_direction').value = 'left';
                    document.querySelector('#live_comments_only').checked = true;
                    await save(false);
                    return await (await fetch('/api/state')).json();
                })()""")
                assert saved['mod']['spawn_direction'] == 'left'
                assert saved['bridge']['live_comments_only'] is True
                assert browser.evaluate("document.querySelector('#spawn_direction').options.length") == 5
                assert browser.evaluate("document.querySelector('#settingsEventsHome #eventEditors') !== null")
                assert browser.evaluate("document.querySelectorAll('.event-editor').length") == 5
                view_saved = browser.evaluate("""(async () => {
                    document.querySelector('#view_enabled').checked = false;
                    document.querySelector('#view_interval_seconds').value = '17';
                    document.querySelector('#view_max_mobs_per_round').value = '8';
                    document.querySelector('.event-editor[data-prefix=view] .event-count').value = '2';
                    document.querySelector('#view_enabled').dispatchEvent(new Event('input', {bubbles:true}));
                    await save(false);
                    return (await (await fetch('/api/state')).json()).bridge;
                })()""")
                assert view_saved['view_enabled'] is False
                assert view_saved['view_interval_seconds'] == 17
                assert view_saved['view_max_mobs_per_round'] == 8
                assert view_saved['view_spawn_count'] == 2
                browser.evaluate("showTab('events')")
                time.sleep(0.2)
                shot = browser.command('Page.captureScreenshot', format='png', captureBeyondViewport=True)
                (screenshots / 'view-interactions.png').write_bytes(base64.b64decode(shot['data']))
                browser.evaluate("showTab('settings')")
                # Real tab buttons hide all other groups without losing form values.
                for group in ("settingsConnection", "settingsMobs", "settingsDisplay", "settingsContent",
                              "settingsPosition", "settingsRewards", "settingsVoice", "settingsVoiceQueue", "settingsInteractions"):
                    browser.evaluate(f"document.querySelector('[data-settings-tab={group}]').click()")
                    assert browser.evaluate("document.querySelectorAll('[data-settings-panel]:not([hidden])').length") == 1
                    assert browser.evaluate(f"document.querySelector('#{group}').getBoundingClientRect().height > 0")
                with patch.object(web.CONTROLLER, "spawn_bridge", return_value={"message": "Test requested"}) as launch:
                    browser.evaluate("document.querySelector('#testGiftAlertBtn').click()")
                    deadline = time.monotonic() + 5
                    while not launch.called and time.monotonic() < deadline:
                        time.sleep(0.05)
                    assert launch.call_args.args[0] == ["--test-gift-alert"]
                with patch.object(web.voicevox_tts, "list_voices", return_value={"voices": [
                        {"id": 3, "name": "ずんだもん — ノーマル"},
                        {"id": 0, "name": "四国めたん — あまあま"}]}):
                    changed_voice = browser.evaluate("""(async () => {
                        showTab('voicevox');
                        await loadVoicevoxCatalog();
                        const choice = document.querySelector('#voicevox_choice');
                        choice.value = '0'; choice.dispatchEvent(new Event('change', {bubbles:true}));
                        const preset = document.querySelector('#voicevox_preset');
                        preset.value = 'cute'; preset.dispatchEvent(new Event('change', {bubbles:true}));
                        document.querySelector('#gift_voicevox_volume').value = '0.65';
                        await save(false);
                        return (await (await fetch('/api/state')).json()).bridge;
                    })()""")
                    assert changed_voice["tts_provider"] == "elevenlabs"
                    assert changed_voice["tts_voicevox_speaker_id"] == 0
                    assert changed_voice["tts_voicevox_pitch"] == 0.06
                    assert changed_voice["gift_voicevox_volume"] == 0.65
                    assert browser.evaluate("document.querySelector('#voicevoxSettings').closest('[data-view]').dataset.view") == "voicevox"
                    assert browser.evaluate("!document.querySelector('#voicevoxSettings').hidden")
                    for width, height, name in ((1440, 1100, "desktop"), (390, 844, "mobile")):
                        browser.command("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=width < 600)
                        browser.evaluate("showTab('voicevox'); window.scrollTo({top:0, behavior:'instant'})")
                        time.sleep(0.3)
                        assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"voicevox {name} overflow"
                        screenshot = browser.command("Page.captureScreenshot", format="png")
                        (screenshots / f"voicevox-{name}.png").write_bytes(base64.b64decode(screenshot["data"]))
                    browser.command("Page.reload")
                    time.sleep(0.5)
                    deadline = time.monotonic() + 15
                    while browser.evaluate("!!document.querySelector('#loading')") and time.monotonic() < deadline:
                        time.sleep(0.1)
                    assert browser.evaluate("document.querySelector('#tts_provider').value") == "elevenlabs"
                    assert browser.evaluate("document.querySelector('#tts_voicevox_pitch').value") == "0.06"
                    edge_settings = browser.evaluate("""(async () => {
                        showTab('settings'); showSettingsTab('settingsVoice');
                        const provider = document.querySelector('#tts_provider');
                        provider.value = 'edge'; provider.dispatchEvent(new Event('change', {bubbles:true}));
                        const preset = document.querySelector('#edge_preset');
                        preset.value = 'cute'; preset.dispatchEvent(new Event('change', {bubbles:true}));
                        document.querySelector('#tts_test_text').value = 'Xin chào mọi người!';
                        await save(false);
                        return (await (await fetch('/api/state')).json()).bridge;
                    })()""")
                    assert edge_settings["tts_provider"] == "edge"
                    assert edge_settings["tts_edge_voice"] == "vi-VN-HoaiMyNeural"
                    assert edge_settings["tts_edge_pitch"] == 60
                    assert edge_settings["tts_edge_rate"] == 10
                    assert browser.evaluate("!document.querySelector('#edgeSettings').hidden && !document.querySelector('[data-view=voicevox]').classList.contains('active')")
                    for width, height, name in ((1440, 1100, "desktop"), (390, 844, "mobile")):
                        browser.command("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=width < 600)
                        browser.evaluate("document.querySelector('#settingsVoice').scrollIntoView({behavior:'instant'})")
                        time.sleep(0.3)
                        assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Vietnamese {name} overflow"
                        screenshot = browser.command("Page.captureScreenshot", format="png")
                        (screenshots / f"vietnamese-{name}.png").write_bytes(base64.b64decode(screenshot["data"]))
                    browser.evaluate("""(async () => {
                        document.querySelector('#tts_provider').value = 'elevenlabs'; renderTtsProvider();
                        await save(false);
                    })()""")
                    assert browser.evaluate("!document.querySelector('#api_key').closest('label').hidden")
                browser.command("Emulation.setDeviceMetricsOverride", width=1440, height=1100, deviceScaleFactor=1, mobile=False)
                # Change controls in the page, use its save code, then read persisted state.
                saved = browser.evaluate("""(async () => {
                    document.querySelector('#tts_volume').value = '0.35';
                    document.querySelector('#display_comment_text').checked = true;
                    document.querySelector('#notification_title_color').value = '#12ab34';
                    document.querySelector('#notification_overflow_policy').value = 'drop_oldest';
                    document.querySelector('#tts_voice_id').value = 'manual-voice-id';
                    document.querySelector('#tts_model_id').value = 'manual-model-id';
                    document.querySelector('#tts_language_code').value = '';
                    document.querySelector('#like_spawn_count').value = '2';
                    document.querySelector('#tts_volume').dispatchEvent(new Event('input', { bubbles: true }));
                    await new Promise(resolve => setTimeout(resolve, 1500));
                    if (!document.querySelector('#saveStatus').textContent.includes('Đã')) throw new Error('Autosave did not finish');
                    return (await fetch('/api/state')).json();
                })()""")
                assert saved["bridge"]["tts_volume"] == 0.35
                assert saved["bridge"]["display_comment_text"] is True
                assert saved["bridge"]["tts_voice_id"] == "manual-voice-id"
                assert saved["bridge"]["tts_model_id"] == "manual-model-id"
                assert saved["bridge"]["tts_language_code"] == ""
                assert saved["bridge"]["like_spawn_count"] == 2
                assert saved["mod"]["notification_title_color"] == "#12ab34"
                assert saved["mod"]["notification_overflow_policy"] == "drop_oldest"
                # Level selection and bulk placement must persist through the real API.
                changed = browser.evaluate("""(async () => {
                    applyReward(0, 'special|enchant_armor');
                    const level = document.querySelector('.reward-level');
                    level.value = '12'; level.dispatchEvent(new Event('input', {bubbles:true}));
                    document.querySelector('[data-position-kind="comment"] .position-tick').checked = true;
                    document.querySelector('[data-position-kind="gift"] .position-tick').checked = true;
                    document.querySelector('#bulkPositionX').value = '85';
                    document.querySelector('#bulkPositionY').value = '10';
                    document.querySelector('#bulkPositionScale').value = '1.5';
                    document.querySelector('#applyPositionSelected').click();
                    await save(false);
                    return (await fetch('/api/state')).json();
                })()""")
                assert changed["bridge"]["gift_actions"][0]["level"] == 12
                assert changed["mod"]["notification_positions"]["gift"] == {"x": 85, "y": 10, "scale": 1.5}
                assert changed["mod"]["notification_positions"]["comment"]["x"] == 85
                assert changed["mod"]["notification_positions"]["like"]["x"] == 50
                assert browser.evaluate("""(async () => {
                    document.querySelector('#bulkPositionX').value = '20';
                    document.querySelector('#applyPositionAll').click();
                    await save(false);
                    const state = await (await fetch('/api/state')).json();
                    return Object.values(state.mod.notification_positions).every(p => p.x === 20);
                })()""")
                original_save = web.CONTROLLER.save
                def slow_save(payload):
                    time.sleep(0.4)
                    return original_save(payload)
                with patch.object(web.CONTROLLER, "save", side_effect=slow_save):
                    assert browser.evaluate("""(async () => {
                        const field = document.querySelector('#tts_volume');
                        field.value = '0.4';
                        const pending = save(false);
                        await new Promise(resolve => setTimeout(resolve, 100));
                        field.value = '0.55'; field.dispatchEvent(new Event('input', { bubbles: true }));
                        await pending;
                        const persisted = await (await fetch('/api/state')).json();
                        return persisted.bridge.tts_volume;
                    })()""") == 0.55
                browser.evaluate("document.querySelector('#tts_volume').value = '0.35'; save(false)")
                # Exercise test buttons via real HTTP routes; only the sending worker is mocked.
                test_calls = []
                def start_test(config, request):
                    test_calls.append((config, request))
                    return {"running": False, "sent": 1, "total": 1, "message": "Mock test sent"}
                with patch.object(web.CONTROLLER.test_runner, "start", side_effect=start_test):
                    browser.evaluate("showTab('tests')")
                    for selector in ("#testSingleMobBtn", "#testFullMobsBtn", "#testSpamBtn", '[data-test-gift="0"]', "#testAllGiftsBtn"):
                        browser.evaluate(f"document.querySelector({json.dumps(selector)}).click()")
                        deadline = time.monotonic() + 10
                        while browser.evaluate("testSubmitting") and time.monotonic() < deadline:
                            time.sleep(0.1)
                    assert [call[1]["mode"] for call in test_calls] == ["mob", "all_mobs", "spam", "gift", "all_gifts"], test_calls
                    assert test_calls[0][0]["tts_volume"] == 0.35
                # Invalid edits remain unsaved and are visibly reported without moving tabs.
                assert browser.evaluate("""(async () => {
                    showTab('settings');
                    const field = document.querySelector('#tts_volume');
                    field.value = '2'; field.dispatchEvent(new Event('input', { bubbles: true }));
                    await new Promise(resolve => setTimeout(resolve, 1300));
                    const ok = document.querySelector('#saveStatus').classList.contains('error');
                    field.value = '0.35'; field.dispatchEvent(new Event('input', { bubbles: true }));
                    await save(false); return ok;
                })()""")
                # Moving the single event editor between tabs must preserve edits.
                assert browser.evaluate("showTab('events'); showTab('settings'); document.querySelector('#like_spawn_count').value") == "2"
                browser.command("Page.reload")
                time.sleep(0.5)
                deadline = time.monotonic() + 15
                while browser.evaluate("!!document.querySelector('#loading')") and time.monotonic() < deadline:
                    time.sleep(0.1)
                assert browser.evaluate("document.querySelector('#tts_volume').value") == "0.35"
                assert browser.evaluate("document.querySelector('.reward-level').value") == "12"
                assert browser.evaluate("document.querySelector('[data-position-kind=gift] [data-axis=x]').value") == "20"
                # Default rewards live outside the gift mappings and survive a save/reload.
                assert browser.evaluate("""(async () => {
                    showTab('settings'); showSettingsTab('settingsRewards');
                    const count = mappings.length;
                    document.querySelector('#unmapped_gift_mode').value = 'reward';
                    document.querySelector('#unmapped_gift_mode').dispatchEvent(new Event('change', {bubbles:true}));
                    document.querySelector('.unmapped-reward .dropdown-toggle').click();
                    const search = document.querySelector('.unmapped-reward .dropdown-search');
                    search.value = 'minecraft:diamond_sword'; search.dispatchEvent(new Event('input', {bubbles:true}));
                    document.querySelector('.unmapped-reward [data-option-value="item|minecraft:diamond_sword"]').click();
                    document.querySelector('#unmapped_gift_amount').value = '3';
                    await save(false);
                    const saved = await (await fetch('/api/state')).json();
                    return saved.bridge.unmapped_gift_mode === 'reward'
                      && saved.bridge.unmapped_gift_target === 'minecraft:diamond_sword'
                      && saved.bridge.unmapped_gift_amount === 3 && mappings.length === count;
                })()""")
                with patch.object(web.CONTROLLER.gift_updater, "start", return_value={"running": True, "message": "Đang kiểm tra cập nhật"}) as update:
                    browser.evaluate("showTab('gifts'); document.querySelector('#updateGiftsBtn').click()")
                    deadline = time.monotonic() + 5
                    while not update.called and time.monotonic() < deadline:
                        time.sleep(0.1)
                    update.assert_called_once()
                for width, height, name in ((1440, 1100, "desktop"), (390, 844, "mobile")):
                    browser.command("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=width < 600)
                    browser.evaluate("showTab('settings'); showSettingsTab('settingsDisplay'); renderSettingsPreview();")
                    time.sleep(0.3)
                    assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"{name} horizontal overflow"
                    screenshot = browser.command("Page.captureScreenshot", format="png")
                    (screenshots / f"settings-{name}.png").write_bytes(base64.b64decode(screenshot["data"]))
                    browser.evaluate("showSettingsTab('settingsPosition'); document.querySelector('#notification_positions').scrollIntoView(); renderSettingsPreview();")
                    time.sleep(0.3)
                    screenshot = browser.command("Page.captureScreenshot", format="png")
                    (screenshots / f"positions-{name}.png").write_bytes(base64.b64decode(screenshot["data"]))
                    browser.evaluate("showTab('gifts')")
                    time.sleep(0.3)
                    assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"gifts {name} overflow"
                    screenshot = browser.command("Page.captureScreenshot", format="png")
                    (screenshots / f"gift-levels-{name}.png").write_bytes(base64.b64decode(screenshot["data"]))
                    browser.evaluate("showTab('settings'); showSettingsTab('settingsRewards')")
                    assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"default reward {name} overflow"
                    screenshot = browser.command("Page.captureScreenshot", format="png")
                    (screenshots / f"unmapped-gifts-{name}.png").write_bytes(base64.b64decode(screenshot["data"]))
                    browser.evaluate("showTab('tests')")
                    time.sleep(0.3)
                    assert browser.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"test tab {name} overflow"
                    screenshot = browser.command("Page.captureScreenshot", format="png")
                    (screenshots / f"tests-{name}.png").write_bytes(base64.b64decode(screenshot["data"]))
                    browser.evaluate("showTab('settings')")
                # Simulate game writes against the same file; the page must update
                # without a reload and preserve an independent local draft.
                runtime_path = Path(web.CONTROLLER.state()["bridge"]["runtime_settings_path"])
                from config_service import load_json, save_json
                from runtime_settings import config_file_lock
                with config_file_lock(runtime_path):
                    changed = load_json(runtime_path, {})
                    changed.update(max_mobs_total=777, share_spawn_count=6, likes_per_skeleton=200)
                    save_json(runtime_path, changed)
                deadline = time.monotonic() + 8
                while browser.evaluate("document.querySelector('#max_mobs_total').value") != '777' and time.monotonic() < deadline:
                    time.sleep(0.1)
                assert browser.evaluate("document.querySelector('#max_mobs_total').value") == '777'
                assert browser.evaluate("document.querySelector('.event-editor[data-prefix=share] .event-count').value") == '6'
                assert browser.evaluate("document.querySelector('.event-editor[data-prefix=like] .event-count').value") == '200'
                browser.evaluate("document.querySelector('#max_mobs_per_user').value = '23'")
                with config_file_lock(runtime_path):
                    changed = load_json(runtime_path, {})
                    changed.update(max_mobs_total=888, max_mobs_per_user=15)
                    save_json(runtime_path, changed)
                time.sleep(2)
                assert browser.evaluate("document.querySelector('#max_mobs_per_user').value") == '23'
                browser.evaluate("save(false)")
                persisted = load_json(runtime_path, {})
                assert persisted['max_mobs_total'] == 888
                assert persisted['max_mobs_per_user'] == 23
                # A server response that began before a completed save must not
                # overwrite the new value. Focused fields update after blur.
                assert browser.evaluate("""(async () => {
                    showTab('settings'); showSettingsTab('settingsMobs');
                    const originalApi = api;
                    const originalTimer = setTimeout;
                    const before = lastSavedPayload;
                    try {
                        setTimeout = () => 0;
                        api = async () => {
                            const base = JSON.parse(lastSavedPayload);
                            base.mod.max_mobs_total = 950;
                            document.querySelector('#max_mobs_total').value = 950;
                            lastSavedPayload = JSON.stringify(base);
                            return {bridge: {}, mod: {max_mobs_total: 1}};
                        };
                        await pollRuntimeSettings();
                        if (document.querySelector('#max_mobs_total').value !== '950') return false;
                        document.querySelector('#max_mobs_total').focus();
                        api = async () => ({bridge: {}, mod: {max_mobs_total: 960}});
                        await pollRuntimeSettings();
                        if (document.querySelector('#max_mobs_total').value !== '950') return false;
                        document.querySelector('#max_mobs_total').blur();
                        await pollRuntimeSettings();
                        return document.querySelector('#max_mobs_total').value === '960';
                    } finally {
                        api = originalApi; setTimeout = originalTimer;
                        lastSavedPayload = before;
                        document.querySelector('#max_mobs_total').value = JSON.parse(before).mod.max_mobs_total;
                    }
                })()""")
                assert not browser.errors, browser.errors
                browser.evaluate("showTab('voicevox')")
                media_state = browser.evaluate("""(async () => {
                    document.querySelector('#gift_phrase_custom').value = 'いつもありがとう！';
                    document.querySelector('#gift_phrase_mode').value = 'custom';
                    document.querySelector('#gift_gif_random').checked = false;
                    document.querySelector('#gift_gif_file').value = 'girl GIF.gif';
                    document.querySelector('#gift_gif_file').dispatchEvent(new Event('change', {bubbles:true}));
                    document.querySelector('#gift_overlay_x').value = 90;
                    document.querySelector('#gift_overlay_y').value = 80;
                    document.querySelector('#gift_overlay_width').value = 500;
                    renderGiftSettings(); await save(false);
                    return (await (await fetch('/api/state')).json()).bridge;
                })()""")
                assert media_state['gift_phrase_mode'] == 'custom'
                assert media_state['gift_phrase_custom'] == 'いつもありがとう！'
                assert media_state['gift_gif_file'] == 'girl GIF.gif'
                assert not media_state['gift_gif_random']
                assert media_state['gift_overlay_width'] == 500
                assert browser.evaluate("getComputedStyle(document.querySelector('#giftPositionSample')).backgroundColor") == 'rgba(0, 0, 0, 0)'
                browser.evaluate("document.querySelector('#randomThanksBtn').click()")
                assert browser.evaluate("document.querySelector('#gift_phrase_mode').value") == 'random'
                browser.evaluate("save(false)")
                for width, height, name in ((1440, 1100, 'desktop'), (390, 844, 'mobile')):
                    browser.command('Emulation.setDeviceMetricsOverride', width=width, height=height, deviceScaleFactor=1, mobile=width < 600)
                    browser.evaluate("document.querySelector('#giftPositionPreview').scrollIntoView({behavior:'instant'}); renderGiftSettings()")
                    time.sleep(0.3)
                    assert browser.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    bounds = browser.evaluate("""(() => {
                        const r = document.querySelector('#giftPositionSample').getBoundingClientRect();
                        const p = document.querySelector('#giftPositionPreview').getBoundingClientRect();
                        return {x:r.x+r.width/2, y:r.y+r.height/2, px:p.x+p.width/2, py:p.y+p.height/2};
                    })()""")
                    browser.command('Input.dispatchMouseEvent', type='mousePressed', x=bounds['x'], y=bounds['y'], button='left', clickCount=1)
                    browser.command('Input.dispatchMouseEvent', type='mouseMoved', x=bounds['px'], y=bounds['py'], button='left', buttons=1)
                    browser.command('Input.dispatchMouseEvent', type='mouseReleased', x=bounds['px'], y=bounds['py'], button='left', clickCount=1)
                    assert 35 <= float(browser.evaluate("document.querySelector('#gift_overlay_x').value")) <= 65
                    browser.evaluate('save(false)')
                    shot = browser.command('Page.captureScreenshot', format='png')
                    (screenshots / f'gift-hud-settings-{name}.png').write_bytes(base64.b64decode(shot['data']))
                assert not browser.errors, browser.errors
                print("BROWSER_SETTINGS_OK desktop/mobile, autosave/reload/errors, all test buttons, zero JS exceptions")
                browser.command("Browser.close")
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)
            server.shutdown()
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
