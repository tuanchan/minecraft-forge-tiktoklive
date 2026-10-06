from pathlib import Path
root=Path('TikTokMobForge')
j=root/'src/main/java/vn/deadchan/tiktokmob'
def edit(p,a,b):
 s=p.read_text(encoding='utf-8'); assert a in s,(p,a[:100]); p.write_text(s.replace(a,b),encoding='utf-8')
edit(j/'PinnedCommentBoard.java','double side = 0, height = 0.15, scale = 1;','double side = 0, height = 0.15, scale = 1, distance = 3;')
edit(j/'PinnedCommentBoard.java','static boolean scroll(double steps)', 'static boolean scroll(double steps, boolean distanceMode)')
edit(j/'PinnedCommentBoard.java','position.scale = clamp(position.scale * Math.pow(1.12, steps), 0.05, 2.5);','if (distanceMode) position.distance = clamp(position.distance - steps * 0.5, 2, 20);\n        else position.scale = clamp(position.scale * Math.pow(1.12, steps), 0.05, 2.5);')
edit(j/'PinnedCommentBoard.java','3, position.scale, active, pinned, orbitPaused','position.distance, position.scale, active, pinned, orbitPaused')
edit(j/'PinnedCommentBoard.java','read.scale = clamp(read.scale, 0.05, 2.5);','read.scale = clamp(read.scale, 0.05, 2.5);\n                read.distance = Double.isFinite(read.distance) ? clamp(read.distance, 2, 20) : 3;')
edit(j/'TikTokClient.java','PinnedCommentBoard.scroll(event.getDeltaY())','PinnedCommentBoard.scroll(event.getDeltaY(),\n                GLFW.glfwGetKey(mc.getWindow().handle(), GLFW.GLFW_KEY_LEFT_SHIFT) == GLFW.GLFW_PRESS\n                || GLFW.glfwGetKey(mc.getWindow().handle(), GLFW.GLFW_KEY_RIGHT_SHIFT) == GLFW.GLFW_PRESS)')
# Distance works even while frozen or paused, without unpinning or rotating the board.
edit(j/'ServerPinnedCommentBoard.java','if (board != null) {\n            if (!previous.pinned()', '''if (board != null) {
            double delta = current.distance() - previous.distance();
            if (delta != 0 && (current.pinned() || current.paused())) {
                Vec3 center = board.display.position().add(0, panelHeight(board.text, board.style) / 2, 0);
                Vec3 direction = center.subtract(player.getEyePosition()).normalize();
                Vec3 at = board.display.position().add(direction.scale(delta));
                moveBoard(board, at);
                if (current.pinned()) board.anchor = at;
                if (current.paused()) board.relativeOffset = at.subtract(player.position());
            }
            if (!previous.pinned()''')
# Explosion defaults and per-entity gift overrides persist with saved entity tags.
edit(j/'TikTokMobMod.java','String pinned_board_background = "black";', 'boolean creeper_break_blocks = false;\n        boolean tnt_break_blocks = true;\n        String pinned_board_background = "black";')
edit(j/'TikTokMobMod.java','TrollEffects.markToolMob(mob);','TrollEffects.markToolMob(mob, interaction.payload());')
edit(j/'TikTokMobMod.java','SpecialRewards.spawnTnt(player, interaction.payload());','SpecialRewards.spawnTnt(player, interaction.payload());')
edit(j/'TikTokMobMod.java','settings = loaded;','settings = loaded;\n            TrollEffects.explosionDefaults(loaded.creeper_break_blocks, loaded.tnt_break_blocks);')
edit(j/'TikTokMobMod.java','private void spawnConfiguredMob(ServerPlayer player, Interaction interaction, int currentTick) {\n        Identifier identifier = Identifier.tryParse(interaction.payload());','private void spawnConfiguredMob(ServerPlayer player, Interaction interaction, int currentTick) {\n        Identifier identifier = Identifier.tryParse(RewardOptions.mobId(interaction.payload()));')
edit(j/'RuntimeSettings.java','new Field("enderman_targets_player"', 'new Field("creeper_break_blocks", "Creeper tool phá khối", 0, "bool", 0, 1, "false"),\n        new Field("tnt_break_blocks", "TNT tool phá khối", 0, "bool", 0, 1, "true"),\n        new Field("enderman_targets_player"')
edit(j/'RewardOptions.java','    static int ticks', '''    static Boolean blockOverride(String payload) {
        try {
            var value = com.google.gson.JsonParser.parseString(payload).getAsJsonObject().get("break_blocks");
            return value != null && value.isJsonPrimitive() && value.getAsJsonPrimitive().isBoolean()
                ? value.getAsBoolean() : null;
        } catch (RuntimeException ignored) { return null; }
    }
    static String mobId(String payload) {
        try { return com.google.gson.JsonParser.parseString(payload).getAsJsonObject().get("mob").getAsString(); }
        catch (RuntimeException ignored) { return payload; }
    }
    static int ticks''')
edit(j/'TrollEffects.java','    private static final List<String> TRICKS', '''    private static final String TOOL_TNT = "tiktokmob:tool_tnt";
    private static final String BREAK = "tiktokmob:break_blocks";
    private static final String PROTECT = "tiktokmob:protect_blocks";
    private static boolean creeperBreakBlocks, tntBreakBlocks = true;
    static void explosionDefaults(boolean creeper, boolean tnt) {
        creeperBreakBlocks = creeper; tntBreakBlocks = tnt;
    }
    static boolean breaksBlocks(Entity source, boolean fallback) {
        return source.entityTags().contains(BREAK) || (!source.entityTags().contains(PROTECT) && fallback);
    }
    private static final List<String> TRICKS''')
edit(j/'TrollEffects.java','event.getAffectedBlocks().clear();','if (!breaksBlocks(source, creeperBreakBlocks)) event.getAffectedBlocks().clear();')
edit(j/'TrollEffects.java','&& entity.entityTags().contains(TOOL_CREEPER));\n            }','&& entity.entityTags().contains(TOOL_CREEPER));\n            } else if (source instanceof net.minecraft.world.entity.item.PrimedTnt\n                && source.entityTags().contains(TOOL_TNT) && !breaksBlocks(source, tntBreakBlocks)) {\n                event.getAffectedBlocks().clear();\n            }')
edit(j/'TrollEffects.java','static void markToolMob(Entity entity) {','static void markToolMob(Entity entity, String payload) {')
edit(j/'TrollEffects.java','if (entity instanceof Creeper) entity.addTag(TOOL_CREEPER);','if (entity instanceof Creeper) { entity.addTag(TOOL_CREEPER); markExplosionOverride(entity, payload); }')
edit(j/'TrollEffects.java','    static void tick() {','''    static void markToolTnt(Entity entity, String payload) {
        entity.addTag(TOOL_TNT);
        markExplosionOverride(entity, payload);
    }
    private static void markExplosionOverride(Entity entity, String payload) {
        Boolean value = RewardOptions.blockOverride(payload);
        if (value != null) entity.addTag(value ? BREAK : PROTECT);
    }

    static void tick() {''')
edit(j/'SpecialRewards.java','tnt.setFuse(RewardOptions.ticks(payload, "fuse_seconds", 4));','tnt.setFuse(RewardOptions.ticks(payload, "fuse_seconds", 4));\n        TrollEffects.markToolTnt(tnt, payload);')
edit(root/'GUI/config_service.py','DEFAULT_MOD_CONFIG = {','DEFAULT_MOD_CONFIG = {\n    "creeper_break_blocks": False,\n    "tnt_break_blocks": True,')
edit(root/'bridge/reward_options.py','def options_for(rule):','''def explosion_target(rule):
    return rule.get("target") in {"creeper", "minecraft:creeper", "troll_creeper", "spawn_tnt"}


def mob_payload(rule):
    if explosion_target(rule) and "break_blocks" in options_for(rule):
        return json.dumps({"mob": rule["target"], **options_for(rule)}, separators=(",", ":"))
    return rule["target"]


def options_for(rule):''')
edit(root/'bridge/reward_options.py','    return result','''    if explosion_target(rule) and rule.get("break_blocks") is not None:
        if not isinstance(rule["break_blocks"], bool):
            raise ValueError("break_blocks: cần bật, tắt hoặc theo cài đặt")
        result["break_blocks"] = rule["break_blocks"]
    return result''')
edit(root/'bridge/reward_options.py','if rule.get("target") in FIELDS:', 'if rule.get("target") in FIELDS or explosion_target(rule):')
edit(root/'bridge/bridge.py','from reward_options import reward_payload','from reward_options import reward_payload, mob_payload')
edit(root/'bridge/bridge.py','config, target, display_name, user_key, current_notification, True','config, mob_payload(action), display_name, user_key, current_notification, True')
edit(root/'bridge/bridge.py','    normalized_id = str(mob_id).strip().lower()','''    if str(mob_id).lstrip().startswith("{"):
        send_interaction(config, "mob", display_name, user_key, notification, mob_id, donation,
                         notification_kind=notification_kind)
        return
    normalized_id = str(mob_id).strip().lower()''')
edit(root/'bridge/test_runner.py','from reward_options import reward_payload','from reward_options import reward_payload, mob_payload')
edit(root/'bridge/test_runner.py','reward_payload(gift) if kind == "special" else reward,','reward_payload(gift) if kind == "special" else mob_payload(gift) if kind == "mob" else reward,')
edit(root/'web/index.html','<label class="check"><input id="enderman_targets_player"','<label class="check"><input id="creeper_break_blocks" data-config="mod" type="checkbox"> Creeper tool phá khối</label>\n          <label class="check"><input id="tnt_break_blocks" data-config="mod" type="checkbox"> TNT tool phá khối</label>\n          <label class="check"><input id="enderman_targets_player"')
edit(root/'web/index.html','G + cuộn chuột đổi kích thước (nhỏ nhất 5%);','G + cuộn chuột đổi kích thước (nhỏ nhất 5%); Shift + G + cuộn chuột chỉnh gần/xa (2–20 block);')
edit(root/'web/app.js',"  if (rule.action !== 'special') return '';\n  const fields", """  const explosion = ['creeper', 'minecraft:creeper', 'troll_creeper', 'spawn_tnt'].includes(rule.target);
  const blockControl = explosion ? `<div class="reward-level-controls"><label>Phá khối khi nổ<select class="reward-blocks"><option value="default" ${rule.break_blocks == null ? 'selected' : ''}>Theo cài đặt mod</option><option value="true" ${rule.break_blocks === true ? 'selected' : ''}>Bật</option><option value="false" ${rule.break_blocks === false ? 'selected' : ''}>Tắt</option></select></label></div>` : '';
  if (rule.action !== 'special') return blockControl;
  const fields""")
edit(root/'web/app.js',"  return fields.length ? '<div class=\"reward-level-controls reward-options\">'", "  return blockControl + (fields.length ? '<div class=\"reward-level-controls reward-options\">'")
edit(root/'web/app.js',".join('') + '</div>' : '';", ".join('') + '</div>' : '');")
edit(root/'web/app.js','    $(".reward-level", row)?.addEventListener', '''    $(".reward-blocks", row)?.addEventListener("change", event => updateMapping(index, "break_blocks",
      event.target.value === "default" ? null : event.target.value === "true"));
    $(".reward-level", row)?.addEventListener''')
print('CONTROLS_AND_EXPLOSIONS_UPDATED')
