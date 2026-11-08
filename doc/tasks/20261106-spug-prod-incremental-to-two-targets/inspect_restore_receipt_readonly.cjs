// Diagnose existing receipt GETs; this is not a replacement for UI acceptance.
const {chromium}=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const kind=process.argv[2];if(!/^restore-(58|59)(-r[2-9])?$/.test(kind))throw Error('EXPLICIT_OPERATION_REQUIRED');
const priv='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106';
const expected=JSON.parse(fs.readFileSync(path.join(__dirname,kind+'-ui-submission.json'),'utf8')).request;
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,timeout:20000});
 const context=await browser.newContext({storageState:priv+'/spug-active-session.private.json'});
 const report={observedAt:new Date().toISOString(),operationId:expected.operationId,businessWrites:0,diagnosticOnly:true,requests:[]};
 try{
  for(const endpoint of ['/backup-entry-api/history','/backup-entry-api/operations/'+expected.operationId,'/backup-entry-api/progress/'+expected.operationId]){
   const started=Date.now(),entry={endpoint};report.requests.push(entry);
   try{
    const response=await context.request.get('http://127.0.0.1:18080'+endpoint,{timeout:35000,maxRedirects:0});
    const raw=await response.body();entry.httpStatus=response.status();entry.bytes=raw.length;
    fs.writeFileSync(priv+'/'+kind+'-diagnostic-'+endpoint.split('/').pop()+'.private.json',raw);
    const value=JSON.parse(raw.toString('utf8'));
    if(endpoint.endsWith('/history')){entry.historyCount=Array.isArray(value)?value.length:null;entry.exactMatches=Array.isArray(value)?value.filter(v=>v.request?.operationId===expected.operationId).map(v=>({operationId:v.request.operationId,spugHistoryId:v.spugHistoryId,state:v.result?.state,dispatchState:v.dispatchState})):[];}
    else {entry.spugHistoryId=value.spugHistoryId;entry.state=value.result?.state;entry.errorCode=value.errorCode||value.code;entry.queryError=value.queryError;entry.sameRequest=value.request?Object.keys(expected).every(k=>value.request[k]===expected[k]):null;}
   }catch(e){entry.error=String(e).split('\n')[0];}
   entry.elapsedMilliseconds=Date.now()-started;console.log(JSON.stringify(entry));
  }
 }finally{report.finishedAt=new Date().toISOString();fs.writeFileSync(path.join(__dirname,kind+'-receipt-diagnostic.json'),JSON.stringify(report,null,2),'utf8');await browser.close();}
})().catch(e=>{console.error(String(e));process.exitCode=1;});
