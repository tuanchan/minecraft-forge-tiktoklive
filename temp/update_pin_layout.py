from pathlib import Path
root=Path('TikTokMobForge'); j=root/'src/main/java/vn/deadchan/tiktokmob'
def edit(p,a,b):
 s=p.read_text(encoding='utf-8'); assert a in s,(p,a[:80]); p.write_text(s.replace(a,b),encoding='utf-8')
# Shared browser geometry: percentages from the top-left, constrained to two disjoint columns.
(root/'web/pin-layout.js').write_text('''window.pinLayout = function(w, h, scale, avatarScale, ax, ay, cy, cx, ny) {
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
  let nameSize = 15 * scale * textScale; author.style.fontSize = nameSize + 'px';
  while (author.scrollWidth > author.clientWidth + 1 && nameSize > 1) author.style.fontSize = (--nameSize) + 'px';
  content.style.left = g.bodyX * 100 + '%'; content.style.top = g.bodyY * 100 + '%';
  content.style.width = g.bodyWidth + 'px'; content.style.minWidth = '0'; content.style.maxWidth = 'none';
  content.style.height = 'auto';
  let bodySize = 15 * scale * textScale; content.style.fontSize = bodySize + 'px';
  while ((content.scrollHeight > g.bodyHeight || content.scrollWidth > g.bodyWidth + 1) && bodySize > 1)
    content.style.fontSize = (--bodySize) + 'px';
};
''',encoding='utf-8')
edit(root/'web/index.html','  <script src="app.js?', '  <script src="pin-layout.js?v=20260927"></script>\n  <script src="app.js?')
edit(root/'web/pinned-overlay.html','<div id="content"><div id="author"></div><p id="comment"></p></div>', '<div id="author"></div><div id="content"><p id="comment"></p></div>')
edit(root/'web/pinned-overlay.html','#author{font-weight:700}', '#author{position:absolute;transform:translate(-50%,-50%);text-align:center;font-weight:700}')
edit(root/'web/pinned-overlay.html','margin:8px 0 0','margin:0')
edit(root/'web/pinned-overlay.html','.texture-surface #content{', '.texture-surface #content,.texture-surface #author{')
edit(root/'web/pinned-overlay.html','<script src="pinned-overlay.js">','<script src="pin-layout.js?v=20260927"></script><script src="pinned-overlay.js">')
p=root/'web/pinned-overlay.js'; s=p.read_text(encoding='utf-8'); start=s.index("  for (const id of ['avatar'"); end=s.index('  const src =',start)
s=s[:start]+'''  // Unhide before measuring so a newly received comment also gets fitted.
  visibility(Boolean(data.text));
  const geometry = {ax:n('avatar_x',17,0,100), ay:n('avatar_y',50,0,100),
    cx:n('content_x',66,0,100), cy:n('content_y',60,0,100), ny:n('author_y',82,0,100)};
  applyPinLayout(board, $('avatar'), $('author'), $('content'), geometry, scale,
    n('text_scale',1,.75,1.4), n('avatar_scale',1,.5,1.8));
  for (const key of ['left','top','width','height']) $('initial').style[key] = $('avatar').style[key];
'''+s[end:];p.write_text(s,encoding='utf-8')
edit(root/'web/app.js','  content.querySelector("p").style.color = value("pinned_board_comment_color") || "#f4f7fb";','''  content.querySelector("p").style.color = value("pinned_board_comment_color") || "#f4f7fb";
  applyPinLayout(preview, avatar, author, content, {
    ax:number("pinned_board_avatar_x",17), ay:number("pinned_board_avatar_y",50),
    cx:number("pinned_board_content_x",66), cy:number("pinned_board_content_y",60),
    ny:number("pinned_board_author_y",82)}, scale, textScale, avatarScale);''')
# Avatar location is needed by native name rendering to exactly match the captured WebView image.
edit(j/'BoardCaption.java','double scale, double x, double y, double authorX, double authorY)', 'double scale, double x, double y, double authorX, double authorY,\n                    double avatarX, double avatarY, double avatarScale, double boardScale)')
edit(j/'BoardCaption.java','|| value.authorX < 0', '|| !Double.isFinite(value.avatarX) || !Double.isFinite(value.avatarY)\n                || !Double.isFinite(value.avatarScale) || value.avatarScale <= 0\n                || !Double.isFinite(value.boardScale) || value.boardScale <= 0\n                || value.authorX < 0')
edit(j/'ServerPinnedCommentBoard.java','style.contentY(), style.authorX(), style.authorY()))','style.contentY(), style.authorX(), style.authorY(),\n                style.avatarX(), style.avatarY(), style.avatarScale(), style.scale()))')
edit(root/'src/test/java/vn/deadchan/tiktokmob/BoardTextChecks.java', '.05, 50, 40, 55, 25);', '.05, 50, 40, 55, 25, 17, 50, 1, 1);')
p=j/'WebBoardRenderer.java'; s=p.read_text(encoding='utf-8'); start=s.index('        int wrapWidth =');end=s.index('\n    private static Component rainbowTitle()',start)
s=s[:start]+'''        float avatarSize = Math.min((float)(.6048 * data.boardScale() * data.avatarScale()), Math.min(width * .26f, height * .40f));
        float avatarX = bound((float)data.avatarX() / 100, .04f + avatarSize / width / 2, .30f - avatarSize / width / 2);
        float avatarY = bound((float)data.avatarY() / 100, .28f + avatarSize / height / 2, .76f - avatarSize / height / 2);
        float nameY = bound((float)data.authorY() / 100, avatarY + avatarSize / height / 2 + .075f, .89f);
        float nameWidth = 2 * Math.min(avatarX - .025f, .315f - avatarX) * width;
        float bodyX = bound((float)data.x() / 100, .65f, .68f);
        float bodyY = bound((float)data.y() / 100, .38f, .80f);
        float bodyWidth = width * .56f;
        float bodyHeight = 2 * Math.min(bodyY - .26f, .94f - bodyY) * height;
        int wrapWidth = Math.max(1, (int)(bodyWidth / pixel));
        var lines = font.split(Component.literal(data.text()), wrapWidth);
        int widest = lines.stream().mapToInt(font::width).max().orElse(1);
        float bodyPixel = Math.min(pixel, Math.min(bodyWidth / Math.max(1, widest), bodyHeight / Math.max(11, lines.size() * 11)));
        float x = width * (bodyX - .5f);
        float top = height * (1 - bodyY) + lines.size() * 11 * bodyPixel / 2;
        int nameColor = 0xff000000 | Integer.parseInt(data.authorColor().substring(1), 16);
        int commentColor = 0xff000000 | Integer.parseInt(data.commentColor().substring(1), 16);
        var author = Component.literal("@" + data.author()).withStyle(style -> style.withBold(true));
        float namePixel = Math.min(pixel, Math.min(nameWidth / Math.max(1, font.width(author)), height * .10f / 9));
        draw(poses, collector, author.getVisualOrderText(), width * (avatarX - .5f),
            height * (1 - nameY) + namePixel * 4.5f, namePixel, nameColor);
        for (var line : lines) {
            draw(poses, collector, line, x, top, bodyPixel, commentColor);
            top -= bodyPixel * 11;
        }
    }

    private static float bound(float value, float low, float high) {
        return Math.max(low, Math.min(high, value));
    }
''' + s[end:];p.write_text(s,encoding='utf-8')
# New installations default to the requested layout; existing values remain safely constrained.
for p in [root/'GUI/config_service.py', j/'TikTokMobMod.java']:
 s=p.read_text(encoding='utf-8')
 import re
 for key,old,new in [('author_x','50.0','17.0'),('author_y','38.0','82.0'),('content_x','50.0','66.0'),('content_y','50.0','60.0')]:
  s=re.sub(r'(pinned_board_'+key+r'[" ]*[:=] )'+re.escape(old),r'\g<1>'+new,s)
 p.write_text(s,encoding='utf-8')
print('BOARD_LAYOUT_UPDATED')
