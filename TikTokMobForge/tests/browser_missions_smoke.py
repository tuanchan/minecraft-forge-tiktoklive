import base64
from pathlib import Path
import tempfile
import threading
import subprocess
from browser_live_panel_smoke import start_chrome, wait_for
from browser_settings_smoke import Browser
from test_settings import isolated_settings, web, ROOT


def main():
    with isolated_settings() as gui, tempfile.TemporaryDirectory(prefix='mission-browser-', ignore_cleanup_errors=True) as directory, \
         web.ThreadingHTTPServer(('127.0.0.1',0),web.Handler) as server:
        web.CONTROLLER.save({'gui':gui,'bridge':{'gift_actions':[dict(gift_name='Rose',action='special',target='mission_penalty',amount=1)]}})
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        process,socket=start_chrome(Path(directory)/'chrome')
        try:
            browser=Browser(socket);browser.command('Runtime.enable');browser.command('Page.enable')
            browser.command('Emulation.setDeviceMetricsOverride',width=1500,height=1100,deviceScaleFactor=1,mobile=False)
            browser.command('Page.navigate',url=f'http://127.0.0.1:{server.server_port}/?view=missions')
            wait_for(lambda:browser.evaluate("document.querySelector('#missionSaveStatus')?.textContent==='Đã tải'"),'Mission API loaded')
            assert browser.evaluate("document.querySelector('[data-view=missions]').classList.contains('active')")
            browser.evaluate("document.querySelector('#missionDiamond').click();document.querySelector('#missionKill').click()")
            wait_for(lambda:browser.evaluate("document.querySelector('#missionSaveStatus').textContent==='Đã lưu'"),'Missions autosaved')
            assert browser.evaluate("document.querySelectorAll('.mission-editor').length")==2
            assert browser.evaluate("document.querySelectorAll('[data-field=milestones]').length")==2
            browser.evaluate("""var steps=document.querySelector('[data-field=milestones]');steps.value='10';steps.dispatchEvent(new Event('change',{bubbles:true}));""")
            assert browser.evaluate("document.querySelector('.mission-card').style.getPropertyValue('--mission-steps')")=='10'
            assert browser.evaluate("document.querySelector('.mission-diamond .mission-icon-left').src.endsWith('Cu%E1%BB%91c%20chim%20kim%20c%C6%B0%C6%A1ng%20ph%C3%A1t%20s%C3%A1ng%20pixel%20art.png')")
            assert browser.evaluate("document.querySelector('.mission-diamond .mission-icon-right').src.endsWith('quangkc.png')")
            browser.evaluate("""var row=document.querySelectorAll('.mission-editor')[1];
              for(const [key,value] of [['mob','minecraft:zombie'],['mode','3d'],['death_penalty','8']]){
                const input=row.querySelector('[data-field='+key+']');input.value=value;input.dispatchEvent(new Event('change',{bubbles:true}));
              }""")
            wait_for(lambda:browser.evaluate("document.querySelector('#missionSaveStatus').textContent==='Đã lưu'"),'3D and mob choice saved')
            assert browser.evaluate("document.querySelectorAll('.mission-stage')[1].hidden")
            before=browser.evaluate("document.querySelector('[data-field=x]').value")
            box=browser.evaluate("(()=>{let r=document.querySelector('.mission-preview').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()")
            browser.command('Input.dispatchMouseEvent',type='mousePressed',x=box['x'],y=box['y'],button='left',clickCount=1)
            browser.command('Input.dispatchMouseEvent',type='mouseMoved',x=box['x']+70,y=box['y']+30,button='left',buttons=1)
            browser.command('Input.dispatchMouseEvent',type='mouseReleased',x=box['x']+70,y=box['y']+30,button='left',clickCount=1)
            assert browser.evaluate("document.querySelector('[data-field=x]').value")!=before
            wait_for(lambda:browser.evaluate("document.querySelector('#missionSaveStatus').textContent==='Đã lưu'"),'Dragged position saved')
            browser.evaluate('window.missionBeforeReload=true')
            browser.command('Page.reload')
            wait_for(lambda:browser.evaluate("!window.missionBeforeReload && document.querySelectorAll('.mission-editor').length===2"),'Missions survive reload')
            assert browser.evaluate("document.querySelectorAll('[data-field=mob]')[0].value")=='minecraft:zombie'
            assert browser.evaluate("document.querySelector('.mission-kill') !== null")
            assert browser.evaluate("document.querySelector('.mission-kill .mission-icon-left').src.endsWith('iconkiemkc.png')")
            browser.evaluate("showTab('gifts');")
            assert browser.evaluate("document.querySelector('.reward-mission').options.length")==3
            browser.evaluate("""var s=document.querySelector('.reward-mission');s.selectedIndex=1;s.dispatchEvent(new Event('change',{bubbles:true}));
                var p=document.querySelector('[data-option=penalty]');p.value='9';p.dispatchEvent(new Event('input',{bubbles:true}));""")
            wait_for(lambda:browser.evaluate("(async()=>{let data=await(await fetch('/api/state')).json();return data.bridge.gift_actions[0].penalty===9;})()"),'Gift penalty saved')
            browser.evaluate("showTab('missions')")
            shot=browser.command('Page.captureScreenshot',format='png',captureBeyondViewport=True)
            output=ROOT/'tests/artifacts/missions.png';output.parent.mkdir(exist_ok=True);output.write_bytes(base64.b64decode(shot['data']))
            assert not browser.errors,browser.errors
            print('MISSIONS_BROWSER_OK: tab, create, autosave, mob filter, 3D, drag 2D, reload, gift target and points')
        finally:
            server.shutdown();thread.join(timeout=5)
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
            socket.close();process.wait(timeout=15)


if __name__=='__main__':main()
