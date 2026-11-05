// Submit the exact approved restore once using genuine Spug controls.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const task=__dirname,priv='C:/Spug/runtime/private/prod-full-to-review-20261105';
const source='intruoyi-57-safe-20261024-v1',point='smallapp-73cd541a95d84d6a86f9d693e4053c75',target='intruoyi-main-59-safe-restore-20261104-v1';
const receipt=path.join(task,'restore-ui-submission.json');
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2),'utf8');
(async()=>{
 if(fs.existsSync(receipt))throw Error('ALREADY_SUBMITTED_FOLLOW_ORIGINAL_OPERATION');
 const browser=await chromium.launch({channel:'chrome',headless:true,timeout:20000});
 const context=await browser.newContext({viewport:{width:1440,height:1080}});
 const page=await context.newPage();page.setDefaultTimeout(45000);
 const out={realBrowser:true,realLogin:false,startedAt:new Date().toISOString(),writes:0,blocked:[],httpFailures:[],pageErrors:[]};
 page.on('pageerror',e=>out.pageErrors.push(String(e)));
 page.on('response',r=>{if(r.status()>=400)out.httpFailures.push({status:r.status(),path:new URL(r.url()).pathname});});
 await page.route('**/*',async route=>{
  const req=route.request(),pathname=new URL(req.url()).pathname;
  if(['GET','HEAD','OPTIONS'].includes(req.method())||req.method()==='POST'&&pathname==='/api/account/login/')return route.continue();
  if(req.method()==='POST'&&pathname==='/backup-entry-api/operations'){
   const r=req.postDataJSON();
   if(!out.writes&&r.action==='RESTORE'&&r.sourceConfigRef===source&&r.recoveryPointRef===point&&r.targetConfigRef===target&&!fs.existsSync(receipt)){
    out.writes++;out.request=r;
    fs.writeFileSync(receipt,JSON.stringify({submittedAt:new Date().toISOString(),request:r},null,2),{encoding:'utf8',flag:'wx'});
    return route.continue();
   }
  }
  out.blocked.push({method:req.method(),path:pathname});await route.abort('blockedbyclient');
 });
 try{
  const admin=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
  await page.goto('http://127.0.0.1:18080/',{waitUntil:'domcontentloaded'});
  await page.getByPlaceholder('请输入账户').fill(admin.username);await page.getByPlaceholder('请输入密码').fill(admin.password);
  const logged=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登 录'}).click();const auth=await (await logged).json();
  if(auth.error)throw Error('SPUG_LOGIN_REJECTED');
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token'))||[...document.querySelectorAll('button')].some(b=>b.innerText==='知道了'));
  if(await page.getByRole('button',{name:'知道了'}).isVisible())await page.getByRole('button',{name:'知道了'}).click();
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));out.realLogin=true;
  await page.getByText('备份与恢复',{exact:true}).first().waitFor();await page.getByText('备份与恢复',{exact:true}).first().click();
  await page.waitForURL('**/backup-center');
  const frame=await (await page.locator('iframe[src="/backup-restore/?embedded=1"]').elementHandle()).contentFrame();
  if(!frame)throw Error('BACKUP_FRAME_MISSING');
  await frame.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:90000});
  await frame.locator('#simple-catalog-tab').click();await frame.locator('#simple-catalog-tab[aria-selected="true"]').waitFor();
  const restore=frame.locator('#catalog-body button:enabled').filter({hasText:/^恢复$/}).first();
  await restore.waitFor();out.catalogRow=await restore.locator('xpath=../..').innerText();
  if(!out.catalogRow.includes('prod-standard-197d8fd4ced92df64f0c152e9c6d470596ec343532e3b2dd82ebbef680114bcb'))throw Error('CATALOGUE_FULL_MISMATCH');
  await restore.click();await frame.locator('#catalog-restore-dialog').waitFor({state:'visible'});
  await frame.waitForFunction(()=>document.querySelector('#simple-target').options.length>=4&&!document.querySelector('#simple-target').disabled);
  await frame.locator('#simple-target').selectOption('172.30.30.59');
  await frame.waitForFunction(()=>!document.querySelector('#simple-submit').disabled);
  await frame.locator('#simple-submit').click();await frame.locator('#simple-confirm').waitFor({state:'visible'});
  out.confirmation=await frame.locator('#confirm-summary').innerText();
  for(const expected of [source,point,target,'172.30.30.59','安全模式'])if(!out.confirmation.includes(expected))throw Error('CONFIRMATION_MISMATCH');
  if(!await frame.locator('#simple-confirm-submit').isDisabled())throw Error('OVERWRITE_ACK_NOT_REQUIRED');
  await frame.locator('#replace-confirm').check();
  await page.screenshot({path:path.join(task,'restore-ui-confirm.png'),fullPage:true});
  await context.storageState({path:priv+'/spug-active-session.private.json'});
  const accepted=page.waitForResponse(r=>new URL(r.url()).pathname==='/backup-entry-api/operations'&&r.request().method()==='POST',{timeout:45000});
  await frame.locator('#simple-confirm-submit').click();
  const response=await accepted;const body=await response.json();write(priv+'/restore-entry-response.private.json',body);
  out.httpStatus=response.status();out.spugHistoryId=body.spugHistoryId;out.result=body.result;out.errorCode=body.errorCode;out.dispatchErrorCode=body.dispatchErrorCode;
  if(out.writes!==1||!response.ok())throw Error(body.errorCode||'RESTORE_SUBMISSION_FAILED');
  await context.storageState({path:priv+'/spug-active-session.private.json'});
  out.visible=await frame.locator('main').innerText();
  await page.screenshot({path:path.join(task,'restore-ui-submitted.png'),fullPage:true});
  if(out.blocked.length||out.pageErrors.length)throw Error('UI_ERRORS_OR_UNEXPECTED_WRITE');
  out.status='PASS';
 }catch(error){out.status='FAIL';out.error=String(error);out.visible=await page.locator('body').innerText().catch(()=>'(unavailable)');process.exitCode=1;}
 finally{out.finishedAt=new Date().toISOString();write(path.join(task,'restore-ui-result.json'),out);console.log(JSON.stringify({status:out.status,realLogin:out.realLogin,writes:out.writes,request:out.request,httpStatus:out.httpStatus,result:out.result,error:out.error,blocked:out.blocked}));await browser.close();}
})().catch(error=>{console.error(String(error));process.exitCode=1;});
