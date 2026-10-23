'use strict';
let simpleConfig=null, simpleConfigError='', simpleRestoring=false, switching=false, telemetry=null, telemetryError='', pollBusy=false;
const pendingProgress=new Set();
const S=id=>document.getElementById(id);
const stages={'archive-admission':'备份前置检查','source-capture':'采集业务数据并恢复源服务','capture-validation':'核验采集材料','nas-upload':'上传 NAS','archive-metadata':'生成归档索引','nas-readback':'NAS 独立读回','archive-final-verification':'归档最终核验','archive-chain-readback':'核对已发布备份链','capture-cleanup':'清理采集临时文件','restore-admission':'恢复前置检查','target-checks':'恢复目标核验','target-replacement':'清空已确认覆盖的小程序目标','database-restore':'恢复数据库','object-restore':'恢复对象文件','consistency':'一致性核验','redis-rebuild':'恢复 Redis（保留原到期时间）','application-start':'启动应用','archive-verification':'归档最终核验','restore-cleanup':'清理恢复临时文件','sql-readback':'数据库独立回读核验'};
function stageName(name){const parts=name.split('/');const stage=parts.at(-1);const sql={'sql-stage':'暂存数据库备份','sql-expand':'解压数据库备份','sql-import':'导入数据库','restore-cleanup':'清理恢复临时文件','target-quiesce':'停止目标应用写入','capture-material-binding':'绑定采集材料','recovery-material-binding':'生成恢复材料'};return (parts[0].startsWith('database-')?`第 ${Number(parts[0].split('-')[1])+1} 个备份点 · `:'')+(sql[stage]||stages[stage]||stage);}
const duration=seconds=>{if(!Number.isFinite(seconds))return '—';if(seconds>=0&&seconds<1)return `${seconds.toFixed(3)}秒`;seconds=Math.max(0,Math.floor(seconds));return `${Math.floor(seconds/3600)}时 ${Math.floor(seconds%3600/60)}分 ${seconds%60}秒`;};
const date=value=>value?new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'—';
const currentBinding=()=>simpleConfig?.bindings.find(b=>b.selectable&&b.product===S('simple-product').value&&b.server===S('simple-server').value&&b.mode===S('simple-mode').value);
function latestSimpleParent(){
  const app=selected(), refs=app?.validated?.parentChainRefs||[];
  if(refs.length===1)return refs[0];
  const candidates=records.filter(r=>r.applicationId===app?.applicationId&&r.request.sourceConfigRef===app.sourceConfigRef&&
    ['FULL','INCREMENTAL'].includes(r.request.action)&&refs.includes(r.request.operationId));
  if(new Set(candidates.map(r=>r.request.operationId)).size!==refs.length)return '';
  candidates.sort((a,b)=>Date.parse(b.createdAt)-Date.parse(a.createdAt));
  if(!candidates.length||candidates.some(r=>!Number.isFinite(Date.parse(r.createdAt)))||
    candidates.length>1&&Date.parse(candidates[0].createdAt)===Date.parse(candidates[1].createdAt))return '';
  return candidates[0].request.operationId;
}
function simpleFreshTargets(){
  const binding=currentBinding();
  if(S('simple-restore-mode').value==='replace'){
    const registered=Object.values(simpleTargetServers(binding));
    return (selected()?.validated?.freshTargetConfigRefs||[]).filter(ref=>registered.includes(ref));
  }
  const used=new Set(records.filter(r=>r.request.action==='RESTORE'&&r.spugHistoryId&&!r.cancelledUnaccepted).map(r=>r.request.targetConfigRef));
  return (selected()?.validated?.freshTargetConfigRefs||[]).filter(ref=>!used.has(ref));
}
function simpleTargetServers(binding=currentBinding()){
  return binding?(S('simple-restore-mode').value==='replace'?binding.overwriteTargetServers:binding.targetServers):{};
}
function replacementRequest(request,binding){
  return request.action==='RESTORE'&&!!binding&&Object.values(binding.overwriteTargetServers).includes(request.targetConfigRef);
}
function simpleRequest(id){
  const binding=currentBinding(), app=selected(), chosenAction=simpleRestoring?'RESTORE':S('simple-type').value;
  if(!binding || app?.applicationId!==binding.applicationId)throw new Error('SOURCE_NOT_REGISTERED_BY_W08');
  return {schemaVersion:'SmallAppBackupUiRequest/v1',operationId:id,action:chosenAction,sourceConfigRef:app.sourceConfigRef,
    parentChainRef:chosenAction==='INCREMENTAL'?S('parent').value:null,
    recoveryPointRef:chosenAction==='RESTORE'?S('simple-package').value:null,
    targetConfigRef:chosenAction==='RESTORE'?simpleTargetServers(binding)[S('simple-target').value]:null};
}
function syncSimpleIdentity(record){
  const matched=simpleConfig?.bindings.find(b=>b.applicationId===record.applicationId);
  if(matched){S('simple-product').value=matched.product;S('simple-server').value=matched.server;S('simple-mode').value=matched.mode;}
  action=record.request.action;simpleRestoring=action==='RESTORE';
  if(simpleRestoring)S('simple-restore-mode').value=replacementRequest(record.request,matched)?'replace':'fresh';
  if(!simpleRestoring)S('simple-type').value=action;
}
function drawOperationDetails(){
  const details=S('simple-operation-details');details.replaceChildren();details.hidden=!active;
  if(!active)return;
  const request=active.request, binding=simpleConfig?.bindings.find(b=>b.applicationId===active.applicationId);
  const fields=[['操作',labels[request.action]],['来源服务器',binding?.server||'来源服务器未登记'],
    ['来源',request.sourceConfigRef],['执行模式',binding?.mode==='fast'?'快速模式 · 跳过核验':binding?.mode==='safe'?'安全模式 · 完整核验':'执行模式未登记']];
  if(request.parentChainRef)fields.push(['增量父点',request.parentChainRef]);
  if(request.recoveryPointRef)fields.push(['备份包',request.recoveryPointRef]);
  if(request.targetConfigRef)fields.push(['恢复目标',request.targetConfigRef]);
  if(request.action==='RESTORE')fields.push(['恢复方式',replacementRequest(request,binding)?'覆盖现有小程序':'恢复到空目标']);
  for(const [label,value] of fields){const term=document.createElement('dt'),description=document.createElement('dd');term.textContent=label;description.textContent=value;details.append(term,description);}
}
async function openRecord(record){
  if(interactionLocked() || switching)return;
  syncSimpleIdentity(record);selectRecord(record);
  S('application').value=record.applicationId;telemetry=null;telemetryError='';render();await query();await progress();
}
function simpleRender(){
  const binding=currentBinding(), restore=simpleRestoring, targetServers=simpleTargetServers(binding), replacing=S('simple-restore-mode').value==='replace';
  S('replace-note').hidden=!restore||!replacing;
  const fast=S('simple-mode').value==='fast';
  for(const option of S('simple-mode').children){
    option.disabled=!simpleConfig?.bindings.some(b=>b.selectable&&b.product===S('simple-product').value&&b.server===S('simple-server').value&&b.mode===option.value);
    option.textContent=(option.value==='safe'?'安全模式 · 完整核验':'快速模式 · 跳过核验')+(simpleConfig&&option.disabled?'（未登记）':'');
  }
  S('mode-note').textContent=fast?'快速模式跳过内容、一致性及环境核验，不保证恢复准确，也不保证不停服务。':'执行完整内容和一致性核验；备份期间可能停写。';
  S('simple-type-field').hidden=restore;S('simple-package-field').hidden=!restore;
  for(const [id,on] of [['simple-backup-tab',!restore],['simple-restore-tab',restore]])S(id).setAttribute('aria-selected',String(on));
  const refs=binding&&selected()?.applicationId===binding.applicationId?selected()?.validated?.recoveryPointRefs||[]:[];
  const previous=S('simple-package').value;S('simple-package').replaceChildren(new Option('请选择可用备份包',''));
  for(const ref of refs){const record=records.find(r=>r.request.operationId===ref);const label=record?`${date(record.createdAt)} · ${labels[record.request.action]} · ${ref}`:ref;S('simple-package').add(new Option(label,ref));}
  if(refs.includes(previous))S('simple-package').value=previous;
  const fresh=binding&&selected()?.applicationId===binding.applicationId?simpleFreshTargets():[];
  const priorTarget=S('simple-target').value;
  S('simple-target').replaceChildren(new Option('请选择可用恢复服务器',''));
  for(const server of simpleConfig?.servers||[]){
    const registered=targetServers[server.address], available=registered&&fresh.includes(registered);
    const option=new Option(`${server.name}　${server.address}${available?'':registered?'（目标当前不可用）':'（未登记目标）'}`,server.address);
    option.disabled=!available;S('simple-target').add(option);
  }
  if(targetServers[priorTarget]&&fresh.includes(targetServers[priorTarget]))S('simple-target').value=priorTarget;
  let blocked='';
  if(!simpleConfig)blocked=simpleConfigError||'配置未读取，不能执行。';
  else if(!binding){
    const available=simpleConfig.bindings.filter(b=>b.selectable&&b.product===S('simple-product').value&&b.server===S('simple-server').value);
    const modes=available.map(b=>b.mode==='safe'?'安全模式':'快速模式');
    blocked=`该服务器尚未登记${fast?'快速':'安全'}模式执行器。`+(modes.length?'请手动选择'+modes.join('或')+'。':'');
  }
  else if(S('simple-nas').value.trim()!==simpleConfig.nas)blocked='该 NAS 路径尚未绑定执行器，不能提交到其他目录。';
  else if(switching||selected()?.applicationId!==binding.applicationId)blocked='正在核对服务器配置…';
  else if(!selected()?.validated)blocked=message(selected()?.readinessError||'SOURCE_NOT_VERIFIED_BY_W01');
  else if(restore&&!S('simple-package').value)blocked='请选择备份包。';
  else if(restore&&!S('simple-target').value)blocked=Object.values(targetServers).some(ref=>fresh.includes(ref))?'请选择可用恢复服务器。':replacing?'所选来源尚无可用的覆盖恢复目标。':'所选来源当前没有可用的空恢复目标。';
  else if(restore&&!targetServers[S('simple-target').value])blocked='该恢复服务器尚无已登记的恢复目标。';
  else if(restore&&!fresh.includes(targetServers[S('simple-target').value]))blocked='该恢复目标当前不可用，请刷新配置后重新选择。';
  else if(!restore&&action==='INCREMENTAL'&&!S('parent').value&&(selected()?.validated?.parentChainRefs||[]).length)blocked='无法确定最近的有效备份链，请刷新配置核对操作记录。';
  else if(S('submit').disabled)blocked=S('blocked-reason').textContent||'当前不可提交。';
  S('simple-status').textContent=blocked||(restore?replacing?'将覆盖所选目标现有小程序的记录、附件及 Redis 数据。':'将按所选备份链恢复到登记的独立目标。':action==='INCREMENTAL'?'已自动关联该来源最近一条可用备份链。':'已连接 Spug 执行器。');
  S('simple-status').dataset.state=blocked?'blocked':'ready';
  S('simple-submit').disabled=!!blocked||interactionLocked();S('simple-submit').textContent=restore?'开始恢复 →':'开始备份 →';
  S('simple-submit').title=blocked;
  if(blocked)S('submit').disabled=true;
  S('simple-result').textContent=S('result-state').textContent;
  if(fast&&active?.result?.state==='SUCCEEDED')S('simple-result').textContent=active.request.action==='RESTORE'?'恢复命令已完成；快速模式未执行完整核验，业务验收待确认。':'备份命令已完成；快速模式未执行完整核验。';
  S('operation-reference').textContent=active?.request.operationId||'';
  drawOperationDetails();
  const draftLocked=interactionLocked()||switching||!!unresolvedOriginal()||!!active&&!resolvedRecord(active);
  for(const id of ['simple-product','simple-server','simple-mode','simple-type','simple-package','simple-target','simple-restore-mode','simple-nas','simple-backup-tab','simple-restore-tab','simple-refresh'])S(id).disabled=draftLocked;
  S('simple-query').disabled=interactionLocked()||!active;
  S('simple-history').replaceChildren();
  const visibleRecords=records.filter(record=>simpleConfig?.bindings.some(b=>b.product===S('simple-product').value&&b.applicationId===record.applicationId));
  for(const record of visibleRecords){
    const row=document.createElement('div');row.className='history-row';
    const label=document.createElement('small');label.textContent=`${date(record.createdAt)} · ${labels[record.request.action]} · ${record.request.operationId}`;
    const button=document.createElement('button');button.textContent='查看进度';button.disabled=interactionLocked()||switching;
    button.onclick=()=>openRecord(record);row.append(label,button);S('simple-history').append(row);
  }
  if(!visibleRecords.length)S('simple-history').textContent='暂无操作记录。';
  drawProgress();
}
function drawProgress(){
  if(!active || telemetry && telemetry.operationId!==active.request.operationId){telemetry=null;telemetryError='';}
  if(active?.cancelledUnaccepted){
    telemetry=null;telemetryError='';S('total-time').textContent='—';
    S('steps').replaceChildren();S('steps').textContent='原请求未受理，未执行任何步骤。';
    S('simple-logs').textContent='原编号已确认未受理并封存，未执行。';return;
  }
  const start=telemetry?.startedAt||active?.createdAt;
  const end=telemetry?.finishedAt;
  // A terminal record without a finish timestamp must not keep accumulating time.
  const terminal=['SUCCEEDED','FAILED'].includes(active?.result?.state)||['SUCCEEDED','FAILED','FAILED_RETAINED','TERMINAL_UNKNOWN'].includes(telemetry?.state);
  S('total-time').textContent=start&&(!terminal||end)?duration(((end?Date.parse(end):Date.now())-Date.parse(start))/1000):'—';
  S('steps').replaceChildren();
  for(const step of telemetry?.steps||[]){
    const row=document.createElement('div');row.className='step';const name=document.createElement('span');name.textContent=stageName(step.name);
    const state=document.createElement('strong');state.textContent={SUCCEEDED:'已完成',FAILED:'失败',RUNNING:'执行中',UNCONFIRMED:'结束回执缺失，状态未确认'}[step.state]||'状态未确认';
    const info=document.createElement('small');const seconds=step.elapsedSeconds??(step.finishedAt?(Date.parse(step.finishedAt)-Date.parse(step.startedAt))/1000:step.state==='RUNNING'&&!terminal?(Date.now()-Date.parse(step.startedAt))/1000:null);
    info.textContent=`开始 ${date(step.startedAt)}　结束 ${date(step.finishedAt)}　耗时 ${duration(seconds)}`;row.append(name,state,info);S('steps').append(row);
  }
  if(!telemetry?.steps?.length)S('steps').textContent=telemetryError||'尚无步骤时间回执。';
  const logEvents=(telemetry?.events||[]).map(e=>({at:e.at,text:e.stage}));
  for(const step of telemetry?.steps||[]){logEvents.push({at:step.startedAt,text:stageName(step.name)+'：开始'});if(step.finishedAt)logEvents.push({at:step.finishedAt,text:stageName(step.name)+(step.state==='SUCCEEDED'?'：已完成':'：失败')+'，耗时 '+duration(step.elapsedSeconds)});}
  logEvents.sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
  const lines=logEvents.map(e=>`${date(e.at)}  ${e.text}`);
  const operationBinding=simpleConfig?.bindings.find(b=>b.applicationId===active?.applicationId);
  if(operationBinding?.mode==='fast')lines.unshift('快速模式：跳过内容、数据一致性和环境核验；步骤完成仅表示对应命令完成。');
  if(telemetry?.finishedAt)lines.push(`${date(telemetry.finishedAt)}  原始执行结果：${telemetry.state}`);
  if(active?.result?.errorCode){
    const code=active.result.errorCode;
    const reserved=active.result.state==='RUNNING'&&['SPUG_DISPATCH_RESERVED','ORIGINAL_OWNER_RESULT_NOT_READY'].includes(code);
    lines.push((reserved?'状态：':'错误：')+message(code));
  }
  for(const step of telemetry?.steps||[])if(step.state==='UNCONFIRMED')lines.push(`${stageName(step.name)}：操作已有终态，步骤结束回执缺失，状态未确认。`);
  if(telemetryError)lines.push(telemetryError+'；已有数据为上次读取结果。');
  S('simple-logs').textContent=lines.length?lines.join('\n'):telemetryError||'暂无日志。';
}
async function progress(){
  if(!active||active.cancelledUnaccepted||pendingProgress.has(viewGeneration))return;
  const operation=active.request.operationId, generation=viewGeneration;
  pendingProgress.add(generation);pollBusy=true;
  try{const value=await api('/progress/'+encodeURIComponent(operation));
    if(generation!==viewGeneration || active?.request.operationId!==operation)return;
    if(value.operationId!==operation)throw new Error('STEP_TELEMETRY_OPERATION_MISMATCH');
    telemetry=value;telemetryError='';}
  catch(error){if(generation===viewGeneration && active?.request.operationId===operation)telemetryError='步骤日志读取失败：'+error.message;}
  finally{pendingProgress.delete(generation);pollBusy=pendingProgress.size>0;drawProgress();}
}
async function chooseSimple(){
  if(interactionLocked() || switching)return;
  const binding=currentBinding();
  if(unresolvedOriginal() || active&&!resolvedRecord(active)){simpleRender();return;}
  selectRecord(null);telemetry=null;telemetryError='';
  S('simple-package').value='';S('point').value='';S('parent').value='';S('target').value='';S('result-state').textContent='尚未执行';
  if(!binding){render();return;}
  action=simpleRestoring?'RESTORE':S('simple-type').value;S('application').value=binding.applicationId;chooseId();
  // Explicit user change starts a new draft; historical operations remain in the history.
  selectRecord(null);operationId='smallapp-'+crypto.randomUUID().replace(/-/g,'');switching=true;render();
  try{await refresh(binding.applicationId);
    if(action==='INCREMENTAL')S('parent').value=latestSimpleParent();
    if(action==='RESTORE'){S('point').value=S('simple-package').value;S('target').value=simpleTargetServers(binding)[S('simple-target').value]||'';}
  }finally{switching=false;render();}
}
async function refreshSimpleConfiguration(){
  if(interactionLocked()||switching||unresolvedOriginal()||active&&!resolvedRecord(active))return;
  switching=true;render();
  try{simpleConfig=await api('/simple-config');simpleConfigError='';S('simple-nas').value=simpleConfig.nas;}
  catch(error){simpleConfig=null;simpleConfigError='配置读取失败：'+message(error.message);problem(simpleConfigError);}
  finally{switching=false;render();}
  if(simpleConfig)await chooseSimple();
}
const originalRender=render;render=function(){originalRender();simpleRender();};
S('simple-backup-tab').onclick=()=>{if(S('simple-backup-tab').disabled)return;simpleRestoring=false;chooseSimple();};
S('simple-restore-tab').onclick=()=>{if(S('simple-restore-tab').disabled)return;simpleRestoring=true;chooseSimple();};
for(const id of ['simple-server','simple-mode','simple-type','simple-restore-mode'])S(id).onchange=chooseSimple;
S('simple-product').onchange=()=>{
  const binding=simpleConfig?.bindings.find(b=>b.selectable&&b.product===S('simple-product').value);
  if(binding){S('simple-server').value=binding.server;S('simple-mode').value=binding.mode;}
  chooseSimple();
};
S('simple-nas').oninput=()=>render();
for(const id of ['simple-package','simple-target'])S(id).onchange=()=>{S('point').value=S('simple-package').value;S('target').value=simpleTargetServers()[S('simple-target').value]||'';render();};
S('simple-refresh').onclick=refreshSimpleConfiguration;
S('simple-query').onclick=async()=>{await query();await progress();render();};
S('simple-submit').onclick=()=>{
  if(S('simple-submit').disabled)return;
  const request=Object.freeze(simpleRequest(operationId));
  confirmation=Object.freeze({request,applicationId:selected().applicationId});
  const replacing=replacementRequest(request,currentBinding());
  S('replace-confirm-field').hidden=!replacing;S('replace-confirm').checked=false;S('simple-confirm-submit').disabled=replacing;
  S('confirm-summary').textContent=`${S('simple-product').selectedOptions[0].textContent} · ${labels[request.action]} · ${S('simple-server').selectedOptions[0].textContent} · ${S('simple-mode').selectedOptions[0].textContent}\nNAS：${S('simple-nas').value}\n来源：${request.sourceConfigRef}\n`+(request.action==='RESTORE'?`备份包：${request.recoveryPointRef}\n恢复到：${S('simple-target').selectedOptions[0].textContent}\n独立目标：${request.targetConfigRef}`:`备份类型：${labels[request.action]}${request.action==='INCREMENTAL'?'\n父链：'+request.parentChainRef:''}`);
  if(replacing)S('confirm-summary').textContent+='\n恢复方式：覆盖现有小程序，将替换目标现有记录、附件及 Redis 数据。';
  render();
  S('simple-confirm').showModal();
};
function cancelConfirmation(){confirmation=null;S('simple-confirm').close();render();}
S('simple-cancel').onclick=cancelConfirmation;
S('simple-confirm').oncancel=event=>{event.preventDefault();cancelConfirmation();};
S('replace-confirm').onchange=()=>{S('simple-confirm-submit').disabled=!S('replace-confirm').checked;};
S('simple-confirm-submit').onclick=async()=>{
  const snapshot=confirmation;if(!snapshot)return;
  if(replacementRequest(snapshot.request,currentBinding())&&!S('replace-confirm').checked)return;
  confirmation=null;S('simple-confirm').close();render();
  if(S('simple-submit').disabled || snapshot.applicationId!==selected()?.applicationId || !sameRequest(snapshot.request,simpleRequest(operationId))){problem('操作参数已变化，请重新确认。');return;}
  await submitOriginal(snapshot.request,snapshot.applicationId);await progress();render();
};
setInterval(()=>{if(!document.hidden&&active?.result?.state==='RUNNING'&&!interactionLocked()&&!pollBusy){query().then(progress);}drawProgress();},5000);
(async()=>{
  try{await initialRefresh;simpleConfig=await api('/simple-config');S('simple-nas').value=simpleConfig.nas;
    if(active&&!pending){active=null;operationId='';}
    const matched=simpleConfig.bindings.find(b=>b.applicationId===active?.applicationId);
    if(matched){S('simple-product').value=matched.product;S('simple-server').value=matched.server;S('simple-mode').value=matched.mode;simpleRestoring=action==='RESTORE';if(!simpleRestoring)S('simple-type').value=action;render();await progress();}
    else {const first=simpleConfig.bindings.find(b=>b.selectable);if(!currentBinding()&&first){S('simple-server').value=first.server;S('simple-mode').value=first.mode;}await chooseSimple();}
  }catch(error){S('simple-status').textContent='配置读取失败：'+error.message;}
})();
