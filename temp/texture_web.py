from pathlib import Path
p=Path('TikTokMobForge/web/pinned-overlay.js');s=p.read_text(encoding='utf-8');s='const textureMode = new URLSearchParams(location.search).has("texture");\nlet lastFrame = "";\nwindow.frameCaptured = false;\n'+s
s=s.replace("  if (visible !== lastVisible) window.chrome?.webview?.postMessage({visible});", "  if (!textureMode && visible !== lastVisible) window.chrome?.webview?.postMessage({visible});")
s=s.replace("  board.style.width = Math.min(innerWidth - 20, 500 * scale * n('width',1,.7,2.5)) + 'px';", "  board.style.width = (textureMode ? 500 * n('width',1,.7,2.5) : Math.min(innerWidth - 20, 500 * scale * n('width',1,.7,2.5))) + 'px';")
s=s.replace("  board.style.height = Math.min(innerHeight * .8, 150 * scale * n('height',1,.7,2.5)) + 'px';", "  board.style.height = (textureMode ? 150 * n('height',1,.7,2.5) : Math.min(innerHeight * .8, 150 * scale * n('height',1,.7,2.5))) + 'px';\n  if (textureMode) { board.style.left = '0'; board.style.top = '0'; board.style.transform = 'none'; }")
s=s.replace("const scale = n('scale',1,.7,2);", "const scale = textureMode ? 1 : n('scale',1,.7,2);")
s=s.replace("    renderPinnedOverlay(await response.json());", """    const data = await response.json();
    renderPinnedOverlay(data);
    if (textureMode && data.text && data.token) {
      const signature = JSON.stringify([data.token, data.avatar, data.style]);
      if (signature !== lastFrame || !window.frameCaptured) {
        lastFrame = signature;
        window.frameCaptured = false;
        await document.fonts.ready;
        try { if (data.avatar) await $('avatar').decode(); } catch { }
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const rect = $('board').getBoundingClientRect();
        window.chrome?.webview?.postMessage({type:'frame', token:data.token, width:rect.width, height:rect.height});
      }
    }""")
p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/web/index.html');s=p.read_text(encoding='utf-8').replace('Bảng bình luận ghim WebView','Bảng bình luận ghim 3D · WebView').replace('Bình luận ghim WebView','Bình luận ghim 3D · WebView');s=s.replace('Bảng WebView nổi trên màn hình, không chặn chuột và bàn phím. Mở bằng MO_GUI.bat; dùng Minecraft chế độ cửa sổ hoặc không viền. Chỉnh chiều rộng, chiều cao và bố cục tại đây; dùng Thử ghim / Bỏ ghim trong tab Kiểm thử.','WebView vẽ nội dung lên bảng 3D trong Minecraft. Mở MO_GUI.bat để chạy bộ vẽ. Giữ G để kéo, G + cuộn chuột đổi kích thước; chạm G dừng quay, G hai lần quay tiếp; F ghim vị trí, X xóa bảng. Chiều rộng và chiều cao chỉnh riêng tại đây.');p.write_text(s,encoding='utf-8')
