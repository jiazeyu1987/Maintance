'use strict';
let simpleConfig=null, simpleConfigError='', simpleRestoring=false, switching=false, telemetry=null, telemetryError='', pollBusy=false;
let simpleInitializing=false;
const pendingProgress=new Set();
const applicationDraftSelections=new Map();
const S=id=>document.getElementById(id);
const simplePages={backup:'simple-form-panel',restore:'simple-form-panel',catalog:'package-catalog',progress:'simple-progress-panel',history:'simple-history-panel'};
const simpleAnchors={backup:'backup',restore:'restore',catalog:'package-catalog',progress:'execution-progress',history:'operation-history'};
let simplePage='backup';
let catalogRestore=null;
function renderSimpleNavigation(){
  for(const name of Object.keys(simplePages)){
    const tab=S('simple-'+name+'-tab'),on=name===simplePage;
    tab.setAttribute('aria-selected',String(on));tab.setAttribute('tabindex',on?'0':'-1');
  }
  for(const panel of new Set(Object.values(simplePages)))S(panel).hidden=panel==='simple-form-panel'&&catalogRestore?false:panel!==simplePages[simplePage];
  S('simple-form-panel').setAttribute('role',catalogRestore?'group':'tabpanel');
  S('simple-form-panel').setAttribute('aria-labelledby',catalogRestore?'catalog-restore-title':simpleRestoring?'simple-restore-tab':'simple-backup-tab');
}
async function openCatalogRestore(row){
  const refuse=text=>{S('catalog-problem').textContent=text;S('catalog-problem').hidden=false;};
  if(!['backup-full','backup-incremental'].includes(row.kind)){refuse('发布包不能用于数据备份恢复，请使用对应发布流程。');return;}
  if(row.status && row.status!=='indexed'){refuse('包清单尚未通过读取核对，不能发起恢复。');return;}
  if(simpleInitializing||interactionLocked()||switching||unresolvedOriginal()||active&&!resolvedRecord(active)){
    refuse('当前操作尚未结束或配置仍在核对，请完成后再恢复。');return;
  }
  if(!simpleConfig){refuse('恢复配置尚未读取，请在恢复页刷新配置后重试。');return;}
  const pin=Object.freeze({packageId:row.packageId,version:row.version||'未记录',application:row.application});
  catalogRestore=pin;simpleRestoring=true;action='RESTORE';
  S('catalog-restore-package').textContent=`程序版本：${pin.version} · 备份包：${pin.packageId}`;
  S('simple-product').value=pin.application;
  const matches=simpleConfig.bindings.filter(b=>b.selectable&&b.product===pin.application&&b.mode==='safe'&&(row.servers||[]).includes(b.server));
  S('simple-server').value=matches.length===1?matches[0].server:'';
  S('simple-mode').value='safe';S('simple-restore-mode').value='replace';
  S('simple-nas').value=simpleConfig.nas;
  S('catalog-restore-form-host').appendChild(S('simple-form-panel'));
  S('catalog-restore-dialog').showModal();render();
  await chooseSimple();
  if(catalogRestore!==pin)return;
  render();S('simple-server').focus?.();
}
function closeCatalogRestore(focus=true){
  if(!catalogRestore)return;
  catalogRestore=null;
  S('simple-workspace').insertBefore(S('simple-form-panel'),S('package-catalog'));
  S('catalog-restore-dialog').close();render();
  if(focus)S('simple-catalog-tab').focus?.();
}
S('catalog-restore-close').onclick=()=>closeCatalogRestore();
S('catalog-restore-dialog').oncancel=event=>{event.preventDefault();closeCatalogRestore();};
function showSimplePage(name,focus=false){
  if(!Object.hasOwn(simplePages,name))throw new Error('Unknown page tab');
  simplePage=name;renderSimpleNavigation();
  if(typeof window!=='undefined'&&window.location.hash!=='#'+simpleAnchors[name])window.location.hash=simpleAnchors[name];
  if(focus)S('simple-'+name+'-tab').focus?.();
}
const stages={'archive-admission':'备份前置检查','source-capture':'采集业务数据并恢复源服务','capture-validation':'核验采集材料','nas-upload':'上传 NAS','archive-metadata':'生成归档索引','nas-readback':'NAS 独立读回','archive-final-verification':'归档最终核验','archive-chain-readback':'核对已发布备份链','capture-cleanup':'清理采集临时文件','restore-admission':'恢复前置检查','target-checks':'恢复目标核验','target-replacement':'清空已确认覆盖的程序目标','database-restore':'恢复数据库','object-restore':'恢复对象文件','consistency':'一致性核验','redis-rebuild':'恢复 Redis（保留原到期时间）','application-start':'启动应用','archive-verification':'归档最终核验','restore-cleanup':'清理恢复临时文件','sql-readback':'数据库独立回读核验'};
function stageName(name){const parts=name.split('/');const stage=parts.at(-1);const sql={'sql-stage':'暂存数据库备份','sql-expand':'解压数据库备份','sql-import':'导入数据库','restore-cleanup':'清理恢复临时文件','target-quiesce':'停止目标应用写入','capture-material-binding':'绑定采集材料','recovery-material-binding':'生成恢复材料'};return (parts[0].startsWith('database-')?`第 ${Number(parts[0].split('-')[1])+1} 个备份点 · `:'')+(sql[stage]||stages[stage]||stage);}
const duration=seconds=>{if(!Number.isFinite(seconds))return '—';if(seconds>=0&&seconds<1)return `${seconds.toFixed(3)}秒`;seconds=Math.max(0,Math.floor(seconds));return `${Math.floor(seconds/3600)}时 ${Math.floor(seconds%3600/60)}分 ${seconds%60}秒`;};
const date=value=>value?new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'—';
const currentBinding=()=>simpleConfig?.bindings.find(b=>b.selectable&&b.product===S('simple-product').value&&b.server===S('simple-server').value&&b.mode===S('simple-mode').value);
let incrementalPlan=null, incrementalPlanError='', incrementalPlanLoading=false, incrementalPlanGeneration=0;
const automaticIncrementalSelected=()=>!simpleRestoring&&S('simple-type').value==='INCREMENTAL';
function currentIncrementalPlan(){
  const app=selected();
  return automaticIncrementalSelected()&&incrementalPlan?.applicationId===app?.applicationId&&
    currentBinding()?.applicationId===app?.applicationId&&incrementalPlan?.plan?.sourceConfigRef===app?.sourceConfigRef?incrementalPlan.plan:null;
}
function invalidateIncrementalPlan(){
  incrementalPlanGeneration++;incrementalPlan=null;incrementalPlanError='';incrementalPlanLoading=false;
}
function incrementalBlockReason(){
  if(incrementalPlanLoading)return '正在自动核对全量基线和最新增量…';
  if(incrementalPlanError)return incrementalPlanError;
  const plan=currentIncrementalPlan();
  if(!plan)return '尚未核对增量基线，请刷新配置。';
  return plan.state==='BLOCKED'?message(plan.reasonCode):'';
}
function incrementalSummary(plan=currentIncrementalPlan()){
  if(!plan)return '';
  if(plan.state==='BASELINE_REQUIRED')return '本次将先建立新的全量基线，实际执行全量备份；完成后再次选择增量即可接续。'+message(plan.reasonCode);
  return `全量基线：${date(plan.baseFinishedAt)}；最新${labels[plan.parentPointType||plan.pointType]}：${date(plan.finishedAt)}。已核对完整备份链。`;
}
async function loadIncrementalPlan(){
  invalidateIncrementalPlan();
  if(!automaticIncrementalSelected())return;
  const app=selected(), generation=incrementalPlanGeneration;
  if(!app||currentBinding()?.applicationId!==app.applicationId)return;
  const applicationId=app.applicationId,sourceConfigRef=app.sourceConfigRef;
  incrementalPlanLoading=true;render();
  try{
    const value=await api('/incremental-plan?applicationId='+encodeURIComponent(applicationId));
    if(generation!==incrementalPlanGeneration||!automaticIncrementalSelected()||selected()?.applicationId!==applicationId||selected()?.sourceConfigRef!==sourceConfigRef)return;
    const plan=value?.plan;
    if(value?.applicationId!==applicationId||plan?.schemaVersion!=='AutomaticIncrementalPlan/v1'||plan.sourceConfigRef!==sourceConfigRef||
      !['READY','BASELINE_REQUIRED','BLOCKED'].includes(plan.state)||!/^([a-f0-9]{64})$/.test(plan.planDigest||'')||!/^([a-f0-9]{64})$/.test(plan.evidenceDigest||'')||
      (plan.state==='READY'&&(!plan.parentChainRef||!plan.baseFullRef||!Number.isFinite(Date.parse(plan.finishedAt))||!Number.isFinite(Date.parse(plan.baseFinishedAt))))||
      (plan.state!=='READY'&&typeof plan.reasonCode!=='string'))throw new Error('INCREMENTAL_PLAN_INVALID');
    incrementalPlan=Object.freeze({applicationId,plan:Object.freeze({...plan})});
  }catch(error){if(generation===incrementalPlanGeneration)incrementalPlanError='增量基线核对失败：'+message(error.message);}
  finally{if(generation===incrementalPlanGeneration){incrementalPlanLoading=false;render();}}
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
  const binding=currentBinding(), app=selected(),plan=currentIncrementalPlan();
  const chosenAction=simpleRestoring?'RESTORE':automaticIncrementalSelected()&&plan?.state==='BASELINE_REQUIRED'?'FULL':S('simple-type').value;
  if(!binding || app?.applicationId!==binding.applicationId)throw new Error('SOURCE_NOT_REGISTERED_BY_W08');
  return {schemaVersion:'SmallAppBackupUiRequest/v1',operationId:id,action:chosenAction,sourceConfigRef:app.sourceConfigRef,
    parentChainRef:chosenAction==='INCREMENTAL'?plan?.parentChainRef||null:null,
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
  const request=active.request, context=active.displayContext;
  const fields=[['操作',labels[request.action]],['来源服务器',context?.server||'来源服务器未记录'],
    ['来源',request.sourceConfigRef],['执行模式',context?.mode==='fast'?'快速模式 · 跳过核验':context?.mode==='safe'?'安全模式 · 完整核验':'执行模式未记录']];
  if(request.parentChainRef)fields.push(['增量父点',request.parentChainRef]);
  if(active.automaticIncrementalPlan){
    const plan=active.automaticIncrementalPlan;
    fields.push(['自动备份计划',plan.state==='BASELINE_REQUIRED'?'建立全量基线：'+message(plan.reasonCode):'接续已核对的最新备份点']);
    if(plan.baseFullRef)fields.push(['全量基线',plan.baseFullRef]);
  }
  if(request.recoveryPointRef)fields.push(['备份包',request.recoveryPointRef]);
  if(request.targetConfigRef)fields.push(['恢复目标',request.targetConfigRef]);
  if(request.action==='RESTORE')fields.push(['恢复方式',context?.restoreMode==='replace'?'覆盖现有程序':context?.restoreMode==='fresh'?'恢复到空目标':'恢复方式未记录']);
  for(const [label,value] of fields){const term=document.createElement('dt'),description=document.createElement('dd');term.textContent=label;description.textContent=value;details.append(term,description);}
}
async function openRecord(record){
  if(interactionLocked() || switching)return;
  syncSimpleIdentity(record);selectRecord(record);
  showSimplePage('progress',true);
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
  renderSimpleNavigation();
  const refs=binding&&selected()?.applicationId===binding.applicationId?selected()?.validated?.recoveryPointRefs||[]:[];
  const previous=S('simple-package').value;S('simple-package').replaceChildren(new Option('请选择可用备份包',''));
  if(catalogRestore){
    S('simple-package').replaceChildren(new Option(`${catalogRestore.version} · ${catalogRestore.packageId}`,catalogRestore.packageId));
    S('simple-package').value=catalogRestore.packageId;
  }else{
    for(const ref of refs){const record=records.find(r=>r.request.operationId===ref);const label=record?`${date(record.createdAt)} · ${labels[record.request.action]} · ${ref}`:ref;S('simple-package').add(new Option(label,ref));}
    if(refs.includes(previous))S('simple-package').value=previous;
  }
  const fresh=binding&&selected()?.applicationId===binding.applicationId?simpleFreshTargets():[];
  const usedTargets=new Set(replacing?[]:records.filter(r=>r.request.action==='RESTORE'&&r.spugHistoryId&&!r.cancelledUnaccepted).map(r=>r.request.targetConfigRef));
  const priorTarget=S('simple-target').value;
  S('simple-target').replaceChildren(new Option('请选择可用恢复服务器',''));
  for(const server of simpleConfig?.servers||[]){
    const registered=targetServers[server.address], available=registered&&fresh.includes(registered);
    const used=usedTargets.has(registered);
    const option=new Option(`${server.name}　${server.address}${used?'（目标已使用）':available?'':registered?'（选择后核验）':'（未登记目标）'}`,server.address);
    option.disabled=!registered||used;S('simple-target').add(option);
  }
  if(targetServers[priorTarget]&&!usedTargets.has(targetServers[priorTarget]))S('simple-target').value=priorTarget;
  let blocked='';
  if(simpleInitializing)blocked='正在读取配置并核对来源，请稍候…';
  else if(!simpleConfig)blocked=simpleConfigError||'配置未读取，不能执行。';
  else if(!binding){
    const available=simpleConfig.bindings.filter(b=>b.selectable&&b.product===S('simple-product').value&&b.server===S('simple-server').value);
    const modes=available.map(b=>b.mode==='safe'?'安全模式':'快速模式');
    blocked=`该服务器尚未登记${fast?'快速':'安全'}模式执行器。`+(modes.length?'请手动选择'+modes.join('或')+'。':'');
  }
  else if(S('simple-nas').value.trim()!==simpleConfig.nas)blocked='该 NAS 路径尚未绑定执行器，不能提交到其他目录。';
  else if(switching||selected()?.applicationId!==binding.applicationId)blocked='正在核对服务器配置…';
  else if(!selected()?.validated)blocked=message(selected()?.readinessError||'SOURCE_NOT_VERIFIED_BY_W01');
  else if(catalogRestore&&!refs.includes(catalogRestore.packageId))blocked='该包未登记为所选来源的可用恢复点，不能执行。请选择正确来源或核对恢复点登记。';
  else if(restore&&!S('simple-package').value)blocked='请选择备份包。';
  else if(restore&&!S('simple-target').value)blocked=Object.values(targetServers).some(ref=>fresh.includes(ref))?'请选择可用恢复服务器。':replacing?'所选来源尚无可用的覆盖恢复目标。':'所选来源当前没有可用的空恢复目标。';
  else if(restore&&!targetServers[S('simple-target').value])blocked='该恢复服务器尚无已登记的恢复目标。';
  else if(restore&&!fresh.includes(targetServers[S('simple-target').value]))blocked='该恢复目标当前不可用，请刷新配置后重新选择。';
  else if(automaticIncrementalSelected()&&incrementalBlockReason())blocked=incrementalBlockReason();
  else if(S('submit').disabled)blocked=S('blocked-reason').textContent||'当前不可提交。';
  S('simple-status').textContent=blocked||(restore?replacing?'将覆盖所选目标现有程序的记录、附件及 Redis 数据。':'将按所选备份链恢复到登记的独立目标。':automaticIncrementalSelected()?incrementalSummary():'已连接 Spug 执行器。');
  S('simple-status').dataset.state=blocked?'blocked':'ready';
  S('simple-submit').disabled=!!blocked||interactionLocked();S('simple-submit').textContent=restore?'开始恢复 →':currentIncrementalPlan()?.state==='BASELINE_REQUIRED'?'建立全量基线 →':'开始备份 →';
  S('simple-submit').title=blocked;
  if(blocked)S('submit').disabled=true;
  S('simple-result').textContent=S('result-state').textContent;
  if(fast&&active?.result?.state==='SUCCEEDED')S('simple-result').textContent=active.request.action==='RESTORE'?'恢复命令已完成；快速模式未执行完整核验，业务验收待确认。':'备份命令已完成；快速模式未执行完整核验。';
  S('operation-reference').textContent=active?.request.operationId||'';
  drawOperationDetails();
  const draftLocked=simpleInitializing||interactionLocked()||switching||!!unresolvedOriginal()||!!active&&!resolvedRecord(active);
  for(const id of ['simple-product','simple-server','simple-mode','simple-type','simple-package','simple-target','simple-restore-mode','simple-nas','simple-backup-tab','simple-restore-tab','simple-refresh'])S(id).disabled=draftLocked;
  if(catalogRestore){S('simple-product').disabled=true;S('simple-package').disabled=true;S('simple-nas').disabled=true;}
  S('simple-query').disabled=interactionLocked()||!active;
  S('simple-history').replaceChildren();
  const visibleRecords=records.filter(record=>simpleConfig?.bindings.some(b=>b.product===S('simple-product').value&&b.applicationId===record.applicationId));
  for(const record of visibleRecords){
    const row=document.createElement('div');row.className='history-row';
    const label=document.createElement('small');label.textContent=`${date(record.createdAt)} · ${labels[record.request.action]} · ${record.request.operationId}`;
    const button=document.createElement('button');button.textContent='查看进度';button.disabled=simpleInitializing||interactionLocked()||switching;
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
  invalidateIncrementalPlan();
  if(binding)applicationDraftSelections.set(binding.product,{server:binding.server,mode:binding.mode});
  selectRecord(null);telemetry=null;telemetryError='';
  S('simple-package').value='';S('simple-target').value='';S('point').value='';S('parent').value='';S('target').value='';S('result-state').textContent='尚未执行';
  if(!binding){render();return;}
  action=simpleRestoring?'RESTORE':S('simple-type').value;S('application').value=binding.applicationId;chooseId();
  // Explicit user change starts a new draft; historical operations remain in the history.
  selectRecord(null);operationId='smallapp-'+crypto.randomUUID().replace(/-/g,'');switching=true;render();
  try{await refresh(binding.applicationId);
    if(automaticIncrementalSelected())await loadIncrementalPlan();
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
S('simple-backup-tab').onclick=()=>{if(S('simple-backup-tab').disabled)return;const changed=simpleRestoring;simpleRestoring=false;showSimplePage('backup');if(changed||active&&resolvedRecord(active))return chooseSimple();else render();};
S('simple-restore-tab').onclick=()=>{if(S('simple-restore-tab').disabled)return;const changed=!simpleRestoring;if(changed)S('simple-restore-mode').value='replace';simpleRestoring=true;showSimplePage('restore');if(changed)chooseSimple();else render();};
for(const name of ['catalog','progress','history'])S('simple-'+name+'-tab').onclick=()=>showSimplePage(name);
for(const name of Object.keys(simplePages))S('simple-'+name+'-tab').onkeydown=event=>{
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();
  const enabled=Object.keys(simplePages).filter(page=>!S('simple-'+page+'-tab').disabled);
  const index=enabled.indexOf(name);
  const next=event.key==='Home'?enabled[0]:event.key==='End'?enabled.at(-1):enabled[(index+(event.key==='ArrowLeft'?-1:1)+enabled.length)%enabled.length];
  S('simple-'+next+'-tab').focus?.();S('simple-'+next+'-tab').onclick();
};
if(typeof window!=='undefined'){
  const requested=Object.keys(simpleAnchors).find(name=>window.location.hash==='#'+simpleAnchors[name]);
  if(requested){simplePage=requested;if(requested==='restore'){simpleRestoring=true;action='RESTORE';}renderSimpleNavigation();}
  window.addEventListener('hashchange',()=>{
    const name=Object.keys(simpleAnchors).find(page=>window.location.hash==='#'+simpleAnchors[page]);
    if(!name || name===simplePage)return;
    if(S('simple-'+name+'-tab').disabled){showSimplePage(simplePage);return;}
    S('simple-'+name+'-tab').onclick();
  });
}
for(const id of ['simple-server','simple-mode','simple-type','simple-restore-mode'])S(id).onchange=chooseSimple;
S('simple-product').onchange=()=>{
  const product=S('simple-product').value;
  const previous=applicationDraftSelections.get(product);
  const binding=simpleConfig?.bindings.find(b=>b.selectable&&b.product===product);
  // Preserve an explicit draft choice even if its registration is now unavailable.
  // Rendering will explain the missing registration and keep submission disabled.
  if(previous){S('simple-server').value=previous.server;S('simple-mode').value=previous.mode;}
  else if(binding){S('simple-server').value=binding.server;S('simple-mode').value=binding.mode;}
  return chooseSimple();
};
S('simple-nas').oninput=()=>render();
S('simple-package').onchange=()=>{S('point').value=S('simple-package').value;render();};
S('simple-target').onchange=async()=>{
  if(interactionLocked()||switching)return;
  S('target').value=simpleTargetServers()[S('simple-target').value]||'';
  await refresh(currentBinding()?.applicationId);
};
S('simple-refresh').onclick=refreshSimpleConfiguration;
S('simple-query').onclick=async()=>{await query();await progress();render();};
S('simple-submit').onclick=()=>{
  if(S('simple-submit').disabled)return;
  const request=Object.freeze(simpleRequest(operationId));
  const plan=currentIncrementalPlan();
  confirmation=Object.freeze({request,applicationId:selected().applicationId,automaticIncrementalPlan:plan});
  const replacing=replacementRequest(request,currentBinding());
  S('replace-confirm-field').hidden=!replacing;S('replace-confirm').checked=false;S('simple-confirm-submit').disabled=replacing;
  S('confirm-summary').textContent=`${S('simple-product').selectedOptions[0].textContent} · ${labels[request.action]} · ${S('simple-server').selectedOptions[0].textContent} · ${S('simple-mode').selectedOptions[0].textContent}\nNAS：${S('simple-nas').value}\n来源：${request.sourceConfigRef}\n`+(request.action==='RESTORE'?`备份包：${request.recoveryPointRef}\n恢复到：${S('simple-target').selectedOptions[0].textContent}\n独立目标：${request.targetConfigRef}`:`备份类型：${labels[request.action]}${request.action==='INCREMENTAL'?'\n父链：'+request.parentChainRef:''}`);
  if(replacing)S('confirm-summary').textContent+='\n恢复方式：覆盖现有程序，将替换目标现有记录、附件及 Redis 数据。';
  if(plan)S('confirm-summary').textContent+='\n'+incrementalSummary(plan)+(plan.baseFullRef?'\n全量基线：'+plan.baseFullRef:'');
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
  if(S('simple-submit').disabled || snapshot.applicationId!==selected()?.applicationId || !sameRequest(snapshot.request,simpleRequest(operationId))||
    snapshot.automaticIncrementalPlan?.planDigest!==currentIncrementalPlan()?.planDigest){problem('操作参数或备份计划已变化，请重新确认。');return;}
  closeCatalogRestore(false);
  showSimplePage('progress',true);
  await submitOriginal(snapshot.request,snapshot.applicationId,false,snapshot.automaticIncrementalPlan);await progress();render();
};
async function pollOriginal(){
  if(!document.hidden&&!interactionLocked()&&!pollBusy){
    if(unresolvedOriginal()&&pending.request.operationId!==active?.request.operationId)await queryPendingOriginal();
    else if(active&&!resolvedRecord(active)){await query();await progress();}
  }
  drawProgress();
}
setInterval(pollOriginal,5000);
(async()=>{
  simpleInitializing=true;render();
  try{await initialRefresh;simpleConfig=await api('/simple-config');S('simple-nas').value=simpleConfig.nas;
    if(active&&!pending){active=null;operationId='';}
    const matched=simpleConfig.bindings.find(b=>b.applicationId===active?.applicationId);
    if(matched){S('simple-product').value=matched.product;S('simple-server').value=matched.server;S('simple-mode').value=matched.mode;simpleRestoring=action==='RESTORE';if(!simpleRestoring)S('simple-type').value=action;render();if(!resolvedRecord(active))await query();await progress();}
    else {const first=simpleConfig.bindings.find(b=>b.selectable);if(!currentBinding()&&first){S('simple-server').value=first.server;S('simple-mode').value=first.mode;}await chooseSimple();}
  }catch(error){simpleConfig=null;simpleConfigError='配置读取失败：'+error.message;problem(simpleConfigError);}
  finally{simpleInitializing=false;render();}
})();
