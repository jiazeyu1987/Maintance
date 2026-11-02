'use strict';
const fs=require('fs'),assert=require('assert/strict'),crypto=require('crypto');
const {chromium}=require('C:/Users/D01021/Documents/spug-handoff-work-20261030/package/tools/playwright/node_modules/playwright');
const privateRoot='C:/SpugHandoff/release/private',evidence=privateRoot+'/post-release-cleanup-20261102/resource-extension';
let credentialValues=[];
(async()=>{
 const credentials=JSON.parse(fs.readFileSync(privateRoot+'/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
 credentialValues=Object.values(credentials).filter(v=>typeof v==='string'&&v);
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
 const writes=[],errors=[],responses=[];let stage='login-page';
 page.on('request',r=>{if(!['GET','HEAD','OPTIONS'].includes(r.method()))writes.push(new URL(r.url()).pathname);});
 page.on('response',r=>{if(/\/api\//.test(new URL(r.url()).pathname))responses.push({path:new URL(r.url()).pathname,status:r.status()});});
 page.on('pageerror',e=>errors.push(e.name));
 try{
  await page.goto('http://127.0.0.1:18081/',{waitUntil:'networkidle',timeout:45000});
  await page.locator('#username').fill(credentials.username);await page.locator('#password').fill(credentials.password);
  assert(!await page.locator('input#captcha').isVisible(),'Visible CAPTCHA requires human response');
  stage='real-login';const auth=page.waitForResponse(r=>/\/api\/account\/login\/?$/.test(new URL(r.url()).pathname)&&r.request().method()==='POST',{timeout:90000});
  await page.getByRole('button',{name:/^登\s*录$/}).click();assert(!(await (await auth).json()).error,'Real login rejected');
  const warning=page.getByRole('button',{name:'知道了',exact:true});if(await warning.isVisible())await warning.click();
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));
  await context.storageState({path:evidence+'/browser-session.private.json'});
  stage='release-overview';
  await page.goto('http://127.0.0.1:18081/release-center/?app=intruoyi&page=0',{waitUntil:'domcontentloaded'});
  await page.getByRole('heading',{name:'发布总览',exact:true}).waitFor({timeout:120000});
  await page.waitForFunction(()=>document.querySelectorAll('#package option').length>1);
  const full=await page.locator('#package option').count();
  await page.locator('aside a.nav').filter({hasText:'任务记录'}).click();
  await page.getByRole('heading',{name:'任务记录',exact:true}).waitFor();
  const historyRows=await page.locator('section.card').filter({has:page.getByRole('heading',{name:'所有持久任务',exact:true})}).locator('tbody tr').count();
  assert.equal(historyRows,271,'Persistent job history changed');
  await page.goto('http://127.0.0.1:18081/release-center/frontend-patch.html',{waitUntil:'domcontentloaded'});
  await page.locator('#fp-package').waitFor({timeout:45000});assert.equal(await page.locator('#fp-package option').count(),2);
  await page.getByRole('heading',{name:'持久任务记录',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>typeof fpCleanup),'function');
  const served={};for(const name of ['app.js','frontend-patch.js']){
   const body=await (await page.request.get('http://127.0.0.1:18081/release-center/'+name)).body();
   const digest=x=>crypto.createHash('sha256').update(x).digest('hex');
   assert.equal(digest(body),digest(fs.readFileSync('C:/SpugHandoff/release/source/ops/spug/release-center/ui/'+name)));
   served[name]=digest(body);
  }
  assert(writes.every(p=>p==='/api/account/login/'),'Unexpected non-login mutation');assert.equal(errors.length,0);
  const result={status:'passed',realLogin:true,jobHistoryRows:historyRows,fullPackageOptions:full,patchPackageOptions:2,
   nonLoginWrites:0,pageErrors:errors.length,servedCode:served,cleanupActionsExecuted:0};
  fs.writeFileSync(evidence+'/ui-verification.json',JSON.stringify(result,null,2),'utf8');console.log(JSON.stringify(result));
 }catch(error){console.log(JSON.stringify({stage,writes,responses,pageErrors:errors}));await page.screenshot({path:evidence+'/ui-failure.private.png',mask:[page.locator('input')]});throw error;}
 finally{await context.close();await browser.close();}
})().catch(e=>{let reason=e.message.split('\n')[0];for(const value of credentialValues)reason=reason.split(value).join('[REDACTED]');console.error(JSON.stringify({status:'failed',errorName:e.name,reason}));process.exitCode=1;});
