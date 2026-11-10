'use strict';
// Local selection contracts only: no browser import, login, HTTP or execution.
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),vm=require('node:vm');
const test=require('node:test');
const acorn=require('C:/Users/D01021/Documents/ChatGPT/IntRuoyiE2E/node_modules/acorn');
const ROOT=path.resolve(__dirname,'../../..');
const TEMPLATE='C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/historical-registration-plan-r1.private.json';
const SIMPLE=path.join(ROOT,'ops/spug/smallapp-ui/simple.js');
const HELPER=path.join(__dirname,'verify_goal_readonly.cjs');
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const templateRaw=fs.readFileSync(TEMPLATE),simpleRaw=fs.readFileSync(SIMPLE),helperRaw=fs.readFileSync(HELPER);
assert.equal(sha(templateRaw),'def93cfb18192a38875e9e7edaccf45927c14398fe3eb3c46bcda7ca08b3def4','APPROVED_R4_INPUT_TEMPLATE_CHANGED');
assert.equal(sha(simpleRaw),'de7afc7cec4cabd06e6262123a38ebcb5b33b50e679e890861c0e8d7adc8b0f0','PRODUCT_SELECTION_SOURCE_CHANGED');
const template=JSON.parse(templateRaw),simpleSource=simpleRaw.toString('utf8'),helperSource=helperRaw.toString('utf8');
assert.equal(template.state,'PLAN_ONLY');
// Keep only public binding fields in the VM and any assertion diagnostics.
const bindings=template.simpleSettings.bindings.map(b=>({product:b.product,server:b.server,mode:b.mode,
 applicationId:b.applicationId,selectable:b.selectable,overwriteTargetServers:b.overwriteTargetServers}));
const legacy=bindings.filter(b=>b.applicationId==='intruoyi-PROD57-20261019');
assert.equal(legacy.length,1);assert.equal(legacy[0].selectable,false);
const historical=bindings.filter(b=>b.applicationId==='intruoyi-59-safe-20261024-v1');
assert.equal(historical.length,1);assert.equal(historical[0].selectable,false);
const current=bindings.filter(b=>b.selectable&&b.product==='intruoyi'&&b.server==='172.30.30.57'&&b.mode==='safe');
assert.equal(current.length,1);
const parse=source=>acorn.parse(source,{ecmaVersion:'latest',sourceType:'script'});
function walk(node,visit){
 if(!node||typeof node!=='object')return;visit(node);
 for(const value of Object.values(node)){
  if(Array.isArray(value))value.forEach(item=>walk(item,visit));
  else if(value&&typeof value==='object')walk(value,visit);
 }
}
function declarator(source,name){
 const found=[];walk(parse(source),node=>{if(node.type==='VariableDeclarator'&&node.id.name===name)found.push(node);});
 assert.equal(found.length,1,'EXACT_PRODUCT_DECLARATION_REQUIRED');return source.slice(found[0].start,found[0].end);
}
function auditNodes(tree){
 const states=[],identities=[];
 walk(tree,node=>{
  if(node.type==='VariableDeclarator'&&node.id.name==='state'&&node.init?.type==='AwaitExpression'&&
   node.init.argument?.callee?.object?.name==='frame'&&node.init.argument?.callee?.property?.name==='evaluate')states.push(node);
  if(node.type==='BlockStatement')for(let i=1;i<node.body.length;i++){
   const next=node.body[i],call=next.expression;
   if(next.type==='ExpressionStatement'&&call?.callee?.name==='need'&&call.arguments[1]?.value==='SOURCE_BINDING_IDENTITY_FAILED'){
    const declaration=node.body[i-1];assert.equal(declaration.type,'VariableDeclaration');
    assert.equal(declaration.declarations.length,1);assert.equal(declaration.declarations[0].id.name,'binding');
    identities.push({declaration,binding:declaration.declarations[0],check:next});
   }
  }
 });
 assert.equal(states.length,1,'EXACT_AUDIT_STATE_REQUIRED');assert.equal(identities.length,1,'EXACT_IDENTITY_CHECK_REQUIRED');
 return {state:states[0],identity:identities[0]};
}
const auditTree=parse(helperSource),nodes=auditNodes(auditTree);
const callback=nodes.state.init.argument.arguments[0];assert.equal(callback.type,'ArrowFunctionExpression');
const stateCode='('+helperSource.slice(callback.start,callback.end)+')()';
const identityCode=helperSource.slice(nodes.identity.declaration.start,nodes.identity.check.end);
const productCode='const '+declarator(simpleSource,'S')+';const '+declarator(simpleSource,'currentBinding')+';';
function page(binding,{restore=true,application=binding.applicationId,onlyBinding=false,controls={}}={}){
 const route=Object.entries(template.simpleSettings.catalogueRestoreBindings).find(([,ref])=>ref===binding.applicationId);
 if(restore)assert.ok(route,'REAL_TEMPLATE_RESTORE_ROUTE_REQUIRED');
 const packageId=route?.[0]||'local-contract-point';
 const values={'simple-product':binding.product,'simple-server':binding.server,'simple-mode':binding.mode,application,...controls};
 const elements=Object.fromEntries(Object.entries(values).map(([id,value])=>[id,{value}]));
 elements.point={options:[{value:''},{value:packageId}]};
 const document={getElementById:id=>elements[id],querySelector:selector=>elements[selector.slice(1)]};
 const context=vm.createContext({document,simpleConfig:{bindings:structuredClone(onlyBinding?[binding]:bindings)},
  catalogRestore:restore?{routeApplicationId:route[1],packageId}:null,
  need:(value,code)=>{if(!value)throw Error(code);}});
 vm.runInContext(productCode,context);
 return {context,packageId,run:code=>vm.runInContext(code,context),audit(){
  return vm.runInContext('const state='+stateCode+';'+identityCode+';({state,binding});',context);
 }};
}
function plain(value){return JSON.parse(JSON.stringify(value));}

test('real approved legacy route is accepted by product and audit without backup eligibility',()=>{
 const p=page(legacy[0]);
 assert.equal(p.run('currentBinding().applicationId'),legacy[0].applicationId);
 assert.equal(p.run('currentBinding().selectable'),false);
 const actual=p.audit();
 assert.equal(actual.binding.applicationId,legacy[0].applicationId);
 assert.equal(actual.state.application,legacy[0].applicationId);
 assert.equal(actual.state.source,legacy[0].server);
 assert.deepEqual(plain(actual.state.accepted),[p.packageId]);
 assert.deepEqual(plain(actual.binding.overwriteTargetServers),legacy[0].overwriteTargetServers);
});

test('real retired 59 route uses its exact historical binding',()=>{
 const p=page(historical[0]);assert.equal(p.run('currentBinding().selectable'),false);
 assert.equal(p.audit().binding.applicationId,historical[0].applicationId);
});

test('normal backup still selects current source and excludes nonselectable legacy',()=>{
 const p=page(current[0],{restore:false});assert.equal(p.run('currentBinding().selectable'),true);
 assert.equal(p.audit().binding.applicationId,current[0].applicationId);
 assert.notEqual(p.run('currentBinding().applicationId'),legacy[0].applicationId);
});

test('nonselectable legacy alone cannot become a normal backup source',()=>{
 const p=page(legacy[0],{restore:false,onlyBinding:true});
 assert.equal(p.run('currentBinding()'),undefined);
 assert.throws(()=>p.audit(),/SOURCE_BINDING_IDENTITY_FAILED/);
});

test('legacy route cannot accept page application for another available current binding',()=>{
 const p=page(legacy[0],{application:current[0].applicationId});
 assert.equal(p.run('currentBinding().applicationId'),legacy[0].applicationId);
 assert.throws(()=>p.audit(),/SOURCE_BINDING_IDENTITY_FAILED/);
});

test('missing current binding never passes merely because other bindings exist',()=>{
 for(const control of ['simple-product','simple-server','simple-mode']){
  const p=page(legacy[0],{controls:{[control]:'unregistered-contract-value'}});
  assert.equal(p.run('currentBinding()'),undefined);
  assert.throws(()=>p.audit(),/SOURCE_BINDING_IDENTITY_FAILED/);
 }
});

test('page observation projects only required public binding identity and targets',()=>{
 const actual=page(current[0],{restore:false}).audit();
 assert.deepEqual(Object.keys(actual.state).sort(),['accepted','application','binding','source']);
 assert.deepEqual(Object.keys(actual.state.binding).sort(),['applicationId','overwriteTargetServers']);
 assert.deepEqual(plain(actual.state.binding),plain(actual.binding));
});

test('all matrix, confirmation, identity and zero business write guards remain unchanged',()=>{
 function normalize(value){
  if(Array.isArray(value))return value.map(normalize);
  if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value)
   .filter(([key])=>!['start','end','raw'].includes(key)).map(([key,item])=>[key,normalize(item)]));
  return value;
 }
 function protectedUi(tree){
  const selected=auditNodes(tree);
  selected.state.init={type:'Literal',value:'BINDING_OBSERVATION'};
  selected.identity.binding.init={type:'Literal',value:'BINDING_SELECTION'};
  const ui=tree.body.filter(n=>n.type==='ExpressionStatement'&&n.expression?.callee?.property?.name==='catch'&&n.expression.callee.object?.callee?.async);
  assert.equal(ui.length,1,'EXACT_ORIGINAL_UI_BODY_REQUIRED');
  const eligible=[],counts=[];
  walk(ui[0],node=>{
   if(node.type==='VariableDeclarator'&&node.id.name==='eligible')eligible.push(node);
   if(node.type==='CallExpression'&&node.callee.name==='need'&&node.arguments[1]?.value==='RESTORABLE_POINTS_REQUIRED')counts.push(node);
   if(node.type==='BlockStatement')node.body=node.body.filter(statement=>{
    if(statement.type==='ExpressionStatement'&&statement.expression.callee?.name==='assertSelectedPointState'){
     assert.equal(helperSource.slice(statement.start,statement.end),'assertSelectedPointState(selectedPoint,state);');return false;
    }
    if(statement.type==='TryStatement'&&statement.block.body[0]?.expression?.callee?.name==='verifyPointAuditInputs'){
     assert.equal(helperSource.slice(statement.start,statement.end),"try{verifyPointAuditInputs(selectedPoint);}catch(error){report.status='FAIL';report.errorCode='POINT_AUDIT_INPUT_CHANGED';process.exitCode=1;}");return false;
    }
    return true;
   });
  });
  assert.equal(eligible.length,1);assert.equal(counts.length,1);
  eligible[0].init={type:'Literal',value:'APPROVED_ELIGIBLE_SELECTION_SEAM'};
  counts[0].arguments[0]={type:'Literal',value:'APPROVED_ELIGIBLE_COUNT_SEAM'};
  const declarations=name=>{
   const found=[];for(const row of tree.body)if(row.type==='VariableDeclaration')
    for(const declaration of row.declarations)if(declaration.id.name===name)found.push(declaration);
   assert.equal(found.length,1,'EXACT_ORIGINAL_DECLARATION_REQUIRED: '+name);return found[0];
  };
  const globals=['TASK','PRIVATE','ORIGIN','CATALOGUE','need','sha','expectedLatest','targets','output','helperRaw','privateDir',
   'browser','page','frame','latest','sequence','finished','pending','responseErrors'].map(declarations);
  const helpers=['save','phase','observe','idle','filter','allVisiblePages'].map(name=>{
   const found=tree.body.filter(n=>n.type==='FunctionDeclaration'&&n.id.name===name);assert.equal(found.length,1);return found[0];
  });
  const report=declarations('report').init;
  const evidence=tree.body.filter(n=>n.type==='ExpressionStatement'&&(
   n.expression.callee?.name==='need'&&n.expression.arguments[1]?.value==='ORIGINAL_OBSERVATION_ALREADY_EXISTS'||
   n.expression.callee?.object?.name==='fs'&&n.expression.callee.property?.name==='mkdirSync'||
   n.expression.callee?.name==='save'&&n.expression.arguments[0]?.value==='executed-helper.cjs'));
  assert.equal(evidence.length,3,'EXCLUSIVE_ORIGINAL_EVIDENCE_GUARDS_REQUIRED');
  return normalize({ui:ui[0],globals,helpers,reportProperties:report.properties.slice(1),evidence});
 }
 // Original whole-file AST: 6bce041b... . The approved input/schema APIs are
 // covered by test_main_new_point_ui_binding.cjs; freeze the original actual
 // UI and evidence here, normalizing only the four exact approved UI seams.
 assert.equal(sha(JSON.stringify(protectedUi(parse(helperSource)))),'cad31c5fc87269da16fcb7018238380017aea9e090cea4ebbf307755d5518c3c');
});

test('real approved template, production JS and audit input are never modified by local contracts',()=>{
 assert.ok(fs.readFileSync(TEMPLATE).equals(templateRaw));
 assert.ok(fs.readFileSync(SIMPLE).equals(simpleRaw));
 assert.ok(fs.readFileSync(HELPER).equals(helperRaw));
});
