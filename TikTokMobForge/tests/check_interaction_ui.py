"""Browser smoke: headless Edge, local server, intercepted writes (no config changes)."""
import json
import sys
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "build/browser-tools"), str(ROOT / "web")]
from playwright.sync_api import sync_playwright
import main as web

web.load_api_key = lambda: ""


class Handler(web.Handler):
    def log_message(self, *args): pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
artifacts = ROOT / "tests/artifacts"
artifacts.mkdir(exist_ok=True)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1080})
        errors = []
        saves = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def intercept(route):
            if route.request.method == "POST":
                if route.request.url.endswith("/api/save"):
                    saves.append(route.request.post_data_json)
                route.fulfill(json={"ok": True, "voices": [], "models": []})
            elif route.request.url.endswith("/api/runtime-settings") and saves:
                route.fulfill(json={"bridge": {key: saves[-1]["bridge"][key] for key in web.EVENT_KEYS}, "mod": {key: saves[-1]["mod"][key] for key in web.MOD_KEYS}})
            else:
                route.continue_()

        page.route("**/api/**", intercept)
        page.goto(f"http://127.0.0.1:{server.server_port}/?view=events")
        page.wait_for_selector("#loading", state="detached")
        page.wait_for_function("document.querySelectorAll('.event-editor').length === 5")
        for event, fields in {"comment": ["comment_limit", "comment_cooldown_seconds"],
                              "share": ["share_limit", "share_cooldown_seconds"],
                              "like": ["like_spawn_count"], "view": ["view_enabled", "view_interval_seconds", "view_max_mobs_per_round"]}.items():
            for field in fields:
                assert page.locator(f'.event-editor[data-prefix="{event}"] #{field}').count() == 1
        for prefix in ("view", "follow", "comment", "share", "like"):
            card = page.locator(f'.event-editor[data-prefix="{prefix}"]')
            card.locator('.dropdown-toggle').click()
            card.locator('.dropdown-search').fill('totem')
            card.locator('[data-option-value="item:minecraft:totem_of_undying"]').click()
            assert 'totem_of_undying' in card.locator('.event-preview').get_attribute('src')
        page.wait_for_timeout(1400)
        for prefix in ("view", "follow", "comment", "share", "like"):
            assert saves[-1]["bridge"][f"{prefix}_mob_type"] == "item:minecraft:totem_of_undying"
        page.evaluate("state.bridge = {...state.bridge, ...collectPayload().bridge}; renderEvents(); renderLivePanel(false)")
        assert page.locator('.event-editor[data-prefix="like"] .event-mob-dropdown').get_attribute('data-value') == 'item:minecraft:totem_of_undying'
        page.locator("#comment_cooldown_seconds").fill("12")
        page.wait_for_function("document.querySelector('.event-editor[data-prefix=comment] .event-rule').textContent.includes('12 giây')")
        page.wait_for_timeout(1400)
        assert saves and saves[-1]["bridge"]["comment_cooldown_seconds"] == 12, ([s["bridge"]["comment_cooldown_seconds"] for s in saves], page.locator("#comment_cooldown_seconds").input_value())
        page.locator('[data-tab="settings"]').click()
        page.locator('[data-tab="events"]').click()
        assert page.locator("#comment_cooldown_seconds").input_value() == "12"
        page.locator("#comment_cooldown_seconds").fill("10")
        page.wait_for_timeout(100)
        assert page.locator('.event-editor[data-prefix="like"] .event-mob-dropdown').get_attribute('data-value') == 'item:minecraft:totem_of_undying'
        page.screenshot(path=str(artifacts / "interactions-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(artifacts / "interactions-mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.locator('.event-editor[data-prefix="comment"] .dropdown-toggle').click()
        assert page.locator('.event-editor[data-prefix="comment"] .dropdown-popover').is_visible()
        assert not errors, errors
        print("INTERACTION_UI_OK: desktop, mobile, grouped controls, dropdown, live summary, autosave payload, tab persistence")
        browser.close()
finally:
    server.shutdown()
    server.server_close()
