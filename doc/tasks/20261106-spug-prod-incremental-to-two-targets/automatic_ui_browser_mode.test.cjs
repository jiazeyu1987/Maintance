'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'automatic_incremental_ui_acceptance.cjs'),'utf8');
function contracts(extra=[]){
 const base=['--kind','FULL','--phase','verify','--observation','mode-contract','--preflight',path.join(__dirname,'gate.json')];
 const context=vm.createContext({require,__dirname,process:{argv:['node','test',...base,...extra]},console,Buffer});
 vm.runInContext(source.slice(0,source.lastIndexOf('\nmain().catch'))+'\nglobalThis.contract={args,browserPolicy};',context);
 return context.contract;
}
test('default browser behavior preserves both existing paths',()=>{
 const c=contracts();assert.equal(c.browserPolicy({cycle:'main-r7'}).headless,false);
 assert.equal(c.browserPolicy({}).headless,true);
});
test('explicit browser mode is parsed and fixes the selected launch policy',()=>{
 for(const mode of ['headed','headless']){
  const c=contracts(['--browser-mode',mode]),options=c.args();
  assert.equal(options['browser-mode'],mode);
  assert.equal(c.browserPolicy({...options,cycle:'main-r7'}).headless,mode==='headless');
  assert.equal(c.browserPolicy(options).mode,mode);
 }
});
test('invalid and duplicate modes fail before a browser can launch',()=>{
 for(const extra of [['--browser-mode','invalid'],['--browser-mode','headless','--browser-mode','headed']]){
  assert.throws(()=>contracts(extra).args());
 }
 assert.throws(()=>contracts().browserPolicy({'browser-mode':'invalid'}));
});
test('actual UI launch and observation use the explicit policy without changing submission fences',()=>{
 assert.match(source,/const browserMode=browserPolicy\(options\)/);
 assert.match(source,/headless:browserMode\.headless/);
 assert.match(source,/if\(!browserMode\.headless\)await page\.bringToFront\(\)/);
 assert.match(source,/browserMode:browserMode\.mode/);
 assert.match(source,/armed&&report\.businessPosts===0/);
 assert.ok(source.indexOf('exclusive(receiptPath,receipt)')<source.indexOf('report.businessPosts++;'));
 assert.match(source,/ACTUAL_SUCCESS_REQUIRED/);
});
