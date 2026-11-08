// Submit the exact approved restore once using genuine Spug controls.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const task=__dirname,priv='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106';
const suffix=process.argv[2];if(!['58','59'].includes(suffix))throw Error('TARGET_REQUIRED');
const load=name=>JSON.parse(fs.readFileSync(path.join(task,name),'utf8'));
const attempts=load('restore-selected-attempts.json'),kind=attempts.targets[suffix].kind;
if(attempts.schemaVersion!=='TaskRestoreAttempts/v1'||!new RegExp('^restore-'+suffix+'(?:-r(?:[2-9]|[1-9][0-9]+))?$').test(kind))throw Error('EXPLICIT_RESTORE_ATTEMPT_REQUIRED');
const acceptedPoint=load('new-incremental-point-verified.json');
const source='intruoyi-57-safe-20261024-v1',point=acceptedPoint.operationId,target='intruoyi-main-'+suffix+'-safe-restore-20261104-v1';
const receipt=path.join(task,kind+'-ui-submission.json');
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2),'utf8');
const attempt=process.argv[3]||'1';if(!/^[1-9][0-9]*$/.test(attempt))throw Error('INVALID_UI_ATTEMPT');
const traceFile=path.join(task,kind+'-ui-trace-'+attempt+'.json');
if(fs.existsSync(traceFile))throw Error('UI_TRACE_ALREADY_EXISTS');
const traceEvents=[];
const trace=(stage,details={})=>{const event={observedAt:new Date().toISOString(),stage,...details};traceEvents.push(event);write(traceFile,traceEvents);console.log(JSON.stringify(event));};
(async()=>{
 if(fs.existsSync(receipt))throw Error('ALREADY_SUBMITTED_FOLLOW_ORIGINAL_OPERATION');
 const readback=load('new-incremental-payload-readback.json'),admission=load('target-new-point-admission-'+kind+'.json');
 const preserved=load('source-after-backup-preservation.json'),rollback=load('target-rollback-point-admission-'+kind+'.json');
 const sourceState=load('source-global-state-restored.json');
 const installations=load('allocator-selected-installations.json'),baselines=load('restore-selected-source-baselines.json');
 if(installations.schemaVersion!=='TaskAllocatorInstallations/v1'||baselines.schemaVersion!=='TaskRestoreSourceBaselines/v1')throw Error('EXPLICIT_INSTALLATION_AND_BASELINE_REQUIRED');
 const contract=load(installations.contracts[suffix]),freshSource=load(baselines.targets[suffix]);
 const samePin=(a,b)=>a&&b&&['path','bytes','sha256'].every(k=>a[k]===b[k]);
 if(acceptedPoint.status!=='PASS'||acceptedPoint.state!=='SUCCEEDED'||acceptedPoint.actualExitCode!==0||acceptedPoint.pointType!=='INCREMENTAL'||acceptedPoint.parentBackupId!=='smallapp-7fec29a3e132463096aec915c08acab3')throw Error('NEW_INCREMENTAL_ACCEPTANCE_REQUIRED');
 if(readback.status!=='PASS'||readback.operationId!==point||!readback.payloadContentVerified||!readback.exactTreeVerifiedBeforeAndAfter||!readback.metadataPinsVerifiedBeforeAndAfter||!samePin(readback.pointPin,acceptedPoint.pointPin)||!samePin(readback.manifestPin,acceptedPoint.manifestPin))throw Error('COMPLETE_SAFE_READBACK_REQUIRED');
 if(admission.status!=='PASS'||admission.recoveryPointRef!==point||admission.targetConfigRef!==target||!samePin(admission.pointPin,acceptedPoint.pointPin)||admission.orderedChainPins.length!==2||Date.now()-Date.parse(admission.observedAt)>900000)throw Error('FRESH_TARGET_ADMISSION_REQUIRED');
 if(preserved.status!=='PASS'||preserved.backupOperationId!==point||rollback.status!=='PASS'||rollback.host!=='172.30.30.'+suffix)throw Error('SOURCE_PRESERVATION_AND_ROLLBACK_BASIS_REQUIRED');
 if(sourceState.status!=='PASS'||sourceState.backupOperationId!==point||!sourceState.originalGlobalStateRestored||!sourceState.strictBinlogToolStillVerified)throw Error('SOURCE_GLOBAL_STATE_RESTORATION_REQUIRED');
 if(!sourceState.registeredExporterTemporaryContractVerified||sourceState.failedOriginalFilesPreserved!==10044)throw Error('SOURCE_REGISTERED_EXPORTER_AND_ALL_FAILED_ORIGINALS_REQUIRED');
 if(contract.status!=='PASS'||!contract.incrementalDatabaseDdlScopeV3Supported||!contract.packageFilesMatch||admission.packageFileCount!==contract.fileCount)throw Error('TARGET_INCREMENTAL_PROTOCOL_CONTRACT_REQUIRED');
 if(!admission.nativeSqlMemoryHeadroom.verified||admission.nativeSqlMemoryHeadroom.rawIncrementalSqlBytes!==acceptedPoint.database.rawSqlBytes)throw Error('TARGET_NATIVE_SQL_MEMORY_HEADROOM_REQUIRED');
 if(!contract.frozenAllocatorRestoreSupported)throw Error('FROZEN_ALLOCATOR_RESTORE_REQUIRED');
 if(!contract.actualHealthContractVerified)throw Error('ACTUAL_MAIN_HEALTH_CONTRACT_REQUIRED');
 if(freshSource.http.backend.status!=='UP'||freshSource.http.backend.httpStatus!==200||freshSource.http.frontend.httpStatus!==200||freshSource.activeReservation||Date.now()-Date.parse(freshSource.observedAt)>900000)throw Error('FRESH_SOURCE_HEALTH_REQUIRED');
 if(suffix==='58'){
  const selected=load('restore-selected-clearances.json');
  if(selected.schemaVersion!=='TaskRestoreClearances/v1'||selected.targets['58']!=='packaged-frontend-retained-recovery-clearance-58.json')throw Error('EXPLICIT_CLEARANCE_REQUIRED');
  const clearance=load(selected.targets['58']),old=load('restore-58-r3-terminal-record.json'),failed=load('failed-370-all-files-preserved.json'),installed=load(installations.targets[suffix]);
  if(kind!=='restore-58-r4'||!installed.actualPackagedConstructorVerified||!installed.constructorEvidencePin||clearance.status!=='PASS'||!clearance.writersRemainStopped||!clearance.noMutationReleasePin||!clearance.inheritedQuiescencePin||clearance.originalFailureFilesUnchanged!==2916||clearance.recoveryPointRef!==point||clearance.targetConfigRef!==target||!admission.retainedQuiescedAdmission||!samePin(admission.retainedClearancePin,clearance.clearancePin)||old.result.state!=='FAILED'||old.result.errorCode!=='MAIN_FRONTEND_READINESS_INVALID'||failed.status!=='PASS'||failed.mutationDispatched!==false)throw Error('RETAINED_FAILURE_CLEARANCE_REQUIRED');
 }
 if(suffix==='59'&&(load('restore-58-native-evidence.json').status!=='PASS'||load('target-58-after-business.json').status!=='PASS'||load('restored-runtime-58.json').status!=='PASS'))throw Error('TEST_TARGET_ACCEPTANCE_REQUIRED_FIRST');
 trace('browser-launch');
 const browser=await chromium.launch({channel:'chrome',headless:true,timeout:20000});
 trace('browser-context');
 const context=await browser.newContext({viewport:{width:1440,height:1080}});
 trace('browser-page');
 const page=await context.newPage();page.setDefaultTimeout(45000);
 trace('page-created');
 let frame=null;
 const out={realBrowser:true,realLogin:false,startedAt:new Date().toISOString(),writes:0,blocked:[],httpFailures:[],pageErrors:[],stage:'login'};
 page.on('pageerror',e=>out.pageErrors.push(String(e)));
 page.on('request',r=>{const p=new URL(r.url()).pathname;if(p==='/api/account/login/'||p==='/backup-entry-api/operations')trace('request',{method:r.method(),path:p});});
 page.on('response',r=>{const p=new URL(r.url()).pathname;if(p==='/'||p==='/api/account/login/'||p==='/backup-entry-api/operations')trace('response',{path:p,httpStatus:r.status()});});
 page.on('response',r=>{if(r.status()>=400)out.httpFailures.push({status:r.status(),path:new URL(r.url()).pathname});});
 await page.route('**/*',async route=>{
  const req=route.request(),pathname=new URL(req.url()).pathname;
  if(['GET','HEAD','OPTIONS'].includes(req.method())||req.method()==='POST'&&pathname==='/api/account/login/')return route.continue();
  if(req.method()==='POST'&&pathname==='/backup-entry-api/operations'){
   const r=req.postDataJSON();
   if(!out.writes&&r.action==='RESTORE'&&r.sourceConfigRef===source&&r.recoveryPointRef===point&&r.targetConfigRef===target&&!fs.existsSync(receipt)){
    out.writes++;out.request=r;
    fs.writeFileSync(receipt,JSON.stringify({submittedAt:new Date().toISOString(),request:r},null,2),{encoding:'utf8',flag:'wx'});
    return route.continue();
   }
  }
  out.blocked.push({method:req.method(),path:pathname});await route.abort('blockedbyclient');
 });
 try{
  const admin=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
  trace('login-navigation');const navigation=await page.goto('http://127.0.0.1:18080/',{waitUntil:'commit'});
  if(navigation.status()!==200)throw Error('SPUG_LOGIN_DOCUMENT_HTTP_FAILED');
  await page.getByPlaceholder('请输入账户').waitFor({state:'visible'});
  await page.getByPlaceholder('请输入密码').waitFor({state:'visible'});trace('login-controls');
  await page.getByPlaceholder('请输入账户').fill(admin.username);await page.getByPlaceholder('请输入密码').fill(admin.password);
  const logged=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST');
  trace('login-click');await page.getByRole('button',{name:'登 录'}).click();const auth=await (await logged).json();trace('login-response-parsed',{rejected:!!auth.error});
  if(auth.error)throw Error('SPUG_LOGIN_REJECTED');
  const loginNotice=page.getByRole('button',{name:'知道了',exact:true});
  await loginNotice.waitFor({state:'visible'});await loginNotice.click();
  await loginNotice.waitFor({state:'hidden'});
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));out.realLogin=true;trace('login-complete');
  await page.getByText('备份与恢复',{exact:true}).first().waitFor();await page.getByText('备份与恢复',{exact:true}).first().click();
  await page.waitForURL('**/backup-center');
  frame=await (await page.locator('iframe[src="/backup-restore/?embedded=1"]').elementHandle()).contentFrame();
  if(!frame)throw Error('BACKUP_FRAME_MISSING');
  await frame.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:90000});
  out.stage='restore-tab';await frame.locator('#simple-restore-tab').click();
  await frame.waitForFunction(()=>!switching&&!document.querySelector('#simple-server').disabled,null,{timeout:120000});
  out.stage='source-server';
  await frame.locator('#simple-server').selectOption('172.30.30.57');
  await frame.waitForFunction(()=>!switching&&!document.querySelector('#simple-mode').disabled,null,{timeout:120000});
  out.stage='safe-mode';
  await frame.locator('#simple-mode').selectOption('safe');
  await frame.waitForFunction(({source,point})=>!switching&&selected()?.applicationId===source&&
   [...document.querySelector('#simple-package').options].some(o=>o.value===point),{source,point},{timeout:90000});
  await frame.locator('#simple-restore-mode').selectOption('replace');
  await frame.waitForFunction(()=>!switching&&!document.querySelector('#simple-package').disabled,null,{timeout:120000});
  await frame.locator('#simple-package').selectOption(point);
  out.selectedPackage=await frame.locator('#simple-package option:checked').innerText();
  out.entry='existing-restore-tab';
  out.stage='target';
  await frame.waitForFunction(()=>document.querySelector('#simple-target').options.length>=4&&!document.querySelector('#simple-target').disabled);
  await frame.locator('#simple-target').selectOption('172.30.30.'+suffix);
  await frame.waitForFunction(()=>!document.querySelector('#simple-submit').disabled);
  out.stage='confirmation';
  await frame.locator('#simple-submit').click();await frame.locator('#simple-confirm').waitFor({state:'visible'});
  out.confirmation=await frame.locator('#confirm-summary').innerText();
  for(const expected of [source,point,target,'172.30.30.'+suffix,'安全模式'])if(!out.confirmation.includes(expected))throw Error('CONFIRMATION_MISMATCH');
  if(!await frame.locator('#simple-confirm-submit').isDisabled())throw Error('OVERWRITE_ACK_NOT_REQUIRED');
  await frame.locator('#replace-confirm').check();
  await page.screenshot({path:path.join(task,kind+'-ui-confirm.png'),fullPage:true});
  await context.storageState({path:priv+'/spug-active-session.private.json'});
  const accepted=page.waitForResponse(r=>new URL(r.url()).pathname==='/backup-entry-api/operations'&&r.request().method()==='POST',{timeout:45000});
  await frame.locator('#simple-confirm-submit').click();
  const response=await accepted;const body=await response.json();write(priv+'/'+kind+'-entry-response.private.json',body);
  out.httpStatus=response.status();out.spugHistoryId=body.spugHistoryId;out.result=body.result;out.errorCode=body.errorCode;out.dispatchErrorCode=body.dispatchErrorCode;
  if(out.writes!==1||!response.ok())throw Error(body.errorCode||'RESTORE_SUBMISSION_FAILED');
  await context.storageState({path:priv+'/spug-active-session.private.json'});
  out.visible=await frame.locator('main').innerText();
  await page.screenshot({path:path.join(task,kind+'-ui-submitted.png'),fullPage:true});
  if(out.blocked.length||out.pageErrors.length)throw Error('UI_ERRORS_OR_UNEXPECTED_WRITE');
  out.status='PASS';
 }catch(error){out.status='FAIL';out.error=String(error);out.visible=await page.locator('body').innerText().catch(()=>'(unavailable)');out.frameVisible=frame?await frame.locator('body').innerText().catch(()=>'(unavailable)'):null;await page.screenshot({path:path.join(task,kind+'-ui-entry-failure-'+attempt+'.png'),fullPage:true});process.exitCode=1;}
 finally{out.finishedAt=new Date().toISOString();write(path.join(task,kind+'-ui-result.json'),out);console.log(JSON.stringify({status:out.status,realLogin:out.realLogin,writes:out.writes,request:out.request,httpStatus:out.httpStatus,result:out.result,error:out.error,blocked:out.blocked}));await browser.close();}
})().catch(error=>{console.error(String(error));process.exitCode=1;});
