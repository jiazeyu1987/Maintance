'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {restoreWriteAllowed,assertPointChain}=require('../../doc/tasks/20261106-spug-prod-incremental-to-two-targets/main_three_target_ui.cjs');
const {jsonEqual}=require('../../doc/tasks/20261106-spug-prod-incremental-to-two-targets/main_three_target_ui.cjs');
const ids=['smallapp-3c2395ff88bd474e9fc007649565b848','smallapp-20a1bb9b78ac402693289675d16c63dd','smallapp-e7b668792c8f4bce945a52f984d3c660'];
const proof={status:'SUCCEEDED_VERIFIED',operationId:ids[2],parentOperationId:ids[1],baseFullOperationId:ids[0],chainDepth:2,actualExitCode:0,originalSourceRestored:true,originalWorkerExited:true};
const request={schemaVersion:'SmallAppBackupUiRequest/v1',operationId:'smallapp-11111111111111111111111111111111',action:'RESTORE',sourceConfigRef:'intruoyi-57-safe-20261024-v1',parentChainRef:null,recoveryPointRef:ids[2],targetConfigRef:'intruoyi-main-58-safe-restore-20261104-v1'};
test('successful original three point chain is retained',()=>assert.deepEqual(assertPointChain(proof),ids));
for(const field of ['status','parentOperationId','baseFullOperationId','chainDepth','actualExitCode','originalSourceRestored','originalWorkerExited']){
 test('invalid original success '+field+' is rejected',()=>assert.throws(()=>assertPointChain({...proof,[field]:null})));
}
test('only explicit submit exact I2 to test58 may write once',()=>assert.equal(restoreWriteAllowed('submit',request,ids[2],false,0),true));
for(const phase of ['preview','verify',null])test('readonly phase '+phase+' cannot dispatch',()=>assert.equal(restoreWriteAllowed(phase,request,ids[2],false,0),false));
for(const key of ['action','schemaVersion','sourceConfigRef','recoveryPointRef','targetConfigRef','operationId','parentChainRef']){
 test('wrong request '+key+' is rejected',()=>assert.equal(restoreWriteAllowed('submit',{...request,[key]:'wrong'},ids[2],false,0),false));
}
test('unknown request fields rejected',()=>assert.equal(restoreWriteAllowed('submit',{...request,extra:true},ids[2],false,0),false));
test('production target rejected',()=>assert.equal(restoreWriteAllowed('submit',{...request,targetConfigRef:'intruoyi-main-57-safe-restore-20261105-v2'},ids[2],false,0),false));
test('review target rejected',()=>assert.equal(restoreWriteAllowed('submit',{...request,targetConfigRef:'intruoyi-main-59-safe-restore-20261104-v1'},ids[2],false,0),false));
test('persisted request prevents repeat even after no response',()=>assert.equal(restoreWriteAllowed('submit',request,ids[2],true,0),false));
test('already passed write prevents second dispatch',()=>assert.equal(restoreWriteAllowed('submit',request,ids[2],false,1),false));

test('canonical response request keys may have another order',()=>assert.equal(jsonEqual(request,Object.fromEntries(Object.entries(request).reverse())),true));
test('nested JSON key order does not change identity',()=>assert.equal(jsonEqual({a:{x:1,y:2},b:[{c:3,d:4}]},{b:[{d:4,c:3}],a:{y:2,x:1}}),true));
test('JSON arrays retain order',()=>assert.equal(jsonEqual([1,2],[2,1]),false));
test('JSON scalar types retain identity',()=>assert.equal(jsonEqual({a:1},{a:true}),false));
test('additional JSON request fields change identity',()=>assert.equal(jsonEqual(request,{...request,extra:null}),false));

const moduleUnderTest=require('../../doc/tasks/20261106-spug-prod-incremental-to-two-targets/main_three_target_ui.cjs');
const V1='TaskMainProgramTargetControlSelection/v1',V2='TaskMainProgramTargetControlSuccessorSelection/v1';
const OLD='a3121c64d46fcdc2c1a3195a2cbbf8ca1c05742e',NEXT='b9caa00b7eeed2b915c8855a8313521e57d06f72';
const failed='smallapp-b4f21de7a0c64d31beda7efa0204ced8';
const localPin={file:'selection.json',bytes:10,sha256:'a'.repeat(64)};
const priorPin={path:'C:\\private\\main-i2-to-test58-ui-submission.json',bytes:10,sha256:'b'.repeat(64)};
function api(name){assert.equal(typeof moduleUnderTest[name],'function','MISSING_UI_SUCCESSOR_'+name);return moduleUnderTest[name];}
function summary(schema=V2){const commit=schema===V1?OLD:NEXT;return {schemaVersion:'MainThreeTargetInstallationSummary/v1',status:'PASS',selectionSchemaVersion:schema,
 selectionPin:localPin,predecessorSelectionPin:localPin,inputPins:[],controllers:Object.fromEntries(['57','58','59'].map(h=>[h,[{host:'172.30.30.'+h,role:'target',sourceCommit:commit}]]))};}
function previous(){return {schemaVersion:'MainI2TestRestoreSubmission/v1',submittedAt:'2026-11-11T00:00:00Z',selectionPin:localPin,pointEvidencePin:priorPin,request:{...request,operationId:failed}};}

test('explicit original and successor schemas dispatch only corresponding formal loaders',()=>{
 const profile=api('targetGeneration');
 assert.equal(profile(V1).loaderFunction,'load_activated_target_installation');
 assert.equal(profile(V2).loaderFunction,'load_activated_target_successor_installation');
 assert.equal(profile(V1).submissionFile,'main-i2-to-test58-ui-submission.json');
 assert.equal(profile(V2).submissionFile,'main-i2-to-test58-ui-submission-b9caa00.json');
 assert.throws(()=>profile('TaskMainProgramTargetControlSelection/v99'));
});
test('both generations require one target per host with their exact official commit',()=>{
 for(const schema of [V1,V2])assert.equal(api('assertInstallationGeneration')(summary(schema)).targetCommit,schema===V1?OLD:NEXT);
});
for(const problem of ['missing-host','extra-host','duplicate','missing-target','mixed','wrong-host','unknown-schema'])test('invalid generation '+problem+' rejected',()=>{
 const s=summary();
 if(problem==='missing-host')delete s.controllers['59'];
 else if(problem==='extra-host')s.controllers['60']=s.controllers['59'];
 else if(problem==='duplicate')s.controllers['58'].push({...s.controllers['58'][0]});
 else if(problem==='missing-target')s.controllers['58']=[];
 else if(problem==='mixed')s.controllers['58'][0].sourceCommit=OLD;
 else if(problem==='wrong-host')s.controllers['58'][0].host='172.30.30.57';
 else s.selectionSchemaVersion='unknown';
 assert.throws(()=>api('assertInstallationGeneration')(s));
});
test('successor receipt names exact predecessor pin and a distinct new operation',()=>{
 const result=api('buildSubmissionReceipt')({installation:summary(),request,pointEvidencePin:priorPin,submittedAt:'2026-11-12T00:00:00Z',previousSubmission:previous(),previousSubmissionPin:priorPin});
 assert.equal(result.schemaVersion,'MainI2TestRestoreSuccessorSubmission/v1');
 assert.deepEqual(result.previousSubmissionPin,priorPin);assert.equal(result.previousOperationId,failed);assert.equal(result.request.operationId,request.operationId);
});
test('original receipt keeps its existing exact shape',()=>{
 const result=api('buildSubmissionReceipt')({installation:summary(V1),request,pointEvidencePin:priorPin,submittedAt:'2026-11-12T00:00:00Z'});
 assert.deepEqual(Object.keys(result).sort(),['schemaVersion','submittedAt','selectionPin','pointEvidencePin','request'].sort());
 assert.equal(result.schemaVersion,'MainI2TestRestoreSubmission/v1');
});
for(const problem of ['old-id','no-prior','wrong-prior-id','wrong-prior-selection','wrong-prior-schema','bad-pin','wrong-point','unknown-request'])test('unsafe successor receipt '+problem+' rejected',()=>{
 const args={installation:summary(),request:{...request},pointEvidencePin:priorPin,submittedAt:'2026-11-12T00:00:00Z',previousSubmission:previous(),previousSubmissionPin:{...priorPin}};
 if(problem==='old-id')args.request.operationId=failed;
 else if(problem==='no-prior')delete args.previousSubmission;
 else if(problem==='wrong-prior-id')args.previousSubmission.request.operationId=request.operationId;
 else if(problem==='wrong-prior-selection')args.previousSubmission.selectionPin={...localPin,sha256:'0'.repeat(64)};
 else if(problem==='wrong-prior-schema')args.previousSubmission.schemaVersion='unknown';
 else if(problem==='bad-pin')args.previousSubmissionPin.sha256='wrong';
 else if(problem==='wrong-point')args.request.recoveryPointRef=ids[0];
 else args.request.extra=true;
 assert.throws(()=>api('buildSubmissionReceipt')(args));
});
test('successor write guard refuses original failed ID and remains readonly during preview/verify',()=>{
 assert.equal(restoreWriteAllowed('submit',{...request,operationId:failed},ids[2],false,0,failed),false);
 for(const phase of ['preview','verify'])assert.equal(restoreWriteAllowed(phase,request,ids[2],false,0,failed),false);
});
test('original provenance can be checked before any new request exists',()=>{
 assert.equal(api('assertPreviousSubmission')({installation:summary(),pointEvidencePin:priorPin,previousSubmission:previous(),previousSubmissionPin:priorPin}),failed);
});
test('embedded Python bridge has explicit schema dispatch and remains compilable',()=>{
 const program=moduleUnderTest.installationLoaderProgram;assert.equal(typeof program,'string','MISSING_EXPORTED_INSTALLATION_BRIDGE');
 const result=require('node:child_process').spawnSync('C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
  ['-B','-X','utf8','-c','import ast,sys; ast.parse(sys.stdin.read())'],{input:program,encoding:'utf8',shell:false,windowsHide:true});
 assert.equal(result.status,0,result.stderr);assert.match(program,/UNKNOWN_TARGET_SELECTION_SCHEMA/);
});
