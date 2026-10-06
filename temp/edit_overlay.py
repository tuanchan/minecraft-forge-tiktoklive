from pathlib import Path
root=Path('TikTokMobForge')
def edit(file,a,b):
 p=root/file;s=p.read_text(encoding='utf-8');assert a in s,(file,a);p.write_text(s.replace(a,b),encoding='utf-8')
edit('bridge/bridge.py','    encoded_avatar = base64.b64encode(avatar_png[:65_536]).decode("ascii")','    if interaction == "pin_comment":\n        from pinned_overlay import publish\n        publish(safe_name, str(payload), avatar_png)\n    encoded_avatar = "" if interaction == "pin_comment" else base64.b64encode(avatar_png[:65_536]).decode("ascii")')
edit('bridge/bridge.py','load_avatar(url, 32)', 'load_avatar(url, 256)')
edit('bridge/gift_alerts.py','("avatar_thumb", "avatar_medium", "avatar_large", "avatar")','("avatar_large", "avatar_medium", "avatar", "avatar_thumb")')
edit('web/main.py','            if parsed.path == "/api/state":','            if parsed.path == "/api/pinned-overlay":\n                from pinned_overlay import snapshot\n                return self.json_response({**snapshot(), "style": CONTROLLER.state()["mod"]})\n            if parsed.path == "/api/state":')
edit('src/main/java/vn/deadchan/tiktokmob/TikTokMobMod.java','ServerPinnedCommentBoard.tick(event.server(), pinnedAuthor, pinnedComment, pinnedAvatar, settings);','// Pinned comments now render in the desktop WebView overlay. Clear old world entities.\n        ServerPinnedCommentBoard.tick(event.server(), "", "", new byte[0], settings);')
edit('Desktop/MainForm.cs','    private bool copyingPanel;','    private bool copyingPanel;\n    private PinOverlayForm? pinOverlay;')
edit('Desktop/MainForm.cs','lifetime.Cancel(); browser.Dispose();','lifetime.Cancel(); pinOverlay?.Dispose(); browser.Dispose();')
edit('Desktop/MainForm.cs','            status.Visible = false;','            status.Visible = false;\n            pinOverlay = new PinOverlayForm();\n            await pinOverlay.InitializeAsync(environment, appOrigin);')
