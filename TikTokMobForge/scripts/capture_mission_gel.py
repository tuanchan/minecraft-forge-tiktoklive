"""Bake the existing Panel LIVE CSS into a 101-frame atlas for Minecraft 2D/3D."""
import base64
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from browser_live_panel_smoke import start_chrome
from browser_settings_smoke import Browser


def main():
    with tempfile.TemporaryDirectory(prefix='mission-gel-') as directory:
        process, socket = start_chrome(Path(directory) / 'chrome')
        try:
            browser = Browser(socket)
            browser.command('Page.enable')
            browser.command('Emulation.setDeviceMetricsOverride', width=3520, height=640, deviceScaleFactor=1, mobile=False)
            browser.command('Emulation.setDefaultBackgroundColorOverride', color={'r': 0, 'g': 0, 'b': 0, 'a': 0})
            css = (ROOT / 'web/milestones.css').read_text(encoding='utf-8')
            html = '<style>' + css + '</style><style>html,body{margin:0;background:transparent}body{display:grid;grid-template-columns:repeat(11,320px);grid-auto-rows:64px}.frame{width:320px;height:64px;display:flex;align-items:center;justify-content:center}.gel-progress{width:300px;height:45px;box-sizing:border-box}</style>'
            html += ''.join(f'<div class="frame"><progress class="gel-progress" value="{value}" max="100"></progress></div>' for value in range(101))
            frame = browser.command('Page.getFrameTree')['frameTree']['frame']['id']
            browser.command('Page.setDocumentContent', frameId=frame, html=html)
            browser.evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            shot = browser.command('Page.captureScreenshot', format='png', captureBeyondViewport=False)
            target = ROOT / 'src/main/resources/assets/tiktokmob/textures/gui/mission_gel.png'
            target.write_bytes(base64.b64decode(shot['data']))
            print(f'GEL_ATLAS_OK: {target} ({target.stat().st_size} bytes)')
        finally:
            socket.close(); process.terminate(); process.wait(timeout=10)


if __name__ == '__main__':
    main()
