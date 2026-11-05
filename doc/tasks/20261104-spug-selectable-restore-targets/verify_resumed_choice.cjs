// Real UI choice/cancel only. Any business or restore POST is rejected and fails.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs');const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,timeout:20000});
 const context=await browser.newContext({viewport:{width:1440,height:1080}});
 const page=await context.newPage();page.setDefaultTimeout(45000);
 const writes=[],blocked=[],httpFailures=[];
 const out={realBrowser:true,realLogin:false,restoreSubmitted:false};
 await page.route('**/*',async route=>{
  const req=route.request(),pathname=new URL(req.url()).pathname;
  if(!['GET','HEAD','OPTIONS'].includes(req.method())&&pathname!='/api/account/login/'){
   blocked.push({method:req.method(),path:pathname});await route.abort('blockedbyclient');return;
  }
  if(req.method()==='POST')writes.push(pathname);
  await route.continue();
 });
 page.on('response',r=>{if(r.status()>=400)httpFailures.push({status:r.status(),path:new URL(r.url()).pathname});});
 try{
  const admin=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
  await page.goto('http://127.0.0.1:18080/',{waitUntil:'domcontentloaded'});
  await page.getByPlaceholder('请输入账户').fill(admin.username);await page.getByPlaceholder('请输入密码').fill(admin.password);
  const authPromise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登 录'}).click();const authBody=await (await authPromise).json();
  if(authBody.error)throw Error('SPUG_LOGIN_REJECTED');
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token'))||[...document.querySelectorAll('button')].some(b=>b.innerText==='知道了'));
  if(await page.getByRole('button',{name:'知道了'}).isVisible())await page.getByRole('button',{name:'知道了'}).click();
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));out.realLogin=true;
  await page.goto('http://127.0.0.1:18080/backup-center',{waitUntil:'domcontentloaded'});
  const frame=await (await page.locator('iframe[src="/backup-restore/?embedded=1"]').elementHandle()).contentFrame();
  if(!frame)throw Error('NATIVE_BACKUP_FRAME_MISSING');
  await frame.locator('#simple-catalog-tab').click();
  const restore=frame.locator('#catalog-body button:enabled').filter({hasText:/^恢复$/}).first();
  await restore.waitFor();out.catalogRow=await restore.locator('xpath=../..').innerText();await restore.click();
  await frame.locator('#catalog-restore-dialog').waitFor({state:'visible'});
  out.catalogPackage=await frame.locator('#catalog-restore-package').innerText();
  await frame.waitForFunction(()=>document.querySelector('#simple-target').options.length>=4);
  await frame.locator('#simple-target').selectOption('172.30.30.58');
  await frame.waitForFunction(()=>!document.querySelector('#simple-submit').disabled);
  await frame.locator('#simple-submit').click();await frame.locator('#simple-confirm').waitFor({state:'visible'});
  out.testConfirmation=await frame.locator('#confirm-summary').innerText();
  if(!out.testConfirmation.includes('intruoyi-main-58-safe-restore-20261104-v1')||!out.testConfirmation.includes('172.30.30.58'))throw Error('TEST_TARGET_BINDING_MISMATCH');
  if(!await frame.locator('#simple-confirm-submit').isDisabled())throw Error('OVERWRITE_ACK_NOT_REQUIRED');
  await page.screenshot({path:path.join(__dirname,'resumed-test-confirm.png'),fullPage:true});
  await frame.locator('#simple-cancel').click();await frame.locator('#simple-confirm').waitFor({state:'hidden'});
  const response=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/selections')&&new URL(r.url()).searchParams.get('targetConfigRef')==='intruoyi-main-59-safe-restore-20261104-v1');
  await frame.locator('#simple-target').selectOption('172.30.30.59');await response;
  await frame.waitForFunction(()=>!document.querySelector('#simple-target').disabled&&document.querySelector('#simple-submit').disabled&&document.querySelector('#simple-status').dataset.state==='blocked');
  out.reviewBlocked=await frame.locator('#simple-status').innerText();
  out.reviewVisibleError=await frame.locator('body').innerText();
  if(!out.reviewVisibleError.includes('MAIN_TARGET_OBSERVATION_FAILED'))throw Error('EXPECTED_REVIEW_ADMISSION_ERROR_NOT_VISIBLE');
  out.targets=await frame.locator('#simple-target option').evaluateAll(nodes=>nodes.map(n=>({value:n.value,label:n.textContent,disabled:n.disabled})));
  if(!out.targets.find(t=>t.value==='172.30.30.57')?.disabled)throw Error('UNREGISTERED_PRODUCTION_ENABLED');
  await page.screenshot({path:path.join(__dirname,'resumed-review-blocked.png'),fullPage:true});
  await frame.locator('#catalog-restore-close').click();
  out.status='PASS';
 }catch(error){out.status='FAIL';out.error=String(error);process.exitCode=1;}
 finally{
  out.writes=writes;out.blocked=blocked;out.httpFailures=httpFailures;
  if(blocked.length){out.status='FAIL';process.exitCode=1;}
  fs.writeFileSync(path.join(__dirname,'resumed-browser-choice.json'),JSON.stringify(out,null,2),'utf8');
  console.log(JSON.stringify({status:out.status,realLogin:out.realLogin,targets:out.targets,reviewBlocked:out.reviewBlocked,error:out.error,writes,blocked}));
  await browser.close();
 }
})().catch(error=>{console.error(String(error));process.exitCode=1;});
