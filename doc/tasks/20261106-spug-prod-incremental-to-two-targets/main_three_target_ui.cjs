'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const TASK=__dirname,PRIVATE='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106';
const ORIGIN='http://127.0.0.1:18080',SOURCE='intruoyi-57-safe-20261024-v1';
const POINTS=['smallapp-3c2395ff88bd474e9fc007649565b848','smallapp-20a1bb9b78ac402693289675d16c63dd','smallapp-e7b668792c8f4bce945a52f984d3c660'];
const ORIGINAL_FAILURE='smallapp-b4f21de7a0c64d31beda7efa0204ced8';
const READER_FAILURE='smallapp-6546b96486f7413a84c7281c95131f1f';
const REPEAT_SCHEMA='TaskMainProgramTargetControlSuccessorSelection/v2';
const MIXED_SCHEMA='TaskMainProgramTargetControlSuccessorSelection/v3';
const isRepeated=schema=>schema===REPEAT_SCHEMA||schema===MIXED_SCHEMA;
const GENERATIONS=Object.freeze({
 'TaskMainProgramTargetControlSelection/v1':Object.freeze({loaderModule:'main_program_target_control_activated',loaderFunction:'load_activated_target_installation',targetCommit:'a3121c64d46fcdc2c1a3195a2cbbf8ca1c05742e',submissionFile:'main-i2-to-test58-ui-submission.json'}),
 'TaskMainProgramTargetControlSuccessorSelection/v1':Object.freeze({loaderModule:'main_program_target_control_successor',loaderFunction:'load_activated_target_successor_installation',targetCommit:'b9caa00b7eeed2b915c8855a8313521e57d06f72',submissionFile:'main-i2-to-test58-ui-submission-b9caa00.json'}),
 [MIXED_SCHEMA]:Object.freeze({loaderModule:'main_program_current_installation',loaderFunction:'load_current_target_installation'}),
 [REPEAT_SCHEMA]:Object.freeze({loaderModule:'main_program_current_installation',loaderFunction:'load_current_target_installation'})
});
const need=(value,code)=>{if(!value)throw Error(code);};
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const equal=require('node:util').isDeepStrictEqual;
function assertPointChain(proof){
 need(proof.status==='SUCCEEDED_VERIFIED'&&proof.operationId===POINTS[2]&&proof.parentOperationId===POINTS[1]&&
  proof.baseFullOperationId===POINTS[0]&&proof.chainDepth===2&&proof.actualExitCode===0&&
  proof.originalSourceRestored===true&&proof.originalWorkerExited===true,'ORIGINAL_I2_SUCCESS_REQUIRED');
 return [...POINTS];
}
function restoreWriteAllowed(phase,request,point,persisted,writes,previousOperationId=null){
 const keys=['schemaVersion','operationId','action','sourceConfigRef','parentChainRef','recoveryPointRef','targetConfigRef'];
 return phase==='submit'&&!persisted&&writes===0&&request&&typeof request==='object'&&!Array.isArray(request)&&
  Object.keys(request).sort().join(',')===keys.sort().join(',')&&request.schemaVersion==='SmallAppBackupUiRequest/v1'&&
  /^smallapp-[0-9a-f]{32}$/.test(request.operationId)&&request.operationId!==previousOperationId&&request.action==='RESTORE'&&request.sourceConfigRef===SOURCE&&
  request.parentChainRef===null&&point===POINTS[2]&&request.recoveryPointRef===point&&
  request.targetConfigRef==='intruoyi-main-58-safe-restore-20261104-v1';
}
function targetGeneration(schema){need(Object.hasOwn(GENERATIONS,schema),'UNKNOWN_TARGET_SELECTION_SCHEMA');return GENERATIONS[schema];}
function localPinShape(value){return value&&equal(Object.keys(value).sort(),['bytes','file','sha256'])&&
 /^[A-Za-z0-9][A-Za-z0-9_.-]*\.json$/.test(value.file)&&Number.isSafeInteger(value.bytes)&&value.bytes>0&&/^[0-9a-f]{64}$/.test(value.sha256);}
function assertInstallationGeneration(value){
 need(value&&value.schemaVersion==='MainThreeTargetInstallationSummary/v1'&&value.status==='PASS','INSTALLATION_SUMMARY_INVALID');
 let profile=targetGeneration(value.selectionSchemaVersion);const controllers=value.controllers;
 if(isRepeated(value.selectionSchemaVersion)){
  need(localPinShape(value.selectionPin)&&localPinShape(value.verifiedTargetBuildPin)&&/^[0-9a-f]{40}$/.test(value.verifiedTargetCommit),'VERIFIED_TARGET_BUILD_REQUIRED');
  const ancestry=value.targetSelectionAncestry;need(Array.isArray(ancestry)&&ancestry.length>=2&&ancestry.length<=18,'VERIFIED_TARGET_ANCESTRY_REQUIRED');
  const seen=new Set();for(const row of ancestry){
   need(row&&equal(Object.keys(row).sort(),['selectionPin','selectionSchemaVersion','sourceCommit'])&&localPinShape(row.selectionPin)&&
    /^[0-9a-f]{40}$/.test(row.sourceCommit)&&!seen.has(row.selectionPin.file)&&row.selectionPin.file!==value.selectionPin.file,'TARGET_ANCESTRY_INVALID');
   const known=targetGeneration(row.selectionSchemaVersion);need(!known.targetCommit||known.targetCommit===row.sourceCommit,'TARGET_ANCESTRY_COMMIT_CHANGED');seen.add(row.selectionPin.file);
  }
  need(ancestry[0].selectionSchemaVersion==='TaskMainProgramTargetControlSelection/v1'&&equal(ancestry.at(-1).selectionPin,value.selectionSchemaVersion===MIXED_SCHEMA?value.partialPredecessor?.baseSelectionPin:value.predecessorSelectionPin),'TARGET_ANCESTRY_PREDECESSOR_CHANGED');
  if(value.selectionSchemaVersion===MIXED_SCHEMA){const p=value.partialPredecessor;need(p&&equal(Object.keys(p).sort(),['activationVerifiedHosts','baseSelectionPin','retainedBaseHosts','selectionPin'])&&localPinShape(p.selectionPin)&&localPinShape(p.baseSelectionPin)&&equal(p.selectionPin,value.predecessorSelectionPin)&&equal(p.activationVerifiedHosts,['57'])&&equal(p.retainedBaseHosts,['58','59']),'PARTIAL_PREDECESSOR_BINDING_REQUIRED');}
  profile={...profile,targetCommit:value.verifiedTargetCommit,submissionFile:'main-i2-to-test58-ui-submission-'+value.selectionPin.sha256+'.json'};
 }
 need(controllers&&equal(Object.keys(controllers).sort(),['57','58','59']),'THREE_TARGET_HOSTS_REQUIRED');
 for(const host of ['57','58','59']){
  const rr=controllers[host];need(Array.isArray(rr),'THREE_TARGET_ROLES_REQUIRED');const targets=rr.filter(r=>r.role==='target');
  need(targets.length===1&&targets[0].host==='172.30.30.'+host&&targets[0].sourceCommit===profile.targetCommit,'TARGET_GENERATION_CHANGED');
  if(isRepeated(value.selectionSchemaVersion))need(equal(value.controllerBuildBindings?.[host]?.target,
   {buildPin:value.verifiedTargetBuildPin,sourceCommit:profile.targetCommit}),'TARGET_BUILD_BINDING_CHANGED');
 }
 return profile;
}
function assertRepeatedSubmissions({installation,pointEvidencePin,previousSubmissions}){
 need(isRepeated(installation.selectionSchemaVersion)&&Array.isArray(previousSubmissions)&&previousSubmissions.length>=2,'RETAINED_SUBMISSIONS_REQUIRED');
 const ancestry=installation.targetSelectionAncestry,seen=new Set(),pins=[],ids=[];let index=-1;
 for(const row of previousSubmissions){
  need(row&&equal(Object.keys(row).sort(),['pin','value'])&&filePinShape(row.pin),'RETAINED_SUBMISSION_PIN');
  const v=row.value,position=ancestry.findIndex(a=>equal(a.selectionPin,v?.selectionPin));
  need(position>index&&!seen.has(v?.request?.operationId)&&equal(v?.pointEvidencePin,pointEvidencePin)&&
   restoreWriteAllowed('submit',v?.request,POINTS[2],false,0)&&typeof v.submittedAt==='string'&&Number.isFinite(Date.parse(v.submittedAt)),'RETAINED_SUBMISSION_BINDING');
  const base=['schemaVersion','submittedAt','selectionPin','pointEvidencePin','request'];
  if(pins.length===0)need(equal(Object.keys(v).sort(),base.sort())&&v.schemaVersion==='MainI2TestRestoreSubmission/v1'&&v.request.operationId===ORIGINAL_FAILURE&&position===0,'ORIGINAL_FAILED_SUBMISSION_REQUIRED');
  else if(pins.length===1)need(equal(Object.keys(v).sort(),[...base,'previousSubmissionPin','previousOperationId'].sort())&&
   v.schemaVersion==='MainI2TestRestoreSuccessorSubmission/v1'&&v.request.operationId===READER_FAILURE&&equal(v.previousSubmissionPin,pins[0])&&v.previousOperationId===ids[0]&&
   ancestry[position].selectionSchemaVersion==='TaskMainProgramTargetControlSuccessorSelection/v1','READER_FAILED_SUBMISSION_REQUIRED');
  else need(equal(Object.keys(v).sort(),[...base,'previousSubmissionPins','previousOperationIds'].sort())&&v.schemaVersion==='MainI2TestRestoreRepeatedSubmission/v1'&&
   equal(v.previousSubmissionPins,pins)&&equal(v.previousOperationIds,ids)&&isRepeated(ancestry[position].selectionSchemaVersion),'REPEATED_SUBMISSION_CHAIN_CHANGED');
  index=position;seen.add(v.request.operationId);pins.push(row.pin);ids.push(v.request.operationId);
 }
 return {pins,ids};
}
function filePinShape(value){return value&&equal(Object.keys(value).sort(),['bytes','path','sha256'])&&typeof value.path==='string'&&
 path.isAbsolute(value.path)&&Number.isSafeInteger(value.bytes)&&value.bytes>0&&/^[0-9a-f]{64}$/.test(value.sha256);}
function assertPreviousSubmission({installation,pointEvidencePin,previousSubmission,previousSubmissionPin}){
 need(assertInstallationGeneration(installation).submissionFile==='main-i2-to-test58-ui-submission-b9caa00.json'&&
  previousSubmission&&equal(Object.keys(previousSubmission).sort(),['pointEvidencePin','request','schemaVersion','selectionPin','submittedAt'])&&
  previousSubmission.schemaVersion==='MainI2TestRestoreSubmission/v1'&&previousSubmission.request?.operationId===ORIGINAL_FAILURE&&
  restoreWriteAllowed('submit',previousSubmission.request,POINTS[2],false,0)&&equal(previousSubmission.selectionPin,installation.predecessorSelectionPin)&&
  equal(previousSubmission.pointEvidencePin,pointEvidencePin)&&filePinShape(previousSubmissionPin),'ORIGINAL_FAILED_SUBMISSION_REQUIRED');
 return ORIGINAL_FAILURE;
}
function buildSubmissionReceipt({installation,request,pointEvidencePin,submittedAt,previousSubmission=null,previousSubmissionPin=null,previousSubmissions=null}){
 const profile=assertInstallationGeneration(installation),successor=profile.submissionFile==='main-i2-to-test58-ui-submission-b9caa00.json';
 need(restoreWriteAllowed('submit',request,POINTS[2],false,0,successor?ORIGINAL_FAILURE:null)&&filePinShape(pointEvidencePin)&&
  typeof submittedAt==='string'&&Number.isFinite(Date.parse(submittedAt)),'SUBMISSION_INPUT_INVALID');
 const value={schemaVersion:'MainI2TestRestoreSubmission/v1',submittedAt,selectionPin:installation.selectionPin,pointEvidencePin,request};
 if(isRepeated(installation.selectionSchemaVersion)){
  need(previousSubmission===null&&previousSubmissionPin===null,'UNEXPECTED_PREDECESSOR_SUBMISSION');
  const {pins,ids}=assertRepeatedSubmissions({installation,pointEvidencePin,previousSubmissions});
  need(!ids.includes(request.operationId),'RETAINED_OPERATION_ID_REUSED');
  Object.assign(value,{schemaVersion:'MainI2TestRestoreRepeatedSubmission/v1',previousSubmissionPins:pins,previousOperationIds:ids});
 }else if(successor){
  assertPreviousSubmission({installation,pointEvidencePin,previousSubmission,previousSubmissionPin});
  Object.assign(value,{schemaVersion:'MainI2TestRestoreSuccessorSubmission/v1',previousSubmissionPin,previousOperationId:ORIGINAL_FAILURE});
 }else need(previousSubmission===null&&previousSubmissionPin===null,'UNEXPECTED_PREDECESSOR_SUBMISSION');
 return structuredClone(value);
}
function pin(file){const raw=fs.readFileSync(file);return {path:path.resolve(file),bytes:raw.length,sha256:sha(raw)};}
function exclusive(file,value){const fd=fs.openSync(file,'wx');try{fs.writeFileSync(fd,JSON.stringify(value,null,2),'utf8');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
function args(argv){
 const out={};need(argv.length%2===0,'ARGUMENT_PAIR_REQUIRED');
 for(let i=0;i<argv.length;i+=2){const k=argv[i].replace(/^--/,'');need(['phase','selection','custody','observation','preview'].includes(k)&&!Object.hasOwn(out,k),'INVALID_ARGUMENT');out[k]=argv[i+1];}
 need(['preview','submit','verify'].includes(out.phase)&&/^[a-z][a-z0-9-]{0,55}$/.test(out.observation||''),'PHASE_AND_OBSERVATION_REQUIRED');
 need(/^[A-Za-z0-9][A-Za-z0-9_.-]*\.json$/.test(out.selection||'')&&out.custody&&path.isAbsolute(out.custody),'SELECTION_AND_CUSTODY_REQUIRED');
 if(out.phase==='submit')need(/^[A-Za-z0-9][A-Za-z0-9_.-]*\.json$/.test(out.preview||''),'SUCCESSFUL_PREVIEW_REQUIRED');
 return out;
}
const INSTALLATION_LOADER=String.raw`
import hashlib,importlib,json,pathlib,sys
task=pathlib.Path(sys.argv[1]);private=pathlib.Path(sys.argv[2]);sys.path.insert(0,str(task))
from main_program_installation_selection import Records
records=Records(task);selected=records.read(sys.argv[3]);profiles=${JSON.stringify(GENERATIONS)}
assert selected.get('schemaVersion') in profiles,'UNKNOWN_TARGET_SELECTION_SCHEMA'
from main_program_current_installation import load_current_target_installation as load
custody=json.loads(sys.argv[4])
v=load(task,private,selection_file=sys.argv[3],historical_source_custody_pin=custody)
assert v['status']=='ACTIVATED' and v['installationVerified'] is True and v['runtimeVerified'] is False
assert v['selectionPin']==records.references[sys.argv[3]],'SELECTION_CHANGED_DURING_DISPATCH'
rows=v['effectiveControllersByHost']
out=dict(schemaVersion='MainThreeTargetInstallationSummary/v1',status='PASS',selectionPin=v['selectionPin'],inputPins=v['inputPins'],
 selectionSchemaVersion=selected['schemaVersion'],predecessorSelectionPin=selected.get('predecessorSelectionPin'),
 effectiveControllersByHost=rows,controllerBuildBindings=v['controllerBuildBindings'],
 controllers={h:[{k:r[k] for k in ('host','role','sourceCommit','controlConfigurationPin','ownerConfigurationPin') if k in r} for r in rr] for h,rr in rows.items()})
if selected['schemaVersion'] in ('TaskMainProgramTargetControlSuccessorSelection/v2','TaskMainProgramTargetControlSuccessorSelection/v3'):
 binding=v['controllerBuildBindings']['58']['target'];ancestry=[];prior=v['predecessorInstallation'];seen=set()
 while True:
  reference=prior['selectionPin'];assert reference['file'] not in seen,'TARGET_ANCESTRY_CYCLE';seen.add(reference['file'])
  assert len(ancestry)<18,'TARGET_ANCESTRY_DEPTH'
  if prior['selection']['schemaVersion']=='TaskMainProgramTargetControlPartialPredecessor/v1':
   assert selected['schemaVersion']=='TaskMainProgramTargetControlSuccessorSelection/v3' and prior['status']=='PARTIALLY_ACTIVATED' and prior['installationVerified'] is False
   out['partialPredecessor']=dict(selectionPin=reference,baseSelectionPin=prior['selection']['baseSelectionPin'],activationVerifiedHosts=prior['activationVerifiedHosts'],retainedBaseHosts=prior['retainedBaseHosts'])
   prior=prior['predecessorInstallation'];continue
  ancestry.append(dict(selectionPin=reference,selectionSchemaVersion=prior['selection']['schemaVersion'],sourceCommit=prior['controllerBuildBindings']['58']['target']['sourceCommit']))
  if prior['selection']['schemaVersion']=='TaskMainProgramTargetControlSelection/v1':break
  prior=prior['predecessorInstallation']
 out.update(verifiedTargetCommit=binding['sourceCommit'],verifiedTargetBuildPin=binding['buildPin'],targetSelectionAncestry=list(reversed(ancestry)))
print(json.dumps(out,ensure_ascii=False,separators=(',',':')))
`;
function installation(options){
 const custody=path.resolve(options.custody),relative=path.relative(PRIVATE,custody),info=fs.lstatSync(custody);
 need(relative&&!relative.startsWith('..')&&!path.isAbsolute(relative)&&info.isFile()&&!info.isSymbolicLink(),'CUSTODY_PRIVATE_FILE_REQUIRED');
 const result=require('node:child_process').spawnSync('C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
  ['-B','-X','utf8','-c',INSTALLATION_LOADER,TASK,PRIVATE,options.selection,JSON.stringify(pin(custody))],
  {shell:false,encoding:'utf8',windowsHide:true,timeout:240000,maxBuffer:16*1024*1024});
 if(result.status!==0||result.error||result.stderr!==''){const e=Error('CURRENT_TARGET_INSTALLATION_FAILED');e.privateDetail={status:result.status,stdout:result.stdout,stderr:result.stderr,error:String(result.error||'')};throw e;}
 const value=JSON.parse(result.stdout);assertInstallationGeneration(value);
 return value;
}
async function main(){
 const options=args(process.argv.slice(2)),label='main-three-target-'+options.phase+'-'+options.observation;
 const dir=path.join(PRIVATE,label),output=path.join(TASK,label+'.json');need(!fs.existsSync(dir)&&!fs.existsSync(output),'UNIQUE_OBSERVATION_REQUIRED');
 fs.mkdirSync(dir);const helperPin=pin(__filename);const report={schemaVersion:'MainThreeTargetRealUi/v1',status:'RUNNING',phase:options.phase,startedAt:new Date().toISOString(),helperPin,loginPosts:0,businessPosts:0,pageErrors:0,blocked:[],matrix:[]};
 const save=(name,value)=>exclusive(path.join(dir,name),value);let browser,page,frame,current;const pending=[],responseErrors=[];
 let receipt,previousSubmission=null,previousSubmissionPin=null,previousSubmissions=null;
 const checkPreviousPins=()=>{
  const pins=previousSubmissions?previousSubmissions.map(row=>row.pin):(previousSubmissionPin?[previousSubmissionPin]:[]);
  for(const reference of pins)need(equal(pin(reference.path),reference),'ORIGINAL_SUBMISSION_CHANGED');
 };
 const phase=value=>{report.stage=value;console.log(JSON.stringify({stage:value,observedAt:new Date().toISOString()}));};
 try{
  phase('formal-current-installation');current=installation(options);save('installation.private.json',current);report.selectionPin=current.selectionPin;
  const generation=assertInstallationGeneration(current);receipt=path.join(TASK,generation.submissionFile);report.submissionFile=generation.submissionFile;
  const pointFile=path.join(TASK,'main-activated-i2-success-r1.json'),proof=JSON.parse(fs.readFileSync(pointFile,'utf8'));
  assertPointChain(proof);report.pointEvidencePin=pin(pointFile);
  if(generation.submissionFile==='main-i2-to-test58-ui-submission-b9caa00.json'){
   const previousFile=path.join(TASK,'main-i2-to-test58-ui-submission.json');previousSubmissionPin=pin(previousFile);
   previousSubmission=JSON.parse(fs.readFileSync(previousFile,'utf8'));report.previousSubmissionPin=previousSubmissionPin;
   // Validate retained provenance before any browser or route is created.
   assertPreviousSubmission({installation:current,pointEvidencePin:report.pointEvidencePin,previousSubmission,previousSubmissionPin});
   need(equal(pin(previousFile),previousSubmissionPin),'ORIGINAL_SUBMISSION_CHANGED');
  }
  if(isRepeated(current.selectionSchemaVersion)){
   previousSubmissions=[];
   for(const ancestor of current.targetSelectionAncestry){
    const known=targetGeneration(ancestor.selectionSchemaVersion);
    const filename=known.submissionFile||'main-i2-to-test58-ui-submission-'+ancestor.selectionPin.sha256+'.json';
    const file=path.join(TASK,filename);
    if(isRepeated(ancestor.selectionSchemaVersion)&&!fs.existsSync(file))continue;
    previousSubmissions.push({pin:pin(file),value:JSON.parse(fs.readFileSync(file,'utf8'))});
   }
   assertRepeatedSubmissions({installation:current,pointEvidencePin:report.pointEvidencePin,previousSubmissions});checkPreviousPins();
   report.previousSubmissionPins=previousSubmissions.map(row=>row.pin);
  }
  if(options.phase==='submit'){
   need(!fs.existsSync(receipt),'ALREADY_SUBMITTED_FOLLOW_ORIGINAL_OPERATION');
   const prior=JSON.parse(fs.readFileSync(path.join(TASK,options.preview),'utf8'));
   need(prior.schemaVersion===report.schemaVersion&&prior.status==='PASS'&&prior.phase==='preview'&&prior.confirmedPairs===9&&
    equal(prior.selectionPin,current.selectionPin)&&equal(prior.pointEvidencePin,report.pointEvidencePin)&&prior.businessPosts===0,'CURRENT_SUCCESSFUL_PREVIEW_REQUIRED');
   report.previewPin=pin(path.join(TASK,options.preview));
  }
  const original=options.phase==='verify'?JSON.parse(fs.readFileSync(receipt,'utf8')):null;
  if(original)need(equal(original,buildSubmissionReceipt({installation:current,request:original.request,pointEvidencePin:report.pointEvidencePin,
   submittedAt:original.submittedAt,previousSubmission,previousSubmissionPin,previousSubmissions})),'ORIGINAL_RESTORE_REQUEST_REQUIRED');
  const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
  phase('real-login');browser=await chromium.launch({channel:'chrome',headless:true});const context=await browser.newContext({viewport:{width:1440,height:1080}});page=await context.newPage();page.setDefaultTimeout(45000);
  page.on('pageerror',e=>{report.pageErrors++;save('page-error-'+report.pageErrors+'.private.json',{error:String(e)});});
  await page.route('**/*',async route=>{
   const req=route.request(),url=new URL(req.url()),method=req.method();
   if(url.origin===ORIGIN&&['GET','HEAD','OPTIONS'].includes(method))return route.continue();
   if(url.origin===ORIGIN&&method==='POST'&&url.pathname==='/api/account/login/'&&!url.search&&report.loginPosts===0){report.loginPosts++;return route.continue();}
   if(url.origin===ORIGIN&&method==='POST'&&url.pathname==='/backup-entry-api/operations'&&!url.search){
    const request=req.postDataJSON();
    if(restoreWriteAllowed(options.phase,request,POINTS[2],fs.existsSync(receipt),report.businessPosts,previousSubmission?.request.operationId||null)){
     checkPreviousPins();
     exclusive(receipt,buildSubmissionReceipt({installation:current,request,pointEvidencePin:report.pointEvidencePin,
      submittedAt:new Date().toISOString(),previousSubmission,previousSubmissionPin,previousSubmissions}));report.businessPosts++;report.request=request;return route.continue();
    }
   }
   report.blocked.push({method,path:url.pathname});return route.abort('blockedbyclient');
  });
  let catalogue;page.on('response',response=>{
   const url=new URL(response.url());
   if(url.origin===ORIGIN&&url.pathname==='/release-center/api/applications/intruoyi/package-catalog')pending.push((async()=>{
    const data=await response.json();need(response.status()===200&&data.schemaVersion==='PackageCatalog/v1'&&Array.isArray(data.items),'CATALOGUE_INVALID');catalogue=data;
   })().catch(e=>responseErrors.push(String(e))));
  });
  const shell=await page.goto(ORIGIN+'/',{waitUntil:'domcontentloaded',timeout:60000});need(shell.status()===200,'LOGIN_DOCUMENT_REQUIRED');
  const credentials=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
  await page.getByPlaceholder('请输入账户').fill(credentials.username);await page.getByPlaceholder('请输入密码').fill(credentials.password);
  const authPromise=page.waitForResponse(r=>new URL(r.url()).origin===ORIGIN&&new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST',{timeout:45000});
  await page.getByRole('button',{name:'登 录',exact:true}).click();const auth=await authPromise,body=await auth.json();save('login-response.private.json',{httpStatus:auth.status(),body});
  need(auth.status()===200&&!body.error&&body.data&&typeof body.data.access_token==='string'&&body.data.access_token&&!body.data.required_mfa&&typeof body.data.has_real_ip==='boolean','REAL_LOGIN_FAILED');
  if(!body.data.has_real_ip){const notice=page.getByRole('button',{name:'知道了',exact:true});await notice.waitFor({state:'visible'});await notice.click();await notice.waitFor({state:'hidden'});}
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));await page.getByText('管理员',{exact:true}).first().waitFor({state:'visible'});report.realLogin=true;
  phase('backup-centre');await page.getByText('备份与恢复',{exact:true}).first().click();await page.waitForURL(ORIGIN+'/backup-center');
  frame=await (await page.locator('iframe[src="/backup-restore/?embedded=1"]').elementHandle()).contentFrame();need(frame,'BACKUP_FRAME_REQUIRED');
  await frame.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:120000});
  const idle=()=>frame.waitForFunction(()=>!simpleInitializing&&!switching&&!busy,null,{timeout:120000});
  if(options.phase==='verify'){
   phase('original-restore-progress');const id=original.request.operationId;report.operationId=id;
   let observation;page.on('response',r=>{const u=new URL(r.url());if(u.origin===ORIGIN&&u.pathname==='/backup-entry-api/operations/'+id)pending.push((async()=>{observation={httpStatus:r.status(),body:await r.json()};})().catch(e=>responseErrors.push(String(e))));});
   await frame.locator('#simple-history-tab').click();const row=frame.locator('#simple-history .history-row').filter({hasText:id});
   await row.waitFor();need(await row.count()===1,'ORIGINAL_HISTORY_ROW_REQUIRED');await row.getByRole('button',{name:'查看进度',exact:true}).click();
   await frame.locator('#simple-progress-tab').click();await frame.waitForFunction(id=>document.querySelector('#operation-reference')?.textContent===id&&!document.querySelector('#simple-query').disabled,id);
   const queried=page.waitForResponse(r=>new URL(r.url()).origin===ORIGIN&&new URL(r.url()).pathname==='/backup-entry-api/operations/'+id,{timeout:90000});await frame.locator('#simple-query').click();await queried;
   await frame.waitForTimeout(3000);await Promise.all(pending);if(observation)save('operation-response.private.json',observation);
   need(observation&&observation.httpStatus===200&&equal(observation.body.request,original.request),'ORIGINAL_OPERATION_RESPONSE_REQUIRED');
   report.operationResponse=observation.body;report.state=observation.body.result?.state;
   report.visibleProblem=await frame.locator('#problem').textContent();report.visibleLogs=await frame.locator('#simple-logs').innerText();
   need(!observation.body.queryError&&!report.visibleProblem&&!report.visibleLogs.includes('ENTRY_REQUEST_TIMEOUT')&&['RUNNING','SUCCEEDED'].includes(report.state),'ORIGINAL_RESTORE_STATE_NOT_READY');report.status='PASS';
  }else{
   phase('complete-catalogue');await frame.locator('#simple-catalog-tab').click();await frame.locator('#catalog-refresh').waitFor({state:'visible'});
   await frame.waitForFunction(()=>!document.querySelector('#catalog-refresh').disabled,null,{timeout:120000});catalogue=null;await frame.locator('#catalog-refresh').click();
   const deadline=Date.now()+180000;while(Date.now()<deadline){await Promise.all(pending.splice(0));if(catalogue&&catalogue.refreshing===false)break;await page.waitForTimeout(500);}
   need(catalogue&&catalogue.complete===true&&catalogue.refreshing===false&&!(catalogue.errors||[]).length,'COMPLETE_FRESH_CATALOGUE_REQUIRED');save('catalogue.private.json',catalogue);
   report.catalogueCount=catalogue.items.length;
   async function filter(kind='',query=''){
    await frame.locator('#catalog-filter-open').click();await frame.locator('#catalog-filter-dialog').waitFor({state:'visible'});
    await frame.locator('#catalog-reset').click();await frame.locator('#catalog-kind').selectOption(kind);await frame.locator('#catalog-query').fill(query);await frame.locator('#catalog-filter-apply').click();await frame.locator('#catalog-filter-dialog').waitFor({state:'hidden'});
   }
   async function pages(){const ids=[];for(let n=0;n<1000;n++){ids.push(...await frame.locator('#catalog-body tr[data-package-id]').evaluateAll(rr=>rr.map(r=>r.dataset.packageId)));if(await frame.locator('#catalog-next').isDisabled())return ids;await frame.locator('#catalog-next').click();}throw Error('CATALOGUE_PAGE_LIMIT');}
   await filter();need(equal((await pages()).sort(),catalogue.items.map(r=>r.packageId).sort()),'VISIBLE_CATALOGUE_COVERAGE_REQUIRED');
   for(const kind of ['backup-full','backup-incremental']){await filter(kind);const ids=await pages();need(equal(ids.sort(),catalogue.items.filter(r=>r.kind===kind).map(r=>r.packageId).sort()),'VISIBLE_FILTER_COVERAGE_REQUIRED');}
   const points=options.phase==='preview'?POINTS:[POINTS[2]];
   for(const point of points){
    const row=catalogue.items.filter(r=>r.packageId===point);need(row.length===1&&row[0].status==='indexed'&&row[0].kind===(point===POINTS[0]?'backup-full':'backup-incremental'),'SUCCESSFUL_POINT_NOT_INDEXED');
    phase('point-'+point);await filter('',point);const actual=frame.locator('#catalog-body tr[data-package-id="'+point+'"]');need(await actual.count()===1,'EXACT_POINT_ROW_REQUIRED');
    await actual.getByRole('button',{name:'恢复',exact:true}).click();await frame.locator('#catalog-restore-dialog').waitFor({state:'visible'});await idle();
    need(await frame.locator('#simple-package').inputValue()===point&&await frame.locator('#simple-server').inputValue()==='172.30.30.57'&&await frame.locator('#application').inputValue()===SOURCE,'POINT_SOURCE_IDENTITY_CHANGED');
    need(await frame.locator('#simple-restore-mode').inputValue()==='replace','OVERWRITE_MODE_REQUIRED');
    for(const host of options.phase==='preview'?['57','58','59']:['58']){
     const ip='172.30.30.'+host,target='intruoyi-main-'+host+'-safe-restore-'+(host==='57'?'20261105-v2':'20261104-v1');
     const option=frame.locator('#simple-target option[value="'+ip+'"]');need(await option.count()===1&&!await option.isDisabled(),'REGISTERED_TARGET_NOT_SELECTABLE');
     await frame.locator('#simple-target').selectOption(ip);await idle();need(await frame.locator('#simple-submit').isEnabled(),'TARGET_NOT_READY');
     await frame.locator('#simple-submit').click();await frame.locator('#simple-confirm').waitFor({state:'visible'});
     const summary=await frame.locator('#confirm-summary').innerText();need(summary.includes('备份包：'+point)&&summary.includes(ip)&&summary.includes('独立目标：'+target),'CONFIRMATION_IDENTITY_CHANGED');
     need(!await frame.locator('#replace-confirm').isChecked()&&await frame.locator('#simple-confirm-submit').isDisabled(),'OVERWRITE_ACK_NOT_REQUIRED');
     report.matrix.push({point,host:ip,targetConfigRef:target,confirmedIdentity:true});save('confirm-'+point+'-'+host+'.private.json',{summary});
     if(options.phase==='submit'){
      phase('single-test58-submit');need(equal(installation(options),current),'INSTALLATION_CHANGED_BEFORE_SUBMIT');
      await frame.locator('#replace-confirm').check();const accepted=page.waitForResponse(r=>new URL(r.url()).origin===ORIGIN&&new URL(r.url()).pathname==='/backup-entry-api/operations'&&r.request().method()==='POST',{timeout:90000});
      await frame.locator('#simple-confirm-submit').click();const response=await accepted,value=await response.json();save('entry-response.private.json',{httpStatus:response.status(),body:value});report.entryResponse=value;report.httpStatus=response.status();
      need(response.ok()&&report.businessPosts===1,'RESTORE_SUBMISSION_FAILED');
     }else{await frame.locator('#simple-cancel').click();await frame.locator('#simple-confirm').waitFor({state:'hidden'});}
    }
    if(options.phase==='preview'){await frame.locator('#catalog-restore-close').click();await frame.locator('#catalog-restore-dialog').waitFor({state:'hidden'});}
   }
   report.confirmedPairs=report.matrix.length;need(report.confirmedPairs===(options.phase==='preview'?9:1),'POINT_TARGET_MATRIX_INCOMPLETE');report.status='PASS';
  }
  await Promise.all(pending.splice(0));need(report.loginPosts===1&&report.pageErrors===0&&report.blocked.length===0&&responseErrors.length===0&&report.businessPosts===(options.phase==='submit'?1:0),'REAL_UI_WRITES_OR_ERRORS');
  need(equal(installation(options),current),'INSTALLATION_CHANGED_DURING_UI');
  need(equal(pin(path.join(TASK,'main-activated-i2-success-r1.json')),report.pointEvidencePin)&&equal(pin(__filename),helperPin),'UI_OR_POINT_INPUT_CHANGED');
  checkPreviousPins();
 }catch(error){report.status='FAIL';report.errorCode=/^[A-Z0-9_]+$/.test(error.message)?error.message:'REAL_UI_OBSERVATION_FAILED';save('failure.private.json',{error:String(error.stack||error),detail:error.privateDetail});process.exitCode=1;}
 finally{
  if(page){await page.screenshot({path:path.join(dir,'actual-page.png'),fullPage:true}).catch(e=>{report.status='FAIL';report.screenshotError=String(e);process.exitCode=1;});}
  report.finishedAt=new Date().toISOString();exclusive(output,report);console.log(JSON.stringify({status:report.status,stage:report.stage,errorCode:report.errorCode,loginPosts:report.loginPosts,businessPosts:report.businessPosts,confirmedPairs:report.confirmedPairs}));if(browser)await browser.close();
 }
}
module.exports={restoreWriteAllowed,assertPointChain,jsonEqual:equal,targetGeneration,assertInstallationGeneration,buildSubmissionReceipt,
 assertPreviousSubmission,installationLoaderProgram:INSTALLATION_LOADER};
if(require.main===module)main().catch(error=>{console.error(JSON.stringify({status:'NOT_STARTED',errorCode:error.message}));process.exitCode=1;});
