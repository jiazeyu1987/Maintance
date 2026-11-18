'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const {chromium}=require('C:/Users/D01021/Documents/spug-handoff-work-20261030/package/tools/playwright/node_modules/playwright');
const original='JOB-7f32aa47ab',privateRoot='C:/SpugHandoff/release/private/backend-patch-full-release-20261102';
const legacy=process.argv.includes('--legacy'),reportName=legacy?'cleanup-retry-legacy-submission.json':'cleanup-retry-submission.json';
let browser,stage='login';
(async()=>{try{
 browser=await chromium.launch({channel:'chrome',headless:true});const page=await browser.newPage({viewport:{width:1440,height:1050}});
 const errors=[];page.on('pageerror',e=>errors.push(e.name));await page.goto('http://127.0.0.1:18081/');
 const credentials=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8'));
 await page.getByPlaceholder('请输入账户').fill(credentials.username);await page.getByPlaceholder('请输入密码').fill(credentials.password);
 await page.getByRole('button',{name:'登 录'}).click();const warning=page.getByRole('button',{name:'知道了'});
 await Promise.race([warning.waitFor({state:'visible',timeout:15000}).then(()=>warning.click()),page.waitForFunction(()=>!!localStorage.token,null,{timeout:15000})]);
 await page.waitForFunction(()=>!!localStorage.token,null,{timeout:15000});
 stage='original-cleanup-result';await page.goto('http://127.0.0.1:18081/release-center/?app=intruoyi&page=7');
 const button=page.locator('button[data-action="retry-release-cleanup"][data-job-id="'+original+'"]');
 await button.first().waitFor({state:'attached',timeout:120000});
 const selected=button.first();await selected.locator('..').locator(':scope > summary').click();assert(await selected.isEnabled());
 stage='submit-independent-cleanup';
 const [response]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/actions/retry-release-cleanup'),{timeout:60000}),selected.click({force:true,timeout:60000})]);
 const job=await response.json();assert(response.ok()&&/^JOB-[a-f0-9]{10}$/.test(job.id));assert.deepEqual(errors,[]);
 const report={submittedAt:new Date().toISOString(),action:'retry-release-cleanup',jobId:job.id,cleanupOf:original,realPlaywrightLogin:true};
 assert(!fs.existsSync(__dirname+'/'+reportName));fs.writeFileSync(__dirname+'/'+reportName,JSON.stringify(report,null,2)+'\n','utf8');
 console.log(JSON.stringify(report));await page.screenshot({path:privateRoot+'/spug-'+job.id+'.png',fullPage:false});
 }catch(e){fs.writeFileSync(privateRoot+'/cleanup-retry-ui-failure.private.log',String(e.stack||e),'utf8');console.error(JSON.stringify({status:'failed',stage,errorCategory:e.name}));process.exitCode=1;}
 finally{if(browser)await browser.close();}
})();
