'use strict';
const names=['发布总览','构建版本','候选包详情','测试服发布','隔离升级验证','正式服发布','备用服发布','任务记录','环境与基线','产物清理'];
const icons=['▦','＋','▣','◈','◇','↗','⇄','≡','⚙','▤'];
let applications=[],applicationId=new URLSearchParams(location.search).get('app')||localStorage.getItem('releaseCenterApplication')||'',selectionEpoch=0,refreshingEpoch=null;
const storageKey=key=>`releaseCenter:${applicationId}:${key}`;
const appLocal={getItem:key=>localStorage.getItem(storageKey(key)),setItem:(key,value)=>localStorage.setItem(storageKey(key),value)};
const appSession={getItem:key=>sessionStorage.getItem(storageKey(key)),setItem:(key,value)=>sessionStorage.setItem(storageKey(key),value)};
let page=Number(new URLSearchParams(location.search).get('page')||0), state=null, commits=[], error='', selected=appLocal.getItem('releaseCenterPackage')||'', busy=false;
let chosenCommit=appLocal.getItem('releaseCenterCommit')||'', packageChoiceMade=appLocal.getItem('releaseCenterPackage')!==null;
let connectionError='';
if(!Number.isInteger(page)||page<0||page>9)page=0;
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const card=(title,body,right='')=>`<section class="card"><div class="cardhead"><h2>${title}</h2>${right}</div>${body}</section>`;
const badge=(text,kind='')=>`<span class="badge ${kind}"><i class="dot"></i>${esc(text)}</span>`;
const kv=(name,value)=>`<div class="kv"><span>${name}</span><b>${value}</b></div>`;
const table=(headers,rows)=>`<table><thead><tr>${headers.map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map(x=>`<td>${x}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
const head=(title,desc,actions='')=>`<div class="heading"><div><div class="eyebrow">RELEASE / RELEASE CENTER</div><h1>${title}</h1><div class="sub">${desc}</div></div><div class="actions">${actions}</div></div>`;
const appUrl=p=>'?'+new URLSearchParams({app:applicationId,page:String(p)});
const link=(label,p)=>`<a class="button" href="${esc(appUrl(p))}">${label}</a>`;
const notice=text=>`<div class="notice">${text}</div>`;
const unresolved=j=>!['check-prerequisites','scan-artifacts','clean-artifacts'].includes(j.action)&&['failed','interrupted'].includes(j.status)&&!j.resolution&&!technicallyReconciled(j);
const remoteApplication=()=>state?.application.runtimeKind==='remote-intruoyi';
const technicalRecords=p=>[...Object.values(p?.outcomes||{}).map(outcome=>outcome.technical),...(p?.technicalHistory||[])];
const technicallyReconciled=j=>{
 if(!remoteApplication()||!j.reconciledBy)return false;
 const p=state.packages.find(candidate=>candidate.releaseTag===j.releaseTag),success=state.jobs.find(job=>job.id===j.reconciledBy);
 if(!p||success?.status!=='succeeded'||success.releaseTag!==j.releaseTag||success.target!==j.target)return false;
 return technicalRecords(p).some(record=>record?.jobId===j.reconciledBy&&record.env===(j.target||j.env||j.payload?.target)&&record.releaseTag===p.releaseTag&&record.packageSha256===p.packageSha256&&record.status==='passed'&&['version','upgrade','login'].every(key=>record.checks?.[key]?.status==='passed'));
};
const historicalBusinessFailure=j=>remoteApplication()&&j.action==='reject-acceptance'&&j.status==='failed'&&!j.effectsStarted&&!['prod','backup'].includes(j.target);
const technicalAction=id=>remoteApplication()&&['mark-tested','accept-rehearsal','verify-prod','verify-backup'].includes(id);
const technicalRecheckAllowed=(j,id)=>{
 if(!technicalAction(id)||j.status!=='failed')return false;
 const env=targetForAction(id),p=pkg(),proof=j.technicalVerification;
 if(historicalBusinessFailure(j)){const records=(p?.acceptances||[]).filter(record=>record.jobId===j.id);return records.length===1&&records[0].env===env&&j.target===env;}
 return proof?.status==='failed'&&proof.env===env&&proof.jobId===j.id&&proof.releaseTag===p?.releaseTag&&proof.packageSha256===p?.packageSha256&&p?.outcomes?.[env]?.deployment?.status==='succeeded';
};
const blockingFailure=(j,id)=>unresolved(j)&&!technicalRecheckAllowed(j,id);
const capability=key=>state?.application.capabilities?.[key];
const actionCapabilities={'initialize-baseline':'initializeBaseline','audit-baseline':'auditBaseline','register-targets':'registerTargets','restore-metadata':'restoreMetadata','build-release':'buildRelease','prepare-rehearsal':'prepareRehearsal','upgrade-rehearsal':'prepareRehearsal','accept-rehearsal':'prepareRehearsal'};
const capabilityAllowed=id=>{const key=actionCapabilities[id];return !key||(!remoteApplication()?capability(key)!==false:capability(key)===true);};
const deploymentBlock=id=>!['publish-test','promote-prod','promote-backup'].includes(id)||!pkg()?null:state.deploymentBlocks?.[selected]===undefined?'发布顺序信息尚未读取，暂不能发布。':state.deploymentBlocks[selected][id]||null;
const action=(label,id,enabled=true)=>{const blocked=deploymentBlock(id);return `<button class="primary" data-action="${id}" ${!enabled||blocked||!capabilityAllowed(id)||busy||(state&&state.jobs.some(j=>blockingFailure(j,id)&&j.releaseTag===selected)&&!['build-release','reset-rehearsal','audit-baseline','register-targets','restore-metadata'].includes(id))?'disabled':''}>${label}</button>${blocked?`<div class="notice warn" data-deployment-block="${id}">${esc(blocked)}</div>`:''}`;};
const pkg=()=>state.packages.find(x=>x.releaseTag===selected);
const testDeploymentAction=(stage,p)=>{const retry=remoteApplication()&&state.testRetries?.[selected];const button=action(retry?'按原包重试测试发布':'发布到测试服','publish-test',stage==='built'&&!p?.baseline);return retry?button.replace('data-action="publish-test"',`data-action="publish-test" data-retry-of="${esc(retry)}"`)+notice('已核对并恢复原起点；本次新尝试保留原任务 '+esc(retry)+' 的恢复资料和失败记录。'):button;};
const running=()=>state.jobs.some(j=>j.status==='running'||(j.status==='interrupted'&&unresolved(j)));
const testAcceptance=()=>remoteApplication()?'mark-tested':'function-passed';
const rehearsalAcceptance=()=>remoteApplication()?'accept-rehearsal':'mark-tested';
const activeRehearsal=()=>pkg()?.rehearsals?.find(r=>r.id===pkg().activeRehearsal);
const sourceKey=()=>`releaseCenterRehearsalSource:${selected}`;
const rehearsalSource=()=>remoteApplication()?'prod':appSession.getItem(sourceKey())||'';
const statusText=value=>({succeeded:'执行成功',failed:'执行失败',interrupted:'执行中断',running:'执行中',ready:'基线已准备',upgraded:remoteApplication()?'升级完成，待技术检查':'升级完成，待业务验收',passed:remoteApplication()?'原记录已通过':'业务验收通过'}[value]||value||'尚未执行');
const pretty=value=>typeof value==='string'?value:JSON.stringify(value,null,2);
const testTailRoot=j=>{if(!remoteApplication())return null;const root=j.action==='resolve-task'&&j.originalDeploymentJobId?state.jobs.find(x=>x.id===j.originalDeploymentJobId):j;return root&&unresolved(root)&&root.action==='publish-test'&&root.target==='test'&&root.effectsStarted&&root.releaseTag===j.releaseTag?root:null;};
const preparationPhase=j=>j.continuationRemotePhase||j.remotePhase;
const preparationTailRoot=j=>{if(!remoteApplication())return null;if(j.action==='resolve-task'&&(j.target!=='rehearsal'||j.sourceEnv!=='prod'||j.payload?.decision!=='retry'))return null;const root=j.action==='resolve-task'&&j.originalPreparationJobId?state.jobs.find(x=>x.id===j.originalPreparationJobId):j;return root&&unresolved(root)&&root.action==='prepare-rehearsal'&&root.target==='rehearsal'&&root.sourceEnv==='prod'&&root.effectsStarted&&root.remoteStatusRequired&&((preparationPhase(root)==='restore-starting'&&root.remoteProgress?.status==='failed')||(preparationPhase(root)==='capture-complete'&&root.remoteProgress?.status==='succeeded'&&root.remoteProgress?.phase==='capture-complete'))&&!root.remoteStatusError&&root.remoteProgress.jobId===root.id&&root.releaseTag===j.releaseTag?root:null;};
const restoredDeployment=j=>remoteApplication()&&j.effectsStarted&&['publish-test','upgrade-rehearsal','promote-prod','promote-backup'].includes(j.action);
const actionTarget={ 'publish-test':'test','function-passed':'test','prepare-rehearsal':'rehearsal','upgrade-rehearsal':'rehearsal','mark-tested':'test','accept-rehearsal':'rehearsal','promote-prod':'prod','accept-prod':'prod','promote-backup':'backup','accept-backup':'backup','verify-prod':'prod','verify-backup':'backup'};
const targetForAction=id=>id==='mark-tested'&&!remoteApplication()?'rehearsal':actionTarget[id];
const targetName=env=>remoteApplication()?(state.application.targets?.[env]?.label||{test:'测试服',prod:'正式服',backup:'备用服',rehearsal:'隔离验证'}[env]||env||'未指定'):({test:'测试服',prod:'演示正式服',backup:'演示备用服',rehearsal:'隔离验证'}[env]||env||'未指定');
const targetAddress=env=>remoteApplication()?(state.application.targets?.[env]?.url||'未配置运行入口'):`127.0.0.1:${state.application.ports?.[env]}`;
const maintenanceText=env=>{const entry=state.environments[env];return entry?.maintenanceUnknown||entry?.maintenanceError?'维护状态无法确认 · 需技术核对':entry?.maintenance===true?'维护中 · 写入暂停':entry?.maintenance===false?'业务写入状态：开放':'维护状态尚未读取';};
const detail=()=>{let p=pkg();return p?`<div class="pad">${kv('固定发布版本',`<span class="mono">${esc(p.releaseTag)}</span>`)}${kv('Git 提交',`<span class="mono">${esc(p.gitCommit.slice(0,12))}</span>`)}${kv('包 SHA256',`<span class="mono" title="${esc(p.packageSha256)}">${esc(p.packageSha256.slice(0,24))}…</span>`)}${kv('当前阶段',badge(p.stage))}${kv('用途',p.baseline?(remoteApplication()?'只读登记基线':'已登记演示基线'):'候选完整发布包')}</div>`:'<div class="pad sub">尚无构建完成的发布包。</div>'};
const flow=n=>`<section class="card flow">${['构建发布包',remoteApplication()?'测试服技术检查':'测试服验收','隔离升级验证','正式服发布','备用服发布'].map((x,i)=>`<div class="step ${i<n?'done':i===n?'current':''}"><div class="num">${i<n?'✓':i+1}</div><span>${x}</span></div>`).join('')}</section>`;
function envlink(env){
 if(!state.environments[env])return '';
 if(!remoteApplication())return `<a class="button envlink" target="_blank" rel="noopener" href="http://127.0.0.1:${state.application.ports[env]}">打开${{test:'测试',prod:'演示正式',backup:'演示备用',rehearsal:'隔离验证'}[env]}系统 ↗</a>`;
 const target=state.application.targets?.[env],entry=state.environments[env];
 if(entry.maintenanceUnknown||entry.maintenanceError)return '<div class="sidenote">维护状态待核对，暂不提供验收入口。</div>';
 const url=entry.maintenance===true?target?.acceptanceUrl:target?.url;
 if(!url)return `<div class="sidenote">${entry.maintenance===true?'维护验收入口尚未配置':'运行入口尚未配置'}</div>`;
 if(!/^https?:\/\//i.test(url))return '<div class="errorbox">运行入口必须配置为有效 HTTP(S) URL。</div>';
 return `<a class="button envlink" target="_blank" rel="noopener" href="${esc(url)}">打开${esc(targetName(env))}${entry.maintenance===true?'维护验收入口':'系统'} ↗</a>`;
}
async function api(path,body,identity=applicationId){const token=localStorage.getItem('token');if(!token)throw Error('请先登录 Spug，再进入发布中心。');const route=path==='applications'?path:'applications/'+encodeURIComponent(identity)+'/'+path;const response=await fetch('api/'+route,{method:body?'POST':'GET',headers:{'X-Token':token,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined,cache:'no-store'});const data=await response.json();if(!response.ok)throw Error(data.error||'请求失败');return data;}
function remoteExecution(j){
 if(!j.remoteStatusRequired)return '';
 if(j.remoteStatusError)return kv('远端执行状态','查询失败，结果待核实：'+esc(j.remoteStatusError));
 const r=j.remoteProgress;
 if(!r)return kv('远端执行状态','尚未取得回执，不能重复启动');
 const text={running:'远端仍在执行',succeeded:'远端阶段已完成；整体准备结果以任务验收为准',failed:'远端阶段失败',unknown:'进程已退出，阶段结果不确定'}[r.status]||'结果待核实';
 return kv('远端执行状态',esc(text))+kv('远端阶段',esc(r.phase))+kv('阶段记录时间',esc(r.observedAt));
}
function migrationPlan(j){
 const plan=j.migrationPlan;if(!Array.isArray(plan?.items))return '';
 const actions={APPLY:'执行迁移',SKIP_ALREADY_APPLIED:'已执行，保留历史',SKIP_ENV_NOT_ALLOWED:'目标环境不适用',SKIP_SCOPE_EXCLUDED:'发布范围排除',SKIP_IMMUTABLE:'由后继迁移替代',BLOCKED_LEDGER_STATE:'阻断：迁移台账异常',BLOCKED_CHECKSUM_MISMATCH:'阻断：校验和不符',BLOCKED_DEPENDENCY_MISSING:'阻断：缺少依赖',BLOCKED_PREREQUISITE_MISSING:'阻断：缺少前置条件',BLOCKED_SCOPE_DEPENDENCY:'阻断：依赖不在发布范围'};
 const excluded=plan.items.filter(item=>item.action==='SKIP_SCOPE_EXCLUDED').length;
 const planKey=storageKey('migrationPlan:'+j.id),expanded=sessionStorage.getItem(planKey)==='open';
 const rows=plan.items.map(item=>[esc(item.migrationId),esc(actions[item.action]||item.action),esc(item.reason||'未记录原因'),esc(item.allowedPublishScopes?.length?item.allowedPublishScopes.join('、'):'未限定')]);
 return `<details class="migration-plan" data-plan-key="${esc(planKey)}"${expanded?' open':''}><summary>迁移计划：${plan.items.length} 项${excluded?' · 发布范围排除 '+excluded+' 项':''}</summary><div class="sub">目标：${esc(targetName(plan.targetEnvironment))} · 本次发布范围：${esc(plan.publishScope||'未记录')}</div><div class="migration-plan-table">${table(['迁移编号','计划动作','原因','适用发布范围'],rows)}</div></details>`;
}
function jobResult(j){
 if(j.action==='check-prerequisites')return precheckResult(j);
 if(!j.result)return '';
 if(['inspect-interruption','reconcile-interruption'].includes(j.action))return notice(esc(j.result.detail||'核对结果已记录'))+`<details><summary>查看中断核对证据</summary><pre class="code">${esc(pretty(j.result))}</pre></details>`;
 if(!['recover-release','accept-recovery'].includes(j.action))return kv('执行结果',esc(pretty(j.result)));
 return kv('恢复后的程序版本',esc(j.result.releaseTag))+kv('业务访问',j.result.maintenance===true?'维护中，等待恢复验收':'旧版本已开放')+`<details><summary>查看恢复技术回执</summary><pre class="code">${esc(pretty(j.result.receipt))}</pre></details>`;
}
function completedRecoveries(p){
 return Object.entries(p.outcomes||{}).filter(([env,result])=>result.recovery?.status==='accepted').map(([env,result])=>{
  const job=state.jobs.find(j=>j.id===result.recovery.originalJobId);
  return `<div class="pad" data-recovery-completed>${notice(esc(targetName(env))+'：升级前版本已恢复并开放。')}${kv('已恢复版本',esc(job?.resolution?.restoredReleaseTag||job?.originState?.releaseTag||'未记录'))}${kv('恢复验收结果',esc(result.recovery.note))}${kv('验收人 / 时间',esc(result.recovery.actor)+' / '+esc(result.recovery.time))}<p class="sub">原失败记录继续保留；此候选版本没有发布成功。</p></div>`;
 }).join('');
}
function logs(all=false){
 const jobs=state.jobs.filter(j=>all||!selected||j.releaseTag===selected||(j.action==='build-release'&&j.status==='running'));
 return card('实际执行记录',jobs.length?`<div class="pad">${jobs.map(j=>`<article class="task-record"><h3>${esc(j.action)} ${badge(statusText(j.status),j.status==='failed'?'red':j.status==='succeeded'?'green':'orange')}</h3><div class="sub">任务 ${esc(j.id)} · 操作人 ${esc(j.actor)} · ${esc(j.createdAt)}</div>${kv('阶段 / 目标',esc(j.target||j.env||j.payload?.target||targetForAction(j.action)||'构建/登记'))}${j.currentStep?kv('当前或失败步骤',esc(pretty(j.currentStep))):''}${historicalBusinessFailure(j)?notice('历史业务问题：保留原失败记录，不属于当前三项发布成功判据。'):''}${j.error?`<div class="errorbox">${esc(j.error)}</div>`:''}${remoteExecution(j)}${migrationPlan(j)}${jobResult(j)}${j.outcomes?`<pre class="code">${esc(pretty(j.outcomes))}</pre>`:''}${j.payload?.note?kv(remoteApplication()?'任务备注':'本次人工备注',esc(j.payload.note)):''}${technicallyReconciled(j)?notice('后续真实技术检查已通过：'+esc(j.reconciledBy)+'；本条原失败记录保留。'):''}${j.resolution?`<div class="reviewbox"><h3>原任务技术处理（保留原执行状态）</h3>${kv('决定',j.resolution.decision==='reconciled'?'中断已核对，具体结果见关联核对任务':j.resolution.decision==='restored'?'已恢复升级前版本并开放业务':j.resolution.decision==='retry'?(j.resolution.resumeReceipt?(j.resolution.originalPreparationJobId?(j.resolution.resumeReceipt.kind==='captured-transfer'?'原快照传输与恢复完成，候选升级仍需单独执行':'保留隔离副本启动尾段恢复完成，候选升级仍需单独执行'):remoteApplication()?'同包测试部署收尾完成，技术结果见三项检查':'同包测试部署收尾完成，仍需功能验收'):'核对通过，允许返回原阶段操作'):'核对通过，放弃本任务')}${kv('核对任务',esc(j.resolution.jobId))}${j.resolution.supersededBy?kv('已验收替代版本',esc(j.resolution.supersededBy)):''}${kv('处理人 / 时间',esc(j.resolution.actor)+' / '+esc(j.resolution.time))}<p>${esc(j.resolution.note)}</p></div>`:''}<pre class="code">${esc((j.logs||[]).map(l=>l.time+'  '+l.message).join('\n'))}</pre></article>`).join('')}</div>`:'<div class="pad sub">尚未执行此包任务。</div>');
}
function technicalEvidence(p,env,evidence=p.outcomes?.[env]?.technical){
 const owner=state.jobs.find(job=>job.id===evidence?.jobId);
 const bound=!!owner&&owner.releaseTag===p.releaseTag&&owner.target===env&&evidence.env===env&&evidence.releaseTag===p.releaseTag&&evidence.packageSha256===p.packageSha256;
 const status=bound&&['running','passed','failed'].includes(evidence.status)?evidence.status:'pending';
 const checks=['version','upgrade','login'].map(key=>{const value=bound?evidence.checks?.[key]:null;return {key,status:['pending','running','passed','failed'].includes(value?.status)?value.status:'pending',error:value?.error};});
 return {evidence,bound,checks,status:status==='passed'&&(owner.status!=='succeeded'||!checks.every(check=>check.status==='passed'))?'pending':status};
}
function technicalBadge(status){return badge({pending:'待查',running:'进行中',passed:'通过',failed:'失败'}[status]||'待查',status==='passed'?'green':status==='failed'?'red':status==='running'?'orange':'gray');}
function technicalResults(p){
 const rows=['test','rehearsal','prod','backup'].map(env=>{
  const record=technicalEvidence(p,env),deployment=p.outcomes?.[env]?.deployment;
  const cells=record.checks.map(check=>technicalBadge(check.status)+(check.error?`<small>${esc(check.error)}</small>`:''));
  const openingError=record.bound&&record.evidence.phase==='opening'&&record.evidence.opening?.status==='failed';
  return [esc(targetName(env)),deployment?badge(statusText(deployment.status),deployment.status==='succeeded'?'green':deployment.status==='failed'?'red':'orange'):'尚未执行',...cells,technicalBadge(record.status)+(openingError?`<small>入口开放失败：${esc(record.evidence.opening.error||record.evidence.error||'请查看原任务并核对实际开放状态')}</small>`:''),esc(record.bound?record.evidence.jobId:record.evidence?'证据未绑定当前包':'尚无技术检查记录')];
 });
 const history=(p.acceptances||[]).map(record=>`<div class="reviewbox"><h3>${esc(record.action)} · 历史业务记录</h3>${kv('原任务 / 时间',esc(record.jobId||'未绑定')+' / '+esc(record.time))}<p>${esc(record.note)}</p></div>`).join('');
 const oldOutcomes=['test','rehearsal'].flatMap(env=>{const old=p.outcomes?.[env]?.acceptance;return old?[`<div class="reviewbox"><h3>${esc(targetName(env))} · 历史业务验收 ${esc(old.status)}</h3>${kv('原任务',esc(old.jobId))}<p>${esc(old.note||old.error||'未记录备注')}</p></div>`]:[];}).join('');
 const formal=['prod','backup'].map(env=>{const item=p.outcomes?.[env]?.acceptance;return [esc(targetName(env)),item?badge(item.status==='passed'?'业务验收通过':'业务验收失败',item.status==='passed'?'green':'red'):'等待业务验收',esc(item?.note||'—'),esc(item?.jobId||'—')];});
 return card('正式与备用业务验收',table(['环境','业务验收','验收说明','验收任务'],formal))+card('三项技术发布检查',`<div class="pad sub">版本与镜像、迁移与启动、Playwright 真实认证登录并进入页面分别记录；正式和备用服技术检查通过后，仍须人工业务验收才能开放业务。</div>`+table(['环境','部署执行','版本与镜像','迁移完整与启动正常','真实登录并进入页面','技术检查结果','检查任务'],rows))+(history||oldOutcomes?card('历史业务记录（不属于当前发布成功判据）',`<div class="pad">${history}${oldOutcomes}</div>`):'');
}
function stageResults(){
 const p=pkg();if(!p)return '';
 if(remoteApplication())return technicalResults(p);
 const jobs=state.jobs.filter(j=>j.releaseTag===selected);
 const stages=[['test','publish-test',testAcceptance()],['rehearsal','upgrade-rehearsal',rehearsalAcceptance()],['prod','promote-prod','accept-prod'],['backup','promote-backup','accept-backup']];
 const rows=stages.map(([env,deployAction,acceptAction])=>{
  const deploy=jobs.find(j=>j.action===deployAction),accepted=jobs.find(j=>j.action===acceptAction);
  const outcome=p.outcomes?.[env],deployment=outcome?.deployment,acceptance=outcome?.acceptance;
  const deploymentText=deployment?badge(statusText(deployment.status),deployment.status==='succeeded'?'green':deployment.status==='failed'?'red':'orange'):(deploy?`无独立记录；原任务：${badge(statusText(deploy.status),deploy.status==='succeeded'?'green':'orange')}`:'尚未执行');
  const acceptanceText=acceptance?badge(acceptance.status==='passed'?'业务验收通过':'业务验收失败',acceptance.status==='passed'?'green':'red')+(acceptance.note?`<small>${esc(acceptance.note)} · ${esc(acceptance.actor)} · ${esc(acceptance.time)}</small>`:''):(accepted?`无独立记录；原任务：${badge(statusText(accepted.status),accepted.status==='succeeded'?'green':'orange')}`:'尚未业务验收');
  return [esc(targetName(env)),deploymentText,acceptanceText,`<div>执行：${esc(deployment?.jobId||deploy?.id||'—')}</div><div>验收：${esc(acceptance?.jobId||accepted?.id||'—')}</div>`,esc(deployment?.status==='failed'?deployment.step||deployment.error||'见原任务错误':deploy?.error?deploy.currentStep||'见原任务错误':'—')];
 });
 const notes=(p.acceptances||[]).map(a=>`<div class="reviewbox"><h3>${esc(a.action)} · ${a.action==='reject-acceptance'?'验收失败': '人工验收记录'}</h3>${kv('任务 / 操作人',esc(a.jobId||jobs.find(j=>j.action===a.action&&j.payload?.note===a.note)?.id||'原记录未绑定任务')+' / '+esc(a.actor))}${kv('阶段 / 时间',esc(a.stage||targetForAction(a.action)||'')+' / '+esc(a.time))}<p>${esc(a.note)}</p></div>`).join('');
 return card('各阶段独立结果',table(['阶段','部署 / 升级执行','业务验收','关联任务','失败步骤'],rows)+(notes?`<div class="pad">${notes}</div>`:''));
}
function rehearsalHistory(){
 if(remoteApplication()){
  const rows=(pkg()?.rehearsals||[]).map(record=>{const technical=technicalEvidence(pkg(),'rehearsal',record.technical);return [esc(record.id),esc(targetName(record.source)),esc(record.originReleaseTag),technicalBadge(technical.status),`<span class="mono">${esc(record.originFingerprint)}</span><small>固定包 ${esc(record.packageSha256)}</small>`,esc(record.technical?.jobId||'尚无三项技术检查记录')];});
  return card('正式基线隔离验证记录',rows.length?table(['演练编号','起点来源','起点版本','技术检查','绑定身份','检查任务'],rows):'<div class="pad sub">尚无隔离验证记录；正式流量不会切入隔离环境。</div>');
 }
 const rows=(pkg()?.rehearsals||[]).map(r=>[esc(r.id),esc(targetName(r.source)),esc(r.originReleaseTag),`${badge(statusText(r.status),r.status==='passed'?'green':'orange')}<small>升级执行：${esc(r.deployment?statusText(r.deployment.status):'无独立记录')}</small><small>业务验收：${esc(r.acceptance?(r.acceptance.status==='passed'?'通过':'失败'):'无独立记录')}</small>`,`<span class="mono">${esc(r.originFingerprint)}</span><small>固定包 ${esc(r.packageSha256)}</small>`,`${esc(r.acceptance?.note||r.note||'尚未填写验收结果')}<small>操作人 ${esc(r.acceptance?.actor||r.actor||'—')} · 执行任务 ${esc(r.deployment?.jobId||r.jobId||'—')} · 验收任务 ${esc(r.acceptance?.jobId||'—')}</small>`]);
 return card('独立演练记录与已通过证据',rows.length?table(['演练编号','起点来源','起点版本','结果','绑定身份','验收备注'],rows):'<div class="pad sub">尚无演练记录。每次演练的起点、原包与验收结果独立保存。</div>');
}
function interruptionPanel(){
 if(!remoteApplication()||!capability('interruptionReconciliation'))return '';
 const pending=state.jobs.filter(j=>['failed','interrupted'].includes(j.status)&&!j.resolution&&!j.reconciledBy&&!['inspect-interruption','reconcile-interruption','check-prerequisites','scan-artifacts','clean-artifacts'].includes(j.action));
 const executing=state.jobs.some(j=>j.status==='running');
 const rows=pending.map(j=>{const evidence=j.interruptionInspection;return `<section class="reviewbox" data-interruption="${esc(j.id)}"><h3>${esc(j.id)} · ${esc(j.action)}</h3>${kv('固定版本',esc(j.releaseTag||'构建尚未分配版本'))}${kv('原步骤',esc(j.currentStep||'尚未开始'))}${evidence?notice(esc(evidence.detail))+kv('核对时间',esc(evidence.observedAt)):notice('中断后先核对原任务；不会因刷新页面自动重新发布。')}<button class="btn" data-action="inspect-interruption" ${executing?'disabled':''}>核对原任务执行状态</button><div class="field"><label>处理依据</label><textarea class="input" data-interruption-note data-draft-key="interruption:${esc(j.id)}">${esc(appSession.getItem('interruption:'+j.id)||'')}</textarea></div><button class="btn" data-action="reconcile-interruption" ${executing||!['close-build','close-pre-effect','verify-deployment','verify-opening','verify-checks'].includes(evidence?.disposition)?'disabled':''}>${evidence?.disposition==='verify-opening'?'核对并完成原验收开放':['verify-deployment','verify-checks'].includes(evidence?.disposition)?'继续部署后的技术检查':'核对并关闭本次失败尝试'}</button></section>`;}).join('');
 return card('中断核对',rows?`<div class="pad">${rows}</div>`:'<div class="pad sub">没有待核对的中断任务。</div>');
}
function backupRetryPanel(){
 if(!remoteApplication()||!capability('independentBackupRetry'))return '';
 const original=state.backupRetries?.[selected];
 if(!original)return '';
 return card('备用服独立补发',`<div class="pad">${notice('固定使用正式当前已验收的原包，仅重新发布备用服；正式服不重新部署、不重新验收。')}${kv('原备用任务',esc(original))}${action('仅补发备用服','promote-backup',true).replace('data-action="promote-backup"',`data-action="promote-backup" data-retry-of="${esc(original)}"`)}</div>`);
}
function taskResolution(){
 const pending=state.jobs.filter(j=>unresolved(j)&&!historicalBusinessFailure(j)),executing=state.jobs.some(j=>j.status==='running');
 return card('失败与中断任务技术处理',pending.length?`<div class="pad">${notice('先核对失败步骤与真实影响，再按原任务的处理范围执行。未知或部分迁移不能直接续接或放弃；技术处理结果以实际检查证据为准。')}${pending.map(j=>{const key='releaseCenterResolution:'+j.id,tail=testTailRoot(j),preparationTail=preparationTailRoot(j);return `<section class="reviewbox" data-resolution="${esc(j.id)}"><h3>${esc(j.id)} · ${esc(j.action)} ${badge(statusText(j.status),'red')}</h3>${kv('原固定包',esc(j.releaseTag||'构建未封包'))}${kv('失败步骤',esc(pretty(j.currentStep||'请查原任务日志')))}${preparationTail?notice(preparationPhase(preparationTail)==='capture-complete'?'继续原任务 '+esc(preparationTail.id)+' 已完成快照的传输与恢复；核对原包和正式起点，复用摘要一致的数据块，不再次停正式服采集。成功后仅登记隔离基线，候选升级仍需单独执行。':'仅恢复原准备任务 '+esc(preparationTail.id)+' 保留副本的启动尾段；先核对原包、正式基线、远端停止及完整恢复证据，不重新捕获、导入或执行迁移。成功后仅登记隔离基线，候选升级仍需单独执行。'):''}${tail?notice('仅继续原测试任务 '+esc(tail.id)+' 的同包部署收尾；不重跑 SQL、不重新备份，发布成功以三项技术检查为准。开放阶段失败须先核对实际启动结果；只有原候选健康且身份一致才可继续，其他情况停止处理。'):''}<p class="dangertext">${esc(j.error||'进程中断，真实效果需核对')}</p><div class="field"><label>技术处理决定</label><select class="input" data-resolution-decision="${esc(j.id)}">${!remoteApplication()||tail||preparationTail?`<option value="retry" ${appSession.getItem('releaseCenterDecision:'+j.id)!=='abandon'?'selected':''}>${preparationTail?(preparationPhase(preparationTail)==='capture-complete'?'继续已捕获副本的传输与恢复':'恢复保留副本的启动尾段'):tail?'继续同包测试部署收尾':'核对后允许返回原阶段续接'}</option>`:''}<option value="abandon" ${appSession.getItem('releaseCenterDecision:'+j.id)==='abandon'?'selected':''}>${remoteApplication()&&j.action==='prepare-rehearsal'&&!j.effectsStarted&&!j.remoteStatusRequired?'核对前置失败并结束本次任务，保留失败记录':(['prepare-rehearsal','upgrade-rehearsal'].includes(j.action)||preparationTail)?'核对源服与远端停止证据，清除本次隔离环境并保留失败记录':restoredDeployment(j)||tail?'已恢复原起点，核对后放弃原任务':'核对后放弃原任务'}</option></select></div><div class="field"><label>原因、核对与处置依据（至少5字）</label><textarea class="input" rows="3" data-draft-key="${esc(key)}" data-resolution-note="${esc(j.id)}">${esc(appSession.getItem(key)||'')}</textarea></div><button class="primary" data-action="resolve-task" data-job-id="${esc(j.id)}" ${executing||(remoteApplication()&&j.effectsStarted&&j.action!=='restore-metadata'&&!restoredDeployment(j)&&!tail&&!preparationTail&&!(j.action==='prepare-rehearsal'&&j.remoteProgress?.status!=='running'))?'disabled':''}>执行技术核对并记录决定</button></section>`;}).join('')}</div>`:'<div class="pad sub">当前没有未处理的失败或中断任务。</div>');
}
function accept(label,id,enabled){if(remoteApplication()&&!['accept-prod','accept-backup'].includes(id))return notice('部署后自动执行三项技术检查。')+action('重新执行三项技术检查',id,enabled);const draftKey='releaseCenterNote:'+JSON.stringify([selected,pkg()?.stage||'',page,page===4?pkg()?.activeRehearsal:'']);const draft=appSession.getItem(draftKey)||'';const failed=state.jobs.some(j=>unresolved(j)&&j.releaseTag===selected);return `<div class="field"><label for="accept-note">业务验收结果</label><textarea id="accept-note" data-draft-key="${esc(draftKey)}" class="input" rows="3" placeholder="填写已实际检查的功能与数据结果（至少5字）">${esc(draft)}</textarea></div>${remoteApplication()?action('重新执行三项技术检查',id==='accept-prod'?'verify-prod':'verify-backup',enabled):''}${action(label,id,enabled)} <button class="danger" data-action="reject-acceptance" ${!enabled||busy||failed?'disabled':''}>记录验收失败并停止</button>`;}
function recoveryPanel(){
 if(capability('releaseRecovery')!==true||!pkg())return '';
 const p=pkg(),executing=state.jobs.some(j=>j.status==='running');
 const jobs=state.jobs.filter(j=>j.releaseTag===selected&&['publish-test','promote-prod','promote-backup'].includes(j.action)&&j.effectsStarted&&(!j.resolution||(j.resolution.decision==='reconciled'&&j.resolution.disposition==='verify-deployment'))&&j.status!=='running'&&(state.environments[j.target]?.maintenance!==false||state.environments[j.target]?.maintenanceUnknown||state.environments[j.target]?.recoveryPending)&&p.outcomes?.[j.target]?.deployment?.jobId===j.id&&p.outcomes?.[j.target]?.acceptance?.status!=='passed');
 return card('迁移失败与验收失败恢复',jobs.length?`<div class="pad">${notice('仅恢复尚未开放业务的发布。核对原任务及恢复点，恢复升级前程序、数据库和数据卷；失败 SQL 不直接重跑。恢复后仍需验收旧版本，再开放业务。')}${jobs.map(j=>{
  const recovery=p.outcomes?.[j.target]?.recovery,key='recovery-note:'+j.id;
  const statuses={applied:'已完成',pending:'未执行','failed-or-unknown':'失败或结果未知，可能部分生效'};
  const rows=(j.migrationExecution?.migrations||[]).map(row=>[esc(row.migrationId),esc(statuses[row.status]||row.status)]);
  return `<section class="reviewbox" data-recovery="${esc(j.id)}" data-recovery-status="${esc(recovery?.status||'pending')}"><h3>${esc(targetName(j.target))} · ${esc(j.id)}</h3>${kv('拟恢复版本',esc(j.originState?.releaseTag||'未记录'))}${kv('恢复状态',esc({'pending-acceptance':'已恢复，等待验收','accepted':'恢复已验收并开放'}[recovery?.status]||'尚未恢复'))}${rows.length?table(['迁移编号','实际执行状态'],rows):''}<button data-action="inspect-release-recovery" ${executing?'disabled':''}>核对迁移执行状态</button><div class="field"><label>恢复原因或恢复后的验收结果（至少5字）</label><textarea class="input" data-recovery-note data-draft-key="${esc(key)}">${esc(appSession.getItem(key)||'')}</textarea></div><button class="danger" data-action="recover-release" ${executing||recovery?.status==='pending-acceptance'?'disabled':''}>恢复本次升级前版本及数据</button> <button class="primary" data-action="accept-recovery" ${executing||recovery?.status!=='pending-acceptance'?'disabled':''}>恢复验收通过并开放旧版本</button>${envlink(j.target)}</section>`;
 }).join('')}</div>`:completedRecoveries(p)+'<div class="pad sub">当前包没有等待恢复的部署。已开放业务的版本不允许直接恢复升级前数据。</div>');
}
function auditBaseline(){
 if(capability('auditBaseline')===false||remoteApplication()&&capability('auditBaseline')!==true)return '';
 const p=pkg();return card(remoteApplication()?'现有基线核对登记':'现有演示基线核对登记',`<div class="pad">${notice('选择带结构合同的新候选包，用其累计迁移定义审核已运行的已知包。只核对登记，不修改程序、数据库或迁移历史。')}${['test','prod','backup'].map(target=>{const key=`releaseCenterAudit:${selected}:${target}`,current=appSession.getItem(key+':version')||'';return `<section class="reviewbox"><h3>${esc(targetName(target))} · ${esc(targetAddress(target))}</h3>${kv('用于审核的候选包',esc(p?.releaseTag||'请先在页首选择候选包'))}<div class="field"><label>明确选择此环境当前已运行的已知包</label><select class="input" data-audit-target="${target}" data-storage-key="${esc(key+':version')}"><option value="">请选择真实已运行版本</option>${state.packages.map(item=>`<option value="${esc(item.releaseTag)}" ${current===item.releaseTag?'selected':''}>${esc(item.releaseTag)} · ${esc(item.gitCommit.slice(0,12))}</option>`).join('')}</select></div><div class="field"><label>核对登记原因与现状说明（至少5字）</label><textarea class="input" rows="2" data-audit-note="${target}" data-draft-key="${esc(key+':note')}">${esc(appSession.getItem(key+':note')||'')}</textarea></div><button class="primary" data-action="audit-baseline" data-target="${target}" ${!p||!current||busy?'disabled':''}>只核对并登记${targetName(target)}现有基线</button></section>`;}).join('')}</div>`);
}
function remoteStorage(){
 return card('发布包存储位置',`<div class="pad">${kv('构建包存储路径',esc(state.application.packageStoragePath||'尚未提供实际包存储路径'))}${state.application.nasPath?kv('NAS 位置',esc(state.application.nasPath)):''}</div>`);
}
function remoteBaselines(){
 const entries=['test','prod','backup'].map(env=>{
  const entry=state.environments[env];
  const registration=entry?.error?badge('登记失败','red'):entry?.baselineStatus==='registered'?badge('已只读核对登记','green'):badge('尚未核对登记','gray');
  return `<section class="reviewbox"><div class="envtop"><h3>${esc(targetName(env))}</h3>${registration}</div>${kv('实际运行入口',esc(targetAddress(env)))}${kv('已读取版本',esc(entry?.releaseTag||'尚未读取'))}${kv('快照时间',esc(entry?.observedAt||'尚未读取'))}${kv('维护状态',esc(maintenanceText(env)))}${kv('后端健康',esc(entry?.backendHealth===undefined?'尚未读取':pretty(entry.backendHealth)))}${kv('前端 HTTP 状态',esc(entry?.frontendHttpStatus??'尚未读取'))}${kv('已应用迁移数',esc(Array.isArray(entry?.ledgerRecords)?new Set(entry.ledgerRecords.filter(row=>['APPLIED','SKIPPED_ALREADY_APPLIED'].includes(row.status)).map(row=>row.migrationId)).size:entry?.migrationCount??'尚未读取'))}${entry?.imageIds?kv('后端镜像',`<span class="mono">${esc(entry.imageIds.backend||'尚未读取')}</span>`)+kv('前端镜像',`<span class="mono">${esc(entry.imageIds.frontend||'尚未读取')}</span>`):''}${entry?.schemaSha256?kv('结构 SHA256',`<span class="mono">${esc(entry.schemaSha256)}</span>`):''}${entry?.fingerprint?kv('基线指纹',`<span class="mono">${esc(entry.fingerprint)}</span>`):''}${entry?.error?`<div class="errorbox">${esc(pretty(entry.error))}</div>`:''}${envlink(env)}</section>`;
 }).join('');
 return notice('以下为远程三服最后一次只读核对的登记快照；未读取或失败的项目保持原始状态。此入口不初始化数据库、不修改程序。')+`<div class="grid two"><div>${card('远程三服只读登记快照',`<div class="pad">${entries}</div>`)}</div><div>${card('三服基线核对登记',`<div class="pad"><p>读取真实三服版本、镜像、健康与结构信息，核对后登记各自基线。</p>${action('核对并登记三服基线','register-targets')}${capability('restoreMetadata')===true?`<div class="field"><p>首次接入时，可按已核实的原包 manifest 恢复遗漏的版本文件。</p>${action('补齐当前包版本信息','restore-metadata',!Object.keys(state.environments).length&&!state.packages.length)}<small>仅补历史运行容器的静态文件，原镜像重建后仍会缺失；新构建必须单独通过镜像内文件校验。</small></div>`:''}<div class="sidenote">无需先选择候选包。构建、部署与验收结果仍需分别执行，不会因登记自动通过。</div></div>`)}${remoteStorage()}</div></div>`;
}
function capabilityStatus(){
 if(!remoteApplication())return '';
 const labels={registerTargets:'三服基线核对登记',buildRelease:'完整程序包构建',prepareRehearsal:'隔离演练环境准备'};
 const rows=Object.entries(labels).map(([key,label])=>[label,capability(key)===true?badge('入口已接入，执行时核对前置条件'):capability(key)===false?badge('当前不可执行','orange'):badge('尚未提供准备状态','gray'),esc(state.application.capabilityReasons?.[key]||'')]);
 return card('实际接入与准备状态',table(['能力','入口状态','实际原因'],rows));
}
const precheckOperation=()=>({1:'build-release',3:'publish-test',5:'promote-prod',6:'promote-backup'}[page]);
function precheckResult(job){
 const report=job?.result;
 if(!report)return job?notice(esc(job.error||'检查任务已创建，等待结果。')):'';
 const labels={running:'检查中',passed:'通过',failed:'未通过',interrupted:'检查中断，需重新检查',blocked:'未检查'};
 const scope={'build-release':'构建前','publish-test':'测试服发布前','promote-prod':'正式服发布前','promote-backup':'备用服发布前'}[report.operation];
 return `<div data-precheck-result="${esc(job.id)}">${kv('检查任务',esc(job.id))}${kv('检查范围',esc(scope||report.operation))}${kv(report.commit?'源码提交':'发布版本',esc(report.commit||report.releaseTag))}${kv('检查结果',esc(labels[report.status]||report.status))}${kv('检查时间',esc(report.finishedAt||report.startedAt))}${report.packageSha256?kv('包摘要',`<span class="mono">${esc(report.packageSha256)}</span>`):''}${table(['检查项','结果','说明'],(report.checks||[]).map(row=>[esc(row.label),badge(labels[row.status]||({passed:'通过',failed:'失败'}[row.status])||row.status,row.status==='passed'?'green':row.status==='running'?'gray':'red'),esc(row.detail)]))}${notice(esc(report.limits||'检查中断，结果不完整。'))}<p class="sub">结果仅对应本次所选提交或发布包及检查时刻；不会自动构建、发布或通过验收。再次操作前可以重新检查。</p></div>`;
}
function precheckPanel(){
 const operation=precheckOperation();
 if(!remoteApplication()||!capability('releasePrecheck')||!operation)return '';
 const build=operation==='build-release',retry=operation==='promote-backup'?state.backupRetries?.[selected]:undefined;
 const job=state.jobs.find(j=>j.action==='check-prerequisites'&&j.payload?.operation===operation&&(build?j.payload.commit===chosenCommit:j.releaseTag===selected&&j.payload.retryOf===retry));
 const label=build?'检查构建前条件':'检查发布前条件';
 const disabled=state.jobs.some(j=>j.status==='running')||(build?!chosenCommit:!pkg());
 return card('发布前检查',`<div class="pad"><p>${build?'按下面选择的固定源码提交，检查构建工具、本地与 NAS 存储及三服环境。':'检查当前所选包、目标环境、空间和发布流程前置条件。'}</p><button class="primary" data-action="check-prerequisites" ${disabled?'disabled':''}>${label}</button>${precheckResult(job)}</div>`);
}
const artifactScan=()=>state.jobs.find(j=>j.action==='scan-artifacts');
const artifactSelection=job=>JSON.parse(appSession.getItem('artifact-selection:'+job.id)||'[]');
function artifactGroups(report){
 const groups=new Map();
 for(const row of report?.items||[]){const key=row.location+':'+row.releaseTag;if(!groups.has(key))groups.set(key,{key,location:row.location,releaseTag:row.releaseTag,items:[]});groups.get(key).items.push(row);}
 return [...groups.values()];
}
function artifactPanel(){
 if(!remoteApplication()||!capability('artifactRetention'))return notice('当前应用尚未接入发布产物清理。');
 const job=artifactScan(),report=job?.result,cleanup=state.jobs.find(j=>j.action==='clean-artifacts'),occupied=state.jobs.some(j=>j.status==='running');
 const consumed=job&&state.jobs.some(j=>j.action==='clean-artifacts'&&j.payload.scanJobId===job.id);
 const ready=job?.status==='succeeded'&&report?.complete&&!consumed&&!occupied&&Number(appSession.getItem('artifact-keep')||'3')===report.keepLatest;
 const chosen=job?artifactSelection(job):[],locations={local:'本机',nas:'NAS',test:'测试服',prod:'正式服',backup:'备用服'};
 const size=bytes=>(bytes/1024/1024/1024).toFixed(2)+' GiB';
 const keep=appSession.getItem('artifact-keep')||'3';
 let html=card('保留规则与扫描',`<div class="pad"><p>保留最近版本，并额外保护三服当前版本、正式上一稳定版本、验证环境和未结束任务需要的产物。容器引用的镜像不会删除。</p><label>最近版本保留数量 <select id="artifact-keep" class="input">${[2,3,5,10,20].map(n=>`<option value="${n}" ${String(n)===keep?'selected':''}>${n} 个</option>`).join('')}</select></label><button class="primary" data-action="scan-artifacts" ${occupied?'disabled':''}>扫描发布产物</button><p class="sub">仅清理登记包、镜像标签和过期恢复归档。保留清单、发布记录和恢复记录；不删除容器、数据库、数据卷、失败现场或未知文件。扫描不执行删除。</p></div>`);
 if(job)html+=card('本次扫描',`<div class="pad">${kv('任务',esc(job.id))}${kv('状态',esc(statusText(job.status)))}${kv('保留最近版本',esc(job.payload.keepLatest)+' 个')}${kv('扫描时间',esc(report?.scannedAt||job.createdAt))}${job.error?notice(esc(job.error)):''}${(report?.errors||[]).map(r=>notice(esc(r.location+'：'+r.error))).join('')}${consumed?notice('这次扫描已用于清理。请重新扫描实际剩余产物。'):''}</div>`);
 if(report)html+=card('产物占用与可清理项',table(['选择','位置 / 版本','登记文件大小','产物数量','必须保留的原因'],artifactGroups(report).map(g=>{
  const available=g.items.filter(r=>!r.reasons.length),ids=available.map(r=>r.id),checked=ids.length&&ids.every(id=>chosen.includes(id));
  const reasons=[...new Set(g.items.flatMap(r=>r.reasons))];
  const key=storageKey('artifact-details:'+job.id+':'+g.key);
  const details=`<details data-plan-key="${esc(key)}" ${sessionStorage.getItem(key)==='open'?'open':''}><summary>查看产物明细</summary>${g.items.map(r=>`<p><span class="mono">${esc(r.reference||r.root+'/'+r.file.relative)}</span><small>${esc(r.reasons.length?'保留：'+r.reasons.join('；'):'可清理')} · ${r.kind==='image'?'镜像共享层，释放量以 Docker 为准':r.kind==='directory'?'目录内容未统计':size(r.bytes)}</small></p>`).join('')}</details>`;
  return [`<input type="checkbox" aria-label="选择 ${esc(g.key)}" data-artifact-group="${esc(g.key)}" ${checked?'checked':''} ${ready&&ids.length?'':'disabled'}>`,esc(locations[g.location])+'<small>'+esc(g.releaseTag)+'</small>',size(g.items.reduce((n,r)=>n+(r.bytes||0),0))+(g.items.some(r=>r.kind==='directory')?' + 未统计目录':''),`${available.length} 可清理 / ${g.items.length-available.length} 保护`,esc(reasons.join('；')||'不在保留范围，可选择清理')+details];
 })))+notice('大小仅统计登记文件，不包含 Docker 共享镜像层。移除镜像标签不保证释放同等磁盘空间。勾选一组只选择其中的可清理项。');
 html+=card('确认清理',`<div class="pad"><p>已选 ${chosen.length} 项。删除不可撤销，涉及的发布包将标记为产物已退役，不能重新发布。</p><label for="artifact-confirm">输入“确认清理”</label><textarea id="artifact-confirm" placeholder="确认清理"></textarea><button class="primary" data-action="clean-artifacts" ${ready&&chosen.length?'':'disabled'}>清理选中产物</button></div>`);
 if(cleanup)html+=card('最近清理结果',`<div class="pad">${kv('任务',esc(cleanup.id))}${kv('状态',esc(statusText(cleanup.status)))}${kv('已完成项',String(cleanup.result?.removed?.length||0))}${cleanup.error?notice(esc(cleanup.error)):''}${cleanup.status!=='succeeded'?notice('失败或中断不代表全部未删除。已完成明细保留，请重新扫描后处理剩余产物。'):''}</div>`);
 return html;
}
function render(){
 const current=applications.find(x=>x.id===applicationId);
 document.getElementById('application').innerHTML='<option value="">请选择应用</option>'+applications.map(x=>`<option value="${esc(x.id)}" ${x.id===applicationId?'selected':''}>${esc(x.name)}${x.status==='pending'?' · 待接入':''}</option>`).join('');
 document.getElementById('application').disabled=!applications.length;
 document.getElementById('application-scope').textContent=remoteApplication()?'IntRuoyi · 远程三服发布':current?.scope||'请明确选择已登记的应用';
 document.getElementById('nav').innerHTML=names.map((n,i)=>i===9&&!capability('artifactRetention')?'':`<a class="nav ${i===page?'active':''}" href="${esc(appUrl(i))}"><i>${icons[i]}</i>${n}</a>`).join('');document.getElementById('crumb').textContent=(current?current.name+' / ':'')+names[page];document.title=(current?current.name+' · ':'')+names[page]+' · 发布中心';
 if(current?.status==='pending'){document.getElementById('app').innerHTML=head(names[page],esc(current.name)+' · 发布接入待完成')+card('应用接入状态',`<div class="pad">${kv('当前应用',esc(current.name))}${kv('源码目录',esc(current.repo))}${kv('接入状态',badge('待接入','orange'))}<div class="notice warn">此应用尚未接入本发布中心，不能读取其三服版本或执行构建、发布。不会使用其他应用的数据代替。</div><ul>${current.blockers.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><p class="sub">切换应用仅改变当前操作对象；正在运行的应用和原发布任务保持原状。</p></div>`);return;}
 if(!state){document.getElementById('app').innerHTML=`<div class="errorbox">${esc(connectionError||error||'读取中…')}</div><a class="button" href="/">返回 Spug 登录</a>`;return;}
 busy=running();let p=pkg(),stage=p?.stage,html=head(names[page],state.application.name+' · 同一完整程序包贯穿测试、验证与两服发布',link('刷新状态',page));
 html+=`<div class="card pad"><label for="package">当前发布包　</label><select id="package" class="input"><option value="">请选择已构建发布包</option>${state.packages.map(x=>`<option value="${esc(x.releaseTag)}" ${x.releaseTag===selected?'selected':''}>${esc(x.releaseTag)} · ${esc(x.stage)}${x.baseline?' · 初始基线':''}</option>`).join('')}</select></div>`;
 if(error)html+=`<div role="alert" class="errorbox">${esc(error)}</div>`;
 if(connectionError)html+=`<div role="alert" class="errorbox" data-connection-error>${esc(connectionError)}</div>`;
 html+=precheckPanel();
 if(busy)html+=notice('原任务正在执行或存在未处理的中断。页面刷新不会重新提交。')+link('查看原任务与技术处理',7);
 if(page===0){html+='<div class="grid three">'+['test','prod','backup'].map(env=>{const e=state.environments[env],remote=remoteApplication();const registered=remote?e?.baselineStatus==='registered'&&!e?.error:!!e;return `<div class="card pad"><div class="envtop"><span class="envname">${esc(targetName(env))}</span>${e?.error?badge('登记失败','red'):badge(registered?'已登记':remote?'尚未核对登记':'未初始化',registered?'green':'gray')}</div><div class="envhost">${esc(targetAddress(env))}${remote?'':' · 本地独立演示'}</div><div class="version">${esc(e?.releaseTag||'尚无基线')}</div><div class="envmeta">${remote?esc(maintenanceText(env)):e?.maintenanceError?'维护状态无法确认 · 需技术核对':e?.maintenance?'维护中 · 写入暂停':'状态以实际发布检查为准'}</div>${remote?`<div class="sub">核对时间：${esc(e?.observedAt||'尚未读取')}</div>`:''}${envlink(env)}</div>`;}).join('')+'</div>'+card('当前候选发布包',detail(),link('查看发布包',2))+stageResults()+logs();}
 if(page===1){html+=flow(0)+`<div class="grid two">${card('选择构建来源',`<div class="pad"><div class="field"><label>源码仓库</label><div class="input">${esc(state.application.repo)}</div></div><div class="field"><label for="commit">固定 Git 提交</label><select id="commit" class="input">${chosenCommit&&!commits.some(c=>c.commit===chosenCommit)?`<option value="${esc(chosenCommit)}" selected disabled>所选提交不在当前列表：${esc(chosenCommit.slice(0,12))}</option>`:''}${commits.map(c=>`<option value="${c.commit}" ${c.commit===chosenCommit?'selected':''}>${esc(c.commit.slice(0,12)+' · '+c.message)}</option>`).join('')}</select><small>在专用干净 worktree 构建完整后端、前端镜像与迁移文件。</small></div>${action('开始构建','build-release',commits.some(c=>c.commit===chosenCommit))}</div>`)}${card('构建内容',`<div class="pad">${kv('完整程序镜像','后端 + 前端')}${kv('前端版本验收','从镜像读回 release-info.json')}${kv('导出内容','images.tar + migrations + manifest')}${kv('版本规则','北京时间 yyyy-MM-dd-HH-mm-ss')}<div class="reviewbox">只接受已提交 Git 源码。未提交开发修改不进入发布包。</div></div>`)}</div>`+logs();}
 if(page===2){html+=card('本次固定包',detail())+card('发布包目录与身份',p?`<div class="pad">${kv('包位置',esc(p.directory))}${p.nasDirectory?kv('NAS 原包位置',esc(p.nasDirectory)):''}${kv('Manifest SHA256',`<span class="mono">${esc(p.manifestSha256)}</span>`)}${kv('程序包 SHA256',`<span class="mono">${esc(p.packageSha256)}</span>`)}<div class="checks"><span>完整镜像导出</span><span>编号迁移及校验和</span><span>Git 提交独立记录</span></div>${link('发布测试服',3)}</div>`:'<div class="pad">先构建完整程序包。</div>');}
 if(page===3){html+=flow(1)+`<div class="grid two"><div>${card('固定测试发布包',detail())}${logs()}</div><div>${card(remoteApplication()?'测试部署与技术检查':'测试部署与功能验收',`<div class="pad">${testDeploymentAction(stage,p)}${remoteApplication()?'<div class="sidenote">固定原包直接部署到测试服，三项技术检查通过后进入正式基线隔离验证。</div>':''}${envlink('test')}<div class="sidenote">部署读取原包、校验迁移历史，检查镜像、后端 UP、前端200与版本。</div>${accept(remoteApplication()?'当前测试版本验收通过':'功能测试通过',testAcceptance(),remoteApplication()?['test-deployed','tested'].includes(stage):stage==='test-deployed')}${link('进入隔离升级验证',4)}</div>`)}</div></div>`;}
 if(page===4){const active=activeRehearsal(),source=rehearsalSource(),canPrepare=!!p&&!p.baseline&&!state.environments.rehearsal&&(remoteApplication()?['tested','rehearsal-passed'].includes(stage):((source==='prod'&&['function-passed','tested'].includes(stage))||(source==='backup'&&stage==='prod-accepted')));html+=flow(2)+notice(remoteApplication()?'测试服三项技术检查通过后，从正式服当前真实基线建立隔离副本；同包升级并通过三项技术检查后才允许正式发布。隔离验证不切换正式流量。':'从明确选择的演示正式或备用起点建立独立副本。每次演练绑定起点与原包；既有正式验收结果独立保留。')+`<div class="grid two"><div>${card('验证起点与目标',`<div class="pad">${remoteApplication()?kv('本次演练起点',esc(targetName('prod'))):`<div class="field"><label for="rehearsal-source">本次演练起点</label><select id="rehearsal-source" class="input"><option value="">请明确选择起点</option><option value="prod" ${source==='prod'?'selected':''}>${esc(targetName('prod'))}</option><option value="backup" ${source==='backup'?'selected':''}>${esc(targetName('backup'))}</option></select></div>`}${kv('所选起点当前版本',esc(source?state.environments[source]?.releaseTag||'尚未登记':'未选择'))}${kv('候选原包',esc(p?.releaseTag||'未选择'))}${kv('当前演练编号',esc(active?.id||'尚未准备'))}${kv('当前演练来源',esc(active?targetName(active.source):'—'))}${kv('当前演练状态',active?(remoteApplication()&&active.status==='passed'?technicalBadge(technicalEvidence(p,'rehearsal',active.technical).status):badge(statusText(active.status),'orange')):'尚未准备')}${kv('绑定起点指纹',`<span class="mono">${esc(active?.originFingerprint||'准备后记录')}</span>`)}${envlink('rehearsal')}</div>`)}${rehearsalHistory()}</div><div>${card('升级验证操作',`<div class="pad"><div class="field"><label>① 建立所选起点的隔离副本</label>${action(remoteApplication()?'准备正式基线验证环境':'准备所选起点验证环境','prepare-rehearsal',canPrepare)} ${action('清除独立验证环境（保留证据）','reset-rehearsal',!!p&&!!state.environments.rehearsal)}<small>重新准备前先清除独立验证环境，历史证据保留。正式起点发生变化时必须重新演练并验收。</small></div><div class="field"><label>② 使用原候选包执行升级</label>${action('执行升级验证','upgrade-rehearsal',active?.status==='ready'&&(!remoteApplication()||active.source==='prod'))}</div>${accept('正式起点升级演练验收通过',rehearsalAcceptance(),(remoteApplication()?['upgraded','passed'].includes(active?.status)&&active.source==='prod':active?.status==='upgraded'))}<div class="reviewbox">${remoteApplication()?'技术检查绑定当前演练、正式基线与固定包；各环境独立记录，不替代其它环境检查。':'验收绑定当前演练编号、正式起点与包身份。测试验收、演练验收及正式验收分别记录。'}</div></div>`)}</div></div>`+stageResults()+logs();}
 if(page===5||page===6){const prod=page===5,env=prod?'prod':'backup';html+=flow(prod?3:4)+notice(remoteApplication()?(prod?'正式服发布必须使用本包已通过的正式基线隔离验证；原地升级通过技术检查后保持维护，人工业务验收通过才开放入口。':'备用服直接发布正式已通过业务验收的同一原包，核对起点与正式演练基线兼容并执行自身数据检查；升级后自动执行三项技术检查。'):'在演示目标原地升级，先暂停写入并生成数据库恢复点；部署后等待人工验收开放。')+`<div class="grid two"><div>${card('本次固定发布包',detail())}${logs()}</div><div>${card(remoteApplication()?esc(targetName(env))+'发布与技术检查':prod?'正式演示发布与验收':'备用演示发布与验收',`<div class="pad">${kv('目标',esc(targetAddress(env))+(remoteApplication()?'':' · 独立演示'))}${action(prod?'开始发布正式服':'开始发布备用服',prod?'promote-prod':'promote-backup',stage===(prod?(remoteApplication()?'rehearsal-passed':'tested'):'prod-accepted'))}${envlink(env)}<div class="sidenote">${remoteApplication()?'技术检查通过后保持维护；请检查实际业务，明确验收后再开放。':'运行检查通过后依然保持维护状态，人工确认业务后开放写入。'}</div>${accept(prod?'正式验收通过并开放业务':'备用验收通过并完成发布',prod?'accept-prod':'accept-backup',(remoteApplication()?(prod?['prod-deployed','prod-accepted']:['backup-deployed','completed']).includes(stage):stage===(prod?'prod-deployed':'backup-deployed')))}</div>`)}</div></div>`;}
 if(page===7){html+=taskResolution()+card('所有持久任务',table(['任务 / 操作','固定版本','原执行状态 / 技术处理','失败或当前步骤','操作人 / 创建时间'],state.jobs.map(j=>[esc(j.id)+'<small>'+esc(j.action)+'</small>',esc(j.releaseTag||'尚未封包'),badge(statusText(j.status),j.status==='failed'?'red':j.status==='succeeded'?'green':'orange')+(j.resolution?'<small>已记录技术处理：'+esc(j.resolution.decision)+'</small>':''),esc(j.currentStep||'—'),esc(j.actor)+'<small>'+esc(j.createdAt)+'</small>'])))+stageResults()+logs(true);}
 if(page===8&&!remoteApplication()){html+=notice('只初始化本应用的空白演示资源。已存在未知容器或数据库结构时立即停止，不登记默认成功。')+`<div class="grid two"><div>${card('已登记环境',table(['目标','当前版本','运行入口'],Object.entries(state.environments).map(([env,e])=>[esc(env),esc(e.releaseTag),envlink(env)])))}${card('隔离与迁移规则',`<div class="pad">${kv('数据库镜像','mysql:8.0.39')}${kv('迁移表','release_migration_history')}${kv('历史迁移','仅跳过 succeeded 且校验和匹配项')}<div class="reviewbox">未知迁移、失败迁移和校验和变化立即失败；原任务不会盲目重试。</div></div>`)}</div><div>${card('首次初始化演示基线',`<div class="pad"><p>选择第一版基线程序包，在独立测试、演示正式和演示备用环境建立真实数据库与程序。</p>${detail()}${action('初始化三服演示基线','initialize-baseline',!!p&&Object.keys(state.environments).length===0)}<div class="sidenote">此操作仅用于首次建立真实起点，不自动通过后续业务验收。</div>${action('清除已登记隔离验证环境（保留证据）','reset-rehearsal',!!p&&!!state.environments.rehearsal)}</div>`)}</div></div>`;}
 if(page===8&&remoteApplication())html+=remoteBaselines()+logs(true);
 if(page===9)html+=artifactPanel();
 if(remoteApplication()&&[0,1,4,8].includes(page))html+=capabilityStatus();
 if(remoteApplication()&&[1,2].includes(page))html+=remoteStorage();
 if([2,3,5,6].includes(page))html+=stageResults();
 if(remoteApplication()&&[3,5,6,7].includes(page))html+=recoveryPanel();
 if(remoteApplication()&&[0,3,4,5,6,7].includes(page))html+=interruptionPanel();
 if(page===6)html+=backupRetryPanel();
 if(page===8)html+=auditBaseline();
 html+='<div class="bottomnote"><span>通用发布执行器 · 持久化任务与原包身份</span><span>所有状态来自真实执行记录</span></div>';document.getElementById('app').innerHTML=html;
}
document.addEventListener('toggle',event=>{
 const control=event.target;
 if(control.tagName==='DETAILS'&&control.isConnected&&control.dataset.planKey)sessionStorage.setItem(control.dataset.planKey,control.open?'open':'closed');
},true);
document.addEventListener('change',event=>{
 const control=event.target;
 if(control.id==='artifact-keep'){appSession.setItem('artifact-keep',control.value);render();return;}
 if(control.dataset.artifactGroup){const job=artifactScan(),group=artifactGroups(job?.result).find(g=>g.key===control.dataset.artifactGroup);if(!job||!group)return;const ids=group.items.filter(r=>!r.reasons.length).map(r=>r.id),selectedIds=new Set(artifactSelection(job));for(const id of ids){if(control.checked)selectedIds.add(id);else selectedIds.delete(id);}appSession.setItem('artifact-selection:'+job.id,JSON.stringify([...selectedIds]));render();return;}
 if(control.id==='application'){selectApplication(control.value);return;}
 if(control.id==='package'){selected=control.value;packageChoiceMade=true;appLocal.setItem('releaseCenterPackage',selected);render();}
 else if(control.id==='commit'){chosenCommit=control.value;appLocal.setItem('releaseCenterCommit',chosenCommit);}
 else if(control.id==='rehearsal-source'){appSession.setItem(sourceKey(),control.value);render();}
 else if(control.dataset.storageKey){appSession.setItem(control.dataset.storageKey,control.value);render();}
 else if(control.dataset.resolutionDecision){appSession.setItem('releaseCenterDecision:'+control.dataset.resolutionDecision,control.value);}
});
 document.addEventListener('input',event=>{if(event.target.dataset.draftKey)appSession.setItem(event.target.dataset.draftKey,event.target.value);});
 document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-action]');if(!button||button.disabled||!state)return;button.disabled=true;
 const originApplication=applicationId,originEpoch=selectionEpoch;
 try{
  const id=button.dataset.action,payload={requestId:crypto.randomUUID(),applicationId:originApplication};
  if(!capabilityAllowed(id))throw Error('此操作当前未接入或未准备：'+(state.application.capabilityReasons?.[actionCapabilities[id]]||id));
  if(id==='scan-artifacts')payload.keepLatest=Number(document.getElementById('artifact-keep').value);
  else if(id==='clean-artifacts'){const scan=artifactScan();if(!scan)throw Error('请先扫描');payload.scanJobId=scan.id;const selectedIds=artifactSelection(scan);payload.groups=artifactGroups(scan.result).filter(g=>g.items.some(r=>!r.reasons.length&&selectedIds.includes(r.id))).map(g=>g.key);payload.confirmation=document.getElementById('artifact-confirm').value.trim();}
  else if(id==='check-prerequisites'){
   payload.operation=precheckOperation();
   if(payload.operation==='build-release')payload.commit=document.getElementById('commit').value;
   else{payload.releaseTag=selected;if(payload.operation==='promote-backup'&&state.backupRetries?.[selected])payload.retryOf=state.backupRetries[selected];}
  }else if(id==='build-release')payload.commit=document.getElementById('commit').value;else if(!['register-targets','restore-metadata'].includes(id))payload.releaseTag=selected;
  if(id==='prepare-rehearsal'){payload.source=rehearsalSource();if(!payload.source)throw Error('请明确选择演练起点');}
  if(['promote-backup','publish-test'].includes(id)&&button.dataset.retryOf)payload.retryOf=button.dataset.retryOf;
  if(['inspect-interruption','reconcile-interruption'].includes(id)){
   const group=button.closest('[data-interruption]'),original=state.jobs.find(j=>j.id===group.dataset.interruption);
   if(!original)throw Error('原任务不存在，请刷新核对');
   payload.jobId=original.id;payload.releaseTag=original.releaseTag;
   if(id==='reconcile-interruption')payload.note=group.querySelector('[data-interruption-note]').value;
  }else if(['inspect-release-recovery','recover-release','accept-recovery'].includes(id)){
   const group=button.closest('[data-recovery]');payload.jobId=group.dataset.recovery;
   if(id!=='inspect-release-recovery')payload.note=group.querySelector('[data-recovery-note]').value;
  }else if(id==='resolve-task'){
   const job=state.jobs.find(j=>j.id===button.dataset.jobId);
   if(!job)throw Error('原任务不存在，请刷新核对');
   const group=button.closest('[data-resolution]');payload.jobId=job.id;payload.releaseTag=job.releaseTag;payload.decision=group.querySelector('[data-resolution-decision]').value;payload.note=group.querySelector('[data-resolution-note]').value;
  }else if(id==='audit-baseline'){
   payload.target=button.dataset.target;payload.currentReleaseTag=document.querySelector(`[data-audit-target="${payload.target}"]`).value;payload.note=document.querySelector(`[data-audit-note="${payload.target}"]`).value;
   if(!payload.currentReleaseTag)throw Error('请明确选择目标当前已运行的已知包');
  }else if(['function-passed','mark-tested','accept-rehearsal','accept-prod','accept-backup','reject-acceptance'].includes(id)){
   payload.note=remoteApplication()&&!['accept-prod','accept-backup','reject-acceptance'].includes(id)?'执行三项技术检查：版本镜像、迁移启动、真实登录进入页面':document.getElementById('accept-note').value;
  }
  if('note' in payload&&payload.note.trim().length<5)throw Error('请填写至少5字的真实核对或验收依据');
  await api('actions/'+id,payload,originApplication);if(originEpoch!==selectionEpoch)return;error='';await refresh();
 }catch(exc){if(originEpoch===selectionEpoch){error=exc.message;render();}}
});
function selectApplication(identity){
 if(identity==='fenbeitong'&&applications.some(x=>x.id===identity&&x.status==='ready')){location.href='fenbeitong.html?app=fenbeitong&page=0';return;}
 applicationId=identity;selectionEpoch++;state=null;commits=[];busy=false;error='';connectionError='';
 selected=appLocal.getItem('releaseCenterPackage')||'';chosenCommit=appLocal.getItem('releaseCenterCommit')||'';packageChoiceMade=appLocal.getItem('releaseCenterPackage')!==null;
 localStorage.setItem('releaseCenterApplication',identity);history.replaceState(null,'',appUrl(page));
 if(!applications.some(x=>x.id===identity)){error='未登记的应用，请明确选择其他应用；未自动切换。';render();return;}
 render();refresh();
}
async function refresh(){
 const current=applications.find(x=>x.id===applicationId),epoch=selectionEpoch,identity=applicationId;
 if(!current||current.status!=='ready'||refreshingEpoch===epoch)return;
 refreshingEpoch=epoch;
 try{
  const next=await api('state',undefined,identity);if(epoch!==selectionEpoch)return;
  if(next.application?.id!==identity)throw Error('返回状态的应用身份不符，已停止显示。');
  state=next;connectionError='';
  if(page===1&&!commits.length){const rows=await api('commits',undefined,identity);if(epoch!==selectionEpoch)return;commits=rows;if(!chosenCommit&&commits.length){chosenCommit=commits[0].commit;appLocal.setItem('releaseCenterCommit',chosenCommit);}}
  if(!packageChoiceMade&&!selected&&state.packages.length){selected=state.packages[0].releaseTag;packageChoiceMade=true;appLocal.setItem('releaseCenterPackage',selected);}
  render();
 }catch(exc){if(epoch===selectionEpoch){state=null;connectionError='发布状态读取失败：'+exc.message;render();}}
 finally{if(refreshingEpoch===epoch)refreshingEpoch=null;}
}
async function initialize(){try{const catalog=await api('applications');applications=catalog.applications;if(!Array.isArray(applications)||!applications.length)throw Error('没有已登记应用');selectApplication(applicationId||catalog.defaultApplication);}catch(exc){connectionError=exc.message;render();}}
initialize();setInterval(()=>{if(!document.querySelector('textarea:focus')&&!document.querySelector('select:focus'))refresh();},3000);
