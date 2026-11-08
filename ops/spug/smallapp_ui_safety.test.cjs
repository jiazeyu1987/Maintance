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
    appendChild(value) { this.append(value); }
    insertBefore(value,before) { this.children.splice(Math.max(0,this.children.indexOf(before)),0,value); }
    focus() { this.focused=true; }
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
    crypto:{randomUUID:()=> 'afdecba7-abcd-abcd-abcd-afdecba789ab'},
    setTimeout,clearTimeout,AbortController,Date,
  });
  const run=code=>vm.runInContext(code,context);
  const source=fs.readFileSync(path.join(__dirname,'smallapp-ui','app.js'),'utf8').replace('const initialRefresh = refresh();','const initialRefresh = Promise.resolve();');
  run(source);
  const requestApi=run('api');
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
  const start=()=>{run('simpleConfig=null;');return run(simple.slice(simple.indexOf('(async()=>{',simple.indexOf('\nsetInterval('))));};
  return {run,get,context,buttons,store,start,requestApi};
}

const record=(id='original-operation-123')=>({applicationId:'app',request:{schemaVersion:'SmallAppBackupUiRequest/v1',operationId:id,
  action:'FULL',sourceConfigRef:'source-ref',parentChainRef:null,recoveryPointRef:null,targetConfigRef:null},
  result:{state:'RUNNING',errorCode:null,logRefs:[],resultRef:null}});

function requestTimers(p){
  const timers=[],cleared=[];
  p.store.set('token','local-request-contract-only');
  p.context.setTimeout=(callback,milliseconds)=>{const timer={callback,milliseconds};timers.push(timer);return timer;};
  p.context.clearTimeout=timer=>cleared.push(timer);
  return {timers,cleared};
}

test('only automatic plan GET and automatic submission POST have a 60 second request deadline',async()=>{
  const p=page(),{timers,cleared}=requestTimers(p);
  p.context.fetch=async()=>({ok:true,json:async()=>({})});
  for(const [url,body,milliseconds] of [
    ['/incremental-plan?applicationId=app',undefined,60000],['/incremental-plan',undefined,60000],
    ['/automatic-incremental',{operationId:'deadline-test'},60000],
    ['/automatic-incremental',undefined,20000],['/incremental-plan?applicationId=app',{},20000],
    ['/incremental-plan-other?applicationId=app',undefined,20000],
    ['/operations',{},20000],['/operations/original-operation-123',undefined,20000],
    ['/progress/original-operation-123',undefined,20000],['/history',undefined,20000],
  ]){
    await p.requestApi(url,body);
    assert.equal(timers.at(-1).milliseconds,milliseconds,url);
    assert.equal(cleared.at(-1),timers.at(-1),url);
  }
});

test('automatic request deadline covers response body consumption and always clears its timer',async()=>{
  const p=page(),{timers,cleared}=requestTimers(p);
  let bodyReading;
  const started=new Promise(resolve=>{bodyReading=resolve;});
  p.context.fetch=async(_url,options)=>({ok:true,json:()=>new Promise((_resolve,reject)=>{
    options.signal.addEventListener('abort',()=>reject(Object.assign(new Error('aborted body'),{name:'AbortError'})));
    bodyReading();
  })});
  const request=p.requestApi('/incremental-plan?applicationId=app');
  const rejected=assert.rejects(request,/ENTRY_REQUEST_TIMEOUT/);
  await started;
  assert.equal(timers[0].milliseconds,60000);
  assert.equal(cleared.length,0);
  timers[0].callback();await rejected;
  assert.deepEqual(cleared,[timers[0]]);
});

test('automatic POST deadline and failed follow-up query retain the exact original without another POST',async()=>{
  const p=page();planApi(p);p.get('simple-type').value='INCREMENTAL';await p.get('simple-type').onchange();
  p.get('simple-submit').onclick();const original=JSON.parse(p.run('JSON.stringify(confirmation.request)'));
  const {timers,cleared}=requestTimers(p),calls=[];
  p.context.api=p.requestApi;
  p.context.fetch=async(url,options)=>{
    calls.push({url,method:options.method});
    if(options.method==='POST')return new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>
      reject(Object.assign(new Error('aborted submission'),{name:'AbortError'}))));
    throw new Error('BRIDGE_TIMEOUT');
  };
  const submission=p.get('simple-confirm-submit').onclick();
  assert.equal(timers[0].milliseconds,60000);
  assert.equal(p.run('pending.request.operationId'),original.operationId);
  timers[0].callback();await submission;
  assert.deepEqual(JSON.parse(p.store.get('spug-backup-original')).request,original);
  assert.equal(calls.filter(call=>call.method==='POST').length,1);
  assert.ok(calls.some(call=>call.url==='/backup-entry-api/operations/'+original.operationId));
  assert.ok(timers.slice(1).every(timer=>timer.milliseconds===20000));
  assert.equal(cleared.length,timers.length);
  assert.match(p.get('problem').textContent,/ENTRY_REQUEST_TIMEOUT/);
  assert.equal(p.get('simple-submit').disabled,true);
});

test('backend plan timeout is visible in Chinese and keeps automatic submission blocked',async()=>{
  const p=page();p.get('simple-type').value='INCREMENTAL';
  p.run("api=async()=>{throw new Error('INCREMENTAL_PLAN_TIMEOUT');};");
  await p.run('loadIncrementalPlan()');
  assert.match(p.get('simple-status').textContent,/核对.*超时/);
  assert.match(p.get('simple-status').textContent,/INCREMENTAL_PLAN_TIMEOUT/);
  assert.equal(p.get('simple-submit').disabled,true);
});

test('bridge readiness explains the proven cause and keeps execution blocked',()=>{
  const p=page();
  for(const [code,description] of Object.entries({
    BRIDGE_TIMEOUT:/超时/, BRIDGE_CONNECTION_REFUSED:/连接被拒绝/, BRIDGE_DNS_FAILED:/域名解析失败/,
    BRIDGE_CONNECTION_RESET:/连接.*中断/, BRIDGE_NETWORK_UNREACHABLE:/网络.*不可达/,
    BRIDGE_TLS_CERTIFICATE_INVALID:/证书.*校验失败/, BRIDGE_TLS_FAILED:/TLS.*失败/,
    BRIDGE_CONNECTION_FAILED:/连接失败.*未.*具体原因/, BRIDGE_IO_FAILED:/读写失败/,
    BRIDGE_RESPONSE_ENCODING_INVALID:/UTF-8/, BRIDGE_RESPONSE_JSON_INVALID:/JSON/,
    BRIDGE_RESPONSE_TOO_LARGE:/64 KiB/, BRIDGE_RESPONSE_INCOMPLETE:/响应.*完整/,
    BRIDGE_RESPONSE_HTTP_INVALID:/HTTP.*格式/, BRIDGE_REQUEST_INVALID:/请求.*无效/,
    BRIDGE_HTTP_401:/认证失败/, BRIDGE_HTTP_403:/拒绝.*权限/, BRIDGE_HTTP_404:/接口.*不存在/,
    BRIDGE_HTTP_502:/网关/, BRIDGE_HTTP_503:/服务.*不可用/, BRIDGE_HTTP_504:/网关.*超时/,
  })) {
    p.context.code=code;
    p.run('options[0].validated=null;options[0].readinessError=code;render();');
    assert.match(p.get('simple-status').textContent,description,code);
    assert.ok(p.get('simple-status').textContent.includes(code));
    assert.equal(p.get('simple-submit').disabled,true);
    assert.doesNotMatch(p.get('simple-status').textContent,/只能继续查询原操作/);
  }
  assert.match(p.run("message('BRIDGE_HTTP_418')"),/HTTP 418/);
  assert.match(p.run("message('BRIDGE_UNAVAILABLE_OR_RESPONSE_INVALID')"),/旧记录.*具体原因/);
});

test('restore form names the shared program and initially selects replacement',()=>{
  const html=fs.readFileSync(path.join(__dirname,'smallapp-ui','index.html'),'utf8');
  assert.match(html,/<option value="replace" selected>覆盖现有程序<\/option>/);
  assert.doesNotMatch(html,/覆盖[^<。]*小程序/);
});

test('a new restore draft defaults to replacement without selecting a target or admitting unregistered overwrite',async()=>{
  const p=page();p.run("refresh=async()=>{};S('simple-restore-mode').value='fresh';");
  p.get('simple-restore-tab').onclick();
  assert.equal(p.get('simple-restore-mode').value,'replace');
  assert.equal(p.get('simple-target').value,'');
  assert.equal(p.get('simple-target').children.find(o=>o.value==='target-server').disabled,true);
  assert.equal(p.get('simple-submit').disabled,true);
  await p.get('simple-restore-mode').onchange();
  p.get('simple-restore-mode').value='fresh';await p.get('simple-restore-mode').onchange();
  assert.equal(p.get('simple-target').children.find(o=>o.value==='target-server').disabled,false);
});

test('catalogue restore defaults to replacement and preserves old fresh-operation semantics',async()=>{
  const p=page();p.context.packageRow={packageId:'point-ref',kind:'backup-full',application:'product',servers:['server'],version:'version-1'};
  p.run('refresh=async()=>{};');await p.run('openCatalogRestore(packageRow)');
  assert.equal(p.get('simple-restore-mode').value,'replace');
  assert.equal(p.get('simple-target').value,'');assert.equal(p.get('simple-submit').disabled,true);
  p.get('catalog-restore-close').onclick();
  p.context.original=record();p.run("original.request.action='RESTORE';original.request.targetConfigRef='target-ref';syncSimpleIdentity(original);");
  assert.equal(p.get('simple-restore-mode').value,'fresh');
});

test('catalogue restore reuses the form, pins the selected point and requires an explicit target and confirmation',async()=>{
  const p=page();p.context.packageRow={packageId:'point-ref',kind:'backup-full',category:'backup',application:'product',servers:['server'],version:'version-1'};
  p.run("refresh=async()=>{};globalThis.submissions=[];submitOriginal=async request=>submissions.push(request);progress=async()=>{};showSimplePage('catalog');");
  await p.run('openCatalogRestore(packageRow)');
  p.get('simple-restore-mode').value='fresh';await p.get('simple-restore-mode').onchange();
  assert.equal(p.get('catalog-restore-dialog').open,true);
  assert.equal(p.get('simple-form-panel').hidden,false);
  assert.equal(p.get('simple-catalog-tab')['aria-selected'],'true');
  assert.equal(p.get('simple-package').value,'point-ref');
  assert.equal(p.get('simple-package').disabled,true);
  assert.equal(p.get('simple-target').value,'');
  assert.equal(p.get('simple-submit').disabled,true);
  assert.equal(p.run('submissions.length'),0);
  p.get('simple-target').value='target-server';await p.get('simple-target').onchange();p.run('render()');
  assert.equal(p.get('simple-submit').disabled,false);
  p.get('simple-submit').onclick();
  assert.equal(p.get('simple-confirm').open,true);
  assert.match(p.get('confirm-summary').textContent,/point-ref/);
  assert.match(p.get('confirm-summary').textContent,/target-server/);
  assert.equal(p.run('submissions.length'),0);
  p.get('simple-cancel').onclick();assert.equal(p.get('catalog-restore-dialog').open,true);
  p.get('simple-submit').onclick();await p.get('simple-confirm-submit').onclick();
  assert.equal(p.run('submissions.length'),1);
  assert.equal(p.run('submissions[0].recoveryPointRef'),'point-ref');
  assert.equal(p.run('submissions[0].targetConfigRef'),'target-ref');
  assert.equal(p.get('catalog-restore-dialog').open,false);
  assert.equal(p.get('simple-progress-tab')['aria-selected'],'true');
});

test('catalogue point absent from server accepted refs stays visible but cannot submit or substitute another package',async()=>{
  const p=page();p.context.packageRow={packageId:'unaccepted-point',kind:'backup-incremental',category:'backup',application:'product',servers:['server']};
  p.run('refresh=async()=>{};');await p.run('openCatalogRestore(packageRow)');
  p.get('simple-target').value='target-server';p.run('render()');
  assert.equal(p.get('simple-package').value,'unaccepted-point');
  assert.equal(p.get('simple-submit').disabled,true);
  assert.match(p.get('simple-status').textContent,/未.*恢复点/);
  p.get('simple-submit').onclick();assert.equal(p.run('confirmation'),null);
  p.get('catalog-restore-close').onclick();
  assert.equal(p.get('catalog-restore-dialog').open,false);
  assert.equal(p.run('catalogRestore'),null);
  p.get('simple-restore-tab').onclick();assert.equal(p.get('simple-form-panel').hidden,false);
});

test('explicit archive-only source restores an admitted point and still requires confirmation',()=>{
  const p=page();
  p.run(`options[0].validated.fullReady=false;options[0].validated.fullErrorCode='SOURCE_RESTORE_ONLY';
    simpleRestoring=true;action='RESTORE';S('simple-package').value='point-ref';
    S('simple-target').value='target-server';render();`);
  assert.equal(p.get('submit').disabled,false);
  assert.equal(p.get('simple-submit').disabled,false);
  p.get('simple-submit').onclick();
  assert.equal(p.get('simple-confirm').open,true);
  assert.equal(p.run('confirmation.request.recoveryPointRef'),'point-ref');
  assert.equal(p.run('confirmation.request.targetConfigRef'),'target-ref');
});

function historicalRoutePage(){
  const p=page();
  p.run(`simpleConfig.bindings.push({...simpleConfig.bindings[0],applicationId:'historical-app',selectable:false});
    simpleConfig.catalogueRestoreBindings={'historical-point':'historical-app'};
    options.push({...options[0],applicationId:'historical-app',sourceConfigRef:'historical-source',validated:{
      fullReady:false,fullErrorCode:'SOURCE_RESTORE_ONLY',parentChainRefs:[],
      recoveryPointRefs:['historical-point'],freshTargetConfigRefs:['target-ref']}});
    refresh=async()=>{};`);
  p.context.packageRow={packageId:'historical-point',kind:'backup-full',application:'unknown',servers:['wrong-nas-label']};
  return p;
}

test('catalogue explicit historical route selects its retired source without trusting NAS labels',async()=>{
  const p=historicalRoutePage();await p.run('openCatalogRestore(packageRow)');
  assert.equal(p.run('currentBinding().applicationId'),'historical-app');
  assert.equal(p.get('simple-product').value,'product');assert.equal(p.get('simple-server').value,'server');
  p.get('simple-restore-mode').value='fresh';await p.get('simple-restore-mode').onchange();
  p.get('simple-target').value='target-server';p.run('render()');
  assert.equal(p.get('simple-submit').disabled,false);p.get('simple-submit').onclick();
  assert.equal(p.run('confirmation.request.sourceConfigRef'),'historical-source');
  assert.equal(p.run('confirmation.request.recoveryPointRef'),'historical-point');
  assert.equal(p.run('confirmation.applicationId'),'historical-app');
  p.get('simple-cancel').onclick();p.get('catalog-restore-close').onclick();
  assert.equal(p.run('currentBinding().applicationId'),'app','normal choices retain current capture source');
});

test('historical catalogue route cannot override source acceptance or survive an explicit source change',async()=>{
  const p=historicalRoutePage();p.run("options[1].validated.recoveryPointRefs=[];");
  await p.run('openCatalogRestore(packageRow)');p.get('simple-target').value='target-server';p.run('render()');
  assert.equal(p.get('simple-submit').disabled,true);assert.match(p.get('simple-status').textContent,/未.*恢复点/);
  p.get('simple-mode').value='fast';await p.get('simple-mode').onchange();
  assert.equal(p.run('currentBinding()'),undefined);assert.equal(p.get('simple-submit').disabled,true);
  assert.equal(p.run('confirmation'),null);
});

test('unknown or unsafe explicit historical route is rejected before opening a restore draft',async()=>{
  for(const invalid of ['missing','fast']){
    const p=historicalRoutePage();
    p.run(invalid==='missing'?"simpleConfig.catalogueRestoreBindings['historical-point']='missing-app';":"simpleConfig.bindings[1].mode='fast';");
    await p.run('openCatalogRestore(packageRow)');
    assert.equal(p.run('catalogRestore'),null);assert.equal(p.get('catalog-restore-dialog').open,undefined);
    assert.match(p.get('catalog-problem').textContent,/历史.*来源.*登记/);
  }
});

test('archive-only admission keeps new backups blocked with a readable reason',()=>{
  const p=page();
  p.run("options[0].validated.fullReady=false;options[0].validated.fullErrorCode='SOURCE_RESTORE_ONLY';render();");
  assert.equal(p.get('simple-submit').disabled,true);
  assert.match(p.get('simple-status').textContent,/历史备份.*恢复/);
  assert.match(p.get('simple-status').textContent,/SOURCE_RESTORE_ONLY/);
});

test('archive restore never ignores another readiness failure or a quarantine error',()=>{
  const p=page();
  p.run(`simpleRestoring=true;action='RESTORE';S('simple-package').value='point-ref';
    S('simple-target').value='target-server';options[0].validated.fullReady=false;
    options[0].validated.fullErrorCode='SOURCE_CONFIGURATION_REQUIRED';render();`);
  assert.equal(p.get('simple-submit').disabled,true);
  p.run("options[0].validated.fullErrorCode='SOURCE_RESTORE_ONLY';options[0].validated.historyErrorCode='POINT_QUARANTINED';render();");
  assert.equal(p.get('simple-submit').disabled,true);
  assert.match(p.get('simple-status').textContent,/POINT_QUARANTINED/);
});

test('catalogue restore refuses a running draft and never treats release artifacts as backup points',async()=>{
  const p=page();p.context.packageRow={packageId:'point-ref',kind:'release-full',category:'release',application:'product',servers:['server']};
  await p.run('openCatalogRestore(packageRow)');assert.equal(p.get('catalog-restore-dialog').open,undefined);
  p.context.original=record();p.run("active=original;packageRow.kind='backup-full';packageRow.category='backup';render();");
  await p.run('openCatalogRestore(packageRow)');assert.equal(p.run('active.request.operationId'),'original-operation-123');
  assert.equal(p.get('catalog-restore-dialog').open,undefined);
});

test('five peer tabs show one panel and read-only navigation preserves the draft',()=>{
  const p=page();p.get('simple-type').value='INCREMENTAL';
  p.run("showSimplePage('catalog');render();");
  assert.equal(p.get('simple-catalog-tab')['aria-selected'],'true');
  assert.equal(p.get('simple-backup-tab')['aria-selected'],'false');
  assert.equal(p.get('package-catalog').hidden,false);
  assert.equal(p.get('simple-form-panel').hidden,true);
  for(const name of ['progress','history']){
    p.get('simple-'+name+'-tab').onclick();p.run('render();');
    assert.equal(p.get('simple-'+name+'-tab')['aria-selected'],'true');
    assert.equal(p.get('simple-'+name+'-panel').hidden,false);
    assert.equal(p.get('package-catalog').hidden,true);
  }
  p.run("showSimplePage('backup');");
  assert.equal(p.get('simple-form-panel').hidden,false);
  assert.equal(p.get('simple-type').value,'INCREMENTAL');
});

test('tab anchors work when the existing history renderer occupies window.history',()=>{
  const p=page();
  p.context.window={location:{hash:''},history:()=>{}};
  p.run("showSimplePage('catalog');");
  assert.equal(p.context.window.location.hash,'package-catalog');
});

test('returning from a read-only panel retains the chosen restore package and original draft id',()=>{
  const p=page();
  p.run("simpleRestoring=true;action='RESTORE';showSimplePage('restore');render();S('simple-package').value='point-ref';S('point').value='point-ref';showSimplePage('catalog');");
  p.get('simple-restore-tab').onclick();
  assert.equal(p.get('simple-package').value,'point-ref');
  assert.equal(p.run('operationId'),'test-operation-123');
  assert.equal(p.get('simple-restore-tab')['aria-selected'],'true');
});

test('read-only tabs remain usable during a running draft and keyboard skips disabled form tabs',()=>{
  const p=page();p.context.original=record();
  p.run('active=original;render();');
  assert.equal(p.get('simple-backup-tab').disabled,true);
  p.get('simple-history-tab').onclick();
  assert.equal(p.get('simple-history-tab')['aria-selected'],'true');
  assert.equal(p.get('simple-history-tab').disabled,false);
  p.get('simple-history-tab').onkeydown({key:'ArrowRight',preventDefault(){}});
  assert.equal(p.get('simple-catalog-tab')['aria-selected'],'true');
  p.get('simple-catalog-tab').onkeydown({key:'End',preventDefault(){}});
  assert.equal(p.get('simple-history-tab')['aria-selected'],'true');
});

test('viewing an existing operation opens progress without starting a new request',async()=>{
  const p=page();p.context.original=record();
  p.run("query=async()=>{};progress=async()=>{};showSimplePage('history');");
  await p.run('openRecord(original)');
  assert.equal(p.get('simple-progress-tab')['aria-selected'],'true');
  assert.equal(p.get('simple-progress-panel').hidden,false);
  assert.equal(p.run('active.request.operationId'),'original-operation-123');
  assert.equal(p.run('pending'),null);
});

test('initial configuration keeps draft locked until source synchronization completes',async()=>{
  const p=page();
  p.run(`globalThis.configuration=simpleConfig;globalThis.releaseConfiguration=null;
    api=async url=>{if(url==='/simple-config')return new Promise(resolve=>{releaseConfiguration=resolve;});
      if(url==='/history')return [];return {applications:options,initialOperationIds:{},registrationVersions:{}};};`);
  const initializing=p.start();
  await Promise.resolve();
  assert.equal(p.get('simple-product').disabled,true);
  assert.equal(p.get('simple-restore-tab').disabled,true);
  assert.equal(p.get('simple-submit').disabled,true);
  p.run('releaseConfiguration(configuration)');await initializing;
  assert.equal(p.get('simple-product').disabled,false);
  assert.equal(p.run('busy || switching'),false);
  assert.equal(p.run('currentBinding().applicationId'),p.get('application').value);
});

test('initial render with an empty source catalogue waits for configuration instead of throwing',async()=>{
  const p=page();
  p.run(`globalThis.configuration=simpleConfig;globalThis.applications=options;
    options=[];S('application').replaceChildren();
    api=async url=>{if(url==='/simple-config')return configuration;if(url==='/history')return [];
      return {applications,initialOperationIds:{},registrationVersions:{}};};`);
  await p.start();
  assert.equal(p.run('simpleInitializing'),false);
  assert.equal(p.run('simpleConfigError'),'');
  assert.equal(p.get('simple-product').disabled,false);
  assert.equal(p.run('selected().applicationId'),'app');
});

test('initial configuration failure remains visible and explicit refresh can recover',async()=>{
  const p=page();p.run('globalThis.configuration=simpleConfig;');
  await p.start();
  p.run('render()');
  assert.match(p.get('simple-status').textContent,/UNEXPECTED_TEST_API_CALL/);
  assert.equal(p.get('simple-submit').disabled,true);
  assert.equal(p.get('simple-refresh').disabled,false);
  p.run(`api=async url=>{if(url==='/simple-config')return configuration;if(url==='/history')return [];
    return {applications:options,initialOperationIds:{},registrationVersions:{}};};`);
  await p.get('simple-refresh').onclick();
  assert.equal(p.get('simple-product').disabled,false);
  assert.equal(p.run('simpleConfigError'),'');
});

test('registered restore target can be selected before its readiness probe and cannot submit',()=>{
  const p=page();
  p.run("simpleRestoring=true;action='RESTORE';selected().validated.freshTargetConfigRefs=[];S('simple-target').value='';render();");
  assert.equal(p.get('simple-target').children.find(o=>o.value==='target-server').disabled,false);
  p.get('simple-target').value='target-server';
  p.run('render()');
  assert.equal(p.get('simple-target').value,'target-server');
  assert.equal(p.get('simple-submit').disabled,true);
});

test('restore target selection probes only that registered target; backup refresh has no target',async()=>{
  const p=page();p.context.calls=[];
  p.run(`api=async url=>{calls.push(url);if(url==='/history')return [];return {applications:options,initialOperationIds:{},registrationVersions:{}};};
    simpleRestoring=true;action='RESTORE';S('simple-target').value='target-server';`);
  await p.get('simple-target').onchange();
  assert.ok(p.context.calls.includes('/selections?applicationId=app&targetConfigRef=target-ref'));
  p.context.calls.length=0;
  p.run("simpleRestoring=false;action='FULL';");
  await p.run("refresh('app')");
  assert.ok(p.context.calls.includes('/selections?applicationId=app'));
  assert.equal(p.context.calls.some(url=>url.includes('targetConfigRef')),false);
});

test('returning to an application retains its explicitly selected server and fast mode',async()=>{
  const p=page();
  p.run(`
    simpleConfig.bindings.push({...simpleConfig.bindings[0],mode:'fast',applicationId:'fast-app'});
    simpleConfig.bindings.push({...simpleConfig.bindings[0],product:'other',server:'other-server',applicationId:'other-app'});
    options.push({...options[0],applicationId:'fast-app'},{...options[0],applicationId:'other-app'});
    refresh=async()=>{};
    S('simple-mode').value='fast';
  `);
  await p.run('chooseSimple()');
  p.get('simple-product').value='other';
  await p.get('simple-product').onchange();
  assert.equal(p.get('simple-server').value,'other-server');
  p.get('simple-product').value='product';
  await p.get('simple-product').onchange();
  assert.equal(p.get('simple-server').value,'server');
  assert.equal(p.get('simple-mode').value,'fast');
});

test('a remembered mode becoming unavailable does not silently select another executor',async()=>{
  const p=page();
  p.run(`
    simpleConfig.bindings.push({...simpleConfig.bindings[0],mode:'fast',applicationId:'fast-app'});
    options.push({...options[0],applicationId:'fast-app'});
    refresh=async()=>{};S('simple-mode').value='fast';
  `);
  await p.run('chooseSimple()');
  p.get('simple-product').value='unregistered-product';
  await p.get('simple-product').onchange();
  p.run("simpleConfig.bindings.find(b=>b.mode==='fast').selectable=false;");
  p.get('simple-product').value='product';
  await p.get('simple-product').onchange();
  assert.equal(p.get('simple-mode').value,'fast');
  assert.equal(p.get('simple-submit').disabled,true);
  assert.match(p.get('simple-status').textContent,/尚未登记快速模式/);
});

const automaticPlan=(changes={})=>({schemaVersion:'AutomaticIncrementalPlan/v1',sourceConfigRef:'source-ref',
  state:'READY',reasonCode:null,parentChainRef:'verified-increment',baseFullRef:'verified-full',generationId:'generation-1',
  chainDepth:2,pointType:'INCREMENTAL',parentPointType:'INCREMENTAL',basePointType:'FULL',
  finishedAt:'2026-11-06T01:00:00Z',baseFinishedAt:'2026-11-05T01:00:00Z',evidenceDigest:'d'.repeat(64),planDigest:'a'.repeat(64),...changes});

function planApi(p,plan=automaticPlan()){
  p.context.planResponse={applicationId:'app',plan};p.context.apiCalls=[];
  p.run(`api=async(url,body)=>{apiCalls.push({url,body});
    if(url.startsWith('/incremental-plan?'))return planResponse;
    if(url.startsWith('/selections'))return {applications:options,initialOperationIds:{},registrationVersions:{}};
    if(url==='/history')return [];throw new Error('UNEXPECTED_TEST_API_CALL');};`);
}

test('automatic incremental uses the authoritative plan despite absent local history and selection refs',async()=>{
  const p=page();planApi(p);
  p.run("records=[];selected().validated.parentChainRefs=[];selected().validated.historyErrorCode='LOCAL_HISTORY_UNAVAILABLE';S('simple-type').value='INCREMENTAL';");
  await p.get('simple-type').onchange();
  assert.equal(p.context.apiCalls.filter(call=>call.url==='/incremental-plan?applicationId=app').length,1);
  assert.equal(p.get('simple-submit').disabled,false);
  assert.equal(p.run("simpleRequest('plan-test').parentChainRef"),'verified-increment');
  assert.match(p.get('simple-status').textContent,/全量基线.*2026/);
  assert.match(p.get('simple-status').textContent,/最新.*增量/);
  p.get('simple-submit').onclick();
  assert.match(p.get('confirm-summary').textContent,/verified-full/);
  assert.match(p.get('confirm-summary').textContent,/verified-increment/);
  assert.equal(p.context.apiCalls.filter(call=>call.body).length,0);
});

test('a required baseline is explicitly confirmed as FULL and submitted through the automatic endpoint',async()=>{
  const p=page();planApi(p,automaticPlan({state:'BASELINE_REQUIRED',reasonCode:'BACKUP_POINT_EPOCH_CHANGED',parentChainRef:null,
    baseFullRef:null,chainDepth:0,pointType:null,parentPointType:null,basePointType:null,finishedAt:null,baseFinishedAt:null}));
  p.get('simple-type').value='INCREMENTAL';await p.get('simple-type').onchange();
  assert.equal(p.get('simple-submit').disabled,false);
  assert.match(p.get('simple-status').textContent,/全量.*基线/);
  assert.match(p.get('simple-submit').textContent,/全量基线/);
  p.get('simple-submit').onclick();
  assert.match(p.get('confirm-summary').textContent,/全量备份/);
  assert.match(p.get('confirm-summary').textContent,/BACKUP_POINT_EPOCH_CHANGED/);
  assert.equal(p.run('confirmation.request.action'),'FULL');
  assert.equal(p.run('confirmation.request.parentChainRef'),null);
  p.context.expected=p.run('JSON.parse(JSON.stringify(confirmation.request))');
  p.run(`api=async(url,body)=>{apiCalls.push({url,body});if(url==='/automatic-incremental')return {applicationId:'app',request:expected,automaticIncrementalPlan:planResponse.plan,result:{state:'RUNNING',logRefs:[]}};
    if(url==='/history')return [];if(url.startsWith('/progress/'))return {operationId:expected.operationId,steps:[]};throw new Error('UNEXPECTED_TEST_API_CALL');};`);
  await p.get('simple-confirm-submit').onclick();
  const posts=p.context.apiCalls.filter(call=>call.body);
  assert.equal(posts.length,1);assert.equal(posts[0].url,'/automatic-incremental');
  assert.deepEqual(JSON.parse(JSON.stringify(posts[0].body)),{schemaVersion:'AutomaticIncrementalRequest/v1',
    operationId:p.context.expected.operationId,applicationId:'app',planDigest:'a'.repeat(64)});
  assert.equal(p.run('pending.request.action'),'FULL');
  assert.match(p.get('simple-operation-details').children.map(node=>node.textContent).join('\n'),/全量基线/);
});

test('live source preflight reasons explain the need for a new baseline or a blocked source',()=>{
  const p=page();
  for(const [code,detail] of Object.entries({
    INCREMENTAL_PARENT_BINLOG_PURGED:/日志.*清理.*全量基线/,
    INCREMENTAL_BINLOG_CHAIN_GAP:/日志.*缺段.*全量基线/,
    INCREMENTAL_SOURCE_POSITION_REGRESSED:/位置.*倒退.*全量基线/,
    INCREMENTAL_SOURCE_LINEAGE_CHANGED:/来源.*版本.*变化.*全量基线/,
    INCREMENTAL_LIVE_SOURCE_IDENTITY_CHANGED:/实际数据库身份.*登记.*不符/,
    BACKUP_EPOCH_CHANGED_DURING_PLAN:/核对.*期间.*恢复周期.*变化/,
    SOURCE_EPOCH_STORAGE_OVERLAP:/恢复周期.*数据.*路径.*重叠/,
  })){
    p.context.code=code;const text=p.run('message(code)');
    assert.match(text,detail);assert.ok(text.includes(code));
  }
});

test('blocked, failed and mismatched plans invalidate earlier readiness and explain the exact reason',async()=>{
  for(const mode of ['blocked','network','source','application','evidence']){
    const p=page();planApi(p);p.get('simple-type').value='INCREMENTAL';await p.get('simple-type').onchange();
    if(mode==='blocked')p.context.planResponse.plan=automaticPlan({state:'BLOCKED',reasonCode:'INCREMENTAL_PARENT_PREFIX_INVALID'});
    if(mode==='network')p.run("api=async()=>{throw new Error('BRIDGE_TIMEOUT');};");
    if(mode==='source')p.context.planResponse.plan=automaticPlan({sourceConfigRef:'other-source'});
    if(mode==='application')p.context.planResponse.applicationId='other-app';
    if(mode==='evidence')delete p.context.planResponse.plan.evidenceDigest;
    await p.run('loadIncrementalPlan()');
    assert.equal(p.get('simple-submit').disabled,true,mode);
    assert.match(p.get('simple-status').textContent,mode==='blocked'?/INCREMENTAL_PARENT_PREFIX_INVALID/:mode==='network'?/BRIDGE_TIMEOUT/:/INCREMENTAL_PLAN_INVALID/);
    p.get('simple-submit').onclick();assert.equal(p.run('confirmation'),null);
  }
});

test('missing source restoration proof blocks backup and explains the receipt without suggesting FULL',async()=>{
  const p=page();planApi(p,automaticPlan({state:'BLOCKED',reasonCode:'INCREMENTAL_SOURCE_RESTORATION_INVALID'}));
  p.get('simple-type').value='INCREMENTAL';await p.get('simple-type').onchange();
  assert.match(p.get('simple-status').textContent,/备份源服务.*恢复回执.*缺失或不匹配.*检查/);
  assert.match(p.get('simple-status').textContent,/INCREMENTAL_SOURCE_RESTORATION_INVALID/);
  assert.doesNotMatch(p.get('simple-status').textContent,/全量|FULL/);
  assert.equal(p.get('simple-submit').disabled,true);
  p.get('simple-submit').onclick();
  assert.equal(p.run('confirmation'),null);
  assert.equal(p.context.apiCalls.filter(call=>call.body).length,0);
});

test('a late plan from an earlier source cannot replace the current source plan',async()=>{
  const p=page();planApi(p);p.get('simple-type').value='INCREMENTAL';
  p.run(`globalThis.waiters=[];api=async()=>new Promise(resolve=>waiters.push(resolve));`);
  const first=p.run('loadIncrementalPlan()');
  p.run("options[0].sourceConfigRef='new-source';");
  const second=p.run('loadIncrementalPlan()');
  p.context.nextPlan=automaticPlan({sourceConfigRef:'new-source',parentChainRef:'new-parent',planDigest:'b'.repeat(64)});
  p.run("waiters[1]({applicationId:'app',plan:nextPlan});");await second;
  p.run('waiters[0](planResponse);');await first;
  assert.equal(p.run("simpleRequest('plan-test').parentChainRef"),'new-parent');
  assert.equal(p.get('simple-submit').disabled,false);
});

test('confirming an incremental freezes the plan digest and double clicks dispatch only once',async()=>{
  const p=page();planApi(p);p.get('simple-type').value='INCREMENTAL';await p.get('simple-type').onchange();
  p.get('simple-submit').onclick();p.context.expected=p.run('JSON.parse(JSON.stringify(confirmation.request))');
  p.run(`globalThis.releasePost=null;api=async(url,body)=>{apiCalls.push({url,body});if(body)return new Promise(resolve=>{releasePost=resolve;});if(url==='/history')return [];return {operationId:expected.operationId,steps:[]};};`);
  const first=p.get('simple-confirm-submit').onclick();await p.get('simple-confirm-submit').onclick();
  assert.equal(p.context.apiCalls.filter(call=>call.body).length,1);
  assert.equal(JSON.parse(p.store.get('spug-backup-original')).request.parentChainRef,'verified-increment');
  p.run("releasePost({applicationId:'app',request:expected,automaticIncrementalPlan:planResponse.plan,result:{state:'RUNNING',logRefs:[]}});");await first;
  assert.equal(p.run('pending.request.operationId'),p.context.expected.operationId);
});

test('a changed plan digest after confirmation requires a fresh confirmation',async()=>{
  const p=page();planApi(p);p.get('simple-type').value='INCREMENTAL';await p.get('simple-type').onchange();
  p.get('simple-submit').onclick();p.run("incrementalPlan={...incrementalPlan,plan:{...incrementalPlan.plan,planDigest:'b'.repeat(64)}};");
  await p.get('simple-confirm-submit').onclick();
  assert.equal(p.context.apiCalls.filter(call=>call.body).length,0);
  assert.match(p.get('problem').textContent,/重新确认/);
});

test('only an exact pre-admission rejection unlocks the draft and refreshes the plan without resubmitting',async()=>{
  for(const matches of [true,false]){
    const p=page();planApi(p);p.get('simple-type').value='INCREMENTAL';await p.get('simple-type').onchange();
    p.get('simple-submit').onclick();p.context.expected=p.run('JSON.parse(JSON.stringify(confirmation.request))');p.context.matches=matches;
    p.run(`api=async(url,body)=>{apiCalls.push({url,body});if(body)throw Object.assign(new Error('INCREMENTAL_PLAN_CHANGED'),
      {status:409,rejection:{accepted:false,operationId:matches?expected.operationId:'other-id',applicationId:'app'}});
      if(url.startsWith('/incremental-plan?'))return planResponse;if(url==='/history')return [];
      throw new Error('ORIGINAL_OPERATION_NOT_LOCALLY_RECORDED');};`);
    await p.get('simple-confirm-submit').onclick();
    assert.equal(p.context.apiCalls.filter(call=>call.body).length,1);
    if(matches){
      assert.equal(p.run('pending'),null);assert.equal(p.store.has('spug-backup-original'),false);
      assert.equal(p.get('simple-submit').disabled,false);assert.match(p.get('problem').textContent,/重新确认/);
      assert.equal(p.context.apiCalls.filter(call=>call.url.startsWith('/incremental-plan?')).length,2);
    }else{
      assert.equal(p.run('pending.request.operationId'),p.context.expected.operationId);
      assert.equal(p.get('simple-submit').disabled,true);
    }
  }
});

test('unknown dispatch results keep polling the saved operation without another POST and stop at terminal state',async()=>{
  const p=page();p.context.original=record();p.context.apiCalls=[];
  p.run(`api=async(url,body)=>{apiCalls.push({url,body});throw new Error('ENTRY_REQUEST_TIMEOUT');};`);
  await p.run('submitOriginal(original.request,original.applicationId)');
  assert.equal(p.run('active.result'),undefined);
  await p.run('pollOriginal()');
  await p.run('pollOriginal()');
  assert.equal(p.context.apiCalls.filter(call=>call.body).length,1);
  assert.equal(p.context.apiCalls.filter(call=>call.url==='/operations/original-operation-123').length,3);
  assert.match(p.get('problem').textContent,/ENTRY_REQUEST_TIMEOUT/);
  p.run(`api=async(url,body)=>{apiCalls.push({url,body});if(url==='/history')return [];if(url.startsWith('/progress/'))return {operationId:original.request.operationId,steps:[]};return {...original,result:{state:'SUCCEEDED',logRefs:[]}};};`);
  await p.run('pollOriginal()');const length=p.context.apiCalls.length;await p.run('pollOriginal()');
  assert.equal(p.context.apiCalls.length,length);
  assert.equal(p.run('pending.result.state'),'SUCCEEDED');
});

test('reopening an unresolved original immediately queries that original ID',async()=>{
  const p=page();p.context.original=record();p.context.apiCalls=[];
  p.run(`globalThis.configuration=simpleConfig;active={...original,result:undefined};pending=active;
    api=async(url,body)=>{apiCalls.push({url,body});if(url==='/simple-config')return configuration;
    if(url==='/history')return [];if(url.startsWith('/progress/'))return {operationId:original.request.operationId,steps:[]};
    if(url.startsWith('/operations/'))return original;throw new Error('UNEXPECTED_TEST_API_CALL');};`);
  await p.start();
  assert.equal(p.context.apiCalls.filter(call=>call.url==='/operations/original-operation-123').length,1);
  assert.equal(p.context.apiCalls.filter(call=>call.body).length,0);
});

test('viewing a completed history row continues tracking the unresolved original without replacing the viewed row',async()=>{
  const p=page();p.context.original=record();p.context.historical=record('historical-operation');p.context.apiCalls=[];
  p.run(`pending=original;historical.result.state='SUCCEEDED';selectRecord(historical);
    api=async(url,body)=>{apiCalls.push({url,body});return {...original,result:{state:'SUCCEEDED',logRefs:[]}};};`);
  await p.run('pollOriginal()');
  assert.equal(p.context.apiCalls.filter(call=>call.url==='/operations/original-operation-123').length,1);
  assert.equal(p.run('active.request.operationId'),'historical-operation');
  assert.equal(p.run('pending.result.state'),'SUCCEEDED');
  assert.equal(p.context.apiCalls.filter(call=>call.body).length,0);
});

test('returning to backup after a terminal operation requests a new authoritative plan',async()=>{
  const p=page();planApi(p);p.get('simple-type').value='INCREMENTAL';await p.get('simple-type').onchange();
  p.context.original=record();p.run("original.result.state='SUCCEEDED';active=original;pending=original;showSimplePage('progress');render();");
  p.context.planResponse.plan=automaticPlan({parentChainRef:'next-increment',planDigest:'c'.repeat(64)});
  await p.get('simple-backup-tab').onclick();
  assert.equal(p.run("simpleRequest('next-operation').parentChainRef"),'next-increment');
  assert.equal(p.get('simple-submit').disabled,false);
});

test('unregistered targets are disabled and unverified registered choices cannot submit',()=>{
  const p=page();
  p.run("simpleConfig.servers.push({address:'missing',name:'Missing'});simpleRestoring=true;action='RESTORE';render();");
  assert.equal(p.get('simple-target').children.find(o=>o.value==='missing').disabled,true);
  p.run("S('simple-target').value='target-server';selected().validated.freshTargetConfigRefs=[];render();");
  assert.equal(p.get('simple-target').value,'target-server');
  assert.equal(p.get('simple-target').children.find(o=>o.value==='target-server').disabled,false);
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
  assert.equal(p.get('simple-target').children.find(o=>o.value==='target-server').disabled,false);
  assert.equal(p.get('simple-submit').disabled,true);
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
  assert.match(p.get('confirm-summary').textContent,/覆盖现有程序/);
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
  p.context.original.displayContext={server:'original-server',mode:'fast',restoreMode:'replace'};
  p.run(`original.request.action='RESTORE';original.request.recoveryPointRef='historical-point';original.request.targetConfigRef='historical-target';
    simpleConfig.bindings[0].mode='fast';simpleConfig.bindings[0].targetServers['target-server']='new-draft-target';selectRecord(original);render();`);
  const details=p.get('simple-operation-details');
  assert.equal(details.hidden,false);
  const text=details.children.map(item=>item.textContent).join('\n');
  assert.match(text,/historical-point/);assert.match(text,/historical-target/);
  assert.match(text,/快速模式 · 跳过核验/);assert.doesNotMatch(text,/new-draft-target/);
  assert.match(text,/覆盖现有程序/);assert.match(text,/original-server/);
  p.run('selectRecord(null);render();');assert.equal(details.hidden,true);assert.equal(details.children.length,0);
});

test('legacy history never infers restore semantics from current mappings',()=>{
  const p=page();p.context.original=record();
  p.run(`original.request.action='RESTORE';original.request.targetConfigRef='historical-target';
    simpleConfig.bindings[0].overwriteTargetServers={'target-server':'historical-target'};selectRecord(original);render();`);
  const text=p.get('simple-operation-details').children.map(item=>item.textContent).join('\n');
  assert.match(text,/恢复方式未记录/);assert.match(text,/执行模式未记录/);
  assert.doesNotMatch(text,/覆盖现有程序|恢复到空目标/);
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
