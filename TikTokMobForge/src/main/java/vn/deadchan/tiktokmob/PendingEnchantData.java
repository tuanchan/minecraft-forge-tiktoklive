package vn.deadchan.tiktokmob;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.saveddata.SavedDataType;
import java.util.*;
import java.util.function.BiPredicate;

/** Unclaimed enchants belong to the player's UUID, not the replaceable player entity. */
public final class PendingEnchantData extends SavedData {
    record Reward(String slot, int level, Map<String, Integer> enchantments) {
        static final Codec<Reward> CODEC = RecordCodecBuilder.create(i -> i.group(
            Codec.STRING.fieldOf("slot").forGetter(Reward::slot),
            Codec.intRange(0, 255).fieldOf("level").forGetter(Reward::level),
            Codec.unboundedMap(Codec.STRING, Codec.intRange(1, 255))
                .optionalFieldOf("enchantments", Map.of()).forGetter(Reward::enchantments)
        ).apply(i, Reward::new));
    }
    private static final Codec<PendingEnchantData> CODEC = Codec.unboundedMap(Codec.STRING, Reward.CODEC.listOf())
        .xmap(PendingEnchantData::new, data -> data.pending);
    public static final SavedDataType<PendingEnchantData> TYPE = new SavedDataType<>(
        Identifier.fromNamespaceAndPath("tiktokmob", "pending_enchants"), PendingEnchantData::new, CODEC, null);
    private final Map<String, List<Reward>> pending = new HashMap<>();

    public PendingEnchantData() {}
    private PendingEnchantData(Map<String, List<Reward>> saved) {
        saved.forEach((key, rewards) -> pending.put(key, new ArrayList<>(rewards)));
    }
    static PendingEnchantData get(ServerPlayer player) {
        return player.level().getServer().overworld().getDataStorage().computeIfAbsent(TYPE);
    }
    void add(UUID owner, boolean armor, int level) {
        add(owner, armor, level, Map.of());
    }
    void add(UUID owner, boolean armor, int level, Map<String, Integer> enchantments) {
        List<Reward> rewards = pending.computeIfAbsent(owner.toString(), key -> new ArrayList<>());
        for (EquipmentSlot slot : armor ? SpecialRewards.ARMOR : List.of(EquipmentSlot.MAINHAND)) {
            rewards.add(new Reward(slot.name(), Math.clamp(level, 0, 255), Map.copyOf(enchantments)));
        }
        setDirty();
    }
    Set<EquipmentSlot> waitingSlots(UUID owner) {
        Set<EquipmentSlot> slots = EnumSet.noneOf(EquipmentSlot.class);
        for (Reward reward : pending.getOrDefault(owner.toString(), List.of()))
            slots.add(EquipmentSlot.valueOf(reward.slot()));
        return slots;
    }
    Set<EquipmentSlot> applyReady(UUID owner, BiPredicate<EquipmentSlot, Integer> apply) {
        return applyConfigured(owner, (slot, level, enchantments) -> apply.test(slot, level));
    }
    @FunctionalInterface
    interface ApplyEnchant {
        boolean apply(EquipmentSlot slot, int level, Map<String, Integer> enchantments);
    }
    Set<EquipmentSlot> applyConfigured(UUID owner, ApplyEnchant apply) {
        Set<EquipmentSlot> applied = EnumSet.noneOf(EquipmentSlot.class);
        List<Reward> rewards = pending.get(owner.toString());
        if (rewards == null) return applied;
        for (Iterator<Reward> it = rewards.iterator(); it.hasNext();) {
            Reward reward = it.next();
            EquipmentSlot slot = EquipmentSlot.valueOf(reward.slot());
            // Consume only after a compatible item has actually received the reward.
            if (apply.apply(slot, reward.level(), reward.enchantments())) {
                it.remove();
                applied.add(slot);
                setDirty();
            }
        }
        if (rewards.isEmpty()) pending.remove(owner.toString());
        return applied;
    }
}
