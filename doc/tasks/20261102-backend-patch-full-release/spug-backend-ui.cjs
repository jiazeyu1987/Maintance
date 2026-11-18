'use strict';
const fs=require('node:fs');const assert=require('node:assert/strict');
const {chromium}=require('C:/Users/D01021/Documents/spug-handoff-work-20261030/package/tools/playwright/node_modules/playwright');
const [action,argument,note]=process.argv.slice(2);
assert(['register-baseline','build','deploy','accept','restore','refresh','inspect'].includes(action));
const privateRoot='C:/SpugHandoff/release/private/backend-patch-full-release-20261102';
let stage='launch',browser;
(async()=>{try{
 browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}});
 page.on('dialog',async dialog=>{assert(['deploy','restore'].includes(action),'Unexpected confirmation');await dialog.accept(dialog.type()==='prompt'?'PROD':undefined);});
 const errors=[];page.on('pageerror',e=>errors.push(e.name));
 stage='login';await page.goto('http://127.0.0.1:18081/');
 const credentials=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8'));
 await page.getByPlaceholder('请输入账户').fill(credentials.username);await page.getByPlaceholder('请输入密码').fill(credentials.password);
 await page.getByRole('button',{name:'登 录'}).click();
 const warning=page.getByRole('button',{name:'知道了'});
 await Promise.race([warning.waitFor({state:'visible',timeout:15000}).then(()=>warning.click()),page.waitForFunction(()=>!!localStorage.token,null,{timeout:15000})]);
 await page.waitForFunction(()=>!!localStorage.token,null,{timeout:15000});
 stage='backend-page';await page.goto('http://127.0.0.1:18081/release-center/backend-patch.html');
 await page.getByRole('heading',{name:'构建后端补丁',exact:true}).waitFor({timeout:120000});
 if(action==='inspect'){
  const value=await page.evaluate(()=>({baselines:bpState.backendPatchBaselines.map(b=>({id:b.id,gitCommit:b.gitCommit,releaseTag:b.releaseTag})),packages:bpState.backendPatches.map(p=>({tag:p.releaseTag,stage:p.stage}))}));
  console.log(JSON.stringify(value));return;
 }
 if(action==='build'){
  const options=await page.locator('#bp-base option').evaluateAll(rows=>rows.map(r=>r.value).filter(v=>v.startsWith('live:')));
  assert(options.length>0,'Registered baseline required');await page.locator('#bp-base').selectOption(options[0]);
  await page.locator('[data-draft=review]').fill(note);await page.locator('[data-draft=commit]').fill(argument);
 }else if(['deploy','accept','restore'].includes(action)){
  assert(['test','prod','backup'].includes(argument));
  const record=JSON.parse(fs.readFileSync(__dirname+'/selected-release.json','utf8'));
  await page.locator('#bp-package').selectOption(record.backendPatchTag);
  await page.locator('[data-draft='+argument+']').fill(note);
 }
 const button=page.locator('[data-back-action="backend-patch-'+action+'"]'+(['deploy','accept','restore'].includes(action)?'[data-target="'+argument+'"]':''));
 stage='submit-'+action;await button.waitFor({state:'visible'});assert(await button.isEnabled(),'UI gate disabled action');
 const responsePromise=page.waitForResponse(r=>r.request().method()==='POST'&&r.url().endsWith('/actions/backend-patch-'+action),{timeout:45000});
 await button.click();const response=await responsePromise;const job=await response.json();
 if(!response.ok()){
  fs.writeFileSync(privateRoot+'/spug-'+action+'-response.private.json',JSON.stringify({status:response.status(),body:job},null,2),'utf8');
  console.log(JSON.stringify({rejected:true,httpStatus:response.status(),reason:job.error||job.message||'See private response'}));
 }
 assert(response.ok()&&/^JOB-[a-f0-9]{10}$/.test(job.id),'Spug rejected operation');
 assert.deepEqual(errors,[]);
 const report={submittedAt:new Date().toISOString(),action,target:['deploy','accept','restore'].includes(action)?argument:null,jobId:job.id,realPlaywrightLogin:true};
 fs.writeFileSync(__dirname+'/ui-submit-'+job.id+'.json',JSON.stringify(report,null,2),'utf8');console.log(JSON.stringify(report));
 await page.screenshot({path:privateRoot+'/spug-'+job.id+'.png',fullPage:false});
 }catch(e){fs.writeFileSync(privateRoot+'/spug-'+action+'-failure.private.log',String(e.stack||e),'utf8');console.error(JSON.stringify({status:'failed',stage,errorCategory:e.name}));process.exitCode=1;}
 finally{if(browser)await browser.close();}
})();
