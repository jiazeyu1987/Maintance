// Read-only browser acceptance. Run only after the parent confirms restore success.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root='C:/Spug/runtime/private/spug-backup59-mvp-20261116';
const base='http://127.0.0.1:18089';
const phase=process.argv[2];
if(!['full','incremental'].includes(phase))throw Error('PHASE_REQUIRED');
const readJson=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const urlPath=u=>decodeURIComponent(new URL(u).pathname);
const allowedPosts=new Set(['/admin-api/system/auth/login','/admin-api/system/captcha/get','/admin-api/system/captcha/check']);

(async()=>{
 const credentials=readJson('C:/SpugHandoff/release/private/loginCredentials.json');
 const baseline=readJson(path.join(root,'full3c2395-acceptance-baseline.private.json'));
 if(baseline.attachmentSamples?.length!==3)throw Error('THREE_BASELINE_SAMPLES_REQUIRED');
 const samples=baseline.attachmentSamples;
 const profile=fs.mkdtempSync(path.join(root,`attachment-browser-${phase}-`));
 fs.mkdirSync(path.join(profile,'Default'));
 fs.writeFileSync(path.join(profile,'Default','Preferences'),JSON.stringify({plugins:{always_open_pdf_externally:true}}),'utf8');
 const context=await chromium.launchPersistentContext(profile,{channel:'msedge',headless:true,
  viewport:{width:1440,height:1080},acceptDownloads:true,serviceWorkers:'block'});
 const page=context.pages()[0]??await context.newPage();page.setDefaultTimeout(45000);
 const result={phase,realBrowser:true,realLogin:false,businessMutations:0,blockedWriteAttempts:0,status:'FAIL',
  observedAt:new Date().toISOString(),origin:base,baselineRecoveryPoint:baseline.recoveryPoint,attachments:[],pageErrors:[]};
 const observations=[],pending=[],downloads=[];
 let permissions=null;
 const matching=u=>samples.find(s=>urlPath(u)===s.frontendPath);
 function watchPage(p){
  p.on('pageerror',e=>result.pageErrors.push(e.message));
  p.on('download',d=>{
   const work=(async()=>{
    const sample=matching(d.url());if(!sample)throw Error('UNEXPECTED_ATTACHMENT_DOWNLOAD');
    if(new URL(d.url()).origin!==base)throw Error('ATTACHMENT_DOWNLOAD_ORIGIN_MISMATCH');
    const saved=path.join(root,`target-59-${phase}-attachment-${sample.recordId}.download`);
    await d.saveAs(saved);const bytes=fs.readFileSync(saved);
    if(/\.pdf$/i.test(sample.databasePath)&&bytes.subarray(0,5).toString('ascii')!=='%PDF-')throw Error('DOWNLOADED_PDF_SIGNATURE_MISMATCH');
    downloads.push({recordId:sample.recordId,url:d.url(),origin:new URL(d.url()).origin,bytes:bytes.length,sha256:hash(bytes),evidenceKind:'browser-download'});
   })().catch(e=>{result.downloadError=String(e);});
   pending.push(work);
  });
 }
 watchPage(page);context.on('page',watchPage);
 await context.route('**/*',async route=>{
  const r=route.request(),u=new URL(r.url());
  if((u.pathname.includes('/admin-api/')||matching(r.url()))&&u.origin!==base){
   result.originViolation=true;await route.abort('blockedbyclient');return;
  }
  if(!['GET','HEAD','OPTIONS'].includes(r.method())&&!allowedPosts.has(u.pathname)){
   result.blockedWriteAttempts++;(result.blockedPaths??=[]).push(u.pathname);await route.abort('blockedbyclient');return;
  }
  await route.continue();
 });
 context.on('response',r=>{
  if(!['GET','HEAD','OPTIONS'].includes(r.request().method())&&!allowedPosts.has(new URL(r.url()).pathname)){
   result.businessMutations++;(result.mutationPaths??=[]).push(new URL(r.url()).pathname);
  }
  if(new URL(r.url()).pathname.endsWith('/system/auth/get-permission-info')){
   pending.push(r.json().then(v=>{permissions=v;}).catch(e=>{result.permissionReadError=String(e);}));
  }
  const sample=matching(r.url());if(!sample)return;
  const item={recordId:sample.recordId,url:r.url(),origin:new URL(r.url()).origin,status:r.status(),
   contentRange:r.headers()['content-range']??null};observations.push(item);
  // Download navigation has no readable Playwright response body. PDF bytes
  // come exclusively from the completed native download above.
  if(/\.(jpg|jpeg|png)$/i.test(sample.databasePath)){
   pending.push(r.body().then(bytes=>{item.bytes=bytes.length;item.sha256=hash(bytes);})
    .catch(e=>{item.bodyReadError=String(e);}));
  }
 });
 try{
  await page.goto(base+'/login?redirect=/index',{waitUntil:'domcontentloaded'});
  const tenant=page.locator('.el-form:visible .el-select input');await tenant.waitFor();
  if(await tenant.inputValue()!==credentials.tenantName){await tenant.fill(credentials.tenantName);await tenant.press('Enter');}
  await page.getByPlaceholder('请输入用户名',{exact:true}).fill(credentials.username);
  await page.locator('input[type="password"]:visible').fill(credentials.password);
  const remember=page.getByRole('checkbox',{name:'记住我',exact:true});if(await remember.isChecked())await remember.uncheck();
  const logged=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/system/auth/login')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登录',exact:true}).click();
  const response=await logged,auth=await response.json();
  if(!response.ok()||auth.code!==0)throw Error('LOGIN_REJECTED');
  await page.waitForURL(u=>u.origin===base&&u.pathname!=='/login');
  await page.locator('.el-menu').first().waitFor({timeout:20000});await Promise.all(pending.splice(0));
  if(permissions?.code!==0||permissions?.data?.user?.username!==credentials.username)throw Error('AUTHENTICATED_IDENTITY_NOT_VERIFIED');
  result.realLogin=true;
  console.log('Attachment acceptance: login verified');
  await page.goto(base+'/infra/file/file',{waitUntil:'domcontentloaded'});
  const search=page.getByPlaceholder('请输入文件路径',{exact:true});await search.waitFor();
  for(const sample of samples){
   console.log(`Attachment acceptance: searching record ${sample.recordId}`);
   const listResponse=page.waitForResponse(r=>{
    const u=new URL(r.url());return u.pathname.endsWith('/infra/file/page')&&u.searchParams.get('path')===sample.databasePath;
   });
   await search.fill(sample.databasePath);await page.getByRole('button',{name:'搜索',exact:true}).click();
   const list=await listResponse,payload=await list.json();
   if(!list.ok()||payload.code!==0)throw Error('FILE_SEARCH_FAILED');
   const matchingRows=payload.data?.list?.filter(r=>String(r.id)===sample.recordId&&r.path===sample.databasePath);
   if(matchingRows?.length!==1)throw Error('BASELINE_FILE_RECORD_MISSING_OR_AMBIGUOUS');
   const data=matchingRows[0],attachmentUrl=new URL(data.url,base);
   if(attachmentUrl.origin!==base||urlPath(attachmentUrl.href)!==sample.frontendPath)throw Error('FILE_RECORD_TARGET_URL_MISMATCH');
   if(String(data.configId)!==sample.configId)throw Error('FILE_CONFIG_MISMATCH');
   // Distinct file records can share a path. Bind the rendered row to the
   // exact record ID in this search response, preserving its actual list order.
   const recordIndex=payload.data.list.findIndex(r=>String(r.id)===sample.recordId);
   const rows=page.locator('.el-table__body-wrapper tr.el-table__row');
   await rows.first().waitFor();
   if(await rows.count()!==payload.data.list.length)throw Error('FILE_UI_ROW_COUNT_MISMATCH');
   const row=rows.nth(recordIndex);
   if(!(await row.innerText()).includes(sample.databasePath))throw Error('FILE_UI_ROW_BINDING_MISMATCH');
   await row.scrollIntoViewIfNeeded();
   const isImage=/\.(jpg|jpeg|png)$/i.test(sample.databasePath);
   if(isImage){
    const img=row.locator('.el-image img');await img.waitFor();
    const src=await img.getAttribute('src');if(new URL(src,base).href!==attachmentUrl.href)throw Error('IMAGE_UI_URL_MISMATCH');
    await img.click();await page.locator('.el-image-viewer__wrapper').waitFor();
   }else{
    const link=row.getByRole('link',{name:'预览',exact:true});
    if(new URL(await link.getAttribute('href'),base).href!==attachmentUrl.href)throw Error('PREVIEW_UI_URL_MISMATCH');
    await link.click();
   }
   // Observe only bytes requested by the page or its real preview/download.
   const deadline=Date.now()+45000;let evidence;
   while(Date.now()<deadline){
    await Promise.all(pending.splice(0));
    const candidate=isImage&&observations.find(o=>o.recordId===sample.recordId&&o.status===200&&o.origin===base&&o.bytes===sample.bytes&&o.sha256===sample.sha256);
    const download=downloads.find(o=>o.recordId===sample.recordId&&o.bytes===sample.bytes&&o.sha256===sample.sha256);
    const downloadResponse=download&&observations.find(o=>o.recordId===sample.recordId&&o.status===200&&o.origin===base);
    if(candidate||download){evidence=candidate?{...candidate,evidenceKind:'browser-response'}:{status:downloadResponse?.status??null,...download};break;}
    if(result.downloadError||result.originViolation)throw Error('ATTACHMENT_BROWSER_REQUEST_FAILED');
    await page.waitForTimeout(200);
   }
   if(!evidence)throw Error('ATTACHMENT_BYTES_OR_HASH_NOT_VERIFIED');
   result.attachments.push({recordId:sample.recordId,origin:evidence.origin,status:evidence.status,bytes:evidence.bytes,sha256:evidence.sha256,evidenceKind:evidence.evidenceKind,openedViaUI:true,passed:true});
   console.log(`Attachment acceptance: record ${sample.recordId} bytes and SHA verified via ${evidence.evidenceKind}`);
   if(isImage)await page.locator('.el-image-viewer__close').click();
   // Edge creates its own downloads-hub page. Its Page.close protocol request
   // does not settle; close only actual web previews, then close the context.
   for(const popup of context.pages())if(popup!==page&&/^https?:/.test(popup.url()))await popup.close();
  }
  if(result.businessMutations||result.originViolation||result.pageErrors.length)throw Error('READ_ONLY_BROWSER_ACCEPTANCE_FAILED');
  await page.screenshot({path:path.join(root,`target-59-${phase}-attachments.png`),fullPage:true});
  result.status='PASS';
 }catch(e){result.error=String(e).replaceAll(credentials.password,'<redacted>');process.exitCode=1;}
 finally{
  result.observations=observations;result.downloads=downloads;result.browserProfile=profile;result.finishedAt=new Date().toISOString();
  fs.writeFileSync(path.join(root,`target-59-${phase}-attachments.private.json`),JSON.stringify(result,null,2),'utf8');
  const summary={phase,status:result.status,realLogin:result.realLogin,businessMutations:result.businessMutations,blockedWriteAttempts:result.blockedWriteAttempts,
   passedAttachments:result.attachments.length,expectedAttachments:3,origin:base,error:result.error};
  fs.writeFileSync(path.join(__dirname,`target-59-${phase}-attachments.json`),JSON.stringify(summary,null,2),'utf8');
  console.log(JSON.stringify(summary));await context.close();console.log('Attachment acceptance: browser closed');
 }
})().catch(e=>{console.error(String(e));process.exitCode=1;});
