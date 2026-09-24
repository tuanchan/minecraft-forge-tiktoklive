const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

let state;
let mappings = [];
let rewardFilter = "all";
let selectedMapping = 0;
let logOffset = 0;
const defaultVoiceModels = [
  { model_id: "eleven_flash_v2_5", name: "Flash v2.5", description: "Độ trễ thấp · hỗ trợ tiếng Việt" },
  { model_id: "eleven_turbo_v2_5", name: "Turbo v2.5", description: "Hỗ trợ tiếng Việt" },
  { model_id: "eleven_v3", name: "Eleven v3", description: "Giàu biểu cảm · hỗ trợ tiếng Việt" },
  { model_id: "eleven_multilingual_v2", name: "Multilingual v2", description: "Đa ngôn ngữ · không hỗ trợ tiếng Việt" },
];
let voiceCatalog = { voices: [], models: defaultVoiceModels };
let voiceCatalogRequest = 0;
let voicevoxRequest = 0;
let voicevoxVoices = [];

function renderVoicevoxChoices() {
  const id = numberValue("tts_voicevox_speaker_id", 3);
  const voices = [...voicevoxVoices];
  if (!voices.some(voice => voice.id === id))
    voices.unshift({ id, name: id === 3 ? "Zundamon / ずんだもん — Normal (chưa kiểm tra trên máy)" : `Giọng ID ${id} (chưa kiểm tra trên máy)` });
  $("#voicevox_choice").innerHTML = voices.map(voice => `<option value="${voice.id}">${escapeHtml(voice.name)}</option>`).join("");
  setValue("voicevox_choice", id);
}

function renderTtsProvider() {
  const elevenlabs = value("tts_provider") === "elevenlabs";
  $("#edgeSettings").hidden = value("tts_provider") !== "edge";
  ["api_key", "voice_search", "voice_choice", "tts_model_choice", "tts_voice_name", "tts_voice_id",
    "tts_model_id", "tts_stability", "tts_similarity_boost", "tts_style", "tts_speed",
    "tts_language_code", "tts_use_speaker_boost"].forEach(id => { $(`#${id}`).closest("label").hidden = !elevenlabs; });
  ["voiceCatalogStatus", "voiceModelHelp", "reloadVoicesBtn"].forEach(id => { $(`#${id}`).hidden = !elevenlabs; });
  renderVoicevoxChoices();
}

async function loadVoicevoxCatalog() {
  const request = ++voicevoxRequest;
  const url = value("tts_voicevox_url");
  const status = $("#voicevoxStatus");
  status.textContent = "Đang kết nối / tự khởi động VOICEVOX… Lần đầu có thể mất đến 60 giây.";
  try {
    const result = await api("/api/voicevox", { method: "POST", body: JSON.stringify({ url }) });
    if (request !== voicevoxRequest || url !== value("tts_voicevox_url")) return;
    voicevoxVoices = result.voices || [];
    renderVoicevoxChoices();
    status.textContent = voicevoxVoices.length ? `Đã kết nối · ${voicevoxVoices.length} kiểu giọng. Chọn nhân vật rồi bấm Test VOICEVOX + GIF.` : "VOICEVOX chưa có giọng đọc được cài.";
  } catch (error) {
    if (request !== voicevoxRequest || url !== value("tts_voicevox_url")) return;
    voicevoxVoices = []; renderVoicevoxChoices();
    status.textContent = error.message;
  }
}
let autoSaveReady = false;
let autoSaveTimer;
let saveFlight = null;
let lastSavedPayload = "";
const panelPreviewKey = "tiktok-mob-forge.panel-preview.v1";
const panelChannel = "BroadcastChannel" in window ? new BroadcastChannel("tiktok-mob-forge-panel") : null;

const eventTypes = [
  { prefix: "view", title: "Người xem LIVE", subtitle: "Người xem LIVE", fallback: "zombie", icon: "/assets/viewer.png" },
  { prefix: "follow", title: "Follower", subtitle: "Theo dõi", fallback: "creeper", icon: "/assets/flow.png" },
  { prefix: "comment", title: "Comment", subtitle: "Bình luận", fallback: "zombie", icon: "/assets/comment.png" },
  { prefix: "share", title: "Share", subtitle: "Chia sẻ", fallback: "enderman", icon: "/assets/share.png" },
  { prefix: "like", title: "Tim", subtitle: "Lượt thích", fallback: "skeleton", icon: "/assets/like.png" },
];

function toast(message, error = false) {
  const node = document.createElement("div");
  node.className = `toast${error ? " error" : ""}`;
  node.textContent = message;
  $("#toastHost").append(node);
  setTimeout(() => node.remove(), 4500);
}

async function api(url, options = {}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Thao tác thất bại");
  return data;
}

function iconUrl(entry) {
  const target = String(entry.target || "").replace(/^minecraft:/, "");
  if (target === "iron_golem") return "/assets/sumongoblem.png";
  if (target === "wolf" || target === "armored_wolf") return "/assets/summomdog.png";
  return `/api/icon?v=inventory-26.2-r1&kind=${encodeURIComponent(entry.kind)}&id=${encodeURIComponent(entry.target)}`;
}

function eventMobImage(prefix, mob) {
  const normalize = target => String(target || "").replace(/^minecraft:/, "");
  const bound = state.bridge.event_image_targets?.[prefix];
  return bound && normalize(bound) === normalize(mob.target)
    ? state.bridge.event_images?.[prefix] || iconUrl(mob) : iconUrl(mob);
}

function allRewards() {
  return [...state.catalog.special, ...state.catalog.items, ...state.catalog.mobs];
}

function rewardKey(entry) { return `${entry.kind}|${entry.target}`; }
function findReward(rule) { return allRewards().find(x => x.kind === rule.action && x.target === rule.target); }
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[char]));
}

function giftMetadata(rule) {
  if (rule.gift_id) return state.gifts.find(gift => String(gift.gift_id) === String(rule.gift_id));
  return state.gifts.find(gift => String(gift.name || "").toLowerCase() === String(rule.gift_name || "").toLowerCase());
}

function giftImageUrl(gift = {}) {
  const discovered = giftMetadata(gift) || {};
  return gift.asset_image || discovered.asset_image || gift.image_url || discovered.image_url || "";
}

function giftImageMarkup(gift, className) {
  const image = giftImageUrl(gift);
  return image
    ? `<img loading="lazy" class="${className}" src="${escapeHtml(image)}" alt="${escapeHtml(gift.name || gift.gift_name || '')}">`
    : `<span class="${className} gift-image-missing">Chưa có ảnh</span>`;
}

function dropdownMarkup(className, value, label, placeholder) {
  return `<div class="search-dropdown ${className}" data-value="${escapeHtml(value)}">
    <button class="dropdown-toggle" type="button"><span>${escapeHtml(label || placeholder)}</span><i>▾</i></button>
    <div class="dropdown-popover">
      <input class="dropdown-search" type="search" placeholder="${escapeHtml(placeholder)}" autocomplete="off">
      <div class="dropdown-options"></div>
    </div>
  </div>`;
}

function mountSearchDropdown(root, items, options) {
  if (!root) return;
  const getValue = options.getValue;
  const getLabel = options.getLabel;
  const renderOptions = query => {
    const needle = query.trim().toLowerCase();
    const filtered = items.filter(item => `${getLabel(item)} ${getValue(item)}`.toLowerCase().includes(needle)).slice(0, 180);
    $(".dropdown-options", root).innerHTML = filtered.map(item => {
      const image = options.getImage?.(item) || "";
      return `<button type="button" class="dropdown-option" data-option-value="${escapeHtml(getValue(item))}">${image ? `<img src="${escapeHtml(image)}" alt="">` : ""}<span>${escapeHtml(getLabel(item))}</span></button>`;
    }).join("") || `<div class="dropdown-empty">Không tìm thấy kết quả</div>`;
    $$(".dropdown-option", root).forEach(button => button.addEventListener("click", () => {
      const item = items.find(candidate => getValue(candidate) === button.dataset.optionValue);
      if (!item) return;
      root.dataset.value = getValue(item);
      $(".dropdown-toggle span", root).textContent = getLabel(item);
      root.classList.remove("open");
      options.onSelect(item);
    }));
  };
  $(".dropdown-toggle", root).addEventListener("click", event => {
    event.stopPropagation();
    const shouldOpen = !root.classList.contains("open");
    $$(".search-dropdown.open").forEach(node => node.classList.remove("open"));
    root.classList.toggle("open", shouldOpen);
    if (shouldOpen) {
      const search = $(".dropdown-search", root);
      search.value = "";
      renderOptions("");
      requestAnimationFrame(() => search.focus());
    }
  });
  $(".dropdown-search", root).addEventListener("click", event => event.stopPropagation());
  $(".dropdown-search", root).addEventListener("input", event => renderOptions(event.target.value));
}

function showSettingsTab(id) {
  $$("[data-settings-panel]").forEach(panel => { panel.hidden = panel.id !== id; });
  $$("[data-settings-tab]").forEach(button => {
    const active = button.dataset.settingsTab === id;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  if (id === "settingsPosition") requestAnimationFrame(renderSettingsPreview);
}

function showTab(name) {
  if (name === "settings" || name === "events") {
    $(name === "settings" ? "#settingsEventsHome" : "#eventsHome").append($("#interactionControls"));
  }
  $$(".tab").forEach(x => x.classList.toggle("active", x.dataset.tab === name));
  $$(".view[data-view]").forEach(x => x.classList.toggle("active", x.dataset.view === name));
  if (name === "tests" && state) renderTests();
  if (name === "voicevox") requestAnimationFrame(renderGiftSettings);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setLiveBadge(running) {
  const badge = $("#liveBadge");
  badge.textContent = running ? "LIVE đang chạy" : "Đã dừng";
  badge.className = `badge ${running ? "online" : "offline"}`;
}

function value(id, fallback = "") { const node = $(`#${id}`); return node ? node.value : fallback; }
function numberValue(id, fallback = 1) { const parsed = Number(value(id, fallback)); return Number.isFinite(parsed) ? parsed : fallback; }
function checked(id) { return Boolean($(`#${id}`)?.checked); }
function setValue(id, value) { const node = $(`#${id}`); if (node) node.value = value ?? ""; }
function setChecked(id, value) { const node = $(`#${id}`); if (node) node.checked = Boolean(value); }

function renderEvents() {
  // Move existing inputs to retain their values across preview refreshes.
  const tuningGroups = $$(".event-tuning");
  $("#eventEditors").innerHTML = eventTypes.map(type => {
    const target = state.bridge[`${type.prefix}_mob_type`] || type.fallback;
    const fullTarget = target.includes(":") ? target : `minecraft:${target}`;
    const mob = state.catalog.mobs.find(item => item.target === fullTarget) || { kind: "mob", target: fullTarget };
    const label = type.prefix === "like" ? "Số tim mỗi lượt" : type.prefix === "view" ? "Số mob / view / đợt" : "Số mob mỗi sự kiện";
    const customImage = state.bridge.event_images?.[type.prefix] || "";
    return `<article class="panel event-editor" data-prefix="${type.prefix}">
      <header class="event-editor-heading"><img src="${type.icon}" alt=""><div><h3>${type.subtitle}</h3><small>${type.title} · ${type.prefix === "like" ? "Tích lũy tim riêng từng người" : type.prefix === "view" ? "Có người xem là tạo mob theo chu kỳ" : "Tạo mob cho người tương tác"}</small></div></header>
      <div class="event-editor-mob">
      <div class="event-image-editor">
        <img class="event-preview" src="${escapeHtml(eventMobImage(type.prefix, mob))}" alt="">
        <label class="image-picker">Đổi ảnh mob<input class="event-image-input" type="file" accept="image/png,image/jpeg,image/webp"></label>
      </div>
      <div><label>Mob được tạo
        ${dropdownMarkup("event-mob-dropdown", mob.target, `${mob.vietnamese_name || mob.target} — ${mob.target}`, "Tìm mob trong danh sách…")}
      </label></div>
      </div>
      <div class="event-editor-settings"><label>${label}<input class="event-count" type="number" min="1" max="${type.prefix === "like" ? 100000 : 100}"></label></div>
      <p class="event-rule"></p>
    </article>`;
  }).join("");
  tuningGroups.forEach(group => $(`.event-editor[data-prefix="${group.dataset.event}"] .event-editor-settings`).append(group));
  $$(".event-editor").forEach(card => {
    const prefix = card.dataset.prefix;
    const raw = state.bridge[`${prefix}_mob_type`] || eventTypes.find(x => x.prefix === prefix).fallback;
    const target = raw.includes(":") ? raw : `minecraft:${raw}`;
    const selectedMob = state.catalog.mobs.find(item => item.target === target);
    const dropdown = $(".event-mob-dropdown", card);
    $(".event-count", card).value = prefix === "like" ? state.bridge.likes_per_skeleton : state.bridge[`${prefix}_spawn_count`];
    mountSearchDropdown(dropdown, state.catalog.mobs, {
      getValue: item => item.target,
      getLabel: item => `${item.vietnamese_name} — ${item.target}`,
      getImage: iconUrl,
      onSelect: mob => {
        delete state.bridge.event_images?.[prefix];
        delete state.bridge.event_image_targets?.[prefix];
        $(".event-preview", card).src = iconUrl(mob);
        renderLivePanel();
      },
    });
    $(".event-image-input", card).addEventListener("change", event => uploadEventImage(prefix, event.target.files?.[0], card));
    $(".event-count", card).addEventListener("input", renderLivePanel);
    card.oninput = () => updateEventRule(card);
    updateEventRule(card);
  });
}

function updateEventRule(card) {
  const prefix = card.dataset.prefix;
  const count = Number($(".event-count", card).value) || 1;
  let rule = `Mỗi lượt theo dõi tạo ${count} mob cho người đó.`;
  if (prefix === "view") rule = checked("view_enabled") ? `Mỗi người được nhận diện tạo ${count} mob; lặp lại sau ${numberValue("view_interval_seconds", 60)} giây. Tối đa ${numberValue("view_max_mobs_per_round", 20)} mob mỗi đợt. Mob mang tên từng tài khoản đã nhận diện khi vào LIVE hoặc tương tác.` : "Đã tắt tạo mob theo View.";
  if (prefix === "like") rule = `Mỗi người đủ ${count} tim → ${numberValue("like_spawn_count", 1)} mob. Tim dư giữ lại cho chính người đó.`;
  if (prefix === "comment" || prefix === "share") {
    const label = prefix === "comment" ? "bình luận" : "chia sẻ";
    rule = `Mỗi ${label} tạo ${count} mob. Sau ${numberValue(`${prefix}_limit`, 1)} lượt của cùng một người, người đó chờ ${numberValue(`${prefix}_cooldown_seconds`, 10)} giây.`;
  }
  $(".event-rule", card).textContent = rule;
}

async function uploadEventImage(prefix, file, card) {
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) return toast("Ảnh mob phải nhỏ hơn 5 MB", true);
  try {
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
    const mobTarget = $(".event-mob-dropdown", card).dataset.value;
    const result = await api("/api/upload-image", { method: "POST", body: JSON.stringify({ slot: prefix, data_url: dataUrl, mob_target: mobTarget }) });
    state.bridge.event_images = { ...(state.bridge.event_images || {}), [prefix]: result.url };
    state.bridge.event_image_targets = { ...(state.bridge.event_image_targets || {}), [prefix]: result.mob_target };
    $(".event-preview", card).src = eventMobImage(prefix, {kind: "mob", target: $(".event-mob-dropdown", card).dataset.value});
    renderLivePanel();
    toast("Đã thay ảnh mob. Cấu hình sẽ được lưu tự động.");
  } catch (error) { toast(error.message, true); }
}

function renderGiftSources() {
  const query = $("#giftSearch").value.trim().toLowerCase();
  const assigned = new Set(mappings.map(x => x.gift_id ? `id:${x.gift_id}` : `name:${String(x.gift_name).toLowerCase()}`));
  const gifts = state.gifts.filter(gift => `${gift.name} ${gift.diamond_count} ${gift.gift_id}`.toLowerCase().includes(query));
  $("#giftSource").innerHTML = gifts.map((gift, index) => {
    const key = gift.gift_id ? `id:${gift.gift_id}` : `name:${String(gift.name).toLowerCase()}`;
    return `<div class="source-item" draggable="true" data-gift-index="${state.gifts.indexOf(gift)}">
      ${giftImageMarkup(gift, "source-gift-image")}<b>${escapeHtml(gift.name)}</b><span>${Number(gift.diamond_count || 0)} xu</span>
      <small>ID ${escapeHtml(gift.gift_id || "—")}${assigned.has(key) ? " · đã gán" : ""}</small><button class="quick-add" title="Thêm">+</button>
    </div>`;
  }).join("") || `<div class="empty show">Không tìm thấy quà</div>`;
  $$(".source-item").forEach(node => {
    node.addEventListener("dragstart", event => event.dataTransfer.setData("application/x-gift", node.dataset.giftIndex));
    node.addEventListener("dblclick", () => addGiftFromCatalog(Number(node.dataset.giftIndex)));
    $(".quick-add", node).addEventListener("click", event => { event.stopPropagation(); addGiftFromCatalog(Number(node.dataset.giftIndex)); });
  });
}

function renderRewardSources() {
  const query = $("#rewardSearch").value.trim().toLowerCase();
  const rewards = allRewards().filter(item => (rewardFilter === "all" || item.kind === rewardFilter) && `${item.vietnamese_name} ${item.target} ${item.group}`.toLowerCase().includes(query)).slice(0, 160);
  $("#rewardSource").innerHTML = rewards.map(item => `<div class="reward-card" draggable="true" title="${escapeHtml(item.vietnamese_name)}" data-reward="${escapeHtml(rewardKey(item))}">
    <img loading="lazy" src="${iconUrl(item)}" alt=""><b>${escapeHtml(item.vietnamese_name)}</b><small>${escapeHtml(item.target)}</small>
  </div>`).join("") || `<div class="empty show">Không tìm thấy phần thưởng</div>`;
  $$(".reward-card").forEach(node => {
    node.addEventListener("dragstart", event => event.dataTransfer.setData("application/x-reward", node.dataset.reward));
    node.addEventListener("dblclick", () => applyReward(selectedMapping, node.dataset.reward));
  });
}

function defaultRule(gift = {}) {
  return { gift_name: gift.name || "Quà mới", gift_id: String(gift.gift_id || ""), vietnamese_name: gift.name || "Quà mới", coin_value: Number(gift.diamond_count || 0), action: "special", target: "absorption", amount: 1 };
}

function addGiftFromCatalog(index) {
  const gift = state.gifts[index];
  const duplicate = mappings.findIndex(x => (gift.gift_id && String(x.gift_id) === String(gift.gift_id)) || String(x.gift_name).toLowerCase() === String(gift.name).toLowerCase());
  if (duplicate >= 0) { selectedMapping = duplicate; renderMappings(); toast("Quà này đã có trong danh sách"); return; }
  mappings.push(defaultRule(gift));
  selectedMapping = mappings.length - 1;
  renderMappings(); renderGiftSources(); renderLivePanel();
}

function updateMapping(index, key, value) {
  if (!mappings[index]) return;
  mappings[index][key] = value;
  if (key === "gift_name" && !mappings[index].vietnamese_name) mappings[index].vietnamese_name = value;
  renderLivePanel();
}

function applyGift(index, giftIndex) {
  const gift = state.gifts[giftIndex];
  if (!gift || !mappings[index]) return;
  const duplicate = mappings.findIndex((x, i) => i !== index && ((gift.gift_id && String(x.gift_id) === String(gift.gift_id)) || String(x.gift_name).toLowerCase() === String(gift.name).toLowerCase()));
  if (duplicate >= 0) mappings.splice(duplicate, 1);
  const row = mappings[index > duplicate && duplicate >= 0 ? index - 1 : index];
  row.gift_name = gift.name; row.gift_id = String(gift.gift_id || ""); row.vietnamese_name = gift.name; row.coin_value = Number(gift.diamond_count || 0);
  renderMappings(); renderGiftSources(); renderLivePanel();
}

function applyReward(index, key) {
  const [kind, target] = key.split("|");
  if (!mappings[index] || !target) return;
  mappings[index].action = kind; mappings[index].target = target;
  mappings[index].level = target.startsWith("enchant_") ? 0 : 1;
  renderMappings(); renderLivePanel();
}

function renderMappings() {
  const rewards = allRewards();
  const rewardLabel = item => `${item.vietnamese_name} — ${item.target}`;
  $("#mappingList").innerHTML = mappings.map((rule, index) => {
    const reward = findReward(rule) || { kind: rule.action, target: rule.target, vietnamese_name: rule.target };
    return `<div class="mapping-row${index === selectedMapping ? " selected" : ""}" data-index="${index}">
      <span class="grip" draggable="true" title="Kéo đổi thứ tự">⋮⋮</span>
      ${giftImageMarkup(rule, "mapping-gift-icon")}
      ${dropdownMarkup("gift-select", rule.gift_id || rule.gift_name, `${rule.gift_name}${rule.gift_id ? ` · ID ${rule.gift_id}` : ""}`, "Tìm quà theo tên, xu hoặc Gift ID…")}
      <span class="arrow">→</span>
      <img class="mapping-icon" src="${iconUrl(reward)}" alt="">
      ${dropdownMarkup("reward-select", rewardKey(reward), rewardLabel(reward), "Tìm mob hoặc vật phẩm…")}
      <input class="amount" type="number" min="1" max="100" value="${Number(rule.amount || 1)}" title="Số lượng">
      <button class="delete" title="Xóa quà">✕</button>
      ${rule.action === "special" && ["enchant_armor", "enchant_weapon", "experience"].includes(rule.target) ? `<div class="reward-level-controls"><label>${rule.target === "experience" ? "Cấp kinh nghiệm" : "Cấp enchant"}<input class="reward-level" type="number" min="${rule.target === "experience" ? 1 : 0}" max="255" value="${Number(rule.level ?? (rule.target.startsWith("enchant_") ? 0 : 1))}"></label><small>${rule.target === "experience" ? "1–255 cấp mỗi lần nhận" : "0 = tối đa tự nhiên từng enchant · 1–255 = cấp chỉ định · không gồm lời nguyền"}</small></div>` : ""}
    </div>`;
  }).join("");
  $("#emptyMappings").classList.toggle("show", mappings.length === 0);
  $$(".mapping-row").forEach(row => {
    const index = Number(row.dataset.index);
    row.addEventListener("click", () => selectedMapping = index);
    $(".reward-level", row)?.addEventListener("input", event => updateMapping(index, "level", Number(event.target.value)));
    $(".amount", row).addEventListener("input", event => updateMapping(index, "amount", Math.max(1, Number(event.target.value || 1))));
    mountSearchDropdown($(".gift-select", row), state.gifts, {
      getValue: gift => String(gift.gift_id || gift.name),
      getLabel: gift => `${gift.name} · ${Number(gift.diamond_count || 0)} xu${gift.gift_id ? ` · ID ${gift.gift_id}` : ""}`,
      getImage: giftImageUrl,
      onSelect: gift => applyGift(index, state.gifts.indexOf(gift)),
    });
    mountSearchDropdown($(".reward-select", row), rewards, {
      getValue: rewardKey,
      getLabel: rewardLabel,
      getImage: iconUrl,
      onSelect: reward => applyReward(index, rewardKey(reward)),
    });
    $(".delete", row).addEventListener("click", () => { mappings.splice(index, 1); selectedMapping = Math.max(0, Math.min(index, mappings.length - 1)); renderMappings(); renderGiftSources(); renderLivePanel(); });
    $(".grip", row).addEventListener("dragstart", event => event.dataTransfer.setData("application/x-mapping", String(index)));
    row.addEventListener("dragover", event => { event.preventDefault(); row.classList.add("dragover"); });
    row.addEventListener("dragleave", () => row.classList.remove("dragover"));
    row.addEventListener("drop", event => {
      event.preventDefault(); row.classList.remove("dragover");
      const transferTypes = [...event.dataTransfer.types];
      if (transferTypes.includes("application/x-gift")) applyGift(index, Number(event.dataTransfer.getData("application/x-gift")));
      else if (transferTypes.includes("application/x-reward")) applyReward(index, event.dataTransfer.getData("application/x-reward"));
      else if (transferTypes.includes("application/x-mapping")) {
        const source = Number(event.dataTransfer.getData("application/x-mapping"));
        const [moved] = mappings.splice(source, 1); mappings.splice(index, 0, moved); selectedMapping = index; renderMappings(); renderLivePanel();
      }
    });
  });
  $("#mappingList").ondragover = event => event.preventDefault();
  $("#mappingList").ondrop = event => {
    if (event.target !== $("#mappingList") && event.target !== $("#emptyMappings")) return;
    const giftIndex = event.dataTransfer.getData("application/x-gift");
    if (giftIndex !== "") addGiftFromCatalog(Number(giftIndex));
  };
}

function panelPreviewState() {
  if (!state) return null;
  const bridge = { ...state.bridge, event_images: { ...(state.bridge.event_images || {}) } };
  bridge.like_spawn_count = numberValue("like_spawn_count", state.bridge.like_spawn_count);
  $$(".event-editor").forEach(card => {
    const prefix = card.dataset.prefix;
    bridge[`${prefix}_mob_type`] = $(".event-mob-dropdown", card).dataset.value.replace(/^minecraft:/, "");
    if (prefix === "like") bridge.likes_per_skeleton = Number($(".event-count", card).value);
    else bridge[`${prefix}_spawn_count`] = Number($(".event-count", card).value);
  });
  return { bridge, mappings: mappings.map(rule => ({ ...rule })) };
}

function publishPanelPreview() {
  if (document.body.classList.contains("detached-panel")) return;
  const preview = panelPreviewState();
  if (!preview) return;
  localStorage.setItem(panelPreviewKey, JSON.stringify(preview));
  panelChannel?.postMessage(preview);
}

function applyPanelPreview(preview) {
  if (!state || !preview?.bridge || !Array.isArray(preview.mappings)) return;
  state.bridge = { ...state.bridge, ...preview.bridge, event_images: { ...(preview.bridge.event_images || {}) } };
  setValue("like_spawn_count", state.bridge.like_spawn_count);
  mappings = preview.mappings.map(rule => ({ ...rule }));
  renderEvents();
  renderLivePanel(false);
}

function renderLivePanel(publish = true) {
  if (!state) return;
  $("#eventCards").innerHTML = eventTypes.map(type => {
    const editor = $(`.event-editor[data-prefix="${type.prefix}"]`);
    const target = editor ? $(".event-mob-dropdown", editor).dataset.value : `minecraft:${state.bridge[`${type.prefix}_mob_type`] || type.fallback}`;
    const count = editor ? $(".event-count", editor).value : (type.prefix === "like" ? state.bridge.likes_per_skeleton : state.bridge[`${type.prefix}_spawn_count`]);
    const mob = state.catalog.mobs.find(x => x.target === target) || { kind: "mob", target };
    const customImage = state.bridge.event_images?.[type.prefix];
    const eventTitle = type.prefix === "like" ? `${count} Tim` : type.title;
    const spawnCount = type.prefix === "like" ? numberValue("like_spawn_count", state.bridge.like_spawn_count || 1) : count;
    const viewEnabled = $("#view_enabled") ? checked("view_enabled") : state.bridge.view_enabled !== false;
    const viewInterval = numberValue("view_interval_seconds", state.bridge.view_interval_seconds || 60);
    const caption = type.prefix === "view"
      ? (viewEnabled ? `${spawnCount} mob / người · ${viewInterval} giây` : "Đã tắt tạo mob theo View")
      : `Tạo ${spawnCount} mob`;
    return `<div class="event-card event-${type.prefix}" data-event-kind="${type.prefix}">
      <div class="event-card-title"><img class="event-action-icon" src="${type.icon}" alt=""><b>${escapeHtml(eventTitle)}</b></div>
      <div class="mob-stage"><img src="${escapeHtml(eventMobImage(type.prefix, mob))}" alt=""></div>
      <div class="event-caption"><strong>${escapeHtml(mob.vietnamese_name || target)}</strong><small>${escapeHtml(caption)}</small></div>
    </div>`;
  }).join("");
  $("#giftPreview").innerHTML = mappings.map((rule, index) => {
    const reward = findReward(rule) || { kind: rule.action, target: rule.target, vietnamese_name: rule.target };
    const wide = mappings.length > 3 && index === mappings.length - 1 && mappings.length % 3 === 1 ? " wide-gift" : "";
    return `<div class="gift-card${wide}" data-gift-index="${index}" title="${escapeHtml(rule.gift_name)} → ${escapeHtml(reward.vietnamese_name)} ×${Number(rule.amount || 1)} · Chuột phải để thêm chú thích">
      ${rule.panel_note ? `<small class="gift-panel-note">${escapeHtml(rule.panel_note)}</small>` : ""}
      <b class="gift-amount">${Number(rule.amount || 1)}x</b>
      <div class="gift-top"><b>${escapeHtml(rule.gift_name)}</b>${giftImageMarkup(rule, "tiktok-gift-image")}</div>
      <span class="gift-divider">◆</span>
      <div class="reward-bottom"><img src="${iconUrl(reward)}" alt=""><div class="reward-caption"><strong>${escapeHtml(reward.vietnamese_name)}</strong><small>x${Number(rule.amount || 1)}${rule.target.startsWith("enchant_") ? ` · ${Number(rule.level || 0) === 0 ? "Max" : `Cấp ${Number(rule.level)}`}` : rule.target === "experience" ? ` · ${Number(rule.level || 1)} cấp` : ""}</small></div></div>
    </div>`;
  }).join("") || `<div class="empty show">Chưa gán quà</div>`;
  if (publish) { publishPanelPreview(); scheduleAutoSave(); }
}

function collectPayload() {
  const bridge = { ...state.bridge, gift_actions: mappings.map(rule => ({ ...rule })) };
  const mod = { ...state.mod, notification_positions: collectPositions(), notification_display_modes: collectDisplayModes() };
  $$('[data-config]').forEach(node => {
    const target = node.dataset.config === "mod" ? mod : bridge;
    target[node.id] = node.type === "checkbox" ? node.checked : node.type === "number" ? Number(node.value) : node.value;
  });
  $$(".event-editor").forEach(card => {
    const prefix = card.dataset.prefix;
    bridge[`${prefix}_mob_type`] = $(".event-mob-dropdown", card).dataset.value.replace(/^minecraft:/, "");
    if (prefix === "like") bridge.likes_per_skeleton = Number($(".event-count", card).value);
    else bridge[`${prefix}_spawn_count`] = Number($(".event-count", card).value);
  });
  Object.assign(bridge, {
    tiktok_username: value("tiktok_username"), minecraft_host: value("minecraft_host"), minecraft_port: numberValue("minecraft_port", 9876),
    like_spawn_count: numberValue("like_spawn_count"),
    comment_limit: numberValue("comment_limit"), comment_cooldown_seconds: numberValue("comment_cooldown_seconds"),
    share_limit: numberValue("share_limit"), share_cooldown_seconds: numberValue("share_cooldown_seconds"),
    tts_enabled: checked("tts_enabled"), tts_voice_name: value("tts_voice_name"), tts_voice_id: value("tts_voice_id"),
    tts_model_id: value("tts_model_id"), tts_read_username: checked("tts_read_username"),
    tts_max_characters: numberValue("tts_max_characters"), tts_queue_size: numberValue("tts_queue_size"),
    tts_keep_latest_comment: checked("tts_keep_latest_comment"),
    tts_pause_between_comments_seconds: numberValue("tts_pause_between_comments_seconds", 0),
    tts_trailing_silence_seconds: numberValue("tts_trailing_silence_seconds", 0),
    tts_stability: numberValue("tts_stability", 0), tts_similarity_boost: numberValue("tts_similarity_boost", 0),
    tts_style: numberValue("tts_style", 0), tts_speed: numberValue("tts_speed", 1),
    tts_language_code: value("tts_language_code"), tts_use_speaker_boost: checked("tts_use_speaker_boost"),
  });
  Object.assign(mod, {
    max_mobs_per_user: numberValue("max_mobs_per_user"), max_mobs_total: numberValue("max_mobs_total"),
    mob_lifetime_seconds: numberValue("mob_lifetime_seconds"), max_interactions_per_tick: numberValue("max_interactions_per_tick"),
    golem_teleport_distance: numberValue("golem_teleport_distance", 5), wolf_teleport_distance: numberValue("wolf_teleport_distance", 5),
    spawn_min_distance: numberValue("spawn_min_distance", 0), spawn_max_distance: numberValue("spawn_max_distance", 0),
    spawn_direction: value("spawn_direction"), spawn_height_offset: numberValue("spawn_height_offset", 0), max_pending_events: numberValue("max_pending_events"),
    notification_queue_size: numberValue("notification_queue_size"),
    notification_duration_seconds: numberValue("notification_duration_seconds"),
    donation_notification_duration_seconds: numberValue("donation_notification_duration_seconds"),
    enderman_targets_player: checked("enderman_targets_player"), mobs_persistent: checked("mobs_persistent"),
    show_death_counter: checked("show_death_counter"), show_countdown_in_name: checked("show_countdown_in_name"), effect_duration_seconds: numberValue("effect_duration_seconds"),
    absorption_hearts_per_rose: numberValue("absorption_hearts_per_rose"), money_gun_arrow_count: numberValue("money_gun_arrow_count"),
    universe_effect_level: numberValue("universe_effect_level"),
  });
  return { bridge, mod, gui: { minecraft_directory: value("minecraft_directory"), keep_minecraft_running_in_background: checked("keep_minecraft_running_in_background") }, api_key: value("api_key") };
}

function validatedPayload() {
  const invalid = $$('input[type="number"]').filter(node => !node.closest('[data-view="tests"]')).find(node => node.value === "" || !node.checkValidity());
  if (invalid) {
    throw new Error(`Kiểm tra ${invalid.closest("label")?.textContent.trim() || "giá trị số"}: cần điền đúng khoảng cho phép.`);
  }
  return JSON.stringify(collectPayload());
}

function saveStatus(text, error = false) {
  $("#saveStatus").textContent = text;
  $("#saveStatus").classList.toggle("error", error);
  $("#saveStatus").title = text;
}

function scheduleAutoSave() {
  if (!autoSaveReady || document.body.classList.contains("detached-panel")) return;
  clearTimeout(autoSaveTimer);
  if (JSON.stringify(collectPayload()) === lastSavedPayload) {
    if (!saveFlight) saveStatus("Đã tự động lưu");
    return;
  }
  saveStatus("Chờ tự động lưu…");
  autoSaveTimer = setTimeout(() => save(false).catch(() => {}), 1000);
}

async function save(showMessage = true) {
  clearTimeout(autoSaveTimer);
  if (!saveFlight) {
    saveFlight = (async () => {
      let result = { message: "Đã lưu", restart_live: false };
      while (true) {
        const payload = validatedPayload();
        if (payload === lastSavedPayload) break;
        saveStatus("Đang lưu…");
        result = await api("/api/save", { method: "POST", body: JSON.stringify({ ...JSON.parse(payload), base: JSON.parse(lastSavedPayload || "{}") }) });
        lastSavedPayload = payload;
        // Re-read after the request: edits made while saving must be saved next.
      }
      saveStatus(result.restart_live ? "Đã lưu · đổi TikTok/TTS cần chạy lại LIVE" : "Đã tự động lưu");
      return result;
    })().catch(error => { saveStatus(`Lỗi lưu: ${error.message}`, true); throw error; })
      .finally(() => { saveFlight = null; });
  }
  const result = await saveFlight;
  if (showMessage) toast(result.message + (result.restart_live ? " · hãy chạy lại LIVE để áp dụng phần TikTok" : ""));
  return result;
}

async function runAction(name, saveFirst = false) {
  try {
    if (saveFirst) await save(false);
    const result = await api("/api/action", { method: "POST", body: JSON.stringify({ name }) });
    toast(result.message); if ("running" in result) setLiveBadge(result.running);
    if (name.startsWith("test_")) showTab("logs");
  } catch (error) { toast(error.message, true); }
}

async function pollLogs() {
  try {
    const data = await api(`/api/logs?offset=${logOffset}`, {cache: "no-store", signal: AbortSignal.timeout(5000)});
    if (data.lines.length) {
      const box = $("#logBox"); box.textContent = (box.textContent + `${data.lines.join("\n")}\n`).slice(-120000); box.scrollTop = box.scrollHeight;
      const testLines = data.lines.filter(line => /\[(TEST|ERROR)\]/.test(line));
      if (testLines.length) {
        const box = $("#testLogBox"); box.textContent = (box.textContent + testLines.join("\n") + "\n").slice(-40000); box.scrollTop = box.scrollHeight;
      }
    }
    if (data.test) updateTestStatus(data.test);
    logOffset = data.offset; setLiveBadge(data.live_running);
  } catch (_) {}
  setTimeout(pollLogs, 700);
}

async function loadVoiceCatalog(silent = false) {
  const apiKey = value("api_key");
  const request = ++voiceCatalogRequest;
  const status = $("#voiceCatalogStatus");
  status.textContent = "Đang tải danh sách giọng và model…";
  renderVoiceChoices();
  try {
    if (!silent) toast("Đang tải voice và model từ ElevenLabs…");
    const result = await api("/api/elevenlabs", { method: "POST", body: JSON.stringify({ api_key: apiKey }) });
    if (request !== voiceCatalogRequest) return;
    voiceCatalog = { voices: result.voices || [], models: result.models?.length ? result.models : defaultVoiceModels };
    renderVoiceChoices();
    status.textContent = `${voiceCatalog.voices.length} giọng · ${voiceCatalog.models.length} model`;
    status.classList.toggle("warning", Boolean(result.warnings?.length));
    if (result.warnings?.length) status.textContent += "\n" + result.warnings.join("\n");
    if (!silent) {
      toast(`Đã tải ${voiceCatalog.voices.length} giọng và ${voiceCatalog.models.length} model`);
    }
  } catch (error) {
    if (request !== voiceCatalogRequest) return;
    status.textContent = `Chưa tải được danh sách: ${error.message}. Vẫn có thể chọn model tích hợp hoặc nhập Voice ID.`;
    status.classList.add("warning");
    if (!silent) toast(error.message, true);
  }
}

function renderVoiceChoices() {
  const selected = value("tts_voice_id");
  const query = value("voice_search").trim().toLowerCase();
  const voices = [...voiceCatalog.voices];
  if (selected && !voices.some(voice => voice.voice_id === selected))
    voices.unshift({ voice_id: selected, name: value("tts_voice_name") || "Giọng hiện tại" });
  const filtered = voices.filter(voice => `${voice.name} ${voice.voice_id}`.toLowerCase().includes(query));
  $("#voice_choice").innerHTML = `<option value="">${filtered.length ? "Chọn giọng đọc…" : "Không tìm thấy giọng"}</option>`
    + filtered.map(voice => `<option value="${escapeHtml(voice.voice_id)}">${escapeHtml(`${voice.name} — ${voice.voice_id}`)}</option>`).join("");
  setValue("voice_choice", filtered.some(voice => voice.voice_id === selected) ? selected : "");
  const models = [...voiceCatalog.models];
  const modelId = value("tts_model_id");
  if (modelId && !models.some(model => model.model_id === modelId)) models.unshift({ model_id: modelId, name: "Model đang dùng" });
  $("#tts_model_choice").innerHTML = models.map(model => `<option value="${escapeHtml(model.model_id)}">${escapeHtml(`${model.name} — ${model.model_id}`)}</option>`).join("");
  setValue("tts_model_choice", modelId);
  renderVoiceModelHelp();
}

function renderVoiceModelHelp() {
  const id = value("tts_model_id");
  const model = defaultVoiceModels.find(model => model.model_id === id) || voiceCatalog.models.find(model => model.model_id === id);
  $("#voiceModelHelp").textContent = model?.description || "Chọn model được tài khoản ElevenLabs của bạn hỗ trợ.";
}

function bindVoiceSearch() {
  $("#edge_preset").addEventListener("change", event => {
    const preset = {cute: [60, 10], soft: [20, -5], energetic: [35, 15], normal: [0, 0]}[event.target.value];
    if (!preset) return;
    if (event.target.value !== "normal") setValue("tts_edge_voice", "vi-VN-HoaiMyNeural");
    setValue("tts_edge_pitch", preset[0]); setValue("tts_edge_rate", preset[1]); scheduleAutoSave();
  });
  ["tts_edge_pitch", "tts_edge_rate", "tts_edge_voice"].forEach(id => $(`#${id}`).addEventListener("input", () => setValue("edge_preset", "")));
  $("#tts_provider").addEventListener("change", () => {
    renderTtsProvider();
    if (value("tts_provider") === "elevenlabs") loadVoiceCatalog(true);
  });
  $("#reloadVoicevoxBtn").addEventListener("click", loadVoicevoxCatalog);
  $("#tts_voicevox_url").addEventListener("input", () => {
    ++voicevoxRequest; voicevoxVoices = []; renderVoicevoxChoices();
    $("#voicevoxStatus").textContent = "Địa chỉ đã đổi. Bấm Tải giọng để kết nối lại.";
  });
  $("#voicevox_choice").addEventListener("change", event => {
    setValue("tts_voicevox_speaker_id", event.target.value); scheduleAutoSave();
  });
  $("#tts_voicevox_speaker_id").addEventListener("input", renderVoicevoxChoices);
  $("#voicevox_preset").addEventListener("change", event => {
    const preset = { cute: [1.05, 0.06, 1.2], soft: [0.9, 0.02, 0.85], energetic: [1.15, 0.04, 1.4], normal: [1, 0, 1] }[event.target.value];
    if (!preset) return;
    ["speed", "pitch", "intonation"].forEach((field, i) => setValue(`tts_voicevox_${field}`, preset[i]));
    scheduleAutoSave();
  });
  ["speed", "pitch", "intonation"].forEach(field => $(`#tts_voicevox_${field}`).addEventListener("input", () => setValue("voicevox_preset", "")));
  $("#voice_search").addEventListener("input", renderVoiceChoices);
  $("#voice_choice").addEventListener("change", event => {
    const voice = voiceCatalog.voices.find(item => item.voice_id === event.target.value);
    if (voice) { setValue("tts_voice_name", voice.name); setValue("tts_voice_id", voice.voice_id); scheduleAutoSave(); }
  });
  $("#tts_model_choice").addEventListener("change", event => {
    if (event.target.value) { setValue("tts_model_id", event.target.value); renderVoiceModelHelp(); scheduleAutoSave(); }
  });
  ["tts_voice_id", "tts_voice_name"].forEach(id => $(`#${id}`).addEventListener("input", () => {
    setValue("voice_search", ""); renderVoiceChoices();
  }));
  $("#tts_model_id").addEventListener("input", renderVoiceChoices);
}

function setPreviewSize(size) {
  const width = Number(size?.width) || 1920, height = Number(size?.height) || 1080;
  $("#notificationPreview").style.aspectRatio = `${width} / ${height}`;
  $("#previewSizeLabel").textContent = size?.detected
    ? `Theo cửa sổ Minecraft: ${width} × ${height} · Kéo chữ để đặt vị trí`
    : "Chưa thấy cửa sổ Minecraft · Xem thử tỷ lệ 16:9 (1920 × 1080)";
  renderSettingsPreview();
}

const notificationKinds = { like: "Like", comment: "Comment", share: "Share", follow: "Follow", view: "View", gift: "Quà tặng" };
function collectPositions() {
  return Object.fromEntries(Object.keys(notificationKinds).map(kind => {
    const row = document.querySelector(`[data-position-kind="${kind}"]`);
    const previous = state?.mod?.notification_positions?.[kind] || { x: 50, y: 40, scale: 1 };
    return [kind, row ? Object.fromEntries(["x", "y", "scale"].map(key => [key, Number(row.querySelector(`[data-axis="${key}"]`).value)])) : { ...previous }];
  }));
}
const displayModes = { legacy: "Kiểu cũ / vị trí tùy chỉnh", center: "Giữa màn hình", chat: "Chat trong game" };
function collectDisplayModes() {
  return Object.fromEntries(Object.keys(notificationKinds).map(kind => [kind,
    document.querySelector(`[data-display-kind="${kind}"]`)?.value || state?.mod?.notification_display_modes?.[kind] || "legacy"]));
}
function initializeDisplayModes() {
  const modes = collectDisplayModes();
  $("#notificationDisplayModes").innerHTML = Object.entries(notificationKinds).map(([kind, label]) =>
    `<label>${label}<select data-display-kind="${kind}">${Object.entries(displayModes).map(([mode, text]) => `<option value="${mode}" ${modes[kind] === mode ? "selected" : ""}>${text}</option>`).join("")}</select></label>`).join("");
  $("#notificationDisplayModes").addEventListener("change", event => {
    setValue("positionPreviewKind", event.target.dataset.displayKind);
    renderSettingsPreview(); scheduleAutoSave();
  });
  $("#applyDisplayModeAll").addEventListener("click", () => {
    $$("[data-display-kind]").forEach(select => select.value = value("bulkDisplayMode"));
    renderSettingsPreview(); scheduleAutoSave(); toast("Đã áp dụng kiểu hiển thị cho tất cả tương tác");
  });
}
function initializePositions() {
  initializeDisplayModes();
  const positions = collectPositions();
  $("#notification_positions").innerHTML = Object.entries(notificationKinds).map(([kind, label]) => `<div class="position-row" data-position-kind="${kind}"><label class="check"><input class="position-tick" type="checkbox">${label}</label>${["x", "y", "scale"].map((axis, i) => `<label>${["Ngang %", "Dọc %", "Cỡ chữ"][i]}<input data-axis="${axis}" type="number" min="${axis === "scale" ? 0.5 : 0}" max="${axis === "scale" ? 4 : 100}" step="${axis === "scale" ? 0.1 : 1}" value="${Number(positions[kind][axis])}"></label>`).join("")}</div>`).join("");
  $("#notification_positions").addEventListener("input", event => {
    if (!event.target.dataset.axis) return;
    setValue("positionPreviewKind", event.target.closest("[data-position-kind]").dataset.positionKind);
    renderSettingsPreview();
  });
  const apply = all => {
    const controls = ["bulkPositionX", "bulkPositionY", "bulkPositionScale"].map(id => $(`#${id}`));
    if (controls.some(node => node.value === "" || !node.checkValidity())) { toast("Kiểm tra tọa độ và cỡ chữ chung", true); return; }
    const rows = $$("[data-position-kind]").filter(row => all || $(".position-tick", row).checked);
    if (!rows.length) { toast("Hãy tick ít nhất một loại thông báo", true); return; }
    rows.forEach(row => ["x", "y", "scale"].forEach((axis, i) => { $(`[data-axis="${axis}"]`, row).value = controls[i].value; }));
    setValue("positionPreviewKind", rows[0].dataset.positionKind);
    renderSettingsPreview(); scheduleAutoSave(); toast(`Đã áp dụng vị trí cho ${rows.length} loại`);
  };
  $("#applyPositionSelected").addEventListener("click", () => apply(false));
  $("#applyPositionAll").addEventListener("click", () => apply(true));
  $("#positionPreviewKind").addEventListener("change", renderSettingsPreview);
  const sample = $("#notificationPreviewText"), preview = $("#notificationPreview");
  let dragging = false, offsetX = 0, offsetY = 0;
  sample.addEventListener("pointerdown", event => {
    if (collectDisplayModes()[value("positionPreviewKind")] !== "legacy") return;
    dragging = true; sample.setPointerCapture(event.pointerId);
    const bounds = sample.getBoundingClientRect(); offsetX = event.clientX - bounds.left; offsetY = event.clientY - bounds.top;
  });
  sample.addEventListener("pointermove", event => {
    if (!dragging) return;
    const bounds = preview.getBoundingClientRect();
    const row = $(`[data-position-kind="${value("positionPreviewKind")}"]`);
    const clamp = n => Math.round(Math.min(100, Math.max(0, n)));
    $('[data-axis="x"]', row).value = clamp((event.clientX - bounds.left - offsetX) / Math.max(1, preview.clientWidth - sample.offsetWidth) * 100);
    $('[data-axis="y"]', row).value = clamp((event.clientY - bounds.top - offsetY) / Math.max(1, preview.clientHeight - sample.offsetHeight) * 100);
    renderSettingsPreview();
  });
  sample.addEventListener("pointerup", () => { dragging = false; scheduleAutoSave(); });
  sample.addEventListener("pointercancel", () => { dragging = false; scheduleAutoSave(); });
  new ResizeObserver(renderSettingsPreview).observe(preview);
  $("#refreshPreviewSize").addEventListener("click", async () => {
    try { setPreviewSize(await api("/api/minecraft-viewport")); }
    catch (error) { toast(error.message, true); }
  });
}

let previewDonation = false;
function renderSettingsPreview() {
  const preview = $("#notificationPreview");
  const title = $("strong", preview), username = $("span", preview);
  previewDonation = value("positionPreviewKind") === "gift";
  title.textContent = previewDonation ? "Quà: Hoa Hồng" : value("positionPreviewKind") !== "comment" ? `+ ${notificationKinds[value("positionPreviewKind")]}` : checked("display_comment_text") ? "Xin chào, chúc buổi LIVE vui vẻ!" : "Comment";
  title.style.color = value(previewDonation ? "donation_notification_color" : "notification_title_color");
  username.style.color = value(previewDonation ? "donation_notification_color" : "notification_username_color");
  preview.style.fontWeight = previewDonation && checked("donation_notification_bold") ? "700" : "400";
  username.hidden = !checked("notification_show_username");
  preview.style.opacity = checked("notification_enabled") ? "1" : "0.35";
  const mode = collectDisplayModes()[value("positionPreviewKind")] || "legacy";
  const pos = { ...(collectPositions()[value("positionPreviewKind")] || { x: 50, y: 40, scale: 1 }) };
  if (mode === "center") { pos.x = 50; pos.y = 50; }
  if (mode === "chat") { pos.x = 0; pos.y = 100; }
  $("#notificationPreviewText").classList.toggle("chat-preview", mode === "chat");
  $("#notificationPreviewText").style.cursor = mode === "legacy" ? "grab" : "default";
  $("#displayModeHint").textContent = mode === "chat" ? "Thông báo vào lịch sử chat Minecraft; vị trí tùy theo giao diện chat của game." : mode === "center" ? "Căn giữa màn hình; giữ nguyên vị trí tùy chỉnh đã lưu để dùng lại kiểu cũ." : "Kéo thông báo để đổi vị trí kiểu cũ.";
  const sample = $("#notificationPreviewText");
  sample.style.fontSize = `${pos.scale * 14 * preview.clientWidth / 960}px`;
  sample.style.left = `${Math.max(0, preview.clientWidth - sample.offsetWidth) * pos.x / 100}px`;
  sample.style.top = `${Math.max(0, preview.clientHeight - sample.offsetHeight) * pos.y / 100}px`;
  $("#ttsQueueHelp").textContent = checked("tts_keep_latest_comment")
    ? "Trong khoảng chờ, chỉ giữ câu mới nhất để đọc; khi hàng đầy, thay câu cũ nhất bằng câu mới. Câu đang phát vẫn được đọc hết."
    : "Đọc lần lượt toàn bộ câu đã nhận vào hàng đợi, nghỉ sau mỗi câu. Khi đầy, bỏ câu mới; tăng hàng đợi để nhận thêm.";
}

let testRunning = false;
let testSubmitting = false;
function renderTests() {
  const picker = $("#testMobPicker");
  if (!picker.firstElementChild) {
    const mob = state.catalog.mobs.find(x => x.target === "minecraft:zombie") || state.catalog.mobs[0];
    if (mob) {
      picker.innerHTML = dropdownMarkup("test-mob-dropdown", mob.target, mob.vietnamese_name || mob.target, "Tìm mob cần triệu hồi…");
      mountSearchDropdown(picker.firstElementChild, state.catalog.mobs, {
        getValue: x => x.target, getLabel: x => `${x.vietnamese_name} — ${x.target}`, getImage: iconUrl,
        onSelect: () => {},
      });
    }
  }
  $("#testEventButtons").innerHTML = eventTypes.map(type => {
    const card = $(`.event-editor[data-prefix="${type.prefix}"]`);
    const mob = $(".event-mob-dropdown", card).dataset.value;
    const count = type.prefix === "like" ? numberValue("like_spawn_count") : Number($(".event-count", card).value);
    return `<button data-test-run data-test-event="${type.prefix}">${type.title}<small>${escapeHtml(mob)} × ${count}</small></button>`;
  }).join("");
  $$('[data-test-event]').forEach(button => button.addEventListener("click", () => launchTest("event", { event: button.dataset.testEvent })));
  renderTestGifts();
  updateSpamEstimate();
  updateTestButtons();
}

function renderTestGifts() {
  const query = value("testGiftSearch").toLowerCase().trim();
  $("#testGiftList").innerHTML = mappings.map((rule, index) => ({ rule, index }))
    .filter(({ rule }) => `${rule.gift_name} ${rule.vietnamese_name || ""}`.toLowerCase().includes(query))
    .map(({ rule, index }) => `<div class="test-gift-row">${giftImageMarkup(rule, "source-gift-image")}<div><b>${escapeHtml(rule.gift_name)}</b><small>${escapeHtml(rule.action)}: ${escapeHtml(rule.target)} × ${Number(rule.amount)}</small></div><button data-test-run data-test-gift="${index}">Test quà này</button></div>`).join("") || '<p class="settings-help">Không có quà phù hợp. Gán quà tại tab Quà tặng.</p>';
  $$('[data-test-gift]').forEach(button => button.addEventListener("click", () => launchTest("gift", { gift_index: Number(button.dataset.testGift) })));
  updateTestButtons();
}

function updateTestButtons() {
  $$('[data-test-run]').forEach(button => button.disabled = testRunning || testSubmitting);
  $("#stopTestBtn").disabled = !testRunning;
}

function updateTestStatus(status) {
  testRunning = status.running;
  $("#testStatus").textContent = `${status.message} · ${status.sent}/${status.total}`;
  $("#testProgress").max = Math.max(1, status.total);
  $("#testProgress").value = status.sent;
  updateTestButtons();
}

function updateSpamEstimate() {
  if (!state) return;
  const selected = value("testSpamEvent");
  const types = selected === "all" ? eventTypes : eventTypes.filter(type => type.prefix === selected);
  const perRound = types.reduce((sum, type) => {
    const editor = $(`.event-editor[data-prefix="${type.prefix}"]`);
    return sum + (type.prefix === "like" ? numberValue("like_spawn_count") : Number($(".event-count", editor).value));
  }, 0);
  const total = perRound * numberValue("testSpamCount") * numberValue("testSpamUsers");
  $("#testSpamEstimate").textContent = `Dự kiến ${total} lệnh triệu hồi. Giới hạn hiện tại: ${numberValue("max_mobs_per_user")} mob/người, ${numberValue("max_mobs_total")} mob toàn world. Tối đa 10.000 lệnh/bài test.`;
}

async function launchTest(mode, extra = {}) {
  if (testSubmitting || testRunning) return;
  testSubmitting = true; updateTestButtons();
  try {
    const ids = mode === "spam" ? ["testSpamUsers", "testSpamCount", "testSpamInterval"] : ["testUsers", "testCount", "testInterval"];
    for (const id of ids) if (!$(`#${id}`).checkValidity() || value(id) === "") throw new Error("Hãy điền thông số test đúng khoảng cho phép.");
    await save(false);
    const payload = {
      mode, name: value("testName"), users: numberValue(ids[0]), count: numberValue(ids[1]), interval: numberValue(ids[2], 0),
      mob: $(".test-mob-dropdown")?.dataset.value || "minecraft:zombie", ...extra,
    };
    if (mode === "spam") payload.event = value("testSpamEvent");
    updateTestStatus(await api("/api/test", { method: "POST", body: JSON.stringify(payload) }));
  } catch (error) { toast(error.message, true); }
  finally { testSubmitting = false; updateTestButtons(); }
}

function bindTests() {
  $("#testSingleMobBtn").addEventListener("click", () => launchTest("mob"));
  $("#testFullMobsBtn").addEventListener("click", () => launchTest("all_mobs"));
  $("#testSpamBtn").addEventListener("click", () => launchTest("spam"));
  $("#testAllGiftsBtn").addEventListener("click", () => launchTest("all_gifts"));
  $("#testGiftSearch").addEventListener("input", renderTestGifts);
  ["testSpamEvent", "testSpamUsers", "testSpamCount", "testSpamInterval"].forEach(id => $(`#${id}`).addEventListener("input", updateSpamEstimate));
  $("#stopTestBtn").addEventListener("click", async () => {
    try { updateTestStatus(await api("/api/test/stop", { method: "POST", body: "{}" })); }
    catch (error) { toast(error.message, true); }
  });
}

function bindStaticEvents() {
  bindTests();
  window.addEventListener("online", scheduleAutoSave);
  for (const type of ["input", "change"]) document.addEventListener(type, event => {
    const node = event.target;
    if (node.closest('[data-view="tests"]') || node.matches('.search, .dropdown-search, input[type="file"], #voice_search, #tts_model_choice')) {
      if (node.matches('#voice_search, #tts_model_choice')) scheduleAutoSave();
      return;
    }
    if (node.matches('input, select')) scheduleAutoSave();
  });
  window.addEventListener("beforeunload", event => {
    if (autoSaveReady && !document.body.classList.contains("detached-panel") && JSON.stringify(collectPayload()) !== lastSavedPayload) {
      save(false).catch(() => {});
      event.preventDefault(); event.returnValue = "";
    }
  });
  $("#previewDonationBtn").addEventListener("click", () => { previewDonation = !previewDonation; setValue("positionPreviewKind", previewDonation ? "gift" : "comment"); renderSettingsPreview(); });
  $$('[data-config], #tts_keep_latest_comment').forEach(node => node.addEventListener("input", renderSettingsPreview));
  panelChannel?.addEventListener("message", event => {
    if (document.body.classList.contains("detached-panel")) applyPanelPreview(event.data);
  });
  document.addEventListener("click", () => $$(".search-dropdown.open").forEach(node => node.classList.remove("open")));
  $$(".tab").forEach(tab => tab.addEventListener("click", () => showTab(tab.dataset.tab)));
  $$('[data-go]').forEach(button => button.addEventListener("click", () => showTab(button.dataset.go)));
  $("#giftSearch").addEventListener("input", renderGiftSources);
  $("#rewardSearch").addEventListener("input", renderRewardSources);
  $$(".chip").forEach(chip => chip.addEventListener("click", () => { rewardFilter = chip.dataset.filter; $$(".chip").forEach(x => x.classList.toggle("active", x === chip)); renderRewardSources(); }));
  $("#addGiftBtn").addEventListener("click", () => { mappings.push(defaultRule()); selectedMapping = mappings.length - 1; renderMappings(); renderLivePanel(); });
  $("#startBtn").addEventListener("click", () => runAction("start_live", true));
  $("#stopBtn").addEventListener("click", () => runAction("stop_live"));
  $("#testGiftsBtn").addEventListener("click", () => runAction("test_gifts", true));
  $("#testGiftAlertBtn").addEventListener("click", () => runAction("test_gift_alert", true));
  $$("[data-settings-tab]").forEach(button => button.addEventListener("click", () => showSettingsTab(button.dataset.settingsTab)));
  $("#testTtsBtn").addEventListener("click", () => runAction("test_tts", true));
  $("#reloadVoicesBtn").addEventListener("click", () => loadVoiceCatalog(false));
  $("#installBtn").addEventListener("click", () => runAction("install_mod", true));
  $("#clearLogsBtn").addEventListener("click", () => $("#logBox").textContent = "");
  $("#copyPanelBtn").addEventListener("click", () => {
    if (window.chrome?.webview) window.chrome.webview.postMessage("copy-panel");
    else toast("Mở bằng MO_GUI.bat / WinForms để sao chép ảnh panel.", true);
  });
  ["view_enabled", "view_interval_seconds"].forEach(id => $(`#${id}`).addEventListener("input", renderLivePanel));
  ["like_spawn_count","comment_limit","comment_cooldown_seconds","share_limit","share_cooldown_seconds","max_mobs_per_user","max_mobs_total","mob_lifetime_seconds"].forEach(id => $(`#${id}`).addEventListener("input", renderLivePanel));
  bindVoiceSearch();
  bindGiftSettings();
}

async function initialize() {
  bindStaticEvents();
  const query = new URLSearchParams(location.search);
  if (query.get("panel") === "1") document.body.classList.add("detached-panel");
  try {
    state = await api("/api/state");
    await loadGiftMedia();
    let storedPreview = null;
    if (query.get("panel") === "1") {
      try { storedPreview = JSON.parse(localStorage.getItem(panelPreviewKey) || "null"); }
      catch (_) { localStorage.removeItem(panelPreviewKey); }
    }
    if (storedPreview?.bridge && Array.isArray(storedPreview.mappings)) {
      state.bridge = { ...state.bridge, ...storedPreview.bridge, event_images: { ...(storedPreview.bridge.event_images || {}) } };
      mappings = storedPreview.mappings.map(rule => ({ ...rule }));
    } else mappings = (state.bridge.gift_actions || []).map(rule => ({ ...rule }));
    setValue("tiktok_username", state.bridge.tiktok_username); setValue("minecraft_host", state.bridge.minecraft_host); setValue("minecraft_port", state.bridge.minecraft_port);
    setValue("like_spawn_count", state.bridge.like_spawn_count || 1);
    setValue("comment_limit", state.bridge.comment_limit); setValue("comment_cooldown_seconds", state.bridge.comment_cooldown_seconds);
    setValue("share_limit", state.bridge.share_limit || 1); setValue("share_cooldown_seconds", state.bridge.share_cooldown_seconds || 10);
    setValue("minecraft_directory", state.gui.minecraft_directory); setChecked("keep_minecraft_running_in_background", state.gui.keep_minecraft_running_in_background);
    setValue("max_mobs_per_user", state.mod.max_mobs_per_user); setValue("max_mobs_total", state.mod.max_mobs_total || 4); setValue("mob_lifetime_seconds", state.mod.mob_lifetime_seconds);
    setValue("golem_teleport_distance", state.mod.golem_teleport_distance ?? 20); setValue("wolf_teleport_distance", state.mod.wolf_teleport_distance ?? 20);
    setValue("max_interactions_per_tick", state.mod.max_interactions_per_tick); setValue("spawn_min_distance", state.mod.spawn_min_distance); setValue("spawn_max_distance", state.mod.spawn_max_distance);
    setValue("spawn_direction", state.mod.spawn_direction || "front"); setValue("spawn_height_offset", state.mod.spawn_height_offset); setValue("max_pending_events", state.mod.max_pending_events);
    setValue("notification_queue_size", state.mod.notification_queue_size); setValue("notification_duration_seconds", state.mod.notification_duration_seconds);
    setValue("donation_notification_duration_seconds", state.mod.donation_notification_duration_seconds);
    setChecked("enderman_targets_player", state.mod.enderman_targets_player); setChecked("mobs_persistent", state.mod.mobs_persistent); setChecked("show_countdown_in_name", state.mod.show_countdown_in_name); setChecked("show_death_counter", state.mod.show_death_counter);
    setValue("effect_duration_seconds", state.mod.effect_duration_seconds); setValue("absorption_hearts_per_rose", state.mod.absorption_hearts_per_rose);
    setValue("money_gun_arrow_count", state.mod.money_gun_arrow_count); setValue("universe_effect_level", state.mod.universe_effect_level);
    setValue("api_key", state.api_key); setValue("tts_voice_name", state.bridge.tts_voice_name); setValue("tts_voice_id", state.bridge.tts_voice_id); setValue("tts_model_id", state.bridge.tts_model_id);
    setChecked("tts_enabled", state.bridge.tts_enabled);
    setChecked("tts_read_username", state.bridge.tts_read_username); setValue("tts_max_characters", state.bridge.tts_max_characters); setValue("tts_queue_size", state.bridge.tts_queue_size);
    setChecked("tts_keep_latest_comment", state.bridge.tts_keep_latest_comment); setValue("tts_pause_between_comments_seconds", state.bridge.tts_pause_between_comments_seconds);
    setValue("tts_trailing_silence_seconds", state.bridge.tts_trailing_silence_seconds); setValue("tts_stability", state.bridge.tts_stability);
    setValue("tts_similarity_boost", state.bridge.tts_similarity_boost); setValue("tts_style", state.bridge.tts_style); setValue("tts_speed", state.bridge.tts_speed);
    setValue("tts_language_code", state.bridge.tts_language_code); setChecked("tts_use_speaker_boost", state.bridge.tts_use_speaker_boost);
    $$('[data-config]').forEach(node => {
      const saved = state[node.dataset.config][node.id];
      if (saved === undefined) throw new Error("Cần đóng và mở lại MO_GUI.bat để nạp phần Cài đặt mới.");
      if (node.type === "checkbox") node.checked = saved;
      else node.value = saved;
    });
    initializePositions();
    renderUnmappedReward();
    pollGiftCatalog();
    renderTtsProvider();
    setPreviewSize(state.minecraft_viewport);
    renderGiftSettings();
    renderVoiceChoices();
    renderSettingsPreview();
    renderEvents(); renderGiftSources(); renderRewardSources(); renderMappings(); renderLivePanel(); setLiveBadge(state.live_running);
    renderTests();
    lastSavedPayload = JSON.stringify(collectPayload());
    autoSaveReady = true;
    pollRuntimeSettings();
    if (["live", "events", "gifts", "settings", "voicevox", "tests", "logs"].includes(query.get("view"))) showTab(query.get("view"));
    $("#loading").remove();
    if (value("tts_provider") === "elevenlabs") loadVoiceCatalog(true);
  } catch (error) { $("#loading").textContent = error.message; toast(error.message, true); }
  pollLogs();
}

document.addEventListener("contextmenu", event => {
  const card = event.target.closest("#giftPreview [data-gift-index]");
  if (!card) return;
  event.preventDefault();
  const rule = mappings[Number(card.dataset.giftIndex)];
  if (!rule) return;
  document.querySelector(".gift-note-dialog")?.remove();
  const dialog = document.createElement("dialog");
  dialog.className = "gift-note-dialog";
  dialog.innerHTML = `<form method="dialog"><h3>Chú thích quà tặng</h3><p class="gift-note-name"></p><label>Chữ nhỏ trên item<input name="note" maxlength="160" autocomplete="off" placeholder="Ví dụ: Enchant cấp 5 · cộng dồn +1"></label><small>Để trống để xóa chú thích.</small><div class="actions"><button value="cancel">Hủy</button><button value="save" class="primary">Lưu chú thích</button></div></form>`;
  dialog.querySelector(".gift-note-name").textContent = rule.gift_name;
  dialog.querySelector("input").value = rule.panel_note || "";
  dialog.addEventListener("close", () => {
    if (dialog.returnValue === "save" && mappings.includes(rule)) {
      rule.panel_note = dialog.querySelector("input").value.trim();
      renderLivePanel();
    }
    dialog.remove();
  });
  document.body.append(dialog);
  dialog.showModal();
  dialog.querySelector("input").focus();
});

initialize();
