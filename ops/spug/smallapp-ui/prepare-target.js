'use strict';

function createPrepareTarget({document,api,storage,randomId,selection,isBusy,onReady,onBeforeRender=()=>{},onChange=()=>{},onDispatch=()=>{}}) {
  const host='172.30.30.59',storageKey='spug.prepare-target.operation.v1';
  const stageNames={dependencies:'准备最小依赖',cleanup:'清理旧环境',initialize:'初始化空目标'};
  const stateNames={PENDING:'等待执行',RUNNING:'执行中',READY:'空目标已就绪',FAILED:'失败',UNKNOWN:'执行结果未知',SUCCEEDED:'已完成'};
  const stages=Object.keys(stageNames),get=id=>document.getElementById(id);
  let configuration=null,operation=null,plan=null,working=false,querying=false,error='',historyError='',history=[],storageError=false;
  const refreshed=new Set();
  const textError=value=>String(value?.message||value||'PREPARE_REQUEST_FAILED');
  const validId=value=>typeof value==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.:-]{7,159}$/.test(value);
  const validRef=value=>typeof value==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$/.test(value);
  const current=()=>{const s=selection();return {applicationId:s.applicationId,recoveryPointRef:s.recoveryPointRef};};
  const same=(left,right)=>left?.applicationId===right?.applicationId&&left?.recoveryPointRef===right?.recoveryPointRef;
  const blocked=()=>storageError||working||!!plan||!!operation&&operation.state!=='READY';
  const eligible=()=>{const s=selection();return s.restoring&&s.host===host&&validRef(s.applicationId)&&validRef(s.recoveryPointRef);};
  function validateRecord(value,expected) {
    if(!value||!validId(value.operationId)||value.host!==host||!validRef(value.applicationId)||!validRef(value.recoveryPointRef)||
      !['PENDING','RUNNING','READY','FAILED','UNKNOWN'].includes(value.state)||!Array.isArray(value.stages)||
      value.stages.length!==3||value.stages.some((stage,index)=>stage.name!==stages[index]||!Object.hasOwn(stateNames,stage.state))||
      expected&&(value.operationId!==expected.operationId||!same(value,expected))||
      value.state==='READY'&&(!validRef(value.targetConfigRef)||value.stages.some(stage=>stage.state!=='SUCCEEDED')))
      throw new Error('PREPARE_RESULT_INVALID');
    return value;
  }
  function save(value) {
    const persisted={operationId:value.operationId,applicationId:value.applicationId,recoveryPointRef:value.recoveryPointRef};
    storage.setItem(storageKey,JSON.stringify(persisted));
    if(storage.getItem(storageKey)!==JSON.stringify(persisted))throw new Error('PREPARE_OPERATION_STORAGE_FAILED');
  }
  function provisional(value) {
    return {...value,host,state:'UNKNOWN',stages:stages.map(name=>({name,state:'PENDING'})),targetConfigRef:null};
  }
  function render() {
    onBeforeRender();
    const s=selection();
    get('prepare-target-field').hidden=!s.restoring;
    const note=error||(configuration===null?'正在读取空目标准备配置…':!configuration.configured?
      '准备功能未配置：'+(configuration.errorCode||'PREPARE_NOT_CONFIGURED'):
      s.host!==host?'空目标准备仅支持备份服务器 172.30.30.59。':!eligible()?'请选择应用和备份点。':
      operation&&operation.state!=='READY'?'已有准备任务，请查看执行进度。':'准备依赖、清理旧环境并初始化空目标。');
    get('prepare-target-status').textContent=note;
    get('prepare-target-start').disabled=!configuration?.configured||!eligible()||blocked()||isBusy();
    get('prepare-target-confirm-submit').disabled=working||!plan||!get('prepare-target-agree').checked;
    get('prepare-target-query').disabled=querying||!operation;
    get('prepare-target-progress-section').hidden=!operation;
    if(operation) {
      const rows=[stateNames[operation.state]||'执行结果未知',`服务器：${host}`,`任务：${operation.operationId}`,
        `备份点：${operation.recoveryPointRef}`];
      for(const stage of operation.stages)rows.push(`${stageNames[stage.name]}：${stateNames[stage.state]||'状态未知'}${stage.errorCode?' · '+stage.errorCode:''}`);
      if(operation.errorCode)rows.push('原因：'+operation.errorCode);
      if(error)rows.push(error);
      if(operation.state==='READY')rows.push('可恢复目标：'+operation.targetConfigRef);
      if(operation.state==='FAILED')rows.push('本次准备已停止，保留现场和原任务记录。');
      if(operation.state==='UNKNOWN')rows.push('请查询原任务，暂不重新提交清理。');
      get('prepare-target-progress').textContent=rows.join('\n');
    }
    const list=get('prepare-target-history');list.replaceChildren();
    for(const item of history) {
      const row=document.createElement('div');row.className='history-row';
      row.textContent=`${item.operationId} · ${stateNames[item.state]} · ${item.recoveryPointRef}`;list.append(row);
    }
    get('prepare-target-history-status').textContent=historyError||(history.length?'':'暂无空目标准备记录。');
    onChange();
  }
  async function loadHistory() {
    try {
      const value=await api('/prepare-target/history');
      if(!Array.isArray(value))throw new Error('PREPARE_HISTORY_INVALID');
      history=value.map(item=>validateRecord(item));historyError='';
    } catch(cause) {historyError='准备记录读取失败：'+textError(cause);}
    render();
  }
  async function apply(value) {
    operation=validateRecord(value,operation);error='';render();
    if(operation.state==='READY'&&!refreshed.has(operation.operationId)) {
      refreshed.add(operation.operationId);
      try {await onReady(operation);}
      catch(cause) {error='空目标已就绪，但恢复选项刷新失败：'+textError(cause);render();}
    }
  }
  async function query() {
    if(!operation||querying)return;
    querying=true;render();
    try {await apply(await api('/prepare-target/operations/'+encodeURIComponent(operation.operationId)));}
    catch(cause) {operation={...operation,state:'UNKNOWN'};error='原任务查询失败：'+textError(cause);}
    finally {querying=false;render();}
    await loadHistory();
  }
  async function initialize() {
    try {
      const stored=storage.getItem(storageKey);
      if(stored) {
        const value=JSON.parse(stored);
        if(!validId(value.operationId)||!validRef(value.applicationId)||!validRef(value.recoveryPointRef))throw new Error('PREPARE_OPERATION_STORAGE_INVALID');
        operation=provisional(value);
      }
    } catch(cause) {storageError=true;error='原准备任务记录不可读取：'+textError(cause);}
    try {
      configuration=await api('/prepare-target/config');
      if(!configuration||typeof configuration.configured!=='boolean'||configuration.host!==host)throw new Error('PREPARE_CONFIGURATION_INVALID');
    } catch(cause) {configuration={configured:false,host,errorCode:textError(cause)};}
    render();await loadHistory();if(operation)await query();
  }
  async function preview() {
    if(!configuration?.configured||!eligible()||blocked()||isBusy()){render();return;}
    const request=current();working=true;error='';render();
    try {
      const value=await api('/prepare-target/preview',request);
      if(value?.host!==host||!same(value,request)||!/^[a-f0-9]{64}$/.test(value.planDigest)||
        !Array.isArray(value.cleanupSummary)||!value.cleanupSummary.length||!Array.isArray(value.preserveSummary)||!value.preserveSummary.length||
        [...value.cleanupSummary,...value.preserveSummary].some(item=>typeof item!=='string')||
        JSON.stringify(value.stages)!==JSON.stringify(stages))throw new Error('PREPARE_PREVIEW_INVALID');
      if(!eligible()||!same(request,current()))throw new Error('操作参数已变化，请重新预览。');
      plan=Object.freeze({...value});
      get('prepare-target-summary').textContent=`目标服务器：${host}\n备份点：${plan.recoveryPointRef}\n\n将清理：\n${plan.cleanupSummary.join('\n')}\n\n将保留：\n${plan.preserveSummary.join('\n')}`;
      get('prepare-target-agree').checked=false;get('prepare-target-confirm').showModal();
    } catch(cause) {error='准备预览失败：'+textError(cause);}
    finally {working=false;render();}
  }
  function cancel() {if(working)return;plan=null;get('prepare-target-confirm').close();render();}
  async function submit() {
    if(working||!plan||!get('prepare-target-agree').checked)return;
    if(!eligible()||!same(plan,current())||isBusy()) {cancel();error='操作参数或执行状态已变化，请重新预览。';render();return;}
    const request={operationId:randomId(),applicationId:plan.applicationId,recoveryPointRef:plan.recoveryPointRef,planDigest:plan.planDigest,confirmed:true};
    if(!validId(request.operationId)){error='PREPARE_OPERATION_ID_INVALID';render();return;}
    try {save(request);}catch(cause){storageError=true;error='无法保存原任务编号，未提交：'+textError(cause);render();return;}
    operation=provisional(request);working=true;plan=null;error='';get('prepare-target-confirm').close();render();onDispatch();
    try {await apply(await api('/prepare-target/operations',request));}
    catch(cause) {error='准备提交结果未知，请查询原任务：'+textError(cause);}
    finally {working=false;render();}
    await loadHistory();
  }
  get('prepare-target-start').onclick=preview;
  get('prepare-target-query').onclick=query;
  get('prepare-target-history-refresh').onclick=loadHistory;
  get('prepare-target-confirm-submit').onclick=submit;
  get('prepare-target-cancel').onclick=cancel;
  get('prepare-target-agree').onchange=render;
  get('prepare-target-confirm').oncancel=event=>{event.preventDefault();cancel();};
  return {initialize,preview,submit,query,render,blocked,loadHistory,poll:async()=>{if(operation&&['PENDING','RUNNING','UNKNOWN'].includes(operation.state))await query();}};
}

if(typeof module!=='undefined'&&module.exports)module.exports={createPrepareTarget};
else {
  const previousPrepareRender=render;
  const prepareTarget=createPrepareTarget({document,api:(...args)=>api(...args),storage:localStorage,
    randomId:()=> 'prepare-'+crypto.randomUUID(),
    selection:()=>({restoring:simpleRestoring,host:S('simple-target').value,
      applicationId:currentBinding()?.applicationId,recoveryPointRef:S('simple-package').value}),
    isBusy:()=>simpleInitializing||switching||interactionLocked()||!!unresolvedOriginal()||!!active&&!resolvedRecord(active),
    onReady:async()=>{await refreshSimpleConfiguration();},
    onDispatch:()=>{closeCatalogRestore(false);showSimplePage('progress',true);},
    onBeforeRender:()=>{
      const prior=S('simple-target').value;previousPrepareRender();
      if(simpleRestoring){
        const target=[...S('simple-target').options].find(option=>option.value==='172.30.30.59');
        if(target){
          if(target.disabled)target.textContent='备份服务器　172.30.30.59（需准备空目标）';
          target.disabled=false;if(prior===target.value)S('simple-target').value=prior;
        }
      }
    },
    onChange:()=>{if(prepareTarget.blocked()){S('simple-submit').disabled=true;S('submit').disabled=true;}}
  });
  render=function(){prepareTarget.render();};
  prepareTarget.initialize();
  setInterval(()=>{if(!document.hidden)prepareTarget.poll();},5000);
}
