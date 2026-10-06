package vn.deadchan.tiktokmob;

final class MissionMath {
    static long add(long current, long target) {
        return current >= target ? target : current == Long.MAX_VALUE ? Long.MAX_VALUE : current + 1;
    }
    static long subtract(long current, long points) {
        long amount = Math.max(0, points);
        return current < Long.MIN_VALUE + amount ? Long.MIN_VALUE : current - amount;
    }
    static long death(long current, long penalty, boolean percent) {
        long positive = Math.max(0, current);
        long rate = Math.min(100, Math.max(0, penalty));
        long amount = percent ? (positive / 100 * rate + (positive % 100 * rate + 99) / 100) : penalty;
        return subtract(current, amount);
    }
}
