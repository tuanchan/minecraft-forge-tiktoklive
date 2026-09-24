package vn.deadchan.tiktokmob;

import com.mojang.serialization.JsonOps;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.enchantment.EnchantmentHelper;
import net.minecraft.world.item.enchantment.Enchantments;
import java.util.UUID;

final class FullArmorChecks {
    static void run(HolderLookup.Provider registries) {
        var enchantments = registries.lookupOrThrow(Registries.ENCHANTMENT);
        var ops = registries.createSerializationContext(JsonOps.INSTANCE);
        for (boolean netherite : new boolean[]{false, true}) {
            var stacks = SpecialRewards.enchantedArmorSet(registries, netherite);
            if (stacks.size() != 4 || !stacks.getFirst().is(netherite ? Items.NETHERITE_HELMET : Items.DIAMOND_HELMET))
                throw new AssertionError("Wrong armor set");
            GiftBagData bag = new GiftBagData();
            UUID owner = UUID.randomUUID();
            stacks.forEach(stack -> bag.deposit(owner, stack));
            var restored = GiftBagData.TYPE.codec().parse(ops,
                GiftBagData.TYPE.codec().encodeStart(ops, bag).getOrThrow()).getOrThrow();
            if (restored.count(owner) != 4) throw new AssertionError("All four pieces must survive storage");
            for (var entry : restored.page(owner, 0).entries()) {
                ItemStack stack = entry.stack();
                var actual = EnchantmentHelper.getEnchantmentsForCrafting(stack);
                if (actual.getLevel(enchantments.getOrThrow(Enchantments.MENDING)) != 4)
                    throw new AssertionError("Mending IV missing");
                int expectedCount = stack.is(netherite ? Items.NETHERITE_HELMET : Items.DIAMOND_HELMET) ? 9
                    : stack.is(netherite ? Items.NETHERITE_LEGGINGS : Items.DIAMOND_LEGGINGS) ? 8
                    : stack.is(netherite ? Items.NETHERITE_BOOTS : Items.DIAMOND_BOOTS) ? 11 : 7;
                if (actual.size() != expectedCount) throw new AssertionError("Missing slot enchantments: " + stack);
                actual.entrySet().forEach(enchant -> {
                    if (enchant.getIntValue() != 4) throw new AssertionError("Every enchant must be IV");
                });
                for (var key : java.util.List.of(Enchantments.BINDING_CURSE, Enchantments.VANISHING_CURSE))
                    if (actual.getLevel(enchantments.getOrThrow(key)) != 0) throw new AssertionError("Curse present");
                for (var key : java.util.List.of(Enchantments.PROTECTION, Enchantments.FIRE_PROTECTION,
                        Enchantments.BLAST_PROTECTION, Enchantments.PROJECTILE_PROTECTION,
                        Enchantments.THORNS, Enchantments.UNBREAKING))
                    if (actual.getLevel(enchantments.getOrThrow(key)) != 4) throw new AssertionError("Missing common armor enchant");
            }
        }
        System.out.println("FULL_ARMOR_CHECKS_OK: both sets, all supported enchants IV, Mending, no curses, gift bag save/reload");
    }
}
