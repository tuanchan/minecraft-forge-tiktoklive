package vn.deadchan.tiktokmob;

import com.google.gson.Gson;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import org.lwjgl.glfw.GLFW;

import java.nio.file.Files;
import java.nio.file.Path;

/** Client-side controls for the server-owned pinned comment display. */
final class PinnedCommentBoard {
    private static final Gson GSON = new Gson();
    private static final Path POSITION_FILE = Minecraft.getInstance().gameDirectory.toPath()
        .resolve("config/tiktokmob-pinned-board.json");
    private static Position position = load();
    private static String currentAuthor = "", currentText = "";
    private static boolean grabbing, resetHeld, resetRequested, pinned, orbitPaused, wasGrabDown;
    private static long grabStartedAt, lastTapAt, revision = -1;
    private static int syncTicks;
    private static boolean selecting, selectionReady, keyHeld, pendingPin, pendingGrab;
    private static double pendingScroll;
    private static boolean pendingDistance;

    private static final class Position {
        double side = 0, height = 0.15, scale = 1, distance = 3;
    }

    static void receive(GiftNetwork.PinnedComment message) {
        String nextAuthor = message.author().strip();
        String nextText = message.text().strip();
        boolean changed = message.revision() != revision;
        if (selecting && !message.selectionReply()) return;
        if (!changed && !message.selectionReply()) return;
        if (changed) {
            grabbing = false; wasGrabDown = false; resetHeld = false; lastTapAt = 0;
        }
        revision = message.revision(); currentAuthor = nextAuthor; currentText = nextText;
        var saved = message.position();
        position.side = saved.side(); position.height = saved.height(); position.distance = saved.distance(); position.scale = saved.scale();
        pinned = saved.pinned(); orbitPaused = saved.paused();
        if (message.selectionReply()) { selecting = false; selectionReady = true; }
        syncTicks = 0;
    }

    private static void select() {
        selecting = true; selectionReady = false;
        GiftNetwork.selectBoard();
    }

    static void reset() {
        selecting = false; selectionReady = false; keyHeld = false; pendingPin = false; pendingGrab = false; pendingScroll = 0;
        revision = -1;
        currentAuthor = "";
        currentText = "";
        grabbing = false;
        resetHeld = false;
        resetRequested = false;
        pinned = false;
        orbitPaused = false;
        wasGrabDown = false;
        grabStartedAt = 0;
        lastTapAt = 0;
        syncTicks = 0;
    }

    static boolean visible() { return !currentText.isEmpty(); }

    static boolean scroll(double steps, boolean distanceMode) {
        if (steps == 0 || !Double.isFinite(steps)) return false;
        if (!keyHeld && !selecting && pendingScroll == 0) { keyHeld = true; pendingGrab = true; select(); }
        if (selecting) { pendingScroll += steps; pendingDistance = distanceMode; return true; }
        if (!visible()) return false;
        if (distanceMode) {
            double next = Math.max(0, position.distance - steps * 0.5);
            if (Double.isFinite(next)) position.distance = next;
        } else {
            double next = position.scale * Math.pow(1.12, steps);
            // Keep a positive, representable render scale without gameplay zoom limits.
            if (Double.isFinite(next) && Float.isFinite((float) next) && (float) next > 0)
                position.scale = next;
        }
        save();
        syncTicks = 0;
        return true;
    }

    static void tick(Minecraft mc, boolean grabDown, boolean pinClicked) {
        if (mc.level == null || mc.player == null) { reset(); return; }
        if (mc.gui.screen() == null && ((grabDown && !keyHeld) || pinClicked)) {
            keyHeld = grabDown; pendingPin |= pinClicked; pendingGrab |= grabDown;
            if (!selecting) select();
        }
        if (!grabDown) keyHeld = false;
        if (selecting) return;
        pinClicked = pendingPin; pendingPin = false;
        if (selectionReady) {
            selectionReady = false;
            if (pendingGrab && !grabDown && !pinned) wasGrabDown = true;
            pendingGrab = false;
            if (pendingScroll != 0) { double steps = pendingScroll; keyHeld = true; pendingScroll = 0; scroll(steps, pendingDistance); }
        }
        if (currentText.isEmpty()) {
            grabbing = false;
            wasGrabDown = false;
            return;
        }
        if (pinClicked && mc.gui.screen() == null) {
            if (grabbing) finishGrab(mc);
            pinned = !pinned;
            if (!pinned) orbitPaused = false;
            syncTicks = 0;
            mc.gui.hud.getChat().addClientSystemMessage(Component.literal(pinned
                ? "Đã ghim bảng tại vị trí hiện tại. Nhấn F lần nữa để bỏ ghim."
                : "Đã bỏ ghim bảng. Bảng tiếp tục đi theo người chơi."));
        }
        long now = System.currentTimeMillis();
        boolean eligible = grabDown && !pinned && mc.gui.screen() == null;
        if (eligible && !wasGrabDown) grabStartedAt = now;
        boolean active = eligible && now - grabStartedAt >= 180;
        if (!eligible && wasGrabDown) {
            if (grabbing) {
                finishGrab(mc);
                orbitPaused = true;
                lastTapAt = 0;
                syncTicks = 0;
            } else if (mc.gui.screen() == null && !pinned) {
                if (lastTapAt > 0 && now - lastTapAt <= 350) {
                    orbitPaused = false;
                    lastTapAt = 0;
                } else {
                    orbitPaused = true;
                    lastTapAt = now;
                }
                syncTicks = 0;
            }
        }
        wasGrabDown = eligible;
        if (active) {
            if (!grabbing) {
                position.side = 0;
                position.height = 0;
            }
            long window = mc.getWindow().handle();
            boolean resetting = down(window, GLFW.GLFW_KEY_HOME);
            if (resetting && !resetHeld) {
                position = new Position();
                position.height = 0;
                resetRequested = true;
                save();
                mc.gui.hud.getChat().addClientSystemMessage(
                    Component.literal("Đã đưa bảng bình luận ghim về vị trí mặc định."));
            }
            resetHeld = resetting;
            grabbing = true;
        }
        // The server owns the actual entities. Resend periodically after reconnect or a world change.
        if (active || pinClicked || syncTicks++ % 20 == 0) {
            GiftNetwork.sendBoardPosition(revision, new GiftNetwork.BoardPosition(position.side, position.height,
                position.distance, position.scale, active, pinned, orbitPaused));
        }
    }

    private static void finishGrab(Minecraft mc) {
        grabbing = false;
        resetHeld = false;
        resetRequested = false;
        save();
    }

    private static boolean down(long window, int key) { return GLFW.glfwGetKey(window, key) == GLFW.GLFW_PRESS; }
    private static double clamp(double value, double min, double max) { return Math.max(min, Math.min(max, value)); }

    private static Position load() {
        try {
            Position read = GSON.fromJson(Files.readString(POSITION_FILE), Position.class);
            if (read != null && Double.isFinite(read.side) && Double.isFinite(read.height)
                && Double.isFinite(read.scale) && read.scale > 0) {
                read.side = clamp(read.side, -12, 12);
                read.height = clamp(read.height, -8, 8);
                read.distance = Double.isFinite(read.distance) ? Math.max(0, read.distance) : 3;
                return read;
            }
        } catch (Exception ignored) { }
        return new Position();
    }

    private static void save() {
        try {
            Files.createDirectories(POSITION_FILE.getParent());
            Files.writeString(POSITION_FILE, GSON.toJson(position));
        } catch (Exception ignored) { }
    }
}
