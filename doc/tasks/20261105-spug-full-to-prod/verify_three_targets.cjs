// Verify genuine Spug choices after the original production restore succeeds.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const task=__dirname,priv='C:/Spug/runtime/private/full-to-prod-20261105';
const source='intruoyi-57-safe-20261024-v1',point='smallapp-73cd541a95d84d6a86f9d693e4053c75';
(async()=>{
 const native=JSON.parse(fs.readFileSync(path.join(task,'restored-native-evidence.json'),'utf8'));
 if(native.status!=='PASS'||native.state!=='SUCCEEDED'||native.actualExitCode!==0)throw Error('ORIGINAL_RESTORE_SUCCESS_REQUIRED');
 const plan=JSON.parse(fs.readFileSync(priv+'/production-route-plan.private.json','utf8'));
 const targets=plan.settings['smallapp-simple-settings.json'].bindings.find(b=>b.applicationId===source).overwriteTargetServers;
 if(Object.keys(targets).sort().join(',')!=='172.30.30.57,172.30.30.58,172.30.30.59')throw Error('THREE_EXACT_TARGETS_REQUIRED');
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1080}});
 const page=await context.newPage();page.setDefaultTimeout(60000);let frame=null;
 const out={observedAt:new Date().toISOString(),operationId:native.operationId,realBrowser:true,realLogin:false,restorePosts:0,blocked:[],choices:[],stage:'login',httpFailures:[],pageErrors:[]};
 page.on('response',r=>{if(r.status()>=400)out.httpFailures.push({status:r.status(),path:new URL(r.url()).pathname});});
 page.on('pageerror',e=>out.pageErrors.push(String(e)));
 await page.route('**/*',async route=>{
  const r=route.request(),pathname=new URL(r.url()).pathname;
  if(['GET','HEAD','OPTIONS'].includes(r.method())||r.method()==='POST'&&pathname==='/api/account/login/')return route.continue();
  if(r.method()==='POST'&&pathname==='/backup-entry-api/operations')out.restorePosts++;
  out.blocked.push({method:r.method(),path:pathname});await route.abort('blockedbyclient');
 });
 try{
  const admin=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
  await page.goto('http://127.0.0.1:18080/',{waitUntil:'domcontentloaded'});
  await page.getByPlaceholder('请输入账户').fill(admin.username);await page.getByPlaceholder('请输入密码').fill(admin.password);
  const logged=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登 录'}).click();if((await (await logged).json()).error)throw Error('SPUG_LOGIN_REJECTED');
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token'))||[...document.querySelectorAll('button')].some(b=>b.innerText==='知道了'));
  if(await page.getByRole('button',{name:'知道了'}).isVisible())await page.getByRole('button',{name:'知道了'}).click();
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));out.realLogin=true;
  await page.getByText('备份与恢复',{exact:true}).first().click();await page.waitForURL('**/backup-center');
  frame=await (await page.locator('iframe[src="/backup-restore/?embedded=1"]').elementHandle()).contentFrame();
  if(!frame)throw Error('BACKUP_FRAME_MISSING');
  out.stage='configuration';
  await frame.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:90000});
  out.stage='catalogue';await frame.locator('#simple-catalog-tab').click();
  const restore=frame.locator('#catalog-body tr').filter({hasText:'prod-standard-197d8fd4ced92df64f0c152e9c6d470596ec343532e3b2dd82ebbef680114bcb'}).getByRole('button',{name:'恢复',exact:true});
  await restore.click();await frame.locator('#catalog-restore-dialog').waitFor({state:'visible'});out.stage='target-options';
  await frame.waitForFunction(()=>document.querySelector('#simple-target').options.length>=4&&!document.querySelector('#simple-target').disabled);
  for(const host of Object.keys(targets).sort()){
   await frame.locator('#simple-target').selectOption(host);
   await frame.waitForFunction(()=>!document.querySelector('#simple-submit').disabled);
   await frame.locator('#simple-submit').click();await frame.locator('#simple-confirm').waitFor({state:'visible'});
   const summary=await frame.locator('#confirm-summary').innerText();
   for(const expected of [host,targets[host],source,point,'安全模式'])if(!summary.includes(expected))throw Error('TARGET_CONFIRMATION_MISMATCH');
   if(!await frame.locator('#simple-confirm-submit').isDisabled())throw Error('OVERWRITE_ACK_NOT_REQUIRED');
   out.choices.push({host,targetConfigRef:targets[host],exactSourceAndPointVerified:true,overwriteAcknowledgementRequired:true});
   await page.screenshot({path:path.join(task,'three-targets-confirm-'+host.split('.').pop()+'.png'),fullPage:true});
   await frame.locator('#simple-cancel').click();await frame.locator('#simple-confirm').waitFor({state:'hidden'});
  }
  await frame.locator('#catalog-restore-close').click();
  if(out.restorePosts||out.blocked.length)throw Error('UNEXPECTED_WRITE_DURING_CHOICE_VERIFICATION');
  out.status='PASS';
 }catch(e){out.status='FAIL';out.error=String(e);out.frameVisible=frame?await frame.locator('body').innerText().catch(()=>'(unavailable)'):null;await page.screenshot({path:path.join(task,'three-targets-entry-failure.png'),fullPage:true});process.exitCode=1;}
 finally{out.finishedAt=new Date().toISOString();fs.writeFileSync(path.join(task,'three-targets-ui-verification.json'),JSON.stringify(out,null,2),'utf8');console.log(JSON.stringify(out));await browser.close();}
})().catch(e=>{console.error(String(e));process.exitCode=1;});
