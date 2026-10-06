package vn.deadchan.tiktokmob;

import com.mojang.serialization.JsonOps;
import net.minecraft.core.HolderLookup;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import java.util.*;

/** Checks the pending reward lifecycle; equipment readiness is simulated without a world. */
final class PendingEnchantChecks {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    static void run(HolderLookup.Provider registries) {
        selectedChecks(registries);
        int current = 0;
        for (int expected : new int[]{5, 6, 7}) {
            current = SpecialRewards.nextEnchantLevel(current, 5);
            check(current == expected, "Repeated level 5 gifts progress to " + expected);
        }
        check(SpecialRewards.nextEnchantLevel(7, 5) == 8, "Lower gift increments stronger enchant");
        check(SpecialRewards.nextEnchantLevel(7, 12) == 12, "Higher gift reaches requested level");
        check(SpecialRewards.nextEnchantLevel(255, 5) == 255, "Enchantment capped at 255");
        UUID owner = UUID.randomUUID(), other = UUID.randomUUID();
        PendingEnchantData data = new PendingEnchantData();
        data.add(owner, true, 7);
        data.add(owner, false, 3);
        check(data.waitingSlots(owner).size() == 5, "Four independent armor slots plus main hand");
        check(data.applyReady(owner, (slot, level) -> SpecialRewards.enchantStack(
            registries, ItemStack.EMPTY, slot != EquipmentSlot.MAINHAND, level)).isEmpty(), "Empty equipment keeps reward");
        check(data.applyReady(owner, (slot, level) -> SpecialRewards.enchantStack(
            registries, new ItemStack(Items.APPLE), slot != EquipmentSlot.MAINHAND, level)).isEmpty(), "Non-equipment does not consume reward");
        check(data.waitingSlots(owner).size() == 5, "All slots still pending");
        check(data.applyReady(other, (slot, level) -> { throw new AssertionError("Wrong owner"); }).isEmpty(), "UUID isolation");

        Set<EquipmentSlot> equipped = EnumSet.of(EquipmentSlot.HEAD);
        List<String> received = new ArrayList<>();
        check(data.applyReady(owner, (slot, level) -> {
            if (!equipped.contains(slot)) return false;
            received.add(slot + ":" + level);
            return true;
        }).equals(Set.of(EquipmentSlot.HEAD)), "First helmet receives its reward immediately");
        check(received.equals(List.of("HEAD:7")), "Saved enchant level applied to helmet");
        check(data.waitingSlots(owner).size() == 4, "Other three armor slots and weapon continue waiting");
        data.applyReady(owner, (slot, level) -> {
            check(slot != EquipmentSlot.HEAD, "Replacing or re-equipping helmet cannot claim twice");
            return false;
        });

        // Save/reload between individual pieces, as on a restart or respawn with the same UUID.
        var saved = PendingEnchantData.TYPE.codec().encodeStart(JsonOps.INSTANCE, data).getOrThrow();
        data = PendingEnchantData.TYPE.codec().parse(JsonOps.INSTANCE, saved).getOrThrow();
        UUID respawned = UUID.fromString(owner.toString());
        check(data.waitingSlots(respawned).equals(Set.of(EquipmentSlot.CHEST, EquipmentSlot.LEGS,
            EquipmentSlot.FEET, EquipmentSlot.MAINHAND)), "Only unclaimed slots survive reload");
        for (EquipmentSlot next : List.of(EquipmentSlot.FEET, EquipmentSlot.CHEST, EquipmentSlot.LEGS)) {
            check(data.applyReady(respawned, (slot, level) -> {
                check(level == (slot == EquipmentSlot.MAINHAND ? 3 : 7), "Configured levels survive reload");
                return slot == next;
            }).equals(Set.of(next)), "Equip armor in any order: " + next);
        }
        check(data.waitingSlots(owner).equals(Set.of(EquipmentSlot.MAINHAND)), "All four armor pieces completed; weapon still waits");
        check(data.applyReady(owner, (slot, level) -> slot == EquipmentSlot.MAINHAND).size() == 1, "First weapon claims reward");
        check(data.waitingSlots(owner).isEmpty(), "Fully claimed reward removed");
        data.applyReady(owner, (slot, level) -> { throw new AssertionError("Reward replayed"); });

        // Separate gifts retain their own level, including level 0 (natural maximum).
        data.add(owner, false, 0);
        data.add(owner, false, 12);
        saved = PendingEnchantData.TYPE.codec().encodeStart(JsonOps.INSTANCE, data).getOrThrow();
        data = PendingEnchantData.TYPE.codec().parse(JsonOps.INSTANCE, saved).getOrThrow();
        List<Integer> levels = new ArrayList<>();
        data.applyReady(owner, (slot, level) -> { levels.add(level); return true; });
        check(levels.equals(List.of(0, 12)), "Multiple pending gifts preserve natural and explicit levels");
        check(data.waitingSlots(owner).isEmpty(), "Multiple gifts consumed once on the first weapon");
        System.out.println("PENDING_ENCHANT_CHECKS_OK: empty/invalid equipment, individual armor slots, weapon, levels, no replay, UUID isolation, save/reload");
    }

    static void selectedChecks(HolderLookup.Provider registries) {
        var choices = SpecialRewards.parseSelectedEnchants("""
            {"enchant_mode":"selected","enchantments":[
              {"id":"minecraft:sharpness","level":7},
              {"id":"minecraft:smite","level":12},
              {"id":"minecraft:binding_curse","level":255}]}
            """);
        check(choices.size() == 3, "Count of selected types");
        check(!SpecialRewards.enchantSelectedStack(registries, ItemStack.EMPTY, choices), "Empty hand waits");
        var stack = new ItemStack(Items.DIAMOND_PICKAXE);
        check(SpecialRewards.enchantSelectedStack(registries, stack, choices), "Selected conflicting and unsupported types allowed");
        var actual = net.minecraft.world.item.enchantment.EnchantmentHelper.getEnchantmentsForCrafting(stack);
        var lookup = registries.lookupOrThrow(net.minecraft.core.registries.Registries.ENCHANTMENT);
        for (var entry : choices.entrySet()) {
            var holder = lookup.getOrThrow(net.minecraft.resources.ResourceKey.create(
                net.minecraft.core.registries.Registries.ENCHANTMENT, net.minecraft.resources.Identifier.parse(entry.getKey())));
            check(actual.getLevel(holder) == entry.getValue(), "Exact per-type level including curse");
        }
        check(actual.size() == 3, "No unselected types added");
        SpecialRewards.enchantSelectedStack(registries, stack, choices);
        check(net.minecraft.world.item.enchantment.EnchantmentHelper.getEnchantmentsForCrafting(stack).equals(actual), "Repeated selection does not raise chosen levels");
        UUID owner = UUID.randomUUID();
        var data = new PendingEnchantData();
        data.add(owner, true, 0, choices);
        var saved = PendingEnchantData.TYPE.codec().encodeStart(JsonOps.INSTANCE, data).getOrThrow();
        data = PendingEnchantData.TYPE.codec().parse(JsonOps.INSTANCE, saved).getOrThrow();
        check(data.applyConfigured(owner, (slot, level, selected) -> {
            check(selected.equals(choices), "Selection survives world reload");
            return slot == EquipmentSlot.HEAD;
        }).equals(Set.of(EquipmentSlot.HEAD)), "Selected armor delivered per slot");
        check(data.waitingSlots(owner).size() == 3, "Unworn armor retains choices");
        for (String bad : List.of("{\"enchant_mode\":\"selected\",\"enchantments\":[]}",
                "{\"enchant_mode\":\"selected\",\"enchantments\":[{\"id\":\"minecraft:mending\",\"level\":1.5}]}")) {
            boolean rejected = false;
            try { SpecialRewards.parseSelectedEnchants(bad); } catch (RuntimeException expected) { rejected = true; }
            check(rejected, "Invalid selection rejected without granting FULL");
        }
        System.out.println("SELECTED_ENCHANT_CHECKS_OK: levels, conflicts, curses, tools, count, persistence, partial armor, validation");
    }
}
