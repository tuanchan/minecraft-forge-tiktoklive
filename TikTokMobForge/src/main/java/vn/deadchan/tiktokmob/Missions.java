package vn.deadchan.tiktokmob;

import com.google.gson.Gson;
import com.google.gson.JsonParser;
import com.mojang.logging.LogUtils;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.level.block.Blocks;
import net.minecraftforge.event.entity.living.LivingDeathEvent;
import net.minecraftforge.event.level.BlockEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import java.nio.file.*;
import java.util.*;

/** Server-authoritative mission counters, persistent per world and player. */
final class Missions {
    static final Gson GSON = new Gson();
    private static final Path CONFIG = Path.of("config", "tiktokmob-missions.json");
    private static final Path STATE = Path.of("config", "tiktokmob-missions-state.json");
    record Rule(String id, String title, String kind, String mob, boolean enabled, boolean summoned_only,
                long target, int milestones, long death_penalty, String death_mode, String mode, double x, double y, double scale, int reset) {
        boolean matches(String eventKind, String entityType, boolean summoned) {
            return enabled && kind.equals(eventKind) && (!kind.equals("kill")
                || (mob.equals("*") || mob.equals(entityType)) && (!summoned_only || summoned));
        }
        void validate() {
            if (id == null || !id.matches("[a-zA-Z0-9_-]{1,48}") || title == null || title.isBlank() || title.length() > 64
                || !Set.of("diamond", "kill").contains(kind) || mob == null || !mob.matches("\\*|[a-z0-9_.-]+:[a-z0-9_./-]+")
                || target < 1 || target > Integer.MAX_VALUE || milestones < 0 || milestones > 100
                || death_penalty < 0 || death_penalty > Integer.MAX_VALUE
                || !Set.of("points", "percent").contains(death_mode) || death_mode.equals("percent") && death_penalty > 100
                || !Set.of("2d", "3d").contains(mode) || !Double.isFinite(x) || x < 0 || x > 100
                || !Double.isFinite(y) || y < 0 || y > 100 || !Double.isFinite(scale) || scale < .25 || scale > 3 || reset < 0)
                throw new IllegalArgumentException("Invalid mission: " + id);
        }
        int effectiveMilestones() { return milestones == 0 ? 10 : milestones; }
    }
    record Config(boolean enabled, List<Rule> rules) {}
    record View(String id, String title, String kind, long current, long target, int milestones,
                String mode, double x, double y, double scale) {}
    record PlayerView(String uuid, String name, List<View> rules) {}
    private static Config config = new Config(false, List.of());
    private static long modified = Long.MIN_VALUE;
    private static final List<Runnable> pending = new ArrayList<>();

    static void register() {
        BlockEvent.BreakEvent.BUS.addListener((event, cancelled) -> {
            if (cancelled) return;
            if (event.getPlayer() instanceof ServerPlayer player && !player.isCreative()
                && (event.getState().is(Blocks.DIAMOND_ORE) || event.getState().is(Blocks.DEEPSLATE_DIAMOND_ORE))) {
                var level = player.level(); var pos = event.getPos().immutable(); var state = event.getState();
                // Check after every listener: a canceled break leaves its ore in place.
                pending.add(() -> { if (!level.getBlockState(pos).equals(state)) increment(player, "diamond", "", false); });
            }
        });
        LivingDeathEvent.BUS.addListener((event, cancelled) -> {
            if (cancelled) return;
            var entity = event.getEntity();
            if (entity.level().isClientSide()) return;
            if (entity instanceof ServerPlayer player) {
                pending.add(() -> { if (player.isDeadOrDying()) death(player); });
            } else if (entity instanceof Mob && event.getSource().getEntity() instanceof ServerPlayer player) {
                String mob = BuiltInRegistries.ENTITY_TYPE.getKey(entity.getType()).toString();
                boolean summoned = entity.entityTags().contains("tiktokmob:summoned");
                pending.add(() -> { if (entity.isDeadOrDying()) increment(player, "kill", mob, summoned); });
            }
        });
        ServerStoppingEvent.BUS.addListener(event -> {
            pending.clear(); config = new Config(false, List.of()); modified = Long.MIN_VALUE;
            writeState(List.of());
        });
    }
    static void tick(MinecraftServer server, TikTokMobMod.ModSettings settings) {
        if (modified == Long.MIN_VALUE || server.getTickCount() % 20 == 0) reload();
        var work = new ArrayList<>(pending); pending.clear(); work.forEach(Runnable::run);
        if (server.getTickCount() % 10 != 0) return;
        List<PlayerView> players = new ArrayList<>();
        for (ServerPlayer player : server.getPlayerList().getPlayers()) {
            List<View> views = new ArrayList<>();
            if (config.enabled()) for (Rule rule : config.rules()) if (rule.enabled()) {
                long current = MissionData.get(player).current(player, rule);
                views.add(new View(rule.id(), rule.title(), rule.kind(), current, rule.target(), rule.effectiveMilestones(),
                    rule.mode(), rule.x(), rule.y(), rule.scale()));
            }
            GiftNetwork.send(player, new GiftNetwork.MissionState(GSON.toJson(views)));
            ServerPinnedCommentBoard.missions(player, views, settings);
            players.add(new PlayerView(player.getUUID().toString(), player.getGameProfile().name(), views));
        }
        writeState(players);
    }
    private static void increment(ServerPlayer player, String kind, String mob, boolean summoned) {
        if (!config.enabled()) return;
        MissionData data = MissionData.get(player);
        for (Rule rule : config.rules()) if (rule.matches(kind, mob, summoned))
            data.set(player, rule, MissionMath.add(data.current(player, rule), rule.target()));
    }
    private static void death(ServerPlayer player) {
        if (!config.enabled()) return;
        MissionData data = MissionData.get(player);
        for (Rule rule : config.rules()) if (rule.enabled())
            data.set(player, rule, MissionMath.death(data.current(player, rule), rule.death_penalty(), rule.death_mode().equals("percent")));
    }
    static void penalty(ServerPlayer player, String payload) {
        if (!config.enabled()) return;
        try {
            var json = JsonParser.parseString(payload).getAsJsonObject();
            String id = json.get("mission_id").getAsString();
            long points = json.get("penalty").getAsLong();
            if (points < 1 || points > Integer.MAX_VALUE) return;
            MissionData data = MissionData.get(player);
            for (Rule rule : config.rules()) if (rule.enabled() && (id.equals("*") || id.equals(rule.id())))
                data.set(player, rule, MissionMath.subtract(data.current(player, rule), points));
        } catch (RuntimeException invalid) { LogUtils.getLogger().warn("Invalid mission penalty payload"); }
    }
    private static void reload() {
        try {
            long stamp = Files.exists(CONFIG) ? Files.getLastModifiedTime(CONFIG).toMillis() : 0;
            if (stamp == modified) return;
            modified = stamp;
            Config next = stamp == 0 ? new Config(false, List.of()) : GSON.fromJson(Files.readString(CONFIG), Config.class);
            if (next == null || next.rules() == null || next.rules().size() > 32) throw new IllegalArgumentException("Invalid mission config");
            Set<String> ids = new HashSet<>();
            for (Rule rule : next.rules()) { rule.validate(); if (!ids.add(rule.id())) throw new IllegalArgumentException("Duplicate mission"); }
            config = next;
        } catch (Exception error) { LogUtils.getLogger().warn("Cannot load missions; keeping previous config", error); }
    }
    private static void writeState(List<PlayerView> players) {
        try {
            Files.createDirectories(STATE.getParent());
            Path temporary = STATE.resolveSibling(STATE.getFileName() + ".tmp");
            Files.writeString(temporary, GSON.toJson(Map.of("updated", System.currentTimeMillis(), "players", players)));
            try { Files.move(temporary, STATE, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
            catch (AtomicMoveNotSupportedException ignored) { Files.move(temporary, STATE, StandardCopyOption.REPLACE_EXISTING); }
        } catch (Exception error) { LogUtils.getLogger().debug("Cannot publish mission progress", error); }
    }
}
