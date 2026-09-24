package vn.deadchan.tiktokmob;

import net.minecraft.world.phys.Vec3;

final class RewardMotionChecks {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    static void run() {
        check(SkyLaunch.readyToRelease(0.000001, true, 32, 200), "Release near apex despite rounding");
        check(!SkyLaunch.readyToRelease(30, true, 10, 200), "Do not release early");
        check(!SkyLaunch.readyToRelease(0, false, 32, 200), "Clear ceiling before release");
        check(SkyLaunch.readyToRelease(30, false, 200, 200), "Deadline prevents endless flight");
        Vec3 position = Vec3.ZERO;
        Vec3 velocity = Vec3.ZERO;
        Vec3 target = new Vec3(8, 0, 0);
        for (int tick = 0; tick < 80; tick++) {
            velocity = SpecialRewards.chaseVelocity(target.subtract(position), velocity, false);
            check(velocity.length() <= 0.320001, "Chase speed must stay bounded");
            position = position.add(velocity);
        }
        check(position.distanceTo(target) < 0.05, "TNT approaches stationary player smoothly");
        Vec3 turn = SpecialRewards.chaseVelocity(new Vec3(-8, 0, 0), new Vec3(0.32, -0.1, 0), false);
        check(turn.x > 0 && turn.x < 0.32, "Reversing target brakes before turning");
        check(turn.y == -0.1, "Chasing preserves falling velocity");
        Vec3 hop = SpecialRewards.chaseVelocity(new Vec3(3, 1, 0), Vec3.ZERO, true);
        check(hop.y > 0, "Grounded TNT hops toward target");
        check(SpecialRewards.chaseVelocity(Vec3.ZERO, Vec3.ZERO, true).equals(Vec3.ZERO),
            "Coincident target has no division by zero or forced hop");
        System.out.println("REWARD_MOTION_CHECKS_OK: apex, deadline, chase convergence, turning, gravity, hop");
    }
}
