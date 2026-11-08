// Observe the real login page after a pre-submission navigation timeout.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
(async()=>{
 const out={startedAt:new Date().toISOString(),businessWrites:0,blocked:[],responses:[],failedRequests:[]};
 const browser=await chromium.launch({channel:'chrome',headless:true,timeout:20000});
 const page=await browser.newPage();
 page.on('response',r=>out.responses.push({path:new URL(r.url()).pathname,status:r.status()}));
 page.on('requestfailed',r=>out.failedRequests.push({path:new URL(r.url()).pathname,error:r.failure()?.errorText}));
 await page.route('**/*',async route=>{
  if(['GET','HEAD','OPTIONS'].includes(route.request().method()))return route.continue();
  out.blocked.push({method:route.request().method(),path:new URL(route.request().url()).pathname});
  await route.abort('blockedbyclient');
 });
 try{
  const response=await page.goto('http://127.0.0.1:18080/',{waitUntil:'domcontentloaded',timeout:45000});
  out.httpStatus=response.status();
  await page.getByPlaceholder('请输入账户').waitFor({state:'visible',timeout:15000});
  await page.getByPlaceholder('请输入密码').waitFor({state:'visible',timeout:15000});
  out.loginControlsVisible=true;out.status='PASS';
 }catch(error){out.status='FAIL';out.error=String(error);process.exitCode=1;}
 finally{
  out.observedAt=new Date().toISOString();
  fs.writeFileSync(path.join(__dirname,'spug-login-after-navigation-timeout.json'),JSON.stringify(out,null,2),{encoding:'utf8',flag:'wx'});
  console.log(JSON.stringify(out));await browser.close();
 }
})().catch(e=>{console.error(String(e));process.exitCode=1;});
