'use strict';
// CLI protocol boundary only: no completed deployment, browser or host fixture.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const os=require('node:os'),crypto=require('node:crypto'),vm=require('node:vm'),test=require('node:test');
const acorn=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/acorn');
const source=fs.readFileSync(path.join(__dirname,'verify_goal_readonly.cjs'),'utf8');
const tree=acorn.parse(source,{ecmaVersion:'latest',sourceType:'script'});
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
function fixture(t){
 const task=fs.mkdtempSync(path.join(os.tmpdir(),'current-proof-protocol-'));
 t.after(()=>fs.rmSync(task,{recursive:true,force:true}));
 function pin(name,raw){const p=path.join(task,name);fs.writeFileSync(p,raw);return {path:p,bytes:Buffer.byteLength(raw),sha256:sha(Buffer.from(raw))};}
 const original=pin('original.json','{"protocol":true}\n');
 const selected={file:'selection.json',bytes:2,sha256:sha(Buffer.from('{}'))};pin(selected.file,'{}');
 const ref={file:'proof.json',bytes:2,sha256:selected.sha256};
 const summary={schemaVersion:'MainProgramCurrentInstallationSummary/v1',status:'PASS',selectionPin:selected,
  sourceCommit:'a'.repeat(40),controlGenerationPin:ref,spugInstallationPin:ref,buildPin:ref,
  build:{fileCount:147,fileManifestSha256:'b'.repeat(64),packageSha256:'c'.repeat(64)},
  resourceBuildPin:ref,spugCommit:'d'.repeat(40),inputPins:[original,pin('selection.json','{}')]};
 let reply={status:0,stdout:JSON.stringify(summary),stderr:''},calls=[];
 const names=['sameAuditPin','readAuditBoundInput','readCurrentInstallationSummary','verifyPointAuditInputs','readAuditTaskFile'];
 const code=names.map(name=>{const found=tree.body.filter(n=>n.type==='FunctionDeclaration'&&n.id.name===name);
  assert.equal(found.length,1,'FORMAL_CLI_CONSUMER_REQUIRED: '+name);return source.slice(found[0].start,found[0].end);}).join('\n');
 const context=vm.createContext({fs,path,crypto,Buffer,TASK:task,sha,
  require:name=>{assert.equal(name,'node:child_process');return {spawnSync(...args){calls.push(args);return reply;}};},
  need:(ok,code)=>{if(!ok)throw Error(code);}});
 vm.runInContext(code+'\nthis.api={'+names.join(',')+'}',context);
 return {task,selected,summary,original,calls,api:context.api,setReply:r=>reply=r,
  run(){reply.stdout=JSON.stringify(summary);return context.api.readCurrentInstallationSummary('selection.json',selected);}};
}
test('fixed readonly CLI uses argv without shell and records real original bytes',t=>{
 const f=fixture(t),out=f.run();assert.equal(out.summary.sourceCommit,f.summary.sourceCommit);
 assert.equal(f.calls.length,1);const [exe,argv,options]=f.calls[0];
 assert.ok(exe.endsWith('/dependencies/python/python.exe'));
 assert.deepEqual(Array.from(argv),['-B','-X','utf8',path.join(f.task,'main_program_current_installation.py'),'--selection','selection.json','--public-summary']);
 assert.equal(options.shell,false);assert.equal(out.records.length,2);
 f.api.verifyPointAuditInputs({records:out.records});
 fs.appendFileSync(f.original.path,' ');
 assert.throws(()=>f.api.verifyPointAuditInputs({records:out.records}),/POINT_AUDIT_INPUT_CHANGED/);
});
for(const mode of ['nonzero','error','invalid-json','stderr'])test('CLI failure is fail fast: '+mode,t=>{
 const f=fixture(t),reply={status:0,stdout:JSON.stringify(f.summary),stderr:''};
 if(mode==='nonzero')reply.status=1;else if(mode==='error')reply.error=Error('spawn failed');
 else if(mode==='invalid-json')reply.stdout='not json';else reply.stderr='warning';
 f.setReply(reply);assert.throws(()=>f.api.readCurrentInstallationSummary('selection.json',f.selected),/POINT_AUDIT_CURRENT_INSTALLATION/);
});
for(const mode of ['schema','status','extra','selection','empty','pin','outside-shape'])test('summary cannot substitute identity or omit closure: '+mode,t=>{
 const f=fixture(t);
 if(mode==='schema')f.summary.schemaVersion='Unknown/v1';
 else if(mode==='status')f.summary.status='RUNNING';
 else if(mode==='extra')f.summary.privatePlan={password:'DO_NOT_OUTPUT'};
 else if(mode==='selection')f.summary.selectionPin={...f.selected,bytes:3};
 else if(mode==='empty')f.summary.inputPins=[];
 else if(mode==='pin')f.summary.inputPins[0].sha256='0'.repeat(64);
 else f.summary.inputPins[0]={...f.summary.inputPins[0],unapproved:true};
 assert.throws(()=>f.run(),/POINT_AUDIT_/);
});
