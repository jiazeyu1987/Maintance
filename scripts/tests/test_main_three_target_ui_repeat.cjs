'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const m=require('../../doc/tasks/20261106-spug-prod-incremental-to-two-targets/main_three_target_ui.cjs');
const schema='TaskMainProgramTargetControlSuccessorSelection/v2',commit='e'.repeat(40);
const old='a3121c64d46fcdc2c1a3195a2cbbf8ca1c05742e',b9='b9caa00b7eeed2b915c8855a8313521e57d06f72';
const lp=(file,c)=>({file,bytes:10,sha256:c.repeat(64)}),fp=c=>({path:require('node:path').resolve('private-'+c+'.json'),bytes:10,sha256:c.repeat(64)});
const request={schemaVersion:'SmallAppBackupUiRequest/v1',operationId:'smallapp-'+'1'.repeat(32),action:'RESTORE',sourceConfigRef:'intruoyi-57-safe-20261024-v1',parentChainRef:null,
 recoveryPointRef:'smallapp-e7b668792c8f4bce945a52f984d3c660',targetConfigRef:'intruoyi-main-58-safe-restore-20261104-v1'};
const original='smallapp-b4f21de7a0c64d31beda7efa0204ced8',point=fp('d');
function fixture(){
 const selection=lp('next.json','c'),build=lp('build.json','d'),a=lp('a.json','a'),b=lp('b.json','b');
 const installation={schemaVersion:'MainThreeTargetInstallationSummary/v1',status:'PASS',selectionSchemaVersion:schema,selectionPin:selection,
  predecessorSelectionPin:b,verifiedTargetCommit:commit,verifiedTargetBuildPin:build,
  targetSelectionAncestry:[{selectionPin:a,selectionSchemaVersion:'TaskMainProgramTargetControlSelection/v1',sourceCommit:old},
   {selectionPin:b,selectionSchemaVersion:'TaskMainProgramTargetControlSuccessorSelection/v1',sourceCommit:b9}],
  controllers:Object.fromEntries(['57','58','59'].map(h=>[h,[{host:'172.30.30.'+h,role:'target',sourceCommit:commit}]])),
  controllerBuildBindings:Object.fromEntries(['57','58','59'].map(h=>[h,{target:{buildPin:build,sourceCommit:commit}}]))};
 const first={schemaVersion:'MainI2TestRestoreSubmission/v1',submittedAt:'2026-11-11T00:00:00Z',selectionPin:a,pointEvidencePin:point,request:{...request,operationId:original}};
 const second={schemaVersion:'MainI2TestRestoreSuccessorSubmission/v1',submittedAt:'2026-11-12T00:00:00Z',selectionPin:b,pointEvidencePin:point,
  request:{...request,operationId:'smallapp-6546b96486f7413a84c7281c95131f1f'},previousSubmissionPin:fp('a'),previousOperationId:original};
 return {installation,request:{...request},pointEvidencePin:point,submittedAt:'2026-11-12T01:00:00Z',previousSubmissions:[{pin:fp('a'),value:first},{pin:fp('b'),value:second}]};
}
test('repeat schema uses the one current loader and verified dynamic build',()=>{
 const profile=m.assertInstallationGeneration(fixture().installation);
 assert.equal(profile.loaderFunction,'load_current_target_installation');assert.equal(profile.targetCommit,commit);
 assert.equal(profile.submissionFile,'main-i2-to-test58-ui-submission-'+ 'c'.repeat(64)+'.json');
});
test('repeat receipt binds every prior original and forbids old operation reuse',()=>{
 const k=fixture(),r=m.buildSubmissionReceipt(k);assert.equal(r.schemaVersion,'MainI2TestRestoreRepeatedSubmission/v1');
 assert.deepEqual(r.previousSubmissionPins,k.previousSubmissions.map(x=>x.pin));
 assert.deepEqual(r.previousOperationIds,k.previousSubmissions.map(x=>x.value.request.operationId));
});
for(const problem of ['commit','mixed','build','missing_ancestor','ancestor_pin','prior_pin','prior_id','old_id','old_second_id','point','unknown'])test('repeat refuses '+problem,()=>{
 const k=fixture();
 if(problem==='commit')k.installation.verifiedTargetCommit='z'.repeat(40);
 else if(problem==='mixed')k.installation.controllers['58'][0].sourceCommit=old;
 else if(problem==='build')k.installation.controllerBuildBindings['59'].target={buildPin:lp('bad.json','0'),sourceCommit:commit};
 else if(problem==='missing_ancestor')k.previousSubmissions.pop();
 else if(problem==='ancestor_pin')k.installation.targetSelectionAncestry[0].selectionPin=lp('foreign.json','0');
 else if(problem==='prior_pin')k.previousSubmissions[1].value.previousSubmissionPin=fp('0');
 else if(problem==='prior_id')k.previousSubmissions[1].value.previousOperationId=request.operationId;
 else if(problem==='old_id')k.request.operationId=original;
 else if(problem==='old_second_id')k.request.operationId=k.previousSubmissions[1].value.request.operationId;
 else if(problem==='point')k.previousSubmissions[0].value.pointEvidencePin=fp('0');
 else k.previousSubmissions[1].value.extra=true;
 assert.throws(()=>m.buildSubmissionReceipt(k));
});
test('repeat remains readonly outside explicit submit',()=>{
 for(const phase of ['preview','verify'])assert.equal(m.restoreWriteAllowed(phase,request,request.recoveryPointRef,false,0),false);
});
