package vn.deadchan.tiktokmob;

import com.google.gson.*;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.*;
import java.util.function.Consumer;

/** Uses the local GUI runner so game and desktop share cancellation and logs. */
final class TestControlScreen extends Screen {
    private static final HttpClient HTTP = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();
    private final Screen parent;
    private final List<String> logs = new ArrayList<>();
    private final List<Button> starts = new ArrayList<>();
    private final Map<String, EditBox> fields = new LinkedHashMap<>();
    private JsonArray gifts = new JsonArray();
    private int giftIndex, logPage;
    private long offset, nextPoll, nextCatalog;
    private boolean polling, submitting, running, loadingCatalog;
    private String status = "Đang kết nối GUI trên máy này…";
    private Button giftButton, stop;

    TestControlScreen(Screen parent) { super(Component.literal("TikTok · Test mod, quà và nhật ký")); this.parent = parent; }

    @Override protected void init() {
        Map<String, String> saved = new HashMap<>();
        fields.forEach((key, box) -> saved.put(key, box.getValue()));
        fields.clear(); starts.clear();
        int left = 8, col = (width - 16) / 4;
        String[] keys = {"name", "users", "count", "interval", "mob"};
        String[] defaults = {"Test User", "1", "1", "0.2", "minecraft:zombie"};
        for (int i = 0; i < keys.length; i++) {
            EditBox box = new EditBox(font, left + (i % 4) * col, i < 4 ? 40 : 76,
                i == 4 ? col * 2 - 4 : col - 4, 18, Component.literal(keys[i]));
            box.setMaxLength(128); box.setValue(saved.getOrDefault(keys[i], defaults[i]));
            fields.put(keys[i], addRenderableWidget(box));
        }
        start("Mob đã nhập", left + col * 2, 76, col - 4, "mob", "");
        start("Full 4 tương tác", left + col * 3, 76, col - 4, "all_mobs", "");
        String[] events = {"like", "comment", "share", "follow"};
        for (int i = 0; i < 4; i++) start(events[i], left + i * col, 99, col - 4, "event", events[i]);
        giftButton = addRenderableWidget(Button.builder(Component.literal(giftLabel()), b -> {
            if (!gifts.isEmpty()) giftIndex = (giftIndex + 1) % gifts.size();
            b.setMessage(Component.literal(giftLabel()));
        }).bounds(left, 122, col * 2 - 4, 20).build());
        start("Test quà đã chọn", left + col * 2, 122, col - 4, "gift", "");
        start("Tất cả quà", left + col * 3, 122, col - 4, "all_gifts", "");
        start("Spam 4 tương tác", left, 145, col - 4, "spam", "all");
        stop = addRenderableWidget(Button.builder(Component.literal("Dừng test"), b -> post("/api/test/stop", new JsonObject()))
            .bounds(left + col, 145, col - 4, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Log cũ ←"), b -> logPage++)
            .bounds(left + col * 2, 145, col - 4, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Mới nhất"), b -> logPage = 0)
            .bounds(left + col * 3, 145, col - 4, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Quay lại"), b -> onClose()).bounds(width - 90, height - 24, 82, 20).build());
        loadCatalog();
    }
    private void loadCatalog() {
        if (loadingCatalog) return;
        loadingCatalog = true;
        request("/api/test/catalog", null, data -> {
            gifts = data.getAsJsonArray("gifts"); giftIndex = Math.min(giftIndex, Math.max(0, gifts.size() - 1));
            giftButton.setMessage(Component.literal(giftLabel()));
        }, () -> { loadingCatalog = false; nextCatalog = System.nanoTime() + 5_000_000_000L; });
    }

    private String giftLabel() {
        if (gifts.isEmpty()) return "Chưa có quà · mở GUI để gán";
        JsonObject gift = gifts.get(giftIndex).getAsJsonObject();
        return (giftIndex + 1) + "/" + gifts.size() + " · " + gift.get("gift_name").getAsString() + " ▸";
    }
    private void start(String label, int x, int y, int w, String mode, String event) {
        starts.add(addRenderableWidget(Button.builder(Component.literal(label), b -> {
            if (submitting || running) return;
            try {
                JsonObject body = new JsonObject();
                body.addProperty("mode", mode); body.addProperty("event", event);
                body.addProperty("gift_index", giftIndex);
                body.addProperty("name", fields.get("name").getValue());
                body.addProperty("mob", fields.get("mob").getValue());
                for (String key : List.of("users", "count", "interval")) {
                    double value = Double.parseDouble(fields.get(key).getValue());
                    if (!Double.isFinite(value)) throw new IllegalArgumentException();
                    body.addProperty(key, value);
                }
                post("/api/test", body);
            } catch (Exception error) { status = "Kiểm tra số người, số lượt và thời gian nghỉ"; }
        }).bounds(x, y, w, 20).build()));
    }
    private void post(String path, JsonObject body) {
        if (submitting) return;
        submitting = true;
        request(path, body, this::testState, () -> submitting = false);
    }
    private void testState(JsonObject data) {
        running = data.get("running").getAsBoolean();
        status = data.get("message").getAsString() + " · " + data.get("sent") + "/" + data.get("total") + " lệnh";
    }
    private void request(String path, JsonObject body, Consumer<JsonObject> success, Runnable done) {
        var builder = HttpRequest.newBuilder(URI.create("http://127.0.0.1:54420" + path)).timeout(Duration.ofSeconds(5));
        if (body != null) builder.header("Content-Type", "application/json").POST(HttpRequest.BodyPublishers.ofString(body.toString()));
        HTTP.sendAsync(builder.build(), HttpResponse.BodyHandlers.ofString()).whenComplete((response, error) ->
            Minecraft.getInstance().execute(() -> {
                try {
                    if (error != null) throw new IllegalStateException("Mở GUI trên máy này; đang tự kết nối lại");
                    JsonObject data = JsonParser.parseString(response.body()).getAsJsonObject();
                    if (response.statusCode() != 200) throw new IllegalStateException(data.has("error") ? data.get("error").getAsString() : "GUI chưa hỗ trợ API này");
                    success.accept(data);
                } catch (Exception failure) { status = failure.getMessage() == null ? "Không đọc được phản hồi GUI" : failure.getMessage(); }
                finally { done.run(); }
            }));
    }
    @Override public void tick() {
        if (minecraft.level == null) { minecraft.gui.setScreen(null); return; }
        starts.forEach(b -> b.active = !running && !submitting);
        stop.active = running && !submitting;
        if (!running && !submitting && System.nanoTime() >= nextCatalog) loadCatalog();
        if (polling || System.nanoTime() < nextPoll) return;
        polling = true;
        request("/api/logs?offset=" + offset, null, data -> {
            offset = data.get("offset").getAsLong();
            for (JsonElement line : data.getAsJsonArray("lines")) logs.add(line.getAsString());
            if (logs.size() > 1000) logs.subList(0, logs.size() - 1000).clear();
            testState(data.getAsJsonObject("test"));
        }, () -> { polling = false; nextPoll = System.nanoTime() + 700_000_000L; });
    }
    @Override public void extractRenderState(GuiGraphicsExtractor g, int mx, int my, float partial) {
        g.fill(0, 0, width, height, 0xf00a121e);
        g.centeredText(font, title, width / 2, 8, 0xff55ffff);
        String[] labels = {"Tên người thử", "Số người (1–50)", "Lượt/người (1–100)", "Nghỉ (0–10 giây)"};
        for (int i = 0; i < 4; i++) g.text(font, labels[i], 8 + i * ((width - 16) / 4), 28, 0xffb9d6ef);
        g.text(font, "ID mob · quà: bấm tên để chuyển", 8, 64, 0xffb9d6ef);
        List<String> wrapped = new ArrayList<>();
        for (String line : logs) {
            while (!line.isEmpty()) {
                String part = font.plainSubstrByWidth(line, Math.max(40, width - 20));
                if (part.isEmpty()) break;
                wrapped.add(part); line = line.substring(part.length());
            }
        }
        int rows = Math.max(1, (height - 207) / 10);
        logPage = Math.min(logPage, Math.max(0, (wrapped.size() - 1) / rows));
        int end = Math.max(0, wrapped.size() - logPage * rows), begin = Math.max(0, end - rows);
        for (int i = begin; i < end; i++) g.text(font, wrapped.get(i), 8, 174 + (i - begin) * 10, 0xffd3dfeb);
        g.text(font, font.plainSubstrByWidth(status, Math.max(40, width - 108)), 8, height - 20, 0xffffdb83);
        for (var widget : renderables) widget.extractRenderState(g, mx, my, partial);
    }
    @Override public void onClose() { minecraft.gui.setScreen(parent); }
    @Override public boolean isPauseScreen() { return false; }
}
