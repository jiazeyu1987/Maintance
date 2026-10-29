'use strict';
const fbtNames=['发布总览','构建版本','候选包','测试服发布','正式起点演练','正式服发布','审查服发布','任务记录'];
let fbtPage=Number(new URLSearchParams(location.search).get('page')||0);
if(!Number.isInteger(fbtPage)||fbtPage<0||fbtPage>7)fbtPage=0;
let fbtState=null,fbtSource=null,fbtError='',fbtBusy=false,fbtLoading=false;
let fbtSelected=localStorage.getItem('fenbeitong:selected')||'';
const fbtEsc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fbtCard=(title,body)=>`<section class="card"><div class="cardhead"><h2>${fbtEsc(title)}</h2></div><div class="pad">${body}</div></section>`;
const fbtRow=(label,value)=>`<div class="kv"><span>${fbtEsc(label)}</span><b>${fbtEsc(value||'—')}</b></div>`;
const fbtStatus=x=>({built:'构建完成',running:'运行中',succeeded:'执行成功',failed:'执行失败',interrupted:'执行中断','not-installed':'未部署',stopped:'已停止','test-deployed':'测试部署完成，待验收',tested:'测试验收通过',rehearsed:'演练启动检查完成','rehearsal-passed':'演练已确认','prod-deployed':'正式部署完成，待验收','prod-accepted':'正式验收通过','backup-deployed':'审查部署完成，待验收',completed:'三服验收完成'}[x]||x||'尚未读取');
const fbtButton=(name,action,enabled=true,extra='')=>`<button class="primary" data-fbt-action="${action}" ${fbtBusy||!enabled?'disabled':''} ${extra}>${fbtEsc(name)}</button>`;
const fbtPackage=()=>fbtState?.packages.find(p=>p.releaseTag===fbtSelected);
const fbtCanDeploy=(p,state,env)=>Boolean(p&&!p.rejected&&(!state.environments[env]?.releaseTag||state.environments[env].releaseTag<p.releaseTag)&&(env==='test'||env==='prod'&&p.accepted?.test&&p.rehearsal?.accepted||env==='backup'&&p.accepted?.prod&&state.environments.prod?.packageSha256===p.packageSha256));
const fbtNote=key=>`<div class="field"><label for="note">实际验收或核对结论（至少5字）</label><textarea id="note" data-note-key="${fbtEsc(key)}" class="input" rows="3">${fbtEsc(sessionStorage.getItem('fenbeitong:note:'+key)||'')}</textarea></div>`;

async function fbtApi(path,payload){
 const token=localStorage.getItem('token');if(!token)throw Error('请先返回 Spug 登录。');
 const response=await fetch('/release-center/api/'+path,{method:payload?'POST':'GET',headers:{'X-Token':token,'Content-Type':'application/json'},...(payload?{body:JSON.stringify(payload)}:{})});
 const result=await response.json();if(!response.ok)throw Error(result.error||'请求失败：'+response.status);return result;
}
function fbtRender(){
 document.getElementById('nav').innerHTML=fbtNames.map((name,i)=>`<a class="nav ${i===fbtPage?'active':''}" href="fenbeitong.html?app=fenbeitong&amp;page=${i}">${fbtEsc(name)}</a>`).join('');
 if(!fbtState){document.getElementById('app').innerHTML=fbtCard('发布状态',fbtEsc(fbtError||'读取中…')+'<p><a href="/home">返回 Spug 首页</a></p>');return;}
 fbtBusy=fbtState.jobs.some(j=>j.status==='running');
 const p=fbtPackage();
 let html=`<div class="heading"><div><div class="eyebrow">FENBEITONG / RELEASE</div><h1>${fbtNames[fbtPage]}</h1><p class="sub">独立 Node 程序 · 同一个完整包发布三服 · 业务数据留在各自服务器</p></div></div>`;
 if(fbtError)html+=`<div role="alert" class="errorbox">${fbtEsc(fbtError)}</div>`;
 html+=fbtCard('当前发布包',`<select id="package" class="input"><option value="">请选择发布包</option>${fbtState.packages.map(x=>`<option value="${fbtEsc(x.releaseTag)}" ${fbtSelected===x.releaseTag?'selected':''}>${fbtEsc(x.releaseTag)} · ${fbtStatus(x.stage)}${x.rejected?' · 验收失败':''}</option>`).join('')}</select>`);
 if(fbtBusy)html+='<div class="notice">任务正在执行。关闭或刷新页面不会重新提交，请在任务记录中查看结果。</div>';
 const detail=p?fbtRow('版本',p.releaseTag)+fbtRow('源码类型','本地源码快照')+fbtRow('源码摘要',p.sourceSha256)+fbtRow('包摘要',p.packageSha256)+fbtRow('镜像身份',p.imageId)+fbtRow('阶段',fbtStatus(p.stage)):'请先构建并选择发布包。';
 if(fbtPage===0){
  html+='<div class="grid three">'+Object.entries(fbtState.application.targets).map(([key,t])=>{const e=fbtState.environments[key];return fbtCard(t.label,fbtRow('服务器',t.host)+fbtRow('版本',e?.releaseTag)+fbtRow('状态',fbtStatus(e?.status))+fbtRow('最近核对',e?.observedAt));}).join('')+'</div>';
  html+=fbtCard('读取三服现状',fbtButton('刷新三服版本','register-targets')+' '+fbtButton('检查三服发布条件','check-prerequisites')+'<p class="sub">只读核对连接、Docker、存储空间及端口占用；不会部署或导入业务数据。</p>');
 }
 if(fbtPage===1){
  html+=fbtCard('构建本地源码快照',fbtRow('源码目录',fbtState.application.repo)+fbtRow('快照摘要',fbtSource?.commit)+fbtRow('纳入文件数',fbtSource?.fileCount)+fbtRow('运行时镜像',fbtState.application.nodeImage)+'<p>读取当前保存到磁盘的程序文件，固定快照后构建完整镜像。源码在冻结期间变化则失败。</p><p class="sub">本目录没有 Git 仓库，此处不表示已提交 Git 代码。包中不包含 .env、本地业务数据、凭据和测试记录。</p>'+fbtButton('刷新源码快照','refresh-source')+' '+fbtButton('构建发布包','build-release',!!fbtSource));
 }
 if(fbtPage===2)html+=fbtCard('完整包身份',detail)+fbtCard('存储与数据',fbtRow('发布包目录',p?.directory||fbtState.application.packageStoragePath)+'<p>完整包包含程序镜像与发布清单。每次构建生成新包；后续三服使用该包原件。</p><p>各服独立保存分贝通配置及数据。本次发布不分发本机业务数据，也不自动同步分贝通或写入金蝶。</p>');
 if([3,5,6].includes(fbtPage)){
  const env={3:'test',5:'prod',6:'backup'}[fbtPage],action={test:'publish-test',prod:'promote-prod',backup:'promote-backup'}[env],accept={test:'mark-tested',prod:'accept-prod',backup:'accept-backup'}[env];
  const current=fbtState.environments[env],eligible=fbtCanDeploy(p,fbtState,env);
  html+=fbtCard(fbtState.application.targets[env].label+'发布',detail+fbtRow('当前运行版本',current?.releaseTag)+'<p>停止本助手、保存其数据恢复点、安装固定原包，再检查镜像身份、版本和健康状态。IntRuoyi 容器保持原状。</p>'+fbtButton('发布到'+fbtState.application.targets[env].label,action,eligible));
  html+=fbtCard('人工功能验收',`<p>从对应 IntRuoyi 的分贝通入口实际检查功能，再填写结论。健康检查不能替代功能验收；入口地址、授权或业务凭据未配置时，不能确认通过。</p><p><a href="${fbtEsc(fbtState.application.targets[env].entryUrl)}" target="_blank" rel="noopener">打开对应 IntRuoyi</a></p>`+fbtNote(env+':'+fbtSelected)+fbtButton('确认验收通过',accept,!!p&&!p.rejected&&current?.packageSha256===p.packageSha256)+' '+fbtButton('记录验收失败','reject-acceptance',!!p&&current?.packageSha256===p.packageSha256)+ '<p class="sub">验收失败会禁止此包继续晋级。发布不会自动猜测回退方式，也不会清除失败证据。</p>');
 }
 if(fbtPage===4){
  html+=fbtCard('正式起点隔离演练',detail+'<p>已有正式助手时，短暂停止助手取得一致数据副本，再恢复原助手；首次部署使用空数据起点。使用候选原包启动独立容器，禁止连接外部网络，验证版本与启动。副本不切换为正式服务。</p><p class="sub">本版没有独立业务迁移脚本契约。演练证明程序启动路径，不代表外部系统联调或完整报销业务已通过；业务验收仍需真实环境验证。</p>'+fbtButton('执行正式起点演练','prepare-rehearsal',!!p&&!p.rejected&&!!p.accepted?.test)+fbtRow('演练结果',fbtStatus(p?.rehearsal?.status))+fbtRow('正式起点版本',p?.rehearsal?.origin?.releaseTag||'未部署或尚未演练')+fbtNote('rehearsal:'+fbtSelected)+fbtButton('确认演练结果','accept-rehearsal',p?.rehearsal?.status==='succeeded'));
 }
 if(fbtPage===7||fbtPage===0||fbtPage===1){
  html+=fbtCard('任务记录',fbtState.jobs.slice(0,fbtPage===7?100:6).map(j=>`<details><summary>${fbtEsc(j.id)} · ${fbtEsc(j.action)} · ${fbtStatus(j.status)}</summary><p>${fbtEsc(j.releaseTag||'未分配版本')} · ${fbtEsc(j.createdAt)}</p><p>${fbtEsc(j.currentStep||'')}</p>${j.error?`<div class="notice error">${fbtEsc(j.error)}</div>`:''}<pre>${fbtEsc(j.logs.map(x=>x.time+' '+x.message).join('\n'))}</pre>${j.result?`<pre>${fbtEsc(JSON.stringify(j.result,null,2))}</pre>`:''}${['failed','interrupted'].includes(j.status)&&!j.resolution?`<p>核对按钮只关闭明确未产生远端影响的失败；已产生影响或状态未知时停止，交由技术人员处理。</p>${fbtNote(j.id)}${fbtButton('核对原失败任务','resolve-task',true,`data-job-id="${fbtEsc(j.id)}"`)}`:''}</details>`).join('')||'暂无任务');
 }
 document.getElementById('app').innerHTML=html;
}
async function fbtRefresh(){
 if(fbtLoading)return;fbtLoading=true;
 try{const next=await fbtApi('applications/fenbeitong/state');if(next.application?.id!=='fenbeitong')throw Error('应用身份不符');fbtState=next;if(fbtPage===1&&!fbtSource)fbtSource=(await fbtApi('applications/fenbeitong/commits'))[0];if(!fbtSelected&&next.packages.length){fbtSelected=next.packages[0].releaseTag;localStorage.setItem('fenbeitong:selected',fbtSelected);}fbtRender();}
 catch(e){fbtError=e.message;fbtRender();}finally{fbtLoading=false;}
}
document.addEventListener('input',event=>{if(event.target.dataset.noteKey)sessionStorage.setItem('fenbeitong:note:'+event.target.dataset.noteKey,event.target.value);});
document.addEventListener('change',event=>{if(event.target.id==='package'){fbtSelected=event.target.value;localStorage.setItem('fenbeitong:selected',fbtSelected);fbtRender();}if(event.target.id==='application'&&event.target.value!=='fenbeitong')location.href='./?app='+encodeURIComponent(event.target.value)+'&page=0';});
document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-fbt-action]');if(!button||button.disabled)return;
 button.disabled=true;const action=button.dataset.fbtAction;
 try{
  if(action==='refresh-source'){fbtSource=(await fbtApi('applications/fenbeitong/commits'))[0];fbtError='';fbtRender();return;}
  const payload={applicationId:'fenbeitong',requestId:crypto.randomUUID()};
  if(action==='build-release')payload.sourceSha256=fbtSource.commit;
  else if(!['register-targets','check-prerequisites','resolve-task'].includes(action))payload.releaseTag=fbtSelected;
  if(['mark-tested','accept-prod','accept-backup','accept-rehearsal','reject-acceptance','resolve-task'].includes(action)){
   const group=action==='resolve-task'?button.closest('details'):button.closest('section');payload.note=group.querySelector('textarea').value;
   if(payload.note.trim().length<5)throw Error('请填写至少5字的实际验收或核对结论。');
  }
  if(action==='resolve-task')payload.jobId=button.dataset.jobId;
  await fbtApi('applications/fenbeitong/actions/'+action,payload);fbtError='';await fbtRefresh();
 }catch(e){fbtError=e.message;fbtRender();}
});
(async()=>{try{const catalog=await fbtApi('applications');const picker=document.getElementById('application');picker.innerHTML=catalog.applications.map(a=>`<option value="${fbtEsc(a.id)}" ${a.id==='fenbeitong'?'selected':''}>${fbtEsc(a.name)}</option>`).join('');picker.disabled=false;await fbtRefresh();}catch(e){fbtError=e.message;fbtRender();}})();
setInterval(()=>{if(!document.querySelector('textarea:focus,select:focus'))fbtRefresh();},3000);
