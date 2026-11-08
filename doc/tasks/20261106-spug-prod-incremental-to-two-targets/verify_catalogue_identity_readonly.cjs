// Actual UI only; one explicit authentication POST, no business write or direct fetch.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const TASK=__dirname,PRIVATE='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106';
const ORIGIN='http://127.0.0.1:18080',CATALOGUE='/release-center/api/applications/intruoyi/package-catalog';
const need=(value,code)=>{if(!value)throw Error(code);};
function classifyLoginContract(status,body){
 need(status===200&&body&&typeof body==='object'&&!body.error,'REAL_LOGIN_REJECTED');
 const data=body.data;
 need(data&&typeof data==='object'&&!Array.isArray(data),'REAL_LOGIN_SUCCESS_DATA_INVALID');
 need(!data.required_mfa,'REAL_LOGIN_MFA_REQUIRED');
 need(typeof data.access_token==='string'&&data.access_token.length>0&&typeof data.has_real_ip==='boolean','REAL_LOGIN_SUCCESS_DATA_INVALID');
 return {needsNotice:!data.has_real_ip};
}
function catalogueRequestPolicy(method,address,authPosts){
 const url=new URL(address);
 if(url.origin!==ORIGIN)return 'blocked';
 if(['GET','HEAD','OPTIONS'].includes(method))return 'readonly';
 if(method==='POST'&&url.pathname==='/api/account/login/'&&!url.search&&authPosts===0)return 'authentication';
 return 'blocked';
}
async function waitForBackupDocument(frame){
 await frame.waitForURL(ORIGIN+'/backup-restore/?embedded=1',{waitUntil:'domcontentloaded',timeout:45000});
 const address=new URL(frame.url());
 need(address.origin===ORIGIN&&address.pathname==='/backup-restore/'&&address.search==='?embedded=1','BACKUP_DOCUMENT_IDENTITY_REQUIRED');
}
const installedPath=path.join(TASK,'catalogue-identity-installation.json');
const installedRaw=fs.readFileSync(installedPath),installed=JSON.parse(installedRaw);
need(process.argv.length===5&&process.argv[2]==='--observation'&&process.argv[4]==='--login','EXPLICIT_OBSERVATION_AND_REAL_LOGIN_REQUIRED');
const observation=process.argv[3];
need(/^r(?:[3-9]|[1-9][0-9]+)$/.test(observation),'INVALID_OBSERVATION_SEQUENCE');
const ordinal=Number(observation.slice(1));
const output=path.join(TASK,'catalogue-identity-readonly-verification-'+observation+'.json');
const filePin=file=>{const raw=fs.readFileSync(path.join(TASK,file));return {file,bytes:raw.length,sha256:crypto.createHash('sha256').update(raw).digest('hex')};};
const failed=[];
for(let index=1;index<ordinal;index++){
 const file='catalogue-identity-readonly-verification'+(index===1?'':'-r'+index)+'.json';
 const previous=JSON.parse(fs.readFileSync(path.join(TASK,file),'utf8'));
 need(previous.status==='FAIL'&&previous.businessWrites===0,'PREVIOUS_FAILED_OBSERVATION_REQUIRED');failed.push(filePin(file));
}
const selectionPath=path.join(TASK,'catalogue-identity-readonly-selection.json');
need(!fs.existsSync(selectionPath),'SUCCESSFUL_OBSERVATION_ALREADY_SELECTED');
need(installed.schemaVersion==='CatalogueIdentityInstallation/v1'&&installed.status==='PASS','ACTUAL_CATALOGUE_INSTALLATION_REQUIRED');
need(!fs.existsSync(output),'ORIGINAL_UI_OBSERVATION_ALREADY_EXISTS');
const receipt=path.join(TASK,'catalogue-identity-readonly-attempt-'+observation+'.json');
const began=new Date().toISOString();
fs.writeFileSync(receipt,JSON.stringify({schemaVersion:'CatalogueReadonlyAttempt/v1',startedAt:began,observation,authentication:'fresh-real-ui-login',sourceCommit:installed.sourceCommit,
 retainedFailedObservationPins:failed,
 installationPin:{file:path.basename(installedPath),bytes:installedRaw.length,sha256:crypto.createHash('sha256').update(installedRaw).digest('hex')}},null,2),{encoding:'utf8',flag:'wx'});
const privateDir=path.join(PRIVATE,'catalogue-readonly-'+began.replace(/[:.]/g,'-'));
fs.mkdirSync(privateDir,{recursive:false});
(async()=>{
 const report={schemaVersion:'CatalogueIdentityReadonlyUi/v1',startedAt:began,observation,authentication:'fresh-real-ui-login',sourceCommit:installed.sourceCommit,
  realBrowser:true,actualPageRequest:false,businessWrites:0,authPosts:0,blockedRequests:[],identityVerified:false,pageErrors:[],httpObservations:[]};
 let browser,page,frame,latest=null,sequence=0,refreshAt=null,finished=false;
 const pending=[],failures=[];
 const observe=async response=>{
  const url=new URL(response.url());
  if(url.origin!==ORIGIN||url.pathname!==CATALOGUE)return;
  const number=++sequence,observedAt=new Date().toISOString(),raw=await response.body();
  fs.writeFileSync(path.join(privateDir,'catalogue-'+number+'.private.json'),raw,{flag:'wx'});
  const data=JSON.parse(raw);
  const row={sequence:number,httpStatus:response.status(),observedAt,method:response.request().method(),
   refresh:url.searchParams.get('refresh')==='1',bytes:raw.length,sha256:crypto.createHash('sha256').update(raw).digest('hex'),
   itemCount:Array.isArray(data.items)?data.items.length:null,refreshing:data.refreshing,complete:data.complete};
  report.httpObservations.push(row);
  need(response.request().method()==='GET','CATALOGUE_PAGE_GET_REQUIRED');
  need(response.status()===200&&data.schemaVersion==='PackageCatalog/v1'&&Array.isArray(data.items),'CATALOGUE_HTTP_CONTRACT_FAILED');
  latest={row,data};
 };
 try{
  browser=await chromium.launch({channel:'chrome',headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1080}});
  page=await context.newPage();page.setDefaultTimeout(45000);
  page.on('pageerror',error=>report.pageErrors.push(String(error)));
  await page.route('**/*',async route=>{
   const request=route.request(),policy=catalogueRequestPolicy(request.method(),request.url(),report.authPosts);
   if(policy==='readonly')return route.continue();
   if(policy==='authentication'){report.authPosts++;return route.continue();}
   report.blockedRequests.push({method:request.method(),pathname:new URL(request.url()).pathname});
   if(!['GET','HEAD','OPTIONS'].includes(request.method()))report.businessWrites++;
   return route.abort('blockedbyclient');
  });
  page.on('response',response=>{
   const url=new URL(response.url());
   if(url.origin===ORIGIN&&url.pathname==='/backup-restore/'&&response.request().resourceType()==='document')report.documentHttpStatus=response.status();
   if(!finished)pending.push(observe(response).catch(error=>failures.push(String(error))));
  });
  report.stage='real-login-page';
  const shell=await page.goto(ORIGIN+'/',{waitUntil:'domcontentloaded',timeout:60000});
  need(shell.status()===200,'PLATFORM_DOCUMENT_NOT_200');
  await page.getByPlaceholder('请输入账户').waitFor({state:'visible'});
  const credential=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
  need(typeof credential.username==='string'&&typeof credential.password==='string','PRIVATE_LOGIN_CREDENTIALS_INVALID');
  await page.getByPlaceholder('请输入账户').fill(credential.username);
  await page.getByPlaceholder('请输入密码').fill(credential.password);
  const login=page.waitForResponse(response=>new URL(response.url()).origin===ORIGIN&&new URL(response.url()).pathname==='/api/account/login/'&&response.request().method()==='POST',{timeout:45000});
  await page.getByRole('button',{name:'登 录',exact:true}).click();
  report.stage='login-response-contract';
  const response=await login,raw=await response.text();
  fs.writeFileSync(path.join(privateDir,'login-response.private.json'),JSON.stringify({observedAt:new Date().toISOString(),httpStatus:response.status(),body:raw},null,2),{encoding:'utf8',flag:'wx'});
  report.loginResponseRecorded=true;
  let body;try{body=JSON.parse(raw);}catch{need(false,'REAL_LOGIN_RESPONSE_JSON_INVALID');}
  const loginData=body?.data;
  report.loginShape={httpStatus:response.status(),errorPresent:Boolean(body?.error),dataPresent:Object.hasOwn(body||{},'data'),
   dataObject:Boolean(loginData&&typeof loginData==='object'&&!Array.isArray(loginData)),requiredMfa:Boolean(loginData?.required_mfa),
   hasRealIp:typeof loginData?.has_real_ip==='boolean'?loginData.has_real_ip:null,tokenReturned:typeof loginData?.access_token==='string'&&loginData.access_token.length>0};
  const contract=classifyLoginContract(response.status(),body);
  if(contract.needsNotice){
   report.stage='login-security-notice';const notice=page.getByRole('button',{name:'知道了',exact:true});
   await notice.waitFor({state:'visible'});await notice.click();await notice.waitFor({state:'hidden'});report.loginNoticeConfirmed=true;
  }
  report.stage='login-token-stored';await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));
  need(report.authPosts===1,'ONE_REAL_AUTHENTICATION_REQUIRED');
  report.stage='authenticated-nickname';
  await page.getByText('管理员',{exact:true}).first().waitFor({state:'visible'});
  report.stage='authenticated-backup-menu';const menu=page.getByText('备份与恢复',{exact:true}).first();await menu.waitFor({state:'visible'});
  report.identityVerified=true;await menu.click();await page.waitForURL(ORIGIN+'/backup-center');
  const handle=await page.locator('iframe[src="/backup-restore/?embedded=1"]').elementHandle();
  need(handle,'BACKUP_IFRAME_REQUIRED');frame=await handle.contentFrame();need(frame,'BACKUP_IFRAME_UNAVAILABLE');
  report.stage='backup-document-navigation';await waitForBackupDocument(frame);
  need(report.documentHttpStatus===200,'BACKUP_DOCUMENT_HTTP_NOT_200');
  report.stage='initialized-backup-page';
  await frame.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:120000});
  report.backupPageInitialized=true;
  await frame.locator('#simple-catalog-tab').click();await frame.locator('#package-catalog').waitFor({state:'visible'});
  await frame.waitForFunction(()=>!document.querySelector('#catalog-refresh').disabled,null,{timeout:120000});
  refreshAt=new Date().toISOString();report.refreshClickedAt=refreshAt;report.stage='completed-real-catalogue';
  await frame.locator('#catalog-refresh').click();
  const deadline=Date.now()+180000;
  while(Date.now()<deadline){
   await Promise.all(pending.splice(0));need(!failures.length,'CATALOGUE_RESPONSE_PROCESSING_FAILED');
   if(latest&&latest.row.observedAt>=refreshAt&&latest.data.refreshing===false)break;
   await page.waitForTimeout(500);
  }
  need(latest&&latest.row.observedAt>=refreshAt,'POST_CLICK_CATALOGUE_RESPONSE_REQUIRED');
  const {data,row}=latest;
  need(data.refreshing===false&&data.complete===true&&data.items.length>0&&!(data.errors||[]).length,'COMPLETE_NONEMPTY_CATALOGUE_REQUIRED');
  await frame.waitForFunction(count=>document.querySelector('#catalog-body').children.length>0&&
   document.querySelector('#catalog-count').textContent.startsWith('共 '+count+' 个包')&&!document.querySelector('#catalog-refresh').disabled,data.items.length);
  report.visibleProblem=await frame.locator('#catalog-problem').isVisible()?await frame.locator('#catalog-problem').innerText():'';
  report.visibleRowCount=await frame.locator('#catalog-body tr').count();report.displayedCountText=await frame.locator('#catalog-count').innerText();
  const match=/^共 (\d+) 个包 · 筛选 (\d+) 个 · 第 (\d+) \/ (\d+) 页$/.exec(report.displayedCountText);
  need(match&&Number(match[1])===data.items.length&&Number(match[2])===data.items.length,'VISIBLE_CATALOGUE_COUNT_MISMATCH');
  need(!report.visibleProblem&&!report.businessWrites&&!report.blockedRequests.length&&!report.pageErrors.length&&!failures.length,'READONLY_CATALOGUE_UI_FAILED');
  Object.assign(report,{status:'PASS',actualPageRequest:true,httpStatus:row.httpStatus,itemCount:data.items.length,
   displayedTotal:Number(match[1]),refreshing:data.refreshing,complete:data.complete,catalogueErrors:[],selectedResponse:row});
 }catch(error){report.status='FAIL';report.error=String(error);report.responseErrors=failures;process.exitCode=1;}
 finally{
  finished=true;await Promise.all(pending.splice(0));
  if(failures.length){report.responseErrors=failures;report.status='FAIL';process.exitCode=1;}
  if(page)await page.screenshot({path:path.join(privateDir,'actual-page.png'),fullPage:true}).catch(error=>{report.screenshotError=String(error);report.status='FAIL';process.exitCode=1;});
  report.observedAt=new Date().toISOString();fs.writeFileSync(output,JSON.stringify(report,null,2),{encoding:'utf8',flag:'wx'});
  if(report.status==='PASS'){
   for(const pin of failed)need(JSON.stringify(filePin(pin.file))===JSON.stringify(pin),'ORIGINAL_FAILURE_CHANGED_DURING_OBSERVATION');
   fs.writeFileSync(selectionPath,JSON.stringify({schemaVersion:'TaskCatalogueReadonlySelection/v1',failed,
    selectedPin:filePin(path.basename(output))},null,2),{encoding:'utf8',flag:'wx'});
  }
  console.log(JSON.stringify(report));if(browser)await browser.close();
 }
})().catch(error=>{console.error(String(error));process.exitCode=1;});
