from pathlib import Path
r=Path('TikTokMobForge')
def e(f,a,b):
 p=r/f;s=p.read_text(encoding='utf-8');assert a in s,(f,a);p.write_text(s.replace(a,b),encoding='utf-8')
e('src/main/java/vn/deadchan/tiktokmob/PinnedCommentBoard.java','position.scale + steps * 0.1, 0.5, 2.5','position.scale * Math.pow(1.12, steps), 0.05, 2.5')
e('src/main/java/vn/deadchan/tiktokmob/PinnedCommentBoard.java','clamp(read.scale, 0.5, 2.5)','clamp(read.scale, 0.05, 2.5)')
e('src/main/java/vn/deadchan/tiktokmob/ServerPinnedCommentBoard.java','clamp(packet.scale(), 0.5, 2.5)','clamp(packet.scale(), 0.05, 2.5)')
e('src/main/java/vn/deadchan/tiktokmob/ServerPinnedCommentBoard.java','+ (5.4 * style.scale() * style.width()) + ":" + panelHeight(text, style));','+ (5.4 * style.scale() * style.width()) + ":" + panelHeight(text, style) + ":"\n            + BoardCaption.encode(new BoardCaption(author, text, style.authorColor(), style.commentColor(),\n                style.scale() * style.textScale(), style.contentX(), style.contentY())));')
e('web/pinned-overlay.js',"  const board = $('board');","  const board = $('board');\n  board.classList.toggle('texture-surface', textureMode);")
p=r/'web/pinned-overlay.html';s=p.read_text(encoding='utf-8');s=s.replace('</style>', '''.texture-surface h1,.texture-surface #content{visibility:hidden}
.board-pin{position:absolute;right:12px;top:8px;width:28px;height:28px;background:#ef3434;mask:url('/icon/thumbtack-solid-full.svg') center/contain no-repeat;transform:rotate(24deg);filter:drop-shadow(2px 3px 1px #0008)}
</style>''').replace('<h1>BÌNH LUẬN GHIM</h1>','<h1>BÌNH LUẬN GHIM</h1><i class="board-pin" aria-hidden="true"></i>');p.write_text(s,encoding='utf-8')
p=r/'web/index.html';s=p.read_text(encoding='utf-8');s=s.replace('<strong id="pinnedBoardTitle">BÌNH LUẬN GHIM</strong>','<strong id="pinnedBoardTitle">BÌNH LUẬN GHIM</strong><i class="board-pin" aria-hidden="true"></i>');a='<div id="pinnedBoardAvatar" data-board-drag="avatar">A</div>';s=s.replace(a,a+''.join(f'<span class="board-resize board-resize-{side}" data-board-resize="{side}" title="Kéo để đổi kích thước"></span>' for side in ['n','s','e','w','ne','nw','se','sw']));p.write_text(s,encoding='utf-8')
p=r/'web/styles.css';s=p.read_text(encoding='utf-8');s+='''
#pinnedBoardPreview .board-pin{position:absolute;right:12px;top:8px;width:28px;height:28px;background:#ef3434;mask:url('/icon/thumbtack-solid-full.svg') center/contain no-repeat;transform:rotate(24deg);pointer-events:none}
.board-resize{position:absolute;z-index:5;touch-action:none}
.board-resize-n,.board-resize-s{left:14px;right:14px;height:9px;cursor:ns-resize}
.board-resize-n{top:0}.board-resize-s{bottom:0}
.board-resize-e,.board-resize-w{top:14px;bottom:14px;width:9px;cursor:ew-resize}
.board-resize-e{right:0}.board-resize-w{left:0}
.board-resize-ne,.board-resize-nw,.board-resize-se,.board-resize-sw{width:14px;height:14px;background:#fff9;border:2px solid #63dbf0;border-radius:3px}
.board-resize-ne{right:0;top:0;cursor:nesw-resize}.board-resize-nw{left:0;top:0;cursor:nwse-resize}
.board-resize-se{right:0;bottom:0;cursor:nwse-resize}.board-resize-sw{left:0;bottom:0;cursor:nesw-resize}
''';p.write_text(s,encoding='utf-8')
e('web/app.js','  let drag = null;\n  preview.addEventListener("pointerdown", event => {','''  let drag = null, resize = null;
  preview.addEventListener("pointerdown", event => {
    const handle = event.target.closest("[data-board-resize]");
    if (handle) {
      const rect = preview.getBoundingClientRect();
      resize = {side:handle.dataset.boardResize, x:event.clientX, y:event.clientY,
        width:rect.width, height:rect.height, scale:Number(value("pinned_board_scale")),
        w:Number(value("pinned_board_width")), h:Number(value("pinned_board_height"))};
      handle.setPointerCapture(event.pointerId);
      event.preventDefault(); return;
    }''')
e('web/app.js','  preview.addEventListener("pointermove", event => {\n    if (!drag) return;','''  preview.addEventListener("pointermove", event => {
    if (resize) {
      const dx = (event.clientX - resize.x) * (resize.side.includes("w") ? -1 : 1) * 2 / resize.width;
      const dy = (event.clientY - resize.y) * (resize.side.includes("n") ? -1 : 1) * 2 / resize.height;
      const set = (key, v) => {
        const input = document.getElementById(key);
        setValue(key, Math.round(Math.max(Number(input.min), Math.min(Number(input.max), v)) * 100) / 100);
      };
      if (resize.side.length === 2) set("pinned_board_scale", resize.scale * Math.max(.05, 1 + (dx + dy) / 2));
      else if (resize.side === "e" || resize.side === "w") set("pinned_board_width", resize.w * (1 + dx));
      else set("pinned_board_height", resize.h * (1 + dy));
      renderPinnedBoardPreview(); scheduleAutoSave(); return;
    }
    if (!drag) return;''')
e('web/app.js','() => { drag = null; }','() => { drag = null; resize = null; }')
for f in ['web/main.py','src/main/java/vn/deadchan/tiktokmob/TikTokMobMod.java']:
 p=r/f;s=p.read_text(encoding='utf-8').replace('("pinned_board_scale", 0.7, 2.0)','("pinned_board_scale", 0.1, 2.0)').replace('clamp(pinned_board_scale, 0.7, 2.0)','clamp(pinned_board_scale, 0.1, 2.0)');p.write_text(s,encoding='utf-8')
e('web/index.html','id="pinned_board_scale" data-config="mod" type="number" min="0.7"','id="pinned_board_scale" data-config="mod" type="number" min="0.1"')
e('web/pinned-overlay.js',"n('scale',1,.7,2)","n('scale',1,.1,2)")
