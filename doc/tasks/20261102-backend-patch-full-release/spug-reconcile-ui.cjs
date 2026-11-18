'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const {chromium}=require('C:/Users/D01021/Documents/spug-handoff-work-20261030/package/tools/playwright/node_modules/playwright');
const action=process.argv[2];assert(['inspect-interruption','reconcile-interruption'].includes(action));
const privateRoot='C:/SpugHandoff/release/private/backend-patch-full-release-20261102';
let browser,stage='login';
(async()=>{try{
 browser=await chromium.launch({channel:'chrome',headless:true});const page=await browser.newPage({viewport:{width:1440,height:1050}});
 const errors=[];page.on('pageerror',e=>errors.push(e.name));
 await page.goto('http://127.0.0.1:18081/');
 const credentials=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8'));
 await page.getByPlaceholder('请输入账户').fill(credentials.username);await page.getByPlaceholder('请输入密码').fill(credentials.password);
 await page.getByRole('button',{name:'登 录'}).click();
 const warning=page.getByRole('button',{name:'知道了'});
 await Promise.race([warning.waitFor({state:'visible',timeout:15000}).then(()=>warning.click()),page.waitForFunction(()=>!!localStorage.token,null,{timeout:15000})]);
 await page.waitForFunction(()=>!!localStorage.token,null,{timeout:15000});
 stage='original-task';await page.goto('http://127.0.0.1:18081/release-center/?app=intruoyi&page=3');
 const group=page.locator('[data-interruption="JOB-fdd84f0df3"]');await group.waitFor({state:'visible'});
 if(action==='reconcile-interruption')await group.locator('[data-interruption-note]').fill('后续显式恢复JOB-a03c92262b与远端成功回执、实际原JAR及配置/台账已核；仅核销早先中断尝试，原未知回执保留，不重放恢复。');
 const button=group.locator('[data-action="'+action+'"]');assert(await button.isEnabled(),'UI reconciliation gate disabled');
 stage='submit';const responsePromise=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/actions/'+action));
 await button.click();const response=await responsePromise,job=await response.json();
 assert(response.ok()&&/^JOB-[a-f0-9]{10}$/.test(job.id),'Reconciliation request rejected');assert.deepEqual(errors,[]);
 const report={submittedAt:new Date().toISOString(),action,jobId:job.id,originalJobId:'JOB-fdd84f0df3',realPlaywrightLogin:true};
 fs.writeFileSync(__dirname+'/ui-submit-'+job.id+'.json',JSON.stringify(report,null,2),'utf8');console.log(JSON.stringify(report));
 await page.screenshot({path:privateRoot+'/spug-'+job.id+'.png',fullPage:false});
 }catch(e){fs.writeFileSync(privateRoot+'/spug-reconcile-failure.private.log',String(e.stack||e),'utf8');console.error(JSON.stringify({status:'failed',stage,errorCategory:e.name}));process.exitCode=1;}
 finally{if(browser)await browser.close();}
})();
