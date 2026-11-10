'use strict';
// Local contract/files only. No browser, network, credentials or actual preflight.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),vm=require('node:vm'),crypto=require('node:crypto');
const source=fs.readFileSync(path.join(__dirname,'automatic_incremental_ui_acceptance.cjs'),'utf8');
const SOURCE='intruoyi-57-safe-20261024-v1',CYCLE='main-20261110-r6';
const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const save=(root,name,value)=>{const raw=Buffer.from(JSON.stringify(value));fs.writeFileSync(path.join(root,name),raw);return {file:name,bytes:raw.length,sha256:hash(raw)};};
function contracts(root=__dirname,argv=[]){
 const context=vm.createContext({require,__dirname:root,process:{argv:['node','driver',...argv]},console,Buffer});
 vm.runInContext(source.slice(0,source.lastIndexOf('\nmain().catch'))+'\nglobalThis.contract={args,artifactPaths,validateGate,validateMainDeploymentContract,validateMainBaseline,validateReceiptDeployment,validateCycleBinding,exclusive};',context);
 return context.contract;
}
function fixture(root,phase='submit'){
 const local=name=>({file:name,bytes:10,sha256:'a'.repeat(64)}),remote=name=>({path:'/opt/main/'+name,bytes:20,sha256:'b'.repeat(64)});
 const selection={schemaVersion:'TaskMainProgramInstallations/v4',sourceCommit:'1'.repeat(40),controlGenerationPin:local('control.json'),spugInstallationPin:local('spug.json'),verificationInputsPin:local('verification.json')};
 const selectionPin=save(root,'main-selection.json',selection);
 const expected={applicationId:'main-app',sourceConfigRef:SOURCE,operationId:phase==='verify'?'original-operation-123':null,
  plan:{state:'READY',parentChainRef:'existing-main-parent',baseFullRef:'existing-main-full',planDigest:'c'.repeat(64)}};
 const options={kind:'I1',phase,cycle:CYCLE,selection:path.join(root,'main-selection.json'),preflight:path.join(root,'gate.json'),execute:phase==='submit'};
 const gate={schemaVersion:'MainProgramAutomaticIncrementalUiPreflight/v1',status:'PASS',experiencePreflight:'PASS',kind:'I1',phase,
  cycle:CYCLE,origin:'http://127.0.0.1:18080',server:'172.30.30.57',mode:'safe',applicationId:expected.applicationId,sourceConfigRef:SOURCE,
  expectedPlan:expected.plan,implementationCommit:selection.sourceCommit,installationCommit:selection.sourceCommit,buildCommit:selection.sourceCommit,
  spugCommit:'2'.repeat(40),deploymentSelectionPin:{...selectionPin},controlGenerationPin:{...selection.controlGenerationPin},spugInstallationPin:{...selection.spugInstallationPin},
  sourceCaptureConfigurationPin:remote('capture.json'),sourceOwnerConfigurationPin:remote('owner.json'),mainDeploymentVerified:true,
  observedAt:new Date().toISOString(),expectedUserLabel:'Administrator',sourceIdentityVerified:true,installationVerified:true,sourceServicesHealthy:true,
  archiveReady:true,capacityReady:true,noConcurrentMaintenance:true,sourceIdleVerified:true};
 const baseline={schemaVersion:'MainProgramAutomaticIncrementalUiBaseline/v1',status:'PASS',cycle:CYCLE,observedAt:gate.observedAt,
  applicationId:expected.applicationId,sourceConfigRef:SOURCE,deploymentSelectionPin:selectionPin,expectedPlan:expected.plan,operationId:expected.operationId};
 gate.baselineEvidencePin=save(root,'baseline.json',baseline);save(root,'gate.json',gate);
 return {options,gate,selection,selectionPin,expected,baseline};
}
function temporary(t){const root=fs.mkdtempSync(path.join(os.tmpdir(),'main-cycle-contract-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));return root;}

test('explicit cycle and selection are paired; old arguments remain available',()=>{
 const common=['--kind','I1','--phase','preview','--observation','preview-1','--preflight',path.join(__dirname,'gate.json')];
 assert.equal(contracts(__dirname,common).args().cycle,undefined);
 const options=contracts(__dirname,[...common,'--cycle',CYCLE,'--selection',path.join(__dirname,'main.json')]).args();
 assert.equal(options.cycle,CYCLE);
 for(const extra of [['--cycle',CYCLE],['--selection',path.join(__dirname,'main.json')],['--cycle','../old','--selection',path.join(__dirname,'main.json')],['--cycle',CYCLE,'--selection',path.join(__dirname,'../outside.json')]]){
  assert.throws(()=>contracts(__dirname,[...common,...extra]).args());
 }
});
test('cycles isolate all public/private artifacts and preserve old names',t=>{
 const root=temporary(t),c=contracts(root),base={kind:'I1',phase:'submit',observation:'once'};
 const old=c.artifactPaths(base),a=c.artifactPaths({...base,cycle:CYCLE}),b=c.artifactPaths({...base,cycle:'main-next'});
 assert.equal(path.basename(old.receiptPath),'automatic-i1-ui-submission.json');
 assert.equal(path.basename(old.terminalPath),'automatic-i1-ui-terminal.json');
 for(const key of ['receiptPath','terminalPath','resultPath','screenshot','kindSession']){assert.notEqual(a[key],old[key]);assert.notEqual(a[key],b[key]);}
 assert.equal(path.basename(a.receiptPath),'automatic-main-20261110-r6-i1-ui-submission.json');
 c.exclusive(a.receiptPath,{operationId:'original'});
 assert.throws(()=>c.exclusive(a.receiptPath,{operationId:'replacement'}),/EEXIST/);
 assert.equal(JSON.parse(fs.readFileSync(a.receiptPath)).operationId,'original');
 assert.equal(fs.existsSync(old.receiptPath),false);
});
test('MAIN gate binds actual v4 and accepts I1 with an existing READY root',t=>{
 const root=temporary(t),c=contracts(root),f=fixture(root);
 c.validateMainDeploymentContract(f.gate,f.options,f.selection,f.selectionPin);
 assert.equal(c.validateGate(f.options,f.expected).gate.cycle,CYCLE);
 assert.equal(fs.existsSync(path.join(root,'automatic-full-ui-terminal.json')),false);
});
test('MAIN deployment mismatch cannot be read through the old contract',t=>{
 const root=temporary(t),c=contracts(root);
 for(const mutate of [f=>f.gate.schemaVersion='AutomaticIncrementalUiPreflight/v2',f=>f.gate.cycle='other',f=>f.selection.schemaVersion='TaskMainProgramInstallations/v3',
  f=>f.gate.implementationCommit='3'.repeat(40),f=>f.gate.spugCommit='invalid',f=>f.gate.mainDeploymentVerified=false,
  f=>f.gate.deploymentSelectionPin.sha256='0'.repeat(64),f=>f.gate.controlGenerationPin={...f.gate.controlGenerationPin,sha256:'0'.repeat(64)},
  f=>f.gate.spugInstallationPin={...f.gate.spugInstallationPin,sha256:'0'.repeat(64)},f=>f.gate.sourceCaptureConfigurationPin=null,
  f=>f.gate.sourceOwnerConfigurationPin={path:'relative',bytes:1,sha256:'b'.repeat(64)}]){
  const f=fixture(root);mutate(f);assert.throws(()=>c.validateMainDeploymentContract(f.gate,f.options,f.selection,f.selectionPin));
 }
});
test('baseline checks every immutable plan field and source/cycle/selection/age',t=>{
 const root=temporary(t),c=contracts(root);
 for(const mutate of [f=>f.baseline.expectedPlan={...f.baseline.expectedPlan,state:'BASELINE_REQUIRED'},f=>f.baseline.expectedPlan={...f.baseline.expectedPlan,parentChainRef:'other'},
  f=>f.baseline.expectedPlan={...f.baseline.expectedPlan,baseFullRef:'other'},f=>f.baseline.expectedPlan={...f.baseline.expectedPlan,planDigest:'0'.repeat(64)},
  f=>f.baseline.sourceConfigRef='other',f=>f.baseline.cycle='other',f=>f.baseline.deploymentSelectionPin={...f.selectionPin,sha256:'0'.repeat(64)},
  f=>f.baseline.observedAt='2000-01-01T00:00:00Z',f=>f.baseline.operationId='unexpected',f=>f.baseline.extra=true]){
  const f=fixture(root);mutate(f);assert.throws(()=>c.validateMainBaseline(f.gate,f.options,f.expected,f.baseline));
 }
});
test('gate reads exact selection/baseline bytes and keeps reviewed preflight immutable',t=>{
 const root=temporary(t),c=contracts(root),f=fixture(root),reviewed=c.validateGate(f.options,f.expected);
 fs.appendFileSync(path.join(root,'baseline.json'),' ');assert.throws(()=>c.validateGate(f.options,f.expected));
 fixture(root);fs.appendFileSync(f.options.selection,' ');assert.throws(()=>c.validateGate(f.options,f.expected));
 fixture(root);fs.appendFileSync(f.options.preflight,' ');assert.throws(()=>c.validateGate(f.options,f.expected,reviewed.hash),/PREFLIGHT_CHANGED/);
});
test('MAIN receipt v3 verifies only same cycle/deployment and the original operation plan',t=>{
 const root=temporary(t),c=contracts(root),f=fixture(root,'verify');
 const receipt={schemaVersion:'AutomaticIncrementalUiSubmission/v3',kind:'I1',cycle:CYCLE,implementationCommit:f.gate.implementationCommit,spugCommit:f.gate.spugCommit,
  ...Object.fromEntries(['deploymentSelectionPin','controlGenerationPin','spugInstallationPin','sourceCaptureConfigurationPin','sourceOwnerConfigurationPin','baselineEvidencePin'].map(k=>[k,f.gate[k]]))};
 c.validateReceiptDeployment(receipt,f.gate,'I1',CYCLE);
 c.validateMainBaseline(f.gate,f.options,f.expected,f.baseline);
 for(const changed of [{cycle:'other'},{schemaVersion:'AutomaticIncrementalUiSubmission/v2'},{sourceCaptureConfigurationPin:{...receipt.sourceCaptureConfigurationPin,sha256:'0'.repeat(64)}}]){
  assert.throws(()=>c.validateReceiptDeployment({...receipt,...changed},f.gate,'I1',CYCLE));
 }
 assert.throws(()=>c.validateReceiptDeployment(receipt,f.gate,'I1'));
 assert.throws(()=>c.validateMainBaseline(f.gate,f.options,f.expected,{...f.baseline,operationId:'another-operation'}));
 assert.throws(()=>c.validateMainBaseline(f.gate,f.options,f.expected,{...f.baseline,expectedPlan:{...f.expected.plan,parentChainRef:'advanced-current-parent'}}));
});
test('headed MAIN path uses ordinary UI actions and retains the durable one-POST guard',()=>{
 assert.match(source,/headless:\s*!options\.cycle/);
 assert.match(source,/await page\.bringToFront\(\)/);
 assert.doesNotMatch(source,/force\s*:\s*true/);
 assert.ok(source.indexOf('exclusive(receiptPath,receipt)')<source.indexOf('report.businessPosts++;'));
 assert.match(source,/armed&&report\.businessPosts===0/);
 assert.match(source,/VERIFY_OTHER_OPERATION_READ_REFUSED/);
 assert.match(source,/await frame\.locator\('#simple-confirm-submit'\)\.click\(\)/);
});
test('MAIN terminal binding also rejects a changed source implementation commit',t=>{
 const root=temporary(t),c=contracts(root),{gate}=fixture(root,'verify');
 const terminal={schemaVersion:'AutomaticIncrementalUiTerminal/v3',kind:'I1',cycle:CYCLE,implementationCommit:gate.implementationCommit,spugCommit:gate.spugCommit,
  ...Object.fromEntries(['deploymentSelectionPin','controlGenerationPin','spugInstallationPin','sourceCaptureConfigurationPin','sourceOwnerConfigurationPin','baselineEvidencePin'].map(k=>[k,gate[k]]))};
 c.validateCycleBinding(terminal,gate,CYCLE);
 assert.throws(()=>c.validateCycleBinding({...terminal,implementationCommit:'3'.repeat(40)},gate,CYCLE));
});
