'use strict';
// Temporary protocol examples only. No browser, HTTP, server or backup execution.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const os=require('node:os'),crypto=require('node:crypto'),vm=require('node:vm'),test=require('node:test');
const acorn=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/acorn');
const HELPER=path.join(__dirname,'verify_goal_readonly.cjs'),source=fs.readFileSync(HELPER,'utf8');
const tree=acorn.parse(source,{ecmaVersion:'latest',sourceType:'script'});
const functions=['parseAuditArguments','sameAuditPin','readAuditTaskFile','preparePointAudit',
 'selectAuditPoints','auditReportFields','verifyPointAuditInputs','assertSelectedPointState',
 'readAuditBoundInput','readCurrentInstallationSummary'];
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const SOURCE='intruoyi-57-safe-20261024-v1',COMMIT='1'.repeat(40),SPUG='2'.repeat(40),MANIFEST='a'.repeat(64);
const ids=[1,2,3,4].map(n=>'smallapp-'+String(n).repeat(32));
function load(task,cliRequire){
 const declarations=functions.map(name=>{
  const matches=tree.body.filter(n=>n.type==='FunctionDeclaration'&&n.id.name===name);
  assert.equal(matches.length,1,'POINT_AUDIT_API_REQUIRED: '+name);
  return source.slice(matches[0].start,matches[0].end);
 }).join('\n');
 const context=vm.createContext({fs,path,crypto,Buffer,TASK:task,sha,require:cliRequire,
  need:(value,code)=>{if(!value)throw Error(code);}});
 vm.runInContext(declarations+'\nthis.api={'+functions.join(',')+'};',context);
 return context.api;
}
const plain=value=>JSON.parse(JSON.stringify(value));
function walk(node,visit){
 if(!node||typeof node!=='object')return;visit(node);
 for(const value of Object.values(node)){
  if(Array.isArray(value))value.forEach(item=>walk(item,visit));
  else if(value&&typeof value==='object')walk(value,visit);
 }
}
function fixture(t){
 const task=fs.mkdtempSync(path.join(os.tmpdir(),'main-point-protocol-'));
 t.after(()=>fs.rmSync(task,{recursive:true,force:true}));
 function put(file,value){
  const raw=Buffer.from(JSON.stringify(value)+'\n','utf8');fs.writeFileSync(path.join(task,file),raw);
  return {file,bytes:raw.length,sha256:sha(raw)};
 }
 const buildPin=put('build.json',{status:'PASS',targetCommit:COMMIT,fileCount:147,fileManifestSha256:MANIFEST});
 const controlGenerationPin=put('generation.json',{schemaVersion:'MainProgramControlGeneration/v1',status:'PASS',sourceCommit:COMMIT,buildPin});
 const spugInstallationPin=put('spug.json',{schemaVersion:'MainProgramSpugInstallation/v1',status:'PASS',sourceCommit:COMMIT});
 const resourceBuildPin=put('resource-build.json',{status:'PASS',sourceCommit:SPUG});
 const transitionCorePin=put('transition.json',{schemaVersion:'MainProgramSpugResourceTransition/v1',status:'PASS',resourceBuildPin});
 const resourceTransitionPin=put('custody.json',{schemaVersion:'MainProgramSpugResourceTransitionReaderCustody/v1',transitionCorePin});
 const verificationInputsPin=put('verification.json',{schemaVersion:'MainProgramSpugPublicationVerificationInputs/v2',resourceTransitionPin});
 const selection={schemaVersion:'TaskMainProgramInstallations/v4',sourceCommit:COMMIT,controlGenerationPin,spugInstallationPin,verificationInputsPin};
 const selectionPin=put('selection.json',selection);
 const baseline={schemaVersion:'MainProgramAutomaticIncrementalUiBaseline/v1',status:'PASS',cycle:'main-fixture-cycle',
  applicationId:SOURCE,sourceConfigRef:SOURCE,deploymentSelectionPin:selectionPin};
 const baselineEvidencePin=put('baseline.json',baseline);
 const chain=ids.map((operationId,i)=>({operationId,pointType:i?'INCREMENTAL':'FULL',
  pointPin:{path:'/protocol-original/'+operationId+'/point.json',bytes:i+100,sha256:String(i+3).repeat(64)}}));
 const audit={schemaVersion:'AutomaticBackupChainAudit/v1',status:'PASS',state:'SUCCEEDED',actualExitCode:0,
  protocolFixtureOnly:true,operationId:ids[3],sourceConfigRef:SOURCE,pointType:'INCREMENTAL',sourceRestored:true,
  uniqueOwnerOperationVerified:true,readback:{payloadContentVerified:true},sourceCommit:COMMIT,spugCommit:SPUG,
  cycle:baseline.cycle,deploymentSelectionPin:selectionPin,controlGenerationPin,spugInstallationPin,baselineEvidencePin,
  package:{variant:'standard',fileCount:147,fileManifestSha256:MANIFEST,allInstalledFilesShaVerified:true},
  generationId:ids[0],pointPin:chain[3].pointPin,parentPointPins:chain.slice(0,-1).map(r=>r.pointPin),chain};
 put('audit.json',audit);
 const args={observation:'r14',pointAudit:'audit.json',selection:'selection.json'};
 const items=ids.map((packageId,i)=>({packageId,status:'indexed',kind:i?'backup-incremental':'backup-full'}));
 items.push({packageId:'old-blocked',status:'indexed',kind:'backup-incremental'});
 // The fixed subprocess boundary below returns a protocol summary. It does not
 // claim these temporary records pass the Python completed native validator.
 const inputPins=fs.readdirSync(task).filter(name=>!['audit.json','baseline.json'].includes(name)).map(name=>{
  const filename=path.join(task,name),raw=fs.readFileSync(filename);return {path:filename,bytes:raw.length,sha256:sha(raw)};
 });
 const summary={schemaVersion:'MainProgramCurrentInstallationSummary/v1',status:'PASS',selectionPin,sourceCommit:COMMIT,
  controlGenerationPin,spugInstallationPin,buildPin,resourceBuildPin,spugCommit:SPUG,inputPins,
  build:{fileCount:147,fileManifestSha256:MANIFEST,packageSha256:'c'.repeat(64)}};
 const cliRequire=name=>{assert.equal(name,'node:child_process');return {spawnSync(exe,argv,options){
  assert.ok(exe.endsWith('/dependencies/python/python.exe'));assert.equal(options.shell,false);
  assert.deepEqual(Array.from(argv),['-B','-X','utf8',path.join(task,'main_program_current_installation.py'),'--selection','selection.json','--public-summary']);
  return {status:0,stdout:JSON.stringify(summary),stderr:''};
 }};};
 return {task,put,selection,selectionPin,audit,baseline,args,items,cliRequire,api:load(task,cliRequire),prepare(){return this.api.preparePointAudit(this.args);}};
}

test('old arguments keep full-matrix mode and new arguments require an explicit pair',()=>{
 const api=load(__dirname);
 assert.deepEqual(plain(api.parseAuditArguments(['--observation','r14'])),{observation:'r14',pointAudit:null,selection:null});
 assert.deepEqual(plain(api.parseAuditArguments(['--selection','selection.json','--observation','r14','--point-audit','audit.json'])),
  {observation:'r14',pointAudit:'audit.json',selection:'selection.json'});
 for(const args of [['--observation','r14','--point-audit','audit.json'],['--observation','r14','--selection','selection.json']])
  assert.throws(()=>api.parseAuditArguments(args),/POINT_AUDIT_SELECTION_PAIR_REQUIRED/);
 for(const args of [[],['--observation','r0'],['--observation','r14','--observation','r15'],['--observation','r14','--unknown','x']])
  assert.throws(()=>api.parseAuditArguments(args),/EXPLICIT_OBSERVATION_REQUIRED/);
});

test('explicit temporary CLI summary protocol binds exact v4 bytes and only its unique new point',t=>{
 const f=fixture(t),scope=f.prepare(),fields=f.api.auditReportFields(scope);
 assert.equal(scope.operationId,ids[3]);assert.deepEqual(plain(scope.chainIds),ids);
 assert.equal(fields.schemaVersion,'SpugSelectedPointReadonlyAudit/v1');assert.equal(fields.scope,'single_verified_point');
 assert.deepEqual(plain(fields.deploymentSelectionPin),f.selectionPin);
 assert.equal(fields.pointAuditPin.file,'audit.json');
 assert.equal(fields.pointAuditPin.sha256,sha(fs.readFileSync(path.join(f.task,'audit.json'))));
 assert.deepEqual(plain(f.api.selectAuditPoints(f.items,scope)),[f.items[3]]);
 f.api.verifyPointAuditInputs(scope);
});

test('legacy selection still includes every indexed backup and never creates a single-point report',t=>{
 const f=fixture(t);assert.equal(f.api.preparePointAudit({observation:'r14',pointAudit:null,selection:null}),null);
 const items=[...f.items,{packageId:'unpublished',status:'unpublished',kind:'backup-full'},
  {packageId:'release',status:'indexed',kind:'release'}];
 assert.deepEqual(plain(f.api.selectAuditPoints(items,null)),f.items);
 assert.deepEqual(plain(f.api.auditReportFields(null)),{schemaVersion:'SpugCompleteGoalReadonlyAudit/v1'});
});

for(const [name,mutate] of [
 ['schema',a=>a.schemaVersion='Unknown/v1'],['status',a=>a.status='RUNNING'],['state',a=>a.state='FAILED'],
 ['exit',a=>a.actualExitCode=2],['typed-exit',a=>a.actualExitCode=false],['source-restored',a=>a.sourceRestored=false],
 ['full-payload',a=>a.readback.payloadContentVerified=false],['source',a=>a.sourceConfigRef='foreign'],
 ['source-commit',a=>a.sourceCommit='3'.repeat(40)],['spug-commit',a=>a.spugCommit='4'.repeat(40)],
 ['cycle',a=>a.cycle='different-cycle'],['package-count',a=>a.package.fileCount=130],
 ['package-verification',a=>a.package.allInstalledFilesShaVerified=false],['package-manifest',a=>a.package.fileManifestSha256='b'.repeat(64)],
 ['selection-bytes',a=>a.deploymentSelectionPin.bytes++],['selection-sha',a=>a.deploymentSelectionPin.sha256='b'.repeat(64)],
 ['control-generation',a=>a.controlGenerationPin.sha256='c'.repeat(64)],['spug-installation',a=>a.spugInstallationPin.sha256='c'.repeat(64)],
 ['unique-operation',a=>a.operationId=ids[0]],['chain-duplicate',a=>a.chain[2].operationId=ids[1]],
 ['chain-parent-prefix',a=>a.parentPointPins=a.parentPointPins.slice(1)],['chain-root',a=>a.chain[0].pointType='INCREMENTAL'],
])test('reject protocol mismatch: '+name,t=>{
 const f=fixture(t);mutate(f.audit);f.put('audit.json',f.audit);
 assert.throws(()=>f.prepare(),/POINT_AUDIT_/);
});

test('v4 exact schema and fields cannot be weakened',t=>{
 const f=fixture(t);f.selection.schemaVersion='TaskCurrentInstallations/v2';
 f.audit.deploymentSelectionPin=f.put('selection.json',f.selection);f.put('audit.json',f.audit);
 assert.throws(()=>f.prepare(),/POINT_AUDIT_/);
});

test('v4 linked source originals and resource build commits are actually pinned',t=>{
 const f=fixture(t);fs.appendFileSync(path.join(f.task,'resource-build.json'),' ');
 assert.throws(()=>f.prepare(),/POINT_AUDIT_INPUT_CHANGED/);
});

test('TASK filenames reject escapes and mixed path separators before reading',t=>{
 const f=fixture(t);
 for(const file of ['../audit.json','..\\audit.json',path.join(f.task,'audit.json'),'x/audit.json','audit.txt'])
  assert.throws(()=>f.api.readAuditTaskFile(file),/POINT_AUDIT_TASK_FILE_REQUIRED/);
});

test('input mutation after preparation fails the final original-byte barrier',t=>{
 const f=fixture(t),scope=f.prepare();fs.appendFileSync(path.join(f.task,'selection.json'),' ');
 assert.throws(()=>f.api.verifyPointAuditInputs(scope),/POINT_AUDIT_INPUT_CHANGED/);
});

for(const mode of ['missing-parent','non-indexed-parent','wrong-kind','duplicate-parent'])test('whole chain catalogue refusal: '+mode,t=>{
 const f=fixture(t),scope=f.prepare(),items=structuredClone(f.items);
 if(mode==='missing-parent')items.shift();
 if(mode==='non-indexed-parent')items[0].status='unpublished';
 if(mode==='wrong-kind')items[0].kind='release';
 if(mode==='duplicate-parent')items.push(structuredClone(items[0]));
 assert.throws(()=>f.api.selectAuditPoints(items,scope),/POINT_AUDIT_CHAIN_NOT_INDEXED/);
});

test('selected UI source must equal independently audited source and original fixed server',t=>{
 const f=fixture(t),scope=f.prepare();
 f.api.assertSelectedPointState(scope,{application:SOURCE,source:'172.30.30.57'});
 for(const state of [{application:'foreign',source:'172.30.30.57'},{application:SOURCE,source:'172.30.30.58'}])
  assert.throws(()=>f.api.assertSelectedPointState(scope,state),/POINT_AUDIT_UI_SOURCE_CHANGED/);
});

test('actual current v4 is read locally with its real raw pin, without inventing a terminal audit',()=>{
 const api=load(__dirname),actual=api.readAuditTaskFile('main-program-current-installations-45dd7dc-r6-v4.json');
 assert.equal(actual.value.schemaVersion,'TaskMainProgramInstallations/v4');
 assert.equal(actual.pin.bytes,664);assert.equal(actual.pin.sha256,'0e45e0a0b420e32318d53c99251dbadee8013d7e65b6fc772dae0cc089f84004');
 const read=pin=>api.readAuditTaskFile(pin.file,pin).value,generation=read(actual.value.controlGenerationPin);
 const build=read(generation.buildPin);assert.equal(build.fileCount,147);assert.equal(build.targetCommit,actual.value.sourceCommit);
 assert.equal(read(actual.value.spugInstallationPin).sourceCommit,actual.value.sourceCommit);
 const verification=read(actual.value.verificationInputsPin),custody=read(verification.resourceTransitionPin);
 const transition=read(custody.transitionCorePin),resource=read(transition.resourceBuildPin);
 assert.equal(resource.status,'PASS');assert.equal(resource.sourceCommit,'5651efc5b9972b20bcacb50d0774e5862cbe8e6b');
});

test('actual driver input initializers prepare the new point in production evaluation order',t=>{
 const f=fixture(t),names=['sha','auditArguments','selectedPoint'];
 const initializers=tree.body.filter(n=>n.type==='VariableDeclaration'&&n.declarations.some(d=>names.includes(d.id.name)));
 assert.equal(initializers.length,names.length);
 const definitions=tree.body.filter(n=>n.type==='FunctionDeclaration'&&functions.includes(n.id.name));
 const code=[...definitions,...initializers].map(n=>source.slice(n.start,n.end)).join('\n');
 const context=vm.createContext({fs,path,crypto,Buffer,TASK:f.task,require:f.cliRequire,
  process:{argv:['node','helper','--observation','r14','--point-audit','audit.json','--selection','selection.json']},
  need:(value,code)=>{if(!value)throw Error(code);}});
 vm.runInContext(code+'\nthis.selected=selectedPoint;',context);
 assert.equal(context.selected.operationId,ids[3]);
});

test('actual eligible and count seams preserve full mode and require exactly the audited new point',t=>{
 const f=fixture(t),scope=f.prepare();
 const ui=tree.body.find(n=>n.type==='ExpressionStatement'&&n.expression?.callee?.property?.name==='catch'&&n.expression.callee.object?.callee?.async);
 const selected=[],guards=[];
 walk(ui,node=>{
  if(node.type==='VariableDeclarator'&&node.id.name==='eligible')selected.push(node);
  if(node.type==='CallExpression'&&node.callee.name==='need'&&node.arguments[1]?.value==='RESTORABLE_POINTS_REQUIRED')guards.push(node);
 });
 assert.equal(selected.length,1);assert.equal(guards.length,1);
 const code='const eligible='+source.slice(selected[0].init.start,selected[0].init.end)+';'+source.slice(guards[0].start,guards[0].end)+';eligible;';
 const run=(items,point)=>vm.runInNewContext(code,{catalogue:{items},selectedPoint:point,selectAuditPoints:f.api.selectAuditPoints,
  need:(value,code)=>{if(!value)throw Error(code);}});
 assert.equal(run(f.items,null).length,f.items.length);
 assert.throws(()=>run(f.items.slice(0,2),null),/RESTORABLE_POINTS_REQUIRED/);
 assert.deepEqual(plain(run(f.items,scope)),[f.items[3]]);
 const expected=tree.body.find(n=>n.type==='VariableDeclaration'&&n.declarations[0].id.name==='expectedLatest');
 const targets=tree.body.find(n=>n.type==='VariableDeclaration'&&n.declarations[0].id.name==='targets');
 assert.deepEqual(plain(vm.runInNewContext(source.slice(expected.declarations[0].init.start,expected.declarations[0].init.end))),
  ['smallapp-fbaf12b584214695b6b687e010f4773b','smallapp-ab4fefb2bcfb4c3eb0ae5027fea35da5','smallapp-9d5ed2108497411a81bcd5ba7d1a6291']);
 assert.deepEqual(plain(vm.runInNewContext(source.slice(targets.declarations[0].init.start,targets.declarations[0].init.end))),
  ['172.30.30.57','172.30.30.58','172.30.30.59']);
});

test('actual UI source call and finally input barrier are reachable and fail visibly',t=>{
 const f=fixture(t),scope=f.prepare(),sourceCalls=[],finalizers=[];
 walk(tree,node=>{
  if(node.type==='ExpressionStatement'&&node.expression.callee?.name==='assertSelectedPointState')sourceCalls.push(node);
  if(node.type==='TryStatement'&&node.block.body[0]?.expression?.callee?.name==='verifyPointAuditInputs')finalizers.push(node);
 });
 assert.equal(sourceCalls.length,1);assert.equal(finalizers.length,1);
 assert.equal(source.slice(sourceCalls[0].start,sourceCalls[0].end),'assertSelectedPointState(selectedPoint,state);');
 assert.throws(()=>vm.runInNewContext(source.slice(sourceCalls[0].start,sourceCalls[0].end),{
  selectedPoint:scope,state:{application:'foreign',source:'172.30.30.57'},assertSelectedPointState:f.api.assertSelectedPointState}),/POINT_AUDIT_UI_SOURCE_CHANGED/);
 const ui=tree.body.find(n=>n.type==='ExpressionStatement'&&n.expression?.callee?.property?.name==='catch'&&n.expression.callee.object?.callee?.async);
 const main=ui.expression.callee.object.callee.body.body.find(n=>n.type==='TryStatement');
 assert.ok(main.finalizer.body.includes(finalizers[0]),'INPUT_BARRIER_MUST_RUN_IN_UI_FINALLY');
 fs.appendFileSync(path.join(f.task,'audit.json'),' ');
 const report={status:'RUNNING'},process={exitCode:0};
 vm.runInNewContext(source.slice(finalizers[0].start,finalizers[0].end),{selectedPoint:scope,report,process,verifyPointAuditInputs:f.api.verifyPointAuditInputs});
 assert.deepEqual(report,{status:'FAIL',errorCode:'POINT_AUDIT_INPUT_CHANGED'});assert.equal(process.exitCode,1);
 const reportDeclaration=tree.body.find(n=>n.type==='VariableDeclaration'&&n.declarations[0].id.name==='report').declarations[0];
 assert.equal(source.slice(reportDeclaration.init.properties[0].start,reportDeclaration.init.properties[0].end),'...auditReportFields(selectedPoint)');
});
