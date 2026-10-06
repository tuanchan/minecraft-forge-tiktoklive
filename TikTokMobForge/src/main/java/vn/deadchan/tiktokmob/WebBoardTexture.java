package vn.deadchan.tiktokmob;

import com.google.gson.Gson;
import com.mojang.blaze3d.platform.NativeImage;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.resources.Identifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/** Persistent per-board disk frames; GPU images are kept only while their boards are being rendered. */
final class WebBoardTexture {
    private static final Path ROOT = Path.of(System.getenv().getOrDefault("LOCALAPPDATA", System.getProperty("user.home")),
        "TikTokMobForge", "pinned-board");
    private static final Map<String, Entry> ENTRIES = new LinkedHashMap<>();
    private static boolean busy;
    private static int generation;
    private static long nextPoll;
    private record Frame(String token, String file, int width, int height) { }
    private static final class Entry {
        final Identifier id;
        String file = "";
        long seen, checked;
        boolean ready;
        Entry(String token) { id = Identifier.fromNamespaceAndPath("tiktokmob", "web_board/" + token); }
    }

    static Identifier texture(String wanted) {
        if (!wanted.matches("[a-f0-9]{32}")) return null;
        Entry entry = ENTRIES.computeIfAbsent(wanted, Entry::new);
        entry.seen = System.nanoTime();
        return entry.ready ? entry.id : null;
    }

    static void tick() {
        long now = System.nanoTime();
        ENTRIES.entrySet().removeIf(item -> {
            Entry entry = item.getValue();
            if (now - entry.seen < 30_000_000_000L) return false;
            if (entry.ready) Minecraft.getInstance().getTextureManager().release(entry.id);
            return true;
        });
        if (busy || now < nextPoll || ENTRIES.isEmpty()) return;
        var wanted = ENTRIES.entrySet().stream().min(java.util.Comparator.comparingLong(e -> e.getValue().checked)).orElseThrow();
        String token = wanted.getKey();
        Entry entry = wanted.getValue();
        if (now - entry.checked < 500_000_000L) return;
        entry.checked = now;
        nextPoll = now + 50_000_000;
        busy = true;
        int request = generation;
        String previous = entry.file;
        CompletableFuture.runAsync(() -> {
            NativeImage image = null;
            try {
                Path manifest = ROOT.resolve(token + ".json");
                if (!Files.exists(manifest)) manifest = ROOT.resolve("frame.json");
                Frame frame = new Gson().fromJson(Files.readString(manifest), Frame.class);
                if (frame == null || !token.equals(frame.token) || frame.file == null
                    || !frame.file.matches("[a-f0-9]{32}\\.png") || frame.file.equals(previous)
                    || frame.width < 1 || frame.height < 1 || frame.width > 4096 || frame.height > 4096) return;
                Path path = ROOT.resolve(frame.file);
                if (Files.size(path) > 16_777_216) return;
                try (var stream = Files.newInputStream(path)) { image = NativeImage.read(stream); }
                if (image.getWidth() != frame.width || image.getHeight() != frame.height) return;
                NativeImage upload = image;
                image = null;
                Minecraft.getInstance().execute(() -> {
                    if (request != generation || ENTRIES.get(token) != entry) { upload.close(); return; }
                    try {
                        Minecraft.getInstance().getTextureManager().register(entry.id, new DynamicTexture(entry.id::toString, upload));
                        entry.file = frame.file; entry.ready = true;
                    } catch (RuntimeException error) {
                        upload.close();
                        com.mojang.logging.LogUtils.getLogger().warn("Cannot upload WebView board", error);
                    }
                });
            } catch (Exception ignored) {
                // A board can arrive before its WebView capture. Retry without hiding other boards.
            } finally {
                if (image != null) image.close();
                Minecraft.getInstance().execute(() -> { if (request == generation) busy = false; });
            }
        });
    }

    static void clear() {
        generation++; busy = false; nextPoll = 0;
        for (Entry entry : ENTRIES.values())
            if (entry.ready) Minecraft.getInstance().getTextureManager().release(entry.id);
        ENTRIES.clear();
    }
}
