package vn.deadchan.tiktokmob;

import java.util.ArrayList;
import java.util.List;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.EntityTypes;

final class LightningCleanupChecks {
    private static void check(boolean value, String label) {
        if (!value) throw new AssertionError(label);
    }
    static void run() {
        check(LightningGift.count("1") == 5, "Legacy lightning uses five strikes");
        check(LightningGift.intervalTicks("{}") == 20, "Default one second interval");
        check(LightningGift.intervalTicks("{\"interval_seconds\":0}") == 1, "Zero means next tick, never a blocking loop");
        check(LightningGift.intervalTicks("{\"interval_seconds\":0.125}") == 3, "Fractional interval rounds up to game tick");
        check(LightningGift.count("{\"strike_count\":10001}") == 10001, "No arbitrary strike cap");
        var queue = new LightningGift.Sequence();
        queue.add(3, 4); queue.add(2, 2);
        var hits = new ArrayList<Integer>();
        for (int tick = 0; tick < 20; tick++) if (queue.advance()) hits.add(tick);
        check(hits.equals(List.of(0, 4, 8, 12, 14)), "Gift batches serialize and retain their own intervals: " + hits);
        check(queue.volleys.isEmpty(), "Completed batches drain");
        queue = new LightningGift.Sequence();
        queue.add(10001, 1);
        for (int i = 0; i < 10001; i++) check(queue.advance(), "Large count not truncated");
        check(!queue.advance(), "No extra strike");
        for (var type : List.of(EntityTypes.PLAYER, EntityTypes.IRON_GOLEM, EntityTypes.SNOW_GOLEM, EntityTypes.WOLF))
            check(!ClearToolMobs.eligible(type, true), "Protected entity " + type);
        for (var type : List.of(EntityTypes.ZOMBIE, EntityTypes.CREEPER, EntityTypes.CAT, EntityTypes.COW, EntityTypes.WITHER)) {
            check(!ClearToolMobs.eligible(type, false), "Never sweep natural mob " + type);
            check(ClearToolMobs.eligible(type, true), "Tool mob included " + type);
        }
        String message = ClearToolMobs.killMessage("Tuấn", Component.literal("Alice [02:45]"), Component.literal("Zombie")).getString();
        check(message.equals("[TikTok] Tuấn đã giết Alice [02:45] (Zombie)"), "Chat preserves killer, summon name, species");
        System.out.println("LIGHTNING_CLEANUP_OK: queue timing, large counts, protected entities, tool filter, chat names");
    }
}
