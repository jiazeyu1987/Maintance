'use strict';
const $ = id => document.getElementById(id);
const labels = {FULL:'全量备份', INCREMENTAL:'增量备份', RESTORE:'恢复'};
const states = {RUNNING:'原操作执行或核对中', SUCCEEDED:'执行完成', FAILED:'原操作失败'};
const reasons = {
  W01_TRANSPORT_BINDING_REQUIRED:'执行桥尚未安装并绑定，当前不能执行。',
  W01_SELECTION_ENDPOINT_REQUIRED:'执行桥尚未提供可用来源和备份链选择。',
  SOURCE_NOT_VERIFIED_BY_W01:'该来源尚未完成实际安装和执行器核验。',
  SOURCE_NOT_REGISTERED_BY_W08:'该来源尚未登记。',
  SOURCE_RESTORE_ONLY:'该来源用于历史备份恢复；创建新备份请选择当前服务器来源。',
  ARCHIVE_CATALOGUE_SOURCE_MISMATCH:'历史归档登记与所选来源不一致，不能恢复。',
  ARCHIVE_SCOPE_IDENTITY_MISMATCH:'历史备份范围与登记的来源身份不一致，不能恢复。',
  ARCHIVE_CHAIN_SCOPE_MISMATCH:'备份链包含不同的来源范围，不能恢复。',
  ARCHIVE_PARENT_NOT_ADMITTED:'历史备份链缺少已登记的父备份，不能恢复。',
  ARCHIVE_NATIVE_POINT_CONFLICT:'历史归档与原备份记录的恢复点不一致，不能恢复。',
  POINT_QUARANTINED:'该恢复点已隔离，不能用于恢复。请查看原验证失败记录。',
  PARENT_CHAIN_NOT_ACCEPTED:'所选父链尚未通过实际备份验收。',
  RECOVERY_POINT_NOT_ACCEPTED:'所选恢复点尚未通过完整链验收。',
  TARGET_NOT_CURRENTLY_FRESH:'恢复目标尚未证明为空且独立。',
  BUSINESS_PAGE_SELECTION_REQUIRED:'请在本页面选择参数后执行。',
  ORIGINAL_EXECUTION_NOT_YET_OBSERVED:'尚未读到原操作执行回执，请查询原编号，勿重复提交。',
  ORIGINAL_OPERATION_NOT_LOCALLY_RECORDED:'未找到此编号的本机受理记录，执行状态尚未证实。请保留原编号，不要重复提交。',
  ORIGINAL_OPERATION_ALREADY_RECORDED:'原编号已有受理或执行记录，只能查询原结果。',
  ORIGINAL_OPERATION_ALREADY_ACCEPTED:'执行器已有此编号，只能查询原结果。',
  ORIGINAL_OPERATION_NOT_PROVEN_UNACCEPTED:'尚不能确认原编号未受理，禁止重试。',
  ORIGINAL_DISPATCH_NOT_RECOVERABLE:'原操作已进入派发或缺少派发证据，不能重新派发；请继续查询原编号。',
  ORIGINAL_RETRY_REQUEST_MISMATCH:'未受理核对结果与原请求不一致，禁止重试。',
  SPUG_DISPATCH_RESERVED:'已保留原操作编号，正在等待执行回执。',
  ORIGINAL_OWNER_RESULT_NOT_READY:'原任务正在执行，尚未生成最终结果；请查询原编号。',
  BRIDGE_UNAVAILABLE_OR_RESPONSE_INVALID:'旧记录未保存具体原因，请刷新配置或查询原编号，获取当前错误。',
  BRIDGE_TIMEOUT:'请求执行桥超时，尚未收到完整响应。请检查执行桥运行状态及网络后重新查询。',
  BRIDGE_CONNECTION_REFUSED:'执行桥连接被拒绝。请检查监听端口及访问限制。',
  BRIDGE_DNS_FAILED:'执行桥域名解析失败。请检查本机或容器的域名解析配置。',
  BRIDGE_CONNECTION_RESET:'执行桥连接被重置或中断，尚未取得完整结果。',
  BRIDGE_NETWORK_UNREACHABLE:'到执行桥的网络或主机不可达。请检查路由及网络连接。',
  BRIDGE_TLS_CERTIFICATE_INVALID:'执行桥 TLS 证书校验失败。请检查证书有效期、域名及信任链。',
  BRIDGE_TLS_FAILED:'执行桥 TLS 握手失败，无法建立安全连接。',
  BRIDGE_CONNECTION_FAILED:'执行桥连接失败，系统未提供可识别的具体原因。请检查执行桥及网络日志。',
  BRIDGE_IO_FAILED:'与执行桥通信时读写失败，系统未提供更具体的原因。',
  BRIDGE_RESPONSE_ENCODING_INVALID:'执行桥响应不是有效的 UTF-8 文本，无法读取。',
  BRIDGE_RESPONSE_JSON_INVALID:'执行桥响应不是有效的 JSON 数据。请检查接口是否返回了错误页或登录页。',
  BRIDGE_RESPONSE_TOO_LARGE:'执行桥响应超过 64 KiB 安全上限，已拒绝读取。',
  BRIDGE_RESPONSE_INCOMPLETE:'执行桥响应未完整返回，连接已提前结束。',
  BRIDGE_RESPONSE_HTTP_INVALID:'执行桥返回的 HTTP 响应格式无效。请检查接口及代理配置。',
  BRIDGE_REQUEST_INVALID:'执行桥请求配置无效，无法发送。请检查已登记的接口配置。',
  BRIDGE_REDIRECT_REFUSED:'执行桥接口返回重定向，已拒绝跳转。请检查接口地址及代理配置。',
  BRIDGE_RESULT_FIELDS_INVALID:'执行桥结果字段不符合约定，无法确认执行结果。',
  BRIDGE_RESULT_SCHEMA_INVALID:'执行桥结果协议版本不匹配，无法确认执行结果。',
  BRIDGE_ORIGINAL_OPERATION_MISMATCH:'执行桥回执编号或操作类型与原请求不一致，已拒绝采用。',
  BRIDGE_STATE_INVALID:'执行桥返回了无效的执行状态，无法确认结果。',
  W01_SELECTION_FIELDS_INVALID:'执行桥可用配置响应字段不符合约定，当前不能执行。',
  SPUG_LOGIN_REQUIRED:'登录已失效，请重新登录 Spug。',
  SPUG_MANUAL_TEMPLATE_CHANGED:'原任务配置与仅手动入口不一致，当前不能执行。',
  W08_DISPLAY_SETTINGS_REQUIRED:'应用来源配置尚未安装，当前不能执行。',
  ENTRY_REQUEST_TIMEOUT:'页面请求超时，请查询原操作编号。',
  ENTRY_SELECTION_TIMEOUT:'恢复来源与目标准入核对超时，当前不能执行；请重新刷新配置。',
  SOURCE_SUBMISSION_LEGACY_LOCK_PRESENT:'检测到旧版提交锁目录，需要管理员核对原操作与旧进程后处理；当前禁止新提交。',
  SOURCE_SUBMISSION_RESERVATION_BUSY:'同一来源正在受理操作，请保留原编号并查询。',
  ENTRY_SELECTION_REFRESH_FAILED:'可用配置刷新失败，旧准入已失效；请成功刷新后再提交。',
  ENTRY_ORIGINAL_RESPONSE_MISMATCH:'原操作回执与请求不一致，已拒绝替换当前记录。',
  ORIGINAL_OPERATION_DEADLINE_EXCEEDED:'原操作已超过执行时限，正在核对实际结果，请继续查询原编号。',
  INCREMENTAL_PLAN_INVALID:'返回的增量计划不完整或与当前来源不一致，不能执行。',
  INCREMENTAL_PLAN_TIMEOUT:'增量基线核对超时，当前不能确认可用计划，请稍后刷新配置。',
  INCREMENTAL_PLAN_CHANGED:'备份基线已变化，本次请求未受理。请重新核对并确认当前计划。',
  INCREMENTAL_BASELINE_CHANGED:'执行前备份基线已变化，请查看原操作结果并重新核对备份计划。',
  SOURCE_OPERATION_IN_PROGRESS:'同一来源已有操作正在执行，完成后再刷新备份计划。',
  ORIGINAL_OPERATION_STILL_UNRESOLVED:'同一来源的原操作尚未确认结束，请在操作记录中查看原编号。',
  NO_SUCCESSFUL_FULL_BASELINE:'该来源尚无成功的全量备份，需要先建立全量基线。',
  SOURCE_BACKUP_IDENTITY_CHANGED:'来源数据库身份已变化，旧链不能接续，需要建立新的全量基线。',
  BACKUP_POINT_EPOCH_REQUIRED:'历史备份缺少当前恢复周期凭证，需要建立新的全量基线。',
  BACKUP_POINT_EPOCH_CHANGED:'来源已执行覆盖恢复，旧备份链已过期，需要建立新的全量基线。',
  INCREMENTAL_PARENT_BINLOG_PURGED:'父备份所需数据库日志已清理，需要建立新的全量基线。',
  INCREMENTAL_BINLOG_CHAIN_GAP:'父备份至当前的数据库日志存在缺段，需要建立新的全量基线。',
  INCREMENTAL_SOURCE_POSITION_REGRESSED:'当前数据库日志位置或事务集合已倒退，需要建立新的全量基线。',
  INCREMENTAL_SOURCE_LINEAGE_CHANGED:'数据库日志来源或版本谱系已变化，需要建立新的全量基线。',
  INCREMENTAL_LIVE_SOURCE_IDENTITY_CHANGED:'实际数据库身份与来源登记不符，请核对来源配置后再备份。',
  BACKUP_EPOCH_CHANGED_DURING_PLAN:'核对基线期间恢复周期发生变化，请等待原操作结束后刷新计划。',
  SOURCE_EPOCH_STORAGE_OVERLAP:'恢复周期登记或锁与可清理的数据路径重叠，请先修正来源登记。',
  DURABLE_INTENT_INCOMPLETE:'原操作的持久记录不完整，需先核对原操作，当前不能开始备份。',
  BACKUP_EPOCH_UNINITIALIZED:'来源恢复周期登记尚未初始化，当前不能开始备份。',
  BACKUP_EPOCH_NOT_READY:'来源恢复尚未结束或保留了失败状态，请先处理原恢复任务。',
  AMBIGUOUS_LATEST_FULL:'存在完成时间相同的全量基线，无法确认最新完整链，请核对备份记录。',
  INCREMENTAL_CHAIN_BRANCHED:'最新全量基线下存在多条增量分支，无法安全接续，请核对备份链。',
  INCREMENTAL_PARENT_PREFIX_INVALID:'增量父链缺失或顺序不完整，当前不能接续备份。',
  NATIVE_PIN_CHANGED:'备份原件摘要发生变化，完整性核验未通过，当前不能接续备份。',
  INCREMENTAL_ORIGINAL_EXIT_INVALID:'父备份原始执行未成功，当前不能接续该备份链。',
  INCREMENTAL_SOURCE_RESTORATION_INVALID:'备份源服务的恢复回执缺失或不匹配，请检查原备份的源服务恢复记录；当前不能接续备份。',
  SOURCE_EPOCH_POLICY_BINDING_INVALID:'当前来源身份与恢复周期登记不符，请核对来源配置。',
  BACKUP_POINT_EPOCH_BINDING_INVALID:'备份点与恢复周期登记不符，当前不能接续备份。',
  BACKUP_POINT_EPOCH_EVENT_INVALID:'备份点的恢复周期凭证无效，当前不能接续备份。',
};
let action = 'FULL', options = [], records = [], active = null, operationId = '', busy = false;
let initialIds = {};
let versions = {}, pending = null;
let retryEvidence = null;
let viewGeneration = 0, confirmation = null;
const interactionLocked = () => busy || !!confirmation;
const resolvedRecord = record => record?.cancelledUnaccepted===true || ['SUCCEEDED','FAILED'].includes(record?.result?.state);
const unresolvedOriginal = () => pending && !resolvedRecord(pending);
function selectRecord(record){
  active=record;viewGeneration++;retryEvidence=null;
  if(record)showResult(record);
  else{$('result-state').textContent='尚未执行';$('result-details').hidden=true;}
}
function sameRequest(left, right){
  const keys=['schemaVersion','operationId','action','sourceConfigRef','parentChainRef','recoveryPointRef','targetConfigRef'];
  return !!left && !!right && Object.keys(left).length===keys.length && Object.keys(right).length===keys.length &&
    keys.every(key=>Object.hasOwn(left,key) && Object.hasOwn(right,key) && left[key]===right[key]);
}
function originalResponse(value, request, applicationId){
  if(!sameRequest(value?.request,request) || value.applicationId!==applicationId)throw new Error('ENTRY_ORIGINAL_RESPONSE_MISMATCH');
  return value;
}
function retryReady(record, evidence){
  return !!record && !record.cancelledUnaccepted && !record.result && !record.spugHistoryId && !record.dispatchErrorCode &&
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
function message(code){
  const http=/^BRIDGE_HTTP_([1-5][0-9]{2})$/.exec(code||'');
  const httpReasons={401:'执行桥认证失败，请检查执行桥凭据配置。',403:'执行桥拒绝访问，请检查执行桥权限或访问限制。',
    404:'执行桥接口不存在，请检查接口路径及版本。',405:'执行桥接口不接受此请求方法，请检查接口版本。',
    429:'执行桥请求过于频繁，请稍后查询。',500:'执行桥服务发生内部错误，请检查服务日志。',
    502:'执行桥网关无法取得有效的上游响应，请检查网关及上游服务。',
    503:'执行桥服务当前不可用，请检查服务运行状态。',504:'执行桥网关等待上游响应超时，请检查上游服务及网络。'};
  const text=reasons[code]||(http?(httpReasons[http[1]]||('执行桥返回 HTTP '+http[1]+'，请求未能正常完成。')):'尚未满足执行条件');
  return text+(code?'（'+code+'）':'');
}
function problem(text){$('problem').textContent=text; $('problem').hidden=!text;}
async function api(path, body){
  const token=localStorage.getItem('token');
  if(!token){$('login').hidden=false; throw new Error('SPUG_LOGIN_REQUIRED');}
  const method=body===undefined?'GET':'POST';
  // The source plan has a 30 s budget and its bridge has 40 s. Keep one
  // bounded browser deadline through response-body reading for these routes.
  const planning=method==='GET'&&path.split('?')[0]==='/incremental-plan'||method==='POST'&&path==='/automatic-incremental';
  // Selection reads share a 50 s bridge budget; ordinary operations keep 20 s.
  const selections=method==='GET'&&path.split('?')[0]==='/selections';
  const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),planning||selections?60000:20000);
  try{
    const response=await fetch('/backup-entry-api'+path,{method,
      headers:{'X-Token':token,'Content-Type':'application/json'},cache:'no-store',signal:controller.signal,
      body:body===undefined?undefined:JSON.stringify(body)});
    const value=await response.json();
    if(!response.ok){
      if(response.status===401)$('login').hidden=false;
      const error=new Error(value.errorCode || value.error || 'ENTRY_REQUEST_FAILED');
      error.status=response.status;error.rejection=value;throw error;
    }
    return value;
  }catch(error){if(error.name==='AbortError')throw new Error(selections?'ENTRY_SELECTION_TIMEOUT':'ENTRY_REQUEST_TIMEOUT');throw error;}
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
  selectRecord(prior || null);
  if(prior)showResult(prior);
  else{$('result-state').textContent='尚未执行';$('result-details').hidden=true;}
}
function render(){
  const app=selected(), row=app?.validated,automatic=typeof automaticIncrementalSelected==='function'&&automaticIncrementalSelected();
  fill('source',app?.sourceConfigRef?[app.sourceConfigRef]:[],'来源尚未登记');
  // One explicit registered source for each current application; never choose a chain or latest point.
  if(app?.sourceConfigRef)$('source').value=app.sourceConfigRef;
  fill('parent',row?.parentChainRefs || [],'请选择已接受的父链');
  fill('point',row?.recoveryPointRefs || [],'请选择已接受的恢复点');
  fill('target',row?.freshTargetConfigRefs || [],'请选择全新独立目标');
  if(!active && app && typeof currentBinding==='function' && currentBinding()?.applicationId===app.applicationId){
    const draft=simpleRequest(operationId);action=draft.action;
    if(automatic&&draft.parentChainRef){$('parent').replaceChildren(new Option(draft.parentChainRef,draft.parentChainRef));$('parent').value=draft.parentChainRef;}
    $('point').value=draft.recoveryPointRef || '';$('target').value=draft.targetConfigRef || '';
  }
  if(active && active.request.action===action){
    for(const [id,key] of [['parent','parentChainRef'],['point','recoveryPointRef'],['target','targetConfigRef']]){
      const ref=active.request[key];
      if(ref){$(id).replaceChildren(new Option(ref+'（原操作）',ref));$(id).value=ref;}
      $(id).disabled=true;
    }
  }
  $('incremental-fields').hidden=action!=='INCREMENTAL';
  $('restore-fields').hidden=action!=='RESTORE';
  // Diagnostic parameters mirror the simple form; they are never a second editor.
  for(const id of ['application','source','parent','point','target'])$(id).disabled=true;
  $('selected-version').textContent=versions[app?.applicationId] || '版本尚未登记';
  $('readiness').dataset.ready=String(!!row?.fullReady);
  $('readiness').textContent=row?.fullReady ? '来源已由执行器核验；本次执行前会重新检查。'+
    (row.historyErrorCode?' 备份链历史暂不可读：'+message(row.historyErrorCode):'') :
    message(app?.readinessError || row?.fullErrorCode || 'SOURCE_NOT_VERIFIED_BY_W01');
  $('action-note').textContent={FULL:'保存当前来源的完整备份。首次全量备份无需等待增量链或恢复目标。',
    INCREMENTAL:'自动核对同一来源的全量基线及最新有效增量，提交前再次验证计划。',
    RESTORE:'按所选完整恢复点恢复到全新独立目标，保留原来源。'}[action];
  let blocked='';
  if(active)blocked=retryReady(active,retryEvidence)?'已核对原编号未受理，可按原编号重试。':'本操作已经保留编号，只能查询原结果或核对是否未受理。';
  else if(unresolvedOriginal())blocked='原操作尚未确认结束，请先查询原编号。';
  else if(!row?.fullReady && !(action==='RESTORE' && row?.fullErrorCode==='SOURCE_RESTORE_ONLY'))blocked=message(app?.readinessError || row?.fullErrorCode || 'SOURCE_NOT_VERIFIED_BY_W01');
  else if(automatic)blocked=incrementalBlockReason();
  else if(action!=='FULL' && row.historyErrorCode)blocked=message(row.historyErrorCode);
  else if(action==='INCREMENTAL' && !$('parent').value)blocked='尚未核对增量基线，请刷新配置。';
  else if(action==='RESTORE' && !$('point').value)blocked=row.recoveryPointRefs.length?'请选择恢复点。':'尚无已接受的完整恢复点。';
  else if(action==='RESTORE' && !$('target').value)blocked=row.freshTargetConfigRefs.length?'请选择全新恢复目标。':'尚无已核验的全新独立恢复目标。';
  $('blocked-reason').textContent=blocked;
  $('operation-id').textContent=active?.request.operationId || operationId;
  $('submit').textContent='开始'+labels[action]; $('submit').disabled=interactionLocked() || !!blocked;
  $('query').disabled=interactionLocked() || !active;
  $('refresh').disabled=interactionLocked();
  $('retry-original').disabled=interactionLocked() || !retryReady(active,retryEvidence);
  $('cancel-unaccepted').disabled=interactionLocked() || !retryReady(active,retryEvidence);
  $('recover-reserved').disabled=interactionLocked() || active?.dispatchState!=='RESERVED' ||
    (!!unresolvedOriginal() && !sameRequest(pending.request,active?.request));
  $('check-unaccepted').disabled=interactionLocked() || (!pending && !active && !app);
  $('original-operation-id').disabled=interactionLocked();
  $('new-operation').disabled=interactionLocked() || !!unresolvedOriginal() || (!!active && !resolvedRecord(active));
  document.querySelectorAll('[data-action]').forEach(button=>{
    button.setAttribute('aria-selected',String(button.dataset.action===action)); button.disabled=true;
  });
  document.querySelectorAll('#history button').forEach(button=>{button.disabled=interactionLocked();});
}
function showResult(record){
  const result=record.result;
  $('result-state').textContent=record.cancelledUnaccepted?'已确认未受理并取消；原编号已封存':record.request.action==='RESTORE' && result?.state==='SUCCEEDED'?
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
    button.disabled=interactionLocked();
    button.addEventListener('click',()=>openRecord(record));
    td.append(button);tr.append(td);$('history').append(tr);
  }
}
async function refresh(applicationOverride){
  if(interactionLocked())return;
  retryEvidence=null;
  busy=true;problem('');render();
  try{
    const applicationId=typeof applicationOverride==='string'?applicationOverride:active?.applicationId || $('application').value || pending?.applicationId;
    const targetRef=active?.request.action==='RESTORE'?active.request.targetConfigRef:
      typeof simpleTargetServers==='function'&&simpleRestoring&&currentBinding()?.applicationId===applicationId?
        simpleTargetServers()[S('simple-target').value]:null;
    const selectionQuery=applicationId?'?applicationId='+encodeURIComponent(applicationId)+
      (targetRef?'&targetConfigRef='+encodeURIComponent(targetRef):''):'';
    const value=await api('/selections'+selectionQuery);options=value.applications;initialIds=value.initialOperationIds;versions=value.registrationVersions;
    const prior=$('application').value;$('application').replaceChildren();
    for(const app of options)$('application').add(new Option(app.displayName,app.applicationId));
    if(options.some(a=>a.applicationId===prior))$('application').value=prior;
    if(active && options.some(a=>a.applicationId===active.applicationId))$('application').value=active.applicationId;
    try{records=await api('/history');history();}
    catch(historyError){problem(message(historyError.message)+' 操作历史暂不可读。');}
    if(!operationId && !active)chooseId();
  }catch(error){
    const code=Object.hasOwn(reasons,error.message)||/^BRIDGE_HTTP_[1-5][0-9]{2}$/.test(error.message)?
      error.message:'ENTRY_SELECTION_REFRESH_FAILED';
    options=options.map(app=>({...app,validated:null,readinessError:code}));
    problem(message('ENTRY_SELECTION_REFRESH_FAILED')+(code==='ENTRY_SELECTION_REFRESH_FAILED'?'':' '+message(code)));
  }
  finally{busy=false;render();}
}
async function query(){
  if(!active || interactionLocked())return;
  const original=active, generation=viewGeneration;
  retryEvidence=null;busy=true;problem('');render();
  try{const value=await api('/operations/'+encodeURIComponent(original.request.operationId));
    if(generation!==viewGeneration || active?.request.operationId!==original.request.operationId)return;
    active=originalResponse(value,original.request,original.applicationId);
    if(pending?.request.operationId===active.request.operationId){pending=active;localStorage.setItem('spug-backup-original',JSON.stringify(active));}
    showResult(active);
    const updated=await api('/history');
    if(generation!==viewGeneration)return;
    records=updated;history();
  }catch(error){if(generation===viewGeneration)problem(message(error.message));}
  finally{busy=false;render();}
}
async function queryPendingOriginal(){
  if(!unresolvedOriginal()||interactionLocked())return;
  const original=pending;
  busy=true;problem('');render();
  try{
    const value=originalResponse(await api('/operations/'+encodeURIComponent(original.request.operationId)),original.request,original.applicationId);
    if(!sameRequest(pending?.request,original.request))return;
    pending=value;localStorage.setItem('spug-backup-original',JSON.stringify(value));
    records=records.map(record=>record.request.operationId===original.request.operationId?value:record);history();
  }catch(error){problem(message(error.message)+' 正在继续核对原编号：'+original.request.operationId);}
  finally{busy=false;render();}
}
async function submitOriginal(request, applicationId, retry=false, automaticPlan=null){
  if(interactionLocked() || (unresolvedOriginal() && !sameRequest(pending.request,request)))return;
  busy=true;problem('');render();
  if(retry){
    retryEvidence=null;
    try{await checkUnaccepted(request,applicationId);}
    catch(error){problem(message(error.message));busy=false;render();return;}
  }
  // Persist the original before POST; a lost reply only enables original-ID queries.
  retryEvidence=null;
  selectRecord({request,applicationId,spugTaskId:null,createdAt:new Date().toISOString(),spugHistoryId:null,dispatchErrorCode:null,
    ...(automaticPlan?{automaticIncrementalPlan:automaticPlan}:{})});
  localStorage.setItem('spug-backup-original',JSON.stringify(active));
  pending=active;
  busy=true;problem('');render();
  try{
    const body=automaticPlan?{schemaVersion:'AutomaticIncrementalRequest/v1',operationId:request.operationId,applicationId,planDigest:automaticPlan.planDigest}:request;
    active=originalResponse(await api(automaticPlan?'/automatic-incremental':'/operations',body),request,applicationId);pending=active;localStorage.setItem('spug-backup-original',JSON.stringify(active));
    showResult(active);records=await api('/history');history();}
  catch(error){
    // Only an explicit, exact pre-admission rejection proves this POST made no reservation.
    if(automaticPlan&&error.status===409&&error.rejection?.accepted===false&&
      error.rejection.operationId===request.operationId&&error.rejection.applicationId===applicationId){
      pending=null;localStorage.removeItem('spug-backup-original');selectRecord(null);
      operationId='smallapp-'+crypto.randomUUID().replace(/-/g,'');
      await loadIncrementalPlan();showSimplePage('backup');
      problem(message(error.message)+' 已重新读取备份计划，请重新确认。');return;
    }
    // A lost HTTP reply queries the saved ID once; it never repeats the POST.
    try{active=originalResponse(await api('/operations/'+encodeURIComponent(request.operationId)),request,applicationId);pending=active;
      localStorage.setItem('spug-backup-original',JSON.stringify(active));showResult(active);}
    catch(queryError){problem(message(error.message)+' '+message(queryError.message)+' 请查询原编号。');showResult(active);}
  }
  finally{busy=false;render();}
}
// New submissions use the simple form's confirmed immutable request only.
$('check-unaccepted').addEventListener('click',async()=>{
  if($('check-unaccepted').disabled)return;
  const id=$('original-operation-id').value.trim();
  if(!/^[A-Za-z0-9][A-Za-z0-9_.:-]{7,159}$/.test(id)){problem('请填写完整的原操作编号。');return;}
  if(unresolvedOriginal() && pending.request.operationId!==id){problem('请先核对已保留的原编号：'+pending.request.operationId);return;}
  const original=pending?.request.operationId===id?pending:active?.request.operationId===id?active:null;
  if(original && (original.result || original.spugHistoryId || original.dispatchErrorCode || original.cancelledUnaccepted)){
    retryEvidence=null;problem(message('ORIGINAL_OPERATION_ALREADY_RECORDED'));render();return;
  }
  const request=original?{...original.request}:selectedRequest(id);
  const applicationId=original?.applicationId || selected().applicationId;
  retryEvidence=null;busy=true;problem('');render();
  try{
    const evidence=await checkUnaccepted(request,applicationId);
    selectRecord({request,applicationId,spugTaskId:null,createdAt:new Date().toISOString(),spugHistoryId:null,dispatchErrorCode:null});
    pending=active;operationId=id;localStorage.setItem('spug-backup-original',JSON.stringify(active));
    displayOriginalIdentity(active);
    retryEvidence=evidence;showResult(active);
    $('result-state').textContent='已核对未受理，可按原编号重试';
  }catch(error){problem(message(error.message));}
  finally{busy=false;render();}
});
function displayOriginalIdentity(record){
  $('application').value=record.applicationId;action=record.request.action;
  if(typeof syncSimpleIdentity==='function')syncSimpleIdentity(record);
}
$('cancel-unaccepted').addEventListener('click',async()=>{
  if($('cancel-unaccepted').disabled || !retryReady(active,retryEvidence))return;
  const original=active;
  if(unresolvedOriginal() && !sameRequest(pending.request,original.request))return;
  busy=true;retryEvidence=null;problem('');render();
  try{
    const value=originalResponse(await api('/cancel-unaccepted',original.request),original.request,original.applicationId);
    if(value.cancelledUnaccepted!==true || value.dispatchState!=='CANCELLED_UNACCEPTED')throw new Error('ENTRY_ORIGINAL_RESPONSE_MISMATCH');
    // Keep the server cancellation receipt locally as well as in history. Only
    // a durable fence, not a prior GET proof, unlocks the editable draft.
    pending=value;localStorage.setItem('spug-backup-original',JSON.stringify(value));
    selectRecord(null);operationId='smallapp-'+crypto.randomUUID().replace(/-/g,'');
    $('result-state').textContent='原请求已确认未受理并取消，可修改参数后重新确认';$('result-details').hidden=true;
    records=await api('/history');history();
  }catch(error){problem(message(error.message));}
  finally{busy=false;render();}
});
$('recover-reserved').addEventListener('click',async()=>{
  if($('recover-reserved').disabled)return;
  const original=active;busy=true;retryEvidence=null;problem('');render();
  try{
    const value=originalResponse(await api('/recover-reserved',original.request),original.request,original.applicationId);
    selectRecord(value);pending=value;localStorage.setItem('spug-backup-original',JSON.stringify(value));showResult(value);
  }catch(error){problem(message(error.message)+' 请查询原编号；不会自动再次派发。');}
  finally{busy=false;render();}
});
$('retry-original').addEventListener('click',async()=>{
  if($('retry-original').disabled || !retryReady(active,retryEvidence))return;
  await submitOriginal({...active.request},active.applicationId,true);
});
$('original-operation-id').addEventListener('input',()=>{retryEvidence=null;render();});
$('query').addEventListener('click',query);
$('refresh').addEventListener('click',refresh);
$('new-operation').addEventListener('click',()=>{
  if($('new-operation').disabled)return;
  retryEvidence=null;
  if(active && pending?.request.operationId===active.request.operationId){pending=null;localStorage.removeItem('spug-backup-original');}
  selectRecord(null);
  operationId='smallapp-'+crypto.randomUUID().replace(/-/g,'');$('result-state').textContent='尚未执行';$('result-details').hidden=true;render();
});
try{const original=localStorage.getItem('spug-backup-original');if(original){active=JSON.parse(original);pending=active;action=active.request.action;}}
catch(error){problem('浏览器原操作记录无法读取，请通过操作记录核查。');}
const initialRefresh = refresh();
