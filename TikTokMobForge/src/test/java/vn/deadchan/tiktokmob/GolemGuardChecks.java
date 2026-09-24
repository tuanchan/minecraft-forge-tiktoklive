package vn.deadchan.tiktokmob;

import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.GoalSelector;
import net.minecraft.world.entity.animal.golem.IronGolem;

/** Exercise Minecraft's real reduced-tick scheduler without starting a world. */
final class GolemGuardChecks {
    static void run() {
        var config = new TikTokMobMod.ModSettings();
        if (GolemGuard.teleportDistance(false, config) != 20 || GolemGuard.teleportDistance(true, config) != 20)
            throw new AssertionError("Both guards default to 20 blocks");
        config.golem_teleport_distance = 35;
        config.wolf_teleport_distance = 12;
        if (GolemGuard.teleportDistance(false, config) != 35 || GolemGuard.teleportDistance(true, config) != 12)
            throw new AssertionError("Guard teleport settings must be independent");
        try {
            var type = Class.forName("vn.deadchan.tiktokmob.GolemGuard$FollowOwner");
            var constructor = type.getDeclaredConstructor(net.minecraft.world.entity.Mob.class);
            constructor.setAccessible(true);
            Goal guard = (Goal) constructor.newInstance((Object) null);
            for (int entityParity = 0; entityParity < 2; entityParity++) {
                int[] clock = {0}, scans = {0}, attacks = {0};
                Goal probe = new Goal() {
                    @Override public boolean canUse() { return true; }
                    @Override public boolean requiresUpdateEveryTick() { return guard.requiresUpdateEveryTick(); }
                    @Override public void tick() {
                        if (clock[0] % 10 == 0) scans[0]++;
                        if (clock[0] % 20 == 0) attacks[0]++;
                    }
                };
                GoalSelector selector = new GoalSelector();
                selector.addGoal(0, probe);
                selector.getAvailableGoals().forEach(goal -> goal.start());
                for (clock[0] = 1; clock[0] <= 200; clock[0]++) {
                    selector.tickRunningGoals((clock[0] + entityParity) % 2 == 0);
                }
                if (scans[0] != 20 || attacks[0] != 10)
                    throw new AssertionError("Guard starved by reduced ticks: parity=" + entityParity);
            }
            System.out.println("GOLEM_GUARD_TICKS_OK: both entity parities scan and attack on every scheduled interval");
        } catch (ReflectiveOperationException error) { throw new AssertionError(error); }
    }
}
