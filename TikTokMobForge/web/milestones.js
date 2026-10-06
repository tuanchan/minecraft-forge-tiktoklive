(() => {
  const labels = {like:'Tim', follow:'Follow', comment:'Bình luận', share:'Chia sẻ', coins:'Xu quà tặng'};
  let progress = {groups:{}}, initialized = false;
  function defaults(kind) {
    const fallback = {like:'skeleton',follow:'creeper',comment:'zombie',share:'enderman',coins:'iron_golem'};
    const reward = eventReward(state.bridge[kind + '_mob_type'] || fallback[kind]);
    return {enabled:kind !== 'coins', remember:false, rules:[{id:kind+'-default', threshold:kind === 'like' ? state.bridge.likes_per_skeleton || 50 : kind === 'coins' ? 100 : 1,
      reward:reward.kind === 'mob' ? reward.target : reward.kind+':'+reward.target, amount:state.bridge[kind+'_spawn_count'] || 1}]};
  }
  const rewardValue = r => r.kind === 'mob' ? r.target : r.kind+':'+r.target;
  function changed() { renderMilestonePanels(); publishPanelPreview(); scheduleAutoSave(); }
  function editor(kind) {
    const group = state.bridge.milestones[kind];
    const section = document.createElement('section'); section.className='milestone-editor panel'; section.dataset.kind=kind;
    section.innerHTML=`<div class="milestone-editor-head"><h3>${labels[kind]} · mốc cả phòng LIVE</h3><label class="milestone-switch"><input type="checkbox" ${group.enabled?'checked':''}> Bật triệu hồi theo mốc</label></div>
      <p class="settings-help">Mốc tổng LIVE là phần thưởng cộng thêm. Tắt mốc chỉ ngừng đếm và trao thưởng mốc tổng; tương tác riêng từng người và quà đã gán vẫn hoạt động. Mỗi mốc lặp độc lập, giữ phần dư. Sửa hoặc bật/tắt mốc bắt đầu lại bộ đếm tổng của loại này.${kind==='coins'?' Xu = giá quà × số lượng combo đã kết thúc.':' Cộng sự kiện nhận được trong phòng; follow chỉ tính tài khoản được hệ thống chấp nhận lần đầu.'}</p><div class="milestone-rows"></div><button type="button" class="add-goal">+ Thêm mốc</button>`;
    section.querySelector('input[type=checkbox]').onchange=e=>{group.enabled=e.target.checked;changed();};
    section.querySelector('.milestone-editor-head').insertAdjacentHTML('afterend', `<label class="milestone-switch"><input class="goal-remember" type="checkbox" ${group.remember?'checked':''}> Ghi nhớ qua nhiều phiên LIVE</label><p class="settings-help">Bật: cộng dồn qua nhiều phiên LIVE và khi mở lại tool. Tắt: về 0 khi dừng; mỗi lần bấm Chạy LIVE hoặc sang phiên LIVE mới sẽ đếm lại. Tự kết nối lại do mất mạng vẫn giữ tiến độ. Đổi chế độ ghi nhớ giữ nguyên tiến độ hiện tại.</p>`);
    section.querySelector('.goal-remember').onchange=e=>{group.remember=e.target.checked;changed();};
    const rows=section.querySelector('.milestone-rows');
    for (const rule of group.rules) {
      const row=document.createElement('div');row.className='milestone-row';
      const rewards=allRewards();
      if (!rewards.some(r=>rewardValue(r)===rule.reward)) rewards.unshift(eventReward(rule.reward));
      const selected=eventReward(rule.reward);
      const rewardLabel=item=>`${item.kind==='mob'?'Mob':item.kind==='item'?'Vật phẩm':'Hiệu ứng'} · ${item.vietnamese_name||item.target} — ${item.target}`;
      row.innerHTML=`<label>Đủ ${labels[kind].toLowerCase()}<input class="goal-threshold" type="number" min="1" step="1" max="9007199254740991" value="${rule.threshold}"></label><div class="goal-reward-field"><span>Triệu hồi / trao quà</span><div class="goal-picker"><img class="goal-selected-image" src="${escapeHtml(iconUrl(selected))}" alt="${escapeHtml(selected.vietnamese_name||selected.target)}">${dropdownMarkup('goal-reward',rule.reward,rewardLabel(selected),'Tìm mob, vật phẩm (Totem), hiệu ứng…')}</div></div><label>Số lượng<input class="goal-amount" type="number" min="1" step="1" max="9007199254740991" value="${rule.amount}"></label><button type="button" class="delete-goal" aria-label="Xóa mốc">Xóa</button>`;
      for(const [selector,field] of [['.goal-threshold','threshold'],['.goal-amount','amount']]) row.querySelector(selector).onchange=e=>{
        const n=Number(e.target.value);if(!Number.isSafeInteger(n)||n<1){e.target.value=rule[field];toast('Nhập số nguyên dương hợp lệ',true);return;}rule[field]=n;changed();
      };
      mountSearchDropdown(row.querySelector('.goal-reward'),rewards,{
        getValue:rewardValue,getLabel:rewardLabel,getImage:iconUrl,
        onSelect:reward=>{
          rule.reward=rewardValue(reward);
          const preview=row.querySelector('.goal-selected-image');
          preview.src=iconUrl(reward);preview.alt=reward.vietnamese_name||reward.target;
          changed();
        },
      });
      row.querySelector('.delete-goal').onclick=()=>{group.rules=group.rules.filter(r=>r!==rule);initMilestones();changed();};
      rows.append(row);
    }
    section.querySelector('.add-goal').onclick=()=>{group.rules.push({...defaults(kind).rules[0],id:kind+'-'+crypto.randomUUID()});initMilestones();changed();};
    return section;
  }
  window.initMilestones=()=>{
    state.bridge.milestones ||= {};
    for(const kind of Object.keys(labels))state.bridge.milestones[kind] ||= defaults(kind);
    document.querySelector('#milestoneEditors').replaceChildren(...Object.keys(labels).filter(k=>k!=='coins').map(editor));
    document.querySelector('#coinMilestoneEditor').replaceChildren(editor('coins'));
    if(!initialized){initialized=true;poll();}
  };
  window.renderMilestonePanels=()=>{
    if(!state?.bridge.milestones)return;
    const markup=kind=>{
      const group=state.bridge.milestones[kind];
      if(!group.enabled)return '';
      const signature=window.milestoneSignature(group);
      const snapshotMatches=signature===window.milestoneSignature(progress.groups?.[kind]);
      return `<div class="milestone-group" data-event-kind="${kind}"><div class="goal-heading"><strong>${labels[kind]} · ${group.remember?'nhiều phiên LIVE':'phiên LIVE này'}</strong><small>${group.enabled?'Thưởng cộng thêm':'Mốc tổng đã tắt'}</small></div>${group.rules.map(rule=>{
        const reward=eventReward(rule.reward), live=snapshotMatches?progress.groups[kind].rules.find(r=>r.id===rule.id):null;
        const current=group.enabled?(live?.current||0):0;
        return `<div class="goal-display" data-goal-kind="${kind}" data-goal-id="${escapeHtml(rule.id)}" data-goal-config="${escapeHtml(signature)}"><div class="goal-reward-line"><img src="${escapeHtml(kind === "coins" ? iconUrl(reward) : eventMobImage(kind,reward))}" alt=""><span>Đủ ${rule.threshold.toLocaleString('vi-VN')} → <strong>${escapeHtml(reward.vietnamese_name||reward.target)} ×${rule.amount}</strong></span></div><div class="gel-field"><progress class="gel-progress" max="${rule.threshold}" value="${current}" aria-label="${labels[kind]}"></progress><span class="gel-label">${current.toLocaleString('vi-VN')} / ${rule.threshold.toLocaleString('vi-VN')}</span></div><small class="goal-rounds">${live?`Đã đạt ${live.completed||0} lần`:'Đã bật · chờ bridge cập nhật'}</small></div>`;
      }).join('')||'<small>Chưa thêm mốc</small>'}</div>`;
    };
    document.querySelector('#interactionGoals').innerHTML=Object.keys(labels).filter(k=>k!=='coins').map(markup).join('');
    document.querySelector('#coinGoals').innerHTML=markup('coins');
  };
  async function poll(){
    try{
      const response=await fetch('/api/milestones',{cache:'no-store'});
      if(!response.ok)throw new Error('progress unavailable');
      const next=await response.json();progress=next;window.updateMilestoneProgress?.(next);
    }
    catch{ /* Retain the last progress while reconnecting. */ }
    finally{setTimeout(poll,500);}
  }
})();
