package vn.deadchan.tiktokmob;

import com.google.gson.JsonParser;
import com.google.gson.JsonObject;
import java.nio.file.Files;

final class RuntimeSettingsChecks {
    static void run() {
        try {
            var directory = Files.createTempDirectory("tiktok-runtime-check-");
            var path = directory.resolve("settings.json");
            Files.writeString(path, "{\"max_mobs_total\":500,\"follow_spawn_count\":3,\"preserved\":{\"value\":42}}");
            RuntimeSettings.savePatch(path, JsonParser.parseString("{\"max_mobs_per_user\":20,\"share_mob_type\":\"minecraft:blaze\"}").getAsJsonObject());
            var result = RuntimeSettings.read(path);
            check(result.get("max_mobs_total").getAsInt() == 500, "concurrent fields preserved");
            check(result.getAsJsonObject("preserved").get("value").getAsInt() == 42, "unknown fields preserved");
            check(result.get("share_mob_type").getAsString().equals("blaze"), "mob normalized for bridge");
            String before = Files.readString(path);
            for (String bad : new String[]{"{\"max_mobs_total\":0}", "{\"follow_spawn_count\":1.2}", "{\"spawn_min_distance\":8,\"spawn_max_distance\":2}", "{\"bridge_port\":1234}", "{\"like_mob_type\":\"minecraft:item\"}", "{\"like_mob_type\":\"minecraft:missing\"}"}) {
                boolean rejected = false;
                try { RuntimeSettings.savePatch(path, JsonParser.parseString(bad).getAsJsonObject()); }
                catch (IllegalArgumentException expected) { rejected = true; }
                check(rejected && Files.readString(path).equals(before), "invalid patch cannot change disk: " + bad);
            }
            check(RuntimeSettings.FIELDS.size() == 33, "all requested fields exposed");
            RuntimeSettings.savePatch(path, JsonParser.parseString("{\"golem_teleport_distance\":35,\"wolf_teleport_distance\":12}").getAsJsonObject());
            var guards = RuntimeSettings.read(path);
            check(guards.get("golem_teleport_distance").getAsDouble() == 35
                && guards.get("wolf_teleport_distance").getAsDouble() == 12, "guard distances roundtrip independently");
            for (String key : new String[]{"golem_teleport_distance", "wolf_teleport_distance"}) {
                for (double value : new double[]{0, 4, 129, Double.NaN}) {
                    JsonObject invalid = new JsonObject(); invalid.addProperty(key, value);
                    boolean rejected = false;
                    try { RuntimeSettings.merge(guards, invalid); }
                    catch (IllegalArgumentException expected) { rejected = true; }
                    check(rejected, "invalid guard distance rejected");
                }
            }
            JsonObject toggle = new JsonObject();
            toggle.addProperty("show_death_counter", false);
            check(!RuntimeSettings.merge(new JsonObject(), toggle).get("show_death_counter").getAsBoolean(), "death HUD toggle");
            for (String direction : new String[]{"front", "right", "left", "back", "random"}) {
                JsonObject patch = new JsonObject();
                patch.addProperty("spawn_direction", direction);
                check(RuntimeSettings.merge(new JsonObject(), patch).get("spawn_direction").getAsString().equals(direction), "spawn direction roundtrip");
            }
            Files.delete(path); Files.delete(directory.resolve("settings.json.lock")); Files.delete(directory);
            System.out.println("RUNTIME_SETTINGS_OK: fields, merge, atomic persistence, validation");
        } catch (Exception error) { throw new AssertionError(error); }
    }
    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); }
}
