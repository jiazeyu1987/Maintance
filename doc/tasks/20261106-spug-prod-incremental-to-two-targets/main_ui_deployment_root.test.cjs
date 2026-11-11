'use strict';
// Only the fixed CLI subprocess boundary is supplied here. Real temporary files/pins
// are read by production code. This is not actual installation or browser evidence.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),vm=require('node:vm'),crypto=require('node:crypto');
const source=fs.readFileSync(path.join(__dirname,'automatic_incremental_ui_acceptance.cjs'),'utf8');
const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
function save(root,name,value){const raw=Buffer.from(JSON.stringify(value));fs.writeFileSync(path.join(root,name),raw);return {file:name,bytes:raw.length,sha256:hash(raw)};}
function setup(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'main-dual-roots-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const pin=name=>({file:name,bytes:1,sha256:'a'.repeat(64)}),remote=name=>({path:'/opt/main/'+name,bytes:1,sha256:'b'.repeat(64)});
 const sourceCommit='1'.repeat(40),spugCommit='2'.repeat(40);
 const build={status:'PASS',targetCommit:sourceCommit,worktree:path.join(root,'source-release'),allFilesShaAndCompileVerified:true};
 const resource={schemaVersion:'MainProgramSpugResourceBuild/v2',status:'PASS',sourceCommit:spugCommit,worktree:path.join(root,'spug-release'),fileCount:1,files:{'ops/spug/smallapp-ui/app.js':{bytes:1,sha256:'a'.repeat(64)}}};
 fs.mkdirSync(build.worktree);fs.mkdirSync(resource.worktree);
 const buildPin=save(root,'source-build.json',build),resourceBuildPin=save(root,'resource-build.json',resource);
 const generation={schemaVersion:'MainProgramControlGeneration/v1',status:'PASS',sourceCommit,buildPin};
 const controlGenerationPin=save(root,'generation.json',generation);
 const selection={schemaVersion:'TaskMainProgramInstallations/v4',sourceCommit,controlGenerationPin,spugInstallationPin:pin('spug.json'),verificationInputsPin:pin('inputs.json')};
 const selectionPin=save(root,'selection.json',selection);
 const component=(commit,scopes)=>({installedCommit:commit,headCommit:commit,installedCommitIsAncestor:true,deploymentInputsUnchanged:true,deploymentInputScopes:scopes});
 const binding=(value,ref,commit)=>({schemaVersion:'MainProgramDeploymentRoot/v1',mode:'PINNED_BUILD_WORKTREE',path:value.worktree.replaceAll('\\','/'),buildPin:ref,targetCommit:commit,headCommit:commit,registeredWorktreeMatched:true,clean:true});
 const inputs={source:component(sourceCommit,['backend/capture.py','ops/backup_engine','ops/recovery']),spug:component(spugCommit,['ops/spug/smallapp-ui/app.js']),
  deploymentRootBindings:{source:binding(build,buildPin,sourceCommit),spug:binding(resource,resourceBuildPin,spugCommit)}};
 const runtime={schemaVersion:'MainProgramAutomaticIncrementalUiRuntime/v1',status:'PASS',deploymentSelectionPin:selectionPin,gitDeploymentInputs:structuredClone(inputs)};
 const gate={schemaVersion:'MainProgramAutomaticIncrementalUiPreflight/v2',cycle:'dual-roots',implementationCommit:sourceCommit,installationCommit:sourceCommit,buildCommit:sourceCommit,spugCommit,
  deploymentSelectionPin:selectionPin,controlGenerationPin,spugInstallationPin:selection.spugInstallationPin,sourceCaptureConfigurationPin:remote('capture'),sourceOwnerConfigurationPin:remote('owner'),mainDeploymentVerified:true,
  runtimeEvidencePin:save(root,'runtime.json',runtime),gitDeploymentInputs:inputs};
 const inputPins=[selectionPin,controlGenerationPin,buildPin,resourceBuildPin].map(ref=>({path:path.join(root,ref.file),bytes:ref.bytes,sha256:ref.sha256}));
 const summary={schemaVersion:'MainProgramCurrentInstallationSummary/v1',status:'PASS',selectionPin,sourceCommit,controlGenerationPin,spugInstallationPin:selection.spugInstallationPin,buildPin,
  build:{fileCount:147,fileManifestSha256:'c'.repeat(64),packageSha256:'d'.repeat(64)},resourceBuildPin,spugCommit,inputPins};
 const f={root,build,resource,generation,selection,selectionPin,gate,runtime,summary,calls:[],reply:null,options:{cycle:'dual-roots',kind:'FULL',phase:'submit',observation:'r1'}};
 const scopedRequire=name=>name==='node:child_process'?{spawnSync:(...args)=>{f.calls.push(args);return f.reply||{status:0,stderr:Buffer.alloc(0),stdout:Buffer.from(JSON.stringify(f.summary))};}}:require(name);
 const context=vm.createContext({require:scopedRequire,__dirname:root,process:{argv:['node','driver']},console,Buffer});
 const relocated=source.replace("PRIVATE='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106'","PRIVATE=__dirname");
 vm.runInContext(relocated.slice(0,relocated.lastIndexOf('\nmain().catch'))+'\nglobalThis.contract={validateMainDeploymentContract};',context);
 f.check=()=>context.contract.validateMainDeploymentContract(f.gate,f.options,f.selection,f.selectionPin);
 return f;
}
test('v2 admits different registered component heads via one fixed real-file CLI protocol',t=>{
 const f=setup(t);f.check();assert.equal(f.calls.length,1);const [exe,args,options]=f.calls[0];
 assert.equal(exe,'C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe');
 assert.deepEqual(Array.from(args),['-B','-X','utf8',path.join(f.root,'main_program_current_installation.py'),'--selection','selection.json','--public-summary']);
 assert.equal(options.shell,false);assert.equal(options.timeout,600000);assert.equal(options.maxBuffer,16*1024*1024);assert.equal(options.windowsHide,true);
 f.check();assert.equal(f.calls.length,1,'later barriers must not repeat the expensive immutable inference');
});
for(const [name,change] of [
 ['missing binding',f=>delete f.gate.gitDeploymentInputs.deploymentRootBindings],
 ['unknown binding field',f=>f.gate.gitDeploymentInputs.deploymentRootBindings.source.extra=true],
 ['false clean',f=>f.gate.gitDeploymentInputs.deploymentRootBindings.spug.clean=false],
 ['string boolean',f=>f.gate.gitDeploymentInputs.deploymentRootBindings.source.registeredWorktreeMatched='true'],
 ['swapped roots',f=>f.gate.gitDeploymentInputs.deploymentRootBindings.spug.path=f.build.worktree.replaceAll('\\','/')],
 ['same invented HEAD',f=>f.gate.gitDeploymentInputs.spug.headCommit=f.selection.sourceCommit],
 ['unverified scope',f=>f.gate.gitDeploymentInputs.source.deploymentInputsUnchanged=false],
 ['empty scope',f=>f.gate.gitDeploymentInputs.spug.deploymentInputScopes=[]],
 ['other build pin',f=>f.gate.gitDeploymentInputs.deploymentRootBindings.spug.buildPin=f.summary.buildPin],
 ['runtime mismatch',f=>{f.runtime.gitDeploymentInputs.source.headCommit='3'.repeat(40);f.gate.runtimeEvidencePin=save(f.root,'runtime.json',f.runtime);}],
 ['runtime selection',f=>{f.runtime.deploymentSelectionPin={...f.selectionPin,sha256:'0'.repeat(64)};f.gate.runtimeEvidencePin=save(f.root,'runtime.json',f.runtime);}],
 ['runtime status',f=>{f.runtime.status='FAIL';f.gate.runtimeEvidencePin=save(f.root,'runtime.json',f.runtime);}],
])test('v2 refuses '+name+' before browser',t=>{const f=setup(t);change(f);assert.throws(f.check,/MAIN_(ROOT|COMPONENT|RUNTIME|BUILD|GIT)/);});
for(const [name,change] of [
 ['nonzero',f=>f.reply={status:1,stderr:Buffer.alloc(0),stdout:Buffer.from('{}')}],
 ['stderr',f=>f.reply={status:0,stderr:Buffer.from('diagnostic'),stdout:Buffer.from('{}')}],
 ['bad schema',f=>f.summary.schemaVersion='unverified'],
 ['other source',f=>f.summary.sourceCommit='4'.repeat(40)],
 ['unbound resource',f=>f.summary.inputPins=f.summary.inputPins.filter(p=>!p.path.endsWith('resource-build.json'))],
 ['duplicate input',f=>f.summary.inputPins.push(f.summary.inputPins[0])],
 ['changed input',f=>fs.appendFileSync(path.join(f.root,'source-build.json'),' ')],
])test('formal CLI closure refuses '+name,t=>{const f=setup(t);change(f);assert.throws(f.check,/MAIN_CURRENT_INSTALLATION/);});
test('failed CLI does not create a successful cached proof',t=>{
 const f=setup(t);f.reply={status:1,stderr:Buffer.alloc(0),stdout:Buffer.from('{}')};assert.throws(f.check,/MAIN_CURRENT_INSTALLATION/);
 f.reply=null;f.options.observation='r2';f.check();assert.equal(f.calls.length,2);
});
test('later barrier rereads all original inputs without a second CLI',t=>{
 const f=setup(t);f.check();fs.appendFileSync(path.join(f.root,'resource-build.json'),' ');
 assert.throws(f.check,/MAIN_CURRENT_INSTALLATION/);assert.equal(f.calls.length,1);
});
test('later barrier rejects selection switching instead of loading another generation',t=>{
 const f=setup(t);f.check();f.selectionPin=save(f.root,'second-selection.json',f.selection);f.gate.deploymentSelectionPin=f.selectionPin;
 assert.throws(f.check,/MAIN_CURRENT_INSTALLATION_SELECTION_CHANGED/);assert.equal(f.calls.length,1);
});
test('v1 does not invoke the new CLI or require dual-root evidence',t=>{
 const f=setup(t);f.gate.schemaVersion='MainProgramAutomaticIncrementalUiPreflight/v1';delete f.gate.gitDeploymentInputs;delete f.gate.runtimeEvidencePin;
 f.check();assert.equal(f.calls.length,0);
});

// Parser contracts only: the existing subprocess boundary above supplies a
// summary. Actual activation evidence is checked separately by the real CLI.
function activatedSetup(t){
 const f=setup(t),oldCommit=f.selection.sourceCommit,oldBuildPin=f.summary.buildPin;
 const basePin=save(f.root,'base-selection.json',f.selection),sourceCommit='6'.repeat(40);
 const build={...f.build,targetCommit:sourceCommit,worktree:path.join(f.root,'new-source-release')};fs.mkdirSync(build.worktree);
 const buildPin=save(f.root,'activated-build.json',build);
 const bindings={57:{source:{buildPin,sourceCommit},target:{buildPin:oldBuildPin,sourceCommit:oldCommit}},
  58:{target:{buildPin:oldBuildPin,sourceCommit:oldCommit}},59:{target:{buildPin:oldBuildPin,sourceCommit:oldCommit}}};
 f.selection={schemaVersion:'TaskMainProgramSourceControlSelection/v2',baseSelectionPin:basePin,
  activationEvidencePins:[{path:path.join(f.root,'actual-receipt.private.json'),bytes:1,sha256:'e'.repeat(64)}]};
 f.selectionPin=save(f.root,'selection.json',f.selection);f.options['source-activation']=true;
 Object.assign(f.gate,{schemaVersion:'MainProgramAutomaticIncrementalUiPreflight/v3',implementationCommit:sourceCommit,
  installationCommit:sourceCommit,buildCommit:sourceCommit,deploymentSelectionPin:f.selectionPin,
  baseSelectionPin:basePin,controllerBuildBindings:structuredClone(bindings)});
 Object.assign(f.gate.gitDeploymentInputs.source,{installedCommit:sourceCommit,headCommit:sourceCommit});
 Object.assign(f.gate.gitDeploymentInputs.deploymentRootBindings.source,{path:build.worktree.replaceAll('\\','/'),
  buildPin,targetCommit:sourceCommit,headCommit:sourceCommit});
 Object.assign(f.runtime,{deploymentSelectionPin:f.selectionPin,gitDeploymentInputs:structuredClone(f.gate.gitDeploymentInputs)});
 f.gate.runtimeEvidencePin=save(f.root,'runtime.json',f.runtime);
 Object.assign(f.summary,{schemaVersion:'MainProgramSourceInstallationSummary/v1',selectionPin:f.selectionPin,
  sourceCommit,buildPin,baseSelectionPin:basePin,baseSourceCommit:oldCommit,baseBuildPin:oldBuildPin,
  controllerBuildBindings:bindings,installationVerified:true,runtimeVerified:false});
 f.summary.inputPins=f.summary.inputPins.filter(p=>!p.path.endsWith('selection.json'));
 for(const ref of [f.selectionPin,basePin,buildPin])f.summary.inputPins.push({path:path.join(f.root,ref.file),bytes:ref.bytes,sha256:ref.sha256});
 return f;
}
test('v3 explicitly accepts activated source and retains base target builds',t=>{
 const f=activatedSetup(t);f.check();assert.equal(f.calls.length,1);
 assert.equal(f.calls[0][1][3],path.join(f.root,'main_program_source_control_activated.py'));
 f.check();assert.equal(f.calls.length,1);
});
for(const [name,change] of [
 ['missing explicit option',f=>delete f.options['source-activation']],
 ['legacy gate',f=>f.gate.schemaVersion='MainProgramAutomaticIncrementalUiPreflight/v2'],
 ['wrong base pin',f=>f.gate.baseSelectionPin={...f.gate.baseSelectionPin,sha256:'0'.repeat(64)}],
 ['wrong source binding',f=>f.gate.controllerBuildBindings[57].source.sourceCommit='0'.repeat(40)],
 ['changed target binding',f=>f.gate.controllerBuildBindings[59].target.buildPin=f.summary.buildPin],
 ['unknown role',f=>f.summary.controllerBuildBindings[58].source=f.summary.controllerBuildBindings[57].source],
 ['claimed live health',f=>f.summary.runtimeVerified=true],
 ['bound only',f=>f.summary.installationVerified=false],
 ['other base generation',f=>f.summary.baseSourceCommit=f.summary.sourceCommit],
 ['unbound base build',f=>f.summary.inputPins=f.summary.inputPins.filter(p=>!p.path.endsWith('source-build.json'))],
])test('v3 refuses '+name,t=>{const f=activatedSetup(t);change(f);assert.throws(f.check,/MAIN_/);});
