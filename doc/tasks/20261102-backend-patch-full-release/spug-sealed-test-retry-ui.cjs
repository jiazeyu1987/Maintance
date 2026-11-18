'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const {chromium}=require('C:/Users/D01021/Documents/spug-handoff-work-20261030/package/tools/playwright/node_modules/playwright');
const originalId=process.argv[2];assert(/^JOB-[a-f0-9]{10}$/.test(originalId));
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
 stage='original-failed-test';await page.goto('http://127.0.0.1:18081/release-center/?app=intruoyi&page=7');
 const group=page.locator('[data-resolution="'+originalId+'"]');await group.waitFor({state:'visible',timeout:120000});
 await group.locator('[data-resolution-decision]').selectOption('retry');
 await group.locator('[data-resolution-note]').fill('沿用原全量包和完整检查点，核原容器、挂载JAR、全表内容、GxP及零写者后仅续接程序切换与验收；不重备份、不执行迁移或恢复数据库，保留原失败。');
 const button=group.locator('[data-action="resolve-task"]');assert(await button.isEnabled());
 stage='submit-original-package-retry';
 // The periodically refreshed full-history page keeps moving the button.
 // Enabled state is checked above; use a real mouse click without waiting for layout stability.
 await button.scrollIntoViewIfNeeded();
 const [response]=await Promise.all([
   page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/actions/resolve-task'),{timeout:60000}),
   button.click({force:true,timeout:60000})
 ]);const job=await response.json();
 if(!response.ok()||!/^JOB-[a-f0-9]{10}$/.test(job.id))fs.writeFileSync(privateRoot+'/sealed-test-retry-response.private.json',JSON.stringify({status:response.status(),body:job},null,2),'utf8');
 assert(response.ok()&&/^JOB-[a-f0-9]{10}$/.test(job.id),'Original package retry rejected');assert.deepEqual(errors,[]);
 const report={submittedAt:new Date().toISOString(),action:'resolve-task',decision:'retry',jobId:job.id,originalDeploymentJobId:originalId,realPlaywrightLogin:true};
 fs.writeFileSync(__dirname+'/ui-submit-'+job.id+'.json',JSON.stringify(report,null,2),'utf8');console.log(JSON.stringify(report));
 await page.screenshot({path:privateRoot+'/spug-'+job.id+'.png',fullPage:false});
 }catch(e){fs.writeFileSync(privateRoot+'/sealed-test-retry-failure.private.log',String(e.stack||e),'utf8');console.error(JSON.stringify({status:'failed',stage,errorCategory:e.name}));process.exitCode=1;}
 finally{if(browser)await browser.close();}
})();
