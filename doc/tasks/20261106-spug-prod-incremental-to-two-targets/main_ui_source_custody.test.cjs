'use strict';
// Explicit subprocess protocol only; real private files and mutations, no UI.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),vm=require('node:vm'),crypto=require('node:crypto');
const source=fs.readFileSync(path.join(__dirname,'automatic_incremental_ui_acceptance.cjs'),'utf8');
const hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
function setup(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'main-custody-cli-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const privateRoot=path.join(root,'private');fs.mkdirSync(privateRoot);
 const selectionPin={file:'main-program-current-installations-b5fa4c5-r7-v4.json',bytes:2,sha256:hash(Buffer.from('{}'))};
 const file=path.join(privateRoot,'custody.json');const raw=Buffer.from(JSON.stringify({schemaVersion:'MainProgramSpugHistoricalSourceRoles/v1',selectionPin}));fs.writeFileSync(file,raw);
 const pin={path:file,bytes:raw.length,sha256:hash(raw)};
 const f={root,privateRoot,file,pin,selectionPin,calls:[],beforeReturn:null,
  options:{cycle:'main-r7-20261110',kind:'I1',phase:'verify',observation:'r1','historical-source-custody':file},summary:{inputPins:[pin]}};
 const scopedRequire=name=>name==='node:child_process'?{spawnSync:(...args)=>{f.calls.push(args);if(f.beforeReturn)f.beforeReturn();return {pid:123,status:0,signal:null,stdout:Buffer.from(JSON.stringify(f.summary)),stderr:Buffer.alloc(0)};}}:require(name);
 const proc={argv:['node','driver']};const context=vm.createContext({require:scopedRequire,__dirname:root,process:proc,console,Buffer});
 const relocated=source.replace("PRIVATE='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106'",'PRIVATE='+JSON.stringify(privateRoot));
 vm.runInContext(relocated.slice(0,relocated.lastIndexOf('\nmain().catch'))+'\nglobalThis.api={runMainInstallationCli,args,historicalCustodyInput:typeof historicalCustodyInput==="function"?historicalCustodyInput:null};',context);
 f.run=()=>context.api.runMainInstallationCli(f.selectionPin,f.options);f.api=context.api;
 f.parse=()=>{proc.argv=['node','driver','--kind','I1','--phase','verify','--observation','r1','--preflight',path.join(root,'preflight.json'),'--cycle',f.options.cycle,'--selection',path.join(root,f.selectionPin.file),'--historical-source-custody',f.options['historical-source-custody']];return context.api.args();};
 f.native=()=>JSON.parse(fs.readFileSync(path.join(privateRoot,'automatic-incremental-ui',f.options.cycle,'i1-verify-r1-current-installation/native.private.json')));
 return f;
}
test('explicit CLI argument is parsed and passed with unchanged native limits',t=>{
 const f=setup(t);assert.equal(f.parse()['historical-source-custody'],f.file);f.run();
 const [exe,argv,opts]=f.calls[0];assert.deepEqual(Array.from(argv),['-B','-X','utf8',path.join(f.root,'main_program_current_installation.py'),'--selection',f.selectionPin.file,'--public-summary','--historical-source-custody',f.file]);
 assert.equal(opts.timeout,600000);assert.equal(opts.maxBuffer,16*1024*1024);assert.equal(opts.shell,false);assert.equal(opts.windowsHide,true);
 assert.deepEqual(f.native().historicalSourceCustodyPin,f.pin);assert.equal(f.native().exitCode,0);
});
for(const mode of ['cycle','selection','relative','outside','dotdot','missing','hardlink','junction','stream-alias','schema','bound-selection','too-large'])test('reject invalid explicit custody before subprocess: '+mode,t=>{
 const f=setup(t);
 if(mode==='cycle')f.options.cycle='other-cycle';
 else if(mode==='selection')f.selectionPin.file='main-program-current-installations-45dd7dc-r6-v4.json';
 else if(mode==='relative')f.options['historical-source-custody']='custody.json';
 else if(mode==='outside'){const p=path.join(f.root,'outside.json');fs.copyFileSync(f.file,p);f.options['historical-source-custody']=p;}
 else if(mode==='dotdot')f.options['historical-source-custody']=f.privateRoot+path.sep+'child'+path.sep+'..'+path.sep+'custody.json';
 else if(mode==='missing')fs.unlinkSync(f.file);
 else if(mode==='hardlink')fs.linkSync(f.file,path.join(f.privateRoot,'alias.json'));
 else if(mode==='junction'){const alias=path.join(f.privateRoot,'alias');fs.symlinkSync(f.privateRoot,alias,'junction');f.options['historical-source-custody']=path.join(alias,'custody.json');}
 else if(mode==='stream-alias'){const alias=f.file+':metadata';fs.writeFileSync(alias,fs.readFileSync(f.file));f.options['historical-source-custody']=alias;}
 else if(mode==='schema')fs.writeFileSync(f.file,JSON.stringify({schemaVersion:'Unknown/v1',selectionPin:f.selectionPin}));
 else if(mode==='bound-selection')fs.writeFileSync(f.file,JSON.stringify({schemaVersion:'MainProgramSpugHistoricalSourceRoles/v1',selectionPin:{...f.selectionPin,sha256:'0'.repeat(64)}}));
 else fs.writeFileSync(f.file,Buffer.alloc(16*1024*1024+1));
 assert.throws(f.run,/MAIN_HISTORICAL_CUSTODY_/);assert.equal(f.calls.length,0);
});
for(const mode of ['missing','sha','bytes','other-path'])test('summary must bind exact physical custody: '+mode,t=>{
 const f=setup(t);
 if(mode==='missing')f.summary.inputPins=[];
 else if(mode==='sha')f.summary.inputPins=[{...f.pin,sha256:'0'.repeat(64)}];
 else if(mode==='bytes')f.summary.inputPins=[{...f.pin,bytes:f.pin.bytes+1}];
 else f.summary.inputPins=[{...f.pin,path:path.join(f.privateRoot,'other.json')}];
 assert.throws(f.run,/MAIN_HISTORICAL_CUSTODY_SUMMARY_UNBOUND/);assert.equal(f.native().exitCode,0);
});
test('real file mutation while Python runs is rejected after retaining native stdout',t=>{
 const f=setup(t);f.beforeReturn=()=>fs.appendFileSync(f.file,' ');
 assert.throws(f.run,/MAIN_HISTORICAL_CUSTODY_CHANGED/);const n=f.native();assert.equal(n.exitCode,0);assert.deepEqual(n.historicalSourceCustodyPin,f.pin);
});
test('later explicit barrier preserves original identity and pin',t=>{
 const f=setup(t);assert.equal(typeof f.api.historicalCustodyInput,'function');
 const before=f.api.historicalCustodyInput(f.selectionPin,f.options);fs.appendFileSync(f.file,' ');
 assert.throws(()=>f.api.historicalCustodyInput(f.selectionPin,f.options,before),/MAIN_HISTORICAL_CUSTODY_CHANGED/);
});
test('canonical slash representation from Python binds the same physical input',t=>{
 const f=setup(t);f.options['historical-source-custody']=f.file.replaceAll('\\','/');
 f.summary.inputPins=[{...f.pin,path:f.file.replaceAll('\\','/')}];f.run();assert.equal(f.calls.length,1);
});
test('cached explicit input cannot be removed from later verification',t=>{
 const f=setup(t);const before=f.api.historicalCustodyInput(f.selectionPin,f.options);delete f.options['historical-source-custody'];
 assert.throws(()=>f.api.historicalCustodyInput(f.selectionPin,f.options,before),/MAIN_HISTORICAL_CUSTODY_CHANGED/);
});
