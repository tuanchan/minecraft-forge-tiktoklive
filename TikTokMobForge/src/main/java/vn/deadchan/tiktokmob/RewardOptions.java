package vn.deadchan.tiktokmob;

/** Legacy numeric payloads retain defaults; new per-gift options use JSON. */
final class RewardOptions {
    static double number(String payload, String key, double fallback, double min, double max) {
        try {
            var object = com.google.gson.JsonParser.parseString(payload).getAsJsonObject();
            if (!object.has(key)) return fallback;
            double value = object.get(key).getAsDouble();
            return Double.isFinite(value) ? Math.max(min, Math.min(max, value)) : fallback;
        } catch (RuntimeException ignored) { return fallback; }
    }
    static Boolean blockOverride(String payload) {
        return booleanOption(payload, "break_blocks");
    }
    static Boolean booleanOption(String payload, String key) {
        try {
            var value = com.google.gson.JsonParser.parseString(payload).getAsJsonObject().get(key);
            return value != null && value.isJsonPrimitive() && value.getAsJsonPrimitive().isBoolean()
                ? value.getAsBoolean() : null;
        } catch (RuntimeException ignored) { return null; }
    }
    static String mobId(String payload) {
        try { return com.google.gson.JsonParser.parseString(payload).getAsJsonObject().get("mob").getAsString(); }
        catch (RuntimeException ignored) { return payload; }
    }
    static int ticks(String payload, String key, double fallback) {
        return (int)Math.ceil(number(payload, key, fallback, key.equals("fuse_seconds") ? 0 : 0.1, 3600) * 20);
    }
}
