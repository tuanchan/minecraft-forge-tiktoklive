/* Shared form controls remain managed by app.js autosave. */
let giftMedia = {phrases: [], gifs: []};
let giftPreviewLabel = "";

async function loadGiftMedia() {
  const previousPhrase = value('gift_phrase_id') || state?.bridge?.gift_phrase_id || 'onichan';
  const previousGif = value('gift_gif_file') || state?.bridge?.gift_gif_file || 'kawaiianimegirlGIF.gif';
  giftMedia = await api('/api/gift-media');
  $('#gift_phrase_id').innerHTML = giftMedia.phrases.map(p => `<option value="${escapeHtml(p.id)}">${escapeHtml(p.text)} — ${escapeHtml(p.name)}</option>`).join('');
  $('#gift_gif_file').innerHTML = giftMedia.gifs.map(name => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
  setValue('gift_phrase_id', previousPhrase);
  setValue('gift_gif_file', previousGif);
  if (!value('gift_gif_file') && giftMedia.gifs.length) setValue('gift_gif_file', giftMedia.gifs[0]);
  $('#giftMediaStatus').textContent = `${giftMedia.gifs.length} GIF · web/assets/GIF · thêm file rồi bấm Nạp lại.`;
  updateGiftPreviewImage(); renderGiftSettings();
}

function updateGiftPreviewImage(name = value('gift_gif_file')) {
  if (!name) return;
  $('#giftPreviewGif').src = '/assets/GIF/' + encodeURIComponent(name);
}

function renderGiftSettings() {
  const mode = value('gift_phrase_mode');
  const phrase = giftMedia.phrases.find(p => p.id === value('gift_phrase_id')) || giftMedia.phrases[0];
  $('#giftPhraseHelp').textContent = mode === 'random' ? 'Mỗi lượt chọn một câu tiếng Nhật trong danh sách. Giữ nguyên nhân vật VOICEVOX đang chọn.'
    : mode === 'custom' ? 'VOICEVOX đọc đúng câu tiếng Nhật tự nhập. Chờ comment đang đọc kết thúc rồi mới phát.' : (phrase?.text || '') + ' · ' + (phrase?.name || '');
  $('#giftPreviewPhrase').textContent = mode === 'custom' ? value('gift_phrase_custom') || 'お兄ちゃん、ありがとう！'
    : mode === 'random' && giftPreviewLabel ? giftPreviewLabel : phrase?.label || 'THANKIU ONICHANN~~';
  const preview = $('#giftPositionPreview'), sample = $('#giftPositionSample');
  const viewport = state?.minecraft_viewport || {width:1920,height:1080};
  preview.style.aspectRatio = `${viewport.width} / ${viewport.height}`;
  const scale = Math.min(numberValue('gift_overlay_width', 320) / 320 * preview.clientWidth / 1920,
    preview.clientHeight / Math.max(1, sample.offsetHeight));
  sample.style.transform = `scale(${scale})`;
  sample.style.left = `${Math.max(0, preview.clientWidth - sample.offsetWidth * scale) * numberValue('gift_overlay_x', 50) / 100}px`;
  sample.style.top = `${Math.max(0, preview.clientHeight - sample.offsetHeight * scale) * numberValue('gift_overlay_y', 45) / 100}px`;
}

function bindGiftSettings() {
  $('#reloadGiftMediaBtn').addEventListener('click', () => loadGiftMedia().then(scheduleAutoSave).catch(error => toast(error.message, true)));
  $('#randomThanksBtn').addEventListener('click', () => { setValue('gift_phrase_mode', 'random'); renderGiftSettings(); scheduleAutoSave(); });
  $('#shuffleGiftPreviewBtn').addEventListener('click', () => {
    const phrase = giftMedia.phrases[Math.floor(Math.random() * giftMedia.phrases.length)];
    giftPreviewLabel = phrase?.label || '';
    if (checked('gift_gif_random')) updateGiftPreviewImage(giftMedia.gifs[Math.floor(Math.random() * giftMedia.gifs.length)]);
    renderGiftSettings();
  });
  $('#gift_gif_file').addEventListener('change', () => { updateGiftPreviewImage(); renderGiftSettings(); });
  $$('[data-view="voicevox"] [data-config]').forEach(node => node.addEventListener('input', renderGiftSettings));
  $('#giftPreviewGif').addEventListener('load', renderGiftSettings);
  new ResizeObserver(renderGiftSettings).observe($('#giftPositionPreview'));
  const preview = $('#giftPositionPreview'), sample = $('#giftPositionSample');
  let dragging = false, dx = 0, dy = 0;
  sample.addEventListener('pointerdown', event => {
    dragging = true; sample.setPointerCapture(event.pointerId); event.preventDefault();
    const rect = sample.getBoundingClientRect(); dx = event.clientX - rect.left; dy = event.clientY - rect.top;
  });
  sample.addEventListener('pointermove', event => {
    if (!dragging) return;
    const rect = preview.getBoundingClientRect(), bounds = sample.getBoundingClientRect();
    const clamp = n => Math.round(Math.max(0, Math.min(100, n)));
    setValue('gift_overlay_x', clamp((event.clientX - rect.left - dx) / Math.max(1, preview.clientWidth - bounds.width) * 100));
    setValue('gift_overlay_y', clamp((event.clientY - rect.top - dy) / Math.max(1, preview.clientHeight - bounds.height) * 100));
    renderGiftSettings();
  });
  ['pointerup', 'pointercancel'].forEach(name => sample.addEventListener(name, () => { dragging = false; scheduleAutoSave(); }));
}
