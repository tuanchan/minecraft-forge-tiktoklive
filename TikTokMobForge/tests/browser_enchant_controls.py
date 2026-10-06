"""Actual dropdown clicks, numeric edits, autosave and reload in Chrome."""
import base64
import time
from test_settings import ROOT


def check_enchant_controls(browser):
    browser.evaluate("""showTab('gifts'); mappings=[{gift_name:'Enchant test',gift_id:'90001',action:'special',target:'absorption',amount:1}]; renderMappings();
        document.querySelector('.reward-select .dropdown-toggle').click();
        var search=document.querySelector('.reward-select .dropdown-search');
        search.value='sharpness'; search.dispatchEvent(new Event('input',{bubbles:true}));""")
    assert browser.evaluate("document.querySelectorAll('.reward-select .dropdown-option').length") == 1
    browser.evaluate("document.querySelector('.reward-select .dropdown-option').click()")
    assert browser.evaluate("mappings[0].enchantments") == [{'id': 'minecraft:sharpness', 'level': 1}]
    assert browser.evaluate("document.querySelectorAll('.reward-level').length") == 0
    browser.evaluate("""var count=document.querySelector('.enchant-count');count.value='3';count.dispatchEvent(new Event('change',{bubbles:true}));
        document.querySelectorAll('.enchant-entry')[1].querySelector('.dropdown-toggle').click();
        var search=document.querySelectorAll('.enchant-entry')[1].querySelector('.dropdown-search');search.value='binding_curse';search.dispatchEvent(new Event('input',{bubbles:true}));""")
    assert browser.evaluate("document.querySelectorAll('.enchant-entry')[1].querySelectorAll('.dropdown-option').length") == 1
    browser.evaluate("document.querySelectorAll('.enchant-entry')[1].querySelector('.dropdown-option').click()")
    browser.evaluate("""document.querySelectorAll('.enchant-level').forEach((input,i)=>{input.value=[7,255,12][i];input.dispatchEvent(new Event('input',{bubbles:true}));});""")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        saved = browser.evaluate("(async () => (await (await fetch('/api/state')).json()).bridge.gift_actions[0])()")
        if saved.get('enchantments', [{}])[0].get('level') == 7:
            break
        time.sleep(.1)
    assert len(saved['enchantments']) == 3, saved
    assert [entry['level'] for entry in saved['enchantments']] == [7, 255, 12], saved
    assert saved['enchantments'][1]['id'] == 'minecraft:binding_curse'
    # Draft numbers must not become zero or an invalid saved level.
    browser.evaluate("""var input=document.querySelector('.enchant-level');input.value='';input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('blur'));""")
    assert browser.evaluate("document.querySelector('.enchant-level').value") == '7'
    browser.evaluate("""var input=document.querySelector('.enchant-level');input.value='256';input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('blur'));""")
    assert browser.evaluate("mappings[0].enchantments[0].level") == 7
    browser.command('Page.reload')
    deadline = time.monotonic() + 20
    time.sleep(.5)
    while time.monotonic() < deadline:
        if browser.evaluate("typeof state !== 'undefined' && !!state && !document.querySelector('#loading')"):
            break
        time.sleep(.1)
    browser.evaluate("showTab('gifts')")
    assert browser.evaluate("mappings[0].enchantments") == saved['enchantments']
    assert browser.evaluate("document.querySelector('.enchant-count').value") == '3'
    browser.evaluate("document.querySelector('.enchant-add').click()")
    assert browser.evaluate("mappings[0].enchantments.length") == 4
    browser.evaluate("document.querySelectorAll('.enchant-remove')[3].click()")
    assert browser.evaluate("mappings[0].enchantments.length") == 3
    # Every native enchant can be selected once; duplicate choices are excluded.
    browser.evaluate("""var input=document.querySelector('.enchant-count');input.value='43';input.dispatchEvent(new Event('change',{bubbles:true}));""")
    assert browser.evaluate("new Set(mappings[0].enchantments.map(e=>e.id)).size") == 43
    browser.evaluate("""var input=document.querySelector('.enchant-count');input.value='3';input.dispatchEvent(new Event('change',{bubbles:true}));""")
    browser.evaluate("document.querySelector('.mapping-row').scrollIntoView({block:'center'})")
    shot = browser.command('Page.captureScreenshot', format='png', captureBeyondViewport=True)
    (ROOT / 'tests/artifacts/enchant-options.png').write_bytes(base64.b64decode(shot['data']))
    browser.evaluate("""var mode=document.querySelector('.enchant-mode');mode.value='full';mode.dispatchEvent(new Event('change',{bubbles:true}));""")
    assert browser.evaluate("document.querySelectorAll('.reward-level').length") == 1
    assert browser.evaluate("document.querySelectorAll('.enchant-entry').length") == 0
    browser.evaluate('save(false)')
    print('ENCHANT_BROWSER_OK: reward search, type search, count, per-type levels, curses, autosave, reload, 43 unique types, FULL mode')
