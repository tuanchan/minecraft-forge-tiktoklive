from pathlib import Path
p=Path('TikTokMobForge/web/app.js');s=p.read_text(encoding='utf-8').replace('  if (id === "settingsPosition") requestAnimationFrame(renderSettingsPreview);','  if (id === "settingsPosition") requestAnimationFrame(renderSettingsPreview);\n  if (id === "settingsPinnedBoard") requestAnimationFrame(renderPinnedBoardPreview);').replace('  if (name === "tests" && state) renderTests();','  if (name === "tests" && state) renderTests();\n  if (name === "settings") requestAnimationFrame(renderPinnedBoardPreview);');p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/web/pin-layout.js');s=p.read_text(encoding='utf-8').replace("  let nameSize = 15 * scale * textScale;", "  author.style.lineHeight = '1.2';\n  let nameSize = Math.min(15 * scale * textScale, h * .1 / 1.2);");p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/tests/browser_reward_options_smoke.py');s=p.read_text(encoding='utf-8').replace("                assert not browser.errors, browser.errors",'''                browser.evaluate("""mappings = [{gift_name:'Creeper',action:'mob',target:'minecraft:creeper',amount:1},
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
                time.sleep(2)
                assert browser.evaluate("[...document.querySelectorAll('.reward-blocks')].map(i=>i.value)") == ['true','false','true']
                assert browser.evaluate("document.querySelector('#creeper_break_blocks').checked") is True
                assert browser.evaluate("document.querySelector('#tnt_break_blocks').checked") is False
                assert not browser.errors, browser.errors''');p.write_text(s,encoding='utf-8')
