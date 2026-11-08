// Independently observe the real page after the retained r4 catalogue 504.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const task=__dirname,priv='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106';
const endpoint='/release-center/api/applications/intruoyi/package-catalog';
const output=path.join(task,'restore-58-r4-catalogue-readonly-verification.json');
if(fs.existsSync(output))throw Error('ORIGINAL_CATALOGUE_OBSERVATION_ALREADY_EXISTS');
(async()=>{
 const report={observedAt:new Date().toISOString(),actualPageRequest:true,businessWrites:0,endpoint};
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const state=JSON.parse(fs.readFileSync(priv+'/spug-active-session.private.json','utf8'));
  const context=await browser.newContext();
  await context.addCookies(state.cookies);
  await context.addInitScript(({origins})=>{const saved=origins.find(v=>v.origin===location.origin);if(saved)for(const item of saved.localStorage)localStorage.setItem(item.name,item.value);},{origins:state.origins});
  const page=await context.newPage();
  await page.route('**/*',async route=>{
   if(['GET','HEAD','OPTIONS'].includes(route.request().method()))return route.continue();
   report.businessWrites++;return route.abort('blockedbyclient');
  });
  const response=page.waitForResponse(r=>r.request().method()==='GET'&&new URL(r.url()).pathname===endpoint,{timeout:150000});
  const navigation=await page.goto('http://127.0.0.1:18080/backup-restore/',{waitUntil:'commit'});
  report.documentHttpStatus=navigation.status();
  if(report.documentHttpStatus!==200)throw Error('SPUG_BACKUP_DOCUMENT_HTTP_FAILED');
  const actual=await response;report.httpStatus=actual.status();report.responseObservedAt=new Date().toISOString();
  fs.writeFileSync(priv+'/restore-58-r4-catalogue-readonly-response.original-http-body',await actual.body(),{flag:'wx'});
  await page.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:120000});
  report.backupPageInitialized=true;
  if(report.httpStatus!==200||report.businessWrites!==0)throw Error('CATALOGUE_HTTP_OR_READONLY_CONTRACT_FAILED');
  report.status='PASS';
 }catch(e){report.status='FAIL';report.error=String(e);process.exitCode=1;}
 finally{
  report.finishedAt=new Date().toISOString();
  fs.writeFileSync(output,JSON.stringify(report,null,2),{encoding:'utf8',flag:'wx'});
  console.log(JSON.stringify(report));await browser.close();
 }
})().catch(e=>{console.error(String(e));process.exitCode=1;});
