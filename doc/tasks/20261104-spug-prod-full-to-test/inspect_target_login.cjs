const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});const page=await browser.newPage({viewport:{width:1440,height:1080}});
 try{
  await page.goto('http://172.30.30.58:8081/login?redirect=/index',{waitUntil:'domcontentloaded'});
  await page.getByPlaceholder('请输入用户名',{exact:true}).waitFor();
  const result={url:page.url(),inputs:await page.locator('input').evaluateAll(ns=>ns.map(n=>({type:n.type,placeholder:n.getAttribute('placeholder'),role:n.getAttribute('role')}))),buttons:await page.getByRole('button').allTextContents(),visible:await page.locator('body').innerText()};
  fs.writeFileSync(path.join(__dirname,'target-login-form.json'),JSON.stringify(result,null,2),'utf8');console.log(JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(String(e));process.exitCode=1;});
