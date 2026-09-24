package vn.deadchan.tiktokmob;

import java.util.ArrayDeque;

final class DonationLimitChecks {
    static void run() {
        try {
            Class<?> type = Class.forName("vn.deadchan.tiktokmob.TikTokMobMod$SpawnedMob");
            var constructor = type.getDeclaredConstructors()[0];
            constructor.setAccessible(true);
            var count = TikTokMobMod.class.getDeclaredMethod("limitedCount", ArrayDeque.class);
            var first = TikTokMobMod.class.getDeclaredMethod("firstLimited", ArrayDeque.class);
            count.setAccessible(true); first.setAccessible(true);
            var queue = new ArrayDeque<>();
            // Donations exceed both configurable limits and precede normal mobs.
            for (int i = 0; i < 10001; i++)
                queue.add(constructor.newInstance(null, Long.MAX_VALUE, (long)i, "donation", null, null));
            if (!count.invoke(null, queue).equals(0) || first.invoke(null, queue) != null)
                throw new AssertionError("Donations cannot count toward limits or become eviction candidates");
            Object regular = constructor.newInstance(null, 1000L, 10001L, "normal", null, null);
            queue.add(regular);
            if (!count.invoke(null, queue).equals(1) || first.invoke(null, queue) != regular)
                throw new AssertionError("Only regular mobs count and are evicted, even behind donations");
            queue.remove(first.invoke(null, queue));
            if (queue.size() != 10001 || !count.invoke(null, queue).equals(0))
                throw new AssertionError("Normal eviction must retain all donations");
            System.out.println("DONATION_LIMITS_OK: 10001 donations excluded; normal eviction preserves donations");
        } catch (ReflectiveOperationException error) { throw new AssertionError(error); }
    }
}
