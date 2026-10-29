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
const remote={deploymentBlocks:{candidate:{}},application:{id:'intruoyi',name:'IntRuoyi',runtimeKind:'remote-intruoyi',repo:'E:/IntRuoyi',targets:{test:{label:'实际测试服 .58',url:'http://test.example.invalid'},prod:{label:'实际正式服 .57',url:'http://prod.example.invalid',acceptanceUrl:'http://accept.example.invalid/private'},backup:{label:'实际备用服 .59',url:'http://backup.example.invalid'},rehearsal:{label:'独立验证机',url:'http://verify.example.invalid'}},capabilities:{initializeBaseline:false,auditBaseline:false,registerTargets:true,buildRelease:true,prepareRehearsal:false},capabilityReasons:{prepareRehearsal:'尚未配置真实隔离目标'},packageStoragePath:'E:/ReleasePackages',nasPath:'//nas/releases'},packages:[candidate],jobs:[],environments:{test:{releaseTag:'baseline-test',baselineStatus:'registered',maintenance:false,observedAt:'2026-10-21T20:00:00+08:00',backendHealth:'UP',frontendHttpStatus:200,migrationCount:3,imageIds:{backend:'sha256:backend',frontend:'sha256:frontend'},schemaSha256:'schema-hash',fingerprint:'fingerprint'},prod:{releaseTag:'baseline-prod',baselineStatus:'registered',maintenance:true},backup:{error:'SSH read refused',maintenanceUnknown:true}}};
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
const demo={deploymentBlocks:{candidate:{}},application:{id:'release-inventory',name:'物品台账',repo:'repo',ports:{test:18201,prod:18202,backup:18203,rehearsal:18204}},packages:[candidate],jobs:[],environments:{test:{releaseTag:'baseline',maintenance:false}}};
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

// A preparation prerequisite failure owns no remote isolation cleanup.
const preEffect=harness();preEffect.set(JSON.parse(JSON.stringify(remote)));
preEffect.evaluate("state.jobs=[{id:'JOB-precheck',action:'prepare-rehearsal',status:'failed',releaseTag:'candidate',payload:{},logs:[]}]");
assert(preEffect.render(7).includes('核对前置失败并结束本次任务，保留失败记录'));
assert(!preEffect.render(7).includes('清除本次隔离环境并保留失败记录'));
for(const flags of [{effectsStarted:true},{remoteStatusRequired:true},{effectsStarted:true,remoteStatusRequired:true}]){
 preEffect.evaluate(`state.jobs[0].effectsStarted=${!!flags.effectsStarted};state.jobs[0].remoteStatusRequired=${!!flags.remoteStatusRequired}`);
 assert(preEffect.render(7).includes('核对源服与远端停止证据，清除本次隔离环境并保留失败记录'));
 assert(!preEffect.render(7).includes('核对前置失败并结束本次任务，保留失败记录'));
}
console.log('Pre-effect preparation failure copy excludes cleanup only when both remote effect markers are absent');

// Retained production-origin copies have one explicit startup-tail retry, not a new restore.
const preparation=harness();preparation.set(JSON.parse(JSON.stringify({...remote,packages:[{...candidate,stage:'tested'}]})));
preparation.evaluate("state.jobs=[{id:'JOB-prepare',action:'prepare-rehearsal',target:'rehearsal',sourceEnv:'prod',status:'failed',effectsStarted:true,remoteStatusRequired:true,remotePhase:'restore-starting',remoteProgress:{jobId:'JOB-prepare',status:'failed',phase:'failed'},releaseTag:'candidate',payload:{},logs:[]}]");
assert(preparation.render(7).includes('核对恢复进度并继续原副本'));
assert(preparation.render(7).includes('禁止重复导入'));
assert(preparation.render(7).includes('资源尚未创建则继续原副本首次恢复'));
assert(preparation.render(7).includes('成功后仅登记隔离基线，候选升级仍需单独执行'));
assert(!/data-job-id="JOB-prepare"[^>]*disabled/.test(preparation.render(7)));
for(const status of ['running','unknown']){
 preparation.evaluate(`state.jobs[0].remoteProgress.status='${status}'`);
 assert(!preparation.render(7).includes('<option value="retry"'),'Unconfirmed original remote outcome must not expose startup-tail retry');
}
preparation.evaluate("state.jobs[0].remoteProgress.status='failed';state.jobs[0].remotePhase='capture-complete'");
assert(!preparation.render(7).includes('<option value="retry"'),'Capture/transfer failure is not a retained startup tail');
preparation.evaluate("state.jobs[0].remotePhase='restore-starting';state.jobs[0].sourceEnv='backup'");
assert(!preparation.render(7).includes('<option value="retry"'),'Only production-origin isolation is eligible');
preparation.evaluate("state.jobs[0].sourceEnv='prod';state.jobs.push({id:'JOB-preparation-retry',action:'resolve-task',target:'rehearsal',sourceEnv:'prod',originalPreparationJobId:'JOB-prepare',releaseTag:'candidate',status:'interrupted',effectsStarted:true,payload:{decision:'retry'},logs:[]})");
assert.equal(preparation.evaluate('preparationTailRoot(state.jobs[1]).id'),'JOB-prepare');
assert(!/data-job-id="JOB-preparation-retry"[^>]*disabled/.test(preparation.render(7)),'Lost retry response can be explicitly reconciled against remote worker/receipt evidence');
preparation.evaluate("state.jobs[1].releaseTag='another'");
assert.equal(preparation.evaluate('preparationTailRoot(state.jobs[1])'),null);
preparation.evaluate("state.jobs[1].releaseTag='candidate';state.jobs[0].remoteProgress.jobId='another'");
assert.equal(preparation.evaluate('preparationTailRoot(state.jobs[1])'),null);
console.log('Preparation tail entry binds failed original job/source/package and keeps interrupted retry children recoverable');

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

// Same-package continuation is an explicit test-only technical action, never acceptance.
const tail=harness();tail.set(JSON.parse(JSON.stringify({...remote,packages:[{...candidate,stage:'built'}]})));
tail.evaluate("state.jobs=[{id:'JOB-original',action:'publish-test',target:'test',status:'failed',effectsStarted:true,releaseTag:'candidate',error:'acceptance port unavailable',payload:{},logs:[]}]");
let tailHtml=tail.render(7);
assert(tailHtml.includes('继续同包测试部署收尾'));
assert(tailHtml.includes('不重跑 SQL、不重新备份，发布成功以三项技术检查为准'));
assert(tailHtml.includes('开放阶段失败须先核对实际启动结果；只有原候选健康且身份一致才可继续，其他情况停止处理。'));
assert(!tailHtml.includes('已进入开放阶段的失败须先技术恢复'));
assert(!/data-job-id="JOB-original"[^>]*disabled/.test(tailHtml));
assert(/data-action="mark-tested" disabled/.test(tail.render(3)),'Tail action must not grant functional acceptance');
tail.evaluate("state.jobs.push({id:'JOB-retry',action:'resolve-task',target:'test',status:'interrupted',effectsStarted:true,originalDeploymentJobId:'JOB-original',releaseTag:'candidate',payload:{decision:'retry'},logs:[]})");
tailHtml=tail.render(7);
assert(!/data-job-id="JOB-retry"[^>]*disabled/.test(tailHtml),'Failed linked continuation remains actionable');
assert.equal(tail.evaluate("testTailRoot(state.jobs[1]).id"),'JOB-original');
tail.evaluate("state.jobs[1].releaseTag='different'");
assert.equal(tail.evaluate('testTailRoot(state.jobs[1])'),null,'Other package cannot inherit continuation');
tail.evaluate("state.jobs=[{id:'JOB-prod',action:'promote-prod',target:'prod',status:'failed',effectsStarted:true,releaseTag:'candidate',payload:{},logs:[]}]");
assert(!tail.render(7).includes('<option value="retry"'),'No production continuation option');
tail.evaluate("state.jobs[0].action='promote-backup';state.jobs[0].target='backup'");
assert(!tail.render(7).includes('<option value="retry"'),'No backup continuation option');
console.log('Test-only same-package tail continuation and failed-child recovery remain separate from functional acceptance');

// Formal technical checks remain separate from explicit business acceptance.
const technical=harness();technical.set(JSON.parse(JSON.stringify({...remote,jobs:[],packages:[{...candidate,stage:'test-deployed'}]})));
for(const page of [3,4,5,6]){
 const html=technical.render(page);
 assert(html.includes('重新执行三项技术检查'));
 assert.equal(html.includes('id="accept-note"'),[5,6].includes(page),'Formal targets require a business acceptance note');
 assert.equal(html.includes('data-action="reject-acceptance"'),[5,6].includes(page),'Formal targets support rejecting business acceptance');
 assert(html.includes('Playwright 真实认证登录并进入页面'));
}
assert.equal(technical.evaluate("technicalEvidence(pkg(),'test').status"),'pending');
technical.evaluate(`state.jobs=[{id:'JOB-check',target:'test',action:'mark-tested',status:'running',releaseTag:'candidate',payload:{},logs:[]}];state.packages[0].outcomes={test:{deployment:{status:'succeeded'},technical:{env:'test',jobId:'JOB-check',releaseTag:'candidate',packageSha256:'package-hash',status:'running',checks:{version:{status:'passed'},upgrade:{status:'running'},login:{status:'pending'}}}}}`);
assert.equal(technical.evaluate("technicalEvidence(pkg(),'test').checks.map(x=>x.status).join(',')"),'passed,running,pending');
assert(technical.render(3).includes('进行中'));
technical.evaluate("state.packages[0].outcomes.test.technical.status='passed'");
assert.equal(technical.evaluate("technicalEvidence(pkg(),'test').status"),'pending','Overall success cannot substitute for missing check evidence');
technical.evaluate("state.jobs[0].status='succeeded';state.packages[0].outcomes.test.technical.checks.upgrade.status='passed';state.packages[0].outcomes.test.technical.checks.login.status='passed'");
assert.equal(technical.evaluate("technicalEvidence(pkg(),'test').status"),'passed');
technical.evaluate("state.jobs[0].target='prod'");
assert.equal(technical.evaluate("technicalEvidence(pkg(),'test').checks.map(x=>x.status).join(',')"),'pending,pending,pending','Evidence owner must belong to this environment');
technical.evaluate("state.jobs[0].target='test';state.packages[0].stage='tested'");
assert(!/data-action="mark-tested" disabled/.test(technical.render(3)),'An already promoted technical stage can be rechecked explicitly');
technical.evaluate("state.packages[0].stage='test-deployed'");
for(const field of ['releaseTag','packageSha256','env','jobId']){
 technical.evaluate(`state.packages[0].outcomes.test.technical.${field}=${field==='jobId'?"''":"'wrong'"}`);
 assert.equal(technical.evaluate("technicalEvidence(pkg(),'test').checks.map(x=>x.status).join(',')"),'pending,pending,pending',field+' must bind evidence');
 technical.evaluate(`state.packages[0].outcomes.test.technical.${field}=${JSON.stringify({releaseTag:'candidate',packageSha256:'package-hash',env:'test',jobId:'JOB-check'}[field])}`);
}
technical.evaluate("state.packages[0].outcomes.test.technical.status='failed';state.packages[0].outcomes.test.technical.phase='opening';state.packages[0].outcomes.test.technical.opening={status:'failed',error:'port <unavailable>'}");
assert(technical.render(3).includes('入口开放失败：port &lt;unavailable&gt;'));
assert.equal(technical.evaluate("technicalEvidence(pkg(),'test').status"),'failed','Passed three checks do not hide failed opening');

// Old business failure stays visible and permits only the matching technical recheck.
technical.evaluate(`state.jobs=[{id:'JOB-reject',action:'reject-acceptance',target:'test',status:'failed',releaseTag:'candidate',error:'old business problem',payload:{note:'preserved business note'},logs:[]}];state.packages[0].acceptances=[{action:'reject-acceptance',jobId:'JOB-reject',env:'test',note:'preserved business note'}]`);
assert(!/data-action="mark-tested" disabled/.test(technical.render(3)));
technical.evaluate("state.packages[0].acceptances[0].env='prod'");
assert(/data-action="mark-tested" disabled/.test(technical.render(3)),'An unbound old rejection is not presumed to be a test business failure');
technical.evaluate("state.packages[0].acceptances[0].env='test'");
assert(technical.render(3).includes('历史业务记录（不属于当前发布成功判据）'));
assert(technical.render(3).includes('old business problem'));
assert(technical.render(3).includes('preserved business note'));
assert(technical.evaluate("action('next','promote-prod',true)").includes('disabled'),'Unreconciled failure cannot authorize next environment');
assert(technical.evaluate("action('wrong environment','accept-prod',true)").includes('disabled'));
technical.evaluate("state.jobs.push({id:'JOB-sql',action:'publish-test',target:'test',status:'failed',releaseTag:'candidate',effectsStarted:true,payload:{},logs:[]})");
assert(/data-action="mark-tested" disabled/.test(technical.render(3)),'Unrelated migration/deployment failure remains blocked');
technical.evaluate("state.jobs.pop();state.jobs.push({id:'JOB-check',action:'mark-tested',target:'test',status:'failed',releaseTag:'candidate',technicalVerification:JSON.parse(JSON.stringify(state.packages[0].outcomes.test.technical)),payload:{},logs:[]})");
assert(!/data-action="mark-tested" disabled/.test(technical.render(3)),'Bound technical failure permits fresh checks');
technical.evaluate("state.packages[0].outcomes.test.deployment.status='failed'");
assert(/data-action="mark-tested" disabled/.test(technical.render(3)),'A failed deployment cannot be bypassed by a technical proof marker');
technical.evaluate("state.packages[0].outcomes.test.deployment.status='succeeded'");
technical.evaluate("state.packages[0].technicalHistory=[JSON.parse(JSON.stringify(state.packages[0].outcomes.test.technical))];state.jobs.push({id:'JOB-check-2',action:'mark-tested',target:'test',status:'failed',releaseTag:'candidate',payload:{},logs:[]});state.packages[0].outcomes.test.technical.jobId='JOB-check-2';state.jobs[2].technicalVerification=JSON.parse(JSON.stringify(state.packages[0].outcomes.test.technical))");
assert(!/data-action="mark-tested" disabled/.test(technical.render(3)),'Earlier failed checks must not permanently block a second retry');
technical.evaluate("state.jobs[2].status='interrupted'");
assert(/data-action="mark-tested" disabled/.test(technical.render(3)),'Unknown/interrupted effects require technical handling');

// A bare reconciliation marker is insufficient; preserve the failed history after proof.
technical.evaluate("state.jobs=[state.jobs[0],{id:'JOB-verified',action:'mark-tested',target:'test',status:'succeeded',releaseTag:'candidate',payload:{},logs:[]}];state.jobs[0].reconciledBy='JOB-verified'");
assert.equal(technical.evaluate('unresolved(state.jobs[0])'),true);
technical.evaluate("state.packages[0].outcomes.test.technical.jobId='JOB-verified';state.packages[0].outcomes.test.technical.status='passed';delete state.packages[0].outcomes.test.technical.opening;delete state.packages[0].outcomes.test.technical.phase");
assert.equal(technical.evaluate('unresolved(state.jobs[0])'),false);
assert.equal(technical.evaluate('state.jobs[0].status'),'failed');
assert(technical.render(7).includes('后续真实技术检查已通过：JOB-verified；本条原失败记录保留。'));
assert(technical.render(7).includes('old business problem'));
technical.evaluate("state.packages[0].outcomes.test.technical.checks.login.status='pending'");
assert.equal(technical.evaluate('unresolved(state.jobs[0])'),true,'Missing real login must not clear historical blocking state');

const unchanged=harness();unchanged.set(JSON.parse(JSON.stringify({...demo,packages:[{...candidate,stage:'test-deployed'}]})));
assert(unchanged.render(3).includes('id="accept-note"'));
assert(unchanged.render(3).includes('data-action="reject-acceptance"'));
assert(!unchanged.render(3).includes('重新执行三项技术检查'));
console.log('Remote three-check evidence, exact failure retry scope, immutable business history and demo isolation passed');

// Exercise the existing click handler without a note textarea or network requests.
(async()=>{
 const click=harness();click.set(JSON.parse(JSON.stringify({...remote,jobs:[],packages:[{...candidate,stage:'test-deployed'}]})));
 click.evaluate("globalThis.sent=[];api=async(path,payload)=>{sent.push({path,payload});return {}};refresh=async()=>{};");
 const button={disabled:false,dataset:{action:'mark-tested'}};
 await click.listener('click').callback({target:{closest:()=>button}});
 assert.equal(click.evaluate('sent.length'),1);
 assert.equal(click.evaluate('sent[0].path'),'actions/mark-tested');
 assert.equal(click.evaluate('sent[0].payload.releaseTag'),'candidate');
 assert.equal(click.evaluate('sent[0].payload.note'),'执行三项技术检查：版本镜像、迁移启动、真实登录进入页面');
 console.log('Remote technical action submits without reading a manual acceptance note');

// Failed formal release exposes bound recovery; only a restored old version
// exposes the explicit reopen action, and only while admission remains closed.
const recovery=harness();recovery.set(JSON.parse(JSON.stringify({...remote,
 application:{...remote.application,capabilities:{...remote.application.capabilities,releaseRecovery:true,businessAcceptance:true}},
 packages:[{...candidate,stage:'prod-deployed',outcomes:{prod:{deployment:{status:'failed',jobId:'JOB-prod-release'},
 recovery:{status:'pending-acceptance',originalJobId:'JOB-prod-release'}}}}],
 jobs:[{id:'JOB-prod-release',action:'promote-prod',target:'prod',status:'failed',effectsStarted:true,releaseTag:'candidate',
 originState:{releaseTag:'baseline-prod'},migrationExecution:{migrations:[{migrationId:'M001',status:'failed-or-unknown'}]},error:'Migration stopped after partial DDL',logs:[]}],
 environments:{...remote.environments,prod:{...remote.environments.prod,maintenance:true,recoveryPending:true}}})));
const recoveryHtml=recovery.render(5);
for(const text of ['迁移失败与验收失败恢复','M001','失败或结果未知，可能部分生效','恢复本次升级前版本及数据','JOB-prod-release'])
 assert(recoveryHtml.includes(text),`Missing bound recovery entry ${text}`);
assert(/data-action="recover-release"[^>]*disabled/.test(recoveryHtml),'Do not repeat a completed recovery');
assert(!/data-action="accept-recovery"[^>]*disabled/.test(recoveryHtml),'Restored old release needs explicit acceptance/open action');
recovery.evaluate("state.environments.prod.maintenance=false;state.environments.prod.recoveryPending=false");
assert(recovery.render(5).includes('已开放业务的版本不允许直接恢复升级前数据'));
assert(!recovery.render(5).includes('data-action="recover-release"'),'Open business must not show a data-destructive restore action');
console.log('Formal partial-migration recovery actions require pending maintenance and separate old-release acceptance');
})().catch(error=>{console.error(error);process.exitCode=1;});

const captureResume=harness();captureResume.set(JSON.parse(JSON.stringify({...remote,packages:[candidate],jobs:[{id:'JOB-capture',action:'prepare-rehearsal',target:'rehearsal',sourceEnv:'prod',releaseTag:candidate.releaseTag,status:'failed',effectsStarted:true,remoteStatusRequired:true,remotePhase:'capture-complete',remoteProgress:{jobId:'JOB-capture',status:'succeeded',phase:'capture-complete'},logs:[],payload:{}}]})));
assert(captureResume.render(7).includes('继续已捕获副本的传输与恢复'));
assert(captureResume.render(7).includes('不再次停正式服采集'));
captureResume.evaluate("state.jobs[0].remoteProgress.status='running'");
assert(!captureResume.render(7).includes('<option value="retry"'));
captureResume.evaluate("state.jobs[0].remoteProgress.status='succeeded';state.jobs[0].remoteProgress.jobId='other'");
assert(!captureResume.render(7).includes('<option value="retry"'));
console.log('Captured-transfer continuation requires completed matching source worker');

// The UI consumes the executor's decision; it never derives order from rows or commits.
const stale=harness();stale.set(JSON.parse(JSON.stringify({...remote,jobs:[],packages:[{...candidate,stage:'rehearsal-passed'}],deploymentBlocks:{candidate:{'promote-prod':'STALE_RELEASE: current production is newer'}}})));
assert(/data-action="promote-prod" disabled/.test(stale.render(5)));
assert(stale.render(5).includes('STALE_RELEASE: current production is newer'));
stale.evaluate("state.deploymentBlocks.candidate={}");
assert(!/data-action="promote-prod" disabled/.test(stale.render(5)));
stale.evaluate("delete state.deploymentBlocks");
assert(/data-action="promote-prod" disabled/.test(stale.render(5)),'Missing ordering decision must block normal publish');
console.log('Stale candidate buttons disabled with server-provided reasons; unknown ordering blocks');

const prerequisite=harness();prerequisite.set(JSON.parse(JSON.stringify({...remote,
 application:{...remote.application,capabilities:{...remote.application.capabilities,releasePrecheck:true}},
 packages:[{...candidate,stage:'built'}],jobs:[{id:'JOB-check',action:'check-prerequisites',releaseTag:'candidate',status:'failed',
 payload:{operation:'publish-test',releaseTag:'candidate'},logs:[],result:{status:'failed',checks:[{label:'NAS',status:'failed',detail:'<script>unsafe</script>'}],limits:'No deployment'}}]})));
assert(prerequisite.render(3).includes('data-precheck-result="JOB-check"'));
assert(prerequisite.render(3).includes('&lt;script&gt;unsafe&lt;/script&gt;'));
assert(!/data-action="publish-test" disabled/.test(prerequisite.render(3)),'Diagnostic failure must not become an unresolved deployment');
prerequisite.render(5);
assert(!prerequisite.evaluate('precheckPanel()').includes('data-precheck-result="JOB-check"'),'Test check is not production evidence');
assert(!prerequisite.render(7).includes('data-interruption="JOB-check"'));
prerequisite.evaluate("state.jobs[0].status='running'");
assert(/data-action="check-prerequisites" disabled/.test(prerequisite.render(3)));
prerequisite.set(demo);assert(!prerequisite.render(3).includes('data-action="check-prerequisites"'));
(async()=>{
 const click=harness();click.set(JSON.parse(JSON.stringify({...remote,packages:[candidate],backupRetries:{candidate:'JOB-original'}})));
 click.render(6);click.evaluate("globalThis.sent=[];api=async(path,payload)=>{sent.push({path,payload});return {}};refresh=async()=>{};");
 await click.listener('click').callback({target:{closest:()=>({disabled:false,dataset:{action:'check-prerequisites'}})}});
 assert.equal(click.evaluate('sent[0].payload.operation'),'promote-backup');
 assert.equal(click.evaluate('sent[0].payload.retryOf'),'JOB-original');
 assert.equal(click.evaluate('sent[0].payload.releaseTag'),'candidate');
 assert.equal(click.evaluate('sent[0].path'),'actions/check-prerequisites');
 console.log('Prerequisite result scope, escaping, retry binding, task exclusion and demo isolation passed');
})().catch(error=>{console.error(error);process.exitCode=1;});

// Production acceptance must not hide recovery for a later partial backup failure.
const backup=harness();backup.set(JSON.parse(JSON.stringify({...remote,
 application:{...remote.application,capabilities:{...remote.application.capabilities,releaseRecovery:true,independentBackupRetry:true,interruptionReconciliation:true}},
 packages:[{...candidate,stage:'prod-accepted',outcomes:{prod:{acceptance:{status:'passed'}},backup:{deployment:{status:'failed',jobId:'JOB-backup'}}}}],
 jobs:[{id:'JOB-backup',action:'promote-backup',target:'backup',releaseTag:'candidate',status:'failed',effectsStarted:true,logs:[],payload:{}}],
 environments:{prod:{releaseTag:'candidate',maintenance:false},backup:{releaseTag:'old',maintenanceUnknown:true}},
 backupRetries:{candidate:null}
})));
assert(backup.render(6).includes('data-recovery="JOB-backup"'),'Partial backup migration must expose its own recovery despite prod-accepted stage');
assert(!/data-action="recover-release"[^>]*disabled/.test(backup.render(6)));
assert(!backup.render(6).includes('data-retry-of='),'Unrestored partial migration cannot offer a retry');
backup.evaluate("state.packages[0].stage='backup-restored';state.jobs[0].resolution={decision:'restored'};state.environments.backup={releaseTag:'old',maintenance:false};state.backupRetries.candidate='JOB-backup'");
assert(/data-action="promote-backup" data-retry-of="JOB-backup"/.test(backup.render(6)));
assert(!/data-action="promote-backup" data-retry-of="JOB-backup" disabled/.test(backup.render(6)));
backup.evaluate("state.packages[0].stage='completed';state.packages[0].outcomes.backup.acceptance={status:'passed'};state.backupRetries.candidate=null");
assert(!backup.render(6).includes('data-recovery="JOB-backup"'));
assert(!backup.render(6).includes('data-retry-of='));

(async()=>{
 const click=harness();click.set(JSON.parse(JSON.stringify({...remote,packages:[candidate]})));
 click.evaluate("globalThis.sent=[];api=async(path,payload)=>{sent.push({path,payload});return {}};refresh=async()=>{};");
 const button={disabled:false,dataset:{action:'promote-backup',retryOf:'JOB-backup-original'}};
 await click.listener('click').callback({target:{closest:()=>button}});
 assert.equal(click.evaluate('sent.length'),1);
 assert.equal(click.evaluate('sent[0].path'),'actions/promote-backup');
 assert.equal(click.evaluate('sent[0].payload.retryOf'),'JOB-backup-original');
 assert.equal(click.evaluate('sent[0].payload.releaseTag'),'candidate');
 assert.equal(click.evaluate('sent[0].payload.applicationId'),'intruoyi');
 console.log('Partial backup recovery visible; independent retry binds original task, selected package and application');
})().catch(error=>{console.error(error);process.exitCode=1;});

// Artifact cleanup groups select only unprotected members and bind the original scan.
const artifacts=harness();artifacts.set(JSON.parse(JSON.stringify({...remote,
 application:{...remote.application,capabilities:{...remote.application.capabilities,artifactRetention:true}},
 jobs:[{id:'JOB-scan',action:'scan-artifacts',status:'succeeded',payload:{keepLatest:3},logs:[],result:{complete:true,keepLatest:3,errors:[],items:[
 {id:'file1',location:'nas',releaseTag:'old',kind:'file',root:'root',file:{relative:'release.tar'},bytes:1073741824,reasons:[]},
 {id:'file2',location:'nas',releaseTag:'old',kind:'file',root:'root',file:{relative:'release.tar'},bytes:1073741824,reasons:['protected']},
 {id:'file3',location:'prod',releaseTag:'current',kind:'image',reference:'current:tag',bytes:null,reasons:['current runtime']}]}}]})));
let artifactHtml=artifacts.render(9);
assert(artifactHtml.includes('2.00 GiB'));
assert(artifactHtml.includes('1 可清理 / 1 保护'));
assert(/data-action="clean-artifacts" disabled/.test(artifactHtml));
artifacts.dispatch('change',{dataset:{artifactGroup:'nas:old'},checked:true});
assert.equal(artifacts.evaluate('artifactSelection(artifactScan()).join()'),'file1');
assert(!/data-action="clean-artifacts" disabled/.test(artifacts.render(9)));
artifacts.evaluate("state.jobs.unshift({id:'JOB-clean',action:'clean-artifacts',status:'failed',payload:{scanJobId:'JOB-scan'},result:{removed:['file1']},logs:[]})");
assert(/data-action="clean-artifacts" disabled/.test(artifacts.render(9)),'A consumed scan cannot be replayed');
assert.equal(artifacts.evaluate('unresolved(state.jobs[0])'),false);
artifacts.set(demo);assert(!artifacts.render(9).includes('data-action="scan-artifacts"'));
console.log('Artifact grouping, protected member exclusion, persisted selections and single-use cleanup passed');

// A failed sealed build can be republished even before any candidate was registered.
const nasRetry=harness();nasRetry.set(JSON.parse(JSON.stringify(remote)));
nasRetry.evaluate("state.application.capabilities.nasPackageRetry=true;state.packages=[];state.jobs=[{id:'build-failed',action:'build-release',status:'failed',releaseTag:'2026-10-29-13-43-28',currentStep:'publish-original-package-to-nas',payload:{},logs:[]}]");
assert(nasRetry.render(7).includes('校验原包并重新上传 NAS'));
assert(!/data-job-id="build-failed"[^>]*disabled/.test(nasRetry.render(7)));
nasRetry.evaluate("state.jobs[0].currentStep='compile-backend'");
assert(!nasRetry.render(7).includes('校验原包并重新上传 NAS'));
console.log('Sealed-build NAS retry entry: available without registered package, excluded before sealing');
