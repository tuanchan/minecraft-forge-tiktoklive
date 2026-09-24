package vn.deadchan.tiktokmob;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Queue;
import java.util.concurrent.atomic.AtomicInteger;

/** Offline audit of the real TCP parser and queues; no listener, players or world. */
final class InteractionQueueChecks {
    private static Object field(String name) throws ReflectiveOperationException {
        var field = TikTokMobMod.class.getDeclaredField(name);
        field.setAccessible(true);
        return field.get(null);
    }
    private static String encoded(String value) {
        return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }
    static void run() {
        try {
            Queue<?> regular = (Queue<?>) field("PENDING");
            Queue<?> donations = (Queue<?>) field("PENDING_DONATIONS");
            AtomicInteger count = (AtomicInteger) field("PENDING_COUNT");
            if (!regular.isEmpty() || !donations.isEmpty() || count.get() != 0)
                throw new AssertionError("Audit requires isolated empty queues");
            var settings = new TikTokMobMod.ModSettings();
            settings.max_pending_events = 1000;
            settings.donation_priority_enabled = true;
            try {
                for (String kind : new String[]{"keep_inventory_on", "keep_inventory_off", "set_respawn",
                        "kill_player", "sky_launch", "spawn_tnt"}) {
                    TikTokMobMod.acceptLine(kind + "\t" + encoded("donor") + "\t" + encoded("Donor")
                        + "\t\t" + encoded("1") + "\tdonation\tgift", settings);
                    if (donations.size() != 1 || count.get() != 1)
                        throw new AssertionError("Gift parser rejected " + kind);
                    Object parsed = TikTokMobMod.pollPendingInteraction(true);
                    if (!parsed.toString().contains("kind=" + kind.toUpperCase(java.util.Locale.ROOT)))
                        throw new AssertionError("Wrong parsed gift kind: " + parsed);
                }
                if (SkyLaunch.targetHeight(64, 70) != 160 || SkyLaunch.targetHeight(-60, 320) != 332
                        || SkyLaunch.targetHeight(400, 70) != 496)
                    throw new AssertionError("Sky launch must clear ceilings, deep caves and high starting points");
                for (int i = 0; i < 1001; i++) {
                    String user = "audit-user-" + i % 3;
                    TikTokMobMod.acceptLine("item\t" + encoded(user) + "\t" + encoded(user)
                        + "\t\t" + encoded("minecraft:golden_apple") + "\tdonation\tgift", settings);
                }
                if (donations.size() != 1000 || count.get() != 1000 || !regular.isEmpty())
                    throw new AssertionError("Unexpected burst queue accounting");
                Object first = donations.peek();
                for (int tick = 0; tick < 1200; tick++) {
                    if (TikTokMobMod.pollPendingInteraction(false) != null)
                        throw new AssertionError("Dead player must not consume a reward");
                }
                if (donations.size() != 1000 || count.get() != 1000 || donations.peek() != first)
                    throw new AssertionError("Waiting for respawn must preserve reward order and count");
                if (TikTokMobMod.pollPendingInteraction(true) != first || count.get() != 999)
                    throw new AssertionError("Respawn resumes with exactly the first waiting reward");
                TikTokMobMod.acceptLine("item\t" + encoded("audit-next") + "\t" + encoded("Next")
                    + "\t\t" + encoded("minecraft:golden_apple") + "\tdonation\tgift", settings);
                if (donations.size() != 1000 || count.get() != 1000)
                    throw new AssertionError("Queue must accept new gifts when capacity is available");
                System.out.println("GIFT_QUEUE_AUDIT_OK: 1000 rewards retained; reward 1001 discarded at capacity; new rewards accepted after draining");
            } finally {
                donations.clear(); regular.clear(); count.set(0);
            }
        } catch (ReflectiveOperationException error) {
            throw new AssertionError(error);
        }
    }
}
