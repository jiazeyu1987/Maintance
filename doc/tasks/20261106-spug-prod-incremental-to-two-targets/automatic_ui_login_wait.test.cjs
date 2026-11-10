'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'automatic_incremental_ui_acceptance.cjs'),'utf8');
function observer(){
 const context=vm.createContext({require,__dirname,process:{},console,Buffer});
 vm.runInContext(source.slice(0,source.lastIndexOf('\nmain().catch'))+'\nglobalThis.observe=observeUiResponse;',context);
 return context.observe;
}
test('login response rejection is handled immediately and retains the original timeout',async()=>{
 const observe=observer(),original=new Error('real response timeout');
 const pending=observe(Promise.reject(original));
 await new Promise(resolve=>setImmediate(resolve));
 const outcome=await pending;assert.equal(outcome.error,original);assert.equal(outcome.value,undefined);
});
test('successful response object remains the original',async()=>{
 const original={status:200};assert.equal((await observer()(Promise.resolve(original))).value,original);
});
test('actual login attaches the handler before click and propagates its error into the report',()=>{
 const start=source.indexOf('const observedLogin=observeUiResponse(login)');
 const click=source.indexOf("await page.getByRole('button',{name:'登 录',exact:true}).click()",start);
 assert.ok(start>0&&click>start);assert.match(source,/if\(loginOutcome\.error\)throw loginOutcome\.error/);
 assert.match(source,/timeout:45000/);assert.match(source,/UI_TIMEOUT/);
});
