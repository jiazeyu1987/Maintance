// Real login and visible Spug controls only. Never dispatch business API calls.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const mode=process.argv[2]||'inspect', task=__dirname;
const priv='C:/Spug/runtime/private/prod-full-to-test-20261104';
const source='intruoyi-57-safe-20261024-v1',target='intruoyi-main-58-safe-restore-20261104-v1';
const receipt=path.join(task,mode==='restore'?'restore-ui-submission.json':'full-ui-submission.json');
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2),'utf8');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,timeout:20000});
 const monitor=mode==='monitor-full'||mode==='monitor-restore';
 const context=await browser.newContext({viewport:{width:1440,height:1080},...(monitor?{storageState:priv+'/spug-active-session.private.json'}:{})});
 const page=await context.newPage();page.setDefaultTimeout(45000);
 const result={mode,realBrowser:true,realLogin:false,startedAt:new Date().toISOString()},failures=[];
 let writes=0;
 page.on('response',r=>{if(r.status()>=400)failures.push({status:r.status(),path:new URL(r.url()).pathname});});
 page.on('request',r=>{
  if(r.method()==='POST'&&new URL(r.url()).pathname==='/backup-entry-api/operations'){
   writes++;const request=r.postDataJSON();
   write(receipt,{submittedAt:new Date().toISOString(),request});
  }
 });
 try{
  if(!monitor){
   const credentials=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
   await page.goto('http://127.0.0.1:18080/',{waitUntil:'domcontentloaded'});
   await page.getByPlaceholder('请输入账户').fill(credentials.username);
   await page.getByPlaceholder('请输入密码').fill(credentials.password);
   const authPromise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST');
   await page.getByRole('button',{name:'登 录'}).click();
   const auth=await (await authPromise).json();if(auth.error)throw Error('LOGIN_REJECTED');
   await page.waitForFunction(()=>Boolean(localStorage.getItem('token'))||[...document.querySelectorAll('button')].some(b=>b.innerText==='知道了'));
   if(await page.getByRole('button',{name:'知道了'}).isVisible())await page.getByRole('button',{name:'知道了'}).click();
   await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));result.realLogin=true;
   await context.storageState({path:priv+'/spug-last-login.private.json'});
  }
  await page.goto('http://127.0.0.1:18080/backup-restore/',{waitUntil:'domcontentloaded'});
  await page.locator('#simple-refresh').waitFor();
  await page.waitForFunction(()=>document.querySelector('#simple-server').options.length>=3&&(document.querySelector('#simple-status').textContent!=='正在读取真实执行配置…'));
  if(monitor){
   await page.locator('#simple-progress-tab').click();
   await page.waitForFunction(()=>Boolean(document.querySelector('#operation-reference').textContent)&&!document.querySelector('#simple-query').disabled);
   result.operationId=await page.locator('#operation-reference').innerText();
   const expected=JSON.parse(fs.readFileSync(path.join(task,mode==='monitor-full'?'full-ui-submission.json':'restore-ui-submission.json'),'utf8')).request.operationId;
   if(result.operationId!==expected)throw Error('PENDING_OPERATION_ID_MISMATCH');
   await page.locator('#simple-query').click();
   await page.waitForFunction(()=>!document.querySelector('#simple-query').disabled);
  }else{
   await page.locator('#simple-product').selectOption('intruoyi');
   await page.waitForFunction(()=>!document.querySelector('#simple-server').disabled);
   await page.locator('#simple-server').selectOption('172.30.30.57');
   await page.waitForFunction(()=>!document.querySelector('#simple-mode').disabled);
   await page.locator('#simple-mode').selectOption('safe');
   await page.waitForFunction(()=>!document.querySelector('#simple-backup-tab').disabled);
   if(mode==='restore'){
    await page.locator('#simple-restore-tab').click();
    await page.waitForFunction(()=>!document.querySelector('#simple-restore-mode').disabled);
    await page.locator('#simple-restore-mode').selectOption('replace');
    const point=JSON.parse(fs.readFileSync(path.join(task,'full-ui-submission.json'),'utf8')).request.operationId;
    await page.waitForFunction(p=>[...document.querySelector('#simple-package').options].some(o=>o.value===p),point);
    await page.locator('#simple-package').selectOption(point);
    await page.locator('#simple-target').selectOption('172.30.30.58');
   }else{
    await page.locator('#simple-backup-tab').click();
    await page.waitForFunction(()=>!document.querySelector('#simple-type').disabled);
    await page.locator('#simple-type').selectOption('FULL');
   }
   await page.waitForFunction(()=>!document.querySelector('#simple-refresh').disabled);
   result.ready=await page.locator('#simple-status').innerText();
   result.disabled=await page.locator('#simple-submit').isDisabled();
   result.operationId=await page.locator('#operation-id').innerText();
   if(mode==='full'||mode==='restore'){
    if(fs.existsSync(receipt))throw Error('ALREADY_SUBMITTED_USE_MONITOR');
    await page.waitForFunction(()=>!document.querySelector('#simple-submit').disabled);
    await page.locator('#simple-submit').click();
    await page.locator('#simple-confirm').waitFor({state:'visible'});
    result.confirmation=await page.locator('#confirm-summary').innerText();
    if(!result.confirmation.includes(source)||!result.confirmation.includes('172.30.30.57')||!result.confirmation.includes('安全模式'))throw Error('SOURCE_CONFIRMATION_MISMATCH');
    if(mode==='restore'){
     const point=JSON.parse(fs.readFileSync(path.join(task,'full-ui-submission.json'),'utf8')).request.operationId;
     if(!result.confirmation.includes(point)||!result.confirmation.includes(target)||!result.confirmation.includes('172.30.30.58'))throw Error('RESTORE_CONFIRMATION_MISMATCH');
     await page.locator('#replace-confirm').check();
    }else if(!result.confirmation.includes('全量备份'))throw Error('FULL_CONFIRMATION_MISMATCH');
    await page.screenshot({path:path.join(task,mode+'-ui-confirm.png'),fullPage:true});
    const accepted=page.waitForResponse(r=>new URL(r.url()).pathname==='/backup-entry-api/operations'&&r.request().method()==='POST',{timeout:30000});
    await page.locator('#simple-confirm-submit').click();
    const response=await accepted;const body=await response.json();
    write(priv+'/'+mode+'-entry-response.private.json',body);
    result.httpStatus=response.status();result.request=body.request;result.spugHistoryId=body.spugHistoryId;result.result=body.result;result.dispatchErrorCode=body.dispatchErrorCode;result.errorCode=body.errorCode;
    await context.storageState({path:priv+'/spug-active-session.private.json'});
    if(writes!==1)throw Error('SUBMISSION_COUNT_INVALID');
    if(!response.ok())throw Error(body.errorCode||'SUBMISSION_REJECTED');
   }
  }
  result.visible=await page.locator('main').innerText();
  if(monitor)result.progress={state:await page.locator('#simple-result').innerText(),steps:await page.locator('#steps').innerText(),problem:await page.locator('#problem').textContent(),logs:(await page.locator('#simple-logs').innerText()).split('\n').slice(-8).join('\n')};
  await page.screenshot({path:path.join(task,mode+'-ui-state.png'),fullPage:true});
  result.status='PASS';
 }catch(e){result.status='FAIL';result.error=String(e);result.visible=await page.locator('body').innerText().catch(()=>'(body unavailable)');process.exitCode=1;}
 finally{
  result.writes=writes;result.httpFailures=failures;result.finishedAt=new Date().toISOString();
  write(path.join(task,mode+'-ui-result.json'),result);
  console.log(JSON.stringify({mode,status:result.status,realLogin:result.realLogin,operationId:result.operationId,ready:result.ready,disabled:result.disabled,writes,httpStatus:result.httpStatus,result:result.result,error:result.error,progress:result.progress}));
  await browser.close();
 }
})().catch(e=>{console.error(String(e));process.exitCode=1;});
