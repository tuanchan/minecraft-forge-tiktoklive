from pathlib import Path
p=Path('TikTokMobForge/web/index.html');s=p.read_text(encoding='utf-8').replace('Mỗi tương tác sẽ tạo mob trong Minecraft!','Mỗi tương tác có thể tạo mob hoặc trao quà trong Minecraft!').replace('Số mob','Số phần thưởng').replace('tạo mob','trao phần thưởng').replace('được tạo mob','được trao phần thưởng').replace('app.js?v=20260927-tnt-damage','app.js?v=20260927-interaction-rewards');p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/tests/check_interaction_ui.py');s=p.read_text(encoding='utf-8');needle='        page.locator("#comment_cooldown_seconds").fill("12")';s=s.replace(needle,'''        for prefix in ("view", "follow", "comment", "share", "like"):
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
'''+needle);p.write_text(s,encoding='utf-8')
