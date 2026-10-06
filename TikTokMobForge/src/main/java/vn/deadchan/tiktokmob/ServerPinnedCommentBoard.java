package vn.deadchan.tiktokmob;

import com.mojang.logging.LogUtils;
import com.mojang.math.Transformation;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentSerialization;
import net.minecraft.network.chat.FontDescription;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Brightness;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.entity.Display;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.TagValueInput;
import net.minecraft.world.level.storage.TagValueOutput;
import net.minecraft.world.phys.Vec3;
import org.joml.Quaternionf;
import org.joml.Vector3f;

import javax.imageio.ImageIO;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Each board has its own owner, movement state, and stable control revision. */
final class ServerPinnedCommentBoard {
    private static long nextRevision;
    private static final String PART = "tiktokmob:board_part:";
    private static final int INNER_WIDTH = 28;
    private static final int AVATAR_PIXELS = 16;
    private static final int[] RAINBOW = {0xff4268, 0xffa442, 0xffe85a, 0x58ef79, 0x39dbf7, 0x8586ff, 0xec62ff};
    private static final FontDescription.Resource PIN_FONT = new FontDescription.Resource(
        Identifier.fromNamespaceAndPath("tiktokmob", "pin"));
    private static final FontDescription.Resource PIXEL_FONT = new FontDescription.Resource(
        Identifier.fromNamespaceAndPath("tiktokmob", "avatar_pixel"));

    private static final Map<Long, Board> BOARDS = new HashMap<>();
    private static final Map<UUID, Long> SELECTED = new HashMap<>();

    private static String missionId(String text) {
        if (!text.startsWith("mission:")) return "";
        String[] parts = text.split(":", 6);
        return parts.length >= 4 ? parts[1] : "";
    }

    static void missions(ServerPlayer player, List<Missions.View> views, TikTokMobMod.ModSettings settings) {
        var active = views.stream().filter(view -> view.mode().equals("3d")).map(Missions.View::id).collect(java.util.stream.Collectors.toSet());
        Set<String> seen = new HashSet<>();
        for (Board board : new ArrayList<>(BOARDS.values())) {
            String id = missionId(board.text);
            if (!id.isEmpty() && player.getUUID().equals(board.owner)
                && (!active.contains(id) || board.level != player.level() || !seen.add(id))) {
                discard(board); BOARDS.remove(board.revision);
                if (java.util.Objects.equals(SELECTED.get(player.getUUID()), board.revision)) SELECTED.remove(player.getUUID());
            }
        }
        for (Missions.View view : views) {
            if (!view.mode().equals("3d")) continue;
            String text = "mission:" + view.id() + ":" + view.current() + ":" + view.target()
                + ":" + view.kind() + ":" + view.milestones();
            Board board = BOARDS.values().stream().filter(item -> player.getUUID().equals(item.owner)
                && view.id().equals(missionId(item.text))).findFirst().orElse(null);
            if (board == null) {
                board = create(player, view.title(), text, new byte[0], DEFAULT, Style.from(settings, 1));
                board.owner = player.getUUID(); board.setting = DEFAULT; board.revision = ++nextRevision;
                // Spread new mission boards so each can be aimed and moved independently.
                board.orbitAngle += views.indexOf(view) * .7;
                BOARDS.put(board.revision, board); persist(board);
                SELECTED.put(player.getUUID(), board.revision); sendState(player);
            } else if (!board.text.equals(text) || !board.author.equals(view.title())) {
                board.text = text; board.author = view.title();
                setTextData(board.display.getEntityData(), commentText(board.author, board.text, board.style));
            }
        }
    }
    private static TikTokMobMod.ModSettings currentSettings = new TikTokMobMod.ModSettings();
    private static final String STATE_TAG = "tiktokmob:board_state:";
    private record SavedBoard(UUID owner, GiftNetwork.BoardPosition position) {}
    private static final GiftNetwork.BoardPosition DEFAULT = new GiftNetwork.BoardPosition(0, 0.15, 3, 1, false, false, false);

    private record Avatar(Display.TextDisplay display) {}
    private record Style(String background, String border, String authorColor, String commentColor,
                         double scale, double textScale, double avatarScale, double radius,
                         double avatarX, double avatarY, double contentX, double contentY,
                         double width, double height, double authorX, double authorY) {
        static Style from(TikTokMobMod.ModSettings settings, double zoom) {
            return new Style(settings.pinned_board_background, settings.pinned_board_border,
                settings.pinned_board_author_color, settings.pinned_board_comment_color,
                settings.pinned_board_scale * zoom, settings.pinned_board_text_scale,
                settings.pinned_board_avatar_scale, settings.pinned_board_corner_radius,
                settings.pinned_board_avatar_x, settings.pinned_board_avatar_y,
                settings.pinned_board_content_x, settings.pinned_board_content_y,
                settings.pinned_board_width, settings.pinned_board_height,
                settings.pinned_board_author_x, settings.pinned_board_author_y);
        }
    }

    private static final class Board {
        final ServerLevel level;
        final Display.TextDisplay display;
        final Display.TextDisplay header;
        List<Display.BlockDisplay> backing;
        String author, text;
        boolean pinned;
        long revision;
        UUID owner;
        GiftNetwork.BoardPosition setting = DEFAULT;
        int rainbowPhase = -1;
        Vec3 anchor;
        Vec3 relativeOffset;
        float orientationYaw, orientationPitch;
        double orbitAngle;
        byte[] avatarPng;
        Avatar avatar;
        final Style style;

        Board(ServerLevel level, Display.TextDisplay display, Display.TextDisplay header,
              List<Display.BlockDisplay> backing,
              String author, String text,
              float orientationYaw, byte[] avatarPng, Style style) {
            this.level = level;
            this.display = display;
            this.header = header;
            this.backing = backing;
            this.author = author;
            this.text = text;
            this.orientationYaw = orientationYaw;
            this.orbitAngle = Math.toRadians(orientationYaw);
            this.avatarPng = avatarPng;
            this.style = style;
        }
    }

    static void position(ServerPlayer player, GiftNetwork.BoardMove message) {
        Board board = BOARDS.get(message.revision());
        if (board == null || !player.getUUID().equals(board.owner) || board.level != player.level()) return;
        GiftNetwork.BoardPosition packet = message.position();
        if (!Double.isFinite(packet.side()) || !Double.isFinite(packet.height())
            || !Double.isFinite(packet.distance()) || !Double.isFinite(packet.scale())
            || packet.distance() < 0 || packet.scale() <= 0
            || !Float.isFinite((float) packet.scale()) || (float) packet.scale() <= 0) return;
        GiftNetwork.BoardPosition previous = board.setting;
        GiftNetwork.BoardPosition current = new GiftNetwork.BoardPosition(
            clamp(packet.side(), -12, 12), clamp(packet.height(), -8, 8),
            packet.distance(), packet.scale(), packet.grabbing() && !packet.pinned(),
            packet.pinned(), packet.paused());
        board.setting = current;
        persist(board);
        if (board != null) {
            double delta = current.distance() - previous.distance();
            if (delta != 0 && (current.pinned() || current.paused())) {
                Vec3 center = board.display.position().add(0, panelHeight(board.text, board.style) / 2, 0);
                Vec3 direction = center.subtract(player.getEyePosition()).normalize();
                Vec3 at = board.display.position().add(direction.scale(delta));
                moveBoard(board, at);
                if (current.pinned()) board.anchor = at;
                if (current.paused()) board.relativeOffset = at.subtract(player.position());
            }
            if (!previous.pinned() && current.pinned())
                board.anchor = board.display.position();
            if ((!previous.paused() && current.paused() && !current.grabbing())
                || previous.grabbing() && !current.grabbing() && current.paused())
                board.relativeOffset = board.display.position().subtract(player.position());
        }
    }

    static void add(MinecraftServer server, String author, String text, byte[] avatarPng,
                    TikTokMobMod.ModSettings settings) {
        if (text.isBlank()) return;
        currentSettings = settings;
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            Board selected = BOARDS.get(SELECTED.get(player.getUUID()));
            if (selected != null && selected.setting.grabbing()) {
                var old = selected.setting;
                selected.setting = new GiftNetwork.BoardPosition(old.side(), old.height(), old.distance(), old.scale(), false, old.pinned(), true);
                selected.relativeOffset = selected.display.position().subtract(player.position());
                persist(selected);
            }
            GiftNetwork.BoardPosition previous = selected == null ? DEFAULT : selected.setting;
            GiftNetwork.BoardPosition position = new GiftNetwork.BoardPosition(previous.side(), previous.height(),
                previous.distance(), previous.scale(), false, false, false);
            Board board = create(player, author, text, avatarPng, position, Style.from(settings, position.scale()));
            board.owner = player.getUUID(); board.setting = position; board.revision = ++nextRevision;
            BOARDS.put(board.revision, board);
            SELECTED.put(player.getUUID(), board.revision);
            persist(board);
            sendState(player);
        }
    }

    static void sendState(ServerPlayer player) { sendState(player, false); }
    private static void sendState(ServerPlayer player, boolean selectionReply) {
        Board board = BOARDS.get(SELECTED.get(player.getUUID()));
        GiftNetwork.send(player, board == null ? new GiftNetwork.PinnedComment("", "", 0, DEFAULT, selectionReply)
            : new GiftNetwork.PinnedComment(board.author, board.text, board.revision, board.setting, selectionReply));
    }

    static void selectAimed(ServerPlayer player) {
        Display.TextDisplay display = aimed(player);
        if (display != null) {
            Board board = BOARDS.values().stream().filter(item -> item.display == display).findFirst().orElse(null);
            if (board == null) board = restore(player, display);
            if (board != null && player.getUUID().equals(board.owner)) SELECTED.put(player.getUUID(), board.revision);
        }
        sendState(player, true);
    }

    private static void persist(Board board) {
        board.display.entityTags().removeIf(tag -> tag.startsWith(STATE_TAG));
        String json = new com.google.gson.Gson().toJson(new SavedBoard(board.owner, board.setting));
        board.display.addTag(STATE_TAG + java.util.Base64.getEncoder().encodeToString(json.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
    }

    private static Board restore(ServerPlayer player, Display.TextDisplay display) {
        String[] fields = display.getEntityData().get(textDataAccessor()).getString().split(":", 6);
        if (fields.length != 6) return null;
        BoardCaption caption = BoardCaption.decode(fields[5]);
        if (caption == null) return null;
        try {
            SavedBoard saved = null;
            for (String tag : display.entityTags()) if (tag.startsWith(STATE_TAG)) {
                saved = new com.google.gson.Gson().fromJson(new String(java.util.Base64.getDecoder().decode(tag.substring(STATE_TAG.length())),
                    java.nio.charset.StandardCharsets.UTF_8), SavedBoard.class);
            }
            if (saved != null && !player.getUUID().equals(saved.owner())) return null;
            double scale = caption.boardScale();
            Style style = new Style(currentSettings.pinned_board_background, currentSettings.pinned_board_border,
                caption.authorColor(), caption.commentColor(), scale, caption.scale() / scale, caption.avatarScale(),
                currentSettings.pinned_board_corner_radius, caption.avatarX(), caption.avatarY(), caption.x(), caption.y(),
                Double.parseDouble(fields[3]) / (5.4 * scale), Double.parseDouble(fields[4]) / (1.62 * scale), caption.authorX(), caption.authorY());
            GiftNetwork.BoardPosition position = saved == null ? new GiftNetwork.BoardPosition(0, .15,
                display.position().distanceTo(player.getEyePosition()), scale / currentSettings.pinned_board_scale, false, false, false) : saved.position();
            if (position == null) return null;
            // Never resume a stale mouse drag after reconnecting.
            position = new GiftNetwork.BoardPosition(position.side(), position.height(), position.distance(), position.scale(), false, position.pinned(), position.paused());
            var header = createHeader(player.level(), display.position(), display.getYRot() - 180, caption.text(), style, position.pinned());
            header.addTag(PART + display.getUUID());
            Board board = new Board(player.level(), display, header, List.of(), caption.author(), caption.text(), display.getYRot() - 180, new byte[0], style);
            board.owner = player.getUUID(); board.setting = position; board.revision = ++nextRevision;
            board.orientationPitch = display.getXRot(); board.pinned = position.pinned();
            board.anchor = position.pinned() ? display.position() : null;
            board.relativeOffset = display.position().subtract(player.position());
            board.orbitAngle = Math.atan2(-board.relativeOffset.x, board.relativeOffset.z);
            BOARDS.put(board.revision, board); persist(board);
            return board;
        } catch (RuntimeException invalid) { return null; }
    }

    static void tick(MinecraftServer server, TikTokMobMod.ModSettings settings) {
        currentSettings = settings;
        // Restore persisted boards before the mission updater can create a replacement.
        if (server.getTickCount() % 10 == 0) for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            for (Display.TextDisplay display : player.level().getEntitiesOfClass(Display.TextDisplay.class, player.getBoundingBox().inflate(105))) {
                if (!display.getEntityData().get(textDataAccessor()).getString().startsWith("tiktokmob:web-board:")) continue;
                if (BOARDS.values().stream().noneMatch(board -> board.display == display)) restore(player, display);
            }
        }
        for (Board existing : new ArrayList<>(BOARDS.values())) {
            long id = existing.revision;
            if (existing.display.isRemoved()) { existing.header.discard(); BOARDS.remove(id); continue; }
            ServerPlayer player = server.getPlayerList().getPlayer(existing.owner);
            if (player == null || existing.level != player.level()) {
                if (existing.setting.grabbing()) {
                    var old = existing.setting;
                    existing.setting = new GiftNetwork.BoardPosition(old.side(), old.height(), old.distance(), old.scale(), false, old.pinned(), true);
                    persist(existing);
                }
                continue;
            }
            String author = existing.author, text = existing.text;
            byte[] avatarPng = existing.avatarPng;
            GiftNetwork.BoardPosition setting = existing.setting;
            Style style = Style.from(settings, setting.scale());
            Board board = BOARDS.get(id);
            if (board == null || board.display.isRemoved()
                || board.level != player.level() && !setting.pinned()
                || !board.style.equals(style)
                || wrap(board.text, INNER_WIDTH - 2).size() != wrap(text, INNER_WIDTH - 2).size()) {
                Board old = board;
                if (old != null && old.level != player.level()) old = null;
                Vec3 previousPosition = old == null ? null : old.display.position();
                float previousYaw = old == null ? player.getYRot() : old.orientationYaw;
                float previousPitch = old == null ? 0 : old.orientationPitch;
                double previousAngle = old == null ? Math.toRadians(player.getYRot()) : old.orbitAngle;
                Vec3 previousAnchor = old == null ? null : old.anchor;
                Vec3 previousOffset = old == null ? null : old.relativeOffset;
                if (old != null) {
                    float difference = (panelHeight(old.text, old.style) - panelHeight(text, style)) / 2;
                    Vector3f up = localUp(previousYaw, previousPitch).mul(difference);
                    previousPosition = previousPosition.add(up.x, up.y, up.z);
                    if (previousAnchor != null) previousAnchor = previousPosition;
                    if (previousOffset != null) previousOffset = previousPosition.subtract(player.position());
                }
                if (board != null) discard(board);
                board = create(player, author, text, avatarPng, setting, style);
                if (previousPosition != null) {
                    board.orbitAngle = previousAngle;
                    board.anchor = previousAnchor;
                    board.relativeOffset = previousOffset;
                    orient(board, previousYaw, previousPitch);
                    moveBoard(board, previousPosition);
                }
                board.revision = existing.revision;
                board.owner = existing.owner; board.setting = existing.setting;
                persist(board);
                BOARDS.put(id, board);
                LogUtils.getLogger().info("Pinned comment board spawned for {}: entity={}",
                    player.getScoreboardName(), board.display.getId());
            }
            if (!Arrays.equals(board.avatarPng, avatarPng)) {
                if (board.avatar != null) board.avatar.display().discard();
                board.avatarPng = avatarPng;
                board.avatar = null;
            }
            int rainbowPhase = server.getTickCount() % (RAINBOW.length * 8);
            if (!board.author.equals(author) || !board.text.equals(text)
                || board.pinned != setting.pinned() || board.rainbowPhase != rainbowPhase) {
                board.author = author;
                board.text = text;
                board.pinned = setting.pinned();
                board.rainbowPhase = rainbowPhase;
                setTextData(board.display.getEntityData(), commentText(author, text, board.style));
            }
            if (setting.pinned()) {
                if (board.anchor == null) board.anchor = board.display.position();
                if (!board.display.position().equals(board.anchor)) board.display.setPos(board.anchor);
            } else if (setting.grabbing()) {
                board.anchor = null;
                board.relativeOffset = null;
                Vec3 at = aimedPosition(player, setting, board.text, board.style);
                if (!board.display.position().equals(at)) board.display.setPos(at);
                orient(board, player.getYRot(), -player.getXRot());
                Vec3 delta = at.subtract(player.position());
                board.orbitAngle = Math.atan2(-delta.x, delta.z);
            } else if (setting.paused()) {
                board.anchor = null;
                if (board.relativeOffset == null)
                    board.relativeOffset = board.display.position().subtract(player.position());
                Vec3 at = player.position().add(board.relativeOffset);
                if (!board.display.position().equals(at)) board.display.setPos(at);
            } else {
                board.anchor = null;
                board.relativeOffset = null;
                board.orbitAngle = (board.orbitAngle + 0.004 * settings.pinned_board_rotation_speed) % (Math.PI * 2);
                Vec3 at = orbitPosition(player, setting, board.orbitAngle, board.text, board.style);
                if (!board.display.position().equals(at)) board.display.setPos(at);
                orient(board, (float) Math.toDegrees(board.orbitAngle), 0);
            }
            moveBoard(board, board.display.position());
        }
    }

    static void clear() {
        for (Board board : BOARDS.values()) { persist(board); board.header.discard(); }
        BOARDS.clear(); SELECTED.clear();
    }

    private static Display.TextDisplay aimed(ServerPlayer player) {
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
        return selected;
    }

    static void deleteAimed(ServerPlayer player) {
        final Display.TextDisplay target = aimed(player);
        if (target == null) return;
        BOARDS.entrySet().removeIf(entry -> {
            if (entry.getValue().display != target) return false;
            if (!player.getUUID().equals(entry.getValue().owner)) return false;
            discard(entry.getValue());
            ServerPlayer owner = player.level().getServer().getPlayerList().getPlayer(entry.getValue().owner);
            if (owner != null && java.util.Objects.equals(SELECTED.get(owner.getUUID()), entry.getKey())) {
                SELECTED.remove(owner.getUUID());
                GiftNetwork.send(owner, new GiftNetwork.PinnedComment("", "", 0, DEFAULT, false));
            }
            return true;
        });
        if (!target.isRemoved()) return;
        String part = PART + target.getUUID();
        for (var helper : player.level().getEntitiesOfClass(Display.class, target.getBoundingBox().inflate(80)))
            if (helper.entityTags().contains(part)) helper.discard();
        target.discard();
    }

    private static void moveBoard(Board board, Vec3 at) {
        if (!board.display.position().equals(at)) board.display.setPos(at);
        Vec3 headerAt = headerPosition(board);
        if (!board.header.position().equals(headerAt)) board.header.setPos(headerAt);
        for (Display.BlockDisplay piece : board.backing)
            if (!piece.position().equals(at)) piece.setPos(at);
        if (board.avatar != null) {
            Vec3 avatarAt = avatarPosition(board);
            if (!board.avatar.display().position().equals(avatarAt)) board.avatar.display().setPos(avatarAt);
        }
    }

    private static Board create(ServerPlayer player, String author, String text,
                                byte[] avatarPng, GiftNetwork.BoardPosition setting, Style style) {
        ServerLevel level = player.level();
        Vec3 at = followingPosition(player, setting).add(0, -panelHeight(text, style) / 2, 0);
        Display.TextDisplay display = new Display.TextDisplay(EntityTypes.TEXT_DISPLAY, level);
        var data = TagValueOutput.createWithContext(ProblemReporter.DISCARDING, level.registryAccess());
        display.saveWithoutId(data);
        data.putString("billboard", "fixed");
        data.putString("alignment", "left");
        data.store("brightness", Brightness.CODEC, Brightness.FULL_BRIGHT);
        // Server position packets arrive at 20 Hz. Interpolate between them on each render frame.
        data.putInt("teleport_duration", 2);
        data.putInt("background", 0);
        data.putInt("line_width", 300);
        data.putFloat("width", (float) (5.4 * style.scale() * style.width()));
        data.putFloat("height", panelHeight(text, style) * 2);
        data.store("transformation", Transformation.EXTENDED_CODEC,
            new Transformation(new Vector3f(), new Quaternionf(), new Vector3f(1, 1, 1), new Quaternionf()));
        data.putBoolean("shadow", true);
        data.putBoolean("see_through", false);
        data.store("text", ComponentSerialization.CODEC, commentText(author, text, style));
        display.load(TagValueInput.create(ProblemReporter.DISCARDING, level.registryAccess(), data.buildResult()));
        display.setNoGravity(true);
        float orientationYaw = player.getYRot();
        display.setYRot(orientationYaw + 180.0f);
        display.setXRot(0);
        display.setPos(at);
        if (!level.addFreshEntity(display)) throw new IllegalStateException("Could not spawn pinned comment board");
        Display.TextDisplay header = createHeader(level, at, orientationYaw, text, style, setting.pinned());
        header.addTag(PART + display.getUUID());
        List<Display.BlockDisplay> backing = List.of();
        Board board = new Board(level, display, header, backing, author, text, orientationYaw, avatarPng, style);
        board.pinned = setting.pinned();
        if (board.pinned) board.anchor = at;
        board.avatar = null;
        return board;
    }

    private static void discard(Board board) {
        board.display.discard();
        board.header.discard();
        board.backing.forEach(Display.BlockDisplay::discard);
        if (board.avatar != null) board.avatar.display().discard();
    }

    private static Display.TextDisplay createHeader(ServerLevel level, Vec3 at, float yaw,
                                                    String text, Style style, boolean pinned) {
        Display.TextDisplay header = new Display.TextDisplay(EntityTypes.TEXT_DISPLAY, level);
        var data = TagValueOutput.createWithContext(ProblemReporter.DISCARDING, level.registryAccess());
        header.saveWithoutId(data);
        data.putString("billboard", "fixed");
        data.putString("alignment", "center");
        data.putInt("teleport_duration", 2);
        data.putInt("background", 0);
        data.putInt("line_width", 300);
        data.putBoolean("shadow", true);
        data.store("brightness", Brightness.CODEC, Brightness.FULL_BRIGHT);
        data.store("text", ComponentSerialization.CODEC, Component.empty());
        float titleScale = (float) (style.scale() * style.textScale());
        data.store("transformation", Transformation.EXTENDED_CODEC,
            new Transformation(new Vector3f(), new Quaternionf(),
                new Vector3f(titleScale, titleScale, titleScale), new Quaternionf()));
        header.load(TagValueInput.create(ProblemReporter.DISCARDING, level.registryAccess(), data.buildResult()));
        header.setNoGravity(true);
        header.setYRot(yaw + 180);
        header.setPos(at.add(0, panelHeight(text, style) - 0.35 * style.scale(), 0));
        if (!level.addFreshEntity(header)) throw new IllegalStateException("Could not spawn pinned comment title");
        return header;
    }

    private static Vec3 headerPosition(Board board) {
        double height = panelHeight(board.text, board.style) - 0.35 * board.style.scale();
        Vector3f up = localUp(board.orientationYaw, board.orientationPitch);
        return board.display.position().add(up.x * height, up.y * height, up.z * height);
    }

    private static List<Display.BlockDisplay> createBacking(ServerLevel level, Vec3 at, float yaw,
                                                            float pitch, String text, Style style) {
        float size = (float) style.scale();
        float width = (float) (5.4 * size * style.width());
        float height = panelHeight(text, style);
        float radius = (float) style.radius() * size, edge = 0.045f * size;
        List<Display.BlockDisplay> pieces = new ArrayList<>(6);
        BlockState highlight = Blocks.CONCRETE.pick(DyeColor.valueOf(style.border().toUpperCase(java.util.Locale.ROOT))).defaultBlockState();
        BlockState black = Blocks.CONCRETE.pick(DyeColor.valueOf(style.background().toUpperCase(java.util.Locale.ROOT))).defaultBlockState();
        // Three outer pieces and three inner pieces make a compact pixel-rounded panel.
        if (radius < edge) {
            pieces.add(blockRect(level, at, yaw, pitch, highlight, -width / 2, 0,
                width, height, -0.085f));
            pieces.add(blockRect(level, at, yaw, pitch, black, -width / 2 + edge, edge,
                width - edge * 2, height - edge * 2, -0.055f));
        } else {
            pieces.add(blockRect(level, at, yaw, pitch, highlight, -width / 2 + radius, 0,
                width - radius * 2, height, -0.085f));
            pieces.add(blockRect(level, at, yaw, pitch, highlight, -width / 2, radius,
                radius, height - radius * 2, -0.085f));
            pieces.add(blockRect(level, at, yaw, pitch, highlight, width / 2 - radius, radius,
                radius, height - radius * 2, -0.085f));
            pieces.add(blockRect(level, at, yaw, pitch, black, -width / 2 + radius, edge,
                width - radius * 2, height - edge * 2, -0.055f));
            pieces.add(blockRect(level, at, yaw, pitch, black, -width / 2 + edge, radius + edge,
                radius - edge, height - (radius + edge) * 2, -0.055f));
            pieces.add(blockRect(level, at, yaw, pitch, black, width / 2 - radius, radius + edge,
                radius - edge, height - (radius + edge) * 2, -0.055f));
        }
        return pieces;
    }

    private static Display.BlockDisplay blockRect(ServerLevel level, Vec3 at, float yaw, float pitch,
                                                   BlockState state, float x, float y, float width,
                                                   float height, float z) {
        Display.BlockDisplay backing = new Display.BlockDisplay(EntityTypes.BLOCK_DISPLAY, level);
        var tag = TagValueOutput.createWithContext(ProblemReporter.DISCARDING, level.registryAccess());
        backing.saveWithoutId(tag);
        tag.store("block_state", BlockState.CODEC, state);
        tag.store("brightness", Brightness.CODEC, Brightness.FULL_BRIGHT);
        tag.putString("billboard", "fixed");
        tag.putInt("teleport_duration", 2);
        tag.putFloat("width", width);
        tag.putFloat("height", height);
        tag.store("transformation", Transformation.EXTENDED_CODEC,
            new Transformation(new Vector3f(x, y, z), new Quaternionf(),
                new Vector3f(width, height, 0.04f), new Quaternionf()));
        backing.load(TagValueInput.create(ProblemReporter.DISCARDING, level.registryAccess(), tag.buildResult()));
        backing.setNoGravity(true);
        backing.setYRot(yaw + 180);
        backing.setXRot(pitch);
        backing.setPos(at);
        if (!level.addFreshEntity(backing)) throw new IllegalStateException("Could not spawn pinned comment backing");
        return backing;
    }

    private static Vec3 avatarPosition(Board board) {
        double yaw = Math.toRadians(board.orientationYaw);
        Vec3 right = new Vec3(Math.cos(yaw), 0, Math.sin(yaw));
        double pitch = Math.toRadians(board.orientationPitch);
        Vec3 front = new Vec3(Math.sin(yaw) * Math.cos(pitch), -Math.sin(pitch),
            -Math.cos(yaw) * Math.cos(pitch));
        double scale = board.style.scale();
        double width = 5.4 * scale * board.style.width();
        double avatarHeight = 0.72 * scale * board.style.avatarScale();
        double localY = panelHeight(board.text, board.style) * (1 - board.style.avatarY() / 100)
            - avatarHeight / 2;
        Vector3f up = localUp(board.orientationYaw, board.orientationPitch);
        return board.display.position().add(right.scale((50 - board.style.avatarX()) / 100 * width))
            .add(front.scale(0.12 * scale)).add(up.x * localY, up.y * localY, up.z * localY);
    }

    private static Avatar createAvatar(Board board, ServerPlayer player, byte[] png) {
        if (png.length == 0 || png.length > 65_536) return null;
        try {
            var image = ImageIO.read(new ByteArrayInputStream(png));
            if (image == null || image.getWidth() < 1 || image.getHeight() < 1
                || image.getWidth() > 128 || image.getHeight() > 128) return null;
            Display.TextDisplay display = new Display.TextDisplay(EntityTypes.TEXT_DISPLAY, board.level);
            var tag = TagValueOutput.createWithContext(ProblemReporter.DISCARDING, board.level.registryAccess());
            display.saveWithoutId(tag);
            tag.putString("billboard", "fixed");
            tag.putString("alignment", "left");
            tag.putInt("teleport_duration", 2);
            tag.putFloat("width", 1);
            tag.putFloat("height", 1);
            tag.putInt("line_width", 200);
            tag.putInt("background", 0);
            tag.putBoolean("shadow", false);
            tag.store("brightness", Brightness.CODEC, Brightness.FULL_BRIGHT);
            tag.store("text", ComponentSerialization.CODEC, avatarText(image));
            tag.store("transformation", Transformation.EXTENDED_CODEC,
                new Transformation(new Vector3f(), new Quaternionf(),
                new Vector3f((float) (0.18 * board.style.scale() * board.style.avatarScale()),
                    (float) (0.18 * board.style.scale() * board.style.avatarScale()),
                    (float) (0.18 * board.style.scale() * board.style.avatarScale())), new Quaternionf()));
            display.load(TagValueInput.create(ProblemReporter.DISCARDING,
                board.level.registryAccess(), tag.buildResult()));
            display.setNoGravity(true);
            display.setYRot(board.orientationYaw + 180);
            display.setXRot(board.orientationPitch);
            display.setPos(avatarPosition(board));
            if (!board.level.addFreshEntity(display)) return null;
            LogUtils.getLogger().info("Pinned avatar rendered for {}: entity={}",
                player.getScoreboardName(), display.getId());
            return new Avatar(display);
        } catch (IOException | RuntimeException error) {
            LogUtils.getLogger().warn("Could not show pinned comment avatar for {}", player.getScoreboardName(), error);
            return null;
        }
    }

    private static Component avatarText(java.awt.image.BufferedImage image) {
        MutableComponent result = Component.empty();
        for (int y = 0; y < AVATAR_PIXELS; y++) {
            for (int x = 0; x < AVATAR_PIXELS; x++) {
                int argb = image.getRGB((x * 2 + 1) * image.getWidth() / (AVATAR_PIXELS * 2),
                    (y * 2 + 1) * image.getHeight() / (AVATAR_PIXELS * 2));
                boolean transparent = (argb >>> 24) < 80;
                int color = argb & 0xffffff;
                result.append(Component.literal(transparent ? "\ue002" : "\ue001")
                    .withStyle(style -> style.withFont(PIXEL_FONT).withColor(color)));
            }
            if (y < AVATAR_PIXELS - 1) result.append(Component.literal("\n"));
        }
        return result;
    }

    private static Vec3 followingPosition(ServerPlayer player, GiftNetwork.BoardPosition setting) {
        Vec3 forward;
        if (setting.grabbing()) {
            forward = player.getLookAngle();
        } else {
            double yaw = Math.toRadians(player.getYRot());
            forward = new Vec3(-Math.sin(yaw), 0, Math.cos(yaw));
        }
        Vec3 right = new Vec3(-forward.z, 0, forward.x);
        return player.position().add(0, player.getEyeHeight() + setting.height(), 0)
            .add(forward.scale(setting.distance())).add(right.scale(setting.side()));
    }

    private static float panelHeight(String text, Style style) {
        // WebView captures mission cards at 500x94; preserve that exact aspect ratio in world space.
        if (text.startsWith("mission:")) return (float) (5.4 * style.scale() * style.width() * 94.0 / 500.0);
        return (float) (1.62 * style.scale() * style.height());
    }

    private static Vec3 aimedPosition(ServerPlayer player, GiftNetwork.BoardPosition setting,
                                      String text, Style style) {
        Vec3 target = followingPosition(player, setting);
        Vector3f up = localUp(player.getYRot(), -player.getXRot());
        double halfHeight = panelHeight(text, style) / 2.0;
        return target.add(-up.x * halfHeight, -up.y * halfHeight, -up.z * halfHeight);
    }

    private static Vector3f localUp(float yaw, float pitch) {
        Vector3f up = new Vector3f(0, 1, 0);
        new Quaternionf().rotationYXZ((float) Math.toRadians(-yaw - 180),
            (float) Math.toRadians(pitch), 0).transform(up);
        return up;
    }

    private static Vec3 orbitPosition(ServerPlayer player, GiftNetwork.BoardPosition setting,
                                      double angle, String text, Style style) {
        return player.position().add(0, player.getEyeHeight() + setting.height(), 0)
            .add(-Math.sin(angle) * setting.distance(), -panelHeight(text, style) / 2.0,
                Math.cos(angle) * setting.distance());
    }

    private static void orient(Board board, float yaw, float pitch) {
        if (board.orientationYaw == yaw && board.orientationPitch == pitch) return;
        board.orientationYaw = yaw;
        board.orientationPitch = pitch;
        board.display.setYRot(yaw + 180);
        board.display.setXRot(pitch);
        board.header.setYRot(yaw + 180);
        board.header.setXRot(pitch);
        for (Display.BlockDisplay piece : board.backing) {
            piece.setYRot(yaw + 180);
            piece.setXRot(pitch);
        }
        if (board.avatar != null) {
            board.avatar.display().setYRot(yaw + 180);
            board.avatar.display().setXRot(pitch);
        }
    }

    /** Resolve the schema, not the non-default values of a particular display.
     * An empty header has no non-default COMPONENT entry at all. */
    private static final class TextData {
        static final EntityDataAccessor<Component> ACCESSOR = resolve();

        @SuppressWarnings("unchecked")
        private static EntityDataAccessor<Component> resolve() {
            for (var field : Display.TextDisplay.class.getDeclaredFields()) {
                if (!java.lang.reflect.Modifier.isStatic(field.getModifiers())
                    || field.getType() != EntityDataAccessor.class) continue;
                try {
                    field.setAccessible(true);
                    var accessor = (EntityDataAccessor<?>) field.get(null);
                    if (accessor.serializer() == EntityDataSerializers.COMPONENT)
                        return (EntityDataAccessor<Component>) accessor;
                } catch (ReflectiveOperationException error) {
                    throw new IllegalStateException("Cannot access TextDisplay text schema", error);
                }
            }
            throw new IllegalStateException("TextDisplay has no COMPONENT accessor");
        }
    }

    static EntityDataAccessor<Component> textDataAccessor() { return TextData.ACCESSOR; }

    static void setTextData(net.minecraft.network.syncher.SynchedEntityData data, Component text) {
        data.set(TextData.ACCESSOR, text);
    }

    private static Component titleText(boolean pinned, int rainbowPhase) {
        MutableComponent result = Component.empty().withStyle(format -> format.withFont(
            new FontDescription.Resource(Identifier.withDefaultNamespace("uniform"))));
        String title = "BÌNH LUẬN GHIM";
        int left = (INNER_WIDTH - title.length()) / 2;
        int right = INNER_WIDTH - left - title.length();
        result.append(Component.literal(" ".repeat(left)));
        for (int i = 0; i < title.length(); i++) {
            int color = rainbowColor(i * 8 + rainbowPhase);
            result.append(Component.literal(title.substring(i, i + 1))
                .withStyle(format -> format.withColor(color).withBold(true)));
        }
        result.append(Component.literal(" ".repeat(right - (pinned ? 1 : 0))));
        if (pinned) result.append(Component.literal("\ue000").withStyle(format -> format.withFont(PIN_FONT)));
        return result;
    }

    private static Component commentText(String author, String text, Style style) {
        return Component.literal("tiktokmob:web-board:" + contentToken(author, text) + ":"
            + (5.4 * style.scale() * style.width()) + ":" + panelHeight(text, style) + ":"
            + BoardCaption.encode(new BoardCaption(author, text, style.authorColor(), style.commentColor(),
                style.scale() * style.textScale(), style.contentX(), style.contentY(), style.authorX(), style.authorY(),
                style.avatarX(), style.avatarY(), style.avatarScale(), style.scale())));
    }

    static String contentToken(String author, String text) {
        try {
            byte[] hash = java.security.MessageDigest.getInstance("SHA-256")
                .digest((author.strip() + "\n" + text.strip()).getBytes(java.nio.charset.StandardCharsets.UTF_8));
            return java.util.HexFormat.of().formatHex(hash).substring(0, 32);
        } catch (java.security.NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }

    private static int rainbowColor(int phase) {
        int from = RAINBOW[(phase / 8) % RAINBOW.length];
        int to = RAINBOW[(phase / 8 + 1) % RAINBOW.length];
        int step = phase % 8;
        int red = (((from >>> 16) & 255) * (8 - step) + ((to >>> 16) & 255) * step) / 8;
        int green = (((from >>> 8) & 255) * (8 - step) + ((to >>> 8) & 255) * step) / 8;
        int blue = ((from & 255) * (8 - step) + (to & 255) * step) / 8;
        return red << 16 | green << 8 | blue;
    }

    private static String abbreviate(String value, int width) {
        if (value.codePointCount(0, value.length()) <= width) return value;
        return value.substring(0, value.offsetByCodePoints(0, width - 3)) + "...";
    }

    private static List<String> wrap(String value, int width) {
        List<String> lines = new ArrayList<>();
        StringBuilder line = new StringBuilder();
        for (String token : value.strip().split("\\s+")) {
            while (token.codePointCount(0, token.length()) > width) {
                if (!line.isEmpty()) {
                    lines.add(line.toString());
                    line.setLength(0);
                }
                int end = token.offsetByCodePoints(0, width);
                lines.add(token.substring(0, end));
                token = token.substring(end);
            }
            if (token.isEmpty()) continue;
            if (!line.isEmpty() && line.codePointCount(0, line.length()) + 1
                + token.codePointCount(0, token.length()) > width) {
                lines.add(line.toString());
                line.setLength(0);
            }
            if (!line.isEmpty()) line.append(' ');
            line.append(token);
        }
        if (!line.isEmpty()) lines.add(line.toString());
        return lines.isEmpty() ? List.of("") : lines;
    }

    private static double clamp(double value, double min, double max) {
        return Math.max(min, Math.min(max, value));
    }
}
