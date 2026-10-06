from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import zipfile


def inventory_item_ids(minecraft_directory: str | Path) -> set[str]:
    """Item definitions, not language keys: translations include non-item aliases."""
    selected = Path(minecraft_directory).expanduser()
    version = "26.2"
    try:
        metadata = json.loads((selected / "minecraftinstance.json").read_text(encoding="utf-8-sig"))
        loader = json.loads(metadata.get("baseModLoader", {}).get("versionJson", "{}"))
        version = str(loader.get("inheritsFrom") or version)
    except (OSError, ValueError, TypeError):
        pass
    roots = [selected, selected.parent.parent / "Install"]
    for root in roots:
        jar = root / "versions" / version / f"{version}.jar"
        try:
            with zipfile.ZipFile(jar) as archive:
                ids = {Path(name).stem for name in archive.namelist()
                       if name.startswith("assets/minecraft/items/") and name.endswith(".json")}
                if ids:
                    return ids - {"air"}
        except (OSError, zipfile.BadZipFile):
            continue
    manifest = Path(__file__).resolve().parents[1] / "web/assets/minecraft-inventory/manifest.json"
    try:
        return set(json.loads(manifest.read_text(encoding="utf-8"))["items"])
    except (OSError, ValueError, KeyError):
        return set()


@dataclass(frozen=True)
class CatalogEntry:
    kind: str
    target: str
    vietnamese_name: str
    group: str

    @property
    def display(self) -> str:
        return f"{self.vietnamese_name} — {self.target}"


SPECIAL_REWARDS = (
    CatalogEntry("special", "mission_penalty", "Trừ tiến độ nhiệm vụ · chọn nhiệm vụ và số điểm", "Nhiệm vụ"),
    CatalogEntry("special", "lightning_player", "Sấm sét vào người chơi · xuyên mái nhà · chỉnh số tia / nghỉ", "Chơi khăm"),
    CatalogEntry("special", "clear_tool_mobs", "Dọn quái tool · chừa golem và chó · ghi tên vào chat", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "keep_inventory_on", "Bật keep · giữ đồ và kinh nghiệm khi chết", "Luật thế giới"),
    CatalogEntry("special", "keep_inventory_off", "Tắt keep · rơi đồ và kinh nghiệm khi chết", "Luật thế giới"),
    CatalogEntry("special", "set_respawn", "Tạo điểm hồi sinh tại vị trí người chơi", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "kill_player", "Giết người chơi", "Chơi khăm"),
    CatalogEntry("special", "sky_launch", "Bay nhanh thẳng lên trời · xuyên trần", "Chơi khăm"),
    CatalogEntry("special", "spawn_tnt", "TNT đuổi theo · tùy chỉnh thời gian nổ", "Chơi khăm"),
    CatalogEntry("special", "armored_wolf", "Triệu hồi chó sói mặc giáp bảo vệ", "Vệ sĩ"),
    CatalogEntry("special", "divine_cat", "Triệu hồi mèo thần 200 máu · theo chủ đuổi Creeper", "Vệ sĩ"),
    CatalogEntry("special", "netherite_armor_full4", "Bộ giáp Netherite FULL enchant IV · gồm Sửa chữa", "Bộ trang bị"),
    CatalogEntry("special", "diamond_armor_full4", "Bộ giáp kim cương FULL enchant IV · gồm Sửa chữa", "Bộ trang bị"),
    CatalogEntry("special", "clear_inventory", "Clear sạch đồ người chơi · túi đồ, giáp, hai tay", "Chơi khăm"),
    CatalogEntry("special", "troll_chicken", "Gà xuất hiện · gợi ý 1 xu", "Chơi khăm"),
    CatalogEntry("special", "troll_cobweb", "Tơ nhện · tùy chỉnh bán kính và thời gian", "Chơi khăm"),
    CatalogEntry("special", "troll_pumpkin", "Đội bí ngô tạm thời · giữ lại mũ cũ", "Chơi khăm"),
    CatalogEntry("special", "troll_slowness", "Chậm chạp 10 giây · gợi ý 20 xu", "Chơi khăm"),
    CatalogEntry("special", "troll_teleport", "Dịch chuyển 5–10 block · gợi ý 50 xu", "Chơi khăm"),
    CatalogEntry("special", "troll_creeper", "Creeper không phá block · gợi ý 100 xu", "Chơi khăm"),
    CatalogEntry("special", "troll_anvil", "Đe rơi liên tục · tùy chỉnh khoảng cách", "Chơi khăm"),
    CatalogEntry("special", "troll_hotbar", "Xáo trộn hotbar · gợi ý 500 xu", "Chơi khăm"),
    CatalogEntry("special", "troll_warden", "Tiếng Warden hù dọa · gợi ý 1.000 xu", "Chơi khăm"),
    CatalogEntry("special", "troll_box", "Troll Box · 3 trò ngẫu nhiên · quà lớn", "Chơi khăm"),
    CatalogEntry("special", "enchant_armor", "Phù phép giáp · FULL / tự chọn loại và cấp", "Enchant · phù phép"),
    CatalogEntry("special", "enchant_weapon", "Phù phép đồ tay chính · FULL / tự chọn loại và cấp", "Enchant · phù phép"),
    CatalogEntry("special", "repair_armor", "Sửa đầy độ bền giáp đang mặc", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "repair_hand", "Sửa đồ đang cầm", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "full_heal", "Hồi đầy máu và thức ăn", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "experience", "Tặng cấp kinh nghiệm", "Hiệu ứng · chọn cấp"),
    CatalogEntry("special", "absorption", "Cộng tim vàng", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "iron_armor", "Tặng trọn bộ giáp sắt", "Bộ trang bị"),
    CatalogEntry("special", "netherite_armor", "Tặng trọn bộ giáp Netherite", "Bộ trang bị"),
    CatalogEntry("special", "golden_apple", "Tặng táo vàng", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "regeneration", "Hồi phục", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "shield", "Tặng khiên", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "money_gun", "Cung và mũi tên", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "diamond_sword", "Tặng kiếm kim cương", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "diamond_armor", "Tặng bộ giáp kim cương", "Hiệu ứng đặc biệt"),
    CatalogEntry("special", "netherite_power", "Bộ Netherite và cường hóa", "Hiệu ứng đặc biệt"),
)

HOSTILE_MOBS = {
    "blaze", "bogged", "breeze", "camel_husk", "cave_spider", "creaking",
    "creaking_transient", "creeper",
    "drowned", "elder_guardian", "ender_dragon", "endermite", "evoker",
    "ghast", "guardian", "hoglin", "husk", "illusioner", "magma_cube",
    "killer_bunny", "parched", "phantom", "piglin_brute", "pillager", "ravager", "shulker",
    "silverfish", "skeleton", "slime", "stray", "vex", "vindicator",
    "sulfur_cube", "warden", "witch", "wither", "wither_skeleton", "zoglin", "zombie",
    "zombie_nautilus", "zombie_villager",
}

FRIENDLY_MOBS = {
    "allay", "armadillo", "axolotl", "bat", "camel", "cat", "chicken",
    "cod", "copper_golem", "cow", "donkey", "frog", "glow_squid",
    "happy_ghast", "horse", "iron_golem", "mooshroom", "mule", "nautilus", "ocelot",
    "parrot", "pig", "rabbit", "salmon", "sheep", "skeleton_horse",
    "sniffer", "snow_golem", "squid", "strider", "tadpole", "tropical_fish",
    "turtle", "villager", "wandering_trader", "wolf", "zombie_horse",
}

NON_MOB_ENTITIES = {
    "area_effect_cloud", "armor_stand", "arrow", "block_display", "boat",
    "chest_boat", "chest_minecart", "command_block_minecart", "dragon_fireball",
    "egg", "ender_pearl", "end_crystal", "evoker_fangs", "experience_bottle",
    "experience_orb", "eye_of_ender", "falling_block", "fireball", "firework_rocket",
    "fishing_bobber", "furnace_minecart", "glow_item_frame", "hopper_minecart",
    "interaction", "item", "item_display", "item_frame", "leash_knot",
    "lightning_bolt", "llama_spit", "marker", "minecart", "ominous_item_spawner",
    "painting", "player", "potion", "shulker_bullet", "small_fireball",
    "snowball", "spawner_minecart", "spectral_arrow", "text_display", "tnt",
    "tnt_minecart", "trident", "wind_charge", "wither_skull", "breeze_wind_charge",
    "falling_block_type", "lingering_potion", "mannequin", "splash_potion",
}

ATTACK_EXACT = {"arrow", "bow", "crossbow", "trident", "mace", "wind_charge", "fire_charge"}
ATTACK_SUFFIXES = ("_sword", "_axe", "_pickaxe", "_spear", "_arrow")
GIFT_ITEM_EXACT = {"golden_apple"}
DEFENSE_TOKENS = (
    "_helmet", "_chestplate", "_leggings", "_boots", "shield", "totem_of_undying",
    "elytra", "horse_armor", "wolf_armor", "nautilus_armor", "turtle_helmet",
)


def _candidate_asset_directories(minecraft_directory: str | Path) -> list[Path]:
    """Return launcher asset locations associated with a game/instance folder."""
    selected = Path(minecraft_directory).expanduser()
    candidates = [selected / "assets"]

    # CurseForge instances live at <root>/Instances/<name>, while its shared
    # Minecraft assets live at <root>/Install/assets.
    for parent in selected.parents:
        candidates.extend((parent / "assets", parent / "Install" / "assets"))

    result: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve(strict=False)).casefold()
        if key not in seen and (candidate / "indexes").is_dir():
            seen.add(key)
            result.append(candidate)
    return result


def _load_vietnamese_language(minecraft_directory: str | Path) -> dict[str, str]:
    for assets in _candidate_asset_directories(minecraft_directory):
        indexes = assets / "indexes"
        candidates = sorted(indexes.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for index_path in candidates:
            try:
                index = json.loads(index_path.read_text(encoding="utf-8-sig"))
                entry = index.get("objects", {}).get("minecraft/lang/vi_vn.json")
                if not entry:
                    continue
                digest = str(entry["hash"])
                language_path = assets / "objects" / digest[:2] / digest
                if language_path.is_file():
                    data = json.loads(language_path.read_text(encoding="utf-8-sig"))
                    if isinstance(data, dict):
                        return {str(key): str(value) for key, value in data.items()}
            except (OSError, ValueError, KeyError):
                continue
    return {}


def _fallback_name(identifier: str) -> str:
    return identifier.removeprefix("minecraft:").replace("_", " ").title()


def load_minecraft_catalog(minecraft_directory: str | Path) -> tuple[list[CatalogEntry], list[CatalogEntry]]:
    language = _load_vietnamese_language(minecraft_directory)
    entity_names = {
        key.removeprefix("entity.minecraft."): value
        for key, value in language.items()
        if key.startswith("entity.minecraft.") and "." not in key.removeprefix("entity.minecraft.")
    }

    mob_ids = set(entity_names)
    mob_ids.update(
        key.removeprefix("item.minecraft.").removesuffix("_spawn_egg")
        for key in language
        if key.startswith("item.minecraft.") and key.endswith("_spawn_egg")
    )
    mob_ids.difference_update(NON_MOB_ENTITIES)
    mob_ids = {
        mob_id
        for mob_id in mob_ids
        if not mob_id.endswith(("_boat", "_chest_boat", "_minecart", "_raft"))
        and not any(token in mob_id for token in ("display", "projectile"))
    }
    mobs: list[CatalogEntry] = []
    for mob_id in sorted(mob_ids):
        if mob_id in HOSTILE_MOBS:
            group = "Thù địch"
        elif mob_id in FRIENDLY_MOBS:
            group = "Thân thiện"
        else:
            group = "Trung lập"
        mobs.append(
            CatalogEntry(
                "mob",
                f"minecraft:{mob_id}",
                entity_names.get(mob_id, _fallback_name(mob_id)),
                group,
            )
        )

    item_names = {
        key.removeprefix("item.minecraft."): value
        for key, value in language.items()
        if key.startswith("item.minecraft.") and "." not in key.removeprefix("item.minecraft.")
    }
    block_names = {
        key.removeprefix("block.minecraft."): value
        for key, value in language.items()
        if key.startswith("block.minecraft.") and "." not in key.removeprefix("block.minecraft.")
    }
    for block_id, name in block_names.items():
        item_names.setdefault(block_id, name)
    registered_items = inventory_item_ids(minecraft_directory)
    if registered_items:
        item_names = {key: item_names.get(key, _fallback_name(key)) for key in registered_items}
    items: list[CatalogEntry] = []
    for item_id, name in sorted(item_names.items()):
        is_attack = item_id in ATTACK_EXACT or item_id.endswith(ATTACK_SUFFIXES)
        is_defense = any(token in item_id for token in DEFENSE_TOKENS)
        is_gift_item = item_id in GIFT_ITEM_EXACT
        group = (
            "Tấn công và phòng thủ"
            if is_attack and is_defense
            else "Tấn công"
            if is_attack
            else "Phòng thủ"
            if is_defense
            else "Vật phẩm quà"
            if is_gift_item
            else "Trứng sinh mob"
            if item_id.endswith("_spawn_egg")
            else "Khối"
            if item_id in block_names
            else "Vật phẩm"
        )
        items.append(CatalogEntry("item", f"minecraft:{item_id}", name, group))

    if not mobs:
        mobs = [
            CatalogEntry("mob", "minecraft:skeleton", "Bộ xương", "Thù địch"),
            CatalogEntry("mob", "minecraft:zombie", "Thây ma", "Thù địch"),
            CatalogEntry("mob", "minecraft:enderman", "Người Ender", "Trung lập"),
            CatalogEntry("mob", "minecraft:creeper", "Creeper", "Thù địch"),
            CatalogEntry("mob", "minecraft:villager", "Dân làng", "Thân thiện"),
            CatalogEntry("mob", "minecraft:iron_golem", "Người sắt", "Thân thiện"),
        ]
    if not items:
        items = [
            CatalogEntry("item", "minecraft:diamond_sword", "Kiếm kim cương", "Tấn công"),
            CatalogEntry("item", "minecraft:bow", "Cung", "Tấn công"),
            CatalogEntry("item", "minecraft:shield", "Khiên", "Phòng thủ"),
            CatalogEntry("item", "minecraft:diamond_chestplate", "Áo giáp kim cương", "Phòng thủ"),
        ]
    return mobs, items
