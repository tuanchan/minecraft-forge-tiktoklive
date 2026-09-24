package vn.deadchan.tiktokmob;

import java.util.EnumSet;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.animal.wolf.Wolf;
import net.minecraft.world.entity.animal.feline.Cat;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import java.util.function.Supplier;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.animal.golem.IronGolem;
import net.minecraft.world.entity.monster.Creeper;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.event.entity.EntityJoinLevelEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.entity.living.LivingChangeTargetEvent;

/** Tool-summoned golems and armored wolves share the same persistent guard AI. */
final class GolemGuard {
    private static Supplier<TikTokMobMod.ModSettings> settings = TikTokMobMod.ModSettings::new;
    private static final String OWNER = "tiktokmob:guard:";
    private static final String SUMMONED = "tiktokmob:summoned";
    static void markSummoned(Mob mob) { mob.addTag(SUMMONED); }
    static boolean canHarmPlayer(Mob mob) {
        var attack = mob.getAttribute(Attributes.ATTACK_DAMAGE);
        return mob.getType().getCategory() == MobCategory.MONSTER
            || (attack != null && attack.getValue() > 0);
    }
    private static boolean isThreat(Mob mob, Mob golem, ServerPlayer owner) {
        if (mob == golem || isGuard(mob) || !mob.isAlive() || mob.isInvulnerable()
            || !canHarmPlayer(mob) || mob.isAlliedTo(owner)) return false;
        return mob instanceof Creeper || mob.entityTags().contains(SUMMONED) || mob.entityTags().contains("tiktokmob:donation")
            || mob.getTarget() == owner || isGuard(mob.getTarget());
    }
    static boolean isGuard(Entity entity) {
        return (entity instanceof IronGolem || entity instanceof Wolf || entity instanceof Cat) && entity.entityTags().stream().anyMatch(t -> t.startsWith(OWNER));
    }
    static void mark(Mob mob, ServerPlayer player) {
        markSummoned(mob);
        if (mob instanceof IronGolem golem) {
            golem.addTag(OWNER + player.getUUID());
            golem.setPlayerCreated(true);
        }
    }
    static void markWolf(Mob mob, ServerPlayer player) {
        if (mob instanceof Wolf wolf) {
            wolf.addTag(OWNER + player.getUUID());
            wolf.setAge(0);
            wolf.tame(player);
            wolf.setOrderedToSit(false);
            wolf.setInSittingPose(false);
            wolf.setHealth(wolf.getMaxHealth());
            wolf.setItemSlot(EquipmentSlot.BODY, new ItemStack(Items.WOLF_ARMOR));
        }
    }
    static void markCat(Mob mob, ServerPlayer player) {
        if (mob instanceof Cat cat) {
            cat.addTag(OWNER + player.getUUID());
            cat.setAge(0);
            cat.tame(player);
            cat.setOrderedToSit(false);
            cat.setInSittingPose(false);
            cat.getAttribute(Attributes.MAX_HEALTH).setBaseValue(200);
            cat.setHealth(200);
            cat.setPersistenceRequired();
        }
    }
    static double teleportDistance(boolean wolf, TikTokMobMod.ModSettings config) {
        return wolf ? config.wolf_teleport_distance : config.golem_teleport_distance;
    }
    static void register(Supplier<TikTokMobMod.ModSettings> config) {
        settings = config;
        LivingAttackEvent.BUS.addListener(event -> {
            return ((isGuard(event.getEntity()) && event.getSource().getEntity() instanceof Player)
                    || (event.getEntity() instanceof Player && event.getSource().getEntity() != null
                        && isGuard(event.getSource().getEntity())));
        });
        LivingChangeTargetEvent.BUS.addListener(event -> {
            if (isGuard(event.getEntity()) && event.getNewTarget() instanceof Player) event.setNewTarget(null);
        });
        EntityJoinLevelEvent.BUS.addListener(event -> {
            if (event.getLevel() instanceof ServerLevel && isGuard(event.getEntity())) {
                Mob golem = (Mob) event.getEntity();
                if (golem instanceof IronGolem iron) iron.setPlayerCreated(true);
                // The owner-follow goal owns navigation and targeting, including Creepers.
                // Vanilla target selectors must not overwrite the player's attack order.
                golem.goalSelector.removeAllGoals(goal -> !(goal instanceof net.minecraft.world.entity.ai.goal.FloatGoal));
                golem.targetSelector.removeAllGoals(goal -> true);
                golem.goalSelector.addGoal(0, new FollowOwner(golem));
            }
        });
    }
    private static final class FollowOwner extends Goal {
        private final Mob golem;
        private ServerPlayer owner;
        FollowOwner(Mob golem) { this.golem = golem; setFlags(EnumSet.of(Flag.MOVE, Flag.LOOK)); }
        // Mob alternates full/reduced goal ticks by entity ID. Without this,
        // tickCount % 10 can miss every update for half of the guards.
        @Override public boolean requiresUpdateEveryTick() { return true; }
        @Override public boolean canUse() {
            owner = null;
            if (!(golem.level() instanceof ServerLevel level)) return false;
            for (String tag : golem.entityTags()) if (tag.startsWith(OWNER)) {
                try { owner = level.getServer().getPlayerList().getPlayer(UUID.fromString(tag.substring(OWNER.length()))); }
                catch (IllegalArgumentException ignored) { }
                break;
            }
            return owner != null && owner.isAlive() && !owner.isSpectator();
        }
        @Override public boolean canContinueToUse() { return canUse(); }
        @Override public void stop() { owner = null; golem.setTarget(null); golem.getNavigation().stop(); }
        @Override public void tick() {
            // Respawn replaces ServerPlayer. Resolve the UUID before using the owner.
            if (!canUse()) { stop(); return; }
            if (owner == null || golem.tickCount % 10 != 0) return;
            if (golem instanceof Wolf wolf) {
                wolf.setOrderedToSit(false);
                wolf.setInSittingPose(false);
            }
            if (golem instanceof Cat cat) {
                cat.setOrderedToSit(false);
                cat.setInSittingPose(false);
            }
            if (golem.getTarget() instanceof Player) golem.setTarget(null);
            if (golem.level() != owner.level() || golem.distanceToSqr(owner) > Math.pow(golem instanceof Cat ? 20 : teleportDistance(golem instanceof Wolf, settings.get()), 2)) {
                teleportNearOwner();
                return;
            }
            if (golem instanceof Cat) {
                // A real Cat triggers vanilla Creeper avoidance; stay close to protect the owner.
                golem.setTarget(null);
                if (golem.distanceToSqr(owner) > 2 * 2) golem.getNavigation().moveTo(owner, 1.2);
                else golem.getNavigation().stop();
                golem.getLookControl().setLookAt(owner, 30, 30);
                return;
            }
            // Keep fighting threats after they switch from the owner to a guard.
            // Each guard picks its nearest threat rather than all chasing one mob.
            // The owner's latest attacked mob wins, even if it is normally passive.
            // Resolve from the current player instance so respawn cannot retain an old order.
            Mob orderedTarget = owner.getLastHurtMob() instanceof Mob mob
                && mob != golem && !isGuard(mob) && mob.isAlive() && !mob.isInvulnerable()
                && mob.level() == owner.level() && !mob.isAlliedTo(owner)
                && mob.distanceToSqr(owner) <= 16 * 16 ? mob : null;
            Mob threat = orderedTarget != null ? orderedTarget : owner.level().getEntitiesOfClass(Mob.class, owner.getBoundingBox().inflate(16),
                m -> isThreat(m, golem, owner))
                .stream().min(java.util.Comparator.comparingDouble(m -> m.distanceToSqr(golem))).orElse(null);
            golem.setTarget(threat);
            var target = golem.getTarget();
            if (target != null && target.isAlive() && target.distanceToSqr(owner) <= 16 * 16) {
                golem.getNavigation().moveTo(target, 1.2);
                golem.getLookControl().setLookAt(target, 30, 30);
                if (golem.hasLineOfSight(target) && golem.distanceToSqr(target) < 9 && golem.tickCount % 20 == 0)
                    // Deliberately use the guard's attack loop: vanilla canAttack rejects Creepers.
                    golem.doHurtTarget(owner.level(), target);
            } else {
                golem.setTarget(null);
                if (golem.distanceToSqr(owner) > 4 * 4) golem.getNavigation().moveTo(owner, 1.2);
                else golem.getNavigation().stop();
            }
        }
        private void teleportNearOwner() {
            ServerLevel level = owner.level();
            for (int radius = 2; radius <= 6; radius++) for (int dx = -radius; dx <= radius; dx++)
                for (int dz = -radius; dz <= radius; dz++) for (int dy : new int[] {0, 1, -1, 2, -2}) {
                    if (Math.abs(dx) != radius && Math.abs(dz) != radius) continue;
                    BlockPos pos = owner.blockPosition().offset(dx, dy, dz);
                    if (!level.hasChunkAt(pos) || !level.getBlockState(pos.below()).isFaceSturdy(level, pos.below(), Direction.UP)) continue;
                    var box = golem.getBoundingBox().move(pos.getX() + .5 - golem.getX(), pos.getY() - golem.getY(), pos.getZ() + .5 - golem.getZ());
                    if (!level.getWorldBorder().isWithinBounds(box) || !level.noCollision(golem, box) || level.containsAnyLiquid(box)) continue;
                    golem.getNavigation().stop();
                    golem.teleportTo(level, pos.getX() + .5, pos.getY(), pos.getZ() + .5,
                        java.util.Set.of(), owner.getYRot(), 0, false);
                    return;
                }
        }
    }
}
