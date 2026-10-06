window.pinLayout = function(w, h, scale, avatarScale, ax, ay, cy, cx, ny) {
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const size = Math.min(56 * scale * avatarScale, w * .26, h * .40);
  const avatarX = clamp(ax / 100, .04 + size / w / 2, .30 - size / w / 2);
  const avatarY = clamp(ay / 100, .28 + size / h / 2, .76 - size / h / 2);
  const nameY = clamp(ny / 100, avatarY + size / h / 2 + .075, .89);
  const bodyX = clamp(cx / 100, .65, .68), bodyY = clamp(cy / 100, .38, .80);
  return {size, avatarX, avatarY, nameY, nameWidth: 2 * Math.min(avatarX - .025, .315 - avatarX) * w,
    bodyX, bodyY, bodyWidth: .56 * w, bodyHeight: 2 * Math.min(bodyY - .26, .94 - bodyY) * h};
};
window.applyPinLayout = function(board, avatar, author, content, settings, scale, textScale, avatarScale) {
  const w = board.clientWidth, h = board.clientHeight;
  if (!w || !h) return;
  const g = pinLayout(w, h, scale, avatarScale, settings.ax, settings.ay, settings.cy, settings.cx, settings.ny);
  avatar.style.left = author.style.left = g.avatarX * 100 + '%';
  avatar.style.top = g.avatarY * 100 + '%';
  avatar.style.width = avatar.style.height = g.size + 'px';
  author.style.top = g.nameY * 100 + '%'; author.style.width = g.nameWidth + 'px';
  author.style.whiteSpace = 'nowrap'; author.style.maxWidth = 'none';
  author.style.lineHeight = '1.2';
  let nameSize = Math.min(15 * scale * textScale, h * .1 / 1.2); author.style.fontSize = nameSize + 'px';
  while (author.scrollWidth > author.clientWidth + 1 && nameSize > 1) author.style.fontSize = (--nameSize) + 'px';
  content.style.left = g.bodyX * 100 + '%'; content.style.top = g.bodyY * 100 + '%';
  content.style.width = g.bodyWidth + 'px'; content.style.minWidth = '0'; content.style.maxWidth = 'none';
  content.style.height = 'auto';
  let bodySize = 15 * scale * textScale; content.style.fontSize = bodySize + 'px';
  while ((content.scrollHeight > g.bodyHeight || content.scrollWidth > g.bodyWidth + 1) && bodySize > 1)
    content.style.fontSize = (--bodySize) + 'px';
};
