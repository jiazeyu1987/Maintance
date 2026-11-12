'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const m=require('../../doc/tasks/20261106-spug-prod-incremental-to-two-targets/main_three_target_ui.cjs');
const lp=(file,c)=>({file,bytes:10,sha256:c.repeat(64)});
function summary(){
 const build=lp('new-build.json','d'),base=lp('b9.json','b'),partial=lp('partial.json','e'),prior=lp('b10.json','f'),commit='9'.repeat(40);
 return {schemaVersion:'MainThreeTargetInstallationSummary/v1',status:'PASS',selectionSchemaVersion:'TaskMainProgramTargetControlSuccessorSelection/v2',
  selectionPin:lp('new.json','c'),predecessorSelectionPin:prior,partialPredecessor:{selectionPin:partial,baseSelectionPin:base,activationVerifiedHosts:['57'],retainedBaseHosts:['58','59']},
  verifiedTargetCommit:commit,verifiedTargetBuildPin:build,
  targetSelectionAncestry:[{selectionPin:lp('a312.json','a'),selectionSchemaVersion:'TaskMainProgramTargetControlSelection/v1',sourceCommit:'a3121c64d46fcdc2c1a3195a2cbbf8ca1c05742e'},
   {selectionPin:base,selectionSchemaVersion:'TaskMainProgramTargetControlSuccessorSelection/v1',sourceCommit:'b9caa00b7eeed2b915c8855a8313521e57d06f72'},
   {selectionPin:prior,selectionSchemaVersion:'TaskMainProgramTargetControlSuccessorSelection/v3',sourceCommit:'b10ba57bd107733d77d74b7494ef72f07ba09205'}],
  controllers:Object.fromEntries(['57','58','59'].map(h=>[h,[{host:'172.30.30.'+h,role:'target',sourceCommit:commit}]])),
  controllerBuildBindings:Object.fromEntries(['57','58','59'].map(h=>[h,{target:{buildPin:build,sourceCommit:commit}}]))};
}
test('complete successor retains a historical partial without treating it as direct predecessor',()=>{
 const x=summary();assert.equal(m.assertInstallationGeneration(x).loaderFunction,'load_current_target_installation');
 // Explicit formal-loader protocol fixture; this tests summary traversal, not
 // installation verification or runtime state. Execute the original bridge.
 const fixture=String.raw`
import json,sys,types
x=json.loads(sys.stdin.read());ancestry=x['targetSelectionAncestry']
def node(index):
 row=ancestry[index]
 v=dict(selectionPin=row['selectionPin'],selection={'schemaVersion':row['selectionSchemaVersion']},controllerBuildBindings={'58':{'target':{'sourceCommit':row['sourceCommit']}}})
 if index>0:v['predecessorInstallation']=node(index-1)
 return v
prior=node(2)
p=x['partialPredecessor']
prior['predecessorInstallation']=dict(selectionPin=p['selectionPin'],selection={'schemaVersion':'TaskMainProgramTargetControlPartialPredecessor/v1','baseSelectionPin':p['baseSelectionPin']},status='PARTIALLY_ACTIVATED',installationVerified=False,activationVerifiedHosts=p['activationVerifiedHosts'],retainedBaseHosts=p['retainedBaseHosts'],predecessorInstallation=node(1))
selected=dict(schemaVersion=x['selectionSchemaVersion'],predecessorSelectionPin=x['predecessorSelectionPin'])
v=dict(selectionPin=x['selectionPin'],selection=selected,status='ACTIVATED',installationVerified=True,runtimeVerified=False,inputPins=[],effectiveControllersByHost=x['controllers'],controllerBuildBindings=x['controllerBuildBindings'],predecessorInstallation=prior)
class Records:
 def __init__(self,task):self.references={'new.json':x['selectionPin']}
 def read(self,name):return selected
r=types.ModuleType('main_program_installation_selection');r.Records=Records;sys.modules[r.__name__]=r
c=types.ModuleType('main_program_current_installation');c.load_current_target_installation=lambda *a,**k:v;sys.modules[c.__name__]=c
sys.argv=['bridge','.','.','new.json','{}']
`;
 const py=process.env.SPUG_TEST_PYTHON;
 assert.ok(py,'SPUG_TEST_PYTHON_REQUIRED');
 const r=require('node:child_process').spawnSync(py,['-B','-X','utf8','-c',fixture+'\n'+m.installationLoaderProgram],{input:JSON.stringify(x),encoding:'utf8'});
 assert.equal(r.status,0,r.stderr);const actual=JSON.parse(r.stdout);
 assert.deepEqual(actual.partialPredecessor,x.partialPredecessor);
 assert.deepEqual(actual.targetSelectionAncestry,x.targetSelectionAncestry);
 assert.equal(m.assertInstallationGeneration(actual).loaderFunction,'load_current_target_installation');
});
for(const fault of ['base','hosts','schema','partial_as_full'])test('historical partial rejects '+fault,()=>{
 const x=summary();
 if(fault==='base')x.partialPredecessor.baseSelectionPin=lp('foreign.json','0');
 else if(fault==='hosts')x.partialPredecessor.activationVerifiedHosts=['58'];
 else if(fault==='schema')x.targetSelectionAncestry[2].selectionSchemaVersion='TaskMainProgramTargetControlSuccessorSelection/v2';
 else x.targetSelectionAncestry.push({selectionPin:x.partialPredecessor.selectionPin,selectionSchemaVersion:'TaskMainProgramTargetControlSuccessorSelection/v2',sourceCommit:'8'.repeat(40)});
 assert.throws(()=>m.assertInstallationGeneration(x));
});
