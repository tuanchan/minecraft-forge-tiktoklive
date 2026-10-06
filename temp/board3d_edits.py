from pathlib import Path
r=Path('TikTokMobForge')
def edit(f,a,b):
 p=r/f;s=p.read_text(encoding='utf-8');assert a in s,(f,a);p.write_text(s.replace(a,b),encoding='utf-8')
edit('bridge/bridge.py','        publish(safe_name, str(payload), avatar_png)\n        return','        publish(safe_name, str(payload)[:200], avatar_png)')
edit('bridge/pinned_overlay.py','import json','import json\nimport hashlib')
edit('bridge/pinned_overlay.py','"updated": time.time()','"token": hashlib.sha256((str(author)[:64].strip() + "\\n" + str(text)[:200].strip()).encode("utf-8")).hexdigest()[:32],\n            "updated": time.time()')
edit('src/main/java/vn/deadchan/tiktokmob/TikTokMobMod.java','// Pinned comments now render in the desktop WebView overlay. Clear old world entities.\n        ServerPinnedCommentBoard.tick(event.server(), "", "", new byte[0], settings);','ServerPinnedCommentBoard.tick(event.server(), pinnedAuthor, pinnedComment, pinnedAvatar, settings);')
p='src/main/java/vn/deadchan/tiktokmob/ServerPinnedCommentBoard.java'
edit(p,'setText(board.header, titleText(board.pinned, rainbowPhase));','setText(board.header, Component.empty());')
edit(p,'List<Display.BlockDisplay> backing = createBacking(level, display.position(), orientationYaw, 0, text, style);','List<Display.BlockDisplay> backing = List.of();')
edit(p,'board.avatar = createAvatar(board, player, avatarPng);','board.avatar = null;')
edit(p,'data.store("text", ComponentSerialization.CODEC, titleText(pinned, 0));','data.store("text", ComponentSerialization.CODEC, Component.empty());')
a='''new Transformation(new Vector3f((float) ((style.contentX() - 50) * 0.054 * style.scale() * style.width()),
                (float) ((50 - style.contentY()) * panelHeight(text, style) / 100), 0),
                new Quaternionf(), new Vector3f((float) (style.scale() * style.textScale()),
                (float) (style.scale() * style.textScale()), (float) (style.scale() * style.textScale())),
                new Quaternionf())'''
edit(p,a,'new Transformation(new Vector3f(), new Quaternionf(), new Vector3f(1, 1, 1), new Quaternionf())')
edit(p,'data.putFloat("height", (float) (3.0 * style.scale()));','data.putFloat("height", panelHeight(text, style) * 2);')
edit(p,'return (float) ((0.25f * (wrap(text, INNER_WIDTH - 2).size() + 4) + 0.1f) * style.scale() * style.height());','return (float) (1.62 * style.scale() * style.height());')
pth=r/p;s=pth.read_text(encoding='utf-8');start=s.index('        MutableComponent result',s.index('private static Component commentText'));end=s.index('\n    private static int rainbowColor',start)
s=s[:start]+'''        return Component.literal("tiktokmob:web-board:" + contentToken(author, text) + ":"
            + (5.4 * style.scale() * style.width()) + ":" + panelHeight(text, style));
    }

    static String contentToken(String author, String text) {
        try {
            byte[] hash = java.security.MessageDigest.getInstance("SHA-256")
                .digest((author.strip() + "\\n" + text.strip()).getBytes(java.nio.charset.StandardCharsets.UTF_8));
            return java.util.HexFormat.of().formatHex(hash).substring(0, 32);
        } catch (java.security.NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }
''' +s[end:];pth.write_text(s,encoding='utf-8')
edit('src/main/java/vn/deadchan/tiktokmob/TikTokClient.java','    static void initialize() {','    static void initialize() {\n        net.minecraftforge.client.event.EntityRenderersEvent.RegisterRenderers.BUS.addListener(event ->\n            event.registerEntityRenderer(net.minecraft.world.entity.EntityTypes.TEXT_DISPLAY, WebBoardRenderer::new));')
edit('src/main/java/vn/deadchan/tiktokmob/TikTokClient.java','            GiftAlertHud.tick();','            GiftAlertHud.tick();\n            WebBoardTexture.tick();')
edit('src/main/java/vn/deadchan/tiktokmob/TikTokClient.java','GiftAlertHud.clear(); PinnedCommentBoard.reset();','GiftAlertHud.clear(); WebBoardTexture.clear(); PinnedCommentBoard.reset();')
