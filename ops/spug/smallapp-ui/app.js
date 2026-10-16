'use strict';
const $ = id => document.getElementById(id);
const labels = {FULL:'全量备份', INCREMENTAL:'增量备份', RESTORE:'恢复'};
const states = {RUNNING:'原操作执行或核对中', SUCCEEDED:'执行完成', FAILED:'原操作失败'};
const reasons = {
  W01_TRANSPORT_BINDING_REQUIRED:'执行桥尚未安装并绑定，当前不能执行。',
  W01_SELECTION_ENDPOINT_REQUIRED:'执行桥尚未提供可用来源和备份链选择。',
  SOURCE_NOT_VERIFIED_BY_W01:'该来源尚未完成实际安装和执行器核验。',
  SOURCE_NOT_REGISTERED_BY_W08:'该来源尚未登记。',
  PARENT_CHAIN_NOT_ACCEPTED:'所选父链尚未通过实际备份验收。',
  RECOVERY_POINT_NOT_ACCEPTED:'所选恢复点尚未通过完整链验收。',
  TARGET_NOT_CURRENTLY_FRESH:'恢复目标尚未证明为空且独立。',
  BUSINESS_PAGE_SELECTION_REQUIRED:'请在本页面选择参数后执行。',
  ORIGINAL_EXECUTION_NOT_YET_OBSERVED:'尚未读到原操作执行回执，请查询原编号，勿重复提交。',
  ORIGINAL_OPERATION_NOT_LOCALLY_RECORDED:'未找到此编号的本机受理记录，执行状态尚未证实。请保留原编号，不要重复提交。',
  ORIGINAL_OPERATION_ALREADY_RECORDED:'原编号已有受理或执行记录，只能查询原结果。',
  ORIGINAL_OPERATION_ALREADY_ACCEPTED:'执行器已有此编号，只能查询原结果。',
  ORIGINAL_OPERATION_NOT_PROVEN_UNACCEPTED:'尚不能确认原编号未受理，禁止重试。',
  ORIGINAL_RETRY_REQUEST_MISMATCH:'未受理核对结果与原请求不一致，禁止重试。',
  SPUG_DISPATCH_RESERVED:'已保留原操作编号，正在等待执行回执。',
  BRIDGE_UNAVAILABLE_OR_RESPONSE_INVALID:'执行桥不可达或返回无效，只能继续查询原操作。',
  SPUG_LOGIN_REQUIRED:'登录已失效，请重新登录 Spug。',
  SPUG_MANUAL_TEMPLATE_CHANGED:'原任务配置与仅手动入口不一致，当前不能执行。',
  W08_DISPLAY_SETTINGS_REQUIRED:'应用来源配置尚未安装，当前不能执行。',
  ENTRY_REQUEST_TIMEOUT:'页面请求超时，请查询原操作编号。',
  ORIGINAL_OPERATION_DEADLINE_EXCEEDED:'原操作已超过执行时限，正在核对实际结果，请继续查询原编号。',
};
let action = 'FULL', options = [], records = [], active = null, operationId = '', busy = false;
let initialIds = {};
let versions = {}, pending = null;
let retryEvidence = null;
function sameRequest(left, right){
  const keys=['schemaVersion','operationId','action','sourceConfigRef','parentChainRef','recoveryPointRef','targetConfigRef'];
  return !!left && !!right && Object.keys(left).length===keys.length && Object.keys(right).length===keys.length &&
    keys.every(key=>Object.hasOwn(left,key) && Object.hasOwn(right,key) && left[key]===right[key]);
}
function retryReady(record, evidence){
  return !!record && !record.result && !record.spugHistoryId && !record.dispatchErrorCode &&
    evidence?.retryAllowed===true && evidence.applicationId===record.applicationId && sameRequest(record.request,evidence.request);
}
function selectedRequest(id){
  return {schemaVersion:'SmallAppBackupUiRequest/v1',operationId:id,action,sourceConfigRef:selected()?.sourceConfigRef,
    parentChainRef:action==='INCREMENTAL'?$('parent').value:null,
    recoveryPointRef:action==='RESTORE'?$('point').value:null,targetConfigRef:action==='RESTORE'?$('target').value:null};
}
async function checkUnaccepted(request, applicationId){
  const evidence=await api('/unaccepted-original?request='+encodeURIComponent(JSON.stringify(request)));
  if(!retryReady({request,applicationId},evidence))throw new Error('ORIGINAL_RETRY_REQUEST_MISMATCH');
  return evidence;
}
function message(code){return (reasons[code] || '尚未满足执行条件') + (code ? '（' + code + '）' : '');}
function problem(text){$('problem').textContent=text; $('problem').hidden=!text;}
async function api(path, body){
  const token=localStorage.getItem('token');
  if(!token){$('login').hidden=false; throw new Error('SPUG_LOGIN_REQUIRED');}
  const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),20000);
  try{
    const response=await fetch('/backup-entry-api'+path,{method:body===undefined?'GET':'POST',
      headers:{'X-Token':token,'Content-Type':'application/json'},cache:'no-store',signal:controller.signal,
      body:body===undefined?undefined:JSON.stringify(body)});
    const value=await response.json();
    if(!response.ok){if(response.status===401)$('login').hidden=false; throw new Error(value.errorCode || 'ENTRY_REQUEST_FAILED');}
    return value;
  }catch(error){if(error.name==='AbortError')throw new Error('ENTRY_REQUEST_TIMEOUT');throw error;}
  finally{clearTimeout(timer);}
}
function selected(){return options.find(a=>a.applicationId===$('application').value);}
function fill(id, refs, empty){
  const element=$(id), prior=element.value;
  element.replaceChildren(new Option(empty,''));
  for(const ref of refs)element.add(new Option(ref,ref));
  if(refs.includes(prior))element.value=prior;
  element.disabled=!refs.length || !!active;
}
function chooseId(){
  retryEvidence=null;
  const app=selected();
  operationId=app && initialIds[app.applicationId]?.[action] || ('smallapp-'+crypto.randomUUID().replace(/-/g,''));
  const prior=pending && app && pending.applicationId===app.applicationId && pending.request.action===action ? pending :
    records.find(r=>r.applicationId===app?.applicationId && r.request.action===action);
  active=prior || null;
  if(prior)showResult(prior);
  else{$('result-state').textContent='尚未执行';$('result-details').hidden=true;}
}
function render(){
  const app=selected(), row=app?.validated;
  fill('source',app?.sourceConfigRef?[app.sourceConfigRef]:[],'来源尚未登记');
  // One explicit registered source for each current application; never choose a chain or latest point.
  if(app?.sourceConfigRef)$('source').value=app.sourceConfigRef;
  fill('parent',row?.parentChainRefs || [],'请选择已接受的父链');
  fill('point',row?.recoveryPointRefs || [],'请选择已接受的恢复点');
  fill('target',row?.freshTargetConfigRefs || [],'请选择全新独立目标');
  if(active && active.request.action===action){
    for(const [id,key] of [['parent','parentChainRef'],['point','recoveryPointRef'],['target','targetConfigRef']]){
      const ref=active.request[key];
      if(ref){$(id).replaceChildren(new Option(ref+'（原操作）',ref));$(id).value=ref;}
      $(id).disabled=true;
    }
  }
  $('incremental-fields').hidden=action!=='INCREMENTAL';
  $('restore-fields').hidden=action!=='RESTORE';
  $('application').disabled=!!active || busy;
  $('selected-version').textContent=versions[app?.applicationId] || '版本尚未登记';
  $('readiness').dataset.ready=String(!!row?.fullReady);
  $('readiness').textContent=row?.fullReady ? '来源已由执行器核验；本次执行前会重新检查。'+
    (row.historyErrorCode?' 备份链历史暂不可读：'+message(row.historyErrorCode):'') :
    message(app?.readinessError || row?.fullErrorCode || 'SOURCE_NOT_VERIFIED_BY_W01');
  $('action-note').textContent={FULL:'保存当前来源的完整备份。首次全量备份无需等待增量链或恢复目标。',
    INCREMENTAL:'只使用你选择的真实已接受父链，不自动选择最新备份。',
    RESTORE:'按所选完整恢复点恢复到全新独立目标，保留原来源。'}[action];
  let blocked='';
  if(active)blocked=retryReady(active,retryEvidence)?'已核对原编号未受理，可按原编号重试。':'本操作已经保留编号，只能查询原结果或核对是否未受理。';
  else if(!row?.fullReady)blocked=message(app?.readinessError || row?.fullErrorCode || 'SOURCE_NOT_VERIFIED_BY_W01');
  else if(action!=='FULL' && row.historyErrorCode)blocked=message(row.historyErrorCode);
  else if(action==='INCREMENTAL' && !$('parent').value)blocked=row.parentChainRefs.length?'请选择父备份链。':'尚无已接受的父备份链；先完成真实全量备份。';
  else if(action==='RESTORE' && !$('point').value)blocked=row.recoveryPointRefs.length?'请选择恢复点。':'尚无已接受的完整恢复点。';
  else if(action==='RESTORE' && !$('target').value)blocked=row.freshTargetConfigRefs.length?'请选择全新恢复目标。':'尚无已核验的全新独立恢复目标。';
  $('blocked-reason').textContent=blocked;
  $('operation-id').textContent=active?.request.operationId || operationId;
  $('submit').textContent='开始'+labels[action]; $('submit').disabled=busy || !!blocked;
  $('query').disabled=busy || !active;
  $('retry-original').disabled=busy || !retryReady(active,retryEvidence);
  $('check-unaccepted').disabled=busy || !app || !row?.fullReady;
  $('original-operation-id').disabled=busy;
  $('new-operation').disabled=busy || (!!active && !['SUCCEEDED','FAILED'].includes(active.result?.state));
  document.querySelectorAll('[data-action]').forEach(button=>{
    button.setAttribute('aria-selected',String(button.dataset.action===action)); button.disabled=busy;
  });
}
function showResult(record){
  const result=record.result;
  $('result-state').textContent=record.request.action==='RESTORE' && result?.state==='SUCCEEDED'?
    '数据恢复及保护启动完成，业务验收尚未完成。':result?states[result.state]:'已保留编号，尚未查询执行回执';
  $('result-details').hidden=false;
  $('result-error').textContent=result?.errorCode?message(result.errorCode):record.dispatchErrorCode?message(record.dispatchErrorCode):'暂无错误回执';
  $('result-logs').textContent=result?.logRefs.length?result.logRefs.join('，'):'尚无日志引用';
  $('result-ref').textContent=result?.resultRef || '尚无结果引用';
  $('result-history').replaceChildren();
  if(record.spugHistoryId){
    const link=document.createElement('a');link.href='/schedule';link.textContent='任务 '+record.spugTaskId+' / 历史 '+record.spugHistoryId;
    $('result-history').append(link);
  }else $('result-history').textContent='尚未生成历史记录；勿据此重复执行';
}
function history(){
  $('history').replaceChildren(); $('empty-history').hidden=!!records.length;
  for(const record of records){
    const tr=document.createElement('tr');
    for(const value of [record.request.operationId,labels[record.request.action],record.request.sourceConfigRef,record.createdAt]){
      const td=document.createElement('td');td.textContent=value;tr.append(td);
    }
    const td=document.createElement('td'),button=document.createElement('button');button.textContent='查看原结果';
    button.addEventListener('click',async()=>{if(busy)return;active=record;action=record.request.action;$('application').value=record.applicationId;render();await query();});
    td.append(button);tr.append(td);$('history').append(tr);
  }
}
async function refresh(){
  retryEvidence=null;
  busy=true;problem('');render();
  try{
    const value=await api('/selections');options=value.applications;initialIds=value.initialOperationIds;versions=value.registrationVersions;
    const prior=$('application').value;$('application').replaceChildren();
    for(const app of options)$('application').add(new Option(app.displayName,app.applicationId));
    if(options.some(a=>a.applicationId===prior))$('application').value=prior;
    if(active && options.some(a=>a.applicationId===active.applicationId))$('application').value=active.applicationId;
    try{records=await api('/history');history();}
    catch(historyError){problem(message(historyError.message)+' 操作历史暂不可读。');}
    if(!operationId && !active)chooseId();
  }catch(error){problem(message(error.message));}
  finally{busy=false;render();}
}
async function query(){
  if(!active)return;retryEvidence=null;busy=true;problem('');render();
  try{active=await api('/operations/'+encodeURIComponent(active.request.operationId));
    if(pending?.request.operationId===active.request.operationId){pending=active;localStorage.setItem('spug-backup-original',JSON.stringify(active));}
    showResult(active);
    records=await api('/history');history();
  }catch(error){problem(message(error.message));}
  finally{busy=false;render();}
}
async function submitOriginal(request, applicationId, retry=false){
  busy=true;problem('');render();
  if(retry){
    retryEvidence=null;
    try{await checkUnaccepted(request,applicationId);}
    catch(error){problem(message(error.message));busy=false;render();return;}
  }
  // Persist the original before POST; a lost reply only enables original-ID queries.
  retryEvidence=null;
  active={request,applicationId,spugTaskId:null,createdAt:new Date().toISOString(),spugHistoryId:null,dispatchErrorCode:null};
  localStorage.setItem('spug-backup-original',JSON.stringify(active));
  pending=active;
  busy=true;problem('');render();
  try{active=await api('/operations',request);pending=active;localStorage.setItem('spug-backup-original',JSON.stringify(active));
    showResult(active);records=await api('/history');history();}
  catch(error){
    // A lost HTTP reply queries the saved ID once; it never repeats the POST.
    try{active=await api('/operations/'+encodeURIComponent(request.operationId));pending=active;
      localStorage.setItem('spug-backup-original',JSON.stringify(active));showResult(active);}
    catch(queryError){problem(message(error.message)+' '+message(queryError.message)+' 请查询原编号。');showResult(active);}
  }
  finally{busy=false;render();}
}
$('submit').addEventListener('click',async()=>{
  if($('submit').disabled || active)return;
  await submitOriginal(selectedRequest(operationId),selected().applicationId);
});
$('check-unaccepted').addEventListener('click',async()=>{
  if($('check-unaccepted').disabled)return;
  const id=$('original-operation-id').value.trim();
  if(!/^[A-Za-z0-9][A-Za-z0-9_.:-]{7,159}$/.test(id)){problem('请填写完整的原操作编号。');return;}
  if(active?.request.operationId===id && (active.result || active.spugHistoryId || active.dispatchErrorCode)){
    retryEvidence=null;problem(message('ORIGINAL_OPERATION_ALREADY_RECORDED'));render();return;
  }
  const request=active?.request.operationId===id?{...active.request}:selectedRequest(id);
  const applicationId=selected().applicationId;
  retryEvidence=null;busy=true;problem('');render();
  try{
    const evidence=await checkUnaccepted(request,applicationId);
    active={request,applicationId,spugTaskId:null,createdAt:new Date().toISOString(),spugHistoryId:null,dispatchErrorCode:null};
    pending=active;operationId=id;localStorage.setItem('spug-backup-original',JSON.stringify(active));
    retryEvidence=evidence;showResult(active);
    $('result-state').textContent='已核对未受理，可按原编号重试';
  }catch(error){problem(message(error.message));}
  finally{busy=false;render();}
});
$('retry-original').addEventListener('click',async()=>{
  if($('retry-original').disabled || !retryReady(active,retryEvidence))return;
  await submitOriginal({...active.request},active.applicationId,true);
});
$('original-operation-id').addEventListener('input',()=>{retryEvidence=null;render();});
$('query').addEventListener('click',query);
$('refresh').addEventListener('click',refresh);
$('application').addEventListener('change',()=>{chooseId();render();});
for(const id of ['parent','point','target'])$(id).addEventListener('change',render);
document.querySelectorAll('[data-action]').forEach(button=>button.addEventListener('click',()=>{
  action=button.dataset.action;active=null;chooseId();render();
}));
$('new-operation').addEventListener('click',()=>{
  if($('new-operation').disabled)return;
  retryEvidence=null;
  if(active && pending?.request.operationId===active.request.operationId){pending=null;localStorage.removeItem('spug-backup-original');}
  active=null;
  operationId='smallapp-'+crypto.randomUUID().replace(/-/g,'');$('result-state').textContent='尚未执行';$('result-details').hidden=true;render();
});
try{const original=localStorage.getItem('spug-backup-original');if(original){active=JSON.parse(original);pending=active;action=active.request.action;}}
catch(error){problem('浏览器原操作记录无法读取，请通过操作记录核查。');}
refresh();
