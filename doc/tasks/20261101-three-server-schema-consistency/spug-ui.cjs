'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('C:/Users/D01021/Documents/spug-handoff-work-20261030/package/tools/playwright/node_modules/playwright');
const privateRoot='C:/SpugHandoff/release/private';
const evidence=path.join(privateRoot,'acceptance','schema-20261101');
fs.mkdirSync(evidence,{recursive:true});
const [command='status',arg='',extra='',note='',decision='abandon']=process.argv.slice(2);
const pages={'scan-artifacts':9,'check-prerequisites':1,'build-release':1,'publish-test':3,'mark-tested':3,'prepare-rehearsal':4,'upgrade-rehearsal':4,'accept-rehearsal':4,'promote-prod':5,'verify-prod':5,'accept-prod':5,'promote-backup':6,'verify-backup':6,'accept-backup':6,'inspect-release-recovery':7,'recover-release':7,'accept-recovery':7,'resolve-task':7};
const session=path.join(evidence,'spug-session.private.json');
const creds=JSON.parse(fs.readFileSync(path.join(privateRoot,'spug-login.private.json'),'utf8').replace(/^\uFEFF/,''));
const sensitive=Object.values(creds).filter(v=>typeof v==='string'&&v.length>2);
const clean=s=>sensitive.reduce((v,k)=>v.split(k).join('[REDACTED]'),String(s));
let browser,context,page,latest,stage='launch';
function summary(s){
 return {application:s.application?.id,packages:s.packages.length,jobs:s.jobs.length,
  active:s.jobs.filter(j=>j.status==='running'||j.status==='interrupted'&&!j.resolution).map(j=>({id:j.id,action:j.action,status:j.status,releaseTag:j.releaseTag,step:j.currentStep})),
  recent:s.jobs.slice(0,8).map(j=>({id:j.id,action:j.action,status:j.status,releaseTag:j.releaseTag,step:j.currentStep,error:clean(j.error||''),result:j.action==='check-prerequisites'?{status:j.result?.status,checks:j.result?.checks?.map(c=>({id:c.id,status:c.status,detail:clean(c.detail||'')}))}:undefined})),
  environments:Object.fromEntries(Object.entries(s.environments).map(([k,v])=>[k,{releaseTag:v.releaseTag,baselineStatus:v.baselineStatus,maintenance:v.maintenance,gxpAuditMode:v.gxpAuditMode,configuredGxpAuditMode:v.configuredGxpAuditMode}])),
  candidate:s.packages.find(p=>p.releaseTag===arg)?{releaseTag:arg,stage:s.packages.find(p=>p.releaseTag===arg).stage}:undefined};
}
(async()=>{
 try{
  browser=await chromium.launch({channel:'chrome',headless:true});
  context=await browser.newContext({viewport:{width:1440,height:1100},...(command!=='login'&&fs.existsSync(session)?{storageState:session}:{})});
  page=await context.newPage();
  page.on('response',async r=>{if(r.url().includes('/release-center/api/applications/intruoyi/state')&&r.ok()){try{latest=await r.json();fs.writeFileSync(path.join(evidence,'state.private.json'),JSON.stringify(latest));}catch{}}});
  page.on('dialog',async d=>{throw Error('Unexpected UI dialog: '+d.type());});
  if(command==='login'||!fs.existsSync(session)){
   stage='real-spug-login';await page.goto('http://127.0.0.1:18081/',{waitUntil:'networkidle'});
   await page.locator('#username').fill(creds.username);await page.locator('#password').fill(creds.password);
   assert(!await page.locator('input#captcha').isVisible(),'Visible CAPTCHA requires human answer');
   const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST');
   await page.getByRole('button',{name:/^登\s*录$/}).click();const auth=await (await response).json();assert(!auth.error,'Spug login rejected');
   const warning=page.getByRole('button',{name:'知道了',exact:true});if(await warning.isVisible())await warning.click();
   await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));await context.storageState({path:session});
  }
  stage='release-page';const index=pages[command]??(command==='build-view'?1:0);
  await page.goto('http://127.0.0.1:18081/release-center/?app=intruoyi&page='+index,{waitUntil:'domcontentloaded'});
  await page.getByRole('heading',{name:index===1?'构建版本':index===0?'发布总览':undefined,exact:true}).first().waitFor({timeout:60000});
  await page.waitForFunction(()=>document.querySelector('#application')?.value==='intruoyi'&&document.querySelectorAll('section.card').length>0,{},{timeout:60000});
  latest=await page.evaluate(()=>state);
  assert(latest?.application?.id==='intruoyi','Application state unavailable');
  fs.writeFileSync(path.join(evidence,'state.private.json'),JSON.stringify(latest));
  if(pages[command]!==undefined){
   stage='select-input';
   if(index===1){await page.locator('#commit').selectOption(arg);assert.equal(await page.locator('#commit').inputValue(),arg);}
   else if(command==='scan-artifacts'){await page.locator('#artifact-keep').selectOption(arg||'5');}
   else if(command!=='resolve-task'){await page.locator('#package').selectOption(arg);assert.equal(await page.locator('#package').inputValue(),arg);}
   if(command==='accept-prod'||command==='accept-backup')await page.locator('#accept-note').fill(extra);
   const recoveryAction=['inspect-release-recovery','recover-release','accept-recovery'].includes(command);
   const resolutionAction=command==='resolve-task';
   const group=recoveryAction?page.locator('[data-recovery="'+extra+'"]'):resolutionAction?page.locator('[data-resolution="'+extra+'"]'):page;
   if(recoveryAction&&command!=='inspect-release-recovery')await group.locator('[data-recovery-note]').fill(note);
   if(resolutionAction){assert(['retry','abandon'].includes(decision));assert(latest.jobs.some(j=>j.id===extra&&j.releaseTag===arg),'Resolution target mismatch');await group.locator('[data-resolution-decision]').selectOption(decision);await group.locator('[data-resolution-note]').fill(note);}
   const selector='[data-action="'+command+'"]'+(command==='promote-backup'&&extra?'[data-retry-of="'+extra+'"]':'');
   const button=group.locator(selector);assert.equal(await button.count(),1,'Action button not unique');
   if(!await button.isEnabled()){fs.writeFileSync(path.join(evidence,'blocked-ui.private.txt'),await page.locator('main').innerText());throw Error('UI action disabled; inspect private blocked-ui evidence');}
   assert(!latest.jobs.some(j=>j.status==='running'),'Another job is running');
   stage='click-'+command;
   const response=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/actions/'+command),{timeout:60000});
   await button.click();const r=await response;const body=await r.json();
   fs.writeFileSync(path.join(evidence,'last-action.private.json'),JSON.stringify(body,null,2));
   assert(r.ok(),clean(body.error||'Action rejected'));
   console.log(JSON.stringify({clicked:command,input:arg,httpStatus:r.status(),jobId:body.id||body.job?.id||body.jobId}));
   await page.waitForTimeout(1500);
  }
  stage='capture';await page.screenshot({path:path.join(evidence,'spug-'+command+'.private.png')});
  latest=await page.evaluate(()=>state);
  fs.writeFileSync(path.join(evidence,'state.private.json'),JSON.stringify(latest));
  const report=summary(latest);
  if(command==='build-view')report.commits=await page.locator('#commit option').evaluateAll(ns=>ns.map(n=>({value:n.value,text:n.textContent})));
  report.buttons=await page.locator('main [data-action]').evaluateAll(ns=>ns.map(n=>({action:n.dataset.action,text:n.textContent,disabled:n.disabled})));
  fs.writeFileSync(path.join(__dirname,'spug-'+command+'-latest.json'),JSON.stringify(report,null,2),'utf8');console.log(JSON.stringify(report));
 }catch(e){
  if(page)await page.screenshot({path:path.join(evidence,'failure-'+command+'.private.png'),mask:[page.locator('input')]}).catch(()=>{});
  console.error(JSON.stringify({status:'FAIL',stage,reason:clean(e.message.split('\n')[0])}));process.exitCode=1;
 }finally{if(context)await context.close();if(browser)await browser.close();}
})();
