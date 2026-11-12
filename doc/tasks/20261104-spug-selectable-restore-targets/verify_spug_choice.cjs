// Real Spug login and choose/cancel only. The final execution button is never used.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');
const catalogMode=process.argv[2]==='catalog';
const output=path.join(__dirname,catalogMode?'browser-catalog-choice.json':'browser-choice.json');
const privateRoot='C:/Spug/runtime/private/restore-targets-20261104';
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,timeout:20000});
 const context=await browser.newContext({viewport:{width:1440,height:1080}});
 let page=await context.newPage();const rootPage=page;page.setDefaultTimeout(25000);
 const writes=[],blocked=[],failures=[];
 page.on('response',r=>{if(r.status()>=400)failures.push({status:r.status(),path:new URL(r.url()).pathname});});
 await page.route('**/*',async route=>{
  const req=route.request();
  if(!['GET','HEAD','OPTIONS'].includes(req.method())&&!new URL(req.url()).pathname.endsWith('/api/account/login/')){
   blocked.push({method:req.method(),path:new URL(req.url()).pathname});await route.abort('blockedbyclient');return;
  }
  if(req.method()==='POST')writes.push(new URL(req.url()).pathname);
  await route.continue();
 });
 const result={mode:process.argv[2]||'inspect',realBrowser:true,realLogin:false,restoreSubmitted:false};
 try{
  const admin=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
  await page.goto('http://127.0.0.1:18080/',{waitUntil:'domcontentloaded'});
  await page.getByPlaceholder('请输入账户').fill(admin.username);
  await page.getByPlaceholder('请输入密码').fill(admin.password);
  const authPromise=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登 录'}).click();
  const auth=await authPromise;const authBody=await auth.json();
  if(authBody.error)throw Error('SPUG_LOGIN_REJECTED: '+String(authBody.error));
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token'))||[...document.querySelectorAll('button')].some(b=>b.innerText==='知道了'));
  if(await page.getByRole('button',{name:'知道了'}).isVisible())await page.getByRole('button',{name:'知道了'}).click();
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));
  result.realLogin=true;
  await context.storageState({path:privateRoot+'/spug-browser-session.private.json'});
  await page.goto('http://127.0.0.1:18080/'+(catalogMode?'backup-center':'backup-restore/'),{waitUntil:'domcontentloaded'});
  if(catalogMode){
   const iframe=await page.locator('iframe[src="/backup-restore/?embedded=1"]').elementHandle();
   page=await iframe.contentFrame();
   if(!page)throw Error('NATIVE_BACKUP_CENTER_FRAME_MISSING');
  }
  await page.locator('#simple-refresh').waitFor();
  await page.waitForFunction(()=>document.querySelector('#simple-server').options.length>=3);
  if(catalogMode){
   await page.locator('#simple-catalog-tab').click();
   const restoreButton=page.locator('#catalog-body button:enabled').filter({hasText:/^恢复$/}).first();
   await restoreButton.waitFor({timeout:45000});
   result.catalogRow=await restoreButton.locator('xpath=../..').innerText();
   await restoreButton.click();
   await page.locator('#catalog-restore-dialog').waitFor({state:'visible'});
   result.catalogPackage=await page.locator('#catalog-restore-package').innerText();
   await page.waitForFunction(()=>document.querySelector('#simple-target').options.length>=4,{},{timeout:45000});
  }else{
  await page.locator('#simple-server').selectOption('172.30.30.57');
  await page.locator('#simple-mode').selectOption('safe');
  await page.locator('#simple-restore-tab').click();
  await page.waitForFunction(()=>document.querySelector('#simple-package').options.length>1,{},{timeout:45000});
  result.packages=await page.locator('#simple-package option').evaluateAll(nodes=>nodes.filter(n=>n.value).map(n=>({value:n.value,label:n.textContent})));
  await page.locator('#simple-package').selectOption(result.packages.at(-1).value);
  }
  result.targets=await page.locator('#simple-target option').evaluateAll(nodes=>nodes.map(n=>({value:n.value,label:n.textContent,disabled:n.disabled})));
  if(result.mode==='verify'||catalogMode){
   result.choices=[];
   for(const server of ['172.30.30.58','172.30.30.59']){
    await page.locator('#simple-target').selectOption(server);
    await page.locator('#simple-submit').waitFor({state:'visible'});
    await page.waitForFunction(()=>!document.querySelector('#simple-submit').disabled,{},{timeout:45000});
    await page.locator('#simple-submit').click();
    await page.locator('#simple-confirm').waitFor({state:'visible'});
    const summary=await page.locator('#confirm-summary').innerText();
    if(!summary.includes(server)||!summary.includes('intruoyi-main-'+server.split('.').at(-1)+'-safe-restore-20261104-v1')||!summary.includes('覆盖现有程序'))throw Error('CONFIRMATION_TARGET_MISMATCH');
    if(!await page.locator('#simple-confirm-submit').isDisabled())throw Error('OVERWRITE_ACK_NOT_REQUIRED');
    if(catalogMode&&!summary.includes(result.catalogPackage.split('备份包：').at(-1)))throw Error('CATALOG_PACKAGE_NOT_BOUND');
    await rootPage.screenshot({path:path.join(__dirname,(catalogMode?'catalog-confirm-':'confirm-')+server.split('.').at(-1)+'.png'),fullPage:true});
    await page.locator('#simple-cancel').click();
    await page.locator('#simple-confirm').waitFor({state:'hidden'});
    result.choices.push({server,summary,cancelled:true});
   }
   const prod=result.targets.find(t=>t.value==='172.30.30.57');
   if(!prod?.disabled)throw Error('UNVERIFIED_PRODUCTION_TARGET_ENABLED');
   if(catalogMode)await page.locator('#catalog-restore-close').click();
  }
  result.status='PASS';
 }catch(error){
  result.status='FAIL';result.error=String(error);
  result.visible=await page.locator('body').innerText().catch(()=>'(body unavailable)');
  process.exitCode=1;
 }finally{
  result.writes=writes;result.blocked=blocked;result.httpFailures=failures;
  if(blocked.length){result.status='FAIL';process.exitCode=1;}
  fs.writeFileSync(output,JSON.stringify(result,null,2),'utf8');
  console.log(JSON.stringify({status:result.status,realLogin:result.realLogin,packages:result.packages?.length,targets:result.targets,choices:result.choices?.length,error:result.error,writePaths:writes,blocked}));
  await browser.close();
 }
})().catch(error=>{console.error(String(error));process.exitCode=1;});
