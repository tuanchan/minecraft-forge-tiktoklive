package vn.deadchan.tiktokmob;

import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.resources.Identifier;
import java.util.List;

final class GiftBagScreen extends Screen {
    private static final Identifier CHEST = Identifier.withDefaultNamespace("textures/gui/container/generic_54.png");
    private static final int ROWS = 5, PANEL_WIDTH = 176, PANEL_HEIGHT = ROWS * 18 + 114;
    private GiftNetwork.BagPage page = new GiftNetwork.BagPage(0, 1, 0, List.of());
    private boolean waiting;
    private boolean loaded;
    private int ticks;
    GiftBagScreen() { super(Component.literal("Túi quà TikTok")); }
    @Override protected void init() {
        layout();
        request(page.page(), "");
    }
    private void request(int number, String id) {
        if (waiting) return;
        waiting = true;
        children().stream().filter(Button.class::isInstance).map(Button.class::cast).forEach(b -> b.active = false);
        GiftNetwork.request(number, id);
    }
    void update(GiftNetwork.BagPage value) {
        page = value; waiting = false; loaded = true; ticks = 0; layout();
    }
    private void layout() {
        clearWidgets();
        int left = (width - PANEL_WIDTH) / 2, top = Math.max(4, (height - 242) / 2);
        for (int i = 0; i < page.entries().size(); i++) {
            var entry = page.entries().get(i);
            addRenderableWidget(Button.builder(entry.stack().getHoverName(), ignored -> request(page.page(), entry.id()))
                .bounds(left + 8 + i % 9 * 18, top + 18 + i / 9 * 18, 16, 16).build());
        }
        Button previous = addRenderableWidget(Button.builder(Component.literal("←"), b -> request(page.page() - 1, ""))
            .bounds(left, top + PANEL_HEIGHT + 3, 30, 20).build());
        previous.active = page.page() > 0;
        Button next = addRenderableWidget(Button.builder(Component.literal("→"), b -> request(page.page() + 1, ""))
            .bounds(left + 146, top + PANEL_HEIGHT + 3, 30, 20).build());
        next.active = page.page() + 1 < page.pages();
        addRenderableWidget(Button.builder(Component.literal("Đóng"), b -> onClose()).bounds(left + 58, top + PANEL_HEIGHT + 3, 60, 20).build());
        // Item names are retained for narration; drawn slots use icons below.
    }
    @Override public void tick() {
        if (minecraft.player == null || !minecraft.player.isAlive()) { onClose(); return; }
        if (++ticks >= 40 && !waiting) request(page.page(), "");
    }
    @Override public void extractRenderState(GuiGraphicsExtractor g, int mx, int my, float partial) {
        int left = (width - PANEL_WIDTH) / 2, top = Math.max(4, (height - 242) / 2);
        // The same nine-column slots and player inventory texture as a vanilla chest.
        g.blit(RenderPipelines.GUI_TEXTURED, CHEST, left, top, 0, 0, PANEL_WIDTH, ROWS * 18 + 17, 256, 256);
        g.blit(RenderPipelines.GUI_TEXTURED, CHEST, left, top + ROWS * 18 + 17,
            0, 126, PANEL_WIDTH, 96, 256, 256);
        g.text(font, "Túi quà", left + 8, top + 6, 0xff404040, false);
        String pageLabel = loaded ? (page.page() + 1) + " / " + page.pages() : "…";
        g.text(font, pageLabel, left + 168 - font.width(pageLabel), top + 6, 0xff404040, false);
        g.text(font, "Túi đồ", left + 8, top + ROWS * 18 + 20, 0xff404040, false);
        // Draw only navigation buttons through the normal button renderer.
        for (int i = page.entries().size(); i < renderables.size(); i++) renderables.get(i).extractRenderState(g, mx, my, partial);
        for (int i = 0; i < 45; i++) {
            int x = left + 8 + i % 9 * 18, y = top + 18 + i / 9 * 18;
            boolean hovered = mx >= x && mx < x + 16 && my >= y && my < y + 16;
            if (hovered) g.fill(x, y, x + 16, y + 16, 0x80ffffff);
            if (i >= page.entries().size()) continue;
            var stack = page.entries().get(i).stack();
            g.item(stack, x, y); g.itemDecorations(font, stack, x, y);
            if (hovered) g.setTooltipForNextFrame(font, stack, mx, my);
        }
        if (minecraft.player != null) {
            for (int i = 0; i < 36; i++) {
                int x = left + 8 + i % 9 * 18;
                int y = top + (i < 9 ? ROWS * 18 + 89 : ROWS * 18 + 31 + (i / 9 - 1) * 18);
                var stack = minecraft.player.getInventory().getItem(i);
                g.item(stack, x, y); g.itemDecorations(font, stack, x, y);
                if (!stack.isEmpty() && mx >= x && mx < x + 16 && my >= y && my < y + 16)
                    g.setTooltipForNextFrame(font, stack, mx, my);
            }
        }
        g.centeredText(font, page.total() + " vật phẩm · Bấm quà để lấy", width / 2, top + PANEL_HEIGHT + 27, 0xffffffff);
    }
    @Override public void onClose() { minecraft.gui.setScreen(null); }
    @Override public boolean isPauseScreen() { return false; }
}
