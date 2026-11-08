// Reconcile the existing timed-out submission using only real page GETs.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const task=__dirname,priv='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106';
const kind=process.argv[2],phase=process.argv[3];
if(!/^restore-(58|59)(-r[2-9])?$/.test(kind)||!['accepted','terminal'].includes(phase))throw Error('EXPLICIT_OPERATION_AND_PHASE_REQUIRED');
const observation=process.argv[4]||'';
if(observation&&!/^r[2-9][0-9]*$/.test(observation))throw Error('EXPLICIT_OBSERVATION_SEQUENCE_REQUIRED');
const label=phase+(observation?'-'+observation:'');
const refreshConfiguration=process.argv[5]==='refresh-configuration';
if(process.argv[5]&&!refreshConfiguration)throw Error('UNKNOWN_READONLY_ENTRY_ACTION');
const expected=JSON.parse(fs.readFileSync(path.join(task,kind+'-ui-submission.json'),'utf8')).request;
const output=path.join(task,kind+'-ui-readonly-'+label+'.json');if(fs.existsSync(output))throw Error('OBSERVATION_ALREADY_EXISTS');
const catalogue='/release-center/api/applications/intruoyi/package-catalog';
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const savedState=JSON.parse(fs.readFileSync(priv+'/spug-active-session.private.json','utf8'));
 const context=await browser.newContext({viewport:{width:1440,height:1080}});
 await context.addCookies(savedState.cookies);
 await context.addInitScript(({origins})=>{const saved=origins.find(v=>v.origin===location.origin);if(saved)for(const item of saved.localStorage)localStorage.setItem(item.name,item.value);},{origins:savedState.origins});
 const page=await context.newPage();page.setDefaultTimeout(45000);
 const out={startedAt:new Date().toISOString(),operationId:expected.operationId,realBrowser:true,businessWrites:0,phase,observation,httpObservations:[],pageErrors:[]};
 let latest=null;const pending=[];
 page.on('pageerror',e=>out.pageErrors.push(String(e)));
 await page.route('**/*',async route=>{
  if(['GET','HEAD','OPTIONS'].includes(route.request().method()))return route.continue();
  out.businessWrites++;return route.abort('blockedbyclient');
 });
 page.on('response',r=>{
  const endpoint=new URL(r.url()).pathname;
  if([catalogue,'/backup-entry-api/operations/'+expected.operationId,'/backup-entry-api/progress/'+expected.operationId].includes(endpoint)){
   pending.push((async()=>{
    out.httpObservations.push({endpoint,httpStatus:r.status(),observedAt:new Date().toISOString()});
    const raw=await r.body();
    fs.writeFileSync(priv+'/'+kind+'-'+label+'-'+(endpoint===catalogue?'catalogue':endpoint.includes('/progress/')?'progress':'operation')+(r.ok()?'.private.json':'.original-http-body'),raw);
    if(endpoint==='/backup-entry-api/operations/'+expected.operationId)latest=JSON.parse(raw);
   })());
  }
 });
 try{
  const cat=page.waitForResponse(r=>new URL(r.url()).pathname===catalogue,{timeout:150000});
  const navigation=await page.goto('http://127.0.0.1:18080/backup-restore/',{waitUntil:'commit'});
  if(navigation.status()!==200)throw Error('SPUG_BACKUP_DOCUMENT_HTTP_FAILED');
  if(refreshConfiguration){
   await page.waitForFunction(()=>typeof simpleInitializing!=='undefined'&&!simpleInitializing,null,{timeout:120000});
   out.configurationRefresh={beforeProblem:await page.locator('#problem').textContent(),clickedAt:new Date().toISOString()};
   await page.getByRole('button',{name:'刷新配置',exact:true}).click();
  }
  await page.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:120000});
  out.backupPageInitialized=true;
  await page.locator('#simple-history-tab').click();
  const row=page.locator('#simple-history .history-row').filter({hasText:expected.operationId});
  await row.waitFor();out.exactHistoryRowCount=await row.count();if(out.exactHistoryRowCount!==1)throw Error('HISTORY_ID_NOT_UNIQUE');
  await row.getByRole('button',{name:'查看进度',exact:true}).click();
  await page.locator('#simple-progress-tab').click();
  await page.waitForFunction(id=>document.querySelector('#operation-reference')?.textContent===id&&!document.querySelector('#simple-query').disabled,expected.operationId);
  const state=page.waitForResponse(r=>new URL(r.url()).pathname==='/backup-entry-api/operations/'+expected.operationId,{timeout:90000});
  await page.locator('#simple-query').click();await state;
  const catResponse=await cat;out.catalogueHttp=catResponse.status();
  await page.waitForTimeout(3000);await Promise.all(pending.splice(0));
  if(!latest||JSON.stringify(latest.request)!==JSON.stringify(expected)){
   if(!latest||Object.keys(expected).some(k=>latest.request?.[k]!==expected[k]))throw Error('REQUEST_CHANGED');
  }
  out.request=latest.request;out.spugHistoryId=latest.spugHistoryId;out.state=latest.result?.state;out.queryError=latest.queryError;
  out.problem=await page.locator('#problem').textContent();out.steps=await page.locator('#steps').innerText();out.visible=await page.locator('#simple-result').innerText();
  out.logs=await page.locator('#simple-logs').innerText();
  if(out.logs.includes('步骤日志读取失败')||out.logs.includes('ENTRY_REQUEST_TIMEOUT'))throw Error('VISIBLE_LOG_QUERY_FAILED');
  if(out.businessWrites||out.pageErrors.length||out.catalogueHttp!==200||out.queryError||out.problem||!['RUNNING','SUCCEEDED'].includes(out.state))throw Error('READONLY_UI_NOT_VERIFIED');
  if(phase==='terminal'&&out.state!=='SUCCEEDED')throw Error('ACTUAL_SUCCESS_REQUIRED');
  if(!out.httpObservations.some(r=>r.endpoint==='/backup-entry-api/operations/'+expected.operationId&&r.httpStatus===200))throw Error('ORIGINAL_OPERATION_GET_REQUIRED');
  if(!out.httpObservations.some(r=>r.endpoint==='/backup-entry-api/progress/'+expected.operationId&&r.httpStatus===200))throw Error('PROGRESS_RECOVERY_REQUIRED');
  out.status='PASS';
 }catch(e){out.status='FAIL';out.error=String(e);process.exitCode=1;}
 finally{
  out.observedAt=new Date().toISOString();await page.screenshot({path:path.join(task,kind+'-ui-readonly-'+label+'.png'),fullPage:true});
  fs.writeFileSync(output,JSON.stringify(out,null,2),{encoding:'utf8',flag:'wx'});
  console.log(JSON.stringify(out));await browser.close();
 }
})().catch(e=>{console.error(String(e));process.exitCode=1;});
