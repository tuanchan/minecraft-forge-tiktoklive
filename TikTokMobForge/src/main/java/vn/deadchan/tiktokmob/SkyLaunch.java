package vn.deadchan.tiktokmob;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.EntityMountEvent;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;

/** A vanilla, network-interpolated carrier moves the rider through ceilings without teleporting. */
final class SkyLaunch {
    private static final Map<UUID, Flight> FLIGHTS = new HashMap<>();
    private record Flight(ServerPlayer player, ArmorStand carrier, double targetY, long deadline) {}
    static final double SPEED = 3.0;

    static boolean readyToRelease(double remaining, boolean clear, long now, long deadline) {
        return (remaining <= 0.25 && clear) || now >= deadline;
    }

    static double stackHeight(double target, double height) { return target + height; }

    static double targetHeight(double startY, int surfaceY) {
        return Math.max(startY + 96.0, surfaceY + 12.0);
    }

    static void register() {
        EntityMountEvent.BUS.addListener(event -> {
            if (event.getLevel().isClientSide() || !event.isDismounting()) return false;
            Flight flight = FLIGHTS.get(event.getEntityMounting().getUUID());
            return flight != null && event.getEntityMounting().isAlive()
                && event.getEntityBeingMounted() == flight.carrier();
        });
        LivingAttackEvent.BUS.addListener(event -> !event.getEntity().level().isClientSide()
            && FLIGHTS.containsKey(event.getEntity().getUUID()) && event.getSource().is(DamageTypes.IN_WALL));
        ServerStoppingEvent.BUS.addListener(event -> {
            SpecialRewards.clearTnt(event.getServer());
            for (Flight flight : java.util.List.copyOf(FLIGHTS.values())) {
                if (flight.player().level().getServer() == event.getServer()) finish(flight);
            }
        });
    }

    static void start(ServerPlayer player) { start(player, ""); }

    static void start(ServerPlayer player, String payload) {
        double height = RewardOptions.number(payload, "height", 96, 1, 2048);
        Flight previous = FLIGHTS.get(player.getUUID());
        double target = player.getY() + height;
        if (previous != null) {
            // Combo gifts extend the current flight without remounting or jumping position.
            FLIGHTS.put(player.getUUID(), new Flight(player, previous.carrier(), stackHeight(previous.targetY(), height), previous.deadline() + (long)Math.ceil(height / SPEED) + 20));
            return;
        }
        ArmorStand carrier = EntityTypes.ARMOR_STAND.create(player.level(), EntitySpawnReason.EVENT);
        if (carrier == null) return;
        carrier.setInvisible(true);
        carrier.setInvulnerable(true);
        carrier.setNoGravity(true);
        carrier.noPhysics = true;
        carrier.setPos(player.getX(), player.getY(), player.getZ());
        Vec3 riderOffset = carrier.getPassengerRidingPosition(player).subtract(carrier.position())
            .subtract(player.getVehicleAttachmentPoint(carrier));
        carrier.setPos(player.position().subtract(riderOffset));
        if (!player.level().addFreshEntity(carrier)) return;
        player.stopFallFlying();
        player.stopRiding();
        if (!player.startRiding(carrier, true, true)) { carrier.discard(); return; }
        FLIGHTS.put(player.getUUID(), new Flight(player, carrier, target, player.level().getGameTime() + (long)Math.ceil(height / SPEED) + 200));
        GiftNetwork.send(player, new GiftNetwork.SkyRide(carrier.getId()));
    }

    static void tick(MinecraftServer server) {
        for (Flight flight : java.util.List.copyOf(FLIGHTS.values())) {
            ServerPlayer player = flight.player();
            ArmorStand carrier = flight.carrier();
            if (carrier.level().getServer() != server) continue;
            if (server.getPlayerList().getPlayer(player.getUUID()) != player || !player.isAlive()
                    || player.isRemoved() || carrier.isRemoved() || player.isSpectator()
                    || player.level() != carrier.level() || player.getVehicle() != carrier) {
                finish(flight);
                continue;
            }
            double remaining = flight.targetY() - player.getY();
            // Only solid blocks matter here; the invisible carrier must not prevent release.
            boolean clear = !player.level().getBlockCollisions(player, player.getBoundingBox()).iterator().hasNext();
            if (readyToRelease(remaining, clear, player.level().getGameTime(), flight.deadline())) {
                finish(flight);
                continue;
            }
            carrier.noPhysics = true;
            // Entity movement is synchronized by vanilla tracking; never teleport the player.
            carrier.move(MoverType.SELF, new Vec3(0, remaining > 0 ? Math.min(SPEED, remaining) : SPEED, 0));
            carrier.positionRider(player);
            player.fallDistance = 0;
        }
    }

    private static void finish(Flight flight) {
        FLIGHTS.remove(flight.player().getUUID());
        ServerPlayer player = flight.player();
        GiftNetwork.send(player, new GiftNetwork.SkyRide(-1));
        if (player.getVehicle() == flight.carrier()) {
            player.stopRiding();
            if (player.isAlive() && !player.isSpectator()) {
                player.stopFallFlying();
                player.getAbilities().flying = false;
                player.onUpdateAbilities();
                player.setDeltaMovement(0, -0.15, 0);
                player.connection.send(new net.minecraft.network.protocol.game.ClientboundSetEntityMotionPacket(player));
            }
        }
        flight.carrier().discard();
        // Gravity and fall damage resume; game mode and permission to fly remain unchanged.
    }
}
