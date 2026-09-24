package vn.deadchan.tiktokmob;

import com.google.gson.*;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.components.Tooltip;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.item.SpawnEggItem;
import net.minecraftforge.network.PacketDistributor;
import java.util.*;

final class RuntimeSettingsScreen extends Screen {
    private final Screen parent;
    private JsonObject baseline;
    private final Map<String, String> drafts = new HashMap<>();
    private final Map<String, EditBox> inputs = new HashMap<>();
    private final Map<String, Button> toggles = new HashMap<>();
    private List<RuntimeSettings.Field> visible = List.of();
    private int group, page, perPage;
    private boolean filling, waiting;
    private String pendingRequest = "";
    private long sentAt;
    private String status = "Lưu để áp dụng trong game, GUI và LIVE";
    private Button save;
    RuntimeSettingsScreen(Screen parent) {
        super(Component.literal("Cài đặt TikTok Mob"));
        this.parent = parent;
        baseline = TikTokClient.runtimeSettings.deepCopy();
    }
    private String value(RuntimeSettings.Field field) {
        return drafts.getOrDefault(field.key(), baseline.has(field.key()) ? baseline.get(field.key()).getAsString() : field.initial());
    }
    private void edit(RuntimeSettings.Field field, String text) {
        if (filling) return;
        String old = baseline.has(field.key()) ? baseline.get(field.key()).getAsString() : field.initial();
        if (old.equals(text)) drafts.remove(field.key()); else drafts.put(field.key(), text);
        status = drafts.isEmpty() ? "Đã đồng bộ" : "Có thay đổi chưa lưu";
    }
    @Override protected void init() { layout(); }
    private void layout() {
        clearWidgets(); inputs.clear(); toggles.clear();
        int panel = Math.min(620, width - 16), left = (width - panel) / 2;
        addRenderableWidget(Button.builder(Component.literal("Test / Log"), b -> minecraft.gui.setScreen(new TestControlScreen(this)))
            .bounds(width - 90, 5, 84, 20).build());
        String[] names = {"Giới hạn", "Theo dõi", "Bình luận", "Chia sẻ", "Lượt thích", "View"};
        for (int i = 0; i < names.length; i++) {
            final int selected = i;
            var tab = addRenderableWidget(Button.builder(Component.literal(names[i]), b -> {group = selected; page = 0; layout();})
                .bounds(left + i * (panel / names.length), 36, panel / names.length - 3, 20).build());
            tab.active = i != group && !waiting;
        }
        int rows = Math.max(1, (height - 140) / 42);
        perPage = rows * 2;
        List<RuntimeSettings.Field> fields = RuntimeSettings.FIELDS.stream().filter(f -> f.group() == group).toList();
        int pages = Math.max(1, (fields.size() + perPage - 1) / perPage);
        page = Math.min(page, pages - 1);
        visible = fields.subList(page * perPage, Math.min(fields.size(), (page + 1) * perPage));
        int column = panel / 2;
        for (int i = 0; i < visible.size(); i++) {
            var field = visible.get(i);
            int x = left + i % 2 * column, y = 80 + i / 2 * 42;
            if (field.kind().equals("direction")) {
                var directions = java.util.List.of("front", "right", "left", "back", "random");
                var labels = java.util.List.of("Trước mặt", "Bên phải", "Bên trái", "Đằng sau", "Ngẫu nhiên");
                int selected = Math.max(0, directions.indexOf(value(field)));
                addRenderableWidget(Button.builder(Component.literal(labels.get(selected)), b -> {
                    int next = (directions.indexOf(value(field)) + 1) % directions.size();
                    edit(field, directions.get(next));
                    b.setMessage(Component.literal(labels.get(next)));
                }).bounds(x, y, column - 10, 20).build());
            } else if (field.kind().equals("bool")) {
                Button toggle = addRenderableWidget(Button.builder(Component.literal(Boolean.parseBoolean(value(field)) ? "Bật" : "Tắt"), b -> {
                    edit(field, Boolean.toString(!Boolean.parseBoolean(value(field))));
                    b.setMessage(Component.literal(Boolean.parseBoolean(value(field)) ? "Bật" : "Tắt"));
                }).bounds(x, y, column - 10, 20).build());
                toggles.put(field.key(), toggle);
            } else {
                boolean mob = field.kind().equals("mob");
                EditBox box = new EditBox(font, x, y, column - (mob ? 56 : 10), 20, Component.literal(field.label()));
                box.setMaxLength(mob ? 128 : 20);
                box.setEditable(!waiting);
                box.setValue(value(field)); box.setResponder(text -> edit(field, text));
                box.setTooltip(Tooltip.create(Component.literal(mob ? "Nhập ID hoặc bấm Chọn để tìm mob" : "Từ " + field.min() + " đến " + field.max())));
                inputs.put(field.key(), addRenderableWidget(box));
                if (mob) addRenderableWidget(Button.builder(Component.literal("Chọn"), b -> minecraft.gui.setScreen(new MobPicker(this, field)))
                    .bounds(x + column - 52, y, 42, 20).build());
            }
        }
        final int totalPages = pages;
        addRenderableWidget(Button.builder(Component.literal("←"), b -> {page = Math.max(0, page - 1); layout();})
            .bounds(left, height - 49, 28, 20).build()).active = page > 0;
        addRenderableWidget(Button.builder(Component.literal("→"), b -> {page = Math.min(totalPages - 1, page + 1); layout();})
            .bounds(left + 32, height - 49, 28, 20).build()).active = page + 1 < pages;
        addRenderableWidget(Button.builder(Component.literal("Nạp lại"), b -> {drafts.clear(); baseline = TikTokClient.runtimeSettings.deepCopy(); status = "Đã nạp cài đặt mới nhất"; layout();})
            .bounds(left + panel - 210, height - 49, 68, 20).build());
        save = addRenderableWidget(Button.builder(Component.literal("Lưu"), b -> submit()).bounds(left + panel - 138, height - 49, 64, 20).build());
        save.active = !waiting;
        addRenderableWidget(Button.builder(Component.literal("Đóng"), b -> onClose()).bounds(left + panel - 70, height - 49, 70, 20).build());
        if (waiting) children().stream().filter(Button.class::isInstance).map(Button.class::cast).forEach(b -> b.active = false);
    }
    private void submit() {
        if (waiting) return;
        try {
            JsonObject patch = new JsonObject();
            for (var field : RuntimeSettings.FIELDS) if (drafts.containsKey(field.key())) patch.add(field.key(), field.parse(drafts.get(field.key())));
            RuntimeSettings.merge(baseline, patch);
            if (patch.isEmpty()) { status = "Không có thay đổi"; return; }
            waiting = true; status = "Đang lưu…";
            pendingRequest = UUID.randomUUID().toString(); sentAt = System.nanoTime();
            GiftNetwork.CHANNEL.send(new GiftNetwork.SettingsPatch(pendingRequest, patch.toString()), PacketDistributor.SERVER.noArg());
            layout();
        } catch (Exception error) { waiting = false; pendingRequest = ""; status = error.getMessage(); layout(); }
    }
    void receive(JsonObject incoming) {
        baseline = incoming.deepCopy();
        filling = true;
        for (var field : visible) {
            EditBox box = inputs.get(field.key());
            if (!drafts.containsKey(field.key()) && (box == null || !box.isFocused())) {
                if (box != null) box.setValue(value(field));
                Button toggle = toggles.get(field.key());
                if (toggle != null) toggle.setMessage(Component.literal(Boolean.parseBoolean(value(field)) ? "Bật" : "Tắt"));
            }
        }
        filling = false;
    }
    void reply(GiftNetwork.SettingsReply reply) {
        if (!waiting || !pendingRequest.equals(reply.requestId())) return;
        waiting = false; status = reply.message();
        pendingRequest = "";
        if (reply.success()) { drafts.clear(); baseline = JsonParser.parseString(reply.json()).getAsJsonObject(); }
        layout();
    }
    @Override public void extractRenderState(GuiGraphicsExtractor g, int mx, int my, float partial) {
        g.fill(0, 0, width, height, 0xf00a121e);
        g.centeredText(font, title, width / 2, 8, 0xff55ffff);
        g.centeredText(font, "Đồng bộ hai chiều · Giới hạn riêng từng người", width / 2, 22, 0xffb2bdcc);
        int panel = Math.min(620, width - 16), left = (width - panel) / 2, column = panel / 2;
        for (int i = 0; i < visible.size(); i++)
            g.text(font, font.plainSubstrByWidth(visible.get(i).label(), column - 8), left + i % 2 * column, 68 + i / 2 * 42, 0xffb9d6ef);
        for (var widget : renderables) widget.extractRenderState(g, mx, my, partial);
        g.centeredText(font, font.plainSubstrByWidth(status, width - 16), width / 2, height - 20, 0xffffdb83);
        if (group == 0) g.text(font, (page + 1) + "/" + ((11 + perPage - 1) / perPage), left + 65, height - 43, 0xffcccccc);
    }
    @Override public void tick() {
        if (minecraft.level == null) { minecraft.gui.setScreen(null); return; }
        if (!waiting) receive(TikTokClient.runtimeSettings);
        if (waiting && System.nanoTime() - sentAt > 10_000_000_000L) {
            waiting = false; pendingRequest = "";
            status = "Chưa nhận xác nhận; Nạp lại để kiểm tra hoặc Lưu để thử lại";
            layout();
        }
    }
    @Override public void onClose() { minecraft.gui.setScreen(parent); }
    @Override public boolean isPauseScreen() { return false; }

    private static final class MobPicker extends Screen {
        private final RuntimeSettingsScreen owner;
        private final RuntimeSettings.Field field;
        private String query = "";
        private int page;
        private record MobChoice(String id, String label) {}
        private final List<MobChoice> all = new ArrayList<>();
        MobPicker(RuntimeSettingsScreen owner, RuntimeSettings.Field field) {
            super(Component.literal("Chọn mob")); this.owner = owner; this.field = field;
            BuiltInRegistries.ENTITY_TYPE.forEach(type -> {
                String id = BuiltInRegistries.ENTITY_TYPE.getKey(type).toString();
                if (type.getCategory() != MobCategory.MISC || SpawnEggItem.byId(type).isPresent() || id.endsWith(":iron_golem") || id.endsWith(":snow_golem"))
                    all.add(new MobChoice(id, type.getDescription().getString()));
            });
            all.sort(Comparator.comparing(MobChoice::label));
        }
        @Override protected void init() { layout(); }
        private void layout() {
            clearWidgets(); int left = Math.max(8, (width - 540) / 2), size = width - left * 2;
            EditBox search = new EditBox(font, left, 28, size, 20, Component.literal("Tìm tên hoặc ID mob"));
            search.setValue(query); search.setMaxLength(100);
            search.setResponder(text -> {query = text; page = 0; layout();});
            addRenderableWidget(search); setInitialFocus(search);
            var matches = all.stream().filter(m -> (m.label + " " + m.id).toLowerCase(Locale.ROOT).contains(query.toLowerCase(Locale.ROOT))).toList();
            int count = Math.max(1, (height - 90) / 24), pages = Math.max(1, (matches.size() + count - 1) / count);
            page = Math.min(page, pages - 1);
            for (int i = page * count; i < Math.min(matches.size(), (page + 1) * count); i++) {
                MobChoice choice = matches.get(i);
                Button b = addRenderableWidget(Button.builder(Component.literal(font.plainSubstrByWidth(choice.label + " — " + choice.id, size - 12)), ignored -> {
                    owner.edit(field, choice.id.startsWith("minecraft:") ? choice.id.substring(10) : choice.id);
                    minecraft.gui.setScreen(owner);
                }).bounds(left, 54 + (i % count) * 24, size, 20).build());
                b.setTooltip(Tooltip.create(Component.literal(choice.id)));
            }
            addRenderableWidget(Button.builder(Component.literal("←"), b -> {page--; layout();}).bounds(left, height - 27, 45, 20).build()).active = page > 0;
            addRenderableWidget(Button.builder(Component.literal("→"), b -> {page++; layout();}).bounds(left + 49, height - 27, 45, 20).build()).active = page + 1 < pages;
            addRenderableWidget(Button.builder(Component.literal("Quay lại"), b -> onClose()).bounds(left + size - 90, height - 27, 90, 20).build());
        }
        @Override public void extractRenderState(GuiGraphicsExtractor g, int mx, int my, float partial) {
            g.fill(0, 0, width, height, 0xf00a121e); g.centeredText(font, title, width / 2, 10, 0xff55ffff);
            for (var widget : renderables) widget.extractRenderState(g, mx, my, partial);
        }
        @Override public void onClose() { minecraft.gui.setScreen(owner); }
        @Override public boolean isPauseScreen() { return false; }
    }
}
