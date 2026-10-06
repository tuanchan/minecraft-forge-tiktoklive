from pathlib import Path
p=Path('TikTokMobForge/bridge/bridge.py');s=p.read_text(encoding='utf-8').replace('        publish(safe_name, str(payload), avatar_png)','        publish(safe_name, str(payload), avatar_png)\n        return').replace('"""Small square portrait for the in-world map; use an initial when TikTok has no image."""','"""High-resolution portrait for the desktop WebView overlay."""').replace('(32, 32), (0, 0, 0, 0)', '(256, 256), (0, 0, 0, 0)').replace('(1, 1, 30, 30)', '(1, 1, 254, 254)').replace('draw.text((16, 15), initial, font=ImageFont.load_default()', 'draw.text((128, 128), initial, font=ImageFont.load_default(size=128)');p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/web/index.html');s=p.read_text(encoding='utf-8');s=s.replace('Bảng bình luận ghim 3D','Bảng bình luận ghim WebView').replace('Bình luận ghim 3D','Bình luận ghim WebView').replace('Nhập nội dung sẽ hiện trên bảng trong Minecraft','Nhập nội dung sẽ hiện trên bảng overlay')
lines=s.splitlines()
for i,line in enumerate(lines):
 if '<p class="settings-help wide">Trong game: chạm G' in line or '<p class="settings-help wide">Trong Minecraft: chạm G' in line:
  lines[i]='          <p class="settings-help wide">Bảng WebView nổi trên màn hình, không chặn chuột và bàn phím. Mở bằng MO_GUI.bat; dùng Minecraft chế độ cửa sổ hoặc không viền. Chỉnh chiều rộng, chiều cao và bố cục tại đây; dùng Thử ghim / Bỏ ghim trong tab Kiểm thử.</p>'
p.write_text('\n'.join(lines)+'\n',encoding='utf-8')
