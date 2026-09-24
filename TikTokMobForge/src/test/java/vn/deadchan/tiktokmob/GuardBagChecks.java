package vn.deadchan.tiktokmob;

import com.mojang.serialization.JsonOps;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.resources.RegistryOps;
import net.minecraft.core.HolderLookup;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import java.util.UUID;

final class GuardBagChecks {
    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
    }
    static void run(HolderLookup.Provider registries) {
        UUID owner = UUID.randomUUID(), other = UUID.randomUUID();
        GuardBagData bag = new GuardBagData();
        CompoundTag first = new CompoundTag();
        first.putString("id", "minecraft:wolf");
        first.putString("CustomName", "Người donate một");
        first.putFloat("Health", 7.5f);
        CompoundTag armor = new CompoundTag(); armor.putInt("damage", 42);
        first.put("armor", armor);
        CompoundTag second = first.copy();
        second.putString("CustomName", "Người donate hai"); second.putFloat("Health", 11f);
        bag.entries(owner, "dog").add(first); bag.entries(owner, "dog").add(second);
        bag.entries(owner, "golem").add(new CompoundTag());
        var saved = GuardBagData.TYPE.codec().encodeStart(NbtOps.INSTANCE, bag).getOrThrow();
        var restored = GuardBagData.TYPE.codec().parse(NbtOps.INSTANCE, saved).getOrThrow();
        check(restored.entries(owner, "dog").size() == 2, "Recall count survives world save/reload");
        check(restored.entries(other, "dog").isEmpty(), "Another owner cannot access guards");
        check(restored.entries(owner, "golem").size() == 1, "Dog and golem storage are independent");
        check(restored.entries(owner, "dog").getFirst().equals(first), "Donor, health and nested equipment preserved");
        check(restored.entries(owner, "dog").getLast().equals(second), "Different donors remain separate entities");
        restored.entries(owner, "dog").removeFirst();
        var afterPartial = GuardBagData.TYPE.codec().parse(NbtOps.INSTANCE,
            GuardBagData.TYPE.codec().encodeStart(NbtOps.INSTANCE, restored).getOrThrow()).getOrThrow();
        check(afterPartial.entries(owner, "dog").size() == 1, "Partial summon keeps remaining entities on disk");
        var ops = RegistryOps.create(JsonOps.INSTANCE, registries);
        for (String kind : new String[]{"dog", "golem"}) {
            ItemStack token = GuardSummons.token(kind);
            ItemStack decoded = ItemStack.CODEC.parse(ops, ItemStack.CODEC.encodeStart(ops, token).getOrThrow()).getOrThrow();
            check(GuardSummons.kind(decoded).equals(kind), "Control item survives save/death storage");
            check(decoded.getMaxStackSize() == 1, "Control items cannot stack");
        }
        check(GuardSummons.kind(new ItemStack(Items.PAPER)).isEmpty(), "Ordinary paper is unaffected");
        System.out.println("GUARD_BAG_CHECKS_OK: counts, donors, health, equipment, owner/type isolation, partial summon, item serialization");
    }
}
