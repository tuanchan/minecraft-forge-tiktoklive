(() => {
  let config, base, timer, saving = false, dirty = false;
  const $ = id => document.getElementById(id), esc = value => escapeHtml(String(value));
  const status = (text, error=false) => { $('missionSaveStatus').textContent=text; $('missionSaveStatus').style.color=error?'#df6060':''; };
  window.missionChoices = () => config?.rules || [];
  async function load() {
    try {
      const data=await api('/api/missions');
      config=data.config; base=structuredClone(config); dirty=false;
      render(); progress(data); status('Đã tải');
      if(typeof mappings!=='undefined' && mappings.some(r=>r.target==='mission_penalty'))renderMappings();
    } catch(error) { status(error.message,true); }
  }
  function changed() { dirty=true;status('Đang chờ lưu…');clearTimeout(timer);timer=setTimeout(save,450); }
  async function save() {
    if(saving || !dirty)return;
    saving=true; dirty=false; const outgoing=structuredClone(config);
    try {
      const response=await api('/api/missions',{method:'POST',body:JSON.stringify({config:outgoing,base})});
      base=response.config;status(dirty?'Đang chờ lưu…':'Đã lưu');
    } catch(error) { status(error.message,true); }
    finally {saving=false;if(dirty)timer=setTimeout(save,100);}
  }
  function add(kind) {
    if(!config)return;
    if(config.rules.length>=32){status('Tối đa 32 nhiệm vụ',true);return;}
    config.rules.push({id:crypto.randomUUID(),title:kind==='diamond'?'Đào kim cương':'Giết mob',kind,mob:'*',
      enabled:true,summoned_only:false,target:kind==='diamond'?100:50,milestones:10,death_penalty:0,death_mode:'points',mode:'2d',
      x:50,y:Math.min(90,10+config.rules.length*15),scale:1,reset:0});
    config.enabled=true;render();changed();
  }
  const number=(field,label,value,min,max,step=1)=>`<label>${label}<input data-field="${field}" type="number" value="${value}" min="${min}" max="${max}" step="${step}"></label>`;
  function render() {
    $('missionsEnabled').checked=config.enabled;
    $('missionEditors').replaceChildren(...config.rules.map(rule=>{
      const node=document.createElement('article');node.className='panel mission-editor';node.dataset.missionId=rule.id;
      node.innerHTML=`<div class="mission-head"><label><input data-field="enabled" type="checkbox" ${rule.enabled?'checked':''}> Bật nhiệm vụ</label><button class="mission-remove danger" type="button">Xóa</button></div>
        <div class="form-grid"><label>Tên nhiệm vụ<input data-field="title" maxlength="64" value="${esc(rule.title)}"></label>
        ${number('target','Mục tiêu',rule.target,1,2147483647)}
        ${number('milestones','Số mốc chia đều',rule.milestones,1,100)}
        ${rule.kind==='kill'?`<label>Mob cần giết (* = tổng mọi loại)<input data-field="mob" list="missionMobList" value="${esc(rule.mob)}" placeholder="* = tất cả"></label><label class="mission-check"><input data-field="summoned_only" type="checkbox" ${rule.summoned_only?'checked':''}> Chỉ mob do mod triệu hồi</label>`:'<p>Đếm khối quặng kim cương đào thành công, không nhân theo Gia tài.</p>'}
        <label>Trừ khi chết theo<select data-field="death_mode"><option value="points">Số điểm</option><option value="percent">% tiến độ hiện có (làm tròn lên)</option></select></label>
        ${number('death_penalty','Mức trừ khi chết (0 = không trừ)',rule.death_penalty,0,rule.death_mode==='percent'?100:2147483647)}
        <label>Hiển thị<select data-field="mode"><option value="2d">2D · trên màn hình</option><option value="3d">3D · bảng trong thế giới</option></select></label>
        ${number('x','Vị trí ngang 2D (%)',rule.x,0,100,.1)}${number('y','Vị trí dọc 2D (%)',rule.y,0,100,.1)}${number('scale','Kích thước 2D',rule.scale,.25,3,.05)}</div>
        <div class="mission-stage" aria-label="Kéo thanh nhiệm vụ để chỉnh vị trí 2D"><div class="mission-preview">${missionCard(rule,Math.round(rule.target*.4),true)}</div></div>
        <p class="mission-help"></p><div class="actions"><button class="mission-reset" type="button">Đặt lại tiến độ về 0</button><small>Mã: ${esc(rule.id)}</small></div>`;
      node.querySelector('[data-field=death_mode]').value=rule.death_mode;
      node.querySelector('[data-field=mode]').value=rule.mode;
      const stage=node.querySelector('.mission-stage'),preview=node.querySelector('.mission-preview');
      function position() {
        stage.hidden=rule.mode!=='2d';
        preview.style.width=`${Math.min(95,40*rule.scale)}%`;
        preview.style.left=`${rule.x}%`;preview.style.top=`${rule.y}%`;preview.style.transform=`translate(-${rule.x}%,-${rule.y}%)`;
        node.querySelector('.mission-help').textContent=rule.mode==='3d'?'Trong game: nhìn vào bảng, giữ G để kéo; G + cuộn để đổi cỡ; G + Shift + cuộn đổi khoảng cách; F ghim/bỏ ghim. X ẩn bảng đến lần bật lại nhiệm vụ hoặc vào lại world.':'Kéo thanh trong khung 16:9 hoặc nhập X/Y. Kích thước tự giới hạn theo màn hình.';
      }
      position();
      for(const input of node.querySelectorAll('[data-field]'))input.addEventListener('change',()=>{
        const field=input.dataset.field;
        if(!input.checkValidity() || input.type==='number' && input.value===''){input.reportValidity();return;}
        let value=input.type==='checkbox'?input.checked:input.type==='number'?Number(input.value):input.value.trim();
        if(field==='title'&&!value){input.value=rule.title;return;}
        if(field==='mob'&&value!=='*'&&!value.includes(':'))value='minecraft:'+value;
        rule[field]=value;
        if(field==='death_mode'){rule.death_penalty=Math.min(rule.death_penalty,value==='percent'?100:2147483647);render();}
        else {preview.innerHTML=missionCard(rule,Math.round(rule.target*.4),true);position();}
        changed();
      });
      let drag;
      preview.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,left:preview.offsetLeft-preview.offsetWidth*rule.x/100,top:preview.offsetTop-preview.offsetHeight*rule.y/100};preview.setPointerCapture(e.pointerId);e.preventDefault();};
      preview.onpointermove=e=>{
        if(!drag)return;
        rule.x=Math.round(Math.max(0,Math.min(100,(drag.left+e.clientX-drag.x)/Math.max(1,stage.clientWidth-preview.offsetWidth)*100))*10)/10;
        rule.y=Math.round(Math.max(0,Math.min(100,(drag.top+e.clientY-drag.y)/Math.max(1,stage.clientHeight-preview.offsetHeight)*100))*10)/10;
        for(const key of ['x','y'])node.querySelector(`[data-field=${key}]`).value=rule[key];position();
      };
      preview.onpointerup=preview.onpointercancel=()=>{if(drag){drag=null;changed();}};
      node.querySelector('.mission-remove').onclick=()=>{config.rules=config.rules.filter(r=>r!==rule);render();changed();};
      node.querySelector('.mission-reset').onclick=()=>{rule.reset++;changed();};
      return node;
    }));
    let list=$('missionMobList');if(!list){list=document.createElement('datalist');list.id='missionMobList';document.body.append(list);}
    list.innerHTML='<option value="*">Tất cả mob</option>'+(state?.catalog?.mobs||[]).map(m=>`<option value="${esc(m.target.includes(':')?m.target:'minecraft:'+m.target)}">${esc(m.vietnamese_name)}</option>`).join('');
  }
  function missionCard(rule,current,preview=false) {
    const safe=Math.max(0,current), percent=Math.max(0,Math.min(100,Math.round(100*safe/rule.target)));
    const milestones=Math.max(1,Number(rule.milestones)||1);
    const kill=rule.kind==='kill';
    return `<div class="mission-card ${kill?'mission-kill':'mission-diamond'}" style="--mission-progress:${percent}%;--mission-steps:${milestones}">
      <img class="mission-icon mission-icon-left" src="/assets/${kill?'iconkiemkc.png':'Cu%E1%BB%91c%20chim%20kim%20c%C6%B0%C6%A1ng%20ph%C3%A1t%20s%C3%A1ng%20pixel%20art.png'}" alt="">
      <div class="mission-card-body"><strong>${esc(rule.title)}</strong><div class="mission-bar"><i></i><b></b><span>${percent}% · ${current} / ${rule.target}</span></div></div>
      <img class="mission-icon mission-icon-right" src="/assets/${kill?'zombieprogess.png':'quangkc.png'}" alt="">
      ${kill?'':`<img class="mission-diamond-gem" src="/assets/iconkc.png" alt="">`}
    </div>`;
  }
  function progress(data) {
    $('missionOnline').textContent=data.online?'Đang nhận tiến độ từ Minecraft':'Minecraft chưa gửi tiến độ · vào world để bắt đầu';
    $('missionProgress').innerHTML=(data.progress.players||[]).map(player=>`<div class="mission-player"><h4>${esc(player.name)}</h4>${(player.rules||[]).map(r=>missionCard(r,r.current)).join('')}</div>`).join('');
  }
  async function poll(){try{const data=await api('/api/missions');progress(data);}catch{}finally{setTimeout(poll,1000);}}
  $('missionDiamond').onclick=()=>add('diamond');$('missionKill').onclick=()=>add('kill');
  $('missionReload').onclick=load;$('missionsEnabled').onchange=e=>{if(config){config.enabled=e.target.checked;changed();}};
  $('missionGifts').onclick=()=>showTab('gifts');
  const ready=setInterval(()=>{if(typeof state!=='undefined'&&state?.catalog){clearInterval(ready);load();poll();}},100);
})();
