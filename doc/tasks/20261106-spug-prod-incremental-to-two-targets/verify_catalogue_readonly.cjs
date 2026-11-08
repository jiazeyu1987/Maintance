// Observe the catalogue's real page request; preserve the original failed request.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const task=__dirname,priv='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106';
const endpoint='/release-center/api/applications/intruoyi/package-catalog';
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({storageState:priv+'/spug-active-session.private.json'});
 const page=await context.newPage();
 const report={observedAt:new Date().toISOString(),actualPageRequest:true,businessWrites:0,endpoint};
 await page.route('**/*',async route=>{
  if(['GET','HEAD','OPTIONS'].includes(route.request().method()))return route.continue();
  report.businessWrites++;return route.abort('blockedbyclient');
 });
 try{
  const response=page.waitForResponse(r=>new URL(r.url()).pathname===endpoint,{timeout:150000});
  await page.goto('http://127.0.0.1:18080/backup-restore/',{waitUntil:'domcontentloaded'});
  const actual=await response;report.httpStatus=actual.status();
  fs.writeFileSync(priv+'/catalogue-readonly-response.private.log',await actual.body());
  await page.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:120000});
  report.backupPageInitialized=true;report.finishedAt=new Date().toISOString();
  report.status=report.httpStatus===200&&report.businessWrites===0?'PASS':'FAIL';
 }catch(e){report.status='FAIL';report.error=String(e);process.exitCode=1;}
 finally{
  fs.writeFileSync(path.join(task,'catalogue-readonly-verification.json'),JSON.stringify(report,null,2),'utf8');
  console.log(JSON.stringify(report));await browser.close();
 }
})().catch(e=>{console.error(String(e));process.exitCode=1;});
