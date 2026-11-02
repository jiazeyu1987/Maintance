'use strict';
const bpEsc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const bpCard=(title,body)=>`<section class="card"><div class="cardhead"><h2>${bpEsc(title)}</h2></div><div class="pad">${body}</div></section>`;
const bpRow=(k,v)=>`<div class="kv"><span>${bpEsc(k)}</span><b>${bpEsc(v||'—')}</b></div>`;
const bpNames={test:'测试服',prod:'正式服',backup:'审查服'};
const bpStatus=x=>({built:'构建完成',running:'执行中',succeeded:'执行成功',failed:'执行失败',interrupted:'执行中断',tested:'测试已验收','test-deployed':'测试待验收','prod-deployed':'正式待验收','prod-accepted':'正式已验收','backup-deployed':'审查待验收',completed:'三服验收完成','test-restored':'测试后端已恢复','prod-restored':'正式后端已恢复','backup-restored':'审查后端已恢复'}[x]||x||'尚未登记');
let bpState=null,bpCommits=[],bpError='',bpLoading=false;
let bpSelected=localStorage.getItem('intruoyi:backendPatch')||'';
const bpDraft=key=>sessionStorage.getItem('backendPatch:'+key)||'';
const bpField=(label,key,value='',placeholder='')=>`<div class="field"><label>${bpEsc(label)}</label><input class="input" data-draft="${bpEsc(key)}" value="${bpEsc(bpDraft(key)||value)}" placeholder="${bpEsc(placeholder)}"></div>`;
async function bpApi(path,payload){
 const token=localStorage.getItem('token');if(!token)throw Error('请先在 Spug 首页登录');
 const r=await fetch('/release-center/api/applications/intruoyi/'+path,{method:payload?'POST':'GET',headers:{'Content-Type':'application/json','X-Token':token},...(payload?{body:JSON.stringify(payload)}:{})});
 const result=await r.json();if(!r.ok)throw Error(result.error||'请求失败 '+r.status);return result;
}
function bpButton(label,action,enabled=true,env='',extra=''){
 const busy=bpState?.jobs.some(j=>j.status==='running');
 return `<button class="primary" data-back-action="backend-patch-${action}" data-target="${env}" ${extra} ${busy||!enabled?'disabled':''}>${bpEsc(label)}</button>`;
}
function bpCleanup(j){
 const report=j.postReleaseCleanup||j.result?.postReleaseCleanup;if(!report)return '';
 const rows=Object.entries(report.environments||{}).map(([env,r])=>`<p>${bpEsc(bpNames[env]||env)}：${bpEsc(r.status)} · 容器 ${(r.removed||[]).filter(x=>x.kind==='container').length} · 镜像 ${(r.removed||[]).filter(x=>x.kind==='image').length} · 文件字节 ${bpEsc(r.bytes||0)} · 磁盘可用变化 ${bpEsc(r.freeBytesDelta??'未测量')}</p><p>保留：${bpEsc((r.retained||[]).map(x=>x.reason).join('；'))}</p>${r.error?'<div class="errorbox">'+bpEsc(r.error)+'</div>':''}`).join('');
 return `<details><summary>发布后资源清理：${bpEsc(report.status)}</summary>${rows}${report.error?'<div class="errorbox">'+bpEsc(report.error)+'</div>':''}<button data-back-action="retry-release-cleanup" data-original="${bpEsc(j.cleanupOf||j.id)}" ${bpState?.jobs.some(x=>x.status==='running')?'disabled':''}>重新检查并清理失效资源</button><pre>${bpEsc(JSON.stringify(report,null,2))}</pre></details>`;
}
function bpRender(){
 const app=document.getElementById('app');
 if(!bpState){app.innerHTML=bpCard('后端补丁',bpEsc(bpError||'读取中…')+'<p><a href="/home">返回 Spug 登录</a></p>');return;}
 const p=bpState.backendPatches.find(x=>x.releaseTag===bpSelected);
 const baselines=bpState.backendPatchBaselines||[];
 const targets=bpState.backendPatchEnvironments||{};
 const base=bpState.environments.prod?.releaseTag||'';
 const choices=baselines.map(b=>({value:'live:'+b.id,label:'现场基线 · '+b.releaseTag+' · '+b.gitCommit.slice(0,12)}));
 const selectedBase=bpDraft('base')||choices[0]?.value||'';
 let html='<div class="heading"><div><h1>后端补丁</h1><p class="sub">固定源码 → 构建后端 → 测试验收 → 正式验收 → 审查验收</p></div></div>';
 if(bpError)html+=`<div class="errorbox" role="alert">${bpEsc(bpError)}</div>`;
 html+=bpCard('构建后端补丁',`<p>只构建一个完整后端 JAR，保留原后端供恢复。不执行数据库结构、数据、菜单权限或配置迁移。切换期间短暂停止访问和后台写者，新程序启动时启用临时数据库只读保护；启动尝试写库则失败并保持关闭。</p><p>其他电脑发布后，本机没有原包时，可读取三服实际程序并登记现场补丁基线。登记实际 JAR、前端、数据库结构和迁移台账；三服起点必须一致。</p>`+bpButton('读取并登记三服补丁基线','register-baseline')+`<div class="field"><label>适用主版本 / 补丁基线</label><select id="bp-base" class="input"><option value="">请选择明确的补丁基线</option>${choices.map(x=>`<option value="${bpEsc(x.value)}" ${selectedBase===x.value?'selected':''}>${bpEsc(x.label)}</option>`).join('')}</select></div>`+bpField('兼容性评审（确认前端、现有库、配置、依赖及恢复兼容；没有启动写库）','review')+bpField('源码提交（完整 Git 提交号）','commit','','选择已提交的后端修复')+`<datalist id="bp-commits">${bpCommits.map(c=>`<option value="${bpEsc(c.commit)}">${bpEsc(c.message)}</option>`).join('')}</datalist>`+bpButton('构建后端补丁','build',choices.some(x=>x.value===selectedBase))+' '+bpButton('刷新三服版本','refresh',!!baselines.length||Object.keys(bpState.environments).length>=3));
 html+=bpCard('固定补丁包',`<select id="bp-package" class="input"><option value="">请选择补丁包</option>${bpState.backendPatches.map(x=>`<option value="${bpEsc(x.releaseTag)}" ${x.releaseTag===bpSelected?'selected':''}>${bpEsc(x.releaseTag)} · ${bpEsc(bpStatus(x.stage))}</option>`).join('')}</select>`+(p?bpRow('适用主版本',p.baseReleaseTag)+bpRow('补丁版本',p.releaseTag)+bpRow('JAR 摘要',p.jarSha256)+bpRow('JAR 大小',Math.ceil(p.jarBytes/1048576)+' MiB')+bpRow('源码提交',p.gitCommit)+bpRow('包摘要',p.packageSha256)+bpRow('包存储',p.nasDirectory||p.directory):''));
 html+='<div class="grid three">'+Object.entries(bpNames).map(([env,name])=>{
  const e=targets[env]||{},same=e.backendPatchTag===p?.releaseTag;
  const eligible=Boolean(p&&e.releaseTag===p.baseReleaseTag&&(!e.backendPatchTag||e.backendPatchTag<p.releaseTag)&&(env==='test'||env==='prod'&&p.accepted.test&&targets.test?.backendPatchTag===p.releaseTag||env==='backup'&&p.accepted.prod&&targets.prod?.backendPatchTag===p.releaseTag));
  const original=bpState.jobs.find(j=>j.action==='backend-patch-deploy'&&j.target===env&&j.releaseTag===p?.releaseTag&&j.effectsStarted&&!j.backendRestoredBy);
  return bpCard(name,bpRow('主版本',e.releaseTag)+bpRow('后端补丁',e.backendPatchTag||'无补丁')+bpRow('状态',p?bpStatus(p.accepted[env]?'已验收':p.deployments[env]?.status):'—')+`<p><a href="${bpEsc(bpState.application.targets[env].url||bpState.application.targets[env].entryUrl||'')}" target="_blank" rel="noopener">打开${name}</a></p>`+bpField('操作依据 / 实际验收结论',env)+bpButton('发布到'+name,'deploy',eligible,env)+' '+bpButton('验收通过','accept',same&&p?.deployments[env]?.status==='succeeded',env)+(original?'<hr>'+bpButton('恢复本次升级前的后端','restore',true,env,`data-original="${bpEsc(original.id)}"`)+'<p class="sub">仅恢复该任务原后端程序，不回退业务数据；不运行数据库恢复。</p>':''));
 }).join('')+'</div>';
 html+=bpCard('持久任务记录',bpState.jobs.filter(j=>j.action.startsWith('backend-patch-')||j.cleanupAction==='backend-patch-accept').slice(0,40).map(j=>`<details><summary>${bpEsc(j.id)} · ${bpEsc(j.action)} · ${bpEsc(bpStatus(j.status))}</summary>${bpRow('固定补丁',j.releaseTag)}${bpRow('当前步骤',j.currentStep)}${j.error?'<div class="errorbox">'+bpEsc(j.error)+'</div>':''}<pre>${bpEsc(j.logs.map(l=>l.time+' '+l.message).join('\n'))}</pre>${j.action==='backend-patch-build'&&j.status==='failed'&&j.sealedPackage?bpButton('校验原包并重传 NAS','retry-upload',true,'',`data-original="${bpEsc(j.id)}"`):''}${bpCleanup(j)}${j.result?'<pre>'+bpEsc(JSON.stringify(j.result,null,2))+'</pre>':''}</details>`).join('')||'暂无补丁任务');
 app.innerHTML=html;
 app.querySelector('[data-draft="commit"]').setAttribute('list','bp-commits');
}
async function bpRefresh(){if(bpLoading)return;bpLoading=true;try{bpState=await bpApi('state');if(!bpState.application.capabilities.backendPatch)throw Error('执行器尚未启用后端补丁');if(!bpCommits.length)bpCommits=await bpApi('commits');if(!bpSelected&&bpState.backendPatches.length){bpSelected=bpState.backendPatches[0].releaseTag;localStorage.setItem('intruoyi:backendPatch',bpSelected);}bpRender();}catch(e){bpError=e.message;bpRender();}finally{bpLoading=false;}}
document.addEventListener('input',e=>{if(e.target.dataset.draft)sessionStorage.setItem('backendPatch:'+e.target.dataset.draft,e.target.value);});
document.addEventListener('change',e=>{if(e.target.id==='bp-base'){sessionStorage.setItem('backendPatch:base',e.target.value);bpRender();}if(e.target.id==='bp-package'){bpSelected=e.target.value;localStorage.setItem('intruoyi:backendPatch',bpSelected);bpRender();}});
document.addEventListener('click',async e=>{
 const button=e.target.closest('[data-back-action]');if(!button||button.disabled)return;button.disabled=true;
 const action=button.dataset.backAction,target=button.dataset.target,payload={applicationId:'intruoyi',requestId:crypto.randomUUID()};
 try{
  if(action==='backend-patch-build'){const baseChoice=document.getElementById('bp-base').value;if(baseChoice.startsWith('live:'))payload.baselineId=baseChoice.slice(5);else if(baseChoice.startsWith('package:'))payload.baseReleaseTag=baseChoice.slice(8);else throw Error('请选择补丁基线');payload.commit=bpDraft('commit').trim();payload.note=bpDraft('review').trim();if(payload.note.length<5)throw Error('请填写真实兼容性评审');}
  else if(!['backend-patch-refresh','backend-patch-register-baseline','retry-release-cleanup','backend-patch-retry-upload'].includes(action)){payload.releaseTag=bpSelected;payload.target=target;payload.note=bpDraft(target).trim();if(payload.note.length<5)throw Error('请填写至少5字的真实操作或验收依据');}
  if(['backend-patch-deploy','backend-patch-restore'].includes(action)&&['prod','backup'].includes(target)){payload.confirmation=prompt('确认操作'+bpNames[target]+'，请输入 PROD');if(payload.confirmation!=='PROD')throw Error('未确认 PROD，未执行');}
  if(action==='backend-patch-restore'){if(!confirm('确认只恢复'+bpNames[target]+'本次升级前的后端？')){bpRender();return;}payload.originalJobId=button.dataset.original;}
  if(action==='retry-release-cleanup')payload.jobId=button.dataset.original;
  if(action==='backend-patch-retry-upload'){payload.originalJobId=button.dataset.original;payload.note='校验已封存原包后重传，不重新编译';}
  const result=await bpApi('actions/'+action,payload);window.bpLastJobId=result.id;bpError='';await bpRefresh();
 }catch(error){bpError=error.message;bpRender();}
});
bpRefresh();setInterval(()=>{if(!document.querySelector('input:focus,select:focus'))bpRefresh();},3000);
