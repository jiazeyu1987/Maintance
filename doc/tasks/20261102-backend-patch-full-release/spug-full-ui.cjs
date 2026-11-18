'use strict';
const fs=require('node:fs');const assert=require('node:assert/strict');
const {chromium}=require('C:/Users/D01021/Documents/spug-handoff-work-20261030/package/tools/playwright/node_modules/playwright');
const [action,note]=process.argv.slice(2);
const pages={'precheck-build':1,'build-release':1,'publish-test':3,'mark-tested':3,'promote-prod':5,'accept-prod':5,'promote-backup':6,'accept-backup':6};
assert(Object.hasOwn(pages,action));
const privateRoot='C:/SpugHandoff/release/private/backend-patch-full-release-20261102';
let browser,stage='launch';
(async()=>{try{
 const selection=JSON.parse(fs.readFileSync(__dirname+'/selected-release.json','utf8'));
 browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}});
 const errors=[];page.on('pageerror',e=>errors.push(e.name));
 stage='login';await page.goto('http://127.0.0.1:18081/');
 const credentials=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8'));
 await page.getByPlaceholder('请输入账户').fill(credentials.username);await page.getByPlaceholder('请输入密码').fill(credentials.password);
 await page.getByRole('button',{name:'登 录'}).click();
 const warning=page.getByRole('button',{name:'知道了'});
 await Promise.race([warning.waitFor({state:'visible',timeout:15000}).then(()=>warning.click()),page.waitForFunction(()=>!!localStorage.token,null,{timeout:15000})]);
 await page.waitForFunction(()=>!!localStorage.token,null,{timeout:15000});
 stage='full-release-page';await page.goto('http://127.0.0.1:18081/release-center/?app=intruoyi&page='+pages[action]);
  const actionId=action==='precheck-build'?'check-prerequisites':action;
  const button=page.locator('[data-action="'+actionId+'"]');await button.waitFor({state:'visible',timeout:120000});
  if(['precheck-build','build-release'].includes(action))await page.locator('#commit').selectOption(selection.commit);
 else await page.locator('#package').selectOption(selection.fullReleaseTag);
 if(['accept-prod','accept-backup'].includes(action)){assert(note&&note.length>=5);await page.locator('#accept-note').fill(note);}
 stage='submit-'+action;assert(await button.isEnabled(),'Full release UI gate disabled action');
  const responsePromise=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/actions/'+actionId),{timeout:45000});
  await button.click();const response=await responsePromise;const job=await response.json();
  if(!response.ok()||!/^JOB-[a-f0-9]{10}$/.test(job.id))fs.writeFileSync(privateRoot+'/spug-'+action+'-response.private.json',JSON.stringify({status:response.status(),body:job},null,2),'utf8');
  assert(response.ok()&&/^JOB-[a-f0-9]{10}$/.test(job.id),'Spug rejected operation');
 assert.deepEqual(errors,[]);
 const report={submittedAt:new Date().toISOString(),action,jobId:job.id,realPlaywrightLogin:true};
 fs.writeFileSync(__dirname+'/ui-submit-'+job.id+'.json',JSON.stringify(report,null,2),'utf8');console.log(JSON.stringify(report));
 await page.screenshot({path:privateRoot+'/spug-'+job.id+'.png',fullPage:false});
 }catch(e){fs.writeFileSync(privateRoot+'/spug-'+action+'-failure.private.log',String(e.stack||e),'utf8');console.error(JSON.stringify({status:'failed',stage,errorCategory:e.name}));process.exitCode=1;}
 finally{if(browser)await browser.close();}
})();
