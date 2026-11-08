// Existing Spug login, menu, form and confirmation; one exact final POST at most.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const task=__dirname,priv='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106';
const source='intruoyi-57-safe-20261024-v1',parent='smallapp-7fec29a3e132463096aec915c08acab3';
const submit=process.argv[2]==='submit',kind=process.argv[3]||'incremental';
if(!['incremental','incremental-2','incremental-3','incremental-4'].includes(kind))throw Error('UNKNOWN_ATTEMPT');
const phase=submit?kind:kind+'-preview';
const receipt=path.join(task,kind+'-ui-submission.json');
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2),'utf8');
(async()=>{
 if(fs.existsSync(receipt))throw Error('ALREADY_SUBMITTED_FOLLOW_ORIGINAL');
 if(submit){const gate=JSON.parse(fs.readFileSync(path.join(task,kind+'-preflight.json'),'utf8'));if(gate.status!=='PASS'||gate.parentChainRef!==parent||gate.sourceConfigRef!==source)throw Error('CURRENT_PREFLIGHT_REQUIRED');if(Date.now()-Date.parse(gate.observedAt)>900000)throw Error('PREFLIGHT_STALE');}
 const browser=await chromium.launch({channel:'chrome',headless:true,timeout:20000});
 const context=await browser.newContext({viewport:{width:1440,height:1080}}),page=await context.newPage();page.setDefaultTimeout(45000);
 const out={startedAt:new Date().toISOString(),realBrowser:true,realLogin:false,writes:0,blocked:[],httpFailures:[],pageErrors:[]};let frame;
 page.on('pageerror',e=>out.pageErrors.push(String(e)));
 page.on('response',r=>{if(r.status()>=400)out.httpFailures.push({path:new URL(r.url()).pathname,status:r.status()});});
 await page.route('**/*',async route=>{
  const req=route.request(),url=new URL(req.url());
  if(['GET','HEAD','OPTIONS'].includes(req.method())||(req.method()==='POST'&&url.origin==='http://127.0.0.1:18080'&&url.pathname==='/api/account/login/'))return route.continue();
  if(submit&&req.method()==='POST'&&url.origin==='http://127.0.0.1:18080'&&url.pathname==='/backup-entry-api/operations'){
   const r=req.postDataJSON();
   if(!out.writes&&!fs.existsSync(receipt)&&r.action==='INCREMENTAL'&&r.sourceConfigRef===source&&r.parentChainRef===parent&&!r.recoveryPointRef&&!r.targetConfigRef){
    out.writes++;out.request=r;fs.writeFileSync(receipt,JSON.stringify({submittedAt:new Date().toISOString(),request:r},null,2),{encoding:'utf8',flag:'wx'});return route.continue();
   }
  }
  out.blocked.push({method:req.method(),path:url.pathname});await route.abort('blockedbyclient');
 });
 try{
  out.stage='login';const cred=JSON.parse(fs.readFileSync('C:/SpugHandoff/release/private/spug-login.private.json','utf8').replace(/^\uFEFF/,''));
  await page.goto('http://127.0.0.1:18080/',{waitUntil:'domcontentloaded'});
  await page.getByPlaceholder('请输入账户').fill(cred.username);await page.getByPlaceholder('请输入密码').fill(cred.password);
  const logged=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/account/login/'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'登 录'}).click();if((await (await logged).json()).error)throw Error('LOGIN_REJECTED');
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token'))||[...document.querySelectorAll('button')].some(b=>b.innerText==='知道了'));
  if(await page.getByRole('button',{name:'知道了'}).isVisible())await page.getByRole('button',{name:'知道了'}).click();
  await page.waitForFunction(()=>Boolean(localStorage.getItem('token')));out.realLogin=true;
  await page.getByText('备份与恢复',{exact:true}).first().click();await page.waitForURL('**/backup-center');
  frame=await (await page.locator('iframe[src="/backup-restore/?embedded=1"]').elementHandle()).contentFrame();
  out.stage='initialization';await frame.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:120000});
  await frame.locator('#simple-backup-tab').click();
  await frame.waitForFunction(()=>!switching&&!document.querySelector('#simple-product').disabled);
  await frame.locator('#simple-product').selectOption('intruoyi');
  await frame.waitForFunction(()=>!switching&&!document.querySelector('#simple-server').disabled,null,{timeout:120000});
  await frame.locator('#simple-server').selectOption('172.30.30.57');
  await frame.waitForFunction(()=>!switching&&!document.querySelector('#simple-mode').disabled,null,{timeout:120000});
  await frame.locator('#simple-mode').selectOption('safe');
  await frame.waitForFunction(s=>!switching&&selected()?.applicationId===s&&!document.querySelector('#simple-type').disabled,source,{timeout:120000});
  await frame.locator('#simple-type').selectOption('INCREMENTAL');
  await frame.waitForFunction(()=>!switching&&!document.querySelector('#simple-submit').disabled,null,{timeout:120000});
  out.parent=await frame.locator('#parent').inputValue();out.ready=await frame.locator('#simple-status').innerText();
  if(out.parent!==parent)throw Error('AUDITED_PARENT_CHANGED');
  out.stage='confirmation';await frame.locator('#simple-submit').click();await frame.locator('#simple-confirm').waitFor({state:'visible'});
  out.confirmation=await frame.locator('#confirm-summary').innerText();
  for(const expected of [source,parent,'172.30.30.57','安全模式','增量备份'])if(!out.confirmation.includes(expected))throw Error('CONFIRMATION_MISMATCH');
  await page.screenshot({path:path.join(task,phase+'-confirmation.png'),fullPage:true});
  await context.storageState({path:priv+'/spug-active-session.private.json'});
  if(submit){
   out.stage='final-submit';const accepted=page.waitForResponse(r=>new URL(r.url()).pathname==='/backup-entry-api/operations'&&r.request().method()==='POST',{timeout:45000});
   await frame.locator('#simple-confirm-submit').click();const response=await accepted,body=await response.json();
   write(priv+'/'+kind+'-entry-response.private.json',body);out.httpStatus=response.status();out.spugHistoryId=body.spugHistoryId;out.result=body.result;out.errorCode=body.errorCode;out.dispatchErrorCode=body.dispatchErrorCode;
   if(out.writes!==1||!response.ok())throw Error(body.errorCode||'SUBMISSION_FAILED');
   await context.storageState({path:priv+'/spug-active-session.private.json'});
  }
  if(out.blocked.length||out.pageErrors.length)throw Error('UNEXPECTED_UI_ERROR');
  out.status='PASS';
 }catch(e){out.status='FAIL';out.error=String(e);out.visible=frame?await frame.locator('body').innerText().catch(()=>'(unavailable)'):await page.locator('body').innerText().catch(()=>'(unavailable)');process.exitCode=1;}
 finally{out.finishedAt=new Date().toISOString();write(path.join(task,phase+'-ui-result.json'),out);console.log(JSON.stringify(out));await browser.close();}
})().catch(e=>{console.error(String(e));process.exitCode=1;});
