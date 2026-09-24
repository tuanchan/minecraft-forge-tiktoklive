package vn.deadchan.tiktokmob;

import com.mojang.serialization.Codec;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;
import java.util.*;

/** Entity snapshots belong to the world and owner, never to a droppable item. */
final class GuardBagData extends SavedData {
    private final Map<String, List<CompoundTag>> bags = new HashMap<>();
    private static final Codec<GuardBagData> CODEC = Codec.unboundedMap(Codec.STRING, CompoundTag.CODEC.listOf())
        .xmap(GuardBagData::new, data -> data.bags);
    static final SavedDataType<GuardBagData> TYPE = new SavedDataType<>(
        Identifier.fromNamespaceAndPath("tiktokmob", "guard_bags"), GuardBagData::new, CODEC, null);
    GuardBagData() {}
    private GuardBagData(Map<String, List<CompoundTag>> saved) {
        saved.forEach((key, value) -> bags.put(key, new ArrayList<>(value)));
    }
    static GuardBagData get(ServerPlayer player) {
        return player.level().getServer().overworld().getDataStorage().computeIfAbsent(TYPE);
    }
    List<CompoundTag> entries(UUID owner, String kind) {
        return bags.computeIfAbsent(owner + "/" + kind, ignored -> new ArrayList<>());
    }
}
