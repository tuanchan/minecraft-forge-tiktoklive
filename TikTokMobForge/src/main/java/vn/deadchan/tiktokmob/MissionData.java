package vn.deadchan.tiktokmob;

import com.mojang.serialization.Codec;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

final class MissionData extends SavedData {
    private final Map<String, Long> progress = new HashMap<>();
    static final Codec<MissionData> CODEC = Codec.unboundedMap(Codec.STRING, Codec.LONG)
        .xmap(MissionData::new, data -> data.progress);
    private static final SavedDataType<MissionData> TYPE = new SavedDataType<>(
        Identifier.fromNamespaceAndPath("tiktokmob", "missions"), MissionData::new, CODEC, null);
    MissionData() {}
    private MissionData(Map<String, Long> saved) { progress.putAll(saved); }
    static MissionData get(ServerPlayer player) {
        return player.level().getServer().overworld().getDataStorage().computeIfAbsent(TYPE);
    }
    private static String key(UUID player, Missions.Rule rule) {
        return player + "/" + rule.id() + "/" + rule.kind() + "/" + rule.mob()
            + "/" + rule.summoned_only() + "/" + rule.reset();
    }
    long current(ServerPlayer player, Missions.Rule rule) {
        return current(player.getUUID(), rule);
    }
    long current(UUID player, Missions.Rule rule) {
        return Math.min(rule.target(), progress.getOrDefault(key(player, rule), 0L));
    }
    void set(ServerPlayer player, Missions.Rule rule, long value) {
        set(player.getUUID(), rule, value);
    }
    void set(UUID player, Missions.Rule rule, long value) {
        progress.put(key(player, rule), Math.min(rule.target(), value));
        setDirty();
    }
}
