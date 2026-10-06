package vn.deadchan.tiktokmob;

import net.minecraft.network.chat.Component;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SyncedDataHolder;
import net.minecraft.network.syncher.SynchedEntityData;

/** Reproduce the crash precondition: no non-default text exists on the first display. */
final class BoardTextChecks {
    private static final class Holder implements SyncedDataHolder {
        @Override public void onSyncedDataUpdated(net.minecraft.network.syncher.EntityDataAccessor<?> accessor) { }
        @Override public void onSyncedDataUpdated(java.util.List<SynchedEntityData.DataValue<?>> values) { }
    }

    static void run() {
        var origin = net.minecraft.world.phys.Vec3.ZERO;
        var forward = new net.minecraft.world.phys.Vec3(0, 0, -1);
        if (BoardRaycast.distance(new net.minecraft.world.phys.Vec3(0, 1, 4), forward, origin, 0, 0, 4, 2) != 4)
            throw new AssertionError("Crosshair inside front face must hit");
        if (BoardRaycast.distance(new net.minecraft.world.phys.Vec3(0, 1, -4), forward.scale(-1), origin, 0, 0, 4, 2) != 4)
            throw new AssertionError("Back face must be selectable");
        for (var eye : new net.minecraft.world.phys.Vec3[]{new net.minecraft.world.phys.Vec3(2.1, 1, 4),
                new net.minecraft.world.phys.Vec3(0, 2.1, 4), new net.minecraft.world.phys.Vec3(0, -.1, 4)})
            if (BoardRaycast.distance(eye, forward, origin, 0, 0, 4, 2) >= 0)
                throw new AssertionError("Looking outside the rectangle must not delete");
        if (BoardRaycast.distance(new net.minecraft.world.phys.Vec3(0, 1, 4), forward.scale(-1), origin, 0, 0, 4, 2) >= 0)
            throw new AssertionError("Board behind the viewer must not hit");
        for (float yaw : new float[]{0, 45, 90, 180, 270}) for (float pitch : new float[]{-70, 0, 60}) {
            var rotation = new org.joml.Quaternionf().rotationYXZ((float)Math.toRadians(-yaw), (float)Math.toRadians(pitch), 0);
            var eye = rotation.transform(new org.joml.Vector3f(0, 1, 7));
            var ray = rotation.transform(new org.joml.Vector3f(0, 0, -1));
            double hit = BoardRaycast.distance(new net.minecraft.world.phys.Vec3(eye.x,eye.y,eye.z),
                new net.minecraft.world.phys.Vec3(ray.x,ray.y,ray.z), origin, yaw, pitch, 4, 2);
            if (Math.abs(hit - 7) > .001) throw new AssertionError("Rotated board ray missed: " + yaw + "/" + pitch);
        }
        System.out.println("BOARD_RAYCAST_OK: front/back, rotated, outside, behind");
        var caption = new BoardCaption("Tuấn 😀", "Xin chào: bảng\nhai mặt", "#ffd99b", "#f4f7fb", .05, 50, 40, 55, 25, 17, 50, 1, 1);
        if (!caption.equals(BoardCaption.decode(BoardCaption.encode(caption))))
            throw new AssertionError("Hologram caption lost Unicode, newline or layout");
        if (BoardCaption.decode("bad!") != null) throw new AssertionError("Invalid caption accepted");
        for (double zoom : new double[]{.001, 25, 100}) {
            var resized = new BoardCaption("Author", "Comment", "#ffd99b", "#f4f7fb",
                zoom, 50, 40, 20, 60, 17, 50, 1, zoom);
            if (!resized.equals(BoardCaption.decode(BoardCaption.encode(resized))))
                throw new AssertionError("Board zoom lost on caption round trip: " + zoom);
        }

        // Use Minecraft's actual TextDisplay schema and real SynchedEntityData storage.
        // A test holder avoids constructing a full ServerLevel merely to test data synchronization.
        var text = ServerPinnedCommentBoard.textDataAccessor();
        var builder = new SynchedEntityData.Builder(new Holder());
        // Builder capacity is determined at construction, so register the holder schema first.
        var padding = new java.util.ArrayList<net.minecraft.network.syncher.EntityDataAccessor<Byte>>();
        for (int i = 0; i < text.id(); i++)
            padding.add(SynchedEntityData.defineId(Holder.class, EntityDataSerializers.BYTE));
        var testText = SynchedEntityData.defineId(Holder.class, EntityDataSerializers.COMPONENT);
        builder = new SynchedEntityData.Builder(new Holder());
        for (var accessor : padding) builder.define(accessor, (byte) 0);
        builder.define(testText, Component.empty());
        var data = builder.build();
        if (data.getNonDefaultValues() != null) throw new AssertionError("Expected empty default state");
        ServerPinnedCommentBoard.setTextData(data, Component.empty());
        var marker = Component.literal("tiktokmob:web-board:test:5.4:1.62");
        ServerPinnedCommentBoard.setTextData(data, marker);
        if (!data.get(text).equals(marker) || data.packDirty() == null)
            throw new AssertionError("New board text was not synchronized");
        ServerPinnedCommentBoard.setTextData(data, Component.empty());
        if (!data.get(text).equals(Component.empty()) || data.packDirty() == null)
            throw new AssertionError("Clearing text was not synchronized");
        ServerPinnedCommentBoard.setTextData(data, marker);
        if (!data.get(text).equals(marker)) throw new AssertionError("Cannot reuse cleared board");
        System.out.println("BOARD_TEXT_CHECKS_OK: default empty, first update, clear, reuse, dirty packets");
    }
}
