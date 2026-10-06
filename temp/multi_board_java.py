from pathlib import Path
j=Path('TikTokMobForge/src/main/java/vn/deadchan/tiktokmob')
def edit(p,a,b):
 s=p.read_text(encoding='utf-8');assert a in s,(p,a[:90]);p.write_text(s.replace(a,b),encoding='utf-8')
p=j/'GiftNetwork.java'
edit(p,'.networkProtocolVersion(9)', '.networkProtocolVersion(10)')
edit(p,'record PinnedComment(String author, String text)', 'record PinnedComment(String author, String text, long revision)')
edit(p,'b.writeUtf(m.text, 400);', 'b.writeUtf(m.text, 400); b.writeLong(m.revision);')
edit(p,'new PinnedComment(b.readUtf(64), b.readUtf(400))', 'new PinnedComment(b.readUtf(64), b.readUtf(400), b.readLong())')
p=j/'PinnedCommentBoard.java'
edit(p,'private static long grabStartedAt, lastTapAt;', 'private static long grabStartedAt, lastTapAt, revision = -1;')
edit(p,'if (nextAuthor.equals(currentAuthor) && nextText.equals(currentText)) return;', 'if (message.revision() == revision && nextAuthor.equals(currentAuthor) && nextText.equals(currentText)) return;\n        reset();\n        revision = message.revision();')
edit(p,'        currentAuthor = "";\n        currentText = "";', '        revision = -1;\n        currentAuthor = "";\n        currentText = "";')
p=j/'TikTokClient.java'
edit(p,'if (mc.gui.screen() == null && PinnedCommentBoard.visible()) GiftNetwork.deleteBoard();','if (mc.gui.screen() == null && mc.player != null) GiftNetwork.deleteBoard();')
p=j/'TikTokMobMod.java';s=p.read_text(encoding='utf-8');start=s.index('        GiftNetwork.onBoardDelete = player -> {');end=s.index('        GiftNetwork.onSettingsPatch',start)
s=s[:start]+'''        GiftNetwork.onBoardDelete = player -> {
            if (RuntimeSettings.canEdit(player)) ServerPinnedCommentBoard.deleteAimed(player);
        };
'''+s[end:]
s=s.replace('ServerPinnedCommentBoard.tick(event.server(), pinnedAuthor, pinnedComment, pinnedAvatar, settings);','ServerPinnedCommentBoard.tick(event.server(), settings);')
s=s.replace('GiftNetwork.send(player, new GiftNetwork.PinnedComment(pinnedAuthor, pinnedComment));','ServerPinnedCommentBoard.sendState(player);')
s=s.replace('            String text = interaction.payload();','            String text = interaction.payload();\n            if (text.isBlank()) return; // Only an aimed X request deletes a world board.')
s=s.replace('            LOGGER.info("Pinned comment updated: avatar={} bytes", pinnedAvatar.length);\n            ServerPinnedCommentBoard.sendState(player);','            ServerPinnedCommentBoard.add(player.level().getServer(), pinnedAuthor, pinnedComment, pinnedAvatar, settings);\n            LOGGER.info("Pinned comment added: avatar={} bytes", pinnedAvatar.length);')
p.write_text(s,encoding='utf-8')
p=j/'ServerPinnedCommentBoard.java';s=p.read_text(encoding='utf-8');s=s.replace('/** One stationary-facing board per player. F freezes its world position. */','/** The newest board is movable; older boards remain saved world displays until aimed deletion. */');s=s.replace('    private static final int INNER_WIDTH', '    private static long nextRevision;\n    private static final String PART = "tiktokmob:board_part:";\n    private static final int INNER_WIDTH')
s=s.replace('        boolean pinned;', '        boolean pinned;\n        long revision;')
start=s.index('    static void tick(MinecraftServer server, String author, String text, byte[] avatarPng,');end=s.index('            GiftNetwork.BoardPosition setting =',start)
s=s[:start]+'''    static void add(MinecraftServer server, String author, String text, byte[] avatarPng,
                    TikTokMobMod.ModSettings settings) {
        if (text.isBlank()) return;
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            UUID id = player.getUUID();
            freeze(BOARDS.remove(id));
            GiftNetwork.BoardPosition previous = POSITIONS.getOrDefault(id, DEFAULT);
            GiftNetwork.BoardPosition position = new GiftNetwork.BoardPosition(previous.side(), previous.height(),
                previous.distance(), previous.scale(), false, false, false);
            POSITIONS.put(id, position);
            Board board = create(player, author, text, avatarPng, position, Style.from(settings, position.scale()));
            board.revision = ++nextRevision;
            BOARDS.put(id, board);
            sendState(player);
        }
    }

    static void sendState(ServerPlayer player) {
        Board board = BOARDS.get(player.getUUID());
        GiftNetwork.send(player, board == null ? new GiftNetwork.PinnedComment("", "", 0)
            : new GiftNetwork.PinnedComment(board.author, board.text, board.revision));
    }

    private static void freeze(Board board) {
        if (board == null) return;
        // Displays already have fixed world coordinates. Stop updating them and discard only the empty helper.
        board.header.discard();
        board.pinned = true;
        board.anchor = board.display.position();
    }

    static void tick(MinecraftServer server, TikTokMobMod.ModSettings settings) {
        var active = new HashSet<UUID>();
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            UUID id = player.getUUID();
            Board existing = BOARDS.get(id);
            if (existing == null) continue;
            if (existing.level != player.level()) { freeze(BOARDS.remove(id)); sendState(player); continue; }
            String author = existing.author, text = existing.text;
            byte[] avatarPng = existing.avatarPng;
            active.add(id);
'''+s[end:]
s=s.replace('                BOARDS.put(id, board);', '                board.revision = existing.revision;\n                BOARDS.put(id, board);')
s=s.replace('                discard(BOARDS.remove(id));','                freeze(BOARDS.remove(id));')
s=s.replace('        BOARDS.values().forEach(ServerPinnedCommentBoard::discard);','        // Keep saved display entities across logout/restart; they remain selectable by their marker.\n        BOARDS.values().forEach(ServerPinnedCommentBoard::freeze);')
# Delete using real display geometry; no client-provided id and no global clear.
anchor='    private static void moveBoard(Board board, Vec3 at) {'
s=s.replace(anchor,'''    static void deleteAimed(ServerPlayer player) {
        Vec3 eye = player.getEyePosition(), direction = player.getLookAngle();
        var obstruction = player.level().clip(new net.minecraft.world.level.ClipContext(eye,
            eye.add(direction.scale(64)), net.minecraft.world.level.ClipContext.Block.COLLIDER,
            net.minecraft.world.level.ClipContext.Fluid.NONE, player));
        double nearest = Math.min(64, eye.distanceTo(obstruction.getLocation()) + .02);
        Display.TextDisplay selected = null;
        for (Display.TextDisplay display : player.level().getEntitiesOfClass(Display.TextDisplay.class,
                player.getBoundingBox().inflate(105))) {
            String marker = display.getEntityData().get(textDataAccessor()).getString();
            String[] fields = marker.split(":", 6);
            if (!marker.startsWith("tiktokmob:web-board:") || fields.length < 5) continue;
            try {
                double hit = BoardRaycast.distance(eye, direction, display.position(), display.getYRot(),
                    display.getXRot(), Double.parseDouble(fields[3]), Double.parseDouble(fields[4]));
                if (hit >= 0 && hit <= nearest) { nearest = hit; selected = display; }
            } catch (NumberFormatException ignored) { }
        }
        if (selected == null) return;
        final Display.TextDisplay target = selected;
        BOARDS.entrySet().removeIf(entry -> {
            if (entry.getValue().display != target) return false;
            discard(entry.getValue());
            ServerPlayer owner = player.level().getServer().getPlayerList().getPlayer(entry.getKey());
            if (owner != null) GiftNetwork.send(owner, new GiftNetwork.PinnedComment("", "", 0));
            return true;
        });
        String part = PART + target.getUUID();
        for (var helper : player.level().getEntitiesOfClass(Display.class, target.getBoundingBox().inflate(80)))
            if (helper.entityTags().contains(part)) helper.discard();
        target.discard();
    }

'''+anchor)
s=s.replace('        List<Display.BlockDisplay> backing = List.of();','        header.addTag(PART + display.getUUID());\n        List<Display.BlockDisplay> backing = List.of();')
p.write_text(s,encoding='utf-8')
(j/'BoardRaycast.java').write_text('''package vn.deadchan.tiktokmob;

import net.minecraft.world.phys.Vec3;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/** Intersect the actual two-sided board rectangle, not TextDisplay's empty collision box. */
final class BoardRaycast {
    static double distance(Vec3 eye, Vec3 direction, Vec3 bottomCenter, float yaw, float pitch,
                           double width, double height) {
        if (!Double.isFinite(width) || !Double.isFinite(height) || width <= 0 || height <= 0) return -1;
        Quaternionf inverse = new Quaternionf().rotationYXZ((float)Math.toRadians(-yaw),
            (float)Math.toRadians(pitch), 0).conjugate();
        Vec3 offset = eye.subtract(bottomCenter);
        Vector3f localEye = inverse.transform(new Vector3f((float)offset.x, (float)offset.y, (float)offset.z));
        Vector3f localRay = inverse.transform(new Vector3f((float)direction.x, (float)direction.y, (float)direction.z));
        if (Math.abs(localRay.z) < 1e-6) return -1;
        double t = -localEye.z / localRay.z;
        double x = localEye.x + t * localRay.x, y = localEye.y + t * localRay.y;
        return t >= 0 && Math.abs(x) <= width / 2 && y >= 0 && y <= height ? t : -1;
    }
}
''',encoding='utf-8')
print('MULTI_BOARD_AND_AIMED_DELETE_UPDATED')
