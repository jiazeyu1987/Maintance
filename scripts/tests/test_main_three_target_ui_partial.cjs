'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const m=require('../../doc/tasks/20261106-spug-prod-incremental-to-two-targets/main_three_target_ui.cjs');
const lp=(file,c)=>({file,bytes:10,sha256:c.repeat(64)});
const mixed='TaskMainProgramTargetControlSuccessorSelection/v3';
function summary(){
 const build=lp('new-build.json','d'),base=lp('b9.json','b'),partial=lp('partial.json','e'),commit='9'.repeat(40);
 return {schemaVersion:'MainThreeTargetInstallationSummary/v1',status:'PASS',selectionSchemaVersion:mixed,
  selectionPin:lp('new.json','c'),predecessorSelectionPin:partial,partialPredecessor:{selectionPin:partial,baseSelectionPin:base,activationVerifiedHosts:['57'],retainedBaseHosts:['58','59']},
  verifiedTargetCommit:commit,verifiedTargetBuildPin:build,
  targetSelectionAncestry:[{selectionPin:lp('a312.json','a'),selectionSchemaVersion:'TaskMainProgramTargetControlSelection/v1',sourceCommit:'a3121c64d46fcdc2c1a3195a2cbbf8ca1c05742e'},
   {selectionPin:base,selectionSchemaVersion:'TaskMainProgramTargetControlSuccessorSelection/v1',sourceCommit:'b9caa00b7eeed2b915c8855a8313521e57d06f72'}],
  controllers:Object.fromEntries(['57','58','59'].map(h=>[h,[{host:'172.30.30.'+h,role:'target',sourceCommit:commit}]])),
  controllerBuildBindings:Object.fromEntries(['57','58','59'].map(h=>[h,{target:{buildPin:build,sourceCommit:commit}}]))};
}
test('complete mixed predecessor generation dispatches current loader and dynamic receipt',()=>{
 const x=summary(),profile=m.assertInstallationGeneration(x);
 assert.equal(profile.loaderFunction,'load_current_target_installation');
 assert.equal(profile.submissionFile,'main-i2-to-test58-ui-submission-'+x.selectionPin.sha256+'.json');
});
test('v3 submits only the existing I2 to58 and binds both retained failed operations',()=>{
 const installation=summary(),point={path:require('node:path').resolve('point.json'),bytes:10,sha256:'d'.repeat(64)};
 const request={schemaVersion:'SmallAppBackupUiRequest/v1',operationId:'smallapp-'+'1'.repeat(32),action:'RESTORE',sourceConfigRef:'intruoyi-57-safe-20261024-v1',parentChainRef:null,
  recoveryPointRef:'smallapp-e7b668792c8f4bce945a52f984d3c660',targetConfigRef:'intruoyi-main-58-safe-restore-20261104-v1'};
 const p=(name,c)=>({path:require('node:path').resolve(name),bytes:10,sha256:c.repeat(64)}),old='smallapp-b4f21de7a0c64d31beda7efa0204ced8',b9='smallapp-6546b96486f7413a84c7281c95131f1f';
 const first={schemaVersion:'MainI2TestRestoreSubmission/v1',submittedAt:'2026-11-11T00:00:00Z',selectionPin:installation.targetSelectionAncestry[0].selectionPin,pointEvidencePin:point,request:{...request,operationId:old}};
 const second={schemaVersion:'MainI2TestRestoreSuccessorSubmission/v1',submittedAt:'2026-11-12T00:00:00Z',selectionPin:installation.targetSelectionAncestry[1].selectionPin,
  pointEvidencePin:point,request:{...request,operationId:b9},previousSubmissionPin:p('first.json','a'),previousOperationId:old};
 const k={installation,request,pointEvidencePin:point,submittedAt:'2026-11-12T01:00:00Z',previousSubmissions:[{pin:p('first.json','a'),value:first},{pin:p('second.json','b'),value:second}]};
 assert.deepEqual(m.buildSubmissionReceipt(k).previousOperationIds,[old,b9]);
 for(const id of [old,b9])assert.throws(()=>m.buildSubmissionReceipt({...k,request:{...request,operationId:id}}));
});
for(const problem of ['missing','partial_pin','base_pin','hosts','mixed_build','fake_ancestor','partial_schema'])test('v3 rejects '+problem,()=>{
 const x=summary();
 if(problem==='missing')delete x.partialPredecessor;
 else if(problem==='partial_pin')x.partialPredecessor.selectionPin=lp('other.json','0');
 else if(problem==='base_pin')x.partialPredecessor.baseSelectionPin=lp('other.json','0');
 else if(problem==='hosts')x.partialPredecessor.activationVerifiedHosts=['57','58','59'];
 else if(problem==='mixed_build')x.controllers['57'][0].sourceCommit='e'.repeat(40);
 else if(problem==='fake_ancestor')x.targetSelectionAncestry.push({selectionPin:x.predecessorSelectionPin,selectionSchemaVersion:'TaskMainProgramTargetControlPartialPredecessor/v1',sourceCommit:'e'.repeat(40)});
 else x.selectionSchemaVersion='TaskMainProgramTargetControlPartialPredecessor/v1';
 assert.throws(()=>m.assertInstallationGeneration(x));
});
