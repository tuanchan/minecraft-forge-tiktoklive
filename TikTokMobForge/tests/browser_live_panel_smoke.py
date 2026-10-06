"""Panel source in a separate browser profile follows GUI edits without storage sharing."""
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
from unittest.mock import patch
import urllib.request
from websockets.sync.client import connect
from browser_settings_smoke import Browser
from test_settings import isolated_settings, web
import live_panel

def wait_for(check, label):
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        if check(): return
        time.sleep(.15)
    raise AssertionError(label)

def start_chrome(folder):
    process=subprocess.Popen([r'C:\Program Files\Google\Chrome\Application\chrome.exe','--headless=new','--disable-gpu',
        '--no-first-run','--remote-debugging-port=0','--user-data-dir='+str(folder),'about:blank'],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    wait_for(lambda:(folder/'DevToolsActivePort').exists(),'Chrome startup')
    port=int((folder/'DevToolsActivePort').read_text().splitlines()[0])
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/json') as response:
        target=next(item for item in json.load(response) if item['type']=='page')
    return process,connect(target['webSocketDebuggerUrl'])

def main():
    with isolated_settings(), tempfile.TemporaryDirectory(prefix='panel-link-') as directory, \
            web.ThreadingHTTPServer(('127.0.0.1',0),web.Handler) as server:
        root=Path(directory)
        with patch.object(live_panel,'PATH',root/'panel.json'):
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            processes=[];sockets=[]
            try:
                for name in ['editor','studio']:
                    process,socket=start_chrome(root/name);processes.append(process);sockets.append(socket)
                editor,studio=[Browser(socket) for socket in sockets]
                origin=f'http://127.0.0.1:{server.server_port}'
                for browser in [editor,studio]:
                    browser.command('Runtime.enable');browser.command('Page.enable')
                    browser.command('Emulation.setDeviceMetricsOverride',width=1920,height=1080,deviceScaleFactor=1,mobile=False)
                editor.command('Page.navigate',url=origin+'/?view=live')
                wait_for(lambda:editor.evaluate("document.querySelector('#eventCards .event-card') !== null"),'Editor loaded')
                editor.evaluate("Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>window.copiedLink=text},configurable:true}); document.querySelector('#copyPanelLinkBtn').click()")
                wait_for(lambda:editor.evaluate('window.copiedLink')==origin+'/live-panel.html','Copy link button')
                studio.command('Page.navigate',url=origin+'/live-panel.html')
                wait_for(lambda:studio.evaluate("document.querySelectorAll('#panel .event-card').length") == 5,'Separate-profile initial snapshot')
                assert studio.evaluate("document.querySelectorAll('button,input,select').length") == 0
                assert studio.evaluate("localStorage.length") == 0
                editor.evaluate("mappings=[{gift_name:'Realtime Test',action:'mob',target:'minecraft:creeper',amount:7,panel_note:'LIVE changes now'}]; renderLivePanel();")
                wait_for(lambda:studio.evaluate("document.querySelector('.gift-amount')?.textContent")=='7x','Realtime amount update')
                wait_for(lambda:studio.evaluate("document.querySelector('.gift-panel-note')?.textContent")=='LIVE changes now','Realtime note update')
                editor.evaluate("document.querySelector('#panelSettingsBtn').click(); const input=document.querySelector('[data-size=mob]');input.value='96';input.dispatchEvent(new Event('input',{bubbles:true}));")
                wait_for(lambda:studio.evaluate("getComputedStyle(document.querySelector('#panel')).getPropertyValue('--panel-mob').trim()")=='96px','Appearance sync across profiles')
                saved=live_panel.snapshot()
                assert set(saved)=={'html','appearance','revision','width'}
                assert 'api_key' not in json.dumps(saved)
                studio.command('Page.reload')
                wait_for(lambda:studio.evaluate("document.querySelector('.gift-amount')?.textContent")=='7x','Reload persistence')
                shot=studio.command('Page.captureScreenshot',format='png')
                out=Path(__file__).resolve().parents[2]/'temp'/'live-panel-source.png'
                out.write_bytes(base64.b64decode(shot['data']))
                assert not editor.errors and not studio.errors,(editor.errors,studio.errors)
                print('LIVE_PANEL_LINK_OK: copy, separate browser profiles, realtime content/style, reload, no controls')
            finally:
                for socket in sockets:socket.close()
                for process in processes:process.terminate();process.wait(timeout=10)
                server.shutdown();thread.join(timeout=5)
if __name__=='__main__':main()
