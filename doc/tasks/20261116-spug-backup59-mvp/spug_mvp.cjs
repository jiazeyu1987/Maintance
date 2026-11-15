const fs=require('fs');
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const root='C:/Spug/runtime/private/spug-backup59-mvp-20261116';
const progressObservations=[];
(async()=>{const b=await chromium.launch({channel:'msedge',headless:true});const querying=process.argv.includes('--query');const restoreQuery=process.argv.includes('--restore-query');const point=process.argv.includes('--incremental')?'smallapp-e7b668792c8f4bce945a52f984d3c660':'smallapp-3c2395ff88bd474e9fc007649565b848';const context=await b.newContext(querying||restoreQuery?{storageState:root+(restoreQuery?'/restore-browser-session.private.json':'/browser-session.private.json')}:{});const p=await context.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));try{
p.on('response',async response=>{const url=new URL(response.url());if(url.pathname.includes('/progress/')){try{const value=await response.json();progressObservations.push({path:url.pathname,status:response.status(),value});fs.writeFileSync(root+'/progress-responses-latest.private.json',JSON.stringify(progressObservations,null,2));console.log(JSON.stringify({progressResponse:url.pathname,status:response.status(),error:value.error,errorCode:value.errorCode,keys:Object.keys(value)}));}catch(error){console.log(JSON.stringify({progressReadError:error.message.split('\n')[0]}));}}if(url.pathname.endsWith('/selections')){try{const value=await response.json();console.log(JSON.stringify({selectionRequest:url.pathname+url.search,status:response.status(),error:value.error,applications:value.applications?.filter(app=>app.applicationId===url.searchParams.get('applicationId')).map(app=>({applicationId:app.applicationId,readinessError:app.readinessError,points:app.validated?.recoveryPointRefs?.length}))}));}catch(error){console.log(JSON.stringify({selectionResponseError:error.message.split('\n')[0]}));}}});
if(restoreQuery){await p.goto('http://127.0.0.1:18080/backup-restore/');await p.locator('#simple-progress-tab').click();await p.locator('#simple-query:not([disabled])').waitFor({timeout:65000});const observed=p.waitForResponse(r=>/^\/backup-entry-api\/operations\//.test(new URL(r.url()).pathname),{timeout:60000});const observedProgress=p.waitForResponse(r=>new URL(r.url()).pathname.includes('/progress/'),{timeout:65000});await p.locator('#simple-query').click();const response=await observed;const result=await response.json();const progressResponse=await observedProgress;const progressValue=await progressResponse.json();if(progressValue.steps?.length)await p.waitForFunction(count=>document.querySelector('#steps')?.children.length===count,progressValue.steps.length,{timeout:10000});await p.locator('#simple-query:not([disabled])').waitFor({timeout:65000});const report={stage:'restore-query',httpStatus:response.status(),result,progress:await p.locator('#simple-progress-panel').innerText(),errors};await p.screenshot({path:root+'/restore-state.png',fullPage:true});fs.writeFileSync(root+'/restore-query-latest.private.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));return;}
if(querying){const observed=p.waitForResponse(r=>new URL(r.url()).pathname.includes('/prepare-target/operations/'),{timeout:60000});await p.goto('http://127.0.0.1:18080/backup-restore/');const response=await observed;const result=await response.json();await p.locator('#simple-progress-tab').click();const report={stage:'query',httpStatus:response.status(),result,progress:await p.locator('#prepare-target-progress').innerText(),errors};await p.screenshot({path:root+'/prepare-state.png',fullPage:true});fs.writeFileSync(root+'/query-latest.private.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));return;}
const c=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
await p.goto('http://127.0.0.1:18080/');await p.locator('#username').fill(c.username);await p.locator('#password').fill(c.password);
if(await p.locator('input#captcha').isVisible())throw new Error('CAPTCHA_REQUIRED');
const auth=p.waitForResponse(r=>r.request().method()==='POST'&&r.url().includes('/account/login/'));
await p.getByRole('button',{name:/^登\s*录$/}).click();const login=await (await auth).json();if(login.error)throw new Error('LOGIN_REJECTED');
const warning=p.getByRole('button',{name:'知道了',exact:true});if(await warning.isVisible())await warning.click();
await p.waitForFunction(()=>!!localStorage.getItem('token'),{},{timeout:20000});
await context.storageState({path:root+'/browser-session.private.json'});
await p.goto('http://127.0.0.1:18080/backup-restore/',{waitUntil:'domcontentloaded'});
await p.locator('#simple-server:not([disabled])').waitFor({timeout:60000});
await p.locator('#simple-server').selectOption('172.30.30.57');
await p.locator('#simple-mode').selectOption('safe');
await p.locator('#simple-restore-tab').click();
await p.locator('#simple-restore-mode').selectOption('fresh');
await p.locator('#simple-target').selectOption('172.30.30.59');
if(process.argv.includes('--catalog')){await p.waitForFunction(()=>document.querySelector('#simple-package').options.length>1,{},{timeout:65000});console.log(JSON.stringify({stage:'catalog',points:await p.locator('#simple-package option').evaluateAll(options=>options.map(o=>({value:o.value,label:o.textContent})))}));return;}
await p.waitForFunction(point=>[...document.querySelector('#simple-package').options].some(o=>o.value===point),point,{timeout:65000});
await p.locator('#simple-package').selectOption(point);
const report={stage:'selected',status:await p.locator('#simple-status').innerText(),prepare:await p.locator('#prepare-target-status').innerText(),errors};
if(process.argv.includes('--restore')){
await p.locator('#simple-submit:not([disabled])').click({timeout:30000});
await p.locator('#simple-confirm[open]').waitFor();report.confirmation=await p.locator('#confirm-summary').innerText();
if(await p.locator('#replace-confirm-field').isVisible())throw new Error('EXPECTED_FRESH_TARGET_RESTORE');
const restored=p.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/backup-entry-api/operations',{timeout:85000});
await p.locator('#simple-confirm-submit').click();await context.storageState({path:root+'/restore-browser-session.private.json'});
const response=await restored;report.restoreResponse=await response.json();report.restoreHttpStatus=response.status();report.stage=response.ok()?'restore-submitted':'restore-rejected';if(!response.ok())process.exitCode=1;
await context.storageState({path:root+'/restore-browser-session.private.json'});
}
if(process.argv.includes('--preview')||process.argv.includes('--prepare')){
await p.locator('#prepare-target-start').click({timeout:20000});
await p.locator('#prepare-target-confirm[open]').waitFor({timeout:85000});report.preview=await p.locator('#prepare-target-summary').innerText();report.stage='preview';
if(process.argv.includes('--prepare')){await p.locator('#prepare-target-agree').check();const submitted=p.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname.endsWith('/prepare-target/operations'),{timeout:85000});await p.locator('#prepare-target-confirm-submit').click();await context.storageState({path:root+'/browser-session.private.json'});await submitted;report.stage='submitted';report.progress=await p.locator('#prepare-target-progress').textContent();}
}
fs.writeFileSync(root+'/page-latest.private.json',JSON.stringify(report,null,2));const summary={...report};delete summary.preview;console.log(JSON.stringify(summary));
}catch(e){console.log(JSON.stringify({error:e.message.split('\n')[0],errors,status:await p.locator('#simple-status').textContent().catch(()=>null),prepare:await p.locator('#prepare-target-status').textContent().catch(()=>null),selection:await p.evaluate(()=>Object.fromEntries(['simple-product','simple-server','simple-mode','application','simple-target'].map(id=>[id,document.getElementById(id)?.value]))).catch(()=>null)}));process.exitCode=1;}finally{await b.close()}})();
