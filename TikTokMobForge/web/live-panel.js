const panel = document.getElementById('panel');
let revision = null, width = 1224;
function fit() {
  const scale = Math.min(innerWidth / width, innerHeight / Math.max(1,panel.scrollHeight));
  panel.style.transform = `scale(${scale})`;
}
async function poll() {
  try {
    const response = await fetch('/api/live-panel', {cache:'no-store'});
    if (!response.ok) throw new Error('Panel unavailable');
    const data = await response.json();
    if (data.revision !== revision) {
      width = (data.width || 1200) + 24;
      panel.style.width = width + 'px';
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
