'use strict';
// Explicit spawnSync protocol boundary; actual temporary files retain raw bytes.
// This does not execute the installation loader, browser or a remote command.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),vm=require('node:vm'),crypto=require('node:crypto');
const source=fs.readFileSync(path.join(__dirname,'automatic_incremental_ui_acceptance.cjs'),'utf8');
const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
function fixture(t,response){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'main-cli-native-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const options={cycle:'native-boundary',kind:'FULL',phase:'submit',observation:'r1'};
 const selectionPin={file:'selection.json',bytes:1,sha256:'a'.repeat(64)};
 const f={root,options,selectionPin,response,calls:[],throwError:null};
 const scopedRequire=name=>name==='node:child_process'?{spawnSync:(...args)=>{f.calls.push(args);if(f.throwError)throw f.throwError;return f.response;}}:require(name);
 const context=vm.createContext({require:scopedRequire,__dirname:root,process:{argv:['node','driver']},console,Buffer});
 const relocated=source.replace("PRIVATE='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106'","PRIVATE=__dirname");
 vm.runInContext(relocated.slice(0,relocated.lastIndexOf('\nmain().catch'))+'\nglobalThis.nativeRunner=(...a)=>runMainInstallationCli(...a);',context);
 f.run=()=>context.nativeRunner(selectionPin,options);
 f.directory=()=>path.join(root,'automatic-incremental-ui',options.cycle,`full-submit-${options.observation}-current-installation`);
 f.evidence=()=>JSON.parse(fs.readFileSync(path.join(f.directory(),'native.private.json'),'utf8'));
 return f;
}
function verifyEvidence(f){
 const value=f.evidence();assert.equal(value.schemaVersion,'MainUiCurrentInstallationNative/v1');
 assert.deepEqual(value.selectionPin,f.selectionPin);assert.equal(value.cycle,f.options.cycle);assert.equal(value.kind,'FULL');assert.equal(value.phase,'submit');assert.equal(value.observation,f.options.observation);
 assert.equal(value.timeoutMs,600000);assert.ok(Number.isFinite(value.durationMs)&&value.durationMs>=0);assert.ok(Number.isFinite(Date.parse(value.startedAt))&&Number.isFinite(Date.parse(value.finishedAt)));
 for(const [name,raw] of [['stdout',f.response?.stdout||Buffer.alloc(0)],['stderr',f.response?.stderr||Buffer.alloc(0)]]){
  const pin=value[name+'Pin'];assert.deepEqual(fs.readFileSync(pin.path),raw);assert.equal(pin.bytes,raw.length);assert.equal(pin.sha256,hash(raw));
 }
 assert.equal(value.pid,f.response?.pid??null);assert.equal(value.exitCode,f.response?.status??null);assert.equal(value.signal,f.response?.signal??null);
 return value;
}
for(const [name,extra,code] of [
 ['timeout',{error:{code:'ETIMEDOUT'},status:null,signal:'SIGTERM'},'TIMEOUT'],
 ['output limit',{error:{code:'ENOBUFS'},status:null,signal:'SIGTERM'},'OUTPUT_LIMIT'],
 ['spawn failure',{error:{code:'ENOENT'},status:null,signal:null},'SPAWN_FAILED'],
 ['signal',{status:null,signal:'SIGKILL'},'TERMINATED'],
 ['unknown exit',{status:null,signal:null},'TERMINATED'],
 ['nonzero exit',{status:7,signal:null},'EXIT_FAILED'],
 ['unexpected stderr',{status:0,signal:null},'STDERR_REJECTED'],
])test('retain exact native '+name+' before exposing safe code',t=>{
 const f=fixture(t,{pid:123,status:0,signal:null,stdout:Buffer.from([0,255,65]),stderr:Buffer.from('private diagnostic\n'),...extra});
 assert.throws(f.run,new RegExp('^Error: MAIN_CURRENT_INSTALLATION_'+code+'$'));
 const value=verifyEvidence(f);assert.equal(value.errorCode,extra.error?.code??null);assert.equal(value.responseReturned,true);
 assert.equal(fs.existsSync(path.join(f.root,'automatic-native-boundary-full-ui-submission.json')),false);
});
test('successful native result is recorded before JSON is consumed',t=>{
 const raw=Buffer.from('{"value":1}\n'),f=fixture(t,{pid:321,status:0,signal:null,stdout:raw,stderr:Buffer.alloc(0)});
 assert.equal(f.run().value,1);verifyEvidence(f);assert.equal(f.calls.length,1);
 const [exe,args,options]=f.calls[0];assert.equal(exe,'C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe');
 assert.deepEqual(Array.from(args),['-B','-X','utf8',path.join(f.root,'main_program_current_installation.py'),'--selection','selection.json','--public-summary']);
 assert.equal(options.shell,false);assert.equal(options.windowsHide,true);assert.equal(options.timeout,600000);assert.equal(options.maxBuffer,16*1024*1024);assert.equal(options.encoding,undefined);
});
test('invalid JSON still retains original successful native exit and raw output',t=>{
 const f=fixture(t,{pid:321,status:0,signal:null,stdout:Buffer.from('not json'),stderr:Buffer.alloc(0)});
 assert.throws(f.run,/MAIN_CURRENT_INSTALLATION_INVALID/);assert.equal(verifyEvidence(f).exitCode,0);
});
test('thrown startup error records unavailable exit fields honestly',t=>{
 const f=fixture(t,null);f.throwError=Object.assign(Error('private thrown detail'),{code:'EACCES'});
 assert.throws(f.run,/MAIN_CURRENT_INSTALLATION_SPAWN_FAILED/);const value=verifyEvidence(f);
 assert.equal(value.errorCode,'EACCES');assert.equal(value.responseReturned,false);assert.equal(value.exitCode,null);assert.equal(value.signal,null);
});
test('same observation never overwrites originals or dispatches another CLI',t=>{
 const f=fixture(t,{pid:9,status:7,signal:null,stdout:Buffer.from('original'),stderr:Buffer.alloc(0)});
 assert.throws(f.run,/MAIN_CURRENT_INSTALLATION_EXIT_FAILED/);const original=fs.readFileSync(path.join(f.directory(),'native.private.json'));
 assert.throws(f.run,/MAIN_CURRENT_INSTALLATION_OBSERVATION_EXISTS/);assert.equal(f.calls.length,1);
 assert.deepEqual(fs.readFileSync(path.join(f.directory(),'native.private.json')),original);
 f.options.observation='r2';f.response={pid:10,status:0,signal:null,stdout:Buffer.from('{}'),stderr:Buffer.alloc(0)};
 f.run();assert.equal(f.calls.length,2);assert.equal(verifyEvidence(f).pid,10);
});
test('evidence directory failure blocks CLI invocation',t=>{
 const f=fixture(t,{status:0,stdout:Buffer.from('{}'),stderr:Buffer.alloc(0)});
 fs.writeFileSync(path.join(f.root,'automatic-incremental-ui'),'blocked');
 assert.throws(f.run,/MAIN_CURRENT_INSTALLATION_EVIDENCE_WRITE_FAILED/);assert.equal(f.calls.length,0);
});
test('only valid fixed observation fields may determine private evidence paths',t=>{
 const f=fixture(t,{status:0,stdout:Buffer.from('{}'),stderr:Buffer.alloc(0)});f.options.observation='../escape';
 assert.throws(f.run,/MAIN_CURRENT_INSTALLATION_OBSERVATION_INVALID/);assert.equal(f.calls.length,0);
});
