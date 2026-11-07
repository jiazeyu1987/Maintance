'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const rows=[
 {packageId:'full',checkKey:'b'.repeat(64),kind:'backup-full',application:'intruoyi',servers:['172.30.30.57'],time:'2026-11-03T13:00:00Z',status:'indexed'},
 {packageId:'patch',checkKey:'a'.repeat(64),version:'2026-11-03-12-15-42',kind:'backend-patch',application:'intruoyi',servers:['172.30.30.58'],time:'2026-11-04T01:00:00Z',status:'indexed'}
];
async function page(verification) {
 const nodes=new Map();let active;
 function make(tag){return {tag,children:[],dataset:{},listeners:{},value:'',textContent:'',hidden:false,open:false,
  get childNodes(){return this.children;},get options(){return this.children;},
  addEventListener(name,handler){this.listeners[name]=handler;},append(...values){this.children.push(...values);},
  replaceChildren(...values){this.children=values;},setAttribute(name,value){this[name]=value;},
  focus(){active=this;},showModal(){this.open=true;},close(){this.open=false;this.fire('close');},
  fire(name,props={}){return this.listeners[name]?.({preventDefault(){},...props});}};}
 function get(id){if(!nodes.has(id))nodes.set(id,make('div'));return nodes.get(id);}
 get('catalog-order').value='desc';
 let restored;
 const context={document:{getElementById:get,createElement:make},openCatalogRestore:row=>{restored=row;},localStorage:{getItem:()=> 'unit-session'},
  Option:function(text,value){return {textContent:text,value};},setTimeout,clearTimeout,Intl,Date,console,
  fetch:async(url)=>url.includes('/verify/')?verification(url):({ok:true,json:async()=>({schemaVersion:'PackageCatalog/v1',items:rows,complete:true,sources:[]})})};
 vm.runInNewContext(fs.readFileSync(require.resolve('./package-catalog.js'),'utf8'),context);
 await new Promise(resolve=>setImmediate(resolve));
 return {get,ids:()=>get('catalog-body').children.map(row=>row.dataset.packageId),active:()=>active,restored:()=>restored};
}
test('filter fields belong to a modal while the catalogue panel starts with toolbar and table',()=>{
 const html=fs.readFileSync(require.resolve('./index.html'),'utf8');
 const modal=html.match(/<dialog\b[^>]*id="catalog-filter-dialog"[^>]*>[\s\S]*?<\/dialog>/)?.[0];
 assert.ok(modal,'filter dialog exists');
 for(const name of ['kind','server','application','status','from','to','query','order'])assert.ok(modal.includes('id="catalog-'+name+'"'),name+' field is in dialog');
 const panel=html.match(/<section id="package-catalog"[\s\S]*?<\/section>/)[0];
 assert.ok(panel.includes('catalog-filter-open'));assert.ok(panel.includes('catalog-table-wrap'));
 assert.equal(panel.includes('class="catalog-filters"'),false,'no inline filter grid takes list space');
});

test('program version is the column value and immutable package ID remains in details',async()=>{
 const html=fs.readFileSync(require.resolve('./index.html'),'utf8');
 assert.ok(html.includes('<th>程序版本</th>'));
 const p=await page(), rendered=p.get('catalog-body').children;
 assert.equal(rendered[0].children[4].textContent,'2026-11-03-12-15-42');
 assert.equal(rendered[1].children[4].textContent,'未记录');
 const details=rendered[0].children[7].children.find(x=>x.tag==='details');
 assert.ok(details.children.some(x=>x.textContent==='包编号：patch'));
 p.get('catalog-filter-open').fire('click');p.get('catalog-query').value='2026-11-03-12-15-42';
 p.get('catalog-filter-form').fire('submit');assert.deepEqual(p.ids(),['patch']);
 p.get('catalog-filter-open').fire('click');p.get('catalog-query').value='full';
 p.get('catalog-filter-form').fire('submit');assert.deepEqual(p.ids(),['full']);
});

test('operations column verifies the chosen row and exposes missing files without changing other rows',async()=>{
 const html=fs.readFileSync(require.resolve('./index.html'),'utf8');assert.ok(html.includes('>操作</th>'));
 let requested;const p=await page(async url=>{requested=url;return {ok:true,json:async()=>({schemaVersion:'PackagePresence/v1',status:'missing',checkedAt:'2026-11-04T06:30:00Z',existingFiles:1,missingFileCount:1,copies:[{path:'NAS package',status:'missing',missingFiles:['release.tar']}]})};});
 const row=p.get('catalog-body').children[0],ops=row.children[8];
 assert.equal(ops.children[0].textContent,'验证');await ops.children[0].fire('click');
 assert.ok(requested.endsWith('/verify/'+'a'.repeat(64)+'?refresh=1'));
 const changed=p.get('catalog-body').children[0].children[8];
 assert.ok(changed.children.some(x=>x.textContent.includes('文件缺失')));
 assert.equal(p.get('catalog-body').children[1].children[8].children[0].textContent,'验证');
});

test('restore row action passes only the chosen backup row to the shared restore dialog',async()=>{
 const p=await page(),rendered=p.get('catalog-body').children;
 const patch=rendered[0].children[8].children.find(x=>x.textContent==='恢复');
 assert.ok(patch);assert.equal(patch.disabled,true);
 const backup=rendered[1].children[8].children.find(x=>x.textContent==='恢复');
 assert.ok(backup);assert.equal(backup.disabled,false);await backup.fire('click');
 assert.equal(p.restored().packageId,'full');
 const html=fs.readFileSync(require.resolve('./index.html'),'utf8');
 assert.ok(html.includes('id="catalog-restore-dialog"'));
 assert.ok(html.includes('id="catalog-restore-form-host"'));
});

test('invalid or conflicting catalogue metadata cannot initiate a restore even for a backup kind',async()=>{
 const p=await page(),backup=rows[0];
 const prior=backup.status;backup.status='conflict';
 try{
  p.get('catalog-filter-form').fire('submit');
  const restore=p.get('catalog-body').children.find(x=>x.dataset.packageId==='full').children[8].children.find(x=>x.textContent==='恢复');
  assert.equal(restore.disabled,true);assert.match(restore.title,/清单/);
 }finally{backup.status=prior;}
});

test('restore dialog hides already bound fields without removing the shared tab fields',()=>{
 const css=fs.readFileSync(require.resolve('./package-catalog.css'),'utf8');
 const html=fs.readFileSync(require.resolve('./index.html'),'utf8');
 const hidden=css.match(/([^{}]+)\{display:none\}/g)||[];
 for(const field of ['#catalog-restore-package','#simple-product','#simple-nas','#simple-package','label[for="simple-product"]','label[for="simple-nas"]','label[for="simple-package"]']){
  assert.ok(hidden.some(rule=>rule.split('{')[0].split(',').some(selector=>selector.trim()==='#catalog-restore-dialog '+field)),field+' is hidden only inside restore dialog');
 }
 for(const id of ['simple-product','simple-nas','simple-package'])assert.ok(html.includes('id="'+id+'"'),id+' stays in the shared form');
});
test('editing modal fields does not change rows until apply, then closes and returns focus',async()=>{
 const p=await page();assert.deepEqual(p.ids(),['patch','full']);
 p.get('catalog-filter-open').fire('click');assert.equal(p.get('catalog-filter-dialog').open,true);
 p.get('catalog-kind').value='backup-full';p.get('catalog-kind').fire('change');
 assert.deepEqual(p.ids(),['patch','full']);p.get('catalog-filter-form').fire('submit');
 assert.deepEqual(p.ids(),['full']);assert.equal(p.get('catalog-filter-dialog').open,false);
 assert.equal(p.active(),p.get('catalog-filter-open'));assert.match(p.get('catalog-filter-open').textContent,/1/);
});
test('cancel, Escape, reset draft and invalid dates preserve the applied list',async()=>{
 const p=await page();p.get('catalog-filter-open').fire('click');p.get('catalog-kind').value='backend-patch';p.get('catalog-filter-form').fire('submit');
 assert.deepEqual(p.ids(),['patch']);
 p.get('catalog-filter-open').fire('click');p.get('catalog-kind').value='backup-full';p.get('catalog-filter-cancel').fire('click');
 assert.deepEqual(p.ids(),['patch']);p.get('catalog-filter-open').fire('click');assert.equal(p.get('catalog-kind').value,'backend-patch');
 p.get('catalog-reset').fire('click');assert.equal(p.get('catalog-kind').value,'');assert.deepEqual(p.ids(),['patch']);
 // Escape also closes when the search input would otherwise consume it to clear text.
 p.get('catalog-filter-dialog').fire('keydown',{key:'Escape'});assert.equal(p.get('catalog-filter-dialog').open,false);
 p.get('catalog-filter-open').fire('click');assert.equal(p.get('catalog-kind').value,'backend-patch');
 p.get('catalog-from').value='2026-11-05';p.get('catalog-to').value='2026-11-01';p.get('catalog-filter-form').fire('submit');
 assert.equal(p.get('catalog-filter-dialog').open,true);assert.equal(p.get('catalog-filter-error').hidden,false);assert.deepEqual(p.ids(),['patch']);
 p.get('catalog-reset').fire('click');p.get('catalog-filter-form').fire('submit');assert.deepEqual(p.ids(),['patch','full']);assert.equal(p.get('catalog-filter-open').textContent,'筛选');
});
