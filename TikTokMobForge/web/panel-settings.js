/* Local panel appearance, shared live between windows of this GUI. */
(() => {
  const key = 'tiktokmob.panel-appearance.v1';
  const fields = [
    ['text', 'Cỡ chữ chính', 12, 9, 32, 'px'],
    ['small', 'Cỡ chữ phụ / chú thích', 11, 8, 28, 'px'],
    ['title', 'Cỡ chữ tiêu đề nhóm', 20, 12, 36, 'px'],
    ['mob', 'Icon mob / phần thưởng', 76, 32, 160, 'px'],
    ['gift', 'Icon quà TikTok', 38, 20, 100, 'px'],
    ['event', 'Icon tương tác', 24, 16, 64, 'px'],
    ['gap', 'Khoảng cách các ô', 12, 0, 40, 'px'],
    ['width', 'Độ rộng ô tối thiểu', 80, 60, 220, 'px'],
    ['split', 'Độ rộng nhóm tương tác', 26, 20, 60, '%'],
  ];
  const defaults = Object.fromEntries(fields.map(([id, , value]) => [id, value]));
  const normalize = input => Object.fromEntries(fields.map(([id, , value, min, max]) => {
    const n = Number(input?.[id] ?? value);
    return [id, Number.isFinite(n) ? Math.max(min, Math.min(max, Math.round(n))) : value];
  }));
  let settings;
  try { settings = normalize(JSON.parse(localStorage.getItem(key) || '{}')); }
  catch { settings = {...defaults}; }
  const style = document.createElement('link');
  style.rel = 'stylesheet'; style.href = 'panel-settings.css?v=20260925-1';
  document.head.append(style);
  const panel = document.querySelector('.minecraft-stage');
  const button = document.querySelector('#panelSettingsBtn');
  const box = document.createElement('aside');
  box.id = 'panelSettingsBox'; box.hidden = true;
  box.setAttribute('aria-label', 'Căn chỉnh panel');
  box.innerHTML = `<div class="panel-settings-heading"><strong>Căn chỉnh panel</strong><button type="button" data-close aria-label="Đóng căn chỉnh">✕</button></div>
    <p>Chỉnh để xem ngay. Kéo tiêu đề để di chuyển hộp. Tự lưu trên máy này.</p>
    ${fields.map(([id, label, , min, max, unit]) => `<label class="panel-setting-row"><span>${label} (${unit})</span><input type="range" data-size="${id}" min="${min}" max="${max}" step="1"><input type="number" aria-label="${label}" data-size="${id}" min="${min}" max="${max}" step="1"></label>`).join('')}
    <div class="panel-settings-footer"><button type="button" data-reset>Khôi phục mặc định</button><span role="status" data-status></span></div>`;
  document.body.append(box);
  const heading = box.querySelector('.panel-settings-heading');
  let drag = null;
  heading.addEventListener('pointerdown', event => {
    if (event.target.closest('button')) return;
    const rect = box.getBoundingClientRect();
    drag = {x:event.clientX - rect.left, y:event.clientY - rect.top};
    heading.setPointerCapture(event.pointerId);
  });
  heading.addEventListener('pointermove', event => {
    if (!drag) return;
    box.style.left = Math.max(0, Math.min(innerWidth - box.offsetWidth, event.clientX - drag.x)) + 'px';
    box.style.top = Math.max(0, Math.min(innerHeight - box.offsetHeight, event.clientY - drag.y)) + 'px';
    box.style.right = 'auto';
  });
  ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(name => heading.addEventListener(name, () => { drag = null; }));
  function apply() {
    for (const [id, , , , , unit] of fields) panel.style.setProperty(`--panel-${id}`, settings[id] + unit);
    box.querySelectorAll('[data-size]').forEach(input => { input.value = settings[input.dataset.size]; });
  }
  function persist() {
    apply();
    try {
      localStorage.setItem(key, JSON.stringify(settings));
      box.querySelector('[data-status]').textContent = 'Đã lưu';
    } catch { box.querySelector('[data-status]').textContent = 'Chưa lưu được'; }
  }
  function close() { box.hidden = true; button.setAttribute('aria-expanded', 'false'); }
  button.addEventListener('click', () => {
    box.hidden = !box.hidden;
    button.setAttribute('aria-expanded', String(!box.hidden));
    if (!box.hidden) box.querySelector('[data-close]').focus();
  });
  box.querySelector('[data-close]').addEventListener('click', () => { close(); button.focus(); });
  box.addEventListener('keydown', event => {
    if (event.key === 'Escape') { close(); button.focus(); event.stopPropagation(); }
  });
  box.addEventListener('input', event => {
    const input = event.target;
    if (!input.dataset.size || input.value === '' || !Number.isFinite(input.valueAsNumber)) return;
    settings = normalize({...settings, [input.dataset.size]: input.valueAsNumber});
    persist();
  });
  box.querySelector('[data-reset]').addEventListener('click', () => { settings = {...defaults}; persist(); });
  document.querySelector('#copyPanelBtn').addEventListener('click', close);
  document.querySelectorAll('[data-tab]').forEach(tab => tab.addEventListener('click', close));
  window.addEventListener('storage', event => {
    if (event.key !== key) return;
    try { settings = normalize(JSON.parse(event.newValue || '{}')); apply(); } catch {}
  });
  apply();
})();
