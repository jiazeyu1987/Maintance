// Read-only browser evidence for the unavailable pre-restore login form.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,timeout:20000});
 const context=await browser.newContext(),page=await context.newPage();
 const out={observedAt:new Date().toISOString(),responses:[],requestFailures:[],pageErrors:[],events:[]};
 page.on('crash',()=>out.events.push('crash'));page.on('close',()=>out.events.push('close'));
 page.on('pageerror',e=>out.pageErrors.push(String(e)));
 page.on('requestfailed',r=>out.requestFailures.push({path:new URL(r.url()).pathname,error:r.failure()?.errorText}));
 page.on('response',r=>out.responses.push({path:new URL(r.url()).pathname,status:r.status()}));
 try{
  const r=await page.goto('http://172.30.30.59:38081/login?redirect=/index',{waitUntil:'domcontentloaded',timeout:25000});
  out.httpStatus=r?.status();out.url=page.url();out.bodyCount=await page.locator('body').count();
  out.formCount=await page.locator('.el-form').count();out.inputs=await page.locator('input').evaluateAll(es=>es.map(e=>({type:e.type,placeholder:e.placeholder})));
  out.html=await page.content();
  await page.screenshot({path:'C:/Spug/runtime/private/prod-full-to-review-20261105/login-diagnosis.png',timeout:10000});
 }catch(e){out.error=String(e);out.url=page.url();}
 finally{
  fs.writeFileSync('C:/Spug/runtime/private/prod-full-to-review-20261105/login-diagnosis.private.json',JSON.stringify(out,null,2),'utf8');
  delete out.html;fs.writeFileSync(__dirname+'/login-diagnosis.json',JSON.stringify(out,null,2),'utf8');console.log(JSON.stringify(out));await browser.close();
 }
})().catch(e=>{console.error(String(e));process.exitCode=1;});
