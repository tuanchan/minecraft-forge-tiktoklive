const textureMode = new URLSearchParams(location.search).has("texture");
let lastFrame = "";
let frameRevision = 0;
window.capturedFrame = -1;
const $ = id => document.getElementById(id);
const palette = {black:'#1d1d21',gray:'#474f52',light_gray:'#9d9d97',white:'#f9fffe',blue:'#3c44aa',light_blue:'#67b4d1',cyan:'#169c9c',purple:'#8932b8',magenta:'#bd55b7',pink:'#f38baa',red:'#b02e26',orange:'#f9801d',yellow:'#fed83d',lime:'#80c71f',green:'#5e7c16',brown:'#835432'};
let lastVisible;
function visibility(visible) {
  $('board').hidden = !visible;
  if (!textureMode && visible !== lastVisible) window.chrome?.webview?.postMessage({visible});
  lastVisible = visible;
}
function renderPinnedOverlay(data) {
  $('missionBoard').hidden = true;
  const s = data.style || {};
  const n = (key, fallback, min, max) => {
    const v = Number(s['pinned_board_' + key] ?? fallback);
    return Number.isFinite(v) ? Math.max(min, Math.min(max, v)) : fallback;
  };
  const scale = textureMode ? 1 : n('scale',1,.1,2);
  const board = $('board');
  board.classList.toggle('texture-surface', textureMode);
  board.style.width = (textureMode ? 500 * n('width',1,.7,2.5) : Math.min(innerWidth - 20, 500 * scale * n('width',1,.7,2.5))) + 'px';
  board.style.height = (textureMode ? 150 * n('height',1,.7,2.5) : Math.min(innerHeight * .8, 150 * scale * n('height',1,.7,2.5))) + 'px';
  if (textureMode) { board.style.left = '0'; board.style.top = '0'; board.style.transform = 'none'; }
  board.style.background = palette[s.pinned_board_background] || palette.black;
  board.style.borderColor = palette[s.pinned_board_border] || palette.light_blue;
  board.style.borderRadius = n('corner_radius',.16,0,.4) * 80 * scale + 'px';
  $('author').textContent = '@' + (data.author || 'TikTok');
  $('comment').textContent = data.text || '';
  const color = (value, fallback) => /^#[0-9a-f]{6}$/i.test(value || '') ? value : fallback;
  $('author').style.color = color(s.pinned_board_author_color,'#ffd99b');
  $('comment').style.color = color(s.pinned_board_comment_color,'#f4f7fb');
  $('content').style.fontSize = 15 * scale * n('text_scale',1,.75,1.4) + 'px';
  board.querySelector('h1').style.fontSize = 18 * scale * n('text_scale',1,.75,1.4) + 'px';
  // Unhide before measuring so a newly received comment also gets fitted.
  visibility(Boolean(data.text));
  const geometry = {ax:n('avatar_x',17,0,100), ay:n('avatar_y',50,0,100),
    cx:n('content_x',66,0,100), cy:n('content_y',60,0,100), ny:n('author_y',82,0,100)};
  applyPinLayout(board, $('avatar'), $('author'), $('content'), geometry, scale,
    n('text_scale',1,.75,1.4), n('avatar_scale',1,.5,1.8));
  for (const key of ['left','top','width','height']) $('initial').style[key] = $('avatar').style[key];
  const src = /^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(data.avatar || '') ? data.avatar : '';
  if ($('avatar').getAttribute('src') !== src) $('avatar').src = src;
  $('avatar').hidden = !src;
  $('initial').textContent = Array.from(data.author || '?')[0].toUpperCase();
  $('initial').style.display = src ? 'none' : 'grid';
  visibility(Boolean(data.text));
}
const escapeMission = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function missionText(rule) {
  return `mission:${rule.id}:${rule.current}:${rule.target}:${rule.kind}:${rule.milestones}`;
}
async function missionToken(rule) {
  const bytes = new TextEncoder().encode(String(rule.title).trim() + '\n' + missionText(rule).trim());
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, '0')).join('').slice(0, 32);
}
function renderMissionOverlay(rule) {
  $('board').hidden = true;
  const kill = rule.kind === 'kill';
  const percent = Math.max(0, Math.min(100, 100 * Number(rule.current) / Math.max(1, Number(rule.target))));
  const percentText = percent > 0 && percent < .01 ? '<0.01' : percent < 1 ? percent.toFixed(2).replace(/0+$/,'').replace(/\.$/,'') : String(Math.round(percent));
  const milestones = Math.max(1, Number(rule.milestones) || 10);
  const mission = $('missionBoard');
  mission.innerHTML = `<div class="mission-card ${kill?'mission-kill':'mission-diamond'}" style="--mission-progress:${percent}%;--mission-steps:${milestones}">
    <img class="mission-icon mission-icon-left" src="/assets/${kill?'iconkiemkc.png':'Cu%E1%BB%91c%20chim%20kim%20c%C6%B0%C6%A1ng%20ph%C3%A1t%20s%C3%A1ng%20pixel%20art.png'}" alt="">
    <div class="mission-card-body"><strong>${escapeMission(rule.title)}</strong><div class="mission-bar"><i></i><b></b><span>${percentText}% · ${rule.current} / ${rule.target}</span></div></div>
    <img class="mission-icon mission-icon-right" src="/assets/${kill?'zombieprogess.png':'quangkc.png'}" alt="">
    ${kill?'':'<img class="mission-diamond-gem" src="/assets/iconkc.png" alt="">'}
  </div>`;
  mission.hidden = false;
}
$('avatar').onerror = () => { $('avatar').hidden = true; $('initial').style.display = 'grid'; };
const capturedTokens = new Map();
let pendingCapture = null;
async function poll() {
  try {
    // Keep the same DOM until the native capture acknowledges it; never photograph a later comment by mistake.
    if (pendingCapture && window.capturedFrame !== pendingCapture.revision) {
      if (Date.now() - pendingCapture.sent > 3000) {
        window.chrome?.webview?.postMessage(pendingCapture.message);
        pendingCapture.sent = Date.now();
      }
      return;
    }
    if (pendingCapture) {
      capturedTokens.set(pendingCapture.token, pendingCapture.signature);
      pendingCapture = null;
    }
    const [response, missionResponse] = await Promise.all([
      fetch('/api/pinned-overlay', {cache:'no-store'}), fetch('/api/missions', {cache:'no-store'})
    ]);
    if (!response.ok || !missionResponse.ok) throw new Error('Overlay unavailable');
    const data = await response.json(), missionData = await missionResponse.json();
    if (!textureMode) { renderPinnedOverlay(data); return; }
    const boards = [...(data.boards || [])];
    if (data.text && data.token) {
      const index = boards.findIndex(board => board.token === data.token);
      if (index >= 0) boards.splice(index, 1);
      boards.unshift(data);
    }
    const missions = [];
    for (const player of missionData.progress?.players || []) for (const rule of player.rules || []) {
      if (rule.mode !== '3d') continue;
      missions.push({...rule, token:await missionToken(rule), mission:true});
    }
    const wanted = [...missions, ...boards].find(board => {
      const signature = JSON.stringify([board.token, board.avatar, data.style]);
      // Frozen boards retain their first captured style; the newest one can still be edited.
      return !capturedTokens.has(board.token) || (board.token === data.token && capturedTokens.get(board.token) !== signature);
    });
    if (!wanted) return;
    if (wanted.mission) renderMissionOverlay(wanted); else renderPinnedOverlay({...wanted, style:data.style});
    const signature = JSON.stringify([wanted.token, wanted.avatar, data.style]);
    await document.fonts.ready;
    try {
      const images = wanted.mission ? [...$('missionBoard').querySelectorAll('img')] : wanted.avatar ? [$('avatar')] : [];
      await Promise.all(images.map(image => image.decode().catch(() => {})));
    } catch { }
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const rect = $(wanted.mission ? 'missionBoard' : 'board').getBoundingClientRect();
    const message = {type:'frame', token:wanted.token, revision:++frameRevision, width:rect.width, height:rect.height, preserveExisting:wanted.token !== data.token};
    pendingCapture = {token:wanted.token, signature, revision:frameRevision, message, sent:Date.now()};
    window.chrome?.webview?.postMessage(message);
  } catch { if (!pendingCapture) visibility(false); }
  finally { setTimeout(poll, 350); }
}
poll();
