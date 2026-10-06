from pathlib import Path
p=Path('TikTokMobForge/web/app.js')
s=p.read_text(encoding='utf-8')
anchor='function renderEvents() {'
s=s.replace(anchor,'''function eventRewardValue(entry) {
  return entry.kind === "mob" ? entry.target : `${entry.kind}:${entry.target}`;
}

function eventReward(raw) {
  raw = String(raw || "zombie");
  const match = raw.match(/^(item|special):(.*)$/);
  const kind = match ? match[1] : "mob";
  const target = match ? match[2] : raw.includes(":") ? raw : `minecraft:${raw}`;
  return allRewards().find(item => item.kind === kind && item.target === target) || { kind, target };
}

'''+anchor)
s=s.replace('const fullTarget = target.includes(":") ? target : `minecraft:${target}`;\n    const mob = state.catalog.mobs.find(item => item.target === fullTarget) || { kind: "mob", target: fullTarget };','const mob = eventReward(target);')
s=s.replace('dropdownMarkup("event-mob-dropdown", mob.target,','dropdownMarkup("event-mob-dropdown", eventRewardValue(mob),')
s=s.replace('const target = raw.includes(":") ? raw : `minecraft:${raw}`;\n    const selectedMob = state.catalog.mobs.find(item => item.target === target);','')
s=s.replace('mountSearchDropdown(dropdown, state.catalog.mobs, {\n      getValue: item => item.target,\n      getLabel: item => `${item.vietnamese_name} — ${item.target}`,','mountSearchDropdown(dropdown, allRewards(), {\n      getValue: eventRewardValue,\n      getLabel: item => `${item.kind === "mob" ? "Mob" : item.kind === "item" ? "Vật phẩm" : "Hiệu ứng"} · ${item.vietnamese_name || item.target} — ${item.target}`,')
s=s.replace('$(".event-preview", card).src = iconUrl(mob);\n        renderLivePanel();','$(".event-preview", card).src = iconUrl(mob);\n        updateEventRule(card);\n        renderLivePanel();')
s=s.replace('eventMobImage(prefix, {kind: "mob", target: $(".event-mob-dropdown", card).dataset.value})','eventMobImage(prefix, eventReward($(".event-mob-dropdown", card).dataset.value))')
s=s.replace(': `minecraft:${state.bridge[`${type.prefix}_mob_type`] || type.fallback}`;',': state.bridge[`${type.prefix}_mob_type`] || type.fallback;')
s=s.replace('const mob = state.catalog.mobs.find(x => x.target === target) || { kind: "mob", target };','const mob = eventReward(target);')
# Use neutral language for counts and summaries, valid for every reward type.
a=s.index('function renderEvents()');b=s.index('function renderGiftSources()')
part=s[a:b]
for old,new in [('Mob được tạo','Mob / quà được trao'),('Tìm mob trong danh sách…','Tìm mob, vật phẩm (Totem), hiệu ứng…'),('Đổi ảnh mob','Đổi ảnh'),('Ảnh mob','Ảnh'),('ảnh mob','ảnh phần thưởng'),('Số mob','Số phần thưởng'),('tạo mob','trao phần thưởng'),('Tạo mob','Trao phần thưởng'),(' mob',' phần thưởng'),('Mob mang tên','Mob mang tên')]:
 part=part.replace(old,new)
# replacement of literal words must not rename identifiers (space mob in function args etc)
# restore accidental identifier replacements
part=part.replace('const phần thưởng =','const mob =').replace(' phần thưởng)', ' mob)').replace(' phần thưởng =>',' mob =>').replace(' phần thưởng.target',' mob.target').replace(' phần thưởng.vietnamese_name',' mob.vietnamese_name')
s=s[:a]+part+s[b:]
s=s.replace('`${spawnCount} mob / người · ${viewInterval} giây`','`${spawnCount} phần thưởng / người · ${viewInterval} giây`').replace('"Đã tắt tạo mob theo View"','"Đã tắt phần thưởng theo View"').replace('`Tạo ${spawnCount} mob`','`Trao ${spawnCount} phần thưởng`')
p.write_text(s,encoding='utf-8')
p=Path('TikTokMobForge/bridge/bridge.py');s=p.read_text(encoding='utf-8');needle='    if str(mob_id).lstrip().startswith("{"):'
s=s.replace(needle,'''    # Legacy mob values stay valid; typed rewards share existing gift handlers.
    reward_id = str(mob_id).strip()
    if reward_id.startswith(("item:", "special:")):
        kind, target = reward_id.split(":", 1)
        send_interaction(
            config, "item" if kind == "item" else target,
            display_name, user_key, notification,
            target if kind == "item" else reward_payload({"target": target}),
            donation, notification_kind=notification_kind,
        )
        return
'''+needle)
p.write_text(s,encoding='utf-8')
