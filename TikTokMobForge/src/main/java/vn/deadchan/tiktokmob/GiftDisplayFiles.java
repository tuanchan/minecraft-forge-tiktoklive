package vn.deadchan.tiktokmob;

import java.nio.file.Files;
import java.nio.file.Path;

/** Heartbeat shared with the local bridge while a gift waits for respawn. */
final class GiftDisplayFiles {
    static final Path ROOT = Path.of(System.getenv().getOrDefault("LOCALAPPDATA", System.getProperty("user.home")),
        "TikTokMobForge", "gift-alerts");
    static void paused(String token, boolean paused) {
        if (!token.matches("[a-f0-9]{32}")) return;
        Path folder = ROOT.resolve(token);
        if (!Files.exists(folder.resolve("manifest.json"))) return;
        try {
            if (paused) Files.writeString(folder.resolve("paused"), "Waiting for respawn");
            else Files.deleteIfExists(folder.resolve("paused"));
        } catch (java.io.IOException ignored) { }
    }
}
