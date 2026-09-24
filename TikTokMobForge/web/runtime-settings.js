let runtimeSyncError = "";
async function pollRuntimeSettings() {
  try {
    if (!autoSaveReady || saveFlight) return;
    const savedBeforeRequest = lastSavedPayload;
    const remote = await api("/api/runtime-settings", {cache: "no-store", signal: AbortSignal.timeout(5000)});
    if (runtimeSyncError) {
      runtimeSyncError = "";
      saveStatus("Đã kết nối lại đồng bộ Minecraft");
    }
    if (saveFlight || lastSavedPayload !== savedBeforeRequest) return;
    const current = collectPayload();
    const baseline = JSON.parse(lastSavedPayload || "{}");
    let changed = false;
    for (const section of ["bridge", "mod"]) {
      for (const [key, raw] of Object.entries(remote[section])) {
        const incoming = key.endsWith("_mob_type") ? raw.replace(/^minecraft:/, "") : raw;
        // Keep local drafts. A stale full-form save sends only fields changed
        // against this baseline, rather than overwriting unrelated game edits.
        const normalize = value => key.endsWith("_mob_type") && typeof value === "string" ? value.replace(/^minecraft:/, "") : value;
        if (JSON.stringify(normalize(current[section][key])) !== JSON.stringify(normalize(baseline[section]?.[key]))) continue;
        if (current[section][key] === incoming) continue;
        state[section][key] = incoming;
        baseline[section][key] = incoming;
        const node = document.getElementById(key);
        // A focused field can still contain its old value while the user starts
        // typing; update it after focus leaves instead of moving their cursor.
        const prefix = key.split("_")[0];
        const card = document.querySelector(`.event-editor[data-prefix="${prefix}"]`);
        const dynamicNode = key === "likes_per_skeleton"
          ? $('.event-editor[data-prefix="like"] .event-count')
          : card && key.endsWith("_spawn_count") && prefix !== "like" ? $(".event-count", card) : null;
        if (node === document.activeElement || dynamicNode === document.activeElement
            || (card && key.endsWith("_mob_type") && $(".event-mob-dropdown", card).contains(document.activeElement))) {
          // Undo baseline advancement: this field is still pending a UI update.
          state[section][key] = current[section][key];
          baseline[section][key] = current[section][key];
          continue;
        }
        if (node) {
          if (node.type === "checkbox") node.checked = incoming;
          else node.value = incoming;
        }
        if (card && key.endsWith("_mob_type")) {
          const root = $(".event-mob-dropdown", card);
          const id = incoming.includes(":") ? incoming : `minecraft:${incoming}`;
          root.dataset.value = id;
          $(".dropdown-toggle span", root).textContent = state.catalog.mobs.find(x => x.target === id)?.vietnamese_name || id;
          const img = $(".event-preview", card);
          if (img) img.src = eventMobImage(prefix, {kind:"mob", target:id});
        }
        if (card && key.endsWith("_spawn_count") && prefix !== "like") $(".event-count", card).value = incoming;
        if (key === "likes_per_skeleton") $('.event-editor[data-prefix="like"] .event-count').value = incoming;
        changed = true;
      }
    }
    if (changed) {
      lastSavedPayload = JSON.stringify(baseline);
      $$(".event-editor").forEach(updateEventRule);
      renderLivePanel();
      updateSpamEstimate();
      saveStatus("Đã đồng bộ cài đặt từ Minecraft");
    }
  } catch (error) {
    const message = `Đồng bộ Minecraft gián đoạn, đang tự kết nối lại: ${error.message}`;
    saveStatus(message, true);
    if (!runtimeSyncError) toast(message, true);
    runtimeSyncError = error.message || message;
  } finally {
    setTimeout(pollRuntimeSettings, 500);
  }
}
