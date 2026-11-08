'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'automatic_incremental_ui_acceptance.cjs'),'utf8');
function classify(status,body){
  const context={require,__dirname};vm.createContext(context);
  vm.runInContext(source.slice(0,source.lastIndexOf('\nmain().catch'))+'\nglobalThis.classifyLoginContract=classifyLoginContract;',context);
  return context.classifyLoginContract(status,body);
}
test('actual nested Spug login data distinguishes MFA from authenticated access token',()=>{
  assert.throws(()=>classify(200,{error:null,data:{required_mfa:true}}),/REAL_LOGIN_MFA_REQUIRED/);
  assert.throws(()=>classify(200,{error:null,data:{}}),/REAL_LOGIN_SUCCESS_DATA_INVALID/);
  assert.throws(()=>classify(200,{data:{required_mfa:false,has_real_ip:false}}),/REAL_LOGIN_SUCCESS_DATA_INVALID/);
  assert.equal(classify(200,{error:null,data:{access_token:'synthetic-test-token',has_real_ip:false}}).needsNotice,true);
  assert.equal(classify(200,{error:null,data:{access_token:'synthetic-test-token',has_real_ip:true}}).needsNotice,false);
});
test('failed HTTP, root error and malformed responses cannot imply login success',()=>{
  for(const [status,body] of [[500,{}],[401,{}],[200,{error:'synthetic rejection'}],[200,null],[200,{access_token:'wrong-level'}]]){
    assert.throws(()=>classify(status,body),/REAL_LOGIN_REJECTED|REAL_LOGIN_SUCCESS_DATA_INVALID/);
  }
});
