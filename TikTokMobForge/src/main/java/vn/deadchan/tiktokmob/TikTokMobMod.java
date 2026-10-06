package vn.deadchan.tiktokmob;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.mojang.logging.LogUtils;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.level.ClipContext;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.monster.piglin.PiglinBrute;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import org.slf4j.Logger;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.Base64;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

@Mod(TikTokMobMod.MOD_ID)
public final class TikTokMobMod {
    public static final String MOD_ID = "tiktokmob";
    private static final Logger LOGGER = LogUtils.getLogger();
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final Path CONFIG_PATH = Path.of("config", "tiktokmob.json");
    private static final ConcurrentLinkedQueue<Interaction> PENDING = new ConcurrentLinkedQueue<>();
    private static final ConcurrentLinkedQueue<Interaction> PENDING_DONATIONS = new ConcurrentLinkedQueue<>();
    private static final AtomicInteger PENDING_COUNT = new AtomicInteger();
    private static final AtomicBoolean BRIDGE_STARTED = new AtomicBoolean();
    private final Map<String, ArrayDeque<SpawnedMob>> mobsByUser = new HashMap<>();
    private final Map<ForcedChunkKey, ForcedChunkLease> forcedChunks = new HashMap<>();
    private final ArrayDeque<DisplayNotification> donationNotifications = new ArrayDeque<>();
    private final ArrayDeque<DisplayNotification> regularNotifications = new ArrayDeque<>();
    private record DeferredMob(UUID playerId, Interaction interaction, EntityType<?> type) {}
    private final ArrayDeque<DeferredMob> deferredMobs = new ArrayDeque<>();
    private int notificationTicksRemaining;
    private volatile ModSettings settings = new ModSettings();
    private String pinnedComment = "";
    private String pinnedAuthor = "";
    private byte[] pinnedAvatar = new byte[0];
    private java.nio.file.attribute.FileTime configModifiedAt;

    public TikTokMobMod(FMLJavaModLoadingContext context) {
        GiftNetwork.register();
        GiftNetwork.onBoardPosition = ServerPinnedCommentBoard::position;
        GiftNetwork.onBoardSelect = ServerPinnedCommentBoard::selectAimed;
        GiftNetwork.onBoardDelete = player -> {
            if (RuntimeSettings.canEdit(player)) ServerPinnedCommentBoard.deleteAimed(player);
        };
        GiftNetwork.onSettingsPatch = (player, patch) -> {
            try {
                RuntimeSettings.savePatch(CONFIG_PATH, com.google.gson.JsonParser.parseString(patch.json()).getAsJsonObject());
                reloadSettings(true);
                GiftNetwork.send(player, new GiftNetwork.SettingsReply(patch.requestId(), RuntimeSettings.snapshot(settings).toString(), "Đã lưu · GUI và LIVE tự đồng bộ", true));
            } catch (Exception error) {
                GiftNetwork.send(player, new GiftNetwork.SettingsReply(patch.requestId(), "{}", "Không lưu được: " + error.getMessage(), false));
            }
        };
        if (net.minecraftforge.fml.loading.FMLEnvironment.dist == net.minecraftforge.api.distmarker.Dist.CLIENT) {
            TikTokClient.initialize();
        }
        reloadSettings(true);
        TickEvent.ServerTickEvent.Post.BUS.addListener(this::onServerTick);
        net.minecraftforge.event.server.ServerStoppingEvent.BUS.addListener(event -> { ServerPinnedCommentBoard.clear(); LightningGift.clear(); });
        TrollEffects.register();
        SkyLaunch.register();
        GuardSummons.register();
        SummonedMeatDrops.register();
        Missions.register();
        GolemGuard.register(() -> settings);
        startBridgeOnce();
    }

    private String playerSettings(ServerPlayer player) {
        var json = RuntimeSettings.snapshot(settings);
        json.addProperty("death_count", player.getStats().getValue(net.minecraft.stats.Stats.CUSTOM.get(net.minecraft.stats.Stats.DEATHS)));
        return json.toString();
    }

    private void startBridgeOnce() {
        if (!BRIDGE_STARTED.compareAndSet(false, true)) {
            return;
        }

        Thread bridgeThread = new Thread(this::listenForTikTokEvents, "tiktokmob-bridge");
        bridgeThread.setDaemon(true);
        bridgeThread.start();
    }

    private void listenForTikTokEvents() {
        int bridgePort = settings.bridge_port;
        try (ServerSocket serverSocket = new ServerSocket(bridgePort, 50, InetAddress.getLoopbackAddress())) {
            LOGGER.info("TikTok Mob bridge đang nghe tại 127.0.0.1:{}", bridgePort);
            while (!Thread.currentThread().isInterrupted()) {
                try (Socket socket = serverSocket.accept();
                     BufferedReader reader = new BufferedReader(
                         new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        acceptLine(line, settings);
                    }
                } catch (Exception error) {
                    LOGGER.warn("Không đọc được sự kiện TikTok", error);
                }
            }
        } catch (Exception error) {
            LOGGER.error("Không thể mở cổng TikTok Mob {}", bridgePort, error);
        }
    }

    static void acceptLine(String line, ModSettings settings) {
        String[] fields = line.split("\\t", -1);
        if (fields.length < 3 || fields.length > 8) {
            return;
        }

        InteractionKind kind;
        try {
            kind = InteractionKind.valueOf(fields[0].trim().toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException ignored) {
            return;
        }

        String userKey;
        String displayName;
        String notification;
        String payload;
        boolean donation;
        try {
            userKey = new String(Base64.getDecoder().decode(fields[1]), StandardCharsets.UTF_8).trim();
            displayName = new String(Base64.getDecoder().decode(fields[2]), StandardCharsets.UTF_8).trim();
            notification = fields.length >= 4
                ? new String(Base64.getDecoder().decode(fields[3]), StandardCharsets.UTF_8).trim()
                : defaultNotification(kind);
            payload = fields.length >= 5
                ? new String(Base64.getDecoder().decode(fields[4]), StandardCharsets.UTF_8).trim()
                : "";
            donation = fields.length >= 6 && "donation".equalsIgnoreCase(fields[5].trim());
        } catch (IllegalArgumentException ignored) {
            return;
        }

        if (userKey.isEmpty()) {
            userKey = displayName;
        }
        userKey = userKey.toLowerCase(Locale.ROOT);
        if (userKey.length() > 128) {
            userKey = userKey.substring(0, 128);
        }
        if (displayName.isEmpty()) {
            displayName = "TikTok";
        }
        if (displayName.length() > 64) {
            displayName = displayName.substring(0, 64);
        }
        if (notification.length() > 96) {
            notification = notification.substring(0, 96);
        }

        if (PENDING_COUNT.incrementAndGet() > settings.max_pending_events) {
            PENDING_COUNT.decrementAndGet();
            LOGGER.warn("Hàng đợi đã đầy, bỏ qua sự kiện của {}", displayName);
            return;
        }
        String notificationKind = fields.length >= 7 ? fields[6].trim().toLowerCase(Locale.ROOT) : "";
        if (!List.of("like", "comment", "share", "follow", "view", "gift").contains(notificationKind)) {
            notificationKind = inferNotificationKind(kind, notification, donation);
        }
        byte[] avatar = new byte[0];
        if (kind == InteractionKind.PIN_COMMENT && fields.length == 8 && !fields[7].isEmpty()) {
            try {
                avatar = Base64.getDecoder().decode(fields[7]);
                if (avatar.length > 65_536) return;
            } catch (IllegalArgumentException ignored) { return; }
        }
        Interaction interaction = new Interaction(kind, userKey, displayName, notification, payload, donation, notificationKind, avatar);
        (donation && settings.donation_priority_enabled ? PENDING_DONATIONS : PENDING).offer(interaction);
    }

    private void onServerTick(TickEvent.ServerTickEvent.Post event) {
        ServerPinnedCommentBoard.tick(event.server(), settings);
        Missions.tick(event.server(), settings);
        TrollEffects.tick();
        SkyLaunch.tick(event.server());
        SpecialRewards.tickTnt(event.server());
        LightningGift.tick(event.server());
        int currentTick = event.server().getTickCount();
        if (currentTick % 20 == 0) {
            reloadSettings(false);
            enforceConfiguredMobLimits();
        }
        removeExpiredMobs(currentTick);

        List<ServerPlayer> players = event.server().getPlayerList().getPlayers();
        if (players.isEmpty()) {
            return;
        }
        for (ServerPlayer player : players) {
            SpecialRewards.applyPending(player);
        }

        if (currentTick % 20 == 0) {
            for (ServerPlayer player : players) {
                GiftNetwork.send(player, new GiftNetwork.UiState(playerSettings(player), GiftBagData.get(player).count(player)));
                ServerPinnedCommentBoard.sendState(player);
            }
        }
        if (currentTick % 20 == 0) {
            int attempts = Math.min(2, deferredMobs.size());
            for (int i = 0; i < attempts; i++) {
                DeferredMob waiting = deferredMobs.removeFirst();
                ServerPlayer owner = event.server().getPlayerList().getPlayer(waiting.playerId());
                if (!canReceiveInteractions(owner) || !trySpawnMob(owner, waiting.interaction(), currentTick, waiting.type())) {
                    deferredMobs.addLast(waiting);
                } else {
                    LOGGER.info("[TikTokSpawn] RETRY_SUCCESS user={}", waiting.interaction().userKey());
                }
            }
        }
        ServerPlayer target = players.get(0);
        if (!canReceiveInteractions(target)) {
            if (currentTick % 20 == 0) {
                for (var queue : List.of(PENDING_DONATIONS, PENDING)) {
                    for (Interaction waiting : queue) if (waiting.kind() == InteractionKind.GIFT_ALERT)
                        GiftDisplayFiles.paused(waiting.payload(), true);
                }
            }
            return;
        }
        for (int i = 0; i < settings.max_interactions_per_tick; i++) {
            // A previous action in this batch may have killed the player.
            Interaction interaction = pollPendingInteraction(canReceiveInteractions(target));
            if (interaction == null) {
                break;
            }
            handleInteraction(target, interaction, currentTick);
        }
        if (canReceiveInteractions(target)) updateNotificationDisplay(target);
    }

    private static boolean canReceiveInteractions(ServerPlayer player) {
        return player != null && player.isAlive() && !player.isRemoved() && !player.isSpectator();
    }

    static Interaction pollPendingInteraction(boolean ready) {
        if (!ready) return null;
        Interaction interaction = PENDING_DONATIONS.poll();
        if (interaction == null) interaction = PENDING.poll();
        if (interaction != null) PENDING_COUNT.decrementAndGet();
        return interaction;
    }

    private void handleInteraction(ServerPlayer player, Interaction interaction, int currentTick) {
        if (interaction.kind() == InteractionKind.PIN_COMMENT) {
            String text = interaction.payload();
            if (text.isBlank()) return; // Only an aimed X request deletes a world board.
            pinnedComment = text.substring(0, text.offsetByCodePoints(0,
                Math.min(200, text.codePointCount(0, text.length()))));
            pinnedAuthor = pinnedComment.isEmpty() ? "" : interaction.displayName();
            pinnedAvatar = pinnedComment.isEmpty() ? new byte[0] : interaction.avatarPng();
            ServerPinnedCommentBoard.add(player.level().getServer(), pinnedAuthor, pinnedComment, pinnedAvatar, settings);
            LOGGER.info("Pinned comment added: avatar={} bytes", pinnedAvatar.length);
            return;
        }
        if (interaction.kind() == InteractionKind.GIFT_ALERT) {
            GiftDisplayFiles.paused(interaction.payload(), false);
            if (interaction.payload().matches("[a-f0-9]{32}"))
                GiftNetwork.send(player, new GiftNetwork.GiftAlert(interaction.payload()));
            return;
        }
        enqueueNotification(interaction);
        switch (interaction.kind()) {
            case MISSION_PENALTY -> Missions.penalty(player, interaction.payload());
            case TROLL_CHICKEN, TROLL_COBWEB, TROLL_PUMPKIN, TROLL_SLOWNESS,
                 TROLL_TELEPORT, TROLL_CREEPER, TROLL_ANVIL, TROLL_HOTBAR, TROLL_WARDEN, TROLL_BOX ->
                TrollEffects.apply(interaction.kind().name(), player, interaction.payload(),
                    type -> spawnMobOfType(player, interaction, currentTick, type),
                    stack -> giveItem(player, stack));
            case ENCHANT_ARMOR -> SpecialRewards.enchant(player, true, interaction.payload());
            case ENCHANT_WEAPON -> SpecialRewards.enchant(player, false, interaction.payload());
            case REPAIR_ARMOR -> SpecialRewards.repair(player, true);
            case REPAIR_HAND -> SpecialRewards.repair(player, false);
            case CLEAR_INVENTORY -> SpecialRewards.clearInventory(player);
            case KEEP_INVENTORY_ON -> SpecialRewards.keepInventory(player, true);
            case KEEP_INVENTORY_OFF -> SpecialRewards.keepInventory(player, false);
            case SET_RESPAWN -> SpecialRewards.setRespawn(player);
            case KILL_PLAYER -> player.kill(player.level());
            case SKY_LAUNCH -> SkyLaunch.start(player, interaction.payload());
            case SPAWN_TNT -> SpecialRewards.spawnTnt(player, interaction.payload());
            case LIGHTNING_PLAYER -> LightningGift.start(player, interaction.payload());
            case CLEAR_TOOL_MOBS -> ClearToolMobs.kill(player.level().getServer(), interaction.displayName());
            case ARMORED_WOLF -> spawnMobOfType(player, interaction, currentTick, EntityTypes.WOLF);
            case DIVINE_CAT -> spawnMobOfType(player, interaction, currentTick, EntityTypes.CAT);
            case NETHERITE_ARMOR_FULL4, DIAMOND_ARMOR_FULL4 ->
                SpecialRewards.enchantedArmorSet(player.registryAccess(), interaction.kind() == InteractionKind.NETHERITE_ARMOR_FULL4)
                    .forEach(stack -> giveItem(player, stack));
            case FULL_HEAL -> { player.setHealth(player.getMaxHealth()); player.getFoodData().eat(20, 1.0F); }
            case EXPERIENCE -> player.giveExperienceLevels(rewardLevel(interaction.payload()));
            case NOTIFICATION -> {
            }
            case ABSORPTION -> addGoldenHeart(player);
            case GOLDEN_APPLE -> giveItem(player, new ItemStack(Items.GOLDEN_APPLE));
            case REGENERATION -> player.addEffect(
                new MobEffectInstance(MobEffects.REGENERATION, secondsToTicks(settings.effect_duration_seconds), 0));
            case SHIELD -> giveItem(player, new ItemStack(Items.SHIELD));
            case MONEY_GUN -> {
                giveItem(player, new ItemStack(Items.BOW));
                giveItem(player, new ItemStack(Items.ARROW, settings.money_gun_arrow_count));
            }
            case DIAMOND_SWORD -> giveItem(player, new ItemStack(Items.DIAMOND_SWORD));
            case DIAMOND_ARMOR -> giveArmorSet(
                player,
                Items.DIAMOND_HELMET,
                Items.DIAMOND_CHESTPLATE,
                Items.DIAMOND_LEGGINGS,
                Items.DIAMOND_BOOTS);
            case IRON_ARMOR -> giveArmorSet(
                player,
                Items.IRON_HELMET,
                Items.IRON_CHESTPLATE,
                Items.IRON_LEGGINGS,
                Items.IRON_BOOTS);
            case NETHERITE_ARMOR -> giveArmorSet(
                player,
                Items.NETHERITE_HELMET,
                Items.NETHERITE_CHESTPLATE,
                Items.NETHERITE_LEGGINGS,
                Items.NETHERITE_BOOTS);
            case NETHERITE_POWER -> {
                giveArmorSet(
                    player,
                    Items.NETHERITE_HELMET,
                    Items.NETHERITE_CHESTPLATE,
                    Items.NETHERITE_LEGGINGS,
                    Items.NETHERITE_BOOTS);
                addUniverseBuffs(player);
            }
            case ITEM -> giveConfiguredItem(player, interaction);
            case MOB -> spawnConfiguredMob(player, interaction, currentTick);
            case CREEPER, ZOMBIE, SKELETON, ENDERMAN -> spawnMob(player, interaction, currentTick);
        }
    }

    private void enqueueNotification(Interaction interaction) {
        if (!settings.notification_enabled || interaction.notification().isEmpty()) {
            return;
        }

        int queued = donationNotifications.size() + regularNotifications.size();
        if (queued >= settings.notification_queue_size) {
            if (settings.donation_priority_enabled && interaction.donation() && !regularNotifications.isEmpty()) {
                DisplayNotification displaced = regularNotifications.removeLast();
                LOGGER.info(
                    "[TikTokMobDisplay] PRIORITY user={} replaced_regular_user={}",
                    interaction.userKey(),
                    displaced.userKey());
            } else if ("drop_oldest".equals(settings.notification_overflow_policy)
                && (!settings.donation_priority_enabled || !regularNotifications.isEmpty() || interaction.donation())) {
                DisplayNotification removed = regularNotifications.isEmpty()
                    ? donationNotifications.removeFirst() : regularNotifications.removeFirst();
                LOGGER.info("[TikTokMobDisplay] DROP_OLDEST user={}", removed.userKey());
            } else {
                LOGGER.warn(
                    "[TikTokMobDisplay] QUEUE_FULL drop user={} donation={} queued={}/{}",
                    interaction.userKey(),
                    interaction.donation(),
                    queued,
                    settings.notification_queue_size);
                return;
            }
        }

        DisplayNotification display = new DisplayNotification(
            interaction.userKey(),
            interaction.displayName(),
            interaction.notification(),
            interaction.donation(), interaction.notificationKind());
        (interaction.donation() && settings.donation_priority_enabled
            ? donationNotifications : regularNotifications).addLast(display);
        LOGGER.info(
            "[TikTokMobDisplay] ENQUEUE user={} donation={} priority_waiting={} regular_waiting={}",
            interaction.userKey(),
            interaction.donation(),
            donationNotifications.size(),
            regularNotifications.size());
    }

    private void updateNotificationDisplay(ServerPlayer player) {
        if (!settings.notification_enabled) {
            donationNotifications.clear();
            regularNotifications.clear();
            if (notificationTicksRemaining > 0) {
                GiftNetwork.send(player, new GiftNetwork.Notification("", "", "comment", false));
            }
            notificationTicksRemaining = 0;
            return;
        }
        if (notificationTicksRemaining > 0 && --notificationTicksRemaining > 0) {
            return;
        }

        DisplayNotification display = donationNotifications.pollFirst();
        if (display == null) {
            display = regularNotifications.pollFirst();
        }
        if (display == null) {
            return;
        }

        double durationSeconds = display.donation()
            ? settings.donation_notification_duration_seconds
            : settings.notification_duration_seconds;
        int stayTicks = secondsToTicks(durationSeconds);
        int fadeInTicks = (int) Math.round(settings.notification_fade_in_seconds * 20);
        int fadeOutTicks = (int) Math.round(settings.notification_fade_out_seconds * 20);
        notificationTicksRemaining = fadeInTicks + stayTicks + fadeOutTicks
            + (int) Math.round(settings.notification_gap_seconds * 20);
        GiftNetwork.send(player, new GiftNetwork.UiState(playerSettings(player), GiftBagData.get(player).count(player)));
        GiftNetwork.send(player, new GiftNetwork.Notification(display.notification(), display.displayName(),
            display.notificationKind(), display.donation()));
        LOGGER.info(
            "[TikTokMobDisplay] SHOW user={} donation={} duration={}s priority_waiting={} regular_waiting={}",
            display.userKey(),
            display.donation(),
            durationSeconds,
            donationNotifications.size(),
            regularNotifications.size());
    }

    private static String defaultNotification(InteractionKind kind) {
        return switch (kind) {
            case MISSION_PENALTY -> "Trừ tiến độ nhiệm vụ";
            case PIN_COMMENT -> "";
            case TROLL_CHICKEN, TROLL_COBWEB, TROLL_PUMPKIN, TROLL_SLOWNESS,
                 TROLL_TELEPORT, TROLL_CREEPER, TROLL_ANVIL, TROLL_HOTBAR, TROLL_WARDEN, TROLL_BOX -> "Quà chơi khăm";
            case CLEAR_INVENTORY -> "Clear sạch đồ người chơi";
            case KEEP_INVENTORY_ON -> "Bật keep đồ khi chết";
            case KEEP_INVENTORY_OFF -> "Tắt keep đồ khi chết";
            case SET_RESPAWN -> "Đặt điểm hồi sinh";
            case KILL_PLAYER -> "Giết người chơi";
            case SKY_LAUNCH -> "Bay thẳng lên trời";
            case SPAWN_TNT -> "TNT đã châm ngòi";
            case LIGHTNING_PLAYER -> "Sấm sét vào người chơi";
            case CLEAR_TOOL_MOBS -> "Dọn quái được tool triệu hồi";
            case ARMORED_WOLF -> "Chó sói giáp bảo vệ";
            case DIVINE_CAT -> "Mèo thần 200 máu · đuổi Creeper";
            case NETHERITE_ARMOR_FULL4 -> "Bộ giáp Netherite FULL enchant IV";
            case DIAMOND_ARMOR_FULL4 -> "Bộ giáp kim cương FULL enchant IV";
            case ENCHANT_ARMOR, ENCHANT_WEAPON, REPAIR_ARMOR, REPAIR_HAND, FULL_HEAL, EXPERIENCE -> "Quà đặc biệt";
            case NOTIFICATION, GIFT_ALERT -> "";
            case CREEPER -> "+ Follow";
            case ZOMBIE -> "Comment";
            case SKELETON -> "+ Like";
            case ENDERMAN -> "+ Share";
            case ABSORPTION -> "Gift: Rose";
            case GOLDEN_APPLE -> "Gift: Donut";
            case REGENERATION -> "Gift: Perfume";
            case SHIELD -> "Gift: Cap";
            case MONEY_GUN -> "Gift: Money Gun";
            case DIAMOND_SWORD -> "Gift: Galaxy";
            case DIAMOND_ARMOR -> "Gift: Lion";
            case IRON_ARMOR -> "Gift: Full Iron Armor";
            case NETHERITE_ARMOR -> "Gift: Full Netherite Armor";
            case NETHERITE_POWER -> "Gift: Universe";
            case ITEM -> "Gift: Item";
            case MOB -> "Gift: Mob";
        };
    }

    private void addGoldenHeart(ServerPlayer player) {
        AttributeInstance maxAbsorption = player.getAttribute(Attributes.MAX_ABSORPTION);
        if (maxAbsorption == null) {
            LOGGER.warn("Không tìm thấy thuộc tính MAX_ABSORPTION của {}", player.getName().getString());
            return;
        }

        float absorptionPoints = (float) (settings.absorption_hearts_per_rose * 2.0);
        maxAbsorption.setBaseValue(maxAbsorption.getBaseValue() + absorptionPoints);
        player.setAbsorptionAmount(player.getAbsorptionAmount() + absorptionPoints);
        player.sendSystemMessage(Component.literal("Hoa Hồng: +"
            + settings.absorption_hearts_per_rose
            + " tim vàng (hiện có "
            + (int) (player.getAbsorptionAmount() / 2.0F)
            + " tim vàng)"));
    }

    private void giveArmorSet(
        ServerPlayer player,
        net.minecraft.world.item.Item helmet,
        net.minecraft.world.item.Item chestplate,
        net.minecraft.world.item.Item leggings,
        net.minecraft.world.item.Item boots
    ) {
        giveItem(player, new ItemStack(helmet));
        giveItem(player, new ItemStack(chestplate));
        giveItem(player, new ItemStack(leggings));
        giveItem(player, new ItemStack(boots));
    }

    private void giveItem(ServerPlayer player, ItemStack stack) {
        GiftBagData.get(player).deposit(player, stack);
        LOGGER.info("[TikTokGiftBag] DEPOSIT player={} item={} count={}", player.getUUID(), stack.getItem(), stack.getCount());
    }

    private void addUniverseBuffs(ServerPlayer player) {
        int duration = secondsToTicks(settings.effect_duration_seconds);
        int amplifier = settings.universe_effect_level - 1;
        player.addEffect(new MobEffectInstance(MobEffects.STRENGTH, duration, amplifier));
        player.addEffect(new MobEffectInstance(MobEffects.RESISTANCE, duration, amplifier));
        player.addEffect(new MobEffectInstance(MobEffects.SPEED, duration, amplifier));
        player.addEffect(new MobEffectInstance(MobEffects.REGENERATION, duration, amplifier));
    }

    private void giveConfiguredItem(ServerPlayer player, Interaction interaction) {
        Identifier identifier = Identifier.tryParse(interaction.payload());
        if (identifier == null || !BuiltInRegistries.ITEM.containsKey(identifier)) {
            LOGGER.warn("Vật phẩm cấu hình không hợp lệ: {}", interaction.payload());
            player.sendSystemMessage(Component.literal(
                "TikTok Mob: vật phẩm không hợp lệ " + interaction.payload()));
            return;
        }
        Item item = BuiltInRegistries.ITEM.getValue(identifier);
        giveItem(player, new ItemStack(item));
        LOGGER.info("[TikTokMobReward] GIVE_ITEM user={} item={}", interaction.userKey(), identifier);
    }

    private void spawnConfiguredMob(ServerPlayer player, Interaction interaction, int currentTick) {
        Identifier identifier = Identifier.tryParse(RewardOptions.mobId(interaction.payload()));
        if (identifier == null || !BuiltInRegistries.ENTITY_TYPE.containsKey(identifier)) {
            LOGGER.warn("Mob cấu hình không hợp lệ: {}", interaction.payload());
            player.sendSystemMessage(Component.literal(
                "TikTok Mob: mob không hợp lệ " + interaction.payload()));
            return;
        }
        spawnMobOfType(
            player,
            interaction,
            currentTick,
            BuiltInRegistries.ENTITY_TYPE.getValue(identifier));
    }

    private void spawnMob(ServerPlayer player, Interaction interaction, int currentTick) {
        EntityType<? extends Mob> type = switch (interaction.kind()) {
            case CREEPER -> EntityTypes.CREEPER;
            case ZOMBIE -> EntityTypes.ZOMBIE;
            case SKELETON -> EntityTypes.SKELETON;
            case ENDERMAN -> EntityTypes.ENDERMAN;
            default ->
                throw new IllegalStateException(interaction.kind() + " is not a mob interaction");
        };

        spawnMobOfType(player, interaction, currentTick, type);
    }

    private void spawnMobOfType(ServerPlayer player, Interaction interaction, int currentTick, EntityType<?> type) {
        if (trySpawnMob(player, interaction, currentTick, type)) return;
        if (deferredMobs.size() >= settings.max_pending_events) {
            LOGGER.warn("[TikTokSpawn] RETRY_QUEUE_FULL user={}", interaction.userKey());
            player.sendSystemMessage(Component.literal("TikTok Mob: hàng chờ spawn đã đầy; hãy ra chỗ thoáng hoặc tăng giới hạn hàng đợi."));
            return;
        }
        deferredMobs.addLast(new DeferredMob(player.getUUID(), interaction, type));
        LOGGER.info("[TikTokSpawn] WAIT_FOR_SPACE user={} queued={}", interaction.userKey(), deferredMobs.size());
    }

    private boolean trySpawnMob(
        ServerPlayer player,
        Interaction interaction,
        int currentTick,
        EntityType<?> type
    ) {
        ServerLevel level = player.level();

        Entity createdEntity = type.create(level, EntitySpawnReason.EVENT);
        if (!(createdEntity instanceof Mob mob)) {
            if (createdEntity != null) {
                createdEntity.discard();
            }
            LOGGER.warn("Entity cấu hình không phải mob sống: {}", interaction.payload());
            return true;
        }

        boolean fallback = player.isInWater() || !placeInFront(player, mob);
        if (fallback) mob.snapTo(player.getX(), player.getY(), player.getZ(), player.getYRot(), 0);
        mob.finalizeSpawn(level, level.getCurrentDifficultyAt(mob.blockPosition()), EntitySpawnReason.EVENT, null);
        TrollEffects.markToolMob(mob, interaction.payload());
        GolemGuard.markSummoned(mob);
        GolemGuard.mark(mob, player);
        if (interaction.kind() == InteractionKind.ARMORED_WOLF) GolemGuard.markWolf(mob, player);
        if (interaction.kind() == InteractionKind.DIVINE_CAT) GolemGuard.markCat(mob, player);
        if (interaction.donation()) mob.addTag("tiktokmob:donation");
        if (interaction.donation() && mob instanceof net.minecraft.world.entity.animal.wolf.Wolf
                && !GolemGuard.isGuard(mob)) GolemGuard.markWolf(mob, player);
        if (!fallback && !level.noCollision(mob, mob.getBoundingBox())) {
            mob.snapTo(player.getX(), player.getY(), player.getZ(), player.getYRot(), 0);
        }
        // Only gift-summoned brutes: vanilla mobs and other TikTok interactions keep normal conversion.
        if (interaction.donation() && mob instanceof PiglinBrute brute) {
            brute.setImmuneToZombification(true);
        }
        if (type == EntityTypes.ENDERMAN && settings.enderman_targets_player) {
            mob.setTarget(player);
        }
        int lifetimeTicks = secondsToTicks(settings.mob_lifetime_seconds);
        updateMobName(mob, interaction.displayName(), lifetimeTicks);
        mob.setCustomNameVisible(true);
        if (settings.mobs_persistent || interaction.donation()) {
            mob.setPersistenceRequired();
        }
        if (level.addFreshEntity(mob)) {
            GuardSummons.donated(player, mob);
            trackMob(interaction.userKey(), interaction.displayName(), player.getUUID(), mob, currentTick);
            return true;
        }
        mob.discard();
        return false;
    }

    private boolean placeInFront(ServerPlayer player, Mob mob) {
        ServerLevel level = player.level();
        double turn = switch (settings.spawn_direction) {
            case "right" -> 90;
            case "left" -> -90;
            case "back" -> 180;
            case "random" -> player.getRandom().nextDouble() * 360;
            default -> 0;
        };
        double yaw = Math.toRadians(player.getYRot() + turn);
        double min = Math.max(settings.spawn_min_distance, 1.5 + mob.getBbWidth() / 2.0);
        double max = Math.max(min, settings.spawn_max_distance);
        // Search the forward cone only, preferring the centre before either side.
        for (int angle : new int[] {0, 15, -15, 30, -30, 45, -45, 60, -60}) {
            double direction = yaw + Math.toRadians(angle);
            for (double distance = min; distance <= max + 0.01; distance += 0.5) {
                double x = player.getX() - Math.sin(direction) * distance;
                double z = player.getZ() + Math.cos(direction) * distance;
                int baseY = (int)Math.floor(player.getY() + settings.spawn_height_offset);
                for (int offset : new int[] {0, 1, -1, 2, -2, 3, -3, 4, -4}) {
                    BlockPos floor = BlockPos.containing(x, baseY + offset - 1, z);
                    if (!level.hasChunkAt(floor) || !level.getFluidState(floor).isEmpty()
                        || !level.getBlockState(floor).isFaceSturdy(level, floor, Direction.UP)) continue;
                    double y = floor.getY() + 1;
                    mob.snapTo(x, y, z, player.getYRot() + 180, 0);
                    var box = mob.getBoundingBox();
                    if (!level.getWorldBorder().isWithinBounds(box)
                        || !level.noCollision(mob, box) || level.containsAnyLiquid(box)
                        || !level.getEntities(mob, box).isEmpty()) continue;
                    // Do not place beyond a wall just because the far side is empty.
                    Vec3 target = new Vec3(x, y + Math.min(mob.getBbHeight() * 0.5, 1.0), z);
                    if (level.clip(new ClipContext(player.getEyePosition(), target,
                            ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, player)).getType()
                            != HitResult.Type.MISS) continue;
                    LOGGER.info("[TikTokSpawn] SAFE_FRONT x={} y={} z={} angle={}", x, y, z, angle);
                    return true;
                }
            }
        }
        return false;
    }

    private boolean placeNearby(ServerPlayer player, Mob mob) {
        ServerLevel level = player.level();
        // Prefer nearby ground in every direction when the forward cone is blocked.
        double yaw = Math.toRadians(player.getYRot());
        double max = Math.min(16, Math.max(8, settings.spawn_max_distance));
        for (double distance = Math.max(1, mob.getBbWidth()); distance <= max; distance += 1) {
            for (int angle = 0; angle < 360; angle += 30) {
                double direction = yaw + Math.toRadians(angle);
                double x = player.getX() - Math.sin(direction) * distance;
                double z = player.getZ() + Math.cos(direction) * distance;
                for (int offset : new int[] {0, 1, -1, 2, -2, 3, -3, 4, -4, 6, -6, 8, -8}) {
                    BlockPos floor = BlockPos.containing(x, player.getY() + offset - 1, z);
                    if (!level.hasChunkAt(floor) || !level.getFluidState(floor).isEmpty()
                        || !level.getBlockState(floor).isFaceSturdy(level, floor, Direction.UP)) continue;
                    mob.snapTo(x, floor.getY() + 1, z, player.getYRot() + 180, 0);
                    var box = mob.getBoundingBox();
                    if (!level.getWorldBorder().isWithinBounds(box) || !level.noCollision(mob, box)
                        || level.containsAnyLiquid(box) || !level.getEntities(mob, box).isEmpty()) continue;
                    LOGGER.info("[TikTokSpawn] SAFE_NEARBY x={} y={} z={}", x, floor.getY() + 1, z);
                    return true;
                }
            }
        }
        return false;
    }

    private void trackMob(String userKey, String displayName, UUID playerId, Mob mob, int currentTick) {
        ArrayDeque<SpawnedMob> userMobs = mobsByUser.computeIfAbsent(userKey, ignored -> new ArrayDeque<>());
        removeMissingMobs(userMobs);
        ForcedChunkKey chunk = chunkOf(mob);
        acquireChunk(chunk);
        SpawnedMob spawnedMob = new SpawnedMob(
            mob,
            mob.entityTags().contains("tiktokmob:donation") ? Long.MAX_VALUE : System.currentTimeMillis() + Math.round(settings.mob_lifetime_seconds * 1_000.0),
            System.currentTimeMillis(),
            displayName,
            playerId,
            chunk);
        userMobs.addLast(spawnedMob);
        LOGGER.info(
            "[TikTokMobLimit] SPAWN user={} mob={} active_before_limit={}",
            userKey,
            displayName,
            userMobs.size());

        while (limitedCount(userMobs) > settings.max_mobs_per_user) {
            SpawnedMob removedMob = firstLimited(userMobs);
            userMobs.remove(removedMob);
            discardTrackedMob(removedMob);
            LOGGER.info(
                "[TikTokMobLimit] DESPAWN_OLDEST user={} mob={} reason=limit_exceeded active_after={}",
                userKey,
                removedMob.displayName(),
                userMobs.size());
        }
        enforceGlobalMobLimit();
        LOGGER.info(
            "[TikTokMobLimit] RESULT user={} active={}/{} global={}/{}",
            userKey,
            userMobs.size(),
            settings.max_mobs_per_user,
            activeMobCount(),
            settings.max_mobs_total);
    }

    private void removeExpiredMobs(int currentTick) {
        long now = System.currentTimeMillis();
        Iterator<Map.Entry<String, ArrayDeque<SpawnedMob>>> users = mobsByUser.entrySet().iterator();
        while (users.hasNext()) {
            Map.Entry<String, ArrayDeque<SpawnedMob>> entry = users.next();
            ArrayDeque<SpawnedMob> userMobs = entry.getValue();
            Iterator<SpawnedMob> mobs = userMobs.iterator();
            while (mobs.hasNext()) {
                SpawnedMob spawnedMob = mobs.next();
                if (spawnedMob.mob().isRemoved()) {
                    releaseChunk(spawnedMob.forcedChunk());
                    mobs.remove();
                    continue;
                }
                if (now >= spawnedMob.expiresAtMillis()) {
                    discardTrackedMob(spawnedMob);
                    LOGGER.info(
                        "[TikTokMobLimit] DESPAWN_EXPIRED user={} mob={} reason=lifetime_finished",
                        entry.getKey(),
                        spawnedMob.displayName());
                    mobs.remove();
                    continue;
                }
                if (currentTick % 20 == 0) {
                    GolemGuard.markSummoned(spawnedMob.mob());
                    keepMobChunkActive(spawnedMob);
                    ServerPlayer target = spawnedMob.forcedChunk().level().getServer().getPlayerList().getPlayer(spawnedMob.playerId());
                    if (target != null && target.isAlive()) {
                        if (!GolemGuard.isGuard(spawnedMob.mob()) && GolemGuard.canHarmPlayer(spawnedMob.mob()))
                            spawnedMob.mob().setTarget(target);
                    }
                    double remainingSeconds = Math.max(
                        0.0,
                        (spawnedMob.expiresAtMillis() - now) / 1_000.0);
                    updateMobName(
                        spawnedMob.mob(),
                        spawnedMob.displayName(),
                        secondsToTicks(remainingSeconds));
                }
            }
            if (userMobs.isEmpty()) {
                users.remove();
            }
        }
    }

    private void removeMissingMobs(ArrayDeque<SpawnedMob> mobs) {
        Iterator<SpawnedMob> iterator = mobs.iterator();
        while (iterator.hasNext()) {
            SpawnedMob spawned = iterator.next();
            if (spawned.mob().isRemoved()) {
                releaseChunk(spawned.forcedChunk());
                iterator.remove();
            }
        }
    }

    private static int limitedCount(ArrayDeque<SpawnedMob> mobs) {
        return (int) mobs.stream().filter(m -> m.expiresAtMillis() != Long.MAX_VALUE).count();
    }

    private static SpawnedMob firstLimited(ArrayDeque<SpawnedMob> mobs) {
        return mobs.stream().filter(m -> m.expiresAtMillis() != Long.MAX_VALUE).findFirst().orElse(null);
    }

    private int activeMobCount() {
        return mobsByUser.values().stream().mapToInt(TikTokMobMod::limitedCount).sum();
    }

    private void enforceGlobalMobLimit() {
        while (activeMobCount() > settings.max_mobs_total) {
            Map.Entry<String, ArrayDeque<SpawnedMob>> oldestOwner = null;
            SpawnedMob oldest = null;
            for (Map.Entry<String, ArrayDeque<SpawnedMob>> entry : mobsByUser.entrySet()) {
                SpawnedMob candidate = firstLimited(entry.getValue());
                if (candidate != null && (oldest == null || candidate.spawnedAtMillis() < oldest.spawnedAtMillis())) {
                    oldest = candidate;
                    oldestOwner = entry;
                }
            }
            if (oldest == null || oldestOwner == null) {
                return;
            }
            oldestOwner.getValue().remove(oldest);
            discardTrackedMob(oldest);
            LOGGER.info(
                "[TikTokMobLimit] DESPAWN_OLDEST user={} mob={} reason=global_limit active_after={}",
                oldestOwner.getKey(),
                oldest.displayName(),
                activeMobCount());
            if (oldestOwner.getValue().isEmpty()) {
                mobsByUser.remove(oldestOwner.getKey());
            }
        }
    }

    private void enforceConfiguredMobLimits() {
        Iterator<Map.Entry<String, ArrayDeque<SpawnedMob>>> users = mobsByUser.entrySet().iterator();
        while (users.hasNext()) {
            Map.Entry<String, ArrayDeque<SpawnedMob>> entry = users.next();
            ArrayDeque<SpawnedMob> mobs = entry.getValue();
            removeMissingMobs(mobs);
            while (limitedCount(mobs) > settings.max_mobs_per_user) {
                SpawnedMob removed = firstLimited(mobs);
                mobs.remove(removed);
                discardTrackedMob(removed);
                LOGGER.info(
                    "[TikTokMobLimit] DESPAWN_OLDEST user={} mob={} reason=configured_user_limit active_after={}",
                    entry.getKey(),
                    removed.displayName(),
                    mobs.size());
            }
            if (mobs.isEmpty()) {
                users.remove();
            }
        }
        enforceGlobalMobLimit();
    }

    private ForcedChunkKey chunkOf(Mob mob) {
        return new ForcedChunkKey((ServerLevel) mob.level(), mob.chunkPosition().x(), mob.chunkPosition().z());
    }

    private void keepMobChunkActive(SpawnedMob mob) {
        ForcedChunkKey current = chunkOf(mob.mob());
        if (!current.equals(mob.forcedChunk())) {
            acquireChunk(current);
            releaseChunk(mob.forcedChunk());
            mob.forcedChunk(current);
        }
    }

    private void acquireChunk(ForcedChunkKey key) {
        ForcedChunkLease lease = forcedChunks.get(key);
        if (lease != null) {
            lease.retain();
            return;
        }
        boolean alreadyForced = key.level().getForceLoadedChunks().contains(net.minecraft.world.level.ChunkPos.pack(key.x(), key.z()));
        if (!alreadyForced) {
            key.level().setChunkForced(key.x(), key.z(), true);
        }
        forcedChunks.put(key, new ForcedChunkLease(!alreadyForced));
    }

    private void releaseChunk(ForcedChunkKey key) {
        ForcedChunkLease lease = forcedChunks.get(key);
        if (lease == null || lease.release() > 0) {
            return;
        }
        forcedChunks.remove(key);
        if (lease.owned()) {
            key.level().setChunkForced(key.x(), key.z(), false);
        }
    }

    private void discardTrackedMob(SpawnedMob mob) {
        mob.mob().discard();
        releaseChunk(mob.forcedChunk());
    }

    private static int secondsToTicks(double seconds) {
        return Math.max(1, (int) Math.round(seconds * 20.0));
    }

    private void reloadSettings(boolean force) {
        try {
            if (Files.notExists(CONFIG_PATH)) {
                Files.createDirectories(CONFIG_PATH.getParent());
                Files.writeString(
                    CONFIG_PATH,
                    GSON.toJson(new ModSettings()),
                    StandardCharsets.UTF_8);
            }

            var modifiedAt = Files.getLastModifiedTime(CONFIG_PATH);
            if (!force && modifiedAt.equals(configModifiedAt)) {
                return;
            }

            ModSettings loaded = GSON.fromJson(
                Files.readString(CONFIG_PATH, StandardCharsets.UTF_8),
                ModSettings.class);
            if (loaded == null) {
                throw new IllegalArgumentException("file cấu hình rỗng");
            }
            loaded.sanitize();
            int previousPort = settings.bridge_port;
            settings = loaded;
            TrollEffects.explosionDefaults(loaded.creeper_break_blocks, loaded.tnt_break_blocks);
            configModifiedAt = modifiedAt;
            LOGGER.info("Đã nạp cấu hình TikTok Mob từ {}", CONFIG_PATH.toAbsolutePath());
            if (!force && previousPort != loaded.bridge_port) {
                LOGGER.warn(
                    "Cổng bridge đổi từ {} sang {}. Hãy khởi động lại Minecraft để áp dụng cổng mới.",
                    previousPort,
                    loaded.bridge_port);
            }
        } catch (Exception error) {
            LOGGER.warn("Không nạp được cấu hình {}. Tiếp tục dùng thông số trước đó.", CONFIG_PATH, error);
        }
    }

    private void updateMobName(Mob mob, String displayName, int remainingTicks) {
        if (!settings.show_countdown_in_name || mob.entityTags().contains("tiktokmob:donation")) {
            mob.setCustomName(Component.literal(displayName));
            return;
        }
        int remainingSeconds = Math.max(0, (remainingTicks + 19) / 20);
        int minutes = remainingSeconds / 60;
        int seconds = remainingSeconds % 60;
        mob.setCustomName(Component.literal(String.format(
            Locale.ROOT,
            "%s [%02d:%02d]",
            displayName,
            minutes,
            seconds)));
    }

    private static int rewardLevel(String payload) {
        try { return Math.max(1, Math.min(255, Integer.parseInt(payload))); }
        catch (NumberFormatException ignored) { return 1; }
    }

    private static String inferNotificationKind(InteractionKind kind, String text, boolean donation) {
        if (donation) return "gift";
        if (text.contains("View")) return "view";
        if (text.contains("Follow") || kind == InteractionKind.CREEPER) return "follow";
        if (text.contains("Share") || kind == InteractionKind.ENDERMAN) return "share";
        if (text.contains("Like") || kind == InteractionKind.SKELETON) return "like";
        return "comment";
    }

    static final class NotificationPosition {
        double x = 50, y = 40, scale = 1;
        void sanitize() {
            x = Double.isFinite(x) ? Math.max(0, Math.min(100, x)) : 50;
            y = Double.isFinite(y) ? Math.max(0, Math.min(100, y)) : 40;
            scale = Double.isFinite(scale) ? Math.max(0.5, Math.min(4, scale)) : 1;
        }
    }

    static final class ModSettings {
        boolean creeper_break_blocks = false;
        boolean tnt_break_blocks = true;
        String pinned_board_background = "black";
        String pinned_board_border = "light_blue";
        String pinned_board_author_color = "#ffd99b";
        String pinned_board_comment_color = "#f4f7fb";
        double pinned_board_scale = 1.0;
        double pinned_board_width = 1.0;
        double pinned_board_height = 1.0;
        double pinned_board_text_scale = 1.0;
        double pinned_board_avatar_scale = 1.0;
        double pinned_board_corner_radius = 0.16;
        double pinned_board_avatar_x = 17.0;
        double pinned_board_avatar_y = 50.0;
        double pinned_board_rotation_speed = 1.0;
        double pinned_board_author_x = 17.0;
        double pinned_board_author_y = 82.0;
        double pinned_board_content_x = 66.0;
        double pinned_board_content_y = 60.0;
        Map<String, String> notification_display_modes = new HashMap<>();
        Map<String, NotificationPosition> notification_positions = new HashMap<>();
        int bridge_port = 9876;
        int max_pending_events = 1_000;
        int max_interactions_per_tick = 5;
        int notification_queue_size = 100;
        int max_mobs_per_user = 4;
        int max_mobs_total = 4;
        double mob_lifetime_seconds = 180.0;
        double golem_teleport_distance = 20.0;
        double wolf_teleport_distance = 20.0;
        double spawn_min_distance = 3.0;
        double spawn_max_distance = 6.0;
        double spawn_height_offset = 0.0;
        String spawn_direction = "front";
        boolean enderman_targets_player = true;
        boolean mobs_persistent = true;
        boolean show_countdown_in_name = true;
        boolean show_death_counter = true;
        double notification_duration_seconds = 1.5;
        double donation_notification_duration_seconds = 4.0;
        boolean notification_enabled = true;
        boolean notification_show_username = true;
        double notification_fade_in_seconds = 0.0;
        double notification_fade_out_seconds = 0.0;
        double notification_gap_seconds = 0.0;
        String notification_title_color = "#55ff55";
        String notification_username_color = "#ffffff";
        String donation_notification_color = "#ffaa00";
        boolean donation_notification_bold = true;
        boolean donation_priority_enabled = true;
        String notification_overflow_policy = "drop_newest";
        double effect_duration_seconds = 30.0;
        double absorption_hearts_per_rose = 1.0;
        int money_gun_arrow_count = 32;
        int universe_effect_level = 2;

        void sanitize() {
            pinned_board_background = sanitizeDye(pinned_board_background, "black");
            pinned_board_border = sanitizeDye(pinned_board_border, "light_blue");
            pinned_board_author_color = sanitizeColor(pinned_board_author_color, "#ffd99b");
            pinned_board_comment_color = sanitizeColor(pinned_board_comment_color, "#f4f7fb");
            pinned_board_scale = clamp(pinned_board_scale, 0.1, 2.0);
            pinned_board_width = clamp(pinned_board_width, 0.7, 2.5);
            pinned_board_height = clamp(pinned_board_height, 0.7, 2.5);
            pinned_board_text_scale = clamp(pinned_board_text_scale, 0.75, 1.4);
            pinned_board_avatar_scale = clamp(pinned_board_avatar_scale, 0.5, 1.8);
            pinned_board_corner_radius = clamp(pinned_board_corner_radius, 0, 0.4);
            pinned_board_avatar_x = clamp(pinned_board_avatar_x, 0, 100);
            pinned_board_avatar_y = clamp(pinned_board_avatar_y, 0, 100);
            pinned_board_rotation_speed = clamp(pinned_board_rotation_speed, 0, 10);
            pinned_board_author_x = clamp(pinned_board_author_x, 0, 100);
            pinned_board_author_y = clamp(pinned_board_author_y, 0, 100);
            pinned_board_content_x = clamp(pinned_board_content_x, 0, 100);
            pinned_board_content_y = clamp(pinned_board_content_y, 0, 100);
            if (notification_display_modes == null) notification_display_modes = new HashMap<>();
            for (String key : List.of("like", "comment", "share", "follow", "view", "gift")) {
                if (!List.of("legacy", "center", "chat").contains(String.valueOf(notification_display_modes.get(key))))
                    notification_display_modes.put(key, "legacy");
            }
            if (notification_positions == null) notification_positions = new HashMap<>();
            for (String key : List.of("like", "comment", "share", "follow", "view", "gift")) {
                notification_positions.computeIfAbsent(key, ignored -> new NotificationPosition()).sanitize();
            }
            bridge_port = clamp(bridge_port, 1_024, 65_535);
            max_pending_events = clamp(max_pending_events, 10, 100_000);
            max_interactions_per_tick = clamp(max_interactions_per_tick, 1, 1_000);
            notification_queue_size = clamp(notification_queue_size, 1, 10_000);
            max_mobs_per_user = clamp(max_mobs_per_user, 1, 1_000);
            max_mobs_total = clamp(max_mobs_total, 1, 10_000);
            mob_lifetime_seconds = clamp(mob_lifetime_seconds, 1.0, 86_400.0);
            golem_teleport_distance = clamp(golem_teleport_distance, 5.0, 128.0);
            wolf_teleport_distance = clamp(wolf_teleport_distance, 5.0, 128.0);
            spawn_min_distance = clamp(spawn_min_distance, 0.0, 128.0);
            spawn_max_distance = clamp(spawn_max_distance, spawn_min_distance, 128.0);
            if (!java.util.List.of("front", "right", "left", "back", "random").contains(spawn_direction == null ? "" : spawn_direction)) spawn_direction = "front";
            spawn_height_offset = clamp(spawn_height_offset, -64.0, 64.0);
            notification_duration_seconds = clamp(notification_duration_seconds, 0.05, 300.0);
            donation_notification_duration_seconds = clamp(donation_notification_duration_seconds, 0.05, 300.0);
            notification_fade_in_seconds = clamp(notification_fade_in_seconds, 0.0, 30.0);
            notification_fade_out_seconds = clamp(notification_fade_out_seconds, 0.0, 30.0);
            notification_gap_seconds = clamp(notification_gap_seconds, 0.0, 300.0);
            notification_title_color = sanitizeColor(notification_title_color, "#55ff55");
            notification_username_color = sanitizeColor(notification_username_color, "#ffffff");
            donation_notification_color = sanitizeColor(donation_notification_color, "#ffaa00");
            if (!"drop_oldest".equals(notification_overflow_policy)) {
                notification_overflow_policy = "drop_newest";
            }
            effect_duration_seconds = clamp(effect_duration_seconds, 0.05, 3_600.0);
            absorption_hearts_per_rose = clamp(absorption_hearts_per_rose, 0.5, 100.0);
            money_gun_arrow_count = clamp(money_gun_arrow_count, 1, 64);
            universe_effect_level = clamp(universe_effect_level, 1, 10);
        }

        private static int clamp(int value, int minimum, int maximum) {
            return Math.max(minimum, Math.min(maximum, value));
        }

        private static String sanitizeColor(String value, String fallback) {
            return value != null && value.matches("#[0-9a-fA-F]{6}") ? value : fallback;
        }

        private static String sanitizeDye(String value, String fallback) {
            try { return net.minecraft.world.item.DyeColor.valueOf(value.toUpperCase(java.util.Locale.ROOT)).name().toLowerCase(java.util.Locale.ROOT); }
            catch (Exception ignored) { return fallback; }
        }

        private static double clamp(double value, double minimum, double maximum) {
            return Math.max(minimum, Math.min(maximum, value));
        }
    }

    private enum InteractionKind {
        MISSION_PENALTY,
        KEEP_INVENTORY_ON, KEEP_INVENTORY_OFF, SET_RESPAWN, KILL_PLAYER, SKY_LAUNCH, SPAWN_TNT, LIGHTNING_PLAYER, CLEAR_TOOL_MOBS,
        TROLL_CHICKEN, TROLL_COBWEB, TROLL_PUMPKIN, TROLL_SLOWNESS,
        TROLL_TELEPORT, TROLL_CREEPER, TROLL_ANVIL, TROLL_HOTBAR, TROLL_WARDEN, TROLL_BOX,
        GIFT_ALERT, PIN_COMMENT,
        ENCHANT_ARMOR, ENCHANT_WEAPON, REPAIR_ARMOR, REPAIR_HAND, FULL_HEAL, EXPERIENCE, CLEAR_INVENTORY, ARMORED_WOLF,
        DIVINE_CAT, NETHERITE_ARMOR_FULL4, DIAMOND_ARMOR_FULL4,
        NOTIFICATION,
        CREEPER,
        ZOMBIE,
        SKELETON,
        ENDERMAN,
        ABSORPTION,
        GOLDEN_APPLE,
        REGENERATION,
        SHIELD,
        MONEY_GUN,
        DIAMOND_SWORD,
        DIAMOND_ARMOR,
        IRON_ARMOR,
        NETHERITE_ARMOR,
        NETHERITE_POWER,
        ITEM,
        MOB
    }

    private record Interaction(
        InteractionKind kind,
        String userKey,
        String displayName,
        String notification,
        String payload,
        boolean donation,
        String notificationKind,
        byte[] avatarPng
    ) {
    }

    private record DisplayNotification(
        String userKey,
        String displayName,
        String notification,
        boolean donation,
        String notificationKind
    ) {
    }

    private static final class SpawnedMob {
        private final Mob mob;
        private final long expiresAtMillis;
        private final long spawnedAtMillis;
        private final String displayName;
        private final UUID playerId;
        private ForcedChunkKey forcedChunk;

        private SpawnedMob(
            Mob mob,
            long expiresAtMillis,
            long spawnedAtMillis,
            String displayName,
            UUID playerId,
            ForcedChunkKey forcedChunk
        ) {
            this.mob = mob;
            this.expiresAtMillis = expiresAtMillis;
            this.spawnedAtMillis = spawnedAtMillis;
            this.displayName = displayName;
            this.playerId = playerId;
            this.forcedChunk = forcedChunk;
        }

        Mob mob() { return mob; }
        long expiresAtMillis() { return expiresAtMillis; }
        long spawnedAtMillis() { return spawnedAtMillis; }
        String displayName() { return displayName; }
        UUID playerId() { return playerId; }
        ForcedChunkKey forcedChunk() { return forcedChunk; }
        void forcedChunk(ForcedChunkKey value) { forcedChunk = value; }
    }

    private record ForcedChunkKey(ServerLevel level, int x, int z) {
    }

    private static final class ForcedChunkLease {
        private int references = 1;
        private final boolean owned;

        private ForcedChunkLease(boolean owned) {
            this.owned = owned;
        }

        void retain() { references++; }
        int release() { return --references; }
        boolean owned() { return owned; }
    }
}
