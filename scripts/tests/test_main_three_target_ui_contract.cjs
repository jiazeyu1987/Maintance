'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {restoreWriteAllowed,assertPointChain}=require('../../doc/tasks/20261106-spug-prod-incremental-to-two-targets/main_three_target_ui.cjs');
const {jsonEqual}=require('../../doc/tasks/20261106-spug-prod-incremental-to-two-targets/main_three_target_ui.cjs');
const ids=['smallapp-3c2395ff88bd474e9fc007649565b848','smallapp-20a1bb9b78ac402693289675d16c63dd','smallapp-e7b668792c8f4bce945a52f984d3c660'];
const proof={status:'SUCCEEDED_VERIFIED',operationId:ids[2],parentOperationId:ids[1],baseFullOperationId:ids[0],chainDepth:2,actualExitCode:0,originalSourceRestored:true,originalWorkerExited:true};
const request={schemaVersion:'SmallAppBackupUiRequest/v1',operationId:'smallapp-11111111111111111111111111111111',action:'RESTORE',sourceConfigRef:'intruoyi-57-safe-20261024-v1',parentChainRef:null,recoveryPointRef:ids[2],targetConfigRef:'intruoyi-main-58-safe-restore-20261104-v1'};
test('successful original three point chain is retained',()=>assert.deepEqual(assertPointChain(proof),ids));
for(const field of ['status','parentOperationId','baseFullOperationId','chainDepth','actualExitCode','originalSourceRestored','originalWorkerExited']){
 test('invalid original success '+field+' is rejected',()=>assert.throws(()=>assertPointChain({...proof,[field]:null})));
}
test('only explicit submit exact I2 to test58 may write once',()=>assert.equal(restoreWriteAllowed('submit',request,ids[2],false,0),true));
for(const phase of ['preview','verify',null])test('readonly phase '+phase+' cannot dispatch',()=>assert.equal(restoreWriteAllowed(phase,request,ids[2],false,0),false));
for(const key of ['action','schemaVersion','sourceConfigRef','recoveryPointRef','targetConfigRef','operationId','parentChainRef']){
 test('wrong request '+key+' is rejected',()=>assert.equal(restoreWriteAllowed('submit',{...request,[key]:'wrong'},ids[2],false,0),false));
}
test('unknown request fields rejected',()=>assert.equal(restoreWriteAllowed('submit',{...request,extra:true},ids[2],false,0),false));
test('production target rejected',()=>assert.equal(restoreWriteAllowed('submit',{...request,targetConfigRef:'intruoyi-main-57-safe-restore-20261105-v2'},ids[2],false,0),false));
test('review target rejected',()=>assert.equal(restoreWriteAllowed('submit',{...request,targetConfigRef:'intruoyi-main-59-safe-restore-20261104-v1'},ids[2],false,0),false));
test('persisted request prevents repeat even after no response',()=>assert.equal(restoreWriteAllowed('submit',request,ids[2],true,0),false));
test('already passed write prevents second dispatch',()=>assert.equal(restoreWriteAllowed('submit',request,ids[2],false,1),false));

test('canonical response request keys may have another order',()=>assert.equal(jsonEqual(request,Object.fromEntries(Object.entries(request).reverse())),true));
test('nested JSON key order does not change identity',()=>assert.equal(jsonEqual({a:{x:1,y:2},b:[{c:3,d:4}]},{b:[{d:4,c:3}],a:{y:2,x:1}}),true));
test('JSON arrays retain order',()=>assert.equal(jsonEqual([1,2],[2,1]),false));
test('JSON scalar types retain identity',()=>assert.equal(jsonEqual({a:1},{a:true}),false));
test('additional JSON request fields change identity',()=>assert.equal(jsonEqual(request,{...request,extra:null}),false));
