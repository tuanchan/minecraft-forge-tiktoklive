package vn.deadchan.tiktokmob;

import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraftforge.event.entity.living.LivingDropsEvent;

/** Cook only the meat dropped by livestock summoned through the mod. */
final class SummonedMeatDrops {
    static void register() {
        LivingDropsEvent.BUS.addListener(event -> {
            var entity = event.getEntity();
            if (!entity.entityTags().contains("tiktokmob:summoned")) return false;

            Item raw;
            Item cooked;
            var type = entity.getType();
            if (type == EntityTypes.COW || type == EntityTypes.MOOSHROOM) {
                raw = Items.BEEF;
                cooked = Items.COOKED_BEEF;
            } else if (type == EntityTypes.SHEEP) {
                raw = Items.MUTTON;
                cooked = Items.COOKED_MUTTON;
            } else if (type == EntityTypes.CHICKEN) {
                raw = Items.CHICKEN;
                cooked = Items.COOKED_CHICKEN;
            } else if (type == EntityTypes.PIG) {
                raw = Items.PORKCHOP;
                cooked = Items.COOKED_PORKCHOP;
            } else {
                return false;
            }

            for (var drop : event.getDrops()) {
                var stack = drop.getItem();
                if (stack.is(raw)) drop.setItem(stack.transmuteCopy(cooked, stack.getCount()));
            }
            return false;
        });
    }
}
