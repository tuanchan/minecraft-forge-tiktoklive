package vn.deadchan.tiktokmob;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.item.FallingBlockEntity;
import net.minecraft.world.entity.monster.Creeper;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.level.ExplosionEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;

/** Gift actions run on the server thread; no changes to global mobGriefing. */
final class TrollEffects {
    private static final String TOOL_CREEPER = "tiktokmob:no_block_explosion";
    private static final String TOOL_TNT = "tiktokmob:tool_tnt";
    private static final String PROTECT_PLAYERS = "tiktokmob:protect_players";
    private static final String BREAK = "tiktokmob:break_blocks";
    private static final String PROTECT = "tiktokmob:protect_blocks";
    private static boolean creeperBreakBlocks, tntBreakBlocks = true;
    static void explosionDefaults(boolean creeper, boolean tnt) {
        creeperBreakBlocks = creeper; tntBreakBlocks = tnt;
    }
    static boolean breaksBlocks(Entity source, boolean fallback) {
        return source.entityTags().contains(BREAK) || (!source.entityTags().contains(PROTECT) && fallback);
    }
    private static final List<String> TRICKS = List.of("TROLL_CHICKEN", "TROLL_COBWEB", "TROLL_PUMPKIN",
        "TROLL_SLOWNESS", "TROLL_TELEPORT", "TROLL_CREEPER", "TROLL_ANVIL", "TROLL_HOTBAR", "TROLL_WARDEN");
    private record WebPosition(ServerLevel level, BlockPos pos) {}
    private record TemporaryWeb(BlockState original, long expires) {}
    private static final Map<WebPosition, TemporaryWeb> WEBS = new HashMap<>();

    private record AnvilDrop(ServerPlayer player, double distance) {}
    private static final Map<java.util.UUID, java.util.ArrayDeque<AnvilDrop>> ANVILS = new HashMap<>();
    private static int anvilTicks;

    static void register() {
        TemporaryPumpkins.register();
        ExplosionEvent.Detonate.BUS.addListener(event -> {
            Entity source = event.getExplosion().getDirectSourceEntity();
            if (source instanceof Creeper && source.entityTags().contains(TOOL_CREEPER)) {
                if (!breaksBlocks(source, creeperBreakBlocks)) event.getAffectedBlocks().clear();
                event.getAffectedEntities().removeIf(entity -> entity instanceof Creeper
                    && entity.entityTags().contains(TOOL_CREEPER));
            } else if (source instanceof net.minecraft.world.entity.item.PrimedTnt
                && source.entityTags().contains(TOOL_TNT)) {
                if (!breaksBlocks(source, tntBreakBlocks)) event.getAffectedBlocks().clear();
                if (source.entityTags().contains(PROTECT_PLAYERS))
                    event.getAffectedEntities().removeIf(entity -> entity instanceof net.minecraft.world.entity.player.Player);
            }
        });
        ServerStoppingEvent.BUS.addListener(event -> {
            WEBS.forEach((position, web) -> restore(position, web));
            WEBS.clear();
            ANVILS.clear();
        });
    }

    static void markToolMob(Entity entity, String payload) {
        // Entity tags are saved with the mob, including charged creepers and chunk reloads.
        if (entity instanceof Creeper) { entity.addTag(TOOL_CREEPER); markExplosionOverride(entity, payload); }
    }

    static void markToolTnt(Entity entity, String payload) {
        entity.addTag(TOOL_TNT);
        markExplosionOverride(entity, payload);
        if (Boolean.FALSE.equals(RewardOptions.booleanOption(payload, "damage_players")))
            entity.addTag(PROTECT_PLAYERS);
        else entity.removeTag(PROTECT_PLAYERS);
    }
    private static void markExplosionOverride(Entity entity, String payload) {
        Boolean value = RewardOptions.blockOverride(payload);
        if (value != null) entity.addTag(value ? BREAK : PROTECT);
    }

    static void tick() {
        TemporaryPumpkins.tick();
        if (++anvilTicks % 10 == 0) {
            var queues = ANVILS.values().iterator();
            while (queues.hasNext()) {
                var queue = queues.next();
                var drop = queue.peek();
                var player = drop.player();
                if (!player.isAlive() || player.isRemoved() || player.isSpectator()
                    || player.level().getServer().getPlayerList().getPlayer(player.getUUID()) != player) {
                    queues.remove(); continue;
                }
                queue.remove();
                anvil(player, drop.distance());
                if (queue.isEmpty()) queues.remove();
            }
        }
        var iterator = WEBS.entrySet().iterator();
        while (iterator.hasNext()) {
            var entry = iterator.next();
            if (entry.getKey().level().getGameTime() >= entry.getValue().expires()) {
                restore(entry.getKey(), entry.getValue());
                iterator.remove();
            }
        }
    }

    private static void restore(WebPosition position, TemporaryWeb web) {
        if (position.level().getBlockState(position.pos()).is(Blocks.COBWEB)) {
            position.level().setBlock(position.pos(), web.original(), 3);
        }
    }

    static void apply(String trick, ServerPlayer player, Consumer<EntityType<?>> spawn, Consumer<ItemStack> storeItem) {
        apply(trick, player, "", spawn, storeItem);
    }

    static void apply(String trick, ServerPlayer player, String payload, Consumer<EntityType<?>> spawn, Consumer<ItemStack> storeItem) {
        switch (trick) {
            case "TROLL_CHICKEN" -> {
                spawn.accept(EntityTypes.CHICKEN);
                player.playSound(SoundEvents.CHICKEN_EGG, 1, 1);
            }
            case "TROLL_COBWEB" -> cobweb(player, payload);
            case "TROLL_PUMPKIN" -> TemporaryPumpkins.start(player, RewardOptions.ticks(payload, "duration_seconds", 10));
            case "TROLL_SLOWNESS" -> player.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, 200, 1));
            case "TROLL_TELEPORT" -> teleport(player);
            case "TROLL_CREEPER" -> spawn.accept(EntityTypes.CREEPER);
            case "TROLL_ANVIL" -> ANVILS.computeIfAbsent(player.getUUID(), ignored -> new java.util.ArrayDeque<>())
                .add(new AnvilDrop(player, RewardOptions.number(payload, "distance", 0, 0, 64)));
            case "TROLL_HOTBAR" -> {
                List<ItemStack> stacks = new ArrayList<>();
                for (int i = 0; i < 9; i++) stacks.add(player.getInventory().getItem(i));
                Collections.shuffle(stacks);
                for (int i = 0; i < 9; i++) player.getInventory().setItem(i, stacks.get(i));
                player.getInventory().setChanged();
                player.containerMenu.broadcastChanges();
                player.inventoryMenu.broadcastChanges();
            }
            case "TROLL_WARDEN" -> player.playSound(SoundEvents.WARDEN_ROAR, 2, 1);
            case "TROLL_BOX" -> {
                List<String> choices = new ArrayList<>(TRICKS);
                Collections.shuffle(choices);
                for (String choice : choices.subList(0, 3)) apply(choice, player, spawn, storeItem);
            }
            default -> throw new IllegalArgumentException("Unknown troll effect: " + trick);
        }
    }

    private static void cobweb(ServerPlayer player, String payload) {
        ServerLevel level = player.level();
        double radius = RewardOptions.number(payload, "radius", 0, 0, 16);
        int bound = (int)Math.ceil(radius);
        long expires = level.getGameTime() + RewardOptions.ticks(payload, "duration_seconds", 5);
        BlockPos center = player.blockPosition();
        for (int x = -bound; x <= bound; x++) for (int z = -bound; z <= bound; z++) {
            if (x * x + z * z > radius * radius) continue;
            BlockPos pos = center.offset(x, 0, z);
            if (!level.hasChunkAt(pos) || level.isOutsideBuildHeight(pos) || !level.getWorldBorder().isWithinBounds(pos)) continue;
            WebPosition key = new WebPosition(level, pos.immutable());
            TemporaryWeb previous = WEBS.get(key);
            if (previous != null && level.getBlockState(pos).is(Blocks.COBWEB)) {
                WEBS.put(key, new TemporaryWeb(previous.original(), Math.max(previous.expires(), expires)));
            } else if (level.getBlockState(pos).isAir()) {
                BlockState original = level.getBlockState(pos);
                if (level.setBlock(pos, Blocks.COBWEB.defaultBlockState(), 3))
                    WEBS.put(key, new TemporaryWeb(original, expires));
            }
        }
    }

    private static void teleport(ServerPlayer player) {
        ServerLevel level = player.level();
        for (int attempt = 0; attempt < 64; attempt++) {
            double angle = player.getRandom().nextDouble() * Math.PI * 2;
            double distance = 5 + player.getRandom().nextDouble() * 5;
            double x = player.getX() + Math.cos(angle) * distance;
            double z = player.getZ() + Math.sin(angle) * distance;
            for (int dy : new int[]{0, 1, -1, 2, -2}) {
                double y = Math.floor(player.getY()) + dy;
                Vec3 delta = new Vec3(x - player.getX(), y - player.getY(), z - player.getZ());
                if (delta.lengthSqr() > 100 || delta.lengthSqr() < 25) continue;
                BlockPos feet = BlockPos.containing(x, y, z);
                if (!level.hasChunkAt(feet) || !level.getWorldBorder().isWithinBounds(feet)) continue;
                BlockState floor = level.getBlockState(feet.below());
                if (!floor.isSolidRender() || floor.is(Blocks.MAGMA_BLOCK) || floor.is(Blocks.CACTUS)
                    || !level.getFluidState(feet).isEmpty() || !level.getFluidState(feet.above()).isEmpty()
                    || !level.getBlockState(feet).isAir() || !level.getBlockState(feet.above()).isAir()) continue;
                if (level.noCollision(player, player.getBoundingBox().move(delta))) {
                    player.teleportTo(x, y, z);
                    player.fallDistance = 0;
                    player.playSound(SoundEvents.ENDERMAN_TELEPORT, 1, 1);
                    return;
                }
            }
        }
        player.sendSystemMessage(Component.literal("TikTok: không có chỗ trống an toàn trong 5–10 block để dịch chuyển."));
    }

    private static void anvil(ServerPlayer player, double distance) {
        double angle = player.getRandom().nextDouble() * Math.PI * 2;
        double x = player.getX() + Math.cos(angle) * distance;
        double z = player.getZ() + Math.sin(angle) * distance;
        ServerLevel level = player.level();
        for (int height = 5; height >= 2; height--) {
            BlockPos pos = BlockPos.containing(x, player.getY() + height, z);
            if (level.isOutsideBuildHeight(pos) || !level.getWorldBorder().isWithinBounds(pos)
                || !level.hasChunkAt(pos) || !level.getBlockState(pos).isAir()) continue;
            FallingBlockEntity falling = FallingBlockEntity.fall(level, pos, Blocks.ANVIL.defaultBlockState());
            // Preserve the exact player X/Z rather than snapping to the block centre.
            falling.setPos(x, player.getY() + height, z);
            falling.setDeltaMovement(Vec3.ZERO);
            falling.setHurtsEntities(2, 8);
            falling.dropItem = false;
            falling.disableDrop(); // Scare/damage on landing, without accumulating permanent anvils.
            return;
        }
        player.playSound(SoundEvents.ANVIL_LAND, 1, 1);
    }
}
