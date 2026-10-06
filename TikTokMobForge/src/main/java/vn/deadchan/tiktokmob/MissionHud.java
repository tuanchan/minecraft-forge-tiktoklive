package vn.deadchan.tiktokmob;

import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.resources.Identifier;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Cyan segmented mission cards shared by the 2D HUD and 3D world display. */
final class MissionHud {
    private static final Identifier KILL_BG = texture("mission_kill_bg.png");
    private static final Identifier ZOMBIE = texture("mission_zombie.png");
    private static final Identifier SWORD = texture("mission_sword.png");
    private static final Identifier ORE = texture("mission_ore.png");
    private static final Identifier DIAMOND = texture("mission_diamond.png");
    private static final Identifier PICKAXE = texture("mission_pickaxe.png");
    private static List<Missions.View> views = List.of();
    private static final Map<String, String> lastReadyTokens = new HashMap<>();
    private static Identifier texture(String name) {
        return Identifier.fromNamespaceAndPath("tiktokmob", "textures/gui/" + name);
    }
    static void receive(GiftNetwork.MissionState packet) {
        try { views = List.of(Missions.GSON.fromJson(packet.json(), Missions.View[].class)); }
        catch (RuntimeException ignored) { views = List.of(); }
    }
    static void clear() { views = List.of(); lastReadyTokens.clear(); }
    private static double percent(long current, long target) {
        return Math.max(0, Math.min(100, 100.0 * current / Math.max(1, target)));
    }
    private static String percentText(double value) {
        if (value > 0 && value < .01) return "<0.01";
        if (value < 1) return String.format(java.util.Locale.ROOT, "%.2f", value).replaceAll("0+$", "").replaceAll("\\.$", "");
        return Long.toString(Math.round(value));
    }
    static void render(GuiGraphicsExtractor g) {
        var mc = Minecraft.getInstance();
        for (var view : views) {
            if (!view.mode().equals("2d")) continue;
            float scale = (float)Math.min(view.scale(), Math.min(g.guiWidth() / 356.0, g.guiHeight() / 94.0));
            float x = (float)((g.guiWidth() - 346 * scale) * view.x() / 100);
            float y = (float)((g.guiHeight() - 88 * scale) * view.y() / 100);
            g.pose().pushMatrix();g.pose().translate(x,y);g.pose().scale(scale,scale);
            card(g, view, mc);
            g.pose().popMatrix();
        }
    }
    private static void card(GuiGraphicsExtractor g, Missions.View view, Minecraft mc) {
        boolean kill = view.kind().equals("kill");
        if (kill) g.blit(RenderPipelines.GUI_TEXTURED, KILL_BG, 0, 0, 0, 0, 346, 88, 2172, 724, 2172, 724);
        else g.fill(0, 0, 346, 88, 0xeb08314b);
        g.fill(0, 0, 346, 3, 0xff63eaff); g.fill(0, 85, 346, 88, 0xff63eaff);
        g.fill(0, 0, 3, 88, 0xff63eaff); g.fill(343, 0, 346, 88, 0xff63eaff);
        Identifier left = kill ? SWORD : PICKAXE, right = kill ? ZOMBIE : ORE;
        g.blit(RenderPipelines.GUI_TEXTURED, left, 5, 12, 0, 0, 65, 65, 1254, 1254, 1254, 1254);
        g.blit(RenderPipelines.GUI_TEXTURED, right, 278, 12, 0, 0, 65, 65, 1254, 1254, 1254, 1254);
        if (!kill) g.blit(RenderPipelines.GUI_TEXTURED, DIAMOND, 315, 55, 0, 0, 27, 27, 1254, 1254, 1254, 1254);
        g.text(mc.font, mc.font.plainSubstrByWidth(view.title(), 192), 76, 10, 0xffffffff);
        double progress = percent(view.current(), view.target());
        g.fill(74, 29, 274, 57, 0xff7bcff3); g.fill(77, 32, 271, 54, 0xff243b52);
        int filled = 77 + (int)Math.ceil(194 * progress / 100);
        if (filled > 77) g.fill(77, 32, filled, 54, 0xff10dce7);
        int steps = Math.max(1, view.milestones());
        for (int i = 1; i < steps; i++) {
            int tick = 77 + 194 * i / steps;
            g.fill(tick, 32, tick + 1, 54, 0xbbe7ffff);
        }
        String label = percentText(progress) + "% · " + view.current() + " / " + view.target();
        g.text(mc.font, label, 174 - mc.font.width(label) / 2, 39, 0xffffffff);
    }
    static void submit(PoseStack poses, SubmitNodeCollector collector, float width, float height, BoardCaption caption, String token) {
        String[] parts = caption.text().split(":", 6);
        if (parts.length != 6) return;
        String missionId = parts[1];
        Identifier web = WebBoardTexture.texture(token);
        if (web != null) lastReadyTokens.put(missionId, token);
        else {
            String previous = lastReadyTokens.get(missionId);
            if (previous != null) web = WebBoardTexture.texture(previous);
        }
        // Keep the previous exact WebView frame while Chromium prepares the update.
        // On first creation, wait for WebView instead of flashing the approximate Java card.
        if (web == null) return;
        for (int side = 0; side < 2; side++) {
            poses.pushPose();
            if (side == 1) poses.mulPose(new org.joml.Quaternionf().rotationY((float)Math.PI));
            poses.translate(0, 0, Math.max(.0002f, width * .0002f));
            quad(poses, collector, web, -width / 2, 0, width / 2, height, -1);
            poses.popPose();
        }
    }
    private static void quad(PoseStack poses, SubmitNodeCollector collector, Identifier texture,
                             float left, float bottom, float right, float top, int color) {
        collector.submitCustomGeometry(poses, RenderTypes.text(texture), (pose, vertices) -> {
            vertices.addVertex(pose,left,bottom,0).setColor(color).setUv(0,1).setLight(0xF000F0);
            vertices.addVertex(pose,right,bottom,0).setColor(color).setUv(1,1).setLight(0xF000F0);
            vertices.addVertex(pose,right,top,0).setColor(color).setUv(1,0).setLight(0xF000F0);
            vertices.addVertex(pose,left,top,0).setColor(color).setUv(0,0).setLight(0xF000F0);
        });
    }
}
