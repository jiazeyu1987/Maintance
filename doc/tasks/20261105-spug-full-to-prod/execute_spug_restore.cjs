// Submit the exact approved restore once using genuine Spug controls.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const task=__dirname,priv='C:/Spug/runtime/private/full-to-prod-20261105';
const source='intruoyi-57-safe-20261024-v1',point='smallapp-73cd541a95d84d6a86f9d693e4053c75',target='intruoyi-main-57-safe-restore-20261105-v2';
const receipt=path.join(task,'restore-ui-submission.json');
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2),'utf8');
(async()=>{
 if(fs.existsSync(receipt))throw Error('ALREADY_SUBMITTED_FOLLOW_ORIGINAL_OPERATION');
 const clearance=JSON.parse(fs.readFileSync(path.join(task,'health-recovery-clearance.json'),'utf8'));
 const archived=JSON.parse(fs.readFileSync(path.join(task,'health-failed-attempt-archive.json'),'utf8'));
 if(clearance.status!=='PASS'||!clearance.originalProtectionsPreciselyReleased||!clearance.writersRemainStopped||clearance.restoreDispatched||clearance.recoveryPointRef!==point||clearance.targetConfigRef!==target||archived.status!=='PASS'||archived.operationId!==clearance.operationId||archived.localOriginalPinsUnchanged!==8)throw Error('FORMAL_CONTINUATION_AND_ORIGINAL_PRESERVATION_REQUIRED');
 const crypto=require('node:crypto');
 if(clearance.originalFailurePinsUnchanged!==908||!clearance.schedulerRemainsPaused||clearance.operationId!=='smallapp-d7a963eb1e9a4c16826c92d5753b30c3')throw Error('CURRENT_FAILURE_CUSTODY_REQUIRED');
 const firstArchive=JSON.parse(fs.readFileSync(path.join(task,'failed-attempt-archive.json'),'utf8'));
 if(firstArchive.status!=='PASS'||firstArchive.operationId!=='smallapp-181aec2e16c94e259f875c0e64eb863a'||firstArchive.localOriginalPinsUnchanged!==8)throw Error('FIRST_FAILURE_PRESERVATION_REQUIRED');
 for(const item of [...archived.localFiles,archived.privateFile,...firstArchive.localFiles,firstArchive.privateFile]){const raw=fs.readFileSync(item.preservedPath);if(raw.length!==item.original.bytes||crypto.createHash('sha256').update(raw).digest('hex')!==item.original.sha256)throw Error('ORIGINAL_LOCAL_FAILURE_CHANGED');}
 const preserved=JSON.parse(fs.readFileSync(path.join(task,'preservation-full-point-verified.json'),'utf8'));
 const readback=JSON.parse(fs.readFileSync(path.join(task,'preservation-full-payload-readback.json'),'utf8'));
 const admission=JSON.parse(fs.readFileSync(path.join(task,'preservation-full-admission.json'),'utf8'));
 const samePin=(a,b)=>a&&b&&['path','bytes','sha256'].every(k=>a[k]===b[k]);
 if(preserved.state!=='SUCCEEDED'||readback.status!=='PASS'||!readback.payloadContentVerified||!readback.exactTreeVerifiedBeforeAndAfter||!readback.metadataPinsVerifiedBeforeAndAfter||readback.operationId!==preserved.operationId||admission.newRecoveryPointRef!==preserved.operationId||!admission.newPointAdmitted||!samePin(readback.manifestPin,preserved.manifestPin)||!samePin(readback.pointPin,preserved.pointPin))throw Error('PRESERVATION_FULL_ACCEPTANCE_REQUIRED');
 const browser=await chromium.launch({channel:'chrome',headless:true,timeout:20000});
 const context=await browser.newContext({viewport:{width:1440,height:1080}});
 const page=await context.newPage();page.setDefaultTimeout(45000);
 let frame=null;
 const out={realBrowser:true,realLogin:false,startedAt:new Date().toISOString(),writes:0,blocked:[],httpFailures:[],pageErrors:[],stage:'login'};
 page.on('pageerror',e=>out.pageErrors.push(String(e)));
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
  await page.goto('http://127.0.0.1:18080/',{waitUntil:'domcontentloaded'});
  await page.getByPlaceholder('请输入账户').fill(admin.username);await page.getByPlaceholder('请输入密码').fill(admin.password);
  const logged=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登 录'}).click();const auth=await (await logged).json();
  if(auth.error)throw Error('SPUG_LOGIN_REJECTED');
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token'))||[...document.querySelectorAll('button')].some(b=>b.innerText==='知道了'));
  if(await page.getByRole('button',{name:'知道了'}).isVisible())await page.getByRole('button',{name:'知道了'}).click();
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));out.realLogin=true;
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
  await frame.locator('#simple-target').selectOption('172.30.30.57');
  await frame.waitForFunction(()=>!document.querySelector('#simple-submit').disabled);
  out.stage='confirmation';
  await frame.locator('#simple-submit').click();await frame.locator('#simple-confirm').waitFor({state:'visible'});
  out.confirmation=await frame.locator('#confirm-summary').innerText();
  for(const expected of [source,point,target,'172.30.30.57','安全模式'])if(!out.confirmation.includes(expected))throw Error('CONFIRMATION_MISMATCH');
  if(!await frame.locator('#simple-confirm-submit').isDisabled())throw Error('OVERWRITE_ACK_NOT_REQUIRED');
  await frame.locator('#replace-confirm').check();
  await page.screenshot({path:path.join(task,'restore-ui-confirm.png'),fullPage:true});
  await context.storageState({path:priv+'/spug-active-session.private.json'});
  const accepted=page.waitForResponse(r=>new URL(r.url()).pathname==='/backup-entry-api/operations'&&r.request().method()==='POST',{timeout:45000});
  await frame.locator('#simple-confirm-submit').click();
  const response=await accepted;const body=await response.json();write(priv+'/restore-entry-response.private.json',body);
  out.httpStatus=response.status();out.spugHistoryId=body.spugHistoryId;out.result=body.result;out.errorCode=body.errorCode;out.dispatchErrorCode=body.dispatchErrorCode;
  if(out.writes!==1||!response.ok())throw Error(body.errorCode||'RESTORE_SUBMISSION_FAILED');
  await context.storageState({path:priv+'/spug-active-session.private.json'});
  out.visible=await frame.locator('main').innerText();
  await page.screenshot({path:path.join(task,'restore-ui-submitted.png'),fullPage:true});
  if(out.blocked.length||out.pageErrors.length)throw Error('UI_ERRORS_OR_UNEXPECTED_WRITE');
  out.status='PASS';
 }catch(error){out.status='FAIL';out.error=String(error);out.visible=await page.locator('body').innerText().catch(()=>'(unavailable)');out.frameVisible=frame?await frame.locator('body').innerText().catch(()=>'(unavailable)'):null;await page.screenshot({path:path.join(task,'restore-ui-entry-failure.png'),fullPage:true});process.exitCode=1;}
 finally{out.finishedAt=new Date().toISOString();write(path.join(task,'restore-ui-result.json'),out);console.log(JSON.stringify({status:out.status,realLogin:out.realLogin,writes:out.writes,request:out.request,httpStatus:out.httpStatus,result:out.result,error:out.error,blocked:out.blocked}));await browser.close();}
})().catch(error=>{console.error(String(error));process.exitCode=1;});
