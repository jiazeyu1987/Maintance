const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const [environment,tag,commit,explicitOrigin]=process.argv.slice(2);
if(!['test','prod','prod-maintenance'].includes(environment)||! /^[0-9a-f]{40}$/.test(commit))throw Error('EXPLICIT_TARGET_REQUIRED');if(!/^\d{4}-\d{2}-\d{2}-\d\d-\d\d-\d\d$/.test(tag||''))throw Error('EXPLICIT_RELEASE_TAG_REQUIRED');
const creds=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/loginCredentials.json','utf8').replace(/^\uFEFF/,''));
if(creds.tenantName!=='芋道源码'||creds.username!=='admin')throw Error('APPROVED_IDENTITY_REQUIRED');
const host=environment==='test'?'172.30.30.58':'172.30.30.57';
const base=explicitOrigin||'http://'+host+':8081';if(new URL(base).hostname!==host)throw Error('TARGET_HOST_MISMATCH');
const out=path.join('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125',environment);fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const context=await browser.newContext({viewport:{width:1500,height:1100},serviceWorkers:'block'});
 const page=await context.newPage();page.setDefaultTimeout(30000);
 const result={environment,releaseTag:tag,startedAt:new Date().toISOString(),checks:[],observations:[],status:'BLOCKED'};
 const allowed=new Set(['/admin-api/system/auth/login','/admin-api/system/captcha/get','/admin-api/system/captcha/check']);
 await context.route('**/*',async route=>{const req=route.request(),u=new URL(req.url());if(!['GET','HEAD','OPTIONS'].includes(req.method())&&!allowed.has(u.pathname)){result.observations.push({kind:'interception',path:u.pathname,method:req.method(),reason:'predeclared read-only boundary'});await route.abort('blockedbyclient');return;}await route.continue();});
 page.on('console',m=>{if(m.type()==='error')result.observations.push({kind:'console',message:m.text(),location:m.location()});});
 page.on('pageerror',e=>result.observations.push({kind:'pageerror',message:String(e)}));
 page.on('requestfailed',r=>result.observations.push({kind:'requestfailed',path:new URL(r.url()).origin+new URL(r.url()).pathname,error:r.failure()?.errorText}));
 let permissions,releaseInfo;const reads=[];
 page.on('response',r=>{const u=new URL(r.url());if(r.status()>=400)result.observations.push({kind:'http',path:u.pathname,status:r.status()});
  if(u.pathname.endsWith('/system/auth/get-permission-info'))reads.push(r.json().then(x=>permissions=x));
  if(u.pathname.endsWith('/release-info.json'))reads.push(r.json().then(x=>releaseInfo=x));
  if(u.pathname.startsWith('/admin-api/')&&r.headers()['content-type']?.includes('json'))reads.push(r.json().then(x=>{if(x.code!==undefined&&x.code!==0&&x.code!==200)result.observations.push({kind:'business',path:u.pathname,code:x.code,message:x.msg});}).catch(e=>result.observations.push({kind:'response-read',path:u.pathname,error:String(e)})));
 });
 try{
  await page.goto(base+'/login?redirect=/index',{waitUntil:'networkidle'});
  await page.locator('.el-form:visible .el-select input').fill(creds.tenantName);await page.getByRole('option',{name:creds.tenantName,exact:true}).click();
  await page.getByPlaceholder('请输入用户名',{exact:true}).fill(creds.username);await page.locator('input[type=password]:visible').fill(creds.password);
  const remember=page.getByRole('checkbox',{name:'记住我',exact:true});if(await remember.isChecked())await remember.uncheck();
  const login=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/system/auth/login')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登录',exact:true}).click();if((await(await login).json()).code!==0)throw Error('LOGIN_REJECTED');
  await page.waitForURL(u=>u.pathname!='/login');await page.locator('.el-menu').first().waitFor();await Promise.all(reads);
  if(permissions?.data?.user?.username!==creds.username)throw Error('IDENTITY_UNVERIFIED');
  result.checks.push({name:'real-login',status:'PASS'});
  const menu=page.locator('.el-menu').first();const root=menu.getByText('智能排产',{exact:true}).first();await root.click();
  const target=menu.getByText('排产工单',{exact:true});await target.waitFor({state:'visible'});
  const orders=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/mes/pro/schedule-order/page')&&r.request().method()==='GET');
  const latest=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/mes/pro/auto-schedule/apply/latest-success')&&r.request().method()==='GET');
  await target.click();await page.waitForURL(u=>u.pathname==='/mes/pro/schedule-order');await page.locator('.schedule-order-pool').waitFor();
  const response=await orders,body=await response.json();if(!response.ok()||body.code!==0||!Array.isArray(body.data?.list))throw Error('SCHEDULE_ORDER_READ_FAILED');
  const latestResponse=await latest,latestData=await latestResponse.json();if(!latestResponse.ok()||latestData.code!==0)throw Error('LATEST_SCHEDULE_READ_FAILED');
  await page.waitForFunction(()=>{const e=document.querySelector('.schedule-order-pool__last-success-time strong');return e&&e.textContent!=='加载中'});
  await page.waitForLoadState('networkidle');result.checks.push({name:'menu-navigation-and-real-data',status:'PASS',path:new URL(page.url()).pathname,total:body.data.total,rows:body.data.list.length,latestStatus:latestData.code});
  const dock=page.getByTestId('release-info-dock').getByRole('button');if((await dock.innerText()).trim()!==tag)throw Error('PAGE_RELEASE_TAG_MISMATCH');
  await dock.click();const dialog=page.locator('.el-dialog:visible');await dialog.getByText('版本变更说明',{exact:true}).waitFor();
  const changes=await dialog.locator('.release-info-dialog li').allTextContents();if(!changes.length)throw Error('CHANGELOG_EMPTY');
  await Promise.all(reads);if(releaseInfo?.releaseTag!==tag||releaseInfo?.sourceCommit!==commit)throw Error('RELEASE_INFO_MISMATCH');
  result.checks.push({name:'page-version-and-changelog',status:'PASS',releaseTag:releaseInfo.releaseTag,sourceCommit:releaseInfo.sourceCommit,changes});
  result.permissionMenus=permissions.data.menus;result.status=result.observations.length?'NEEDS_REVIEW':'PASS';
 }catch(e){result.error=String(e).replaceAll(creds.password,'<redacted>');process.exitCode=1;}
 finally{
  result.endedAt=new Date().toISOString();result.body=await page.locator('body').innerText().catch(()=>'<unavailable>');
  await page.screenshot({path:path.join(out,'menu-page.private.png'),fullPage:true,animations:'disabled'}).catch(()=>{});
  fs.writeFileSync(path.join(out,'menu-page.private.json'),JSON.stringify(result,null,2),'utf8');
  console.log(JSON.stringify({status:result.status,checks:result.checks,observations:result.observations.length,error:result.error}));await browser.close();
 }
})().catch(e=>{console.error(String(e).replaceAll(creds.password,'<redacted>'));process.exitCode=1;});
