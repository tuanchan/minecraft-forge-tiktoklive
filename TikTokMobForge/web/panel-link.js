(() => {
  const panel = document.querySelector('.minecraft-stage');
  const grid = panel.querySelector('.live-grid');
  let timer, sending = false, previous = '', width = 1200;
  function payload() {
    const style = getComputedStyle(panel);
    const appearance = {};
    for (const key of ['text','small','title','mob','gift','event','gap','width','split']) {
      appearance['--panel-' + key] = style.getPropertyValue('--panel-' + key).trim();
    }
    if (grid.clientWidth > 0) width = grid.clientWidth;
    return JSON.stringify({html:grid.outerHTML, appearance, width});
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
  new ResizeObserver(schedule).observe(grid);
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
