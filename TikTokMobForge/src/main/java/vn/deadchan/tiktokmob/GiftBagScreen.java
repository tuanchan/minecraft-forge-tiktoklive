package vn.deadchan.tiktokmob;

import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.Minecraft;
import net.minecraft.world.inventory.InventoryMenu;
import net.minecraft.world.inventory.Slot;
import net.minecraft.network.chat.Component;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.resources.Identifier;
import java.util.List;

final class GiftBagScreen extends AbstractContainerScreen<InventoryMenu> {
    private static final Identifier CHEST = Identifier.withDefaultNamespace("textures/gui/container/generic_54.png");
    private static final int ROWS = 5, PANEL_WIDTH = 176, PANEL_HEIGHT = ROWS * 18 + 114;
    private GiftNetwork.BagPage page = new GiftNetwork.BagPage(0, 1, 0, List.of());
    private boolean waiting;
    private boolean loaded;
    private int ticks;
    private final List<Slot> originalSlots;
    GiftBagScreen() {
        super(Minecraft.getInstance().player.inventoryMenu, Minecraft.getInstance().player.getInventory(),
            Component.literal("Túi quà TikTok"), PANEL_WIDTH, PANEL_HEIGHT);
        originalSlots = List.copyOf(menu.slots);
        for (int id = 0; id < menu.slots.size(); id++) {
            Slot original = originalSlots.get(id);
            boolean visible = id >= 9 && id < 45;
            int inventorySlot = original.getContainerSlot();
            int x = visible ? 8 + inventorySlot % 9 * 18 : -10000;
            int y = visible ? (inventorySlot < 9 ? ROWS * 18 + 89 : ROWS * 18 + 31 + (inventorySlot / 9 - 1) * 18) : -10000;
            Slot slot = new Slot(original.container, inventorySlot, x, y) {
                @Override public boolean isActive() { return visible; }
                @Override public boolean mayPlace(net.minecraft.world.item.ItemStack stack) { return original.mayPlace(stack); }
                @Override public boolean mayPickup(net.minecraft.world.entity.player.Player player) { return original.mayPickup(player); }
                @Override public void onTake(net.minecraft.world.entity.player.Player player, net.minecraft.world.item.ItemStack stack) { original.onTake(player, stack); }
                @Override public void setByPlayer(net.minecraft.world.item.ItemStack stack, net.minecraft.world.item.ItemStack previous) { original.setByPlayer(stack, previous); }
                @Override public int getMaxStackSize(net.minecraft.world.item.ItemStack stack) { return original.getMaxStackSize(stack); }
            };
            slot.index = id;
            menu.slots.set(id, slot);
        }
    }
    @Override protected void init() {
        super.init();
        topPos = Math.max(4, (height - 242) / 2);
        layout();
        request(page.page(), "");
    }
    @Override public void removed() {
        for (int i = 0; i < originalSlots.size(); i++) menu.slots.set(i, originalSlots.get(i));
        super.removed();
    }
    @Override protected void extractLabels(GuiGraphicsExtractor g, int mx, int my) {}
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
        Button previous = addRenderableWidget(Button.builder(Component.literal("←"), b -> request(page.page() - 1, ""))
            .bounds(left, top + PANEL_HEIGHT + 3, 30, 20).build());
        previous.active = page.page() > 0;
        Button next = addRenderableWidget(Button.builder(Component.literal("→"), b -> request(page.page() + 1, ""))
            .bounds(left + 146, top + PANEL_HEIGHT + 3, 30, 20).build());
        next.active = page.page() + 1 < page.pages();
        addRenderableWidget(Button.builder(Component.literal("Đóng"), b -> onClose()).bounds(left + 58, top + PANEL_HEIGHT + 3, 60, 20).build());
        // Item names are retained for narration; drawn slots use icons below.
    }
    @Override protected void containerTick() {
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

        for (int i = 0; i < 45; i++) {
            int x = left + 8 + i % 9 * 18, y = top + 18 + i / 9 * 18;
            boolean hovered = mx >= x && mx < x + 16 && my >= y && my < y + 16;
            if (hovered) g.fill(x, y, x + 16, y + 16, 0x80ffffff);
            if (i >= page.entries().size()) continue;
            var stack = page.entries().get(i).stack();
            g.item(stack, x, y); g.itemDecorations(font, stack, x, y);
            if (hovered) g.setTooltipForNextFrame(font, stack, mx, my);
        }
        super.extractRenderState(g, mx, my, partial);
        g.centeredText(font, page.total() + " vật phẩm · Bấm quà để lấy", width / 2, top + PANEL_HEIGHT + 27, 0xffffffff);
    }
    @Override public boolean mouseClicked(net.minecraft.client.input.MouseButtonEvent event, boolean doubleClick) {
        int x = (int)event.x() - leftPos - 8, y = (int)event.y() - topPos - 18;
        if (x >= 0 && x < 162 && y >= 0 && y < ROWS * 18) {
            int index = y / 18 * 9 + x / 18;
            if (event.button() == 0 && menu.getCarried().isEmpty() && index < page.entries().size())
                request(page.page(), page.entries().get(index).id());
            return true;
        }
        return super.mouseClicked(event, doubleClick);
    }
    @Override public boolean isPauseScreen() { return false; }
}
