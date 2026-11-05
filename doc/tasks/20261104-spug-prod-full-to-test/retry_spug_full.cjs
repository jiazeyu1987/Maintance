// Same original request; UI absence proof is mandatory before its retry button.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');const task=__dirname,priv='C:/Spug/runtime/private/prod-full-to-test-20261104';
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2),'utf8');
(async()=>{
 const original=JSON.parse(fs.readFileSync(path.join(task,'full-ui-submission.json'),'utf8')).request;
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({storageState:priv+'/spug-active-session.private.json',viewport:{width:1440,height:1080}});
 const page=await context.newPage();page.setDefaultTimeout(45000);
 const out={operationId:original.operationId,realBrowser:true,priorHttpStatus:409,writes:0};
 try{
  await page.goto('http://127.0.0.1:18080/backup-restore/',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>Boolean(document.querySelector('#operation-reference')?.textContent)&&!document.querySelector('#simple-query').disabled);
  if(await page.locator('#operation-reference').innerText()!==original.operationId)throw Error('ORIGINAL_ID_MISMATCH');
  await page.locator('#diagnostics summary').click();
  await page.locator('#original-operation-id').fill(original.operationId);
  const checked=page.waitForResponse(r=>new URL(r.url()).pathname==='/backup-entry-api/unaccepted-original');
  await page.locator('#check-unaccepted').click();
  const response=await checked;const proof=await response.json();
  if(!response.ok()||proof.retryAllowed!==true||JSON.stringify(proof.request)!==JSON.stringify(original))throw Error('UNACCEPTED_PROOF_MISSING');
  out.absence=proof;write(path.join(task,'full-original-unaccepted-proof.json'),proof);
  await page.waitForFunction(()=>!document.querySelector('#retry-original').disabled);
  await page.screenshot({path:path.join(task,'full-ui-unaccepted.png'),fullPage:true});
  const submitted=page.waitForResponse(r=>new URL(r.url()).pathname==='/backup-entry-api/operations'&&r.request().method()==='POST',{timeout:30000});
  page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname==='/backup-entry-api/operations'){out.writes++;out.request=r.postDataJSON();write(path.join(task,'full-ui-retry-request.json'),{at:new Date().toISOString(),request:out.request});}});
  await page.locator('#retry-original').click();
  const accepted=await submitted;const body=await accepted.json();
  write(priv+'/full-retry-entry-response.private.json',body);
  out.httpStatus=accepted.status();out.spugHistoryId=body.spugHistoryId;out.result=body.result;out.errorCode=body.errorCode;out.dispatchErrorCode=body.dispatchErrorCode;
  await context.storageState({path:priv+'/spug-active-session.private.json'});
  if(!accepted.ok())throw Error(body.errorCode||'SUBMISSION_REJECTED');
  if(out.writes!==1||JSON.stringify(out.request)!==JSON.stringify(original))throw Error('ORIGINAL_REQUEST_CHANGED');
  out.status='PASS';
 }catch(e){out.status='FAIL';out.error=String(e);process.exitCode=1;}
 finally{out.visible=await page.locator('body').innerText();write(path.join(task,'full-ui-retry-result.json'),out);console.log(JSON.stringify(out));await browser.close();}
})().catch(e=>{console.error(String(e));process.exitCode=1;});
