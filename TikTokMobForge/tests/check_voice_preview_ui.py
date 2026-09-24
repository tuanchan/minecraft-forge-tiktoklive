"""Headless UI checks, intercepted saves and catalog; no real key or synthesis."""
import sys
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'build/browser-tools'), str(ROOT / 'web')]
from playwright.sync_api import sync_playwright
import main as web

web.load_api_key = lambda: ''
web.minecraft_viewport = lambda: {'width': 1920, 'height': 1009, 'detected': True}
server = ThreadingHTTPServer(('127.0.0.1', 0), web.Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
artifacts = ROOT / 'tests/artifacts'
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1080})
        errors, saves = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        def route_api(route):
            if route.request.url.endswith('/api/elevenlabs'):
                route.fulfill(json={'voices': [{'voice_id': 'voice-anna', 'name': 'Anna'},
                    {'voice_id': 'voice-brian', 'name': 'Brian'}], 'models': [],
                    'warnings': ['Danh sách giọng công khai; tài khoản thiếu voices_read.']})
            elif route.request.method == 'POST':
                if route.request.url.endswith('/api/save'):
                    saves.append(route.request.post_data_json)
                route.fulfill(json={'ok': True})
            else:
                route.continue_()
        page.route('**/api/**', route_api)
        page.goto(f'http://127.0.0.1:{server.server_port}/?view=settings')
        page.wait_for_selector('#loading', state='detached')
        page.wait_for_function("document.querySelector('#voiceCatalogStatus').textContent.includes('2 giọng')")
        page.locator('[data-settings-tab="settingsPosition"]').click()
        preview = page.locator('#notificationPreview')
        preview.scroll_into_view_if_needed()
        box = preview.bounding_box()
        assert abs(box['width'] / box['height'] - 1920 / 1009) < .01
        assert box['height'] > 500
        assert page.locator('#previewSizeLabel').inner_text().startswith('Theo cửa sổ Minecraft: 1920 × 1009')
        page.locator('#positionPreviewKind').select_option('comment')
        for axis in ('x', 'y'):
            page.locator(f'[data-position-kind="comment"] [data-axis="{axis}"]').fill('100')
        preview.scroll_into_view_if_needed()
        page.wait_for_timeout(100)
        bounds = preview.bounding_box()
        text = page.locator('#notificationPreviewText').bounding_box()
        assert abs(text['x'] + text['width'] - bounds['x'] - bounds['width']) < 2
        assert abs(text['y'] + text['height'] - bounds['y'] - bounds['height']) < 2
        page.mouse.move(text['x'] + text['width'] / 2, text['y'] + text['height'] / 2)
        page.mouse.down()
        page.mouse.move(bounds['x'] + bounds['width'] / 2, bounds['y'] + bounds['height'] / 2, steps=8)
        page.mouse.up()
        y = float(page.locator('[data-position-kind="comment"] [data-axis="y"]').input_value())
        assert 30 < y < 70, y
        preview.screenshot(path=str(artifacts / 'minecraft-preview-desktop.png'))
        page.locator('[data-settings-tab="settingsVoice"]').click()
        page.locator('#voice_search').fill('Brian')
        assert page.locator('#voice_choice option').count() == 2
        assert page.locator('#voice_choice').input_value() == ''
        page.locator('#voice_choice').select_option('voice-brian')
        page.locator('#tts_model_choice').select_option('eleven_v3')
        assert page.locator('#tts_voice_name').input_value() == 'Brian'
        assert page.locator('#tts_voice_id').input_value() == 'voice-brian'
        assert page.locator('#tts_model_id').input_value() == 'eleven_v3'
        page.wait_for_timeout(1300)
        assert saves[-1]['bridge']['tts_voice_id'] == 'voice-brian'
        assert saves[-1]['bridge']['tts_model_id'] == 'eleven_v3'
        page.locator('#voice_search').fill('')
        page.locator('#settingsVoice').screenshot(path=str(artifacts / 'voice-dropdowns-desktop.png'))
        page.locator('#tts_model_id').fill('custom-model')
        assert page.locator('#tts_model_choice').input_value() == 'custom-model'
        page.locator('[data-settings-tab="settingsPosition"]').click()
        page.locator('#refreshPreviewSize').click()
        assert '1920 × 1009' in page.locator('#previewSizeLabel').inner_text()
        page.set_viewport_size({'width': 390, 'height': 844})
        preview.scroll_into_view_if_needed()
        box = preview.bounding_box()
        assert abs(box['width'] / box['height'] - 1920 / 1009) < .02
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        preview.screenshot(path=str(artifacts / 'minecraft-preview-mobile.png'))
        page.locator('[data-settings-tab="settingsVoice"]').click()
        page.locator('#settingsVoice').screenshot(path=str(artifacts / 'voice-dropdowns-mobile.png'))
        assert not errors, errors
        browser.close()
        print('VOICE_PREVIEW_UI_OK: game aspect ratio, boundaries, desktop/mobile, search, dropdowns, model/voice IDs, autosave, manual model')
finally:
    server.shutdown()
    server.server_close()
