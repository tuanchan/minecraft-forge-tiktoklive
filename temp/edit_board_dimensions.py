from pathlib import Path
root=Path('TikTokMobForge')
def edit(file,a,b):
 p=root/file;s=p.read_text(encoding='utf-8');assert a in s,(file,a);p.write_text(s.replace(a,b),encoding='utf-8')
edit('GUI/config_service.py','    "pinned_board_scale": 1.0,','    "pinned_board_scale": 1.0,\n    "pinned_board_width": 1.0,\n    "pinned_board_height": 1.0,')
edit('web/main.py','            ("pinned_board_scale", 0.7, 2.0),','            ("pinned_board_scale", 0.7, 2.0),\n            ("pinned_board_width", 0.7, 2.5),\n            ("pinned_board_height", 0.7, 2.5),')
edit('web/index.html','          <label>Cỡ chữ<input id="pinned_board_text_scale"','          <label>Chiều rộng bảng (×)<input id="pinned_board_width" data-config="mod" type="number" min="0.7" max="2.5" step="0.05"></label>\n          <label>Chiều cao bảng (×)<input id="pinned_board_height" data-config="mod" type="number" min="0.7" max="2.5" step="0.05"></label>\n          <label>Cỡ chữ<input id="pinned_board_text_scale"')
edit('web/app.js','  preview.style.width = `${Math.round(500 * scale)}px`;','  preview.style.width = `${Math.round(500 * scale * number("pinned_board_width", 1))}px`;\n  preview.style.height = `${Math.round(150 * scale * number("pinned_board_height", 1))}px`;\n  preview.style.minHeight = "0";\n  preview.style.aspectRatio = "auto";')
p='src/main/java/vn/deadchan/tiktokmob/TikTokMobMod.java'
edit(p,'        double pinned_board_scale = 1.0;','        double pinned_board_scale = 1.0;\n        double pinned_board_width = 1.0;\n        double pinned_board_height = 1.0;')
edit(p,'            pinned_board_scale = clamp(pinned_board_scale, 0.7, 2.0);','            pinned_board_scale = clamp(pinned_board_scale, 0.7, 2.0);\n            pinned_board_width = clamp(pinned_board_width, 0.7, 2.5);\n            pinned_board_height = clamp(pinned_board_height, 0.7, 2.5);')
p='src/main/java/vn/deadchan/tiktokmob/ServerPinnedCommentBoard.java'
edit(p,'double avatarX, double avatarY, double contentX, double contentY) {','double avatarX, double avatarY, double contentX, double contentY,\n                         double width, double height) {')
edit(p,'settings.pinned_board_content_x, settings.pinned_board_content_y);','settings.pinned_board_content_x, settings.pinned_board_content_y,\n                settings.pinned_board_width, settings.pinned_board_height);')
edit(p,'5.4 * style.scale()', '5.4 * style.scale() * style.width()')
edit(p,'(style.contentX() - 50) * 0.054 * style.scale()', '(style.contentX() - 50) * 0.054 * style.scale() * style.width()')
edit(p,'float width = 5.4f * size;', 'float width = (float) (5.4 * size * style.width());')
edit(p,'double width = 5.4 * scale;', 'double width = 5.4 * scale * board.style.width();')
edit(p,'+ 0.1f) * style.scale());', '+ 0.1f) * style.scale() * style.height());')
