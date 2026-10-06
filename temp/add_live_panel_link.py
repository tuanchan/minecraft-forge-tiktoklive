from pathlib import Path
r=Path('TikTokMobForge/web')
(r/'live_panel.py').write_text('''"""Display-only panel snapshots shared across independent browser profiles."""
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
import threading

PATH = Path(__file__).resolve().parents[1] / "GUI" / "live-panel.json"
LOCK = threading.Lock()
ALLOWED = {"div", "article", "span", "strong", "small", "b", "img", "p"}

class PanelMarkup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED:
            return
        clean = []
        for key, value in attrs:
            if key not in {"class", "id", "src", "alt", "title"} or value is None:
                continue
            if key == "src" and not (value.startswith(("/", "assets/", "https://", "http://")) or re.fullmatch(r"data:image/(?:png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+", value)):
                continue
            clean.append(f' {key}="{html.escape(value, quote=True)}"')
        self.output.append("<" + tag + "".join(clean) + ">")
    def handle_endtag(self, tag):
        if tag in ALLOWED and tag != "img":
            self.output.append("</" + tag + ">")
    def handle_data(self, data):
        self.output.append(html.escape(data))

def publish(data):
    markup = data.get("html", "")
    if not isinstance(markup, str) or len(markup) > 1_000_000:
        raise ValueError("Panel vượt kích thước cho phép")
    parser = PanelMarkup()
    parser.feed(markup)
    appearance = {key: value for key, value in data.get("appearance", {}).items()
                  if re.fullmatch(r"--panel-(text|small|title|mob|gift|event|gap|width|split)", key)
                  and isinstance(value, str) and re.fullmatch(r"[0-9]{1,3}(?:\\.[0-9]+)?(?:px|%)", value)}
    result = {"html": "".join(parser.output), "appearance": appearance}
    result["revision"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    with LOCK:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=PATH.parent, delete=False) as out:
            json.dump(result, out, ensure_ascii=False)
        os.replace(out.name, PATH)
    return {"revision": result["revision"]}

def snapshot():
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"html": "", "appearance": {}, "revision": ""}
''',encoding='utf-8')
p=r/'main.py';s=p.read_text(encoding='utf-8').replace('            if parsed.path == "/api/pinned-overlay":','            if parsed.path == "/api/live-panel":\n                import live_panel\n                return self.json_response(live_panel.snapshot())\n            if parsed.path == "/api/pinned-overlay":').replace('            if self.path == "/api/save":','            if self.path == "/api/live-panel":\n                import live_panel\n                return self.json_response(live_panel.publish(payload))\n            if self.path == "/api/save":');p.write_text(s,encoding='utf-8')
p=r/'index.html';s=p.read_text(encoding='utf-8').replace('<button id="copyPanelBtn"', '<button id="copyPanelLinkBtn" type="button" title="Dán vào nguồn Liên kết trong TikTok LIVE Studio trên cùng máy">Sao chép link</button><button id="copyPanelBtn"');s=s.replace('  <script src="app.js?', '  <script src="panel-link.js?v=20260927"></script>\n  <script src="app.js?');p.write_text(s,encoding='utf-8')
(r/'panel-link.js').write_text('''(() => {
  const panel = document.querySelector('.minecraft-stage');
  const grid = panel.querySelector('.live-grid');
  let timer, sending = false, previous = '';
  function payload() {
    const style = getComputedStyle(panel);
    const appearance = {};
    for (const key of ['text','small','title','mob','gift','event','gap','width','split']) {
      appearance['--panel-' + key] = style.getPropertyValue('--panel-' + key).trim();
    }
    return JSON.stringify({html:grid.outerHTML, appearance});
  }
  async function publish() {
    if (document.body.classList.contains('detached-panel')) return;
    if (sending) { schedule(); return; }
    const body = payload();
    if (body === previous || !grid.querySelector('.event-card')) return;
    sending = true;
    try {
      const response = await fetch('/api/live-panel', {method:'POST',headers:{'Content-Type':'application/json'},body});
      if (!response.ok) throw new Error('Không cập nhật được panel');
      previous = body;
    } finally { sending = false; }
  }
  function schedule() { clearTimeout(timer); timer = setTimeout(() => publish().catch(() => {}), 150); }
  new MutationObserver(schedule).observe(panel, {childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['style','src']});
  setInterval(() => publish().catch(() => {}), 2000);
  document.getElementById('copyPanelLinkBtn').addEventListener('click', async () => {
    const url = new URL('/live-panel.html', location.origin).href;
    try {
      await publish();
      try { await navigator.clipboard.writeText(url); }
      catch {
        const input = document.createElement('textarea'); input.value = url;
        input.style.position = 'fixed'; input.style.opacity = '0'; document.body.append(input); input.select();
        const copied = document.execCommand('copy'); input.remove();
        if (!copied) throw new Error('clipboard');
      }
      toast('Đã sao chép link. Dán vào nguồn Liên kết trong LIVE Studio. Giữ tool mở; chọn độ phân giải 1920 × 1080.');
    } catch {
      const dialog = document.createElement('dialog');
      const label = document.createElement('p'); label.textContent = 'Link panel — sao chép và dán vào LIVE Studio trên cùng máy:';
      const input = document.createElement('input'); input.value = url; input.readOnly = true;
      const close = document.createElement('button'); close.textContent = 'Đóng'; close.onclick = () => { dialog.close(); dialog.remove(); };
      dialog.append(label,input,close); document.body.append(dialog); dialog.showModal(); input.select();
    }
  });
  schedule();
})();
''',encoding='utf-8')
(r/'live-panel.html').write_text('''<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panel LIVE</title>
<link rel="stylesheet" href="styles.css"><link rel="stylesheet" href="monochrome.css"><link rel="stylesheet" href="panel-settings.css">
<style>
html,body{margin:0!important;padding:0!important;min-width:0!important;width:100%;height:100%;overflow:hidden!important;background:transparent!important}
#panel{position:absolute;left:0;top:0;width:1200px;max-width:none;min-height:0;padding:12px!important;transform-origin:top left;border:0!important;border-radius:0!important;background:#fff!important;box-shadow:none!important}
#panel .live-grid{grid-template-columns:minmax(0,var(--panel-split,26%)) minmax(0,1fr)!important;margin:0!important}
#panel .event-cards,#panel .gift-preview{grid-template-columns:repeat(auto-fit,minmax(min(100%,max(var(--panel-width,80px),var(--panel-mob,76px),var(--panel-gift,38px),var(--panel-event,24px))),1fr))!important}
#panel button,#panel .link{display:none!important}
#panel:empty{display:none}
</style></head><body><section id="panel" class="minecraft-stage"></section><script src="live-panel.js"></script></body></html>
''',encoding='utf-8')
(r/'live-panel.js').write_text('''const panel = document.getElementById('panel');
let revision = null;
function fit() {
  const scale = Math.min(innerWidth / 1200, innerHeight / Math.max(1,panel.scrollHeight));
  panel.style.transform = `scale(${scale})`;
}
async function poll() {
  try {
    const response = await fetch('/api/live-panel', {cache:'no-store'});
    if (!response.ok) throw new Error('Panel unavailable');
    const data = await response.json();
    if (data.revision !== revision) {
      panel.innerHTML = data.html || '';
      for (const [key,value] of Object.entries(data.appearance || {})) panel.style.setProperty(key,value);
      revision = data.revision;
      panel.querySelectorAll('img').forEach(img => img.addEventListener('load', fit, {once:true}));
      fit();
    }
  } catch { /* Retain the last panel while the tool reconnects. */ }
  finally { setTimeout(poll, 500); }
}
new ResizeObserver(fit).observe(panel);
addEventListener('resize',fit);
poll();
''',encoding='utf-8')
print('LIVE_PANEL_LINK_ADDED')
