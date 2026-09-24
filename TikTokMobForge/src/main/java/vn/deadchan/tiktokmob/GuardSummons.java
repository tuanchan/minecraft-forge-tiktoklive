package vn.deadchan.tiktokmob;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.ProblemReporter;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.*;
import net.minecraft.world.entity.animal.golem.IronGolem;
import net.minecraft.world.entity.animal.wolf.Wolf;
import net.minecraft.world.item.*;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.storage.TagValueInput;
import net.minecraft.world.level.storage.TagValueOutput;
import net.minecraftforge.event.entity.living.LivingDropsEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import java.util.*;

final class GuardSummons {
    private static final String KEY = "tiktokmob_guard_control";
    private static final Map<UUID, Long> LAST_USE = new HashMap<>();
    static String kind(Entity entity) {
        return entity instanceof Wolf ? "dog" : entity instanceof IronGolem ? "golem" : "";
    }
    static String kind(ItemStack stack) {
        String value = stack.getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY).copyTag().getStringOr(KEY, "");
        return value.equals("dog") || value.equals("golem") ? value : "";
    }
    static ItemStack token(String kind) {
        ItemStack stack = new ItemStack(Items.PAPER);
        CompoundTag tag = new CompoundTag(); tag.putString(KEY, kind);
        stack.set(DataComponents.CUSTOM_DATA, CustomData.of(tag));
        stack.set(DataComponents.ITEM_MODEL, Identifier.fromNamespaceAndPath("tiktokmob", kind.equals("dog") ? "summomdog" : "sumongoblem"));
        stack.set(DataComponents.MAX_STACK_SIZE, 1);
        stack.set(DataComponents.CUSTOM_NAME, Component.literal(kind.equals("dog") ? "Túi chó donate · Chuột phải thu hồi / triệu hồi" : "Túi golem donate · Chuột phải thu hồi / triệu hồi"));
        return stack;
    }
    static void donated(ServerPlayer player, Mob mob) {
        String kind = kind(mob);
        if (kind.isEmpty() || !mob.entityTags().contains("tiktokmob:donation")) return;
        if (mob instanceof Wolf && !GolemGuard.isGuard(mob)) GolemGuard.markWolf(mob, player);
        ensureToken(player, kind);
    }
    private static void ensureToken(ServerPlayer player, String kind) {
        for (int slot = 0; slot < player.getInventory().getContainerSize(); slot++)
            if (kind.equals(kind(player.getInventory().getItem(slot)))) return;
        GiftBagData bag = GiftBagData.get(player);
        var existing = bag.controlEntries(player).stream().filter(e -> kind.equals(kind(e.stack()))).findFirst();
        if (existing.isPresent()) { bag.withdraw(player, existing.get().id()); return; }
        bag.deposit(player, token(kind));
        restoreTokens(player);
    }
    private static void restoreTokens(ServerPlayer player) {
        GiftBagData bag = GiftBagData.get(player);
        for (var entry : bag.controlEntries(player)) bag.withdraw(player, entry.id());
    }
    static void register() {
        PlayerInteractEvent.RightClickItem.BUS.addListener(GuardSummons::interact);
        PlayerInteractEvent.RightClickBlock.BUS.addListener(GuardSummons::interact);
        PlayerInteractEvent.EntityInteractSpecific.BUS.addListener(GuardSummons::interact);
        LivingDropsEvent.BUS.addListener(event -> {
            if (event.getEntity() instanceof ServerPlayer player) {
                var it = event.getDrops().iterator();
                while (it.hasNext()) {
                    var drop = it.next();
                    if (!kind(drop.getItem()).isEmpty()) {
                        GiftBagData.get(player).deposit(player, drop.getItem());
                        it.remove();
                    }
                }
            }
            return false;
        });
        PlayerEvent.PlayerRespawnEvent.BUS.addListener(event -> {
            if (event.getEntity() instanceof ServerPlayer player) restoreTokens(player);
        });
        PlayerEvent.PlayerLoggedInEvent.BUS.addListener(event -> {
            if (event.getEntity() instanceof ServerPlayer player) restoreTokens(player);
        });
        ServerStoppingEvent.BUS.addListener(event -> LAST_USE.clear());
    }
    private static boolean interact(PlayerInteractEvent event) {
        String kind = kind(event.getItemStack());
        if (kind.isEmpty()) return false;
        event.setCancellationResult(InteractionResult.SUCCESS);
        if (event.getEntity() instanceof ServerPlayer player && player.isAlive() && !player.isSpectator()) {
            long now = player.level().getServer().overworld().getGameTime();
            if (now - LAST_USE.getOrDefault(player.getUUID(), now - 10) >= 10) {
                LAST_USE.put(player.getUUID(), now);
                toggle(player, kind);
            }
        }
        return true;
    }
    private static void effect(Mob mob) {
        ServerLevel level = (ServerLevel)mob.level();
        level.sendParticles(ParticleTypes.SMOKE, mob.getX(), mob.getY() + .7, mob.getZ(), 24, .45, .65, .45, .03);
        level.playSound(null, mob.getX(), mob.getY(), mob.getZ(), SoundEvents.ENDERMAN_TELEPORT, SoundSource.PLAYERS, .7f, 1.25f);
    }
    private static boolean owned(Mob mob, ServerPlayer player, String kind) {
        return mob.isAlive() && kind.equals(kind(mob)) && mob.entityTags().contains("tiktokmob:donation")
            && mob.entityTags().contains("tiktokmob:guard:" + player.getUUID());
    }
    private static void toggle(ServerPlayer player, String kind) {
        GuardBagData bag = GuardBagData.get(player);
        var stored = bag.entries(player.getUUID(), kind);
        int count = 0;
        if (!stored.isEmpty()) {
            var it = stored.iterator();
            while (it.hasNext()) {
                CompoundTag tag = it.next();
                // Only load the two supported types. Do not finalizeSpawn: it resets health/equipment.
                EntityType<?> type = kind.equals("dog") ? EntityTypes.WOLF : EntityTypes.IRON_GOLEM;
                var loaded = EntityType.create(type, TagValueInput.create(ProblemReporter.DISCARDING, player.registryAccess(), tag), player.level(), EntitySpawnReason.EVENT);
                if (loaded.orElse(null) instanceof Mob mob && owned(mob, player, kind)
                        && place(player, mob) && player.level().addFreshEntity(mob)) {
                    it.remove(); bag.setDirty(); effect(mob); count++;
                }
            }
            player.sendSystemMessage(Component.literal("Đã triệu hồi " + count + "; còn " + stored.size() + " trong túi (cần chỗ trống)."));
        } else {
            for (ServerLevel level : player.level().getServer().getAllLevels()) {
                List<Mob> guards = new ArrayList<>();
                for (Entity entity : level.getAllEntities())
                    if (entity instanceof Mob mob && owned(mob, player, kind)) guards.add(mob);
                for (Mob mob : guards) {
                    if (mob.isPassenger() || mob.isVehicle()) continue;
                    var output = TagValueOutput.createWithContext(ProblemReporter.DISCARDING, level.registryAccess());
                    if (!mob.save(output)) continue;
                    stored.add(output.buildResult()); bag.setDirty();
                    effect(mob); mob.discard(); count++;
                }
            }
            player.sendSystemMessage(Component.literal("Đã thu hồi " + count + " " + (kind.equals("dog") ? "chó" : "golem") + " donate vào túi."));
        }
    }
    private static boolean place(ServerPlayer player, Mob mob) {
        ServerLevel level = player.level();
        for (int r = 2; r <= 12; r++) for (int dx = -r; dx <= r; dx++) for (int dz = -r; dz <= r; dz++) {
            if (Math.abs(dx) != r && Math.abs(dz) != r) continue;
            for (int dy : new int[]{0, 1, -1, 2, -2}) {
                BlockPos pos = player.blockPosition().offset(dx, dy, dz);
                if (!level.hasChunkAt(pos) || !level.getBlockState(pos.below()).isFaceSturdy(level, pos.below(), Direction.UP)) continue;
                mob.snapTo(pos.getX() + .5, pos.getY(), pos.getZ() + .5, player.getYRot(), 0);
                var box = mob.getBoundingBox();
                if (level.getWorldBorder().isWithinBounds(box) && level.noCollision(mob, box)
                        && !level.containsAnyLiquid(box) && level.getEntities(mob, box).isEmpty()) {
                    mob.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO); mob.fallDistance = 0; return true;
                }
            }
        }
        return false;
    }
}
