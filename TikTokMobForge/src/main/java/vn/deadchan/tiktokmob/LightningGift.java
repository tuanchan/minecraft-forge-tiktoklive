package vn.deadchan.tiktokmob;

import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityTypes;

/** One deliberate hit per scheduled strike; roofs and lightning rods cannot redirect it. */
final class LightningGift {
    private static final Map<UUID, Sequence> ACTIVE = new HashMap<>();

    static int count(String payload) {
        return (int) RewardOptions.number(payload, "strike_count", 5, 1, Integer.MAX_VALUE);
    }

    static int intervalTicks(String payload) {
        return Math.max(1, (int) Math.ceil(RewardOptions.number(payload, "interval_seconds", 1,
            0, Integer.MAX_VALUE / 20.0) * 20));
    }

    static final class Volley {
        int remaining;
        final int interval;
        Volley(int remaining, int interval) { this.remaining = remaining; this.interval = interval; }
    }

    static final class Sequence {
        final ArrayDeque<Volley> volleys = new ArrayDeque<>();
        int wait;
        void add(int count, int interval) { volleys.addLast(new Volley(count, interval)); }
        boolean advance() {
            if (volleys.isEmpty()) return false;
            if (wait > 0 && --wait > 0) return false;
            Volley volley = volleys.getFirst();
            wait = volley.interval;
            if (--volley.remaining == 0) volleys.removeFirst();
            return true;
        }
    }

    static void start(ServerPlayer player, String payload) {
        ACTIVE.computeIfAbsent(player.getUUID(), id -> new Sequence()).add(count(payload), intervalTicks(payload));
    }

    static void clear() { ACTIVE.clear(); }

    static void tick(MinecraftServer server) {
        var entries = ACTIVE.entrySet().iterator();
        while (entries.hasNext()) {
            var entry = entries.next();
            // Resolve the current player: respawn / dimension travel replaces the entity.
            ServerPlayer player = server.getPlayerList().getPlayer(entry.getKey());
            if (player == null) { entries.remove(); continue; }
            if (!player.isAlive() || player.isSpectator()) continue;
            Sequence sequence = entry.getValue();
            if (sequence.advance()) strike(player);
            if (sequence.volleys.isEmpty()) entries.remove();
        }
    }

    private static void strike(ServerPlayer player) {
        var level = player.level();
        var bolt = EntityTypes.LIGHTNING_BOLT.create(level, EntitySpawnReason.EVENT);
        if (bolt == null) return;
        bolt.snapTo(player.getX(), player.getY(), player.getZ(), 0, 0);
        // Vanilla bolt flashes repeatedly and hits surrounding entities. This gift applies
        // damage once, directly to its target, while retaining the bolt's rendering/sound.
        bolt.setVisualOnly(true);
        level.addFreshEntity(bolt);
        player.invulnerableTime = 0;
        player.thunderHit(level, bolt);
    }
}
