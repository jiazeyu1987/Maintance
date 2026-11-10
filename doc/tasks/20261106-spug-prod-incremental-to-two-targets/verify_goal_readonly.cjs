// Real UI audit. The final execution button is never clicked.
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const TASK=__dirname,PRIVATE='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106';
const ORIGIN='http://127.0.0.1:18080',CATALOGUE='/release-center/api/applications/intruoyi/package-catalog';
const need=(value,code)=>{if(!value)throw Error(code);};
need(process.argv.length===4&&process.argv[2]==='--observation'&&/^r[1-9][0-9]*$/.test(process.argv[3]),'EXPLICIT_OBSERVATION_REQUIRED');
const observation=process.argv[3],output=path.join(TASK,'goal-audit-readonly-'+observation+'.json'),helperRaw=fs.readFileSync(__filename);
need(!fs.existsSync(output),'ORIGINAL_OBSERVATION_ALREADY_EXISTS');
const privateDir=path.join(PRIVATE,'goal-audit-readonly-'+observation);fs.mkdirSync(privateDir,{recursive:false});
const expectedLatest=['smallapp-fbaf12b584214695b6b687e010f4773b','smallapp-ab4fefb2bcfb4c3eb0ae5027fea35da5','smallapp-9d5ed2108497411a81bcd5ba7d1a6291'];
const targets=['172.30.30.57','172.30.30.58','172.30.30.59'];
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const report={schemaVersion:'SpugCompleteGoalReadonlyAudit/v1',startedAt:new Date().toISOString(),observation,
 status:'RUNNING',browserMode:'headedChrome',helperPin:{bytes:helperRaw.length,sha256:sha(helperRaw)},authPosts:0,businessWrites:0,blockedRequests:[],pageErrorCount:0,catalogueResponses:[],pagination:[],filters:[],matrix:[]};
let browser,page,frame,latest,sequence=0,finished=false;const pending=[],responseErrors=[];
function save(name,data){fs.writeFileSync(path.join(privateDir,name),data,{flag:'wx'});}
save('executed-helper.cjs',helperRaw);
function phase(value){report.stage=value;const row={stage:value,observedAt:new Date().toISOString()};save('stage-'+value+'.private.json',JSON.stringify(row));console.log(JSON.stringify(row));}
async function observe(response){
 const url=new URL(response.url());if(url.origin!==ORIGIN||url.pathname!==CATALOGUE)return;
 const number=++sequence,raw=await response.body();save('catalogue-'+number+'.private.json',raw);
 const data=JSON.parse(raw),row={sequence:number,httpStatus:response.status(),observedAt:new Date().toISOString(),bytes:raw.length,sha256:sha(raw),
  itemCount:Array.isArray(data.items)?data.items.length:null,refreshing:data.refreshing,complete:data.complete};
 report.catalogueResponses.push(row);
 need(response.request().method()==='GET'&&response.status()===200&&data.schemaVersion==='PackageCatalog/v1'&&Array.isArray(data.items),'CATALOGUE_RESPONSE_INVALID');
 latest={row,data};
}
async function idle(){await frame.waitForFunction(()=>!simpleInitializing&&!switching&&!busy,null,{timeout:120000});}
async function filter(kind='',query=''){
 await frame.locator('#catalog-filter-open').click();await frame.locator('#catalog-filter-dialog').waitFor({state:'visible'});
 await frame.locator('#catalog-reset').click();await frame.locator('#catalog-kind').selectOption(kind);await frame.locator('#catalog-query').fill(query);
 await frame.locator('#catalog-filter-apply').click();await frame.locator('#catalog-filter-dialog').waitFor({state:'hidden'});
}
async function allVisiblePages(){
 const ids=[],pages=[];
 while(true){
  const rows=await frame.locator('#catalog-body tr[data-package-id]').evaluateAll(nodes=>nodes.map(n=>({id:n.dataset.packageId,kind:n.dataset.kind})));
  const count=await frame.locator('#catalog-count').innerText();pages.push({count,rows});ids.push(...rows.map(r=>r.id));
  if(await frame.locator('#catalog-next').isDisabled())break;
  await frame.locator('#catalog-next').click();
 }
 need(new Set(ids).size===ids.length,'DUPLICATE_VISIBLE_PACKAGE');return {ids,pages};
}
(async()=>{
 try{
  phase('launch-real-browser');browser=await chromium.launch({channel:'chrome',headless:false});phase('create-browser-context');
  const context=await browser.newContext({viewport:{width:1440,height:1080}});page=await context.newPage();page.setDefaultTimeout(45000);phase('real-login');
  page.on('pageerror',error=>{report.pageErrorCount++;save('page-error-'+report.pageErrorCount+'.private.txt',String(error));});
  await page.route('**/*',async route=>{
   const req=route.request(),url=new URL(req.url()),method=req.method();
   if(url.origin===ORIGIN&&['GET','HEAD','OPTIONS'].includes(method))return route.continue();
   if(url.origin===ORIGIN&&method==='POST'&&url.pathname==='/api/account/login/'&&!url.search&&report.authPosts===0){report.authPosts++;save('authentication-post.private.json',JSON.stringify({method,pathname:url.pathname,observedAt:new Date().toISOString()}));return route.continue();}
   report.blockedRequests.push({method,pathname:url.pathname});if(!['GET','HEAD','OPTIONS'].includes(method))report.businessWrites++;
   return route.abort('blockedbyclient');
  });
  page.on('response',response=>{if(!finished)pending.push(observe(response).catch(error=>responseErrors.push(String(error))));});
  const shell=await page.goto(ORIGIN+'/',{waitUntil:'domcontentloaded',timeout:60000});need(shell.status()===200,'SPUG_DOCUMENT_NOT_200');
  await page.getByPlaceholder('请输入账户').waitFor({state:'visible'});
  const credential=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
  need(typeof credential.username==='string'&&typeof credential.password==='string','PRIVATE_LOGIN_INVALID');
  await page.getByPlaceholder('请输入账户').fill(credential.username);await page.getByPlaceholder('请输入密码').fill(credential.password);
  await page.bringToFront();
  report.loginActionability=await page.getByRole('button',{name:'登 录',exact:true}).evaluate(button=>({
   visibilityState:document.visibilityState,documentHasFocus:document.hasFocus(),disabled:button.disabled,
   bounds:button.getBoundingClientRect().toJSON(),display:getComputedStyle(button).display,
   visibility:getComputedStyle(button).visibility,opacity:getComputedStyle(button).opacity,
   activeAnimationCount:document.getAnimations().filter(a=>a.playState==='running').length
  }));save('login-actionability.private.json',JSON.stringify(report.loginActionability));
  phase('submit-real-login');const loginStartedAt=Date.now();
  const [login]=await Promise.all([
   page.waitForResponse(r=>new URL(r.url()).origin===ORIGIN&&new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST',{timeout:180000}),
   page.getByRole('button',{name:'登 录',exact:true}).click()
  ]);
  report.loginResponseMs=Date.now()-loginStartedAt;phase('real-login-response');const loginRaw=await login.body();save('login-response.private.json',loginRaw);
  const body=JSON.parse(loginRaw),data=body?.data;need(login.status()===200&&!body.error&&data&&typeof data.access_token==='string'&&data.access_token.length>0&&!data.required_mfa&&typeof data.has_real_ip==='boolean','REAL_LOGIN_REJECTED');
  if(!data.has_real_ip){const notice=page.getByRole('button',{name:'知道了',exact:true});await notice.waitFor({state:'visible'});await page.bringToFront();await notice.click();await notice.waitFor({state:'hidden'});}
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));await page.getByText('管理员',{exact:true}).first().waitFor({state:'visible'});
  phase('backup-page');await page.getByText('备份与恢复',{exact:true}).first().click();await page.waitForURL(ORIGIN+'/backup-center');
  const handle=await page.locator('iframe[src="/backup-restore/?embedded=1"]').elementHandle();need(handle,'BACKUP_IFRAME_MISSING');frame=await handle.contentFrame();need(frame,'BACKUP_FRAME_MISSING');
  await frame.waitForURL(ORIGIN+'/backup-restore/?embedded=1',{waitUntil:'domcontentloaded',timeout:45000});
  await frame.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:120000});
  await frame.locator('#simple-catalog-tab').click();await frame.locator('#package-catalog').waitFor({state:'visible'});
  await frame.waitForFunction(()=>!document.querySelector('#catalog-refresh').disabled,null,{timeout:120000});
  phase('refresh-complete-catalogue');const refreshAt=new Date().toISOString();await frame.locator('#catalog-refresh').click();const deadline=Date.now()+180000;
  while(Date.now()<deadline){await Promise.all(pending.splice(0));need(!responseErrors.length,'CATALOGUE_RESPONSE_PROCESSING_FAILED');if(latest&&latest.row.observedAt>=refreshAt&&latest.data.refreshing===false)break;await page.waitForTimeout(500);}
  need(latest&&latest.row.observedAt>=refreshAt&&latest.data.complete===true&&latest.data.refreshing===false&&!(latest.data.errors||[]).length,'COMPLETE_FRESH_CATALOGUE_REQUIRED');
  const catalogue=latest.data;report.catalogue={selectedResponse:latest.row,itemCount:catalogue.items.length,
   backups:catalogue.items.filter(r=>['backup-full','backup-incremental'].includes(r.kind)).map(r=>({packageId:r.packageId,kind:r.kind,status:r.status,servers:r.servers,sizeBytes:r.sizeBytes})),sources:catalogue.sources};
  for(const id of expectedLatest)need(catalogue.items.some(r=>r.packageId===id&&r.status==='indexed'),'LATEST_SUCCESS_POINT_MISSING');
  await frame.waitForFunction(n=>document.querySelector('#catalog-count').textContent.startsWith('共 '+n+' 个包')&&!document.querySelector('#catalog-refresh').disabled,catalogue.items.length);
  need(!await frame.locator('#catalog-problem').isVisible(),'CATALOGUE_VISIBLE_PROBLEM');
  phase('all-pages-and-filters');const all=await allVisiblePages();report.pagination=all.pages;
  need(JSON.stringify([...all.ids].sort())===JSON.stringify(catalogue.items.map(r=>r.packageId).sort()),'VISIBLE_CATALOGUE_COVERAGE_FAILED');
  for(const kind of ['backup-full','backup-incremental']){
   await filter(kind);const result=await allVisiblePages(),expected=catalogue.items.filter(r=>r.kind===kind).map(r=>r.packageId).sort();
   report.filters.push({kind,ids:result.ids,pages:result.pages});need(JSON.stringify([...result.ids].sort())===JSON.stringify(expected),'BACKUP_FILTER_COVERAGE_FAILED');
  }
  report.pointFailures=[];report.unpublished=[];
  for(const row of catalogue.items.filter(r=>['backup-full','backup-incremental'].includes(r.kind)&&r.status==='unpublished')){
   await filter('',row.packageId);const actual=frame.locator('#catalog-body tr[data-package-id="'+row.packageId+'"]');
   need(await actual.count()===1&&await actual.getByRole('button',{name:'恢复',exact:true}).isDisabled(),'UNPUBLISHED_POINT_NOT_GUARDED');
   report.unpublished.push({packageId:row.packageId,restoreDisabled:true});
  }
  const eligible=catalogue.items.filter(r=>['backup-full','backup-incremental'].includes(r.kind)&&r.status==='indexed');
  need(eligible.length>=3,'RESTORABLE_POINTS_REQUIRED');
  for(const row of eligible){
   phase('point-'+row.packageId);await filter('',row.packageId);
   const actual=frame.locator('#catalog-body tr[data-package-id="'+row.packageId+'"]');need(await actual.count()===1,'EXACT_CATALOGUE_ROW_REQUIRED');
   const entry=actual.getByRole('button',{name:'恢复',exact:true});need(await entry.isEnabled(),'INDEXED_BACKUP_RESTORE_DISABLED');await entry.click();
   await frame.locator('#catalog-restore-dialog').waitFor({state:'visible'});await idle();
   const chosen=await frame.locator('#simple-package').inputValue();need(chosen===row.packageId,'SELECTED_POINT_IDENTITY_CHANGED');
   const state=await frame.evaluate(()=>{
    const binding=currentBinding();
    return {source:document.querySelector('#simple-server').value,application:document.querySelector('#application').value,
     accepted:[...document.querySelector('#point').options].map(o=>o.value).filter(Boolean),
     binding:binding?{applicationId:binding.applicationId,overwriteTargetServers:binding.overwriteTargetServers}:null};
   });
   const point={packageId:row.packageId,kind:row.kind,source:state.source,accepted:state.accepted.includes(row.packageId),targets:[]};report.matrix.push(point);
   if(!point.accepted){
    point.blockedReason=await frame.locator('#simple-status').innerText();
    report.pointFailures.push({packageId:row.packageId,errorCode:'INDEXED_BACKUP_NOT_ACCEPTED_BY_SOURCE',blockedReason:point.blockedReason});
    save('point-'+report.matrix.length+'.private.json',JSON.stringify(point));
    await frame.locator('#catalog-restore-close').click();await frame.locator('#catalog-restore-dialog').waitFor({state:'hidden'});
    continue;
   }
   const binding=state.binding;need(binding&&binding.applicationId===state.application,'SOURCE_BINDING_IDENTITY_FAILED');
   need(await frame.locator('#simple-restore-mode').inputValue()==='replace','REPLACEMENT_MODE_REQUIRED');
   for(const target of targets){
    const option=frame.locator('#simple-target option[value="'+target+'"]');need(await option.count()===1&&!await option.isDisabled(),'REGISTERED_SERVER_NOT_SELECTABLE');
    await frame.locator('#simple-target').selectOption(target);await idle();
    await frame.locator('#simple-submit').waitFor({state:'visible'});const ready=await frame.locator('#simple-submit').isEnabled();
    const item={server:target,targetConfigRef:binding.overwriteTargetServers?.[target],ready,blockedReason:ready?'':await frame.locator('#simple-status').innerText()};point.targets.push(item);
    if(!ready){report.pointFailures.push({packageId:row.packageId,target,errorCode:'TARGET_ADMISSION_NOT_READY',blockedReason:item.blockedReason});continue;}
    await frame.locator('#simple-submit').click();await frame.locator('#simple-confirm').waitFor({state:'visible'});
    const summary=await frame.locator('#confirm-summary').innerText();need(summary.includes('备份包：'+row.packageId)&&summary.includes('恢复到：')&&summary.includes(target)&&summary.includes('独立目标：'+item.targetConfigRef),'CONFIRMATION_IDENTITY_MISMATCH');
    need(!await frame.locator('#replace-confirm').isChecked()&&await frame.locator('#simple-confirm-submit').isDisabled(),'FINAL_EXECUTION_NOT_GUARDED');
    item.confirmedIdentity=true;item.finalExecutionClicked=false;save('confirmation-'+report.matrix.length+'-'+target.split('.').at(-1)+'.private.txt',summary);
    await frame.locator('#simple-cancel').click();await frame.locator('#simple-confirm').waitFor({state:'hidden'});
   }
   save('point-'+report.matrix.length+'.private.json',JSON.stringify(point));
   await frame.locator('#catalog-restore-close').click();await frame.locator('#catalog-restore-dialog').waitFor({state:'hidden'});
  }
  await Promise.all(pending.splice(0));need(report.authPosts===1&&!report.businessWrites&&!report.blockedRequests.length&&!report.pageErrorCount&&!responseErrors.length,'READONLY_UI_AUDIT_FAILED');
  report.observedIndexedPoints=report.matrix.length;
  report.coveredEligiblePoints=report.matrix.filter(r=>r.accepted&&r.targets.length===3&&r.targets.every(t=>t.confirmedIdentity)).length;
  report.coveredPointTargetPairs=report.matrix.reduce((n,r)=>n+r.targets.filter(t=>t.confirmedIdentity).length,0);
  need(report.observedIndexedPoints===eligible.length,'INDEXED_POINT_OBSERVATION_INCOMPLETE');
  need(!report.pointFailures.length&&report.coveredEligiblePoints===eligible.length,'INCOMPLETE_POINT_TARGET_MATRIX');
  report.status='PASS';
 }catch(error){report.status='FAIL';report.errorCode=error instanceof Error&&/^[A-Z0-9_]+$/.test(error.message)?error.message:'ACTUAL_UI_OBSERVATION_FAILED';save('failure.private.txt',String(error?.stack||error));process.exitCode=1;}
 finally{
  finished=true;await Promise.all(pending.splice(0));if(responseErrors.length){save('response-errors.private.json',JSON.stringify(responseErrors));report.responseErrorCount=responseErrors.length;report.status='FAIL';process.exitCode=1;}
  if(page){try{await page.screenshot({path:path.join(privateDir,'actual-page.png'),fullPage:true});}catch(error){save('screenshot-error.private.txt',String(error));report.status='FAIL';report.screenshotFailed=true;process.exitCode=1;}}
  report.helperInputUnchanged=fs.readFileSync(__filename).equals(helperRaw);if(!report.helperInputUnchanged){report.status='FAIL';report.errorCode='AUDIT_HELPER_INPUT_CHANGED';process.exitCode=1;}
  report.finishedAt=new Date().toISOString();fs.writeFileSync(output,JSON.stringify(report,null,2),{encoding:'utf8',flag:'wx'});
  console.log(JSON.stringify({status:report.status,stage:report.stage,errorCode:report.errorCode,authPosts:report.authPosts,businessWrites:report.businessWrites,coveredEligiblePoints:report.coveredEligiblePoints,coveredPointTargetPairs:report.coveredPointTargetPairs}));if(browser)await browser.close();
 }
})().catch(error=>{console.error('AUDIT_TERMINAL_ERROR');process.exitCode=1;});
