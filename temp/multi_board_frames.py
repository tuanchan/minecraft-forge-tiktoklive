from pathlib import Path
r=Path('TikTokMobForge')
p=r/'bridge/pinned_overlay.py';s=p.read_text(encoding='utf-8');s=s.replace('    name = None\n', '''    if data["text"].strip():
        history = STATE.parent / "pinned-history"
        history.mkdir(parents=True, exist_ok=True)
        entry = history / (data["token"] + ".json")
        # Keep each content frame available even if several comments arrive before WebView captures.
        if not entry.exists():
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=history, delete=False) as saved:
                json.dump(data, saved, ensure_ascii=False)
            os.replace(saved.name, entry)
    name = None
''');s=s.replace('        return data\n', '''        data["boards"] = []
        for entry in sorted((STATE.parent / "pinned-history").glob("*.json")):
            try:
                board = json.loads(entry.read_text(encoding="utf-8"))
                if board.get("text") and board.get("token") == entry.stem:
                    data["boards"].append(board)
            except (OSError, ValueError):
                continue
        if data.get("text") and not any(board["token"] == data["token"] for board in data["boards"]):
            data["boards"].append({key: value for key, value in data.items() if key != "boards"})
        return data
''');p.write_text(s,encoding='utf-8')
p=r/'web/pinned-overlay.js';s=p.read_text(encoding='utf-8');start=s.index('async function poll()');s=s[:start]+'''const capturedTokens = new Map();
let pendingCapture = null;
async function poll() {
  try {
    // Keep the same DOM until the native capture acknowledges it; never photograph a later comment by mistake.
    if (pendingCapture && window.capturedFrame !== pendingCapture.revision) {
      if (Date.now() - pendingCapture.sent > 3000) {
        window.chrome?.webview?.postMessage(pendingCapture.message);
        pendingCapture.sent = Date.now();
      }
      return;
    }
    if (pendingCapture) {
      capturedTokens.set(pendingCapture.token, pendingCapture.signature);
      pendingCapture = null;
    }
    const response = await fetch('/api/pinned-overlay', {cache:'no-store'});
    if (!response.ok) throw new Error('Overlay unavailable');
    const data = await response.json();
    if (!textureMode) { renderPinnedOverlay(data); return; }
    const boards = [...(data.boards || [])];
    if (data.text && data.token) {
      const index = boards.findIndex(board => board.token === data.token);
      if (index >= 0) boards.splice(index, 1);
      boards.unshift(data);
    }
    const wanted = boards.find(board => {
      const signature = JSON.stringify([board.token, board.avatar, data.style]);
      // Frozen boards retain their first captured style; the newest one can still be edited.
      return !capturedTokens.has(board.token) || (board.token === data.token && capturedTokens.get(board.token) !== signature);
    });
    if (!wanted) return;
    renderPinnedOverlay({...wanted, style:data.style});
    const signature = JSON.stringify([wanted.token, wanted.avatar, data.style]);
    await document.fonts.ready;
    try { if (wanted.avatar) await $('avatar').decode(); } catch { }
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const rect = $('board').getBoundingClientRect();
    const message = {type:'frame', token:wanted.token, revision:++frameRevision, width:rect.width, height:rect.height};
    pendingCapture = {token:wanted.token, signature, revision:frameRevision, message, sent:Date.now()};
    window.chrome?.webview?.postMessage(message);
  } catch { if (!pendingCapture) visibility(false); }
  finally { setTimeout(poll, 350); }
}
poll();
''';p.write_text(s,encoding='utf-8')
p=r/'Desktop/PinOverlayForm.cs';s=p.read_text(encoding='utf-8');start=s.index('                foreach (var old in new DirectoryInfo');end=s.index('                await view.ExecuteScriptAsync',start);s=s[:start]+'''                // Index every board separately; capturing a new comment must not evict an older one.
                var tokenManifest = Path.Combine(frameRoot, token + ".json");
                string? oldFile = null;
                if (File.Exists(tokenManifest)) {
                    try {
                        using var previous = JsonDocument.Parse(await File.ReadAllTextAsync(tokenManifest));
                        oldFile = previous.RootElement.GetProperty("file").GetString();
                    } catch (Exception) { }
                }
                var tokenTemp = Path.Combine(frameRoot, Guid.NewGuid().ToString("N") + ".json");
                await File.WriteAllTextAsync(tokenTemp, manifest);
                File.Move(tokenTemp, tokenManifest, true);
                if (oldFile != null && oldFile != filename && System.Text.RegularExpressions.Regex.IsMatch(oldFile, "^[a-f0-9]{32}\\\\.png$")) {
                    try { File.Delete(Path.Combine(frameRoot, oldFile)); } catch (IOException) { }
                }
'''+s[end:];p.write_text(s,encoding='utf-8')
# Per-token GPU cache. World displays request their own texture, including old boards after reconnect.
p=r/'src/main/java/vn/deadchan/tiktokmob/WebBoardTexture.java';p.write_text('''package vn.deadchan.tiktokmob;

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
                    || !frame.file.matches("[a-f0-9]{32}\\\\.png") || frame.file.equals(previous)
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
''',encoding='utf-8')
p=r/'web/app.js';s=p.read_text(encoding='utf-8').replace('$("#testUnpinBtn").addEventListener("click", () => launchTest("pin_clear"));','$("#testUnpinBtn").addEventListener("click", () => toast("Trong Minecraft, ngắm vào bảng cần xóa rồi nhấn X. Các bảng khác được giữ nguyên."));');p.write_text(s,encoding='utf-8')
p=r/'web/index.html';s=p.read_text(encoding='utf-8').replace('>Bỏ ghim bảng</button>','>Cách xóa bảng</button>').replace('F ghim vị trí, X xóa bảng.', 'F ghim vị trí; ngắm vào bảng rồi nhấn X để xóa riêng bảng đó. Bình luận mới giữ nguyên các bảng cũ.');p.write_text(s,encoding='utf-8')
print('MULTI_FRAME_CAPTURE_UPDATED')
