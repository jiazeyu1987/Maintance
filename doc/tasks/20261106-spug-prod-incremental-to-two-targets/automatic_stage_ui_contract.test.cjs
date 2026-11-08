'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'automatic_incremental_ui_acceptance.cjs'),'utf8');
const OLD='0d445782dc06995b3c84b1b45146ea4b75483f92',NEW='1'.repeat(40);
function contracts(){
 const context=vm.createContext({require,__dirname,process:{argv:[]},console,Buffer});
 vm.runInContext(source.slice(0,source.lastIndexOf('\nmain().catch'))+'\nglobalThis.contract={validateDeploymentContract,validateReceiptDeployment};',context);
 return context.contract;
}
function fixture(kind='I1'){
 const deployment={schemaVersion:'AutomaticStageDeployment/v1',kind,sourceConfigRef:'intruoyi-57-safe-20261024-v1',
  sourceCommit:kind==='FULL'?OLD:NEW,spugCommit:OLD};
 const selectionPin={file:`automatic-${kind.toLowerCase()}-deployment-selection.json`,bytes:123,sha256:'a'.repeat(64)};
 const gate={schemaVersion:'AutomaticIncrementalUiPreflight/v2',kind,implementationCommit:deployment.sourceCommit,
  installationCommit:deployment.sourceCommit,buildCommit:deployment.sourceCommit,spugCommit:OLD,deploymentSelectionPin:selectionPin,
  gitDeploymentInputs:{source:{installedCommit:deployment.sourceCommit,headCommit:NEW,deploymentInputsUnchanged:true,installedCommitIsAncestor:true},
   spug:{installedCommit:OLD,headCommit:NEW,deploymentInputsUnchanged:true,installedCommitIsAncestor:true}}};
 return {deployment,selectionPin,gate};
}
test('new source and retained Spug gate binds explicit selection',()=>{
 const {deployment,selectionPin,gate}=fixture();contracts().validateDeploymentContract(gate,'I1',deployment,selectionPin);
});
test('stage/Spug/source mismatch cannot pass as legacy',()=>{
 for(const change of [g=>g.spugCommit=NEW,g=>g.implementationCommit=OLD,g=>g.gitDeploymentInputs.source.deploymentInputsUnchanged=false,g=>g.schemaVersion='AutomaticIncrementalUiPreflight/v1']){
  const {deployment,selectionPin,gate}=fixture();change(gate);
  assert.throws(()=>contracts().validateDeploymentContract(gate,'I1',deployment,selectionPin));
 }
});
test('legacy receipt is limited to historical FULL and never rewritten',()=>{
 const {gate}=fixture('FULL');const receipt={schemaVersion:'AutomaticIncrementalUiSubmission/v1',kind:'FULL',implementationCommit:OLD};
 const original=JSON.stringify(receipt);contracts().validateReceiptDeployment(receipt,gate,'FULL');assert.equal(JSON.stringify(receipt),original);
 assert.throws(()=>contracts().validateReceiptDeployment({...receipt,kind:'I1'},gate,'I1'));
 assert.throws(()=>contracts().validateReceiptDeployment({...receipt,implementationCommit:NEW},gate,'FULL'));
});
test('new submission and verify bind exact selection and Spug commit',()=>{
 const {gate}=fixture();const receipt={schemaVersion:'AutomaticIncrementalUiSubmission/v2',kind:'I1',implementationCommit:NEW,spugCommit:OLD,deploymentSelectionPin:gate.deploymentSelectionPin};
 contracts().validateReceiptDeployment(receipt,gate,'I1');
 assert.throws(()=>contracts().validateReceiptDeployment({...receipt,deploymentSelectionPin:{...gate.deploymentSelectionPin,sha256:'b'.repeat(64)}},gate,'I1'));
});
