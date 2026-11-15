'use strict';
// UI state contracts only; these tests do not claim live server preparation.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {createPrepareTarget} = require('./prepare-target.js');
const host='172.30.30.59', id='prepare-12345678-abcd';
const digest='a'.repeat(64);
const selection={restoring:true,host,applicationId:'app',recoveryPointRef:'point'};
const preview={host,applicationId:'app',recoveryPointRef:'point',planDigest:digest,
  cleanupSummary:['旧容器','旧数据目录'],preserveSummary:['NAS','工具目录'],stages:['dependencies','cleanup','initialize']};
const record=(state='RUNNING')=>({operationId:id,host,applicationId:'app',recoveryPointRef:'point',state,
  stages:['dependencies','cleanup','initialize'].map(name=>({name,state:state==='READY'?'SUCCEEDED':'PENDING'})),
  targetConfigRef:state==='READY'?'new-target':null,errorCode:null});
function page(options={}) {
  class Element {
    constructor(){this.textContent='';this.hidden=false;this.disabled=false;this.checked=false;this.children=[];}
    append(...values){this.children.push(...values);}
    replaceChildren(...values){this.children=[...values];}
    showModal(){this.open=true;}
    close(){this.open=false;}
    setAttribute(key,value){this[key]=value;}
  }
  const elements=new Map(),calls=[],store=options.store||new Map();let chosen={...selection};
  const get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  const api=async(path,body)=>{
    calls.push({path,body});
    if(options.api)return options.api(path,body);
    if(path.endsWith('/config'))return {configured:true,host,errorCode:null};
    if(path.endsWith('/history'))return [];
    if(path.endsWith('/preview'))return preview;
    return record();
  };
  let ready=0;
  const controller=createPrepareTarget({document:{getElementById:get,createElement:()=>new Element()},api,
    storage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)},
    randomId:()=>id,selection:()=>chosen,isBusy:()=>false,onReady:async()=>{ready++;}});
  return {controller,get,calls,store,choose:value=>{chosen={...chosen,...value};},ready:()=>ready};
}
test('missing configuration is visible and cannot preview or submit',async()=>{
  const p=page({api:async path=>path.endsWith('/config')?{configured:false,host,errorCode:'PREPARE_NOT_CONFIGURED'}:[]});
  await p.controller.initialize();await p.controller.preview();
  assert.equal(p.get('prepare-target-start').disabled,true);
  assert.match(p.get('prepare-target-status').textContent,/PREPARE_NOT_CONFIGURED/);
  assert.equal(p.calls.some(x=>x.path.endsWith('/preview')),false);
});
test('preview displays the server cleanup scope and binds confirmation to current selection',async()=>{
  const p=page();await p.controller.initialize();await p.controller.preview();
  assert.equal(p.get('prepare-target-confirm').open,true);
  assert.match(p.get('prepare-target-summary').textContent,/旧数据目录/);
  assert.match(p.get('prepare-target-summary').textContent,/NAS/);
  p.choose({recoveryPointRef:'other'});p.get('prepare-target-agree').checked=true;
  await p.controller.submit();assert.equal(p.calls.some(x=>x.path.endsWith('/operations')),false);
  assert.match(p.get('prepare-target-status').textContent,/变化/);
});
test('only .59 restore selection can prepare',async()=>{
  const p=page();await p.controller.initialize();p.choose({host:'172.30.30.57'});
  await p.controller.preview();assert.equal(p.calls.some(x=>x.path.endsWith('/preview')),false);
  p.choose({host,restoring:false});await p.controller.preview();assert.equal(p.calls.some(x=>x.path.endsWith('/preview')),false);
});
test('confirmation persists the operation before dispatch, duplicate click never dispatches twice',async()=>{
  const p=page();await p.controller.initialize();await p.controller.preview();
  p.get('prepare-target-agree').checked=true;await p.controller.submit();await p.controller.submit();
  const posts=p.calls.filter(x=>x.path.endsWith('/operations'));
  assert.equal(posts.length,1);assert.deepEqual(posts[0].body,{operationId:id,applicationId:'app',recoveryPointRef:'point',planDigest:digest,confirmed:true});
  assert.equal(p.store.size,1);assert.equal(p.controller.blocked(),true);
});
test('unknown submission keeps its original id through refresh and queries only',async()=>{
  const store=new Map();
  const api=async path=>{
    if(path.endsWith('/config'))return {configured:true,host};
    if(path.endsWith('/history'))return [];
    if(path.endsWith('/preview'))return preview;
    throw new Error('CONNECTION_LOST');
  };
  const p=page({store,api});await p.controller.initialize();await p.controller.preview();p.get('prepare-target-agree').checked=true;await p.controller.submit();
  assert.equal(p.controller.blocked(),true);assert.match(p.get('prepare-target-progress').textContent,/未知/);
  assert.match(p.get('prepare-target-progress').textContent,/CONNECTION_LOST/);
  const again=page({store,api});await again.controller.initialize();await again.controller.preview();
  assert.equal(again.calls.some(x=>x.path.endsWith('/operations')),false);
  assert.equal(again.calls.some(x=>x.path==='/prepare-target/operations/'+id),true);
  assert.equal(again.controller.blocked(),true);
  assert.match(again.get('prepare-target-progress').textContent,/CONNECTION_LOST/);
});

test('explicit pre-reservation busy rejection clears only the unaccepted draft',async()=>{
  const p=page({api:async path=>{
    if(path.endsWith('/config'))return {configured:true,host};
    if(path.endsWith('/history'))return [];
    if(path.endsWith('/preview'))return preview;
    const error=new Error('PREPARATION_TARGET_BUSY');error.status=409;
    error.rejection={errorCode:'PREPARATION_TARGET_BUSY'};throw error;
  }});
  await p.controller.initialize();await p.controller.preview();
  p.get('prepare-target-agree').checked=true;await p.controller.submit();
  assert.equal(p.controller.blocked(),false);
  assert.equal(p.store.size,0);
  assert.equal(p.get('prepare-target-progress-section').hidden,true);
  assert.match(p.get('prepare-target-status').textContent,/未受理/);
  assert.match(p.get('prepare-target-status').textContent,/PREPARATION_TARGET_BUSY/);
});
test('READY is shown only with three completed stages and a new target, configuration refresh happens once',async()=>{
  let current=record();
  const p=page({api:async path=>path.endsWith('/config')?{configured:true,host}:path.endsWith('/history')?[]:path.endsWith('/preview')?preview:current});
  await p.controller.initialize();await p.controller.preview();p.get('prepare-target-agree').checked=true;await p.controller.submit();
  current=record('READY');await p.controller.query();await p.controller.query();
  assert.match(p.get('prepare-target-progress').textContent,/空目标已就绪/);assert.equal(p.ready(),1);
  assert.equal(p.controller.blocked(),false);
});
test('FAILED stage is visible, malformed READY cannot be mistaken for success',async()=>{
  let current=record();
  const p=page({api:async path=>path.endsWith('/config')?{configured:true,host}:path.endsWith('/history')?[]:path.endsWith('/preview')?preview:current});
  await p.controller.initialize();await p.controller.preview();p.get('prepare-target-agree').checked=true;await p.controller.submit();
  current={...record('FAILED'),errorCode:'MYSQL_INIT_FAILED',stages:[{name:'dependencies',state:'SUCCEEDED'},{name:'cleanup',state:'SUCCEEDED'},{name:'initialize',state:'FAILED',errorCode:'MYSQL_INIT_FAILED'}]};
  await p.controller.query();assert.match(p.get('prepare-target-progress').textContent,/MYSQL_INIT_FAILED/);assert.equal(p.ready(),0);
  current={...record('READY'),targetConfigRef:null};await p.controller.query();
  assert.match(p.get('prepare-target-status').textContent,/PREPARE_RESULT_INVALID/);assert.equal(p.ready(),0);
});

test('command failure displays its safe action, object, exit code and reason',async()=>{
  const current={...record('FAILED'),errorCode:'PREPARE_NATIVE_COMMAND_FAILED',
    failure:{action:'DOCKER_VOLUME_RM',object:'old-minio',exitCode:1,reason:'RESOURCE_BUSY'}};
  const stored=new Map([['spug.prepare-target.operation.v1',JSON.stringify({operationId:id,applicationId:'app',recoveryPointRef:'point'})]]);
  const p=page({store:stored,api:async path=>path.endsWith('/config')?{configured:true,host}:path.endsWith('/history')?[current]:current});
  await p.controller.initialize();
  const text=p.get('prepare-target-progress').textContent;
  assert.match(text,/DOCKER_VOLUME_RM/);assert.match(text,/old-minio/);
  assert.match(text,/退出码.*1/);assert.match(text,/RESOURCE_BUSY/);
  assert.equal(p.controller.blocked(),false);
});

test('stopped FAILED task permits a new preparation while UNKNOWN still blocks',async()=>{
  let current=record('FAILED');
  const stored=new Map([['spug.prepare-target.operation.v1',JSON.stringify({operationId:id,applicationId:'app',recoveryPointRef:'point'})]]);
  const p=page({store:stored,api:async path=>path.endsWith('/config')?{configured:true,host}:path.endsWith('/history')?[current]:path.endsWith('/preview')?preview:current});
  await p.controller.initialize();
  assert.equal(p.controller.blocked(),false);
  assert.equal(p.controller.restoreBlocked(),true);
  assert.equal(p.get('prepare-target-start').disabled,false);
  await p.controller.preview();
  assert.equal(p.get('prepare-target-confirm').open,true);
  current=record('UNKNOWN');await p.controller.query();
  assert.equal(p.controller.blocked(),true);
});

test('preparation reads the source independently of an offline old .59 target and READY restores target admission',async()=>{
  class Element {
    constructor(){this.value='';this.textContent='';this.children=[];this.disabled=false;this.hidden=false;this.dataset={};}
    add(value){this.children.push(value);if(this.children.length===1)this.value=value.value;}
    append(...values){this.children.push(...values);}
    replaceChildren(...values){this.children=[...values];this.value=values[0]?.value||'';}
    setAttribute(key,value){this[key]=value;}
    get options(){return this.children;}
    addEventListener(name,callback){this['on'+name]=callback;}
    get selectedOptions(){return this.children.filter(x=>x.value===this.value);}
    showModal(){this.open=true;}
    close(){this.open=false;}
  }
  const elements=new Map(),store=new Map(),calls=[];
  const get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
  const context=vm.createContext({document:{hidden:false,getElementById:get,createElement:()=>new Element(),querySelectorAll:()=>[]},
    Option:class{constructor(text,value){this.textContent=text;this.value=value;}},
    localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)},
    crypto:{randomUUID:()=>id},setInterval:()=>0,setTimeout,clearTimeout,AbortController,Date});
  const run=code=>vm.runInContext(code,context);
  run(fs.readFileSync(path.join(__dirname,'app.js'),'utf8').replace('const initialRefresh = refresh();','const initialRefresh = Promise.resolve();'));
  const simple=fs.readFileSync(path.join(__dirname,'simple.js'),'utf8');run(simple.slice(0,simple.indexOf('\nsetInterval(')));
  for(const [name,values] of Object.entries({'simple-product':['product'],'simple-server':['source'],'simple-mode':['safe'],
    'simple-type':['FULL'],'simple-restore-mode':['fresh'],'application':['app']}))for(const value of values)get(name).add(new context.Option(value,value));
  run(`simpleConfig={nas:'nas',servers:[{address:'172.30.30.59',name:'备份服务器'}],bindings:[{product:'product',server:'source',mode:'safe',applicationId:'app',targetServers:{},overwriteTargetServers:{},selectable:true}]};
    options=[{applicationId:'app',sourceConfigRef:'source',validated:{fullReady:true,parentChainRefs:[],recoveryPointRefs:['point'],freshTargetConfigRefs:[]}}];
    S('simple-nas').value='nas';simpleRestoring=true;action='RESTORE';operationId='existing-operation';render();S('simple-package').value='point';`);
  let preparedHistory=[],sourceError=false,targetError=false;
  context.api=async(route,body)=>{
    calls.push({route,body});
    if(route.startsWith('/selections')){
      if(route.includes('targetConfigRef=old-offline-target'))throw new Error('OLD_TARGET_OFFLINE');
      if(targetError&&route.includes('targetConfigRef=new-target'))throw new Error('NEW_TARGET_UNAVAILABLE');
      if(sourceError)throw new Error('SOURCE_READ_FAILED');
      return {applications:[{applicationId:'app',displayName:'app',sourceConfigRef:'source',
        validated:{fullReady:true,parentChainRefs:[],recoveryPointRefs:['point'],freshTargetConfigRefs:route.includes('new-target')?['new-target']:['old-offline-target']}}],initialOperationIds:{},registrationVersions:{}};
    }
    return route.endsWith('/config')?{configured:true,host}:route==='/prepare-target/history'?preparedHistory:
      route.endsWith('/history')?[]:route.endsWith('/preview')?preview:record();
  };
  run(fs.readFileSync(path.join(__dirname,'prepare-target.js'),'utf8'));
  await new Promise(resolve=>setImmediate(resolve));
  const option=get('simple-target').options.find(item=>item.value===host);
  assert.equal(option.disabled,false);
  get('simple-target').value=host;run('render()');
  assert.equal(get('simple-target').value,host);
  assert.equal(get('prepare-target-start').disabled,false);
  assert.equal(get('simple-submit').disabled,true);
  await get('prepare-target-start').onclick();
  assert.equal(get('prepare-target-confirm').open,true);
  assert.equal(calls.filter(x=>x.route.endsWith('/preview')).length,1);
  get('prepare-target-cancel').onclick();
  run(`simpleConfig.bindings[0].targetServers['172.30.30.59']='old-offline-target';render();`);
  get('simple-target').value=host;await get('simple-target').onchange();
  assert.equal(calls.filter(x=>x.route.startsWith('/selections')).at(-1).route,'/selections?applicationId=app');
  assert.equal(get('simple-package').options.some(x=>x.value==='point'),true);
  get('simple-package').value='point';get('simple-package').onchange();
  assert.equal(get('prepare-target-start').disabled,false);
  assert.equal(get('simple-submit').disabled,true);

  preparedHistory=[record('READY')];await get('prepare-target-history-refresh').onclick();
  run(`simpleConfig.bindings[0].targetServers['172.30.30.59']='new-target';render();`);
  get('simple-target').value=host;await get('simple-target').onchange();
  assert.equal(calls.filter(x=>x.route.startsWith('/selections')).at(-1).route,
    '/selections?applicationId=app&targetConfigRef=new-target');
  targetError=true;await get('simple-target').onchange();
  assert.equal(get('simple-submit').disabled,true);
  assert.equal(get('problem').hidden,false);
  targetError=false;

  run(`records=[{request:{action:'RESTORE',targetConfigRef:'new-target'},spugHistoryId:1}];render();`);
  get('simple-target').value=host;await get('simple-target').onchange();
  assert.equal(calls.filter(x=>x.route.startsWith('/selections')).at(-1).route,'/selections?applicationId=app');

  sourceError=true;
  run(`simpleConfig.bindings[0].targetServers['172.30.30.59']='old-offline-target';render();`);
  get('simple-target').value=host;await get('simple-target').onchange();
  assert.equal(get('prepare-target-start').disabled,true);
  assert.equal(get('simple-package').options.some(x=>x.value==='point'),false);
  assert.equal(get('problem').hidden,false);
});
