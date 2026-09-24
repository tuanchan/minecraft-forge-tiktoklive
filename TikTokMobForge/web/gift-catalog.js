let giftCatalogSignature = "";

function renderUnmappedReward() {
  const active = value("unmapped_gift_mode", "thanks") === "reward";
  $("#unmappedRewardSettings").hidden = !active;
  const key = `${value("unmapped_gift_action")}|${value("unmapped_gift_target")}`;
  const reward = allRewards().find(entry => rewardKey(entry) === key);
  $("#unmappedRewardPicker").innerHTML = dropdownMarkup("unmapped-reward", key,
    reward?.vietnamese_name || value("unmapped_gift_target"), "Tìm vật phẩm, mob hoặc hiệu ứng…");
  $("#unmapped_gift_level").min = value("unmapped_gift_target").startsWith("enchant_") ? 0 : 1;
  mountSearchDropdown($(".unmapped-reward"), allRewards(), {
    getValue: rewardKey, getLabel: entry => `${entry.vietnamese_name} — ${entry.target}`,
    getImage: iconUrl,
    onSelect: entry => {
      setValue("unmapped_gift_action", entry.kind);
      setValue("unmapped_gift_target", entry.target);
      setValue("unmapped_gift_level", entry.target.startsWith("enchant_") ? 0 : 1);
      renderUnmappedReward(); scheduleAutoSave();
    },
  });
}

async function pollGiftCatalog() {
  try {
    const result = await api("/api/gifts");
    $("#updateGiftsBtn").disabled = result.update.running;
    $("#giftCatalogStatus").textContent = `${result.gifts.length} quà · ${result.update.message}`;
    const signature = JSON.stringify(result.gifts);
    if (signature !== giftCatalogSignature) {
      giftCatalogSignature = signature;
      state.gifts = result.gifts;
      renderGiftSources(); renderMappings(); renderLivePanel(false);
    }
  } catch (error) {
    $("#giftCatalogStatus").textContent = error.message;
  } finally {
    setTimeout(pollGiftCatalog, 4000);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("#unmapped_gift_mode").addEventListener("change", () => { renderUnmappedReward(); scheduleAutoSave(); });
  $("#updateGiftsBtn").addEventListener("click", async () => {
    const button = $("#updateGiftsBtn");
    button.disabled = true;
    try {
      await save(false);
      const result = await api("/api/action", {method: "POST", body: JSON.stringify({name: "update_gifts"})});
      $("#giftCatalogStatus").textContent = result.message;
    } catch (error) { button.disabled = false; toast(error.message, true); }
  });
});
