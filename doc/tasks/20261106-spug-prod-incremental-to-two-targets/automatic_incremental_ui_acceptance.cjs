'use strict';
// Real UI acceptance only. Preparation/checking this file never launches a browser.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const TASK=__dirname,PRIVATE='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106';
const ORIGIN='http://127.0.0.1:18080',SOURCE='intruoyi-57-safe-20261024-v1',SERVER='172.30.30.57';
const HISTORICAL_COMMIT='0d445782dc06995b3c84b1b45146ea4b75483f92';
const PLAYWRIGHT='C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright';
const CREDENTIALS='C:/SpugHandoff/release/private/spug-login.private.json';
const PLAN_KEYS=['schemaVersion','sourceConfigRef','state','reasonCode','parentChainRef','baseFullRef','generationId','chainDepth','pointType','parentPointType','basePointType','finishedAt','baseFinishedAt','evidenceDigest','planDigest'];
const REQUEST_KEYS=['schemaVersion','operationId','action','sourceConfigRef','parentChainRef','recoveryPointRef','targetConfigRef'];
const MAIN_BINDING_KEYS=['deploymentSelectionPin','controlGenerationPin','spugInstallationPin','sourceCaptureConfigurationPin','sourceOwnerConfigurationPin'];
const CYCLE=/^[a-z][a-z0-9-]{0,47}$/;
const check=(value,code)=>{if(!value){const error=new Error(code);error.publicCode=code;throw error;}};
const read=file=>JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
const exact=(left,right)=>JSON.stringify(Object.keys(left).sort().map(k=>[k,left[k]]))===JSON.stringify(Object.keys(right).sort().map(k=>[k,right[k]]));
const pick=(value,keys)=>Object.fromEntries(keys.map(key=>[key,value?.[key]??null]));
const pin=plan=>pick(plan,['state','parentChainRef','baseFullRef','planDigest']);
function classifyLoginContract(status,body){
  check(status===200&&body&&typeof body==='object'&&!body.error,'REAL_LOGIN_REJECTED');
  const data=body.data;
  check(data&&typeof data==='object'&&!Array.isArray(data),'REAL_LOGIN_SUCCESS_DATA_INVALID');
  check(!data.required_mfa,'REAL_LOGIN_MFA_REQUIRED');
  check(typeof data.access_token==='string'&&data.access_token.length>0&&typeof data.has_real_ip==='boolean','REAL_LOGIN_SUCCESS_DATA_INVALID');
  return {needsNotice:!data.has_real_ip};
}
function exclusive(file,value){
  const descriptor=fs.openSync(file,'wx');
  try{fs.writeFileSync(descriptor,JSON.stringify(value,null,2),'utf8');fs.fsyncSync(descriptor);}finally{fs.closeSync(descriptor);}
}
function args(){
  const value={},flags=new Set(['execute','expect-terminal']);
  const fields=new Set(['kind','phase','observation','preflight','cycle','selection','browser-mode','expected-application','expected-source','expected-state','expected-parent','expected-base','expected-plan']);
  for(let i=2;i<process.argv.length;i++){
    const key=process.argv[i].replace(/^--/,'');
    check(process.argv[i].startsWith('--')&&!Object.hasOwn(value,key),'INVALID_OR_DUPLICATE_ARGUMENT');
    if(flags.has(key))value[key]=true;
    else{check(fields.has(key)&&process.argv[i+1]&&!process.argv[i+1].startsWith('--'),'UNKNOWN_OR_MISSING_ARGUMENT');value[key]=process.argv[++i];}
  }
  check(['FULL','I1','I2'].includes(value.kind)&&['preview','submit','verify'].includes(value.phase),'EXPLICIT_KIND_AND_PHASE_REQUIRED');
  check(/^[a-z0-9][a-z0-9-]{0,47}$/.test(value.observation||''),'UNIQUE_OBSERVATION_REQUIRED');
  check((value.phase==='submit')===!!value.execute,'SUBMIT_REQUIRES_EXPLICIT_EXECUTE');
  check(!value['expect-terminal']||value.phase==='verify','TERMINAL_ASSERTION_REQUIRES_VERIFY');
  const relative=path.relative(TASK,path.resolve(value.preflight||''));
  check(relative&&!relative.startsWith('..')&&!path.isAbsolute(relative)&&relative.endsWith('.json'),'TASK_PREFLIGHT_FILE_REQUIRED');
  value.preflight=path.resolve(value.preflight);
  check(Object.hasOwn(value,'cycle')===Object.hasOwn(value,'selection'),'CYCLE_AND_SELECTION_REQUIRED_TOGETHER');
  if(value.cycle){
    check(CYCLE.test(value.cycle),'EXPLICIT_CYCLE_INVALID');
    const selected=path.relative(TASK,path.resolve(value.selection));
    check(selected&&!selected.startsWith('..')&&!path.isAbsolute(selected)&&selected.endsWith('.json'),'TASK_MAIN_SELECTION_REQUIRED');
    value.selection=path.resolve(value.selection);
  }
  browserPolicy(value);
  return value;
}
function browserPolicy(options){
  const mode=options['browser-mode']??(options.cycle?'headed':'headless');
  check(['headed','headless'].includes(mode),'EXPLICIT_BROWSER_MODE_INVALID');
  return {mode,headless:mode==='headless'};
}
function artifactPaths(options){
  check(!options.cycle||CYCLE.test(options.cycle),'EXPLICIT_CYCLE_INVALID');
  const kind=options.kind.toLowerCase(),stem=options.cycle?`automatic-${options.cycle}-${kind}`:`automatic-${kind}`;
  const privateDir=options.cycle?path.join(PRIVATE,'automatic-incremental-ui',options.cycle):path.join(PRIVATE,'automatic-incremental-ui');
  const privateLabel=`${kind}-${options.phase}-${options.observation}`;
  return {receiptPath:path.join(TASK,stem+'-ui-submission.json'),terminalPath:path.join(TASK,stem+'-ui-terminal.json'),
    resultPath:path.join(TASK,`${stem}-${options.phase}-${options.observation}-result.json`),privateDir,privateLabel,
    screenshot:path.join(privateDir,privateLabel+'.png'),kindSession:path.join(privateDir,kind+'-session.private.json')};
}
function expectedFromArgs(options){
  check(options['expected-source']===SOURCE&&/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$/.test(options['expected-application']||''),'EXACT_REGISTERED_SOURCE_REQUIRED');
  const expected={applicationId:options['expected-application'],sourceConfigRef:SOURCE,plan:{
    state:options['expected-state'],parentChainRef:options['expected-parent']==='NONE'?null:options['expected-parent'],
    baseFullRef:options['expected-base']==='NONE'?null:options['expected-base'],planDigest:options['expected-plan']}};
  check(expected.plan.state===(options.kind==='FULL'?'BASELINE_REQUIRED':'READY')&&/^[a-f0-9]{64}$/.test(expected.plan.planDigest||''),'EXPLICIT_EXPECTED_PLAN_REQUIRED');
  for(const key of ['expected-parent','expected-base'])check(Object.hasOwn(options,key)&&/^(NONE|[A-Za-z0-9][A-Za-z0-9_.:-]{0,159})$/.test(options[key]),'EXPLICIT_PARENT_AND_BASE_REQUIRED');
  return expected;
}
function validateDeploymentContract(gate,kind,deployment,selectionPin){
  check(gate.schemaVersion==='AutomaticIncrementalUiPreflight/v2','EXPLICIT_STAGE_PREFLIGHT_REQUIRED');
  check(deployment.schemaVersion==='AutomaticStageDeployment/v1'&&deployment.kind===kind&&deployment.sourceConfigRef===SOURCE,'STAGE_SELECTION_SCOPE_MISMATCH');
  check(/^[a-f0-9]{40}$/.test(deployment.sourceCommit||'')&&deployment.spugCommit===HISTORICAL_COMMIT,'STAGE_COMMIT_INVALID');
  check(gate.implementationCommit===deployment.sourceCommit&&gate.installationCommit===deployment.sourceCommit&&gate.buildCommit===deployment.sourceCommit&&gate.spugCommit===deployment.spugCommit,'INSTALLED_COMMIT_MISMATCH');
  check(exact(gate.deploymentSelectionPin||{},selectionPin),'STAGE_SELECTION_PIN_CHANGED');
  const inputs=gate.gitDeploymentInputs;
  for(const [component,commit] of [['source',deployment.sourceCommit],['spug',deployment.spugCommit]]){
    check(inputs?.[component]?.installedCommit===commit&&inputs[component].deploymentInputsUnchanged===true&&inputs[component].installedCommitIsAncestor===true,'STAGE_GIT_INPUTS_NOT_VERIFIED');
  }
  check(/^[a-f0-9]{40}$/.test(inputs.source.headCommit||'')&&inputs.source.headCommit===inputs.spug.headCommit,'STAGE_GIT_HEAD_CHANGED');
}
function localPin(value){
  return value&&exact(Object.fromEntries(Object.keys(value).map(k=>[k,true])),{file:true,bytes:true,sha256:true})&&
    typeof value.file==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}\.json$/.test(value.file)&&
    Number.isSafeInteger(value.bytes)&&value.bytes>0&&/^[a-f0-9]{64}$/.test(value.sha256||'');
}
function remotePin(value){
  return value&&exact(Object.fromEntries(Object.keys(value).map(k=>[k,true])),{path:true,bytes:true,sha256:true})&&
    typeof value.path==='string'&&value.path.startsWith('/')&&!value.path.includes('\\')&&
    value.path.split('/').every(p=>p!=='.'&&p!=='..')&&Number.isSafeInteger(value.bytes)&&value.bytes>0&&/^[a-f0-9]{64}$/.test(value.sha256||'');
}
function readTaskPin(reference){
  check(localPin(reference),'MAIN_LOCAL_PIN_INVALID');
  const file=path.join(TASK,reference.file),info=fs.lstatSync(file);
  check(info.isFile()&&!info.isSymbolicLink()&&fs.realpathSync(file)===file&&info.size<=16*1024*1024,'MAIN_LOCAL_FILE_INVALID');
  const raw=fs.readFileSync(file);check(raw.length===reference.bytes&&sha(raw)===reference.sha256,'MAIN_PIN_BYTES_CHANGED');
  return JSON.parse(raw.toString('utf8'));
}
const mainProofIdentity=info=>[info.dev,info.ino,info.size,info.mtimeMs,info.ctimeMs];
const mainDeepEqual=(left,right)=>{
  if(left===right)return true;
  if(!left||!right||typeof left!=='object'||typeof right!=='object'||Array.isArray(left)!==Array.isArray(right))return false;
  const keys=Object.keys(left).sort();return keys.join('\0')===Object.keys(right).sort().join('\0')&&keys.every(k=>mainDeepEqual(left[k],right[k]));
};
const mainKeys=(value,keys)=>value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join(',')===[...keys].sort().join(',');
let mainInstallationProof=null,mainInstallationSelection=null;
function verifyMainInputClosure(summary,previous){
  const identities=[],paths=new Set();
  try{
    check(Array.isArray(summary.inputPins)&&summary.inputPins.length>0,'MAIN_CURRENT_INSTALLATION_INPUTS_REQUIRED');
    for(const pin of summary.inputPins){
      check(mainKeys(pin,['path','bytes','sha256'])&&typeof pin.path==='string'&&path.isAbsolute(pin.path)&&
        !pin.path.replaceAll('\\','/').split('/').some(p=>p==='.'||p==='..')&&Number.isSafeInteger(pin.bytes)&&pin.bytes>=0&&/^[a-f0-9]{64}$/.test(pin.sha256),'MAIN_CURRENT_INSTALLATION_INPUT_INVALID');
      const file=path.resolve(pin.path),before=fs.lstatSync(file);
      check(!paths.has(file)&&before.isFile()&&!before.isSymbolicLink()&&before.nlink===1&&path.resolve(fs.realpathSync(file))===file,'MAIN_CURRENT_INSTALLATION_INPUT_INVALID');
      paths.add(file);const raw=fs.readFileSync(file),after=fs.lstatSync(file),identity=mainProofIdentity(after);
      check(mainDeepEqual(mainProofIdentity(before),identity)&&raw.length===pin.bytes&&sha(raw)===pin.sha256,'MAIN_CURRENT_INSTALLATION_INPUT_CHANGED');
      identities.push({path:file,identity});
    }
    check(!previous||mainDeepEqual(identities,previous),'MAIN_CURRENT_INSTALLATION_INPUT_IDENTITY_CHANGED');
  }catch(error){check(false,error.publicCode||'MAIN_CURRENT_INSTALLATION_INPUT_UNREADABLE');}
  return identities;
}
function runMainInstallationCli(selectionPin,options){
  check(localPin(selectionPin)&&CYCLE.test(options?.cycle||'')&&['FULL','I1','I2'].includes(options?.kind)&&
    ['preview','submit','verify'].includes(options?.phase)&&/^[a-z0-9][a-z0-9-]{0,47}$/.test(options?.observation||''),
    'MAIN_CURRENT_INSTALLATION_OBSERVATION_INVALID');
  const {privateDir,privateLabel}=artifactPaths(options),directory=path.join(privateDir,privateLabel+'-current-installation');
  try{
    fs.mkdirSync(privateDir,{recursive:true});
    check(!fs.existsSync(directory),'MAIN_CURRENT_INSTALLATION_OBSERVATION_EXISTS');
    fs.mkdirSync(directory);
    check(path.resolve(fs.realpathSync(directory))===path.resolve(directory),'MAIN_CURRENT_INSTALLATION_EVIDENCE_WRITE_FAILED');
  }catch(error){check(false,error.publicCode||(error.code==='EEXIST'?'MAIN_CURRENT_INSTALLATION_OBSERVATION_EXISTS':'MAIN_CURRENT_INSTALLATION_EVIDENCE_WRITE_FAILED'));}
  const executable='C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
  const argv=['-B','-X','utf8',path.join(TASK,'main_program_current_installation.py'),'--selection',selectionPin.file,'--public-summary'];
  const timeoutMs=600000,clock=require('node:perf_hooks').performance,startedAt=new Date().toISOString(),start=clock.now();
  let response,thrown=null;
  try{response=require('node:child_process').spawnSync(executable,argv,
    {shell:false,timeout:timeoutMs,maxBuffer:16*1024*1024,windowsHide:true});}catch(error){thrown=error;}
  const finishedAt=new Date().toISOString(),durationMs=clock.now()-start,error=thrown||response?.error;
  const stdout=response?.stdout??Buffer.alloc(0),stderr=response?.stderr??Buffer.alloc(0);
  const exitCode=Number.isSafeInteger(response?.status)?response.status:null,signal=typeof response?.signal==='string'?response.signal:null;
  const errorCode=typeof error?.code==='string'?error.code:null;
  try{
    check(Buffer.isBuffer(stdout)&&Buffer.isBuffer(stderr),'MAIN_CURRENT_INSTALLATION_EVIDENCE_WRITE_FAILED');
    const save=(name,raw)=>{
      const file=path.join(directory,name),descriptor=fs.openSync(file,'wx');
      try{fs.writeFileSync(descriptor,raw);fs.fsyncSync(descriptor);}finally{fs.closeSync(descriptor);}
      check(fs.readFileSync(file).equals(raw),'MAIN_CURRENT_INSTALLATION_EVIDENCE_WRITE_FAILED');
      return {path:file,bytes:raw.length,sha256:sha(raw)};
    };
    const stdoutPin=save('stdout.private.log',stdout),stderrPin=save('stderr.private.log',stderr);
    exclusive(path.join(directory,'native.private.json'),{schemaVersion:'MainUiCurrentInstallationNative/v1',selectionPin,
      cycle:options.cycle,kind:options.kind,phase:options.phase,observation:options.observation,startedAt,finishedAt,durationMs,timeoutMs,
      executable,argv,responseReturned:!thrown&&response!==undefined,pid:Number.isSafeInteger(response?.pid)?response.pid:null,
      exitCode,signal,errorCode,stdoutPin,stderrPin});
  }catch(writeError){check(false,'MAIN_CURRENT_INSTALLATION_EVIDENCE_WRITE_FAILED');}
  if(error)check(false,errorCode==='ETIMEDOUT'?'MAIN_CURRENT_INSTALLATION_TIMEOUT':errorCode==='ENOBUFS'?
    'MAIN_CURRENT_INSTALLATION_OUTPUT_LIMIT':'MAIN_CURRENT_INSTALLATION_SPAWN_FAILED');
  check(signal===null&&exitCode!==null,'MAIN_CURRENT_INSTALLATION_TERMINATED');
  check(exitCode===0,'MAIN_CURRENT_INSTALLATION_EXIT_FAILED');
  check(stderr.length===0,'MAIN_CURRENT_INSTALLATION_STDERR_REJECTED');
  try{
    const text=stdout.toString('utf8');check(Buffer.from(text,'utf8').equals(stdout),'MAIN_CURRENT_INSTALLATION_INVALID');
    return JSON.parse(text);
  }catch(parseError){check(false,'MAIN_CURRENT_INSTALLATION_INVALID');}
}
function currentMainProof(deployment,selectionPin,gate,options){
  check(!mainInstallationSelection||mainDeepEqual(mainInstallationSelection,selectionPin),'MAIN_CURRENT_INSTALLATION_SELECTION_CHANGED');
  let summary=mainInstallationProof?.summary;
  if(!summary){
    summary=runMainInstallationCli(selectionPin,options);
  }
  check(mainKeys(summary,['schemaVersion','status','selectionPin','sourceCommit','controlGenerationPin','spugInstallationPin','buildPin','build','resourceBuildPin','spugCommit','inputPins'])&&
    summary.schemaVersion==='MainProgramCurrentInstallationSummary/v1'&&summary.status==='PASS'&&
    mainDeepEqual(summary.selectionPin,selectionPin)&&summary.sourceCommit===deployment.sourceCommit&&summary.spugCommit===gate.spugCommit&&
    mainDeepEqual(summary.controlGenerationPin,deployment.controlGenerationPin)&&mainDeepEqual(summary.spugInstallationPin,deployment.spugInstallationPin)&&
    mainKeys(summary.build,['fileCount','fileManifestSha256','packageSha256'])&&summary.build.fileCount===147&&
    /^[a-f0-9]{64}$/.test(summary.build.fileManifestSha256)&&/^[a-f0-9]{64}$/.test(summary.build.packageSha256),
    'MAIN_CURRENT_INSTALLATION_INVALID');
  const identities=verifyMainInputClosure(summary,mainInstallationProof?.identities);
  for(const ref of [selectionPin,summary.controlGenerationPin,summary.buildPin,summary.resourceBuildPin]){
    check(localPin(ref)&&summary.inputPins.some(p=>path.resolve(p.path)===path.resolve(TASK,ref.file)&&p.bytes===ref.bytes&&p.sha256===ref.sha256),
      'MAIN_CURRENT_INSTALLATION_DOCUMENT_UNBOUND');
  }
  return {summary,identities};
}
function validateMainDeploymentRoots(gate,deployment,selectionPin,options){
  try{
    const proof=currentMainProof(deployment,selectionPin,gate,options),summary=proof.summary;
    const inputs=gate.gitDeploymentInputs,bindings=inputs?.deploymentRootBindings;
    check(mainKeys(inputs,['source','spug','deploymentRootBindings'])&&mainKeys(bindings,['source','spug']),'MAIN_ROOT_BINDINGS_REQUIRED');
    const generation=readTaskPin(summary.controlGenerationPin);
    check(generation.schemaVersion==='MainProgramControlGeneration/v1'&&generation.status==='PASS'&&
      generation.sourceCommit===summary.sourceCommit&&mainDeepEqual(generation.buildPin,summary.buildPin),'MAIN_BUILD_GENERATION_CHANGED');
    for(const [component,reference,commit] of [['source',summary.buildPin,summary.sourceCommit],['spug',summary.resourceBuildPin,summary.spugCommit]]){
      const binding=bindings[component],original=readTaskPin(reference),git=inputs[component];
      check(mainKeys(binding,['schemaVersion','mode','path','buildPin','targetCommit','headCommit','registeredWorktreeMatched','clean'])&&
        binding.schemaVersion==='MainProgramDeploymentRoot/v1'&&binding.mode==='PINNED_BUILD_WORKTREE'&&
        binding.registeredWorktreeMatched===true&&binding.clean===true&&binding.targetCommit===commit&&binding.headCommit===commit&&
        localPin(binding.buildPin)&&mainDeepEqual(binding.buildPin,reference),'MAIN_ROOT_BINDING_INVALID');
      check(typeof binding.path==='string'&&path.isAbsolute(binding.path)&&typeof original.worktree==='string'&&path.isAbsolute(original.worktree)&&
        !binding.path.split('/').some(p=>p==='.'||p==='..')&&binding.path===path.resolve(binding.path).replaceAll('\\','/')&&
        binding.path===path.resolve(original.worktree).replaceAll('\\','/'),'MAIN_ROOT_PATH_CHANGED');
      check(original.status==='PASS'&&(component==='source'?
        original.targetCommit===commit&&original.allFilesShaAndCompileVerified===true:
        original.schemaVersion==='MainProgramSpugResourceBuild/v2'&&original.sourceCommit===commit&&original.files&&
          Number.isSafeInteger(original.fileCount)&&original.fileCount>0&&original.fileCount===Object.keys(original.files).length),'MAIN_BUILD_CHANGED');
      check(mainKeys(git,['installedCommit','headCommit','installedCommitIsAncestor','deploymentInputsUnchanged','deploymentInputScopes'])&&
        git.installedCommit===commit&&git.headCommit===commit&&git.installedCommitIsAncestor===true&&git.deploymentInputsUnchanged===true&&
        Array.isArray(git.deploymentInputScopes)&&git.deploymentInputScopes.length>0&&
        git.deploymentInputScopes.every(p=>typeof p==='string'&&p&&!p.startsWith('/')&&!p.includes('\\')&&!p.includes(':')&&!p.split('/').some(x=>!x||x==='.'||x==='..'))&&
        mainDeepEqual(git.deploymentInputScopes,[...new Set(git.deploymentInputScopes)].sort()),'MAIN_COMPONENT_GIT_INVALID');
      if(component==='spug')check(mainDeepEqual(git.deploymentInputScopes,Object.keys(original.files).sort()),'MAIN_COMPONENT_SCOPE_CHANGED');
      else check(git.deploymentInputScopes.includes('ops/backup_engine')&&git.deploymentInputScopes.includes('ops/recovery'),'MAIN_COMPONENT_SCOPE_CHANGED');
    }
    let runtime;try{runtime=readTaskPin(gate.runtimeEvidencePin);}catch(error){check(false,'MAIN_RUNTIME_PIN_CHANGED');}
    check(runtime.schemaVersion==='MainProgramAutomaticIncrementalUiRuntime/v1'&&runtime.status==='PASS'&&
      mainDeepEqual(runtime.deploymentSelectionPin,selectionPin)&&mainDeepEqual(runtime.gitDeploymentInputs,inputs),'MAIN_RUNTIME_BINDING_CHANGED');
    verifyMainInputClosure(summary,proof.identities);
    mainInstallationProof=proof;mainInstallationSelection=JSON.parse(JSON.stringify(selectionPin));
  }catch(error){mainInstallationProof=null;throw error;}
}
function validateMainDeploymentContract(gate,options,deployment,selectionPin){
  check(['MainProgramAutomaticIncrementalUiPreflight/v1','MainProgramAutomaticIncrementalUiPreflight/v2'].includes(gate.schemaVersion)&&CYCLE.test(options.cycle||'')&&gate.cycle===options.cycle,'MAIN_PREFLIGHT_CYCLE_MISMATCH');
  check(deployment.schemaVersion==='TaskMainProgramInstallations/v4'&&
    Object.keys(deployment).sort().join(',')===['schemaVersion','sourceCommit','controlGenerationPin','spugInstallationPin','verificationInputsPin'].sort().join(','),'MAIN_V4_SELECTION_REQUIRED');
  check(/^[a-f0-9]{40}$/.test(deployment.sourceCommit||'')&&gate.implementationCommit===deployment.sourceCommit&&
    gate.installationCommit===deployment.sourceCommit&&gate.buildCommit===deployment.sourceCommit&&/^[a-f0-9]{40}$/.test(gate.spugCommit||''),'MAIN_DEPLOYMENT_COMMIT_CHANGED');
  check(localPin(selectionPin)&&localPin(gate.deploymentSelectionPin)&&exact(gate.deploymentSelectionPin,selectionPin),'MAIN_SELECTION_PIN_CHANGED');
  for(const name of ['controlGenerationPin','spugInstallationPin'])check(localPin(deployment[name])&&localPin(gate[name])&&exact(deployment[name],gate[name]),'MAIN_DEPLOYMENT_PIN_CHANGED');
  check(localPin(deployment.verificationInputsPin)&&remotePin(gate.sourceCaptureConfigurationPin)&&remotePin(gate.sourceOwnerConfigurationPin)&&gate.mainDeploymentVerified===true,'MAIN_DEPLOYMENT_NOT_VERIFIED');
  if(gate.schemaVersion==='MainProgramAutomaticIncrementalUiPreflight/v2')validateMainDeploymentRoots(gate,deployment,selectionPin,options);
}
function validateMainBaseline(gate,options,expected,baseline){
  const fields=['schemaVersion','status','cycle','observedAt','applicationId','sourceConfigRef','deploymentSelectionPin','expectedPlan','operationId'];
  check(baseline&&Object.keys(baseline).sort().join(',')===fields.sort().join(',')&&baseline.schemaVersion==='MainProgramAutomaticIncrementalUiBaseline/v1'&&
    baseline.status==='PASS'&&baseline.cycle===options.cycle&&baseline.cycle===gate.cycle,'MAIN_BASELINE_SCOPE_CHANGED');
  check(baseline.applicationId===expected.applicationId&&baseline.sourceConfigRef===SOURCE&&
    localPin(baseline.deploymentSelectionPin)&&exact(baseline.deploymentSelectionPin,gate.deploymentSelectionPin)&&
    exact(baseline.expectedPlan||{},expected.plan)&&exact(baseline.expectedPlan||{},gate.expectedPlan),'MAIN_BASELINE_PLAN_CHANGED');
  check(baseline.operationId===(options.phase==='verify'?expected.operationId:null),'MAIN_BASELINE_OPERATION_CHANGED');
  check(expected.plan.state===(options.kind==='FULL'?'BASELINE_REQUIRED':'READY')&&/^[a-f0-9]{64}$/.test(expected.plan.planDigest||''),'MAIN_BASELINE_STATE_INVALID');
  if(options.kind!=='FULL')for(const key of ['parentChainRef','baseFullRef'])check(typeof expected.plan[key]==='string'&&expected.plan[key].length>0,'MAIN_BASELINE_CHAIN_REQUIRED');
  const age=Date.now()-Date.parse(baseline.observedAt);
  check(Number.isFinite(age)&&age>=-30000&&age<=900000,'MAIN_BASELINE_STALE');
}
function cycleFields(gate,cycle){
  return cycle?{cycle,...Object.fromEntries(MAIN_BINDING_KEYS.map(name=>[name,gate[name]])),baselineEvidencePin:gate.baselineEvidencePin}:{};
}
function validateCycleBinding(record,gate,cycle){
  check(record.cycle===cycle&&gate.cycle===cycle&&record.spugCommit===gate.spugCommit&&
    record.implementationCommit===gate.implementationCommit,'ORIGINAL_CYCLE_DEPLOYMENT_CHANGED');
  for(const name of MAIN_BINDING_KEYS)check(exact(record[name]||{},gate[name]||{}),'ORIGINAL_CYCLE_DEPLOYMENT_CHANGED');
  check(localPin(record.baselineEvidencePin),'ORIGINAL_BASELINE_PIN_REQUIRED');
}
function validateReceiptDeployment(receipt,gate,kind,cycle){
  check(receipt.kind===kind&&receipt.implementationCommit===gate.implementationCommit,'ORIGINAL_RECEIPT_DEPLOYMENT_CHANGED');
  if(cycle){
    check(receipt.schemaVersion==='AutomaticIncrementalUiSubmission/v3','MAIN_ORIGINAL_SUBMISSION_REQUIRED');
    validateCycleBinding(receipt,gate,cycle);return;
  }
  if(receipt.schemaVersion==='AutomaticIncrementalUiSubmission/v1'){
    check(kind==='FULL'&&receipt.implementationCommit===HISTORICAL_COMMIT&&gate.spugCommit===HISTORICAL_COMMIT,'UNKNOWN_LEGACY_SUBMISSION_GENERATION');
  }else{
    check(receipt.schemaVersion==='AutomaticIncrementalUiSubmission/v2'&&receipt.spugCommit===gate.spugCommit&&exact(receipt.deploymentSelectionPin||{},gate.deploymentSelectionPin),'ORIGINAL_RECEIPT_DEPLOYMENT_CHANGED');
  }
}
function validateGate(options,expected,originalHash){
  const raw=fs.readFileSync(options.preflight),gate=JSON.parse(raw.toString('utf8').replace(/^\uFEFF/,''));
  check(!originalHash||sha(raw)===originalHash,'PREFLIGHT_CHANGED_AFTER_REVIEW');
  check(gate.status==='PASS'&&gate.experiencePreflight==='PASS','EXPERIENCE_PREFLIGHT_REQUIRED');
  check(gate.kind===options.kind&&gate.phase===options.phase&&gate.origin===ORIGIN&&gate.server===SERVER&&gate.mode==='safe','PREFLIGHT_SCOPE_MISMATCH');
  check(gate.applicationId===expected.applicationId&&gate.sourceConfigRef===SOURCE&&exact(gate.expectedPlan||{},expected.plan),'PREFLIGHT_PLAN_MISMATCH');
  const selectionFile=options.cycle?path.basename(options.selection):`automatic-${options.kind.toLowerCase()}-deployment-selection.json`;
  const selectionRaw=fs.readFileSync(path.join(TASK,selectionFile));
  const selectionPin={file:selectionFile,bytes:selectionRaw.length,sha256:sha(selectionRaw)};
  if(options.cycle){
    check(path.join(TASK,selectionFile)===options.selection,'TASK_MAIN_SELECTION_REQUIRED');
    const selected=readTaskPin(selectionPin);
    validateMainDeploymentContract(gate,options,selected,selectionPin);
    validateMainBaseline(gate,options,expected,readTaskPin(gate.baselineEvidencePin));
  }else validateDeploymentContract(gate,options.kind,JSON.parse(selectionRaw.toString('utf8')),selectionPin);
  const age=Date.now()-Date.parse(gate.observedAt);
  check(Number.isFinite(age)&&age>=-30000&&age<=900000,'PREFLIGHT_STALE');
  for(const name of ['sourceIdentityVerified','installationVerified','sourceServicesHealthy','archiveReady','capacityReady','noConcurrentMaintenance'])check(gate[name]===true,'PREFLIGHT_'+name.toUpperCase()+'_REQUIRED');
  if(options.execute)check(gate.sourceIdleVerified===true,'SOURCE_IDLE_PREFLIGHT_REQUIRED');
  check(typeof gate.expectedUserLabel==='string'&&gate.expectedUserLabel.length>0&&gate.expectedUserLabel.length<=80,'EXPECTED_LOGGED_IN_IDENTITY_REQUIRED');
  return {gate,hash:sha(raw)};
}
function checkEarlierChain(kind,expected){
  if(kind==='FULL')return;
  const full=read(path.join(TASK,'automatic-full-ui-terminal.json'));
  check(full.schemaVersion==='AutomaticIncrementalUiTerminal/v1'&&full.operationState==='SUCCEEDED'&&full.request.action==='FULL'&&full.request.sourceConfigRef===SOURCE,'SUCCESSFUL_FULL_UI_RECEIPT_REQUIRED');
  check(expected.plan.baseFullRef===full.request.operationId,'EXPECTED_FULL_ROOT_CHANGED');
  const parent=kind==='I1'?full:read(path.join(TASK,'automatic-i1-ui-terminal.json'));
  check(parent.operationState==='SUCCEEDED'&&parent.request.sourceConfigRef===SOURCE&&parent.applicationId===expected.applicationId,'SUCCESSFUL_PARENT_UI_RECEIPT_REQUIRED');
  if(kind==='I2')check(parent.request.action==='INCREMENTAL'&&parent.request.parentChainRef===full.request.operationId,'FIRST_INCREMENT_CHAIN_MISMATCH');
  check(expected.plan.parentChainRef===parent.request.operationId,'EXPECTED_PARENT_CHANGED');
}
async function main(){
  const options=args(),kind=options.kind.toLowerCase();
  const {receiptPath,resultPath,terminalPath,privateDir,privateLabel,screenshot,kindSession}=artifactPaths(options);
  check(!fs.existsSync(resultPath),'OBSERVATION_ALREADY_RECORDED');
  let receipt=null,expected;
  if(options.phase==='verify'){
    check(!Object.keys(options).some(key=>key.startsWith('expected-')),'VERIFY_USES_IMMUTABLE_ORIGINAL_RECEIPT');
    receipt=read(receiptPath);
    check((options.cycle?receipt.schemaVersion==='AutomaticIncrementalUiSubmission/v3':['AutomaticIncrementalUiSubmission/v1','AutomaticIncrementalUiSubmission/v2'].includes(receipt.schemaVersion))&&receipt.kind===options.kind&&receipt.request.sourceConfigRef===SOURCE,'ORIGINAL_RECEIPT_MISMATCH');
    expected={applicationId:receipt.applicationId,sourceConfigRef:SOURCE,plan:pin(receipt.plan)};
    if(options.cycle)expected.operationId=receipt.request.operationId;
  }else{
    check(!fs.existsSync(receiptPath),'ALREADY_ATTEMPTED_USE_VERIFY_ONLY');
    expected=expectedFromArgs(options);if(!options.cycle)checkEarlierChain(options.kind,expected);
  }
  const reviewed=validateGate(options,expected);
  if(receipt)validateReceiptDeployment(receipt,reviewed.gate,options.kind,options.cycle);
  fs.mkdirSync(privateDir,{recursive:true});
  check(!fs.existsSync(screenshot),'PRIVATE_OBSERVATION_ALREADY_EXISTS');
  const commonSession=path.join(PRIVATE,'spug-active-session.private.json');
  const storageState=options.phase==='verify'?(fs.existsSync(kindSession)?kindSession:fs.existsSync(commonSession)?commonSession:undefined):undefined;
  const {chromium}=require(PLAYWRIGHT);
  const browserMode=browserPolicy(options);
  const browser=await chromium.launch({channel:'chrome',headless:browserMode.headless,timeout:20000});
  const context=await browser.newContext({viewport:{width:1440,height:1080},...(storageState?{storageState}:{})});
  const page=await context.newPage();page.setDefaultTimeout(45000);
  if(!browserMode.headless)await page.bringToFront();
  const report={schemaVersion:'AutomaticIncrementalUiObservation/v1',kind:options.kind,phase:options.phase,
    observation:options.observation,browserMode:browserMode.mode,startedAt:new Date().toISOString(),implementationCommit:reviewed.gate.implementationCommit,
    spugCommit:reviewed.gate.spugCommit,deploymentSelectionPin:reviewed.gate.deploymentSelectionPin,
    ...cycleFields(reviewed.gate,options.cycle),
    preflightSha256:reviewed.hash,realBrowser:true,identityVerified:false,permissionVerified:false,loginPosts:0,businessPosts:0,
    blockedRequests:[],pageErrorCount:0,request:null,operationState:null,status:'NOT_COMPLETED'};
  let frame,armed=null,latest=null,followupAttempted=false;
  const pageErrors=[];
  page.on('pageerror',error=>{report.pageErrorCount++;pageErrors.push({name:error.name,message:error.message,stack:error.stack});});
  await context.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url()),method=request.method();
    try{
      check(url.origin===ORIGIN,'UNEXPECTED_NETWORK_ORIGIN');
      if(['GET','HEAD','OPTIONS'].includes(method)){
        if(options.phase==='verify'&&/^\/backup-entry-api\/(operations|progress)\//.test(url.pathname)){
          check(url.pathname.endsWith('/'+receipt.request.operationId),'VERIFY_OTHER_OPERATION_READ_REFUSED');
        }
        return await route.continue();
      }
      if(method==='POST'&&url.pathname==='/api/account/login/'&&report.loginPosts===0){report.loginPosts++;return await route.continue();}
      check(options.execute&&method==='POST'&&url.pathname==='/backup-entry-api/automatic-incremental'&&armed&&report.businessPosts===0,'UNEXPECTED_BUSINESS_WRITE_REFUSED');
      const intent=request.postDataJSON();
      check(exact(intent,armed.intent),'FINAL_POST_DOES_NOT_MATCH_CONFIRMED_INTENT');
      validateGate(options,expected,reviewed.hash);
      receipt={schemaVersion:options.cycle?'AutomaticIncrementalUiSubmission/v3':'AutomaticIncrementalUiSubmission/v2',kind:options.kind,attemptReservedAt:new Date().toISOString(),
        applicationId:expected.applicationId,implementationCommit:reviewed.gate.implementationCommit,preflightSha256:reviewed.hash,
        spugCommit:reviewed.gate.spugCommit,deploymentSelectionPin:reviewed.gate.deploymentSelectionPin,
        ...cycleFields(reviewed.gate,options.cycle),
        request:armed.request,intent:armed.intent,plan:armed.plan,status:'POST_ATTEMPT_RESERVED_OUTCOME_UNKNOWN'};
      exclusive(receiptPath,receipt); // durable wx fence before any final bytes leave the browser
      report.businessPosts++;report.request=receipt.request;armed=null;
      return await route.continue();
    }catch(error){
      report.blockedRequests.push({method,path:url.pathname,code:error.publicCode||'REQUEST_GUARD_FAILED'});
      await route.abort('blockedbyclient');
    }
  });
  const readOriginal=async response=>{
    check(response.status()===200,'ORIGINAL_QUERY_NOT_SUCCESSFUL');
    const value=await response.json();
    check(value.applicationId===receipt.applicationId&&exact(pick(value.request,REQUEST_KEYS),receipt.request),'ORIGINAL_REQUEST_CHANGED');
    check(exact(pin(value.automaticIncrementalPlan),pin(receipt.plan)),'ORIGINAL_PLAN_CHANGED');
    latest=value;report.request=pick(value.request,REQUEST_KEYS);report.operationState=value.result?.state||null;
    report.errorCode=value.result?.errorCode||value.queryError||value.dispatchErrorCode||null;
    report.spugHistoryId=value.spugHistoryId||null;
    return value;
  };
  const queryOriginalThroughUi=async()=>{
    const id=receipt.request.operationId;
    await frame.locator('#simple-progress-tab').click();
    await frame.waitForFunction(expectedId=>document.querySelector('#operation-reference')?.textContent===expectedId&&!document.querySelector('#simple-query').disabled, id,{timeout:90000});
    const response=page.waitForResponse(r=>r.request().method()==='GET'&&new URL(r.url()).origin===ORIGIN&&new URL(r.url()).pathname==='/backup-entry-api/operations/'+id,{timeout:35000});
    const observed=response.then(value=>({value}),()=>({error:true}));
    await frame.locator('#simple-query').click();
    const outcome=await observed;check(!outcome.error,'ORIGINAL_QUERY_TIMEOUT_KEEP_ORIGINAL');
    return readOriginal(outcome.value);
  };
  const followUnknownOriginal=async()=>{
    if(!receipt||!frame||followupAttempted)return;
    followupAttempted=true;armed=null;
    try{
      await queryOriginalThroughUi();
      check(['RUNNING','SUCCEEDED'].includes(report.operationState)&&!latest.queryError,'ORIGINAL_STATE_UNCONFIRMED');
      report.status='ORIGINAL_OBSERVED_AFTER_UNKNOWN';
    }catch(error){report.followupError=error.publicCode||'ORIGINAL_QUERY_UNCONFIRMED';}
  };
  try{
    report.stage='authenticated-page';
    await page.goto(ORIGIN+'/',{waitUntil:'domcontentloaded',timeout:60000});
    await page.waitForFunction(()=>document.querySelector('input[placeholder="请输入账户"]')||[...document.querySelectorAll('span,a')].some(element=>element.textContent.trim()==='备份与恢复'),null,{timeout:45000});
    if(await page.getByPlaceholder('请输入账户').isVisible()){
      const credential=read(CREDENTIALS);
      check(typeof credential.username==='string'&&typeof credential.password==='string','PRIVATE_LOGIN_CREDENTIALS_INVALID');
      await page.getByPlaceholder('请输入账户').fill(credential.username);
      await page.getByPlaceholder('请输入密码').fill(credential.password);
      const login=page.waitForResponse(r=>new URL(r.url()).origin===ORIGIN&&new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST',{timeout:45000});
      await page.getByRole('button',{name:'登 录',exact:true}).click();
      report.stage='login-response-contract';
      const response=await login,raw=await response.text();
      exclusive(path.join(privateDir,privateLabel+'-login-response.private.json'),{observedAt:new Date().toISOString(),httpStatus:response.status(),body:raw});
      report.loginResponseRecorded=true;
      let body;try{body=JSON.parse(raw);}catch{check(false,'REAL_LOGIN_RESPONSE_JSON_INVALID');}
      const data=body?.data;
      report.loginShape={httpStatus:response.status(),errorPresent:Boolean(body?.error),dataPresent:Object.hasOwn(body||{},'data'),
        dataObject:Boolean(data&&typeof data==='object'&&!Array.isArray(data)),requiredMfa:Boolean(data?.required_mfa),
        hasRealIp:typeof data?.has_real_ip==='boolean'?data.has_real_ip:null,tokenReturned:typeof data?.access_token==='string'&&data.access_token.length>0};
      const contract=classifyLoginContract(response.status(),body);
      if(contract.needsNotice){
        report.stage='login-security-notice';
        const notice=page.getByRole('button',{name:'知道了',exact:true});
        await notice.waitFor({state:'visible'});await notice.click();await notice.waitFor({state:'hidden'});
        report.loginNoticeConfirmed=true;
      }
      report.stage='login-session-and-identity';
      await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));
    }
    report.stage='authenticated-nickname';
    await page.getByText(reviewed.gate.expectedUserLabel,{exact:true}).first().waitFor({state:'visible'});
    report.stage='authenticated-backup-menu';
    const menu=page.getByText('备份与恢复',{exact:true}).first();await menu.waitFor({state:'visible'});
    report.identityVerified=true;
    await menu.click();await page.waitForURL(ORIGIN+'/backup-center',{timeout:45000});
    const iframe=await page.locator('iframe[src="/backup-restore/?embedded=1"]').elementHandle();
    check(iframe,'REAL_BACKUP_IFRAME_REQUIRED');frame=await iframe.contentFrame();check(frame,'BACKUP_FRAME_UNAVAILABLE');
    await frame.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:120000});
    if(options.phase==='verify'){
      report.stage='original-only-verification';
      const shown=await frame.locator('#operation-reference').textContent();
      if(shown!==receipt.request.operationId){
        await frame.locator('#simple-history-tab').click();
        const row=frame.locator('#simple-history .history-row').filter({hasText:receipt.request.operationId});
        await row.waitFor({state:'visible'});check(await row.count()===1,'EXACT_ORIGINAL_HISTORY_ROW_REQUIRED');
        await row.getByRole('button',{name:'查看进度',exact:true}).click();
      }
      await queryOriginalThroughUi();report.permissionVerified=true;
      check(report.operationState!=='FAILED','ORIGINAL_BACKUP_FAILED');
      check(['RUNNING','SUCCEEDED'].includes(report.operationState)&&!latest.queryError,'ORIGINAL_STATE_UNCONFIRMED');
      if(options['expect-terminal'])check(report.operationState==='SUCCEEDED'&&!latest.queryError,'ACTUAL_SUCCESS_REQUIRED');
      report.status=report.operationState==='SUCCEEDED'?'SUCCEEDED_VERIFIED':'ORIGINAL_OBSERVED';
    }else{
      report.stage='backup-form';
      await frame.locator('#simple-backup-tab').click();
      for(const [id,value] of [['simple-product','intruoyi'],['simple-server',SERVER],['simple-mode','safe']]){
        await frame.waitForFunction(element=>!switching&&!document.getElementById(element).disabled,id,{timeout:120000});
        await frame.locator('#'+id).selectOption(value);
      }
      await frame.waitForFunction(app=>!switching&&selected()?.applicationId===app&&!document.querySelector('#simple-type').disabled,expected.applicationId,{timeout:120000});
      const planResponse=page.waitForResponse(r=>{
        const url=new URL(r.url());return r.request().method()==='GET'&&url.origin===ORIGIN&&url.pathname==='/backup-entry-api/incremental-plan'&&url.searchParams.get('applicationId')===expected.applicationId;
      },{timeout:70000});
      const observedPlan=planResponse.then(value=>({value}),()=>({error:true}));
      await frame.locator('#simple-type').selectOption('INCREMENTAL');
      const response=await observedPlan;check(!response.error&&response.value.ok(),'LIVE_PLAN_HTTP_NOT_READY');
      const payload=await response.value.json();
      check(payload.applicationId===expected.applicationId&&payload.plan?.sourceConfigRef===SOURCE&&exact(pin(payload.plan),expected.plan),'LIVE_PLAN_CHANGED');
      await frame.waitForFunction(()=>!switching&&!incrementalPlanLoading&&!document.querySelector('#simple-submit').disabled,null,{timeout:90000});
      const rendered=await frame.evaluate(()=>({applicationId:selected()?.applicationId,sourceConfigRef:selected()?.sourceConfigRef,plan:currentIncrementalPlan(),server:S('simple-server').value,mode:S('simple-mode').value}));
      check(rendered.applicationId===expected.applicationId&&rendered.sourceConfigRef===SOURCE&&rendered.server===SERVER&&rendered.mode==='safe'&&exact(pin(rendered.plan),expected.plan),'RENDERED_PLAN_MISMATCH');
      report.permissionVerified=true;report.plan=pick(payload.plan,PLAN_KEYS);
      await frame.locator('#simple-submit').click();await frame.locator('#simple-confirm').waitFor({state:'visible'});
      const confirmed=await frame.evaluate(()=>({request:confirmation?.request,applicationId:confirmation?.applicationId,plan:confirmation?.automaticIncrementalPlan}));
      const request=pick(confirmed.request,REQUEST_KEYS),action=options.kind==='FULL'?'FULL':'INCREMENTAL';
      check(confirmed.applicationId===expected.applicationId&&exact(pin(confirmed.plan),expected.plan),'CONFIRMED_PLAN_CHANGED');
      check(Object.keys(confirmed.request||{}).length===REQUEST_KEYS.length&&request.schemaVersion==='SmallAppBackupUiRequest/v1'&&request.action===action&&request.sourceConfigRef===SOURCE&&request.parentChainRef===(action==='FULL'?null:expected.plan.parentChainRef)&&request.recoveryPointRef===null&&request.targetConfigRef===null,'CONFIRMED_REQUEST_MISMATCH');
      check(/^[A-Za-z0-9][A-Za-z0-9_.:-]{7,159}$/.test(request.operationId||''),'ORIGINAL_OPERATION_ID_REQUIRED');
      const text=await frame.locator('#confirm-summary').innerText();
      for(const term of [SOURCE,SERVER,'安全模式',action==='FULL'?'全量备份':'增量备份'])check(text.includes(term),'VISIBLE_CONFIRMATION_MISMATCH');
      if(action==='FULL')check(text.includes('全量基线')&&text.includes(payload.plan.reasonCode),'FULL_BASELINE_REASON_NOT_VISIBLE');
      else for(const ref of [expected.plan.parentChainRef,expected.plan.baseFullRef])check(text.includes(ref),'VISIBLE_CHAIN_CONFIRMATION_MISMATCH');
      report.request=request;
      await page.screenshot({path:screenshot,fullPage:true});
      await context.storageState({path:kindSession});
      if(options.phase==='preview'){
        await frame.locator('#simple-cancel').click();report.status='PREVIEW_VERIFIED_NO_SUBMISSION';
      }else{
        validateGate(options,expected,reviewed.hash);
        armed={request,plan:pick(payload.plan,PLAN_KEYS),intent:{schemaVersion:'AutomaticIncrementalRequest/v1',operationId:request.operationId,applicationId:expected.applicationId,planDigest:expected.plan.planDigest}};
        report.stage='one-final-ui-submit';
        const responsePromise=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).origin===ORIGIN&&new URL(r.url()).pathname==='/backup-entry-api/automatic-incremental',{timeout:70000});
        const observed=responsePromise.then(value=>({value}),()=>({error:true}));
        await frame.locator('#simple-confirm-submit').click();
        const outcome=await observed;
        check(report.businessPosts===1&&receipt,'FINAL_POST_NOT_DISPATCHED');
        if(outcome.error){
          report.status='UNKNOWN_KEEP_ORIGINAL';report.errorCode='SUBMISSION_RESPONSE_TIMEOUT';
          await followUnknownOriginal();
        }else{
          const value=await outcome.value.json();report.httpStatus=outcome.value.status();
          if(outcome.value.status()===409&&value.accepted===false&&value.operationId===request.operationId&&value.applicationId===expected.applicationId){
            report.status='REJECTED_UNACCEPTED_RECEIPT_RETAINED';report.errorCode=value.errorCode||'AUTOMATIC_REQUEST_REJECTED';
          }else if(outcome.value.ok()){
            check(value.applicationId===expected.applicationId&&exact(pick(value.request,REQUEST_KEYS),request)&&exact(pin(value.automaticIncrementalPlan),expected.plan),'SUBMISSION_RECEIPT_MISMATCH');
            latest=value;report.operationState=value.result?.state||null;report.spugHistoryId=value.spugHistoryId||null;
            report.status='ACCEPTED_FOLLOW_ORIGINAL';
          }else{
            report.status='UNKNOWN_KEEP_ORIGINAL';report.errorCode=value.errorCode||'SUBMISSION_OUTCOME_UNKNOWN';
            await followUnknownOriginal();
          }
        }
      }
    }
    check(report.blockedRequests.length===0&&report.pageErrorCount===0,'UNEXPECTED_PAGE_OR_REQUEST_ERROR');
    if(report.status==='SUCCEEDED_VERIFIED'){
      const terminal={schemaVersion:options.cycle?'AutomaticIncrementalUiTerminal/v3':'AutomaticIncrementalUiTerminal/v1',kind:options.kind,applicationId:receipt.applicationId,
        observedAt:new Date().toISOString(),request:receipt.request,plan:receipt.plan,operationState:'SUCCEEDED',spugHistoryId:report.spugHistoryId,
        observation:options.observation,preflightSha256:reviewed.hash};
      if(options.cycle)Object.assign(terminal,{implementationCommit:receipt.implementationCommit,spugCommit:receipt.spugCommit,...cycleFields(reviewed.gate,options.cycle)});
      if(fs.existsSync(terminalPath)){
        const original=read(terminalPath);check(exact(original.request,terminal.request),'TERMINAL_ORIGINAL_CHANGED');
        if(options.cycle){
          check(original.schemaVersion==='AutomaticIncrementalUiTerminal/v3'&&original.kind===options.kind&&
            original.applicationId===terminal.applicationId&&original.operationState==='SUCCEEDED'&&exact(pin(original.plan),pin(terminal.plan)),'MAIN_ORIGINAL_TERMINAL_REQUIRED');
          validateCycleBinding(original,reviewed.gate,options.cycle);
        }
      }
      else exclusive(terminalPath,terminal);
    }
    if(['UNKNOWN_KEEP_ORIGINAL','REJECTED_UNACCEPTED_RECEIPT_RETAINED'].includes(report.status))process.exitCode=2;
  }catch(error){
    report.status=receipt?'FAILED_KEEP_ORIGINAL':'FAILED_BEFORE_SUBMISSION';
    report.errorCode=error.publicCode||(error.name==='TimeoutError'?'UI_TIMEOUT':'UI_HELPER_FAILED');
    if(options.phase==='submit')await followUnknownOriginal();
    process.exitCode=1;
  }finally{
    report.finishedAt=new Date().toISOString();
    if(pageErrors.length){
      exclusive(path.join(privateDir,privateLabel+'-page-errors.private.json'),{observedAt:report.finishedAt,count:report.pageErrorCount,errors:pageErrors});
      report.pageErrorEvidenceRecorded=true;
    }
    if(report.loginPosts&&!report.identityVerified){
      try{
        const state=await page.evaluate(()=>({tokenStored:Boolean(localStorage.getItem('token')),
          accountInputPresent:Boolean(document.querySelector('input[placeholder="请输入账户"]')),
          captchaInputPresent:Boolean(document.querySelector('input[placeholder="请输入验证码"]')),
          buttons:[...document.querySelectorAll('button')].map(button=>button.textContent.trim()),
          notices:[...document.querySelectorAll('.ant-message,.ant-modal')].map(element=>element.textContent)}));
        exclusive(path.join(privateDir,privateLabel+'-login-state.private.json'),state);report.loginStateRecorded=true;
      }catch{report.loginStateRecorded=false;}
    }
    try{if(!fs.existsSync(screenshot))await page.screenshot({path:screenshot,fullPage:true});}catch{report.screenshotUnavailable=true;}
    try{await context.storageState({path:kindSession});}catch{report.sessionSaveFailed=true;}
    try{exclusive(resultPath,report);console.log(JSON.stringify(report));}
    finally{await browser.close();}
  }
}
main().catch(error=>{console.error(JSON.stringify({status:'NOT_STARTED',errorCode:error.publicCode||'HELPER_PREFLIGHT_OR_RESOURCE_FAILED'}));process.exitCode=1;});
