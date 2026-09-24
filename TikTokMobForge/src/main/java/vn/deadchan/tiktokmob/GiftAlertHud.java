package vn.deadchan.tiktokmob;

import com.google.gson.Gson;
import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.logging.LogUtils;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.resources.Identifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;

/** Local bridge frames are rendered by Minecraft, including in fullscreen and Game Capture. */
final class GiftAlertHud {
    private static final Path ROOT = Path.of(System.getenv().getOrDefault("LOCALAPPDATA", System.getProperty("user.home")),
        "TikTokMobForge", "gift-alerts");
    private static final List<Identifier> textures = new ArrayList<>();
    private static Path directory;
    private static Manifest manifest;
    private static long started, loaded, lastTick, pauseHeartbeat;
    private static int generation;
    private record Manifest(int width, int height, int[] delays, double duration, double display_width, double x, double y) {
        void validate() {
            if (width < 1 || width > 800 || height < 1 || height > 1200 || delays == null
                || delays.length < 1 || delays.length > 300 || (long)width * height * delays.length > 48_000_000
                || !Double.isFinite(duration) || duration < 1 || duration > 120
                || !Double.isFinite(display_width) || display_width < 160 || display_width > 800
                || !Double.isFinite(x) || x < 0 || x > 100 || !Double.isFinite(y) || y < 0 || y > 100)
                throw new IllegalArgumentException("Invalid gift animation manifest");
            for (int delay : delays) if (delay < 20 || delay > 60_000) throw new IllegalArgumentException("Invalid GIF delay");
        }
    }
    static void load(String token) {
        if (!token.matches("[a-f0-9]{32}")) return;
        clear();
        int request = generation;
        Path folder = ROOT.resolve(token);
        CompletableFuture.runAsync(() -> {
            List<NativeImage> images = new ArrayList<>();
            try {
                Manifest data = new Gson().fromJson(Files.readString(folder.resolve("manifest.json")), Manifest.class);
                data.validate();
                for (int i = 0; i < data.delays.length; i++) {
                    try (var input = Files.newInputStream(folder.resolve(i + ".png"))) {
                        NativeImage image = NativeImage.read(input);
                        if (image.getWidth() != data.width || image.getHeight() != data.height) {
                            image.close(); throw new IllegalArgumentException("GIF frame dimensions differ");
                        }
                        images.add(image);
                    }
                }
                Minecraft.getInstance().execute(() -> {
                    if (request != generation || Minecraft.getInstance().level == null || !Files.exists(folder.resolve("manifest.json"))) {
                        images.forEach(NativeImage::close); return;
                    }
                    try {
                        for (int i = 0; i < images.size(); i++) {
                            Identifier id = Identifier.fromNamespaceAndPath("tiktokmob", "gift_alert/" + token + "/" + i);
                            Minecraft.getInstance().getTextureManager().register(id, new DynamicTexture(id::toString, images.get(i)));
                            textures.add(id);
                        }
                        manifest = data; directory = folder; started = 0; loaded = System.nanoTime(); lastTick = loaded;
                    } catch (Exception error) {
                        for (int i = textures.size(); i < images.size(); i++) images.get(i).close();
                        clear(); fail(folder, error);
                    }
                });
            } catch (Exception error) {
                images.forEach(NativeImage::close); fail(folder, error);
            }
        });
    }
    private static void fail(Path folder, Exception error) {
        LogUtils.getLogger().warn("TikTok gift animation failed", error);
        try { if (Files.isDirectory(folder)) Files.writeString(folder.resolve("error"), "Minecraft không tải được GIF: " + error.getMessage()); }
        catch (Exception ignored) {}
    }
    static void clear() {
        if (manifest == null && textures.isEmpty()) { generation++; return; }
        generation++;
        for (Identifier id : textures) Minecraft.getInstance().getTextureManager().release(id);
        textures.clear(); manifest = null; directory = null; started = 0; pauseHeartbeat = 0;
    }
    static void tick() {
        if (manifest == null) return;
        long now = System.nanoTime();
        var mc = Minecraft.getInstance();
        if (mc.player == null || !mc.player.isAlive() || mc.player.isSpectator() || mc.isPaused()) {
            if (started != 0) started += now - lastTick;
            loaded += now - lastTick;
            lastTick = now;
            if (now - pauseHeartbeat > 1_000_000_000L) {
                GiftDisplayFiles.paused(directory.getFileName().toString(), true);
                pauseHeartbeat = now;
            }
            return;
        }
        lastTick = now;
        if (pauseHeartbeat != 0) {
            GiftDisplayFiles.paused(directory.getFileName().toString(), false);
            pauseHeartbeat = 0;
        }
        if (started != 0 && (now - started) / 1e9 > manifest.duration) {
            try { Files.writeString(directory.resolve("finished"), "Minecraft HUD finished"); }
            catch (Exception ignored) { }
            clear();
            return;
        }
        if (!Files.exists(directory.resolve("manifest.json"))
            || (started != 0 && (System.nanoTime() - started) / 1e9 > manifest.duration + 0.15)
            || (started == 0 && (System.nanoTime() - loaded) / 1e9 > 15)) clear();
    }
    static void render(GuiGraphicsExtractor graphics) {
        if (manifest == null || textures.isEmpty()) return;
        var player = Minecraft.getInstance().player;
        if (player == null || !player.isAlive() || player.isSpectator()) return;
        if (started == 0) {
            started = System.nanoTime();
            try { Files.writeString(directory.resolve("ready"), "Minecraft HUD ready"); }
            catch (Exception error) { fail(directory, error); clear(); return; }
            LogUtils.getLogger().info("TikTok gift GIF visible in Minecraft HUD");
        }
        long elapsed = (System.nanoTime() - started) / 1_000_000;
        if (elapsed > manifest.duration * 1000) return;
        long loop = 0;
        for (int delay : manifest.delays) loop += delay;
        long offset = elapsed % loop;
        int frame = 0;
        while (frame < manifest.delays.length - 1 && offset >= manifest.delays[frame]) offset -= manifest.delays[frame++];
        // Width is measured on a reference 1920px game canvas, independent of GUI scale.
        double scale = Math.min(manifest.display_width / 1920.0 * graphics.guiWidth() / manifest.width,
                               (graphics.guiHeight() - 4.0) / manifest.height);
        int width = Math.max(1, (int)Math.round(manifest.width * scale));
        int height = Math.max(1, (int)Math.round(manifest.height * scale));
        int x = (int)Math.round(Math.max(0, graphics.guiWidth() - width) * manifest.x / 100);
        int y = (int)Math.round(Math.max(0, graphics.guiHeight() - height) * manifest.y / 100);
        graphics.blit(RenderPipelines.GUI_TEXTURED, textures.get(frame), x, y, 0, 0, width, height,
                      manifest.width, manifest.height, manifest.width, manifest.height);
    }
}
