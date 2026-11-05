// Real UI choice/cancel only. Any business or restore POST is rejected and fails.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs');const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,timeout:20000});
 const context=await browser.newContext({viewport:{width:1440,height:1080}});
 const page=await context.newPage();page.setDefaultTimeout(45000);
 const writes=[],blocked=[],httpFailures=[];
 const out={realBrowser:true,realLogin:false,restoreSubmitted:false};
 out.pageErrors=[];out.apiErrors=[];
 page.on('pageerror',error=>out.pageErrors.push(String(error)));
 page.on('response',async response=>{
  if(response.request().method()==='GET'&&response.headers()['content-type']?.includes('application/json')){
   try{const value=await response.json();if(value.error||value.errorCode)out.apiErrors.push({path:new URL(response.url()).pathname,error:value.error,errorCode:value.errorCode});}
   catch(error){out.apiErrors.push({path:new URL(response.url()).pathname,readError:String(error)});}
  }
 });
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
  await page.getByText('备份与恢复',{exact:true}).first().waitFor();
  await page.getByText('备份与恢复',{exact:true}).first().click();
  await page.waitForURL('**/backup-center');
  const frame=await (await page.locator('iframe[src="/backup-restore/?embedded=1"]').elementHandle()).contentFrame();
  if(!frame)throw Error('NATIVE_BACKUP_FRAME_MISSING');
  // The real page refuses catalogue actions while initial source checks run.
  await frame.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:90000});
  out.initialConfigurationReady=true;
  console.log('Real Spug initial source checks completed');
  await frame.locator('#simple-catalog-tab').click();
  await frame.locator('#simple-catalog-tab[aria-selected="true"]').waitFor();
  const restore=frame.locator('#catalog-body button:enabled').filter({hasText:/^恢复$/}).first();
  await restore.waitFor();out.catalogRow=await restore.locator('xpath=../..').innerText();
  out.beforeClick=await frame.evaluate(()=>({simpleInitializing,locked:interactionLocked(),switching,unresolvedOriginal:!!unresolvedOriginal(),activeUnresolved:!!active&&!resolvedRecord(active),hasConfiguration:!!simpleConfig}));
  await restore.evaluate(button=>{window.__reviewClickObservation=[];button.addEventListener('click',event=>window.__reviewClickObservation.push({trusted:event.isTrusted,text:event.currentTarget.textContent}),{once:true});});
  await restore.click();
  out.afterClick=await frame.evaluate(()=>({simpleInitializing,locked:interactionLocked(),switching,unresolvedOriginal:!!unresolvedOriginal(),activeUnresolved:!!active&&!resolvedRecord(active),hasConfiguration:!!simpleConfig,catalogRestore,clicks:window.__reviewClickObservation,problem:document.querySelector('#catalog-problem').textContent}));
  await frame.locator('#catalog-restore-dialog').waitFor({state:'visible'});
  console.log('Real catalogue restore dialog opened');
  out.catalogPackage=await frame.locator('#catalog-restore-package').innerText();
  await frame.waitForFunction(()=>document.querySelector('#simple-target').options.length>=4&&!document.querySelector('#simple-target').disabled);
  await frame.locator('#simple-target').selectOption('172.30.30.58');
  await frame.waitForFunction(()=>!document.querySelector('#simple-submit').disabled);
  await frame.locator('#simple-submit').click();await frame.locator('#simple-confirm').waitFor({state:'visible'});
  out.testConfirmation=await frame.locator('#confirm-summary').innerText();
  if(!out.testConfirmation.includes('intruoyi-main-58-safe-restore-20261104-v1')||!out.testConfirmation.includes('172.30.30.58'))throw Error('TEST_TARGET_BINDING_MISMATCH');
  if(!await frame.locator('#simple-confirm-submit').isDisabled())throw Error('OVERWRITE_ACK_NOT_REQUIRED');
  console.log('Test target confirmation verified; cancelling');
  await page.screenshot({path:path.join(__dirname,'review-authorized-test-confirm.png'),fullPage:true});
  await frame.locator('#simple-cancel').click();await frame.locator('#simple-confirm').waitFor({state:'hidden'});
  await frame.locator('#simple-target').selectOption('172.30.30.59');
  await frame.waitForFunction(()=>!document.querySelector('#simple-submit').disabled);
  await frame.locator('#simple-submit').click();await frame.locator('#simple-confirm').waitFor({state:'visible'});
  out.reviewConfirmation=await frame.locator('#confirm-summary').innerText();
  if(!out.reviewConfirmation.includes('intruoyi-main-59-safe-restore-20261104-v1')||!out.reviewConfirmation.includes('172.30.30.59'))throw Error('REVIEW_TARGET_BINDING_MISMATCH');
  if(!await frame.locator('#simple-confirm-submit').isDisabled())throw Error('OVERWRITE_ACK_NOT_REQUIRED');
  console.log('Review target confirmation verified; cancelling');
  await page.screenshot({path:path.join(__dirname,'review-authorized-confirm.png'),fullPage:true});
  await frame.locator('#simple-cancel').click();await frame.locator('#simple-confirm').waitFor({state:'hidden'});
  out.targets=await frame.locator('#simple-target option').evaluateAll(nodes=>nodes.map(n=>({value:n.value,label:n.textContent,disabled:n.disabled})));
  if(!out.targets.find(t=>t.value==='172.30.30.57')?.disabled)throw Error('UNREGISTERED_PRODUCTION_ENABLED');
  await frame.locator('#catalog-restore-close').click();
  out.status='PASS';
 }catch(error){out.status='FAIL';out.error=String(error);out.visible=await page.locator('body').innerText();out.frames=[];for(const frame of page.frames()){if(frame!==page.mainFrame())out.frames.push({url:frame.url(),visible:await frame.locator('body').innerText(),status:await frame.locator('#simple-status').textContent(),refreshDisabled:await frame.locator('#simple-refresh').isDisabled()});}await page.screenshot({path:path.join(__dirname,'review-authorized-browser-failure.png'),fullPage:true});process.exitCode=1;}
 finally{
  out.writes=writes;out.blocked=blocked;out.httpFailures=httpFailures;
  if(blocked.length||out.pageErrors.length||out.apiErrors.length||httpFailures.length){out.status='FAIL';process.exitCode=1;}
  fs.writeFileSync(path.join(__dirname,'review-authorized-browser-choice.json'),JSON.stringify(out,null,2),'utf8');
  console.log(JSON.stringify({status:out.status,realLogin:out.realLogin,targets:out.targets,reviewConfirmation:out.reviewConfirmation,error:out.error,writes,blocked}));
  await browser.close();
 }
})().catch(error=>{console.error(String(error));process.exitCode=1;});
