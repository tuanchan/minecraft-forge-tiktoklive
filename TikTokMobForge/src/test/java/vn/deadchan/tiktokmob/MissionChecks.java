package vn.deadchan.tiktokmob;

public final class MissionChecks {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        check(MissionMath.add(99, 100) == 100, "Completes goal");
        check(MissionMath.add(100, 100) == 100, "Does not overflow completed goal");
        check(MissionMath.subtract(3, 9) == -6, "Gift can make progress negative");
        check(MissionMath.subtract(-6, 9) == -15, "Repeated gifts continue below zero");
        check(MissionMath.subtract(Long.MIN_VALUE + 2, 9) == Long.MIN_VALUE, "Penalty cannot overflow below long minimum");
        check(MissionMath.death(77, 10, false) == 67, "Death points");
        check(MissionMath.death(77, 10, true) == 69, "Percentage rounds penalty up");
        check(MissionMath.death(77, 0, true) == 77, "Zero penalty preserves progress");
        check(MissionMath.death(77, 100, true) == 0, "Full reset percentage");
        check(MissionMath.death(Integer.MAX_VALUE, 100, true) == 0, "No percentage overflow");
        check(MissionMath.death(3, 9, false) == -6, "Death points can make progress negative");
        check(MissionMath.death(-6, 10, true) == -6, "Percentage penalty does not reverse negative progress");
        long value=100; for(int combo=0;combo<3;combo++) for(int amount=0;amount<2;amount++)value=MissionMath.subtract(value,7);
        check(value==58,"Gift amount and combo stack");
        value=10; for(int combo=0;combo<3;combo++) for(int amount=0;amount<2;amount++)value=MissionMath.subtract(value,7);
        check(value==-32,"Gift amount and combo can stack below zero");
        check(MissionMath.add(MissionMath.subtract(100, 1),100)==100,"Can complete again after penalty");
        var rule = new Missions.Rule("zombies", "Giết zombie", "kill", "minecraft:zombie", true, true,
            100, 10, 10, "percent", "2d", 50, 15, 1, 0);
        rule.validate();
        check(rule.matches("kill", "minecraft:zombie", true), "Summoned zombie counts");
        check(!rule.matches("kill", "minecraft:zombie", false), "Natural zombie excluded when selected");
        check(!rule.matches("kill", "minecraft:skeleton", true), "Other species excluded");
        check(!rule.matches("diamond", "", false), "Mining does not count as a kill");
        var total = new Missions.Rule("total", "Tổng mob", "kill", "*", true, false,
            100, 10, 0, "points", "3d", 50, 15, 1, 0);
        check(total.matches("kill", "minecraft:skeleton", false), "Total includes natural mobs");
        var legacy = new Missions.Rule("legacy", "Cũ", "diamond", "*", true, false,
            100, 0, 0, "points", "2d", 50, 15, 1, 0);
        legacy.validate();
        check(legacy.effectiveMilestones()==10,"Legacy missions default to ten milestones");
        var player=java.util.UUID.randomUUID();
        var data=new MissionData();data.set(player,rule,77);
        check(data.current(java.util.UUID.randomUUID(),rule)==0,"Player progress is isolated");
        check(data.current(player,total)==0,"Mission progress is isolated");
        var json=MissionData.CODEC.encodeStart(com.mojang.serialization.JsonOps.INSTANCE,data).getOrThrow();
        var loaded=MissionData.CODEC.parse(com.mojang.serialization.JsonOps.INSTANCE,json).getOrThrow();
        check(loaded.current(player,rule)==77,"World save and reload preserves progress");
        loaded.set(player, rule, -25);
        check(loaded.current(player,rule)==-25,"World data preserves negative progress");
        var negativeJson=MissionData.CODEC.encodeStart(com.mojang.serialization.JsonOps.INSTANCE,loaded).getOrThrow();
        var negativeReload=MissionData.CODEC.parse(com.mojang.serialization.JsonOps.INSTANCE,negativeJson).getOrThrow();
        check(negativeReload.current(player,rule)==-25,"World save and reload preserves negative progress");
        var reset=new Missions.Rule("zombies", "Giết zombie", "kill", "minecraft:zombie", true, true,
            100, 10, 10, "percent", "2d", 50, 15, 1, 1);
        check(loaded.current(player,reset)==0,"Reset revision clears progress");
        Missions.register();
        var deathBus = net.minecraftforge.event.entity.living.LivingDeathEvent.BUS;
        deathBus.addListener(net.minecraftforge.eventbus.api.listener.Priority.HIGHEST, event -> true);
        // A canceled event must return before accessing its entity or mutating mission progress.
        deathBus.post(new net.minecraftforge.event.entity.living.LivingDeathEvent(null, null));
        System.out.println("MISSION_CHECKS_OK");
    }
}
