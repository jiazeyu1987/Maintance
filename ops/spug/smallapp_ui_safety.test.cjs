'use strict';
// State-machine/rendering contracts only. No browser E2E, executor or network calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function page() {
  class Element {
    constructor() { this.value=''; this.textContent=''; this.children=[]; this.disabled=false; this.hidden=false; this.dataset={}; this.listeners={}; }
    add(option) { this.children.push(option); if(this.children.length===1)this.value=option.value; }
    replaceChildren(...values) { this.children=[...values]; this.value=values[0]?.value||''; }
    append(...values) { this.children.push(...values); }
    setAttribute(name, value) { this[name]=value; }
    addEventListener(name, callback) { this.listeners[name]=callback; }
    get selectedOptions() { return this.children.filter(child=>child.value===this.value); }
    showModal() { this.open=true; }
    close() { this.open=false; }
  }
  const elements=new Map(), store=new Map();
  const get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  const buttons=['FULL','INCREMENTAL','RESTORE'].map(action=>Object.assign(new Element(),{dataset:{action}}));
  const context=vm.createContext({
    document:{hidden:false,getElementById:get,createElement:()=>new Element(),querySelectorAll:selector=>selector==='[data-action]'?buttons:[]},
    Option:class {constructor(text,value){this.textContent=text;this.value=value;}},
    localStorage:{getItem:key=>store.get(key)||null,setItem:(key,value)=>store.set(key,value),removeItem:key=>store.delete(key)},
    crypto:{randomUUID:()=> '01234567-1234-1234-1234-012345678901'},
    setTimeout,clearTimeout,AbortController,Date,
  });
  const run=code=>vm.runInContext(code,context);
  const source=fs.readFileSync(path.join(__dirname,'smallapp-ui','app.js'),'utf8').replace('const initialRefresh = refresh();','const initialRefresh = Promise.resolve();');
  run(source);
  const simple=fs.readFileSync(path.join(__dirname,'smallapp-ui','simple.js'),'utf8');
  run(simple.slice(0,simple.indexOf('\nsetInterval(')));
  for(const [id,values] of Object.entries({
    'simple-product':['product'], 'simple-server':['server'], 'simple-mode':['safe','fast'], 'simple-type':['FULL','INCREMENTAL'],
    'simple-target':['target-server'], 'simple-restore-mode':['fresh','replace'], 'application':['app'],
  })) for(const value of values)get(id).add(new context.Option(value,value));
  run(`
    simpleConfig={nas:'registered-nas',servers:[{address:'target-server',name:'Target'}],bindings:[{product:'product',server:'server',mode:'safe',applicationId:'app',targetServers:{'target-server':'target-ref'},overwriteTargetServers:{},selectable:true}]};
    options=[{applicationId:'app',sourceConfigRef:'source-ref',validated:{fullReady:true,parentChainRefs:['parent-ref'],recoveryPointRefs:['point-ref'],freshTargetConfigRefs:['target-ref']}}];
    S('simple-nas').value='registered-nas';operationId='test-operation-123';render();
    api=async()=>{throw new Error('UNEXPECTED_TEST_API_CALL');};
  `);
  return {run,get,context,buttons,store};
}

const record=(id='original-operation-123')=>({applicationId:'app',request:{schemaVersion:'SmallAppBackupUiRequest/v1',operationId:id,
  action:'FULL',sourceConfigRef:'source-ref',parentChainRef:null,recoveryPointRef:null,targetConfigRef:null},
  result:{state:'RUNNING',errorCode:null,logRefs:[],resultRef:null}});

test('incremental chooses the newest accepted point on this source regardless of history order',()=>{
  const p=page();
  p.context.history=[['old-full','2026-10-22T00:00:00Z','FULL'],['new-increment','2026-10-23T01:00:00Z','INCREMENTAL'],['new-full','2026-10-23T00:00:00Z','FULL']]
    .map(([id,createdAt,action])=>({...record(id),createdAt,request:{...record(id).request,action}}));
  p.run("records=history;selected().validated.parentChainRefs=['old-full','new-full','new-increment'];");
  assert.equal(p.run('latestSimpleParent()'),'new-increment');
  p.run("selected().validated.parentChainRefs=['old-full','new-full'];");
  assert.equal(p.run('latestSimpleParent()'),'new-full');
  p.run("selected().validated.parentChainRefs.push('missing-history');");
  assert.equal(p.run('latestSimpleParent()'),'');
});

test('target choices exclude unregistered and already used targets before submission',()=>{
  const p=page();
  p.run("simpleConfig.servers.push({address:'missing',name:'Missing'});simpleRestoring=true;action='RESTORE';render();");
  assert.equal(p.get('simple-target').children.find(o=>o.value==='missing').disabled,true);
  p.run("S('simple-target').value='target-server';selected().validated.freshTargetConfigRefs=[];render();");
  assert.equal(p.get('simple-target').value,'');
  assert.equal(p.get('simple-target').children.find(o=>o.value==='target-server').disabled,true);
  assert.equal(p.get('simple-submit').disabled,true);
});

test('dispatch history prevents offering an already consumed target from a stale controller catalogue',()=>{
  const p=page();p.context.original=record('used-target-operation');
  p.run("original.request.action='RESTORE';original.request.targetConfigRef='target-ref';original.spugHistoryId=123;records=[original];render();");
  assert.equal(p.get('simple-target').children.find(o=>o.value==='target-server').disabled,true);
});

test('registered replacement stays selectable after a previous successful restore',()=>{
  const p=page();p.context.original=record('previous-replacement');
  p.run(`simpleConfig.bindings[0].overwriteTargetServers={'target-server':'replacement-ref'};
    selected().validated.freshTargetConfigRefs.push('replacement-ref');
    original.request.action='RESTORE';original.request.targetConfigRef='replacement-ref';original.spugHistoryId=123;records=[original];
    S('simple-restore-mode').value='replace';simpleRestoring=true;action='RESTORE';render();`);
  assert.equal(p.get('simple-target').children.find(o=>o.value==='target-server').disabled,false);
  p.run("selected().validated.freshTargetConfigRefs=['target-ref'];render();");
  assert.equal(p.get('simple-target').children.find(o=>o.value==='target-server').disabled,true);
});

test('replacement requires an explicit checkbox and retains the exact confirmed target',async()=>{
  const p=page();
  p.run(`simpleConfig.bindings[0].overwriteTargetServers={'target-server':'replacement-ref'};
    selected().validated.freshTargetConfigRefs.push('replacement-ref');S('simple-restore-mode').value='replace';
    simpleRestoring=true;action='RESTORE';render();S('simple-package').value='point-ref';S('simple-target').value='target-server';S('simple-package').onchange();
    globalThis.submissions=[];submitOriginal=async request=>{submissions.push(request);};progress=async()=>{};`);
  p.get('simple-submit').onclick();
  assert.equal(p.get('replace-confirm-field').hidden,false);
  assert.equal(p.get('simple-confirm-submit').disabled,true);
  assert.match(p.get('confirm-summary').textContent,/覆盖现有小程序/);
  await p.get('simple-confirm-submit').onclick();
  assert.equal(p.run('submissions.length'),0);
  p.get('replace-confirm').checked=true;p.get('replace-confirm').onchange();
  assert.equal(p.get('simple-confirm-submit').disabled,false);
  await p.get('simple-confirm-submit').onclick();
  assert.equal(p.run('submissions.length'),1);
  assert.equal(p.run('submissions[0].targetConfigRef'),'replacement-ref');
});

test('refresh configuration reloads registrations before refreshing the selected application',async()=>{
  const p=page();
  p.run("globalThis.calls=[];api=async path=>{calls.push(path);return {...simpleConfig,bindings:simpleConfig.bindings.map(b=>({...b,targetServers:{'target-server':'new-target'}}))};};chooseSimple=async()=>{calls.push(currentBinding().targetServers['target-server']);};");
  await p.get('simple-refresh').onclick();
  assert.equal(p.run("JSON.stringify(calls)"),JSON.stringify(['/simple-config','new-target']));
  p.run("api=async()=>{throw Error('CONFIGURATION_MISSING');};");
  await p.get('simple-refresh').onclick();
  assert.equal(p.run('simpleConfig'),null);
  assert.equal(p.get('simple-submit').disabled,true);
  assert.match(p.get('simple-status').textContent,/配置读取失败/);
});

test('unregistered modes are explicitly unavailable without switching the chosen mode',()=>{
  const p=page();
  p.run("S('simple-mode').value='fast';simpleRestoring=true;action='RESTORE';render();");
  const fast=p.get('simple-mode').children.find(option=>option.value==='fast');
  assert.equal(fast.disabled,true);
  assert.match(fast.textContent,/未登记/);
  assert.equal(p.get('simple-mode').value,'fast');
  assert.equal(p.get('simple-submit').disabled,true);
  assert.equal(p.get('simple-status').dataset.state,'blocked');
  assert.match(p.get('simple-status').textContent,/尚未登记快速模式/);
  assert.match(p.get('simple-status').textContent,/手动选择.*安全模式/);
  p.get('simple-submit').onclick();
  assert.equal(p.run('confirmation'),null);
});

test('restore stays blocked until a package is explicitly selected and explains why',()=>{
  const p=page();p.run("simpleRestoring=true;action='RESTORE';render();");
  assert.equal(p.get('simple-submit').disabled,true);
  assert.equal(p.get('simple-submit').title,'请选择备份包。');
  assert.equal(p.get('simple-status').dataset.state,'blocked');
  p.get('simple-submit').onclick();assert.equal(p.run('confirmation'),null);
  p.run("S('simple-package').value='point-ref';S('simple-target').value='target-server';S('simple-package').onchange();");
  assert.equal(p.get('simple-submit').disabled,false);
  assert.equal(p.get('simple-submit').title,'');
  assert.equal(p.get('simple-status').dataset.state,'ready');
  p.get('simple-submit').onclick();
  assert.equal(p.run('confirmation.request.recoveryPointRef'),'point-ref');
});

test('history details show original point and target after the draft target rotates',()=>{
  const p=page();p.context.original=record();
  p.run(`original.request.action='RESTORE';original.request.recoveryPointRef='historical-point';original.request.targetConfigRef='historical-target';
    simpleConfig.bindings[0].mode='fast';simpleConfig.bindings[0].targetServers['target-server']='new-draft-target';selectRecord(original);render();`);
  const details=p.get('simple-operation-details');
  assert.equal(details.hidden,false);
  const text=details.children.map(item=>item.textContent).join('\n');
  assert.match(text,/historical-point/);assert.match(text,/historical-target/);
  assert.match(text,/快速模式 · 跳过核验/);assert.doesNotMatch(text,/new-draft-target/);
  p.run('selectRecord(null);render();');assert.equal(details.hidden,true);assert.equal(details.children.length,0);
});

test('retired source remains in history while new drafts select its explicit successor',()=>{
  const p=page();
  p.run(`simpleConfig.bindings.unshift({...simpleConfig.bindings[0],applicationId:'retired-app',selectable:false});
    records=[{...${JSON.stringify(record('old-source-operation'))},applicationId:'retired-app'}];render();`);
  assert.equal(p.run('currentBinding().applicationId'),'app');
  assert.equal(p.get('simple-history').children.length,1);
  assert.match(p.get('simple-history').children[0].children[0].textContent,/old-source-operation/);
});

test('a new reservation clears the previous completed result before its POST returns',()=>{
  const p=page();p.context.previous=record('completed-operation-123');p.context.next=record('new-operation-123');
  p.run(`previous.result.state='SUCCEEDED';selectRecord(previous);render();`);
  assert.equal(p.get('simple-result').textContent,'执行完成');
  p.run(`delete next.result;selectRecord(next);render();`);
  assert.equal(p.get('simple-result').textContent,'已保留编号，尚未查询执行回执');
  assert.equal(p.get('operation-reference').textContent,'new-operation-123');
  p.run('selectRecord(null);render();');
  assert.equal(p.get('simple-result').textContent,'尚未执行');
});

test('a pending dispatch reservation is a status while actual failures remain errors',()=>{
  const p=page();p.context.original=record();
  p.run("original.result.errorCode='SPUG_DISPATCH_RESERVED';selectRecord(original);render();");
  assert.match(p.get('simple-logs').textContent,/状态：.*等待执行回执/);
  assert.doesNotMatch(p.get('simple-logs').textContent,/错误：/);
  p.run("original.result.errorCode='ORIGINAL_OWNER_RESULT_NOT_READY';render();");
  assert.match(p.get('simple-logs').textContent,/状态：.*原任务正在执行/);
  assert.doesNotMatch(p.get('simple-logs').textContent,/错误：/);
  p.run("original.result.state='FAILED';render();");
  assert.match(p.get('simple-logs').textContent,/错误：.*ORIGINAL_OWNER_RESULT_NOT_READY/);
  p.run("original.result.errorCode='SPUG_DISPATCH_RESERVED';");
  p.run("original.result.state='FAILED';render();");
  assert.match(p.get('simple-logs').textContent,/错误：.*SPUG_DISPATCH_RESERVED/);
  p.run("original.result.state='RUNNING';original.result.errorCode='BRIDGE_UNAVAILABLE_OR_RESPONSE_INVALID';render();");
  assert.match(p.get('simple-logs').textContent,/错误：.*BRIDGE_UNAVAILABLE_OR_RESPONSE_INVALID/);
});

test('diagnostic request controls are read-only and confirmation submits the exact displayed immutable request',async()=>{
  const p=page();
  p.run(`simpleRestoring=true;action='RESTORE';render();S('simple-package').value='point-ref';S('simple-target').value='target-server';S('simple-package').onchange();`);
  for(const id of ['application','source','parent','point','target'])assert.equal(p.get(id).disabled,true);
  assert.ok(p.buttons.every(button=>button.disabled));
  assert.equal(p.get('simple-submit').disabled,false);
  // A stale diagnostic mirror must not select a different restoration point.
  p.get('point').value='obsolete-diagnostic-point';
  p.get('simple-submit').onclick();
  assert.equal(p.run('Object.isFrozen(confirmation.request)'),true);
  assert.equal(p.run('confirmation.request.recoveryPointRef'),'point-ref');
  assert.match(p.get('confirm-summary').textContent,/point-ref/);
  assert.doesNotMatch(p.get('confirm-summary').textContent,/obsolete/);
  assert.equal(p.get('simple-restore-tab').disabled,true);
  assert.equal(p.get('refresh').disabled,true);
  p.run('globalThis.expected=confirmation.request; submitOriginal=async(request,applicationId)=>{globalThis.captured={request,applicationId};};');
  await p.get('simple-confirm-submit').onclick();
  assert.equal(p.run('captured.request===expected'),true);
  assert.equal(p.run('captured.applicationId'),'app');
});

test('confirmation refuses a draft altered after the dialog opened',async()=>{
  const p=page();p.get('simple-submit').onclick();
  p.run("S('simple-type').value='INCREMENTAL';globalThis.submitted=false;submitOriginal=async()=>{submitted=true;};");
  await p.get('simple-confirm-submit').onclick();
  assert.equal(p.run('submitted'),false);
  assert.match(p.get('problem').textContent,/重新确认/);
});

test('late original query cannot replace another operation or its pending original',async()=>{
  const p=page();p.context.original=record();p.context.other=record('other-operation-123');
  p.run('selectRecord(original);pending=original;api=()=>new Promise(resolve=>{globalThis.resolveQuery=resolve;});');
  const inFlight=p.run('query()');
  assert.equal(p.get('simple-backup-tab').disabled,true);
  p.run('selectRecord(other);resolveQuery({...original,result:{state:"FAILED",logRefs:[]}});');
  await inFlight;
  assert.equal(p.run('active.request.operationId'),'other-operation-123');
  assert.equal(p.run('pending.result.state'),'RUNNING');
});

test('late telemetry is dropped even after switching away and back to the same ID',async()=>{
  const p=page();p.context.original=record();p.context.other=record('other-operation-123');
  p.run('selectRecord(original);api=()=>new Promise(resolve=>{globalThis.resolveProgress=resolve;});');
  const inFlight=p.run('progress()');
  p.run('selectRecord(other);selectRecord(original);resolveProgress({operationId:original.request.operationId,steps:[{name:"stale"}]});');
  await inFlight;
  assert.equal(p.run('telemetry'),null);
});

test('switching to a completed historical operation loads its logs while older progress is pending',async()=>{
  const p=page();p.context.original=record();p.context.other=record('completed-operation-123');
  p.run(`other.result={state:'FAILED',logRefs:[]};selectRecord(original);
    api=async(path)=>{
      if(path==='/progress/'+original.request.operationId)return new Promise(resolve=>{globalThis.resolveOld=resolve;});
      if(path==='/operations/'+other.request.operationId)return other;
      if(path==='/history')return [];
      if(path==='/progress/'+other.request.operationId)return {operationId:other.request.operationId,state:'FAILED',steps:[]};
      throw new Error('UNEXPECTED_TEST_API_CALL');
    };`);
  const older=p.run('progress()');
  await p.run('openRecord(other)');
  assert.equal(p.run('telemetry.operationId'),'completed-operation-123');
  p.run('resolveOld({operationId:original.request.operationId,state:"RUNNING",steps:[]});');
  await older;
  assert.equal(p.run('telemetry.operationId'),'completed-operation-123');
});

test('history clicks are mutually exclusive with queries and unresolved pending IDs survive drafts',async()=>{
  const p=page();p.context.original=record();p.context.other=record('other-operation-123');
  p.run('selectRecord(original);pending=original;busy=true;');
  await p.run('openRecord(other)');
  assert.equal(p.run('active.request.operationId'),'original-operation-123');
  p.run('busy=false;selectRecord({...other,result:{state:"FAILED",logRefs:[]}});render();');
  assert.equal(p.get('new-operation').disabled,true);
  assert.equal(p.get('simple-type').disabled,true);
  await p.run('chooseSimple()');
  assert.equal(p.run('pending.request.operationId'),'original-operation-123');
});

test('refresh failure invalidates prior admission until a later successful refresh',async()=>{
  const p=page();
  assert.equal(p.get('simple-submit').disabled,false);
  p.run('api=async()=>{throw new Error("ENTRY_REQUEST_TIMEOUT");};');
  await p.run('refresh()');
  assert.equal(p.run('selected().validated'),null);
  assert.equal(p.get('simple-submit').disabled,true);
  assert.match(p.get('problem').textContent,/旧准入已失效/);
  p.run(`api=async(path)=>path==='/history'?[]:{applications:[{applicationId:'app',sourceConfigRef:'source-ref',displayName:'app',validated:{fullReady:true,parentChainRefs:[],recoveryPointRefs:[],freshTargetConfigRefs:[]}}],initialOperationIds:{},registrationVersions:{}};`);
  await p.run('refresh()');
  assert.equal(p.get('simple-submit').disabled,false);
});

test('unconfirmed terminal step is explicit and never shows a fabricated duration',()=>{
  const p=page();p.context.original=record();
  p.run(`selectRecord(original);telemetry={operationId:original.request.operationId,state:'TERMINAL_UNKNOWN',steps:[{name:'database-restore',state:'UNCONFIRMED',startedAt:'2026-10-22T01:00:00Z',finishedAt:null,elapsedSeconds:null}]};drawProgress();`);
  const step=p.get('steps').children[0];
  assert.match(step.children[1].textContent,/状态未确认/);
  assert.match(step.children[2].textContent,/结束 —.*耗时 —/);
  assert.match(p.get('simple-logs').textContent,/结束回执缺失/);
});

test('unaccepted check uses pending A identity after opening unrelated historical B',async()=>{
  const p=page();p.context.original=record();delete p.context.original.result;
  p.context.other={...record('history-B-123'),applicationId:'other-app',request:{...record().request,
    operationId:'history-B-123',action:'RESTORE',sourceConfigRef:'other-source',recoveryPointRef:'other-point',targetConfigRef:'other-target'},
    result:{state:'FAILED',logRefs:[]}};
  p.run(`pending=original;selectRecord(other);action='RESTORE';
    options.push({applicationId:'other-app',sourceConfigRef:'other-source',validated:{fullReady:true,parentChainRefs:[],recoveryPointRefs:['other-point'],freshTargetConfigRefs:['other-target']}});
    S('application').add(new Option('other-app','other-app'));S('application').value='other-app';
    api=async(path)=>{globalThis.checked=JSON.parse(decodeURIComponent(path.split('?request=')[1]));return {request:checked,applicationId:'app',retryAllowed:true};};
    render();S('original-operation-id').value=original.request.operationId;`);
  await p.get('check-unaccepted').listeners.click();
  assert.deepEqual(JSON.parse(p.run('JSON.stringify(checked)')),p.context.original.request);
  assert.equal(p.run('pending.applicationId'),'app');
  assert.equal(p.get('application').value,'app');
  assert.equal(p.run('action'),'FULL');
  assert.equal(p.get('retry-original').disabled,false);
});

test('cancellation unlocks draft only after durable exact original cancellation receipt',async()=>{
  const p=page();p.context.original=record();delete p.context.original.result;
  p.run(`selectRecord(original);pending=original;retryEvidence={request:original.request,applicationId:'app',retryAllowed:true};
    api=async(path,request)=>{if(path==='/history')return [];globalThis.cancelRequest=request;return {...original,cancelledUnaccepted:true,dispatchState:'CANCELLED_UNACCEPTED',result:null};};render();`);
  await p.get('cancel-unaccepted').listeners.click();
  assert.deepEqual(JSON.parse(p.run('JSON.stringify(cancelRequest)')),p.context.original.request);
  assert.equal(p.run('active'),null);
  assert.equal(p.run('unresolvedOriginal()'),false);
  assert.equal(p.get('simple-type').disabled,false);
  assert.equal(JSON.parse(p.store.get('spug-backup-original')).dispatchState,'CANCELLED_UNACCEPTED');
});

test('cancellation rejection or ambiguous response retains the unresolved original',async()=>{
  for(const behavior of ['throw new Error("ENTRY_REQUEST_TIMEOUT")','return {...original,cancelledUnaccepted:false}']){
    const p=page();p.context.original=record();delete p.context.original.result;
    p.run(`selectRecord(original);pending=original;retryEvidence={request:original.request,applicationId:'app',retryAllowed:true};api=async()=>{${behavior};};render();`);
    await p.get('cancel-unaccepted').listeners.click();
    assert.equal(p.run('pending.request.operationId'),p.context.original.request.operationId);
    assert.equal(p.run('unresolvedOriginal()'),true);
    assert.equal(p.get('simple-type').disabled,true);
  }
});

test('explicit reserved recovery uses full original request and never retries a timeout',async()=>{
  const p=page();p.context.original={...record(),dispatchState:'RESERVED'};
  p.run(`selectRecord(original);pending=original;globalThis.calls=[];
    api=async(path,request)=>{calls.push({path,request});throw new Error('ENTRY_REQUEST_TIMEOUT');};render();`);
  assert.equal(p.get('recover-reserved').disabled,false);
  await p.get('recover-reserved').listeners.click();
  assert.equal(p.run('calls.length'),1);
  assert.equal(p.run('calls[0].path'),'/recover-reserved');
  assert.deepEqual(JSON.parse(p.run('JSON.stringify(calls[0].request)')),p.context.original.request);
  assert.equal(p.run('pending.request.operationId'),p.context.original.request.operationId);
  p.run(`active={...original,dispatchState:'DISPATCHING'};render();`);
  assert.equal(p.get('recover-reserved').disabled,true);
});

test('cancelled history displays not executed and never queries progress or accumulates time',async()=>{
  const p=page();p.context.original={...record(),result:null,cancelledUnaccepted:true,dispatchState:'CANCELLED_UNACCEPTED'};
  p.run(`selectRecord(original);globalThis.calls=[];api=async(path)=>{calls.push(path);throw new Error('UNEXPECTED_TELEMETRY');};render();`);
  await p.run('progress()');
  assert.equal(p.run('calls.length'),0);
  assert.equal(p.get('total-time').textContent,'—');
  assert.match(p.get('steps').textContent,/未执行/);
  assert.match(p.get('simple-logs').textContent,/未执行/);
});
