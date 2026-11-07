'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {filterRows,catalogFailure}=require('./package-catalog.js');
const rows=[
 {packageId:'full',kind:'backup-full',application:'intruoyi',servers:['172.30.30.57'],time:'2026-11-03T13:00:00Z',version:'v1',nasPaths:['//nas/full'],status:'indexed'},
 {packageId:'patch',kind:'backend-patch',application:'intruoyi',servers:['172.30.30.58'],time:'2026-11-04T01:00:00Z',version:'v2',nasPaths:['//nas/patch'],status:'incomplete'},
 {packageId:'unknown',kind:'unknown',application:'unknown',servers:[],time:null,nasPaths:[],status:'unknown'}
];
test('date descending, unknown dates last and ascending supported',()=>{
 assert.deepEqual(filterRows(rows,{}).map(x=>x.packageId),['patch','full','unknown']);
 assert.deepEqual(filterRows(rows,{order:'asc'}).map(x=>x.packageId),['full','patch','unknown']);
});
test('combined type, server, date, search and status filters',()=>{
 assert.deepEqual(filterRows(rows,{kind:'backup-full',server:'172.30.30.57',from:'2026-11-03',to:'2026-11-03',query:'V1',status:'indexed'}).map(x=>x.packageId),['full']);
 assert.equal(filterRows(rows,{kind:'backend-patch',server:'172.30.30.57'}).length,0);
 assert.equal(filterRows(rows,{query:'nas/patch'}).length,1);
 assert.equal(filterRows(rows,{to:'2026-11-02'}).length,0);
});
test('input rows are immutable and XSS-like search is treated as text',()=>{
 const before=JSON.stringify(rows);assert.equal(filterRows(rows,{query:'<script>'}).length,0);assert.equal(JSON.stringify(rows),before);
});

test('expired sessions require login while missing permission does not',()=>{
 const expired=catalogFailure(403,{error:'Spug login required'});
 assert.equal(expired.loginRequired,true);assert.match(expired.message,/登录已失效/);
 assert.equal(catalogFailure(401,{}).loginRequired,true);
 const denied=catalogFailure(403,{error:'Spug permission required: schedule.schedule.view'});
 assert.equal(denied.loginRequired,false);assert.match(denied.message,/查看权限/);
 assert.doesNotMatch(denied.message,/重新登录/);
});

test('other denied requests and executor failures are not mislabeled as expired login',()=>{
 for(const [status,body] of [[403,{error:'Request origin refused'}],[403,null],[502,{error:'Spug login required'}]]){
  const failure=catalogFailure(status,body);assert.equal(failure.loginRequired,false);assert.match(failure.message,new RegExp('HTTP '+status));
 }
});

const fs=require('node:fs'),vm=require('node:vm');
async function failedPage(status,error,token='session') {
 const elements=new Map();
 const make=tag=>({tag,children:[],hidden:false,disabled:false,value:'',textContent:'',addEventListener(){},append(...values){this.children.push(...values);},replaceChildren(...values){this.children=values;}});
 const get=id=>{if(!elements.has(id))elements.set(id,make('div'));return elements.get(id);};
 const context={document:{getElementById:get,createElement:make},localStorage:{getItem:()=>token},
  fetch:async()=>({ok:false,status,json:async()=>({error})}),setTimeout,clearTimeout,Intl,Date,console};
 vm.runInNewContext(fs.readFileSync(require.resolve('./package-catalog.js'),'utf8'),context);
 await new Promise(resolve=>setImmediate(resolve));
 return get('catalog-problem');
}
test('login failures show a safe login entry and permission failures do not',async()=>{
 for(const token of ['session',null]){
  const problem=await failedPage(403,'Spug login required',token);
  const link=problem.children.find(child=>child.tag==='a');assert.ok(link,'login recovery link is visible');
  assert.equal(link.href,'/');assert.equal(link.target,undefined,'login works without a popup');
  assert.match(link.textContent,/登录 Spug/);assert.equal(problem.hidden,false);
 }
 const denied=await failedPage(403,'Spug permission required: schedule.schedule.view');
 assert.equal(denied.children.some(child=>child.tag==='a'),false);
 assert.match(denied.children[0].textContent,/查看权限/);
});
