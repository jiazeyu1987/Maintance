'use strict';
const fpEsc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fpCard=(title,body)=>`<section class="card"><div class="cardhead"><h2>${fpEsc(title)}</h2></div><div class="pad">${body}</div></section>`;
const fpRow=(k,v)=>`<div class="kv"><span>${fpEsc(k)}</span><b>${fpEsc(v||'—')}</b></div>`;
const fpNames={test:'测试服',prod:'正式服',backup:'审查服'};
const fpStatus=x=>({built:'构建完成',running:'执行中',succeeded:'执行成功',failed:'执行失败',interrupted:'执行中断',tested:'测试已验收','test-deployed':'测试待验收','prod-deployed':'正式待验收','prod-accepted':'正式已验收','backup-deployed':'审查待验收',completed:'三服验收完成','test-restored':'测试前端已恢复','prod-restored':'正式前端已恢复','backup-restored':'审查前端已恢复'}[x]||x||'尚未登记');
let fpState=null,fpCommits=[],fpError='',fpLoading=false;
let fpSelected=localStorage.getItem('intruoyi:frontendPatch')||'';
const fpDraft=key=>sessionStorage.getItem('frontendPatch:'+key)||'';
const fpField=(label,key,value='',placeholder='')=>`<div class="field"><label>${fpEsc(label)}</label><input class="input" data-draft="${fpEsc(key)}" value="${fpEsc(fpDraft(key)||value)}" placeholder="${fpEsc(placeholder)}"></div>`;
async function fpApi(path,payload){
 const token=localStorage.getItem('token');if(!token)throw Error('请先在 Spug 首页登录');
 const r=await fetch('/release-center/api/applications/intruoyi/'+path,{method:payload?'POST':'GET',headers:{'Content-Type':'application/json','X-Token':token},...(payload?{body:JSON.stringify(payload)}:{})});
 const result=await r.json();if(!r.ok)throw Error(result.error||'请求失败 '+r.status);return result;
}
function fpButton(label,action,enabled=true,env='',extra=''){
 const busy=fpState?.jobs.some(j=>j.status==='running');
 return `<button class="primary" data-front-action="frontend-patch-${action}" data-target="${env}" ${extra} ${busy||!enabled?'disabled':''}>${fpEsc(label)}</button>`;
}
function fpRender(){
 const app=document.getElementById('app');
 if(!fpState){app.innerHTML=fpCard('前端补丁',fpEsc(fpError||'读取中…')+'<p><a href="/home">返回 Spug 登录</a></p>');return;}
 const p=fpState.frontendPatches.find(x=>x.releaseTag===fpSelected);
 const baselines=fpState.frontendPatchBaselines||[];
 const targets=p?(p.observedBaseline?fpState.frontendPatchEnvironments:fpState.environments):(baselines.length?fpState.frontendPatchEnvironments:fpState.environments);
 const base=fpState.environments.prod?.releaseTag||'';
 const choices=[...baselines.map(b=>({value:'live:'+b.id,label:'现场基线 · '+b.releaseTag+' · '+b.gitCommit.slice(0,12)})),...fpState.packages.filter(x=>x.releaseTag===base).map(x=>({value:'package:'+x.releaseTag,label:'历史发布包 · '+x.releaseTag}))];
 const selectedBase=fpDraft('base')||choices[0]?.value||'';
 let html='<div class="heading"><div><h1>前端补丁</h1><p class="sub">固定源码 → 构建前端 → 测试验收 → 正式验收 → 审查验收</p></div></div>';
 if(fpError)html+=`<div class="errorbox" role="alert">${fpEsc(fpError)}</div>`;
 html+=fpCard('构建前端补丁',`<p>只构建前端镜像。各服保留原前端容器作为恢复点，后端及数据库保持运行。</p><p>其他电脑发布后，本机没有原包时，可读取三服实际程序并登记现场补丁基线。这不导入历史发布包，也不证明数据库结构一致。</p>`+fpButton('读取并登记三服补丁基线','register-baseline')+`<div class="field"><label>适用主版本 / 补丁基线</label><select id="fp-base" class="input"><option value="">请选择明确的补丁基线</option>${choices.map(x=>`<option value="${fpEsc(x.value)}" ${selectedBase===x.value?'selected':''}>${fpEsc(x.label)}</option>`).join('')}</select></div>`+fpField('源码提交（完整 Git 提交号）','commit','','选择已提交的前端修复')+`<datalist id="fp-commits">${fpCommits.map(c=>`<option value="${fpEsc(c.commit)}">${fpEsc(c.message)}</option>`).join('')}</datalist>`+fpButton('构建前端补丁','build',choices.some(x=>x.value===selectedBase))+' '+fpButton('刷新三服版本','refresh',!!baselines.length||Object.keys(fpState.environments).length>=3));
 html+=fpCard('固定补丁包',`<select id="fp-package" class="input"><option value="">请选择补丁包</option>${fpState.frontendPatches.map(x=>`<option value="${fpEsc(x.releaseTag)}" ${x.releaseTag===fpSelected?'selected':''}>${fpEsc(x.releaseTag)} · ${fpEsc(fpStatus(x.stage))}</option>`).join('')}</select>`+(p?fpRow('适用主版本',p.baseReleaseTag)+fpRow('补丁版本',p.releaseTag)+fpRow('源码提交',p.gitCommit)+fpRow('包摘要',p.packageSha256)+fpRow('包存储',p.nasDirectory||p.directory):''));
 html+='<div class="grid three">'+Object.entries(fpNames).map(([env,name])=>{
  const e=targets[env]||{},same=e.frontendPatchTag===p?.releaseTag;
  const eligible=Boolean(p&&e.releaseTag===p.baseReleaseTag&&(!e.frontendPatchTag||e.frontendPatchTag<p.releaseTag)&&(env==='test'||env==='prod'&&p.accepted.test&&targets.test?.frontendPatchTag===p.releaseTag||env==='backup'&&p.accepted.prod&&targets.prod?.frontendPatchTag===p.releaseTag));
  const original=fpState.jobs.find(j=>j.action==='frontend-patch-deploy'&&j.target===env&&j.releaseTag===p?.releaseTag&&j.effectsStarted&&!j.frontendRestoredBy);
  return fpCard(name,fpRow('主版本',e.releaseTag)+fpRow('前端补丁',e.frontendPatchTag||'无补丁')+fpRow('状态',p?fpStatus(p.accepted[env]?'已验收':p.deployments[env]?.status):'—')+`<p><a href="${fpEsc(fpState.application.targets[env].url||fpState.application.targets[env].entryUrl||'')}" target="_blank" rel="noopener">打开${name}</a></p>`+fpField('操作依据 / 实际验收结论',env)+fpButton('发布到'+name,'deploy',eligible,env)+' '+fpButton('验收通过','accept',same&&p?.deployments[env]?.status==='succeeded',env)+(original?'<hr>'+fpButton('恢复本次升级前的前端','restore',true,env,`data-original="${fpEsc(original.id)}"`)+'<p class="sub">仅恢复该任务保留的原前端；不恢复数据库，不改变后端。</p>':''));
 }).join('')+'</div>';
 html+=fpCard('持久任务记录',fpState.jobs.filter(j=>j.action.startsWith('frontend-patch-')).slice(0,40).map(j=>`<details><summary>${fpEsc(j.id)} · ${fpEsc(j.action)} · ${fpEsc(fpStatus(j.status))}</summary>${fpRow('固定补丁',j.releaseTag)}${fpRow('当前步骤',j.currentStep)}${j.error?'<div class="errorbox">'+fpEsc(j.error)+'</div>':''}<pre>${fpEsc(j.logs.map(l=>l.time+' '+l.message).join('\n'))}</pre>${j.result?'<pre>'+fpEsc(JSON.stringify(j.result,null,2))+'</pre>':''}</details>`).join('')||'暂无补丁任务');
 app.innerHTML=html;
 app.querySelector('[data-draft="commit"]').setAttribute('list','fp-commits');
}
async function fpRefresh(){if(fpLoading)return;fpLoading=true;try{fpState=await fpApi('state');if(!fpState.application.capabilities.frontendPatch)throw Error('执行器尚未启用前端补丁');if(!fpCommits.length)fpCommits=await fpApi('commits');if(!fpSelected&&fpState.frontendPatches.length){fpSelected=fpState.frontendPatches[0].releaseTag;localStorage.setItem('intruoyi:frontendPatch',fpSelected);}fpRender();}catch(e){fpError=e.message;fpRender();}finally{fpLoading=false;}}
document.addEventListener('input',e=>{if(e.target.dataset.draft)sessionStorage.setItem('frontendPatch:'+e.target.dataset.draft,e.target.value);});
document.addEventListener('change',e=>{if(e.target.id==='fp-base'){sessionStorage.setItem('frontendPatch:base',e.target.value);fpRender();}if(e.target.id==='fp-package'){fpSelected=e.target.value;localStorage.setItem('intruoyi:frontendPatch',fpSelected);fpRender();}});
document.addEventListener('click',async e=>{
 const button=e.target.closest('[data-front-action]');if(!button||button.disabled)return;button.disabled=true;
 const action=button.dataset.frontAction,target=button.dataset.target,payload={applicationId:'intruoyi',requestId:crypto.randomUUID()};
 try{
  if(action==='frontend-patch-build'){const baseChoice=document.getElementById('fp-base').value;if(baseChoice.startsWith('live:'))payload.baselineId=baseChoice.slice(5);else if(baseChoice.startsWith('package:'))payload.baseReleaseTag=baseChoice.slice(8);else throw Error('请选择补丁基线');payload.commit=fpDraft('commit').trim();}
  else if(!['frontend-patch-refresh','frontend-patch-register-baseline'].includes(action)){payload.releaseTag=fpSelected;payload.target=target;payload.note=fpDraft(target).trim();if(payload.note.length<5)throw Error('请填写至少5字的真实操作或验收依据');}
  if(action==='frontend-patch-restore'){if(!confirm('确认只恢复'+fpNames[target]+'本次升级前的前端？')){fpRender();return;}payload.originalJobId=button.dataset.original;}
  const result=await fpApi('actions/'+action,payload);window.fpLastJobId=result.id;fpError='';await fpRefresh();
 }catch(error){fpError=error.message;fpRender();}
});
fpRefresh();setInterval(()=>{if(!document.querySelector('input:focus,select:focus'))fpRefresh();},3000);
