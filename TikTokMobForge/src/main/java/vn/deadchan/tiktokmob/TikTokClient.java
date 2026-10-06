package vn.deadchan.tiktokmob;

import com.google.gson.Gson;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.Tooltip;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.client.renderer.RenderPipelines;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraftforge.client.event.AddGuiOverlayLayersEvent;
import net.minecraftforge.client.event.InputEvent;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.client.event.ScreenEvent;
import net.minecraftforge.client.gui.overlay.ForgeLayeredDraw;
import net.minecraftforge.event.TickEvent;
import org.lwjgl.glfw.GLFW;

final class TikTokClient {
    static final Identifier BAG_ICON = Identifier.fromNamespaceAndPath("tiktokmob", "textures/gui/iconbaggift.png");
    static final KeyMapping OPEN_BAG = new KeyMapping("key.tiktokmob.gift_bag", GLFW.GLFW_KEY_B, KeyMapping.Category.INVENTORY);
    static final KeyMapping OPEN_SETTINGS = new KeyMapping("key.tiktokmob.settings", GLFW.GLFW_KEY_F8, KeyMapping.Category.INVENTORY);
    static final KeyMapping GRAB_PIN = new KeyMapping("key.tiktokmob.pin_grab", GLFW.GLFW_KEY_G, KeyMapping.Category.INVENTORY);
    static final KeyMapping PIN_BOARD = new KeyMapping("key.tiktokmob.pin_board", GLFW.GLFW_KEY_F, KeyMapping.Category.INVENTORY);
    static final KeyMapping DELETE_PIN = new KeyMapping("key.tiktokmob.pin_delete", GLFW.GLFW_KEY_X, KeyMapping.Category.INVENTORY);
    static com.google.gson.JsonObject runtimeSettings = new com.google.gson.JsonObject();
    static TikTokMobMod.ModSettings settings = new TikTokMobMod.ModSettings();
    static long giftCount;
    static boolean connected;
    private static int skyCarrierId = -1;
    private static GiftNetwork.Notification notification;
    private static int age;
    private static int duration, fadeIn, fadeOut;

    static void initialize() {
        net.minecraftforge.client.event.EntityRenderersEvent.RegisterRenderers.BUS.addListener(event ->
            event.registerEntityRenderer(net.minecraft.world.entity.EntityTypes.TEXT_DISPLAY, WebBoardRenderer::new));
        GiftNetwork.onSkyRide = message -> {
            int previous = skyCarrierId;
            skyCarrierId = message.carrierId();
            var player = Minecraft.getInstance().player;
            if (skyCarrierId == -1 && player != null && player.getVehicle() != null
                    && player.getVehicle().getId() == previous) {
                // Unlock first, then dismount even if vanilla's passenger packet arrived earlier.
                player.stopRiding();
            }
        };
        net.minecraftforge.event.entity.EntityMountEvent.BUS.addListener(event ->
            event.getLevel().isClientSide() && event.isDismounting()
                && event.getEntityMounting() == Minecraft.getInstance().player
                && event.getEntityMounting().isAlive() && event.getEntityBeingMounted() != null
                && event.getEntityBeingMounted().getId() == skyCarrierId);
        GiftNetwork.onGiftAlert = message -> GiftAlertHud.load(message.token());
        GiftNetwork.onPinnedComment = PinnedCommentBoard::receive;
        GiftNetwork.onMissions = MissionHud::receive;
        InputEvent.MouseScrollingEvent.BUS.addListener((java.util.function.Predicate<InputEvent.MouseScrollingEvent>) event -> {
            var mc = Minecraft.getInstance();
            return mc.gui.screen() == null && GRAB_PIN.isDown() && PinnedCommentBoard.scroll(event.getDeltaY(),
                GLFW.glfwGetKey(mc.getWindow().handle(), GLFW.GLFW_KEY_LEFT_SHIFT) == GLFW.GLFW_PRESS
                || GLFW.glfwGetKey(mc.getWindow().handle(), GLFW.GLFW_KEY_RIGHT_SHIFT) == GLFW.GLFW_PRESS);
        });
        RegisterKeyMappingsEvent.BUS.addListener(event -> {
            event.register(OPEN_BAG); event.register(OPEN_SETTINGS); event.register(GRAB_PIN); event.register(PIN_BOARD); event.register(DELETE_PIN);
        });
        TickEvent.ClientTickEvent.Pre.BUS.addListener(event -> {
            var mc = Minecraft.getInstance();
            if (mc.level != null && mc.gui.screen() == null && PinnedCommentBoard.visible()
                && mc.options.keySwapOffhand.getKey().equals(PIN_BOARD.getKey())) {
                while (mc.options.keySwapOffhand.consumeClick()) { }
            }
        });
        AddGuiOverlayLayersEvent.BUS.addListener(event -> event.getLayeredDraw().add(
            ForgeLayeredDraw.POST_SLEEP_STACK, Identifier.fromNamespaceAndPath("tiktokmob", "hud"),
            (graphics, delta) -> renderHud(graphics)));
        TickEvent.ClientTickEvent.Post.BUS.addListener(event -> {
            var mc = Minecraft.getInstance();
            if (mc.level == null) { reset(); return; }
            GiftAlertHud.tick();
            WebBoardTexture.tick();
            try {
                boolean pinClicked = false;
                while (PIN_BOARD.consumeClick()) pinClicked = !pinClicked;
                PinnedCommentBoard.tick(mc, GRAB_PIN.isDown(), pinClicked);
                while (DELETE_PIN.consumeClick()) {
                    if (mc.gui.screen() == null && mc.player != null) GiftNetwork.deleteBoard();
                }
            } catch (RuntimeException error) {
                com.mojang.logging.LogUtils.getLogger().error("Không thể cập nhật bảng bình luận ghim", error);
                PinnedCommentBoard.reset();
            }
            while (OPEN_SETTINGS.consumeClick()) {
                if (connected && mc.player != null) mc.gui.setScreen(new RuntimeSettingsScreen(mc.gui.screen()));
            }
            if (notification != null && !mc.isPaused() && mc.player != null && mc.player.isAlive()) age++;
            while (OPEN_BAG.consumeClick()) {
                if (connected && mc.player != null && mc.player.isAlive() && mc.gui.screen() == null) openBag();
            }
        });
        ClientPlayerNetworkEvent.LoggingOut.BUS.addListener(event -> reset());
        ScreenEvent.Init.Post.BUS.addListener(event -> {
            if (event.getScreen() instanceof net.minecraft.client.gui.screens.PauseScreen || event.getScreen() instanceof InventoryScreen) {
                var screen = event.getScreen();
                Button settingsButton = Button.builder(Component.literal("TikTok · Cài đặt"), ignored -> Minecraft.getInstance().gui.setScreen(new RuntimeSettingsScreen(screen)))
                    .bounds(Math.max(4, screen.width - 126), 4, 122, 20).build();
                settingsButton.active = connected; event.addListener(settingsButton);
            }
            if (event.getScreen() instanceof InventoryScreen screen) {
                Button button = new Button(Math.max(4, screen.width - 34), Math.max(4, screen.height - 44),
                    28, 28, Component.literal("Túi quà"), ignored -> openBag(), supplier -> supplier.get()) {
                    @Override public void extractContents(GuiGraphicsExtractor g, int mx, int my, float partial) {
                        icon(g, getX() + 2, getY() + 2, 24);
                    }
                };
                button.setTooltip(Tooltip.create(Component.literal("Túi quà · Chỉ lấy ra · Không mất khi chết")));
                button.active = connected;
                event.addListener(button);
            }
        });
        GiftNetwork.onState = state -> {
            runtimeSettings = com.google.gson.JsonParser.parseString(state.settings()).getAsJsonObject();
            if (Minecraft.getInstance().gui.screen() instanceof RuntimeSettingsScreen screen) screen.receive(runtimeSettings);
            settings = new Gson().fromJson(state.settings(), TikTokMobMod.ModSettings.class);
            settings.sanitize(); giftCount = state.giftCount(); connected = true;
        };
        GiftNetwork.onSettingsReply = reply -> {
            if (reply.success()) runtimeSettings = com.google.gson.JsonParser.parseString(reply.json()).getAsJsonObject();
            if (Minecraft.getInstance().gui.screen() instanceof RuntimeSettingsScreen screen) screen.reply(reply);
        };
        GiftNetwork.onNotification = message -> {
            // Empty packets end the current HUD message; never add an empty chat line.
            if (!message.title().isEmpty() && settings.notification_enabled
                    && "chat".equals(settings.notification_display_modes.getOrDefault(message.kind(), "legacy"))) {
                int titleColor = Integer.parseInt((message.donation() ? settings.donation_notification_color : settings.notification_title_color).substring(1), 16);
                int nameColor = Integer.parseInt((message.donation() ? settings.donation_notification_color : settings.notification_username_color).substring(1), 16);
                var line = Component.empty();
                if (settings.notification_show_username && !message.username().isBlank())
                    line.append(Component.literal(message.username() + ": ").withStyle(s -> s.withColor(nameColor)));
                line.append(Component.literal(message.title()).withStyle(s -> s.withColor(titleColor).withBold(message.donation() && settings.donation_notification_bold)));
                Minecraft.getInstance().gui.hud.getChat().addClientSystemMessage(line);
                return;
            }
            notification = message.title().isEmpty() ? null : message;
            age = 0;
            duration = Math.max(1, (int)Math.round(20 * (message.donation()
                ? settings.donation_notification_duration_seconds : settings.notification_duration_seconds)));
            fadeIn = (int)Math.round(20 * settings.notification_fade_in_seconds);
            fadeOut = (int)Math.round(20 * settings.notification_fade_out_seconds);
        };
        GiftNetwork.onPage = page -> {
            giftCount = page.total();
            if (Minecraft.getInstance().gui.screen() instanceof GiftBagScreen screen) screen.update(page);
        };
    }
    private static void reset() { skyCarrierId = -1; connected = false; giftCount = 0; notification = null; GiftAlertHud.clear(); WebBoardTexture.clear(); PinnedCommentBoard.reset(); MissionHud.clear(); }
    static void openBag() {
        if (connected) {
            var minecraft = Minecraft.getInstance();
            if (minecraft.player == null) return;
            minecraft.player.closeContainer();
            minecraft.gui.setScreen(new GiftBagScreen());
        }
    }
    static void icon(GuiGraphicsExtractor g, int x, int y, int size) {
        // Full source image is sampled into the compact button; the asset is kept intact.
        g.blit(RenderPipelines.GUI_TEXTURED, BAG_ICON, x, y, 0, 0, size, size, 1254, 1254, 1254, 1254);
    }
    private static void renderHud(GuiGraphicsExtractor g) {
        var mc = Minecraft.getInstance();
        if (!connected || mc.player == null) return;
        GiftAlertHud.render(g);
        MissionHud.render(g);
        if (settings.show_death_counter) {
            int deaths = runtimeSettings.has("death_count") ? runtimeSettings.get("death_count").getAsInt() : 0;
            g.text(mc.font, "Số lần chết: " + deaths, 8, 8, 0xffffffff);
        }
        if (!mc.player.isAlive()) return;
        int x = g.guiWidth() - 34, y = g.guiHeight() - 44;
        icon(g, x, y, 26);
        g.text(mc.font, OPEN_BAG.getTranslatedKeyMessage(), x + 8, y - 9, 0xffe5d5aa);
        g.text(mc.font, giftCount > 999 ? "999+" : Long.toString(giftCount), x, y + 27, 0xffffd66b);
        if (notification == null || !settings.notification_enabled || age >= duration + fadeIn + fadeOut) return;
        String mode = settings.notification_display_modes.getOrDefault(notification.kind(), "legacy");
        if ("chat".equals(mode)) return;
        var position = settings.notification_positions.getOrDefault(notification.kind(), new TikTokMobMod.NotificationPosition());
        double positionX = "center".equals(mode) ? 50 : position.x;
        double positionY = "center".equals(mode) ? 50 : position.y;
        float opacity = fadeIn > 0 && age < fadeIn ? (float)age / fadeIn
            : fadeOut > 0 && age > fadeIn + duration ? (float)(duration + fadeIn + fadeOut - age) / fadeOut : 1;
        if (opacity <= 0.02) return;
        int alpha = Math.max(4, (int)(255 * opacity)) << 24;
        int titleColor = Integer.parseInt((notification.donation() ? settings.donation_notification_color : settings.notification_title_color).substring(1), 16);
        int nameColor = Integer.parseInt((notification.donation() ? settings.donation_notification_color : settings.notification_username_color).substring(1), 16);
        boolean bold = notification.donation() && settings.donation_notification_bold;
        Component title = Component.literal(notification.title()).withStyle(s -> s.withBold(bold));
        Component name = Component.literal(notification.username()).withStyle(s -> s.withBold(bold));
        int textWidth = Math.max(mc.font.width(title), settings.notification_show_username ? mc.font.width(name) : 0);
        float scale = (float)Math.min(position.scale, (g.guiWidth() - 16.0) / Math.max(1, textWidth));
        int boxWidth = textWidth + 12, boxHeight = settings.notification_show_username ? 32 : 20;
        float left = (float)((g.guiWidth() - boxWidth * scale) * positionX / 100);
        float top = (float)((g.guiHeight() - boxHeight * scale) * positionY / 100);
        g.pose().pushMatrix();
        g.pose().translate(Math.max(0, left), Math.max(0, top)); g.pose().scale(scale, scale);
        g.centeredText(mc.font, title, boxWidth / 2, 6, alpha | titleColor);
        if (settings.notification_show_username) g.centeredText(mc.font, name, boxWidth / 2, 19, alpha | nameColor);
        g.pose().popMatrix();
    }
}
