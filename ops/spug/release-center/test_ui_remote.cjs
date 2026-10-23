'use strict';
// Pure rendering contract checks. Fixture snapshots do not execute HTTP or releases.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'ui/app.js'),'utf8');
function harness(){
 const elements=new Map(),stored=new Map(),listeners=new Map();
 const element=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',disabled:false});return elements.get(id);};
 const storage={getItem:key=>stored.has(key)?stored.get(key):null,setItem:(key,value)=>stored.set(key,value)};
 const context={URLSearchParams,location:{search:'?app=intruoyi'},history:{replaceState:()=>{}},localStorage:storage,sessionStorage:storage,document:{getElementById:element,addEventListener:(name,callback,capture)=>listeners.set(name,{callback,capture}),querySelector:()=>null},fetch:()=>new Promise(()=>{}),setInterval:()=>{},crypto:{randomUUID:()=>''}};
 vm.createContext(context);vm.runInContext(source,context);
 return {dispatch:(name,target)=>listeners.get(name).callback({target}),listener:name=>listeners.get(name),set:snapshot=>{context.inputSnapshot=snapshot;vm.runInContext("state=inputSnapshot;applicationId=state.application.id;applications=[{id:applicationId,name:state.application.name,status:'ready',scope:'scope fixture'}];selected=state.packages[0]?.releaseTag||'';",context);},render:page=>{vm.runInContext(`page=${page};render();`,context);return element('app').innerHTML;},evaluate:expression=>vm.runInContext(expression,context)};
}
const candidate={releaseTag:'candidate',gitCommit:'a'.repeat(40),packageSha256:'package-hash',manifestSha256:'manifest-hash',stage:'function-passed',baseline:false,rehearsals:[]};
const remote={application:{id:'intruoyi',name:'IntRuoyi',runtimeKind:'remote-intruoyi',repo:'E:/IntRuoyi',targets:{test:{label:'实际测试服 .58',url:'http://test.example.invalid'},prod:{label:'实际正式服 .57',url:'http://prod.example.invalid',acceptanceUrl:'http://accept.example.invalid/private'},backup:{label:'实际备用服 .59',url:'http://backup.example.invalid'},rehearsal:{label:'独立验证机',url:'http://verify.example.invalid'}},capabilities:{initializeBaseline:false,auditBaseline:false,registerTargets:true,buildRelease:true,prepareRehearsal:false},capabilityReasons:{prepareRehearsal:'尚未配置真实隔离目标'},packageStoragePath:'E:/ReleasePackages',nasPath:'//nas/releases'},packages:[candidate],jobs:[],environments:{test:{releaseTag:'baseline-test',baselineStatus:'registered',maintenance:false,observedAt:'2026-10-21T20:00:00+08:00',backendHealth:'UP',frontendHttpStatus:200,migrationCount:3,imageIds:{backend:'sha256:backend',frontend:'sha256:frontend'},schemaSha256:'schema-hash',fingerprint:'fingerprint'},prod:{releaseTag:'baseline-prod',baselineStatus:'registered',maintenance:true},backup:{error:'SSH read refused',maintenanceUnknown:true}}};
const h=harness();h.set(remote);
for(let page=0;page<9;page++){
 const html=h.render(page);
 assert(!html.includes('演示'),`Remote page ${page} contains demo copy`);
 assert(!html.includes('127.0.0.1:'),`Remote page ${page} contains demo endpoint`);
 assert(!html.includes('initialize-baseline'),`Remote page ${page} exposes initialization`);
 assert(!html.includes(':undefined'),`Remote page ${page} assumes ports`);
}
const baseline=h.render(8);
for(const text of ['核对并登记三服基线','baseline-test','SSH read refused','sha256:backend','schema-hash','E:/ReleasePackages','//nas/releases','2026-10-21T20:00:00+08:00'])assert(baseline.includes(text),`Missing real snapshot field ${text}`);
assert(!baseline.includes('data-action="audit-baseline"'));
assert(!/data-action="register-targets" disabled/.test(baseline));
assert(h.evaluate("envlink('prod')").includes('http://accept.example.invalid/private'));
assert(!h.evaluate("envlink('prod')").includes('http://prod.example.invalid'));
assert(h.evaluate("envlink('backup')").includes('维护状态待核对'));
h.evaluate("appSession.setItem(sourceKey(),'prod')");
const rehearsal=h.render(4);
assert(rehearsal.includes('尚未配置真实隔离目标'));
assert(/data-action="prepare-rehearsal" disabled/.test(rehearsal));
assert.equal(h.evaluate("capabilityAllowed('upgrade-rehearsal')"),false);
h.evaluate("state.application.capabilities.prepareRehearsal=true;state.environments.rehearsal={releaseTag:'old'}");
const occupied=h.render(4);
assert(/data-action="prepare-rehearsal" disabled/.test(occupied),'Clear the old isolated environment explicitly before preparing another origin');
assert(!/data-action="reset-rehearsal" disabled/.test(occupied),'Remote workflow needs a real explicit reset entry');
h.evaluate("delete state.environments.rehearsal");
h.evaluate("state.application.capabilities.buildRelease=false");
assert.equal(h.evaluate("capabilityAllowed('build-release')"),false);
h.evaluate("state.environments.prod.maintenance=false");
assert(h.evaluate("envlink('prod')").includes('http://prod.example.invalid'));
h.evaluate("state.environments.prod.maintenance=true;delete state.application.targets.prod.acceptanceUrl");
assert(!h.evaluate("envlink('prod')").includes('href='),'No public URL substitute when maintenance acceptance URL is absent');
h.evaluate("selected='';state.packages=[]");
assert(!/data-action="register-targets" disabled/.test(h.render(8)),'Registration must not depend on candidate selection');
h.evaluate("state.jobs=[{id:'running',action:'register-targets',status:'running',logs:[]}]");
assert(/data-action="register-targets" disabled/.test(h.render(8)),'Running task must block registration');
const demo={application:{id:'release-inventory',name:'物品台账',repo:'repo',ports:{test:18201,prod:18202,backup:18203,rehearsal:18204}},packages:[candidate],jobs:[],environments:{test:{releaseTag:'baseline',maintenance:false}}};
h.set(demo);
for(let page=0;page<9;page++)h.render(page);
assert(h.render(0).includes('127.0.0.1:18201'));
assert(h.render(0).includes('演示正式服'));
assert(h.render(8).includes('data-action="initialize-baseline"'));
console.log('PASS: remote 9-page target/capability/baseline/storage/maintenance contracts and local demo regression. No HTTP or release actions executed.');

// Test deploys directly; only production has an isolation entry and separate acceptance.
const gate=harness();gate.set(JSON.parse(JSON.stringify({...remote,jobs:[],packages:[{...candidate,stage:'built',rehearsals:[]}]})));
gate.evaluate("state.application.capabilities.prepareRehearsal=true;appSession.setItem(sourceKey(),'test')");
assert(!/data-action="publish-test" disabled/.test(gate.render(3)));
assert(!gate.render(4).includes('id="rehearsal-source"'),'Remote users cannot select test/backup rehearsals');
assert.equal(gate.evaluate('rehearsalSource()'),'prod','Stale stored source cannot affect remote action');
assert(/data-action="prepare-rehearsal" disabled/.test(gate.render(4)));
assert(/data-action="promote-prod" disabled/.test(gate.render(5)));
gate.evaluate("state.packages[0].stage='test-deployed'");
assert(!/data-action="mark-tested" disabled/.test(gate.render(3)));
assert(!gate.render(3).includes('data-action="function-passed"'));
gate.evaluate("state.packages[0].stage='tested'");
assert(!/data-action="prepare-rehearsal" disabled/.test(gate.render(4)));
assert(/data-action="promote-prod" disabled/.test(gate.render(5)));
gate.evaluate("state.packages[0].activeRehearsal='prod-check';state.packages[0].rehearsals=[{id:'prod-check',source:'prod',status:'upgraded',packageSha256:'package-hash',originFingerprint:'fingerprint'}]");
assert(!/data-action="accept-rehearsal" disabled/.test(gate.render(4)));
assert(!gate.render(4).includes('data-action="mark-tested"'));
gate.evaluate("state.packages[0].stage='rehearsal-passed'");
assert(!/data-action="promote-prod" disabled/.test(gate.render(5)));
assert(/data-action="promote-backup" disabled/.test(gate.render(6)));
gate.evaluate("state.packages[0].stage='prod-accepted'");
assert(!/data-action="promote-backup" disabled/.test(gate.render(6)));
console.log('Direct test, actual test acceptance, production-only rehearsal and direct backup rendering checks passed');

// The transport result and the remote stage must remain separate in the UI.
const progress=harness();progress.set(JSON.parse(JSON.stringify(remote)));
progress.evaluate("state.jobs=[{id:'JOB-0123456789',action:'prepare-rehearsal',status:'interrupted',effectsStarted:true,releaseTag:'candidate',remoteStatusRequired:true,remoteProgress:{status:'running',phase:'restore-starting',observedAt:'2026-10-22'},payload:{},logs:[]}]");
assert(progress.render(7).includes('远端仍在执行'));
assert(/data-job-id="JOB-0123456789"[^>]*disabled/.test(progress.render(7)));
progress.evaluate("state.jobs[0].remoteProgress.status='failed'");
assert(progress.render(7).includes('远端阶段失败'));
progress.evaluate("state.jobs[0].remoteStatusError='ConnectionError'");
assert(progress.render(7).includes('查询失败，结果待核实'));
console.log('Remote task progress is visible without declaring overall preparation success');

// Persisted scope exclusions must be visible without exposing arbitrary SQL fields.
const plans=harness();plans.set(JSON.parse(JSON.stringify(remote)));
plans.evaluate(`state.jobs=[{id:'JOB-plan',action:'publish-test',status:'succeeded',releaseTag:'candidate',payload:{},logs:[],migrationPlan:{targetEnvironment:'test',publishScope:'app-release',items:[
 {migrationId:'cleaning-process',action:'SKIP_SCOPE_EXCLUDED',reason:'app-release is not allowed: fixed site data <sensitive-tag>',allowedPublishScopes:['with-data'],sql:'DO NOT DISPLAY SQL'},
 {migrationId:'schema-change',action:'APPLY',reason:'Missing migration',allowedPublishScopes:[]}
]}}]`);
const planHtml=plans.render(7);
assert(planHtml.includes('<details class="migration-plan" data-plan-key="releaseCenter:intruoyi:migrationPlan:JOB-plan"><summary>迁移计划：2 项 · 发布范围排除 1 项'));
for(const text of ['迁移编号','计划动作','原因','适用发布范围','cleaning-process','发布范围排除','执行迁移','with-data','app-release is not allowed: fixed site data &lt;sensitive-tag&gt;'])assert(planHtml.includes(text),`Missing migration plan field ${text}`);
assert(!planHtml.includes('<sensitive-tag>'));
assert(!planHtml.includes('DO NOT DISPLAY SQL'));
assert(!plans.evaluate('migrationPlan({})').includes('<details'),'Old jobs without plans do not invent migration evidence');
console.log('Migration plans expose escaped scope reasons and Chinese actions in collapsed task details');

// Native toggle does not bubble; capture retains each application's per-job expansion.
assert.equal(plans.listener('toggle').capture,true);
const planToggle={tagName:'DETAILS',isConnected:true,dataset:{planKey:'releaseCenter:intruoyi:migrationPlan:JOB-plan'},open:true};
plans.dispatch('toggle',planToggle);
assert(plans.render(7).includes('data-plan-key="releaseCenter:intruoyi:migrationPlan:JOB-plan" open>'));
assert(plans.render(7).includes('data-plan-key="releaseCenter:intruoyi:migrationPlan:JOB-plan" open>'),'Repeated refresh retains expansion');
plans.evaluate("applicationId='another-app';state.application.id='another-app'");
assert(!plans.render(7).includes('data-plan-key="releaseCenter:another-app:migrationPlan:JOB-plan" open>'),'Same job ID in another application remains collapsed');
plans.dispatch('toggle',{...planToggle,isConnected:false,open:false});
plans.evaluate("applicationId='intruoyi';state.application.id='intruoyi'");
assert(plans.render(7).includes('data-plan-key="releaseCenter:intruoyi:migrationPlan:JOB-plan" open>'),'Detached old DOM toggle cannot erase saved state');
plans.dispatch('toggle',{...planToggle,open:false});
assert(!plans.render(7).includes('data-plan-key="releaseCenter:intruoyi:migrationPlan:JOB-plan" open>'),'Explicit collapse persists too');
console.log('Migration plan expansion survives refresh and stays isolated by application and job');
