'use strict';
// Real login and rendered entry only. Never click a remote operation.
const fs=require('node:fs');
const assert=require('node:assert/strict');
const {chromium}=require('C:/Users/D01021/Documents/spug-handoff-work-20261030/package/tools/playwright/node_modules/playwright');
const privateRoot='C:/SpugHandoff/release/private/backend-jar-patch-20261102';
let stage='launch';
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1050}});
  const errors=[],requests=[];
  page.on('pageerror',error=>errors.push(error.name));
  page.on('request',request=>requests.push({method:request.method(),url:request.url().split('?')[0]}));
  stage='login page';await page.goto('http://127.0.0.1:18081/');
  const credentials=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8'));
  await page.getByPlaceholder('请输入账户').fill(credentials.username);
  await page.getByPlaceholder('请输入密码').fill(credentials.password);
  stage='login';await page.getByRole('button',{name:'登 录'}).click();
  // The existing Spug local proxy displays an informational source-IP modal.
  // Acknowledge it in the real UI; do not change its security settings.
  stage='login source-IP notice';const warning=page.getByRole('button',{name:'知道了'});
  await Promise.race([warning.waitFor({state:'visible',timeout:15000}).then(()=>warning.click()),
                     page.waitForFunction(()=>!!localStorage.getItem('token'),null,{timeout:15000})]);
  stage='authenticated token';await page.waitForFunction(()=>!!localStorage.getItem('token'),null,{timeout:15000});
  stage='release center';await page.goto('http://127.0.0.1:18081/release-center/?app=intruoyi&page=7');
  const entry=page.getByRole('link',{name:'后端补丁',exact:false});
  await entry.waitFor({state:'visible'});stage='backend patch page';await entry.click();
  await page.getByRole('heading',{name:'构建后端补丁',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'构建后端补丁',exact:true}).isDisabled(),true);
  assert.equal(await page.getByRole('button',{name:'发布到正式服',exact:true}).isDisabled(),true);
  assert.equal(await page.getByRole('button',{name:'发布到审查服',exact:true}).isDisabled(),true);
  assert.equal(await page.locator('[role=alert]').count(),0);
  assert.equal(await page.getByText('不执行数据库结构、数据、菜单权限或配置迁移。',{exact:false}).count(),1);
  assert.deepEqual(errors,[]);
  assert.equal(requests.some(r=>r.method==='POST'&&r.url.includes('/actions/')),false);
  assert.equal(requests.some(r=>r.url.startsWith('http://172.30.30.')),false);
  await page.screenshot({path:privateRoot+'/backend-patch-page.png',fullPage:true});
  const result={status:'passed',realPlaywrightLogin:true,entryFromReleaseCenter:true,
      url:page.url(),disabledUntilBaselineAndPackage:true,databasePolicyVisible:true,
      pageErrors:errors.length,operationRequests:0,remoteTargetsOpened:0};
  fs.writeFileSync(privateRoot+'/ui-verification.json',JSON.stringify(result,null,2),'utf8');
  console.log(JSON.stringify(result));
 }finally{await browser.close();}
})().catch(error=>{console.error(error.name+': local UI verification failed at '+stage);process.exitCode=1;});
