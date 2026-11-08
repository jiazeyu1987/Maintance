'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function contracts(){
 const source=fs.readFileSync(path.join(__dirname,'verify_catalogue_identity_readonly.cjs'),'utf8');
 const context={require,__dirname,URL};vm.createContext(context);
 vm.runInContext(source.slice(0,source.indexOf('const installedPath='))+'\nglobalThis.contract={classifyLoginContract,catalogueRequestPolicy,waitForBackupDocument};',context);
 return context.contract;
}
test('only the first exact local Spug authentication POST is allowed',()=>{
 const {catalogueRequestPolicy:policy}=contracts();
 assert.equal(policy('POST','http://127.0.0.1:18080/api/account/login/',0),'authentication');
 assert.equal(policy('POST','http://127.0.0.1:18080/api/account/login/',1),'blocked');
 for(const url of ['http://127.0.0.1:18080/backup-entry-api/automatic-incremental','http://127.0.0.1:18080/api/account/login/?other=1','http://localhost:18080/api/account/login/','http://127.0.0.1:18081/api/account/login/'])assert.equal(policy('POST',url,0),'blocked');
 assert.equal(policy('GET','http://127.0.0.1:18080/release-center/api/applications/intruoyi/package-catalog',1),'readonly');
 assert.equal(policy('GET','https://example.test/',1),'blocked');
});
test('actual nested login contract requires token and explicit security notice or blocks MFA',()=>{
 const {classifyLoginContract:classify}=contracts();
 assert.equal(classify(200,{error:null,data:{access_token:'synthetic-unit-token',has_real_ip:false}}).needsNotice,true);
 assert.equal(classify(200,{error:null,data:{access_token:'synthetic-unit-token',has_real_ip:true}}).needsNotice,false);
 assert.throws(()=>classify(200,{data:{required_mfa:true}}),/REAL_LOGIN_MFA_REQUIRED/);
 for(const [status,value] of [[401,{}],[500,{}],[200,{error:'unit-error'}],[200,null],[200,{access_token:'wrong-level'}],[200,{data:{has_real_ip:false}}]])assert.throws(()=>classify(status,value),/REAL_LOGIN_REJECTED|REAL_LOGIN_SUCCESS_DATA_INVALID/);
});
test('frame address is inspected only after exact navigation and document readiness',async()=>{
 const {waitForBackupDocument:wait}=contracts();
 let current='',finish,reads=0;
 const navigation=new Promise(resolve=>{finish=resolve;});
 // Timing-only unit adapter: it does not launch a browser or claim real navigation.
 const frame={waitForURL:async(expected,options)=>{
  assert.equal(expected,'http://127.0.0.1:18080/backup-restore/?embedded=1');
  assert.equal(options.waitUntil,'domcontentloaded');assert.equal(options.timeout,45000);
  await navigation;
 },url:()=>{reads++;return current;}};
 const checking=wait(frame);assert.equal(reads,0);
 current='http://127.0.0.1:18080/backup-restore/?embedded=1';finish();await checking;
 assert.ok(reads>0);
 await assert.rejects(()=>wait({waitForURL:async()=>{},url:()=> 'http://127.0.0.1:18081/backup-restore/?embedded=1'}),/BACKUP_DOCUMENT_IDENTITY_REQUIRED/);
});
