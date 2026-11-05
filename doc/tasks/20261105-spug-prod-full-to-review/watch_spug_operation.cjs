// Keep the real UI open. Observe only its GET responses and visible progress.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');const kind=process.argv[2]||'full',task=__dirname,priv='C:/Spug/runtime/private/prod-full-to-review-20261105';
const expected=JSON.parse(fs.readFileSync(path.join(task,kind+'-ui-submission.json'),'utf8')).request;
const write=(p,v)=>fs.writeFileSync(p,JSON.stringify(v,null,2),'utf8');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({storageState:priv+'/spug-active-session.private.json',viewport:{width:1440,height:1080}});
 const page=await context.newPage();page.setDefaultTimeout(45000);let latest=null,last=null,writes=0;const reads=[];
 page.on('request',r=>{if(r.method()==='POST')writes++;});
 page.on('response',r=>{if(r.request().method()==='GET'&&new URL(r.url()).pathname==='/backup-entry-api/operations/'+expected.operationId){
  const p=r.json().then(v=>{if(v.request?.operationId===expected.operationId){latest=v;write(priv+'/'+kind+'-live-record.private.json',v);}}).catch(e=>{console.log(JSON.stringify({responseReadError:String(e)}));});reads.push(p);
 }});
 try{
  await page.goto('http://127.0.0.1:18080/backup-restore/',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>typeof simpleConfig!=='undefined'&&simpleConfig&&!simpleInitializing&&!switching,null,{timeout:90000});
  await page.locator('#simple-history-tab').click();
  const original=page.locator('#simple-history .history-row').filter({hasText:expected.operationId});
  await original.getByRole('button',{name:'查看进度',exact:true}).click();
  await page.locator('#simple-progress-tab').click();
  await page.waitForFunction(id=>document.querySelector('#operation-reference')?.textContent===id&&!document.querySelector('#simple-query').disabled,expected.operationId);
  await page.locator('#simple-query').click();
  for(let cycle=0;cycle<1440;cycle++){
   await Promise.all(reads.splice(0));
   const snap={observedAt:new Date().toISOString(),operationId:expected.operationId,state:latest?.result?.state||null,errorCode:latest?.result?.errorCode||null,spugHistoryId:latest?.spugHistoryId||null,queryError:latest?.queryError||null,visible:await page.locator('#simple-result').innerText(),steps:await page.locator('#steps').innerText(),logs:(await page.locator('#simple-logs').innerText()).split('\n').slice(-5).join('\n'),problem:await page.locator('#problem').textContent(),writes};
   write(path.join(task,kind+'-live-progress.json'),snap);
   if(JSON.stringify({...snap,observedAt:null})!==last||cycle%2===0){console.log(JSON.stringify({observedAt:snap.observedAt,operationId:snap.operationId,state:snap.state,errorCode:snap.errorCode,spugHistoryId:snap.spugHistoryId,queryError:snap.queryError,logs:snap.logs,problem:snap.problem,writes}));last=JSON.stringify({...snap,observedAt:null});}
   if(writes)throw Error('UNEXPECTED_POST_DURING_OBSERVATION');
   if(['SUCCEEDED','FAILED'].includes(latest?.result?.state)){
    write(path.join(task,kind+'-terminal-record.json'),latest);
    await page.screenshot({path:path.join(task,kind+'-ui-terminal.png'),fullPage:true});
    await context.storageState({path:priv+'/spug-active-session.private.json'});
    if(latest.result.state==='FAILED')process.exitCode=1;
    return;
   }
   await page.waitForTimeout(15000);
  }
  throw Error('OBSERVATION_WINDOW_EXCEEDED_KEEP_ORIGINAL_ID');
 }finally{await browser.close();}
})().catch(e=>{console.error(String(e));process.exitCode=1;});
