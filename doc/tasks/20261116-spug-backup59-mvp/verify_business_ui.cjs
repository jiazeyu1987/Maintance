// Positive login and read-only pages using the documented private identity.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');const phase=process.argv[2];if(!['full','incremental'].includes(phase))throw Error('PHASE_REQUIRED');const label='59-'+phase;const base='http://127.0.0.1:18089';
(async()=>{
 const credentials=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/loginCredentials.json','utf8').replace(/^\uFEFF/,''));
 const browser=await chromium.launch({channel:'msedge',headless:true});const context=await browser.newContext({viewport:{width:1440,height:1080},serviceWorkers:'block'});const page=await context.newPage();page.setDefaultTimeout(45000);
 const result={label,realBrowser:true,realLogin:false,businessMutations:0,blockedWriteAttempts:0,observedAt:new Date().toISOString()};let permissions=null;const reads=[];
 const prohibitedWrite=r=>!['GET','HEAD','OPTIONS'].includes(r.method())&&!['/admin-api/system/auth/login','/admin-api/system/captcha/get','/admin-api/system/captcha/check'].includes(new URL(r.url()).pathname);
 await context.route('**/*',async route=>{const r=route.request();if(prohibitedWrite(r)){result.blockedWriteAttempts++;(result.blockedPaths??=[]).push(new URL(r.url()).pathname);await route.abort('blockedbyclient');return;}await route.continue();});
 // A request event also fires for an aborted route; only a network response
 // establishes that a prohibited write reached the server.
 context.on('response',response=>{const r=response.request();if(prohibitedWrite(r)){result.businessMutations++;(result.mutationPaths??=[]).push(new URL(r.url()).pathname);}});
 page.on('response',r=>{if(r.url().includes('/system/auth/get-permission-info'))reads.push(r.json().then(v=>{permissions=v;}).catch(e=>{result.permissionReadError=String(e);}));});
 try{
  await page.goto(base+'/login?redirect=/index',{waitUntil:'domcontentloaded'});
  console.log('Restore target login document loaded');
  const tenant=page.locator('.el-form:visible .el-select input');await tenant.waitFor();
  console.log('Restore target login form visible');
  if(await tenant.inputValue()!==credentials.tenantName){await tenant.fill(credentials.tenantName);await tenant.press('Enter');}
  await page.getByPlaceholder('请输入用户名',{exact:true}).fill(credentials.username);
  await page.locator('input[type="password"]:visible').fill(credentials.password);
  const remember=page.getByRole('checkbox',{name:'记住我',exact:true});if(await remember.isChecked())await remember.uncheck();
  const logged=page.waitForResponse(r=>r.url().includes('/system/auth/login')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登录',exact:true}).click();
  const response=await logged;const auth=await response.json();result.loginHttpStatus=response.status();result.loginCode=auth.code;
  console.log('Restore target login response received');
  if(!response.ok()||auth.code!==0)throw Error('LOGIN_REJECTED_CODE_'+auth.code);
  await page.waitForURL(u=>u.pathname!=='/login');await page.locator('.el-menu').first().waitFor({timeout:20000});
  await Promise.all(reads.splice(0));
  if(permissions?.code!==0||permissions?.data?.user?.username!==credentials.username)throw Error('AUTHENTICATED_IDENTITY_NOT_VERIFIED');
  result.realLogin=true;result.authenticatedUser={id:permissions.data.user.id,username:permissions.data.user.username};result.roleCount=permissions.data.roles?.length;result.menuCount=permissions.data.menus?.length;
  {
   await page.getByText('系统管理',{exact:true}).click();
   await page.locator('.el-sub-menu.is-opened').first().waitFor();
   await page.getByRole('menuitem',{name:'用户管理',exact:true}).click();
   await page.locator('.el-table:visible').first().waitFor();
   await page.waitForFunction(()=>document.querySelectorAll('.el-table__body-wrapper tbody tr').length>0&&!document.querySelector('.el-loading-mask:not([style*="display: none"])'));
   result.businessPage={name:'用户管理',url:page.url(),visibleRows:await page.locator('.el-table:visible .el-table__body-wrapper tbody tr').count(),headers:await page.locator('.el-table:visible th').allTextContents()};
   if(result.businessMutations!==0)throw Error('UNEXPECTED_BUSINESS_MUTATION');
  }
  result.url=page.url();result.visible=await page.locator('body').innerText();result.version=result.visible.match(/\b20\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\b/)?.[0];
  if(result.businessPage)result.businessPage.totalRows=Number(result.visible.match(/共\s*(\d+)\s*条/)?.[1]);
  await page.screenshot({path:path.join(result.businessPage?'C:/Spug/runtime/private/spug-backup59-mvp-20261116':__dirname,'target-'+label+'-business.png'),fullPage:true});
  result.status='PASS';
 }catch(e){result.status='FAIL';result.error=String(e).replaceAll(credentials.password,'<redacted>');try{result.visible=await page.locator('body').innerText({timeout:3000});}catch(readError){result.bodyReadError=String(readError);}process.exitCode=1;}
 finally{fs.writeFileSync(path.join('C:/Spug/runtime/private/spug-backup59-mvp-20261116','target-'+label+'-business.private.json'),JSON.stringify(result,null,2),'utf8');delete result.visible;fs.writeFileSync(path.join(__dirname,'target-'+label+'-business.json'),JSON.stringify(result,null,2),'utf8');console.log(JSON.stringify({label,status:result.status,realLogin:result.realLogin,businessMutations:result.businessMutations,blockedWriteAttempts:result.blockedWriteAttempts,businessPage:result.businessPage,version:result.version,error:result.error}));await browser.close();}
})().catch(e=>{console.error(String(e));process.exitCode=1;});
