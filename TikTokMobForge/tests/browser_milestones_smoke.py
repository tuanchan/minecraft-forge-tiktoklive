"""Real browser/API editor persistence and separate LIVE Studio progress."""
import base64
import json
from pathlib import Path
import tempfile
import threading
from unittest.mock import patch
from browser_live_panel_smoke import start_chrome, wait_for
from browser_settings_smoke import Browser
from test_settings import isolated_settings, web
import milestones


def main():
    with isolated_settings() as gui, tempfile.TemporaryDirectory(prefix='milestone-browser-') as directory, \
         web.ThreadingHTTPServer(('127.0.0.1', 0), web.Handler) as server:
        folder=Path(directory)
        web.CONTROLLER.save({'gui': gui, 'bridge': {'milestones': milestones.settings({})}})
        with patch.object(milestones, 'PATH', folder/'progress.json'), \
             patch.object(web.CONTROLLER, 'is_live_running', return_value=False) as running:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            process,socket=start_chrome(folder/'chrome')
            try:
                browser=Browser(socket)
                browser.command('Runtime.enable');browser.command('Page.enable')
                browser.command('Emulation.setDeviceMetricsOverride',width=1440,height=1080,deviceScaleFactor=1,mobile=False)
                origin=f'http://127.0.0.1:{server.server_port}'
                browser.command('Page.navigate',url=origin+'/?view=events')
                wait_for(lambda:browser.evaluate("!document.querySelector('#loading')"),'Editor loaded')
                assert browser.evaluate("document.querySelectorAll('#eventEditors .event-editor').length")==5
                assert browser.evaluate("[...document.querySelectorAll('#eventEditors .event-editor')].every(node=>node.offsetHeight>0)")
                assert browser.evaluate("document.querySelector('#comment_limit').offsetHeight > 0 && document.querySelector('#share_limit').offsetHeight > 0")
                for kind, tab, query, reward in [('like','events','totem','item:minecraft:totem_of_undying'),('coins','gifts','iron_golem','minecraft:iron_golem')]:
                    browser.evaluate(f"document.querySelector('[data-tab={tab}]').click();document.querySelector('[data-kind={kind}] .dropdown-toggle').click()")
                    assert browser.evaluate(f"document.querySelector('[data-kind={kind}] .goal-reward').classList.contains('open')")
                    browser.evaluate(f"{{const input=document.querySelector('[data-kind={kind}] .dropdown-search');input.value='{query}';input.dispatchEvent(new Event('input',{{bubbles:true}}));}}")
                    wait_for(lambda:browser.evaluate(f"[...document.querySelectorAll('[data-kind={kind}] .dropdown-option img')].some(img=>img.complete && img.naturalWidth>0)"),'Dropdown option image loaded')
                    browser.evaluate(f"document.querySelector('[data-kind={kind}] [data-option-value=\"{reward}\"]').click()")
                    assert browser.evaluate(f"document.querySelector('[data-kind={kind}] .goal-reward').dataset.value")==reward
                    assert browser.evaluate(f"!document.querySelector('[data-kind={kind}] .goal-reward').classList.contains('open')")
                    wait_for(lambda:web.CONTROLLER.state()['bridge'].get('milestones',{}).get(kind,{}).get('rules',[{}])[0].get('reward')==reward,'Reward selection saved')
                browser.evaluate("document.querySelector('[data-tab=events]').click()")
                browser.evaluate("const input=document.querySelector('[data-kind=like] .goal-threshold');input.value=100;input.dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('[data-kind=coins] input[type=checkbox]').click();")
                wait_for(lambda:web.CONTROLLER.state()['bridge'].get('milestones',{}).get('coins',{}).get('enabled'),'Saved coins toggle')
                assert web.CONTROLLER.state()['bridge']['milestones']['like']['rules'][0]['threshold']==100
                browser.evaluate("document.querySelector('[data-kind=like] .add-goal').click()")
                wait_for(lambda:len(web.CONTROLLER.state()['bridge']['milestones']['like']['rules'])==2,'Saved multiple rules')
                browser.evaluate("document.querySelector('[data-kind=like] .goal-remember').click()")
                wait_for(lambda:web.CONTROLLER.state()['bridge']['milestones']['like'].get('remember') is True,'Remember saved')
                browser.evaluate('window.beforeMilestoneReload=true')
                browser.command('Page.reload')
                wait_for(lambda:browser.evaluate("!window.beforeMilestoneReload && !document.querySelector('#loading') && document.querySelectorAll('[data-kind=like] .goal-threshold').length === 2"),'Reloaded rules')
                assert browser.evaluate("document.querySelector('[data-kind=like] .goal-remember').checked") is True
                assert browser.evaluate("document.querySelector('[data-kind=like] .goal-reward').dataset.value")=='item:minecraft:totem_of_undying'
                assert browser.evaluate("document.querySelectorAll('.goal-search,select.goal-reward').length")==0
                browser.evaluate("document.querySelector('[data-tab=live]').click()")
                assert browser.evaluate("document.querySelectorAll('#eventCards .event-card').length")==5
                assert browser.evaluate("document.querySelectorAll('#interactionGoals .milestone-group').length")==4
                config=web.CONTROLLER.state()['bridge']
                engine=milestones.Milestones(config,lambda *a,**k:None)
                running.return_value=True
                engine.add('like',70,'Test','test');engine.add('coins',70,'Test','test')
                wait_for(lambda:browser.evaluate("document.querySelector('[data-goal-kind=like] progress')?.value")==70,'Animated admin progress')
                stale=milestones.snapshot()
                stale['groups']['coins']['enabled']=False
                milestones.PATH.write_text(json.dumps(stale),encoding='utf-8')
                wait_for(lambda:browser.evaluate("document.querySelector('[data-goal-kind=coins] .goal-rounds')?.textContent")=='Đã bật · chờ bridge cập nhật','Old disabled snapshot cannot override enabled editor')
                engine.publish()
                wait_for(lambda:browser.evaluate("document.querySelector('[data-goal-kind=coins] progress')?.value")==70,'Current snapshot restores real progress')
                wait_for(lambda:bool(__import__('live_panel').snapshot()['html']),'Published panel')
                browser.command('Page.navigate',url=origin+'/live-panel.html')
                wait_for(lambda:browser.evaluate("document.querySelector('[data-goal-kind=coins] progress')?.value")==70,'Standalone progress')
                stale=milestones.snapshot()
                stale['groups']['coins']['rules'][0]['amount']+=1
                milestones.PATH.write_text(json.dumps(stale),encoding='utf-8')
                wait_for(lambda:browser.evaluate("document.querySelector('[data-goal-kind=coins] .goal-rounds')?.textContent")=='Đã bật · chờ bridge cập nhật','Standalone rejects old reward configuration')
                engine.publish()
                wait_for(lambda:browser.evaluate("document.querySelector('[data-goal-kind=coins] progress')?.value")==70,'Standalone resumes current progress')
                assert browser.evaluate("document.querySelectorAll('input,select,button').length")==0
                assert browser.evaluate("getComputedStyle(document.querySelector('progress'),'::-webkit-progress-value').backgroundImage.includes('gradient')")
                engine.add('like',65,'Other','other')
                wait_for(lambda:browser.evaluate("document.querySelector('[data-goal-kind=like] progress')?.value")==35,'Remainder after reward')
                wait_for(lambda:'1' in browser.evaluate("document.querySelector('[data-goal-kind=like] .goal-rounds').textContent"),'Completed round')
                running.return_value=False
                wait_for(lambda:browser.evaluate("document.querySelector('[data-goal-kind=coins] progress')?.value")==0,'Stopped session clears non-remembered progress')
                assert browser.evaluate("document.querySelector('[data-goal-kind=like] progress')?.value")==35
                browser.command('Page.navigate',url=origin+'/?view=live')
                wait_for(lambda:browser.evaluate("document.querySelector('[data-goal-kind=coins] progress')?.value")==0,'Stopped admin panel clears old coins')
                wait_for(lambda:browser.evaluate("document.querySelector('[data-goal-kind=like] progress')?.value")==35,'Stopped admin panel keeps remembered likes')
                out=Path(__file__).resolve().parents[2]/'temp'/'milestone-panel.png'
                out.write_bytes(base64.b64decode(browser.command('Page.captureScreenshot',format='png')['data']))
                assert not browser.errors,browser.errors
                print('MILESTONES_BROWSER_OK: controls, autosave, reload, animated progress, standalone link, multiple rules, remainder')
            finally:
                socket.close();process.terminate();process.wait(timeout=10)
                server.shutdown();thread.join(timeout=5)


if __name__=='__main__': main()
