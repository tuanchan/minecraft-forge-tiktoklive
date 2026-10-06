"""New gift choices and per-gift lightning controls against the real isolated API."""
import base64
from pathlib import Path
import tempfile
import threading
from browser_live_panel_smoke import start_chrome, wait_for
from browser_settings_smoke import Browser
from test_settings import isolated_settings, web


def main():
    with isolated_settings() as gui, tempfile.TemporaryDirectory(prefix='lightning-browser-') as directory, \
         web.ThreadingHTTPServer(('127.0.0.1', 0), web.Handler) as server:
        web.CONTROLLER.save({'gui': gui, 'bridge': {'gift_actions': [
            {'gift_name': 'Rose', 'action': 'special', 'target': 'lightning_player', 'amount': 1},
            {'gift_name': 'TikTok', 'action': 'special', 'target': 'clear_tool_mobs', 'amount': 1}]}})
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        process,socket=start_chrome(Path(directory)/'chrome')
        try:
            browser=Browser(socket)
            browser.command('Runtime.enable');browser.command('Page.enable')
            browser.command('Emulation.setDeviceMetricsOverride',width=1600,height=1100,deviceScaleFactor=1,mobile=False)
            browser.command('Page.navigate',url=f'http://127.0.0.1:{server.server_port}/?view=gifts')
            wait_for(lambda:browser.evaluate("document.querySelector('[data-option=strike_count]') !== null"),'Lightning editor loaded')
            assert browser.evaluate("document.querySelector('[data-option=strike_count]').step")=='1'
            assert browser.evaluate("document.querySelector('[data-option=strike_count]').closest('label').textContent").strip()=='Số tia sét mỗi đợt'
            assert browser.evaluate("allRewards().some(r=>r.target==='clear_tool_mobs')")
            for key,value in [('strike_count',7),('interval_seconds',0.25)]:
                browser.evaluate(f"{{const input=document.querySelector('[data-option={key}]');input.value={value};input.dispatchEvent(new Event('input',{{bubbles:true}}));input.blur();}}")
            wait_for(lambda:web.CONTROLLER.state()['bridge']['gift_actions'][0].get('interval_seconds')==0.25,'Saved interval')
            assert web.CONTROLLER.state()['bridge']['gift_actions'][0]['strike_count']==7
            browser.evaluate('window.beforeGiftReload=true')
            browser.command('Page.reload')
            wait_for(lambda:browser.evaluate("!window.beforeGiftReload && !document.querySelector('#loading') && document.querySelector('[data-option=strike_count]')?.value === '7' && document.querySelector('[data-option=interval_seconds]')?.value === '0.25'"),'Reloaded strike settings')
            assert browser.evaluate("document.querySelector('[data-option=interval_seconds]').value")=='0.25'
            assert 'người tặng' in browser.evaluate("document.querySelectorAll('.mapping-row')[1].textContent")
            browser.evaluate("document.querySelector('#mappingList').scrollIntoView({block:'center'})")
            out=Path(__file__).resolve().parents[2]/'temp'/'lightning-gift-options.png'
            out.write_bytes(base64.b64decode(browser.command('Page.captureScreenshot',format='png')['data']))
            assert not browser.errors,browser.errors
            print('LIGHTNING_GIFT_BROWSER_OK: catalog, Vietnamese labels, count, interval, autosave, reload, cleanup gift')
        finally:
            socket.close();process.terminate();process.wait(timeout=10)
            server.shutdown();thread.join(timeout=5)


if __name__=='__main__': main()
