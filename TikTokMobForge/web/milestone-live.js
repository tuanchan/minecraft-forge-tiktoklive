(() => {
  const animations=new WeakMap();
  window.milestoneSignature=group=>JSON.stringify([group?.enabled,
    (group?.rules||[]).map(rule=>[rule.id,rule.threshold,rule.reward,rule.amount])]);
  window.updateMilestoneProgress=data=>{
    for(const node of document.querySelectorAll('[data-goal-id]')){
      const group=data.groups?.[node.dataset.goalKind];
      const rule=group?.rules?.find(r=>r.id===node.dataset.goalId);
      const bar=node.querySelector('progress');
      if(!bar)continue;
      if(!rule || window.milestoneSignature(group)!==node.dataset.goalConfig){
        const previous=animations.get(bar);
        if(previous)cancelAnimationFrame(previous.frame);
        animations.delete(bar);
        bar.value=0;
        node.querySelector('.gel-label').textContent=`0 / ${Number(bar.max).toLocaleString('vi-VN')}`;
        node.querySelector('.goal-rounds').textContent='Đã bật · chờ bridge cập nhật';
        continue;
      }
      const target=group.enabled?rule.current:0;
      const label=node.querySelector('.gel-label'), rounds=node.querySelector('.goal-rounds');
      const crossed=group.enabled && rule.completed > Number(rounds.textContent.match(/\d+/)?.[0] || 0);
      const text=`${target.toLocaleString('vi-VN')} / ${rule.threshold.toLocaleString('vi-VN')}`;
      if(label.textContent!==text)label.textContent=text;
      const roundText=`Đã đạt ${rule.completed} lần`;
      if(rounds.textContent!==roundText)rounds.textContent=roundText;
      const previous=animations.get(bar);
      if(previous?.target===target && !crossed)continue;
      if(previous)cancelAnimationFrame(previous.frame);
      const start=performance.now(),from=Number(bar.value),animation={target,frame:0};animations.set(bar,animation);
      const frame=now=>{
        const elapsed=now-start;
        if(crossed && elapsed<450){bar.value=from+(bar.max-from)*Math.min(1,elapsed/220);animation.frame=requestAnimationFrame(frame);return;}
        const t=Math.min(1,(elapsed-(crossed?450:0))/420),initial=crossed?0:from;
        bar.value=initial+(target-initial)*(1-Math.pow(1-t,3));
        if(t<1)animation.frame=requestAnimationFrame(frame);
      };
      animation.frame=requestAnimationFrame(frame);
    }
  };
  if(location.pathname.endsWith('/live-panel.html')){
    const poll=async()=>{try{const response=await fetch('/api/milestones',{cache:'no-store'});if(response.ok)window.updateMilestoneProgress(await response.json());}catch{}finally{setTimeout(poll,500);}};
    poll();
  }
})();
