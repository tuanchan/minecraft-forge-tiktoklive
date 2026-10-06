package vn.deadchan.tiktokmob;

import com.google.gson.*;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.Permissions;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

final class RuntimeSettings {
    static final Gson JSON = new GsonBuilder().setPrettyPrinting().create();
    static final Path PATH = Path.of("config", "tiktokmob.json");
    record Field(String key, String label, int group, String kind, double min, double max, String initial) {
        JsonElement parse(String text) {
            try {
                if (kind.equals("direction")) {
                    if (!List.of("front", "right", "left", "back", "random").contains(text)) throw new IllegalArgumentException();
                    return new JsonPrimitive(text);
                }
                if (kind.equals("bool")) {
                    if (!text.equals("true") && !text.equals("false")) throw new IllegalArgumentException();
                    return new JsonPrimitive(Boolean.parseBoolean(text));
                }
                if (kind.equals("mob")) {
                    String id = text.strip().toLowerCase(Locale.ROOT);
                    if (!id.contains(":")) id = "minecraft:" + id;
                    Identifier identifier = Identifier.tryParse(id);
                    if (identifier == null || !BuiltInRegistries.ENTITY_TYPE.containsKey(identifier)) throw new IllegalArgumentException();
                    var type = BuiltInRegistries.ENTITY_TYPE.getValue(identifier);
                    if (type.getCategory() == net.minecraft.world.entity.MobCategory.MISC
                        && net.minecraft.world.item.SpawnEggItem.byId(type).isEmpty()
                        && !id.equals("minecraft:iron_golem") && !id.equals("minecraft:snow_golem")) throw new IllegalArgumentException();
                    return new JsonPrimitive(id.startsWith("minecraft:") ? id.substring(10) : id);
                }
                double value = Double.parseDouble(text);
                if (!Double.isFinite(value) || value < min || value > max || (kind.equals("int") && value != Math.rint(value))) throw new IllegalArgumentException();
                return kind.equals("int") ? new JsonPrimitive((int)value) : new JsonPrimitive(value);
            } catch (Exception error) {
                throw new IllegalArgumentException(label + (kind.equals("mob") ? ": ID mob không hợp lệ" : ": giá trị không hợp lệ (" + min + "–" + max + ")"));
            }
        }
    }
    static final List<Field> FIELDS = List.of(
        new Field("golem_teleport_distance", "Golem: khoảng dịch chuyển (block)", 0, "number", 5, 128, "20"),
        new Field("wolf_teleport_distance", "Chó giáp: khoảng dịch chuyển (block)", 0, "number", 5, 128, "20"),
        new Field("max_mobs_per_user", "Mob tối đa mỗi người", 0, "int", 1, 1000, "4"),
        new Field("max_mobs_total", "Mob tối đa toàn world", 0, "int", 1, 10000, "4"),
        new Field("mob_lifetime_seconds", "Vòng đời mob (giây)", 0, "number", 1, 86400, "180"),
        new Field("max_interactions_per_tick", "Tương tác mỗi tick", 0, "int", 1, 1000, "5"),
        new Field("spawn_min_distance", "Khoảng sinh tối thiểu", 0, "number", 0, 128, "3"),
        new Field("spawn_max_distance", "Khoảng sinh tối đa", 0, "number", 0, 128, "6"),
        new Field("spawn_direction", "Vị trí triệu hồi", 0, "direction", 0, 0, "front"),
        new Field("spawn_height_offset", "Độ cao sinh mob", 0, "number", -64, 64, "0"),
        new Field("max_pending_events", "Hàng đợi gameplay", 0, "int", 10, 100000, "1000"),
        new Field("creeper_break_blocks", "Creeper tool phá khối", 0, "bool", 0, 1, "false"),
        new Field("tnt_break_blocks", "TNT tool phá khối", 0, "bool", 0, 1, "true"),
        new Field("enderman_targets_player", "Enderman nhắm người chơi", 0, "bool", 0, 1, "true"),
        new Field("mobs_persistent", "Chống biến mất tự nhiên", 0, "bool", 0, 1, "true"),
        new Field("show_death_counter", "Hiện bộ đếm số lần chết", 0, "bool", 0, 1, "true"),
        new Field("show_countdown_in_name", "Hiện đếm ngược tên mob", 0, "bool", 0, 1, "true"),
        new Field("view_enabled", "Bật tương tác View", 5, "bool", 0, 1, "true"),
        new Field("view_mob_type", "Mob theo người xem", 5, "mob", 0, 0, "zombie"),
        new Field("view_spawn_count", "Mob mỗi view mỗi đợt", 5, "int", 1, 100, "1"),
        new Field("view_interval_seconds", "Chu kỳ View (giây)", 5, "number", 1, 86400, "60"),
        new Field("view_max_mobs_per_round", "Mob tối đa mỗi đợt View", 5, "int", 1, 1000, "20"),
        new Field("follow_mob_type", "Mob khi theo dõi", 1, "mob", 0, 0, "creeper"),
        new Field("follow_spawn_count", "Số mob mỗi lượt theo dõi", 1, "int", 1, 100, "1"),
        new Field("comment_mob_type", "Mob khi bình luận", 2, "mob", 0, 0, "zombie"),
        new Field("comment_spawn_count", "Số mob mỗi bình luận", 2, "int", 1, 100, "1"),
        new Field("comment_limit", "Số bình luận / người", 2, "int", 1, 100000, "1"),
        new Field("comment_cooldown_seconds", "Thời gian chờ riêng (giây)", 2, "number", 1, 86400, "10"),
        new Field("share_mob_type", "Mob khi chia sẻ", 3, "mob", 0, 0, "enderman"),
        new Field("share_spawn_count", "Số mob mỗi chia sẻ", 3, "int", 1, 100, "1"),
        new Field("share_limit", "Số chia sẻ / người", 3, "int", 1, 100000, "1"),
        new Field("share_cooldown_seconds", "Thời gian chờ riêng (giây)", 3, "number", 1, 86400, "10"),
        new Field("like_mob_type", "Mob khi đủ tim", 4, "mob", 0, 0, "skeleton"),
        new Field("likes_per_skeleton", "Số tim mỗi lượt", 4, "int", 1, 100000, "50"),
        new Field("like_spawn_count", "Số mob mỗi mốc tim", 4, "int", 1, 100, "1")
    );
    static boolean canEdit(ServerPlayer player) {
        return player.level().getServer().isSingleplayerOwner(player.nameAndId())
            || player.permissions().hasPermission(Permissions.COMMANDS_GAMEMASTER);
    }
    static JsonObject read(Path path) throws Exception {
        return Files.exists(path) ? JsonParser.parseString(Files.readString(path, StandardCharsets.UTF_8)).getAsJsonObject() : new JsonObject();
    }
    static JsonObject snapshot(TikTokMobMod.ModSettings settings) {
        JsonObject result = JSON.toJsonTree(settings).getAsJsonObject();
        try {
            JsonObject disk = read(PATH);
            for (Field field : FIELDS) if (!result.has(field.key))
                result.add(field.key, disk.has(field.key) ? disk.get(field.key) : field.parse(field.initial));
        } catch (Exception ignored) { }
        return result;
    }
    static JsonObject merge(JsonObject original, JsonObject patch) {
        JsonObject result = original.deepCopy();
        for (var entry : patch.entrySet()) {
            Field field = FIELDS.stream().filter(f -> f.key.equals(entry.getKey())).findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Không hỗ trợ cài đặt " + entry.getKey()));
            result.add(field.key, field.parse(entry.getValue().getAsString()));
        }
        double min = result.has("spawn_min_distance") ? result.get("spawn_min_distance").getAsDouble() : 3;
        double max = result.has("spawn_max_distance") ? result.get("spawn_max_distance").getAsDouble() : 6;
        if (max < min) throw new IllegalArgumentException("Khoảng sinh tối đa phải từ khoảng tối thiểu trở lên");
        return result;
    }
    static void savePatch(Path path, JsonObject patch) throws Exception {
        Files.createDirectories(path.toAbsolutePath().getParent());
        // Same byte-range lock as Python; temporary file names are writer-specific.
        try (FileChannel channel = FileChannel.open(Path.of(path + ".lock"), StandardOpenOption.CREATE, StandardOpenOption.WRITE);
             var lock = channel.tryLock(0, 1, false)) {
            if (lock == null) throw new IllegalStateException("GUI đang lưu; bấm Lưu lại sau giây lát");
            JsonObject merged = merge(read(path), patch);
            Path temporary = path.resolveSibling(path.getFileName() + ".minecraft.tmp");
            Files.writeString(temporary, JSON.toJson(merged) + "\n", StandardCharsets.UTF_8);
            try { Files.move(temporary, path, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING); }
            catch (AtomicMoveNotSupportedException ignored) { Files.move(temporary, path, StandardCopyOption.REPLACE_EXISTING); }
        }
    }
}
