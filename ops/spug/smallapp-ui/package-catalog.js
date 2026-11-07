'use strict';
(function () {
  const types = {'backup-full':'全量备份','backup-incremental':'增量备份','release-full':'完整发布包','frontend-patch':'前端补丁','backend-patch':'后端补丁',unknown:'待识别'};
  const statuses = {indexed:'清单已读取',incomplete:'文件不全',invalid:'元数据异常',conflict:'身份冲突',missing:'登记路径缺失',unavailable:'来源不可达',unpublished:'未登记恢复点',unknown:'待核对'};
  const day = value => value && Number.isFinite(Date.parse(value)) ? new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value)) : '';
  function filterRows(rows, filters = {}) {
    const query = (filters.query || '').trim().toLocaleLowerCase();
    return rows.filter(row => {
      const date = day(row.time);
      return (!filters.kind || row.kind === filters.kind) &&
        (!filters.server || (row.servers || []).includes(filters.server)) &&
        (!filters.application || row.application === filters.application) &&
        (!filters.status || row.status === filters.status) &&
        (!filters.from || (date && date >= filters.from)) && (!filters.to || (date && date <= filters.to)) &&
        (!query || [row.packageId,row.version,row.application,types[row.kind],...(row.servers || []),...(row.nasPaths || [])].join(' ').toLocaleLowerCase().includes(query));
    }).sort((a,b) => {
      const ta = Date.parse(a.time), tb = Date.parse(b.time);
      if (!Number.isFinite(ta)) return Number.isFinite(tb) ? 1 : String(a.packageId).localeCompare(String(b.packageId));
      if (!Number.isFinite(tb)) return -1;
      return (filters.order === 'asc' ? ta-tb : tb-ta) || String(a.packageId).localeCompare(String(b.packageId));
    });
  }
  function catalogFailure(status, body) {
    if (status === 401 || (status === 403 && body?.error === 'Spug login required'))
      return {message:'登录已失效，请重新登录 Spug，返回此页后刷新包清单。',loginRequired:true};
    if (status === 403 && typeof body?.error === 'string' && body.error.startsWith('Spug permission required:'))
      return {message:'当前账号缺少任务计划查看权限（schedule.schedule.view），请联系管理员核对权限。',loginRequired:false};
    return {message:'包清单读取失败（HTTP '+status+'），'+(status === 403?'请求被拒绝，请联系管理员核对访问限制。':'请检查执行器连接。'),loginRequired:false};
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {filterRows,catalogFailure};
  if (typeof document === 'undefined') return;
  const $ = id => document.getElementById(id);
  if (!$('package-catalog')) return;
  const keys = ['kind','server','application','status','from','to','query','order'];
  const defaults=()=>Object.fromEntries(keys.map(key=>[key,key==='order'?'desc':'']));
  let filters=defaults();
  let rows = [], page = 1, timer, loading = false;
  const checks=new Map();
  const pageSize = 25;
  const element = (tag, text, cls) => {const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
  const formatTime = value => day(value) ? new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai',dateStyle:'short',timeStyle:'medium',hour12:false}).format(new Date(value)) : '时间未记录';
  const size = value => Number.isFinite(value) ? (value/1024**3 >= 1 ? (value/1024**3).toFixed(2)+' GiB' : (value/1024**2).toFixed(2)+' MiB') : '未记录';
  function choices(id, values, title) {
    const select=$(id), current=select.value;
    select.replaceChildren(new Option(title,''), ...[...new Set(values)].sort().map(v=>new Option(v==='unknown'?'未记录':v,v)));
    if ([...select.options].some(o=>o.value===current)) select.value=current;
  }
  function render() {
    const selected=filterRows(rows,filters), pages=Math.max(1,Math.ceil(selected.length/pageSize));
    const active=keys.filter(key=>key!=='order' && filters[key]);
    $('catalog-filter-open').textContent='筛选'+(active.length?'（'+active.length+'）':'');
    const labels={kind:types[filters.kind],server:filters.server,application:filters.application,status:statuses[filters.status],from:filters.from?'自 '+filters.from:'',to:filters.to?'至 '+filters.to:'',query:filters.query?'关键词：'+filters.query:''};
    $('catalog-filter-summary').textContent=[...active.map(key=>labels[key]),'时间'+(filters.order==='asc'?'从旧到新':'从新到旧')].join(' · ');
    page=Math.min(page,pages);
    const body=$('catalog-body');body.replaceChildren();
    for (const row of selected.slice((page-1)*pageSize,page*pageSize)) {
      const tr=element('tr');tr.dataset.kind=row.kind;tr.dataset.packageId=row.packageId;
      const cell=(text,cls)=>{const td=element('td',text,cls);tr.append(td);return td;};
      cell(formatTime(row.time),'catalog-time');cell(types[row.kind] || '待识别');
      cell(row.application==='intruoyi'?'IntRuoyi':row.application==='smallapp'?'小程序':row.application==='unknown'?'未记录':row.application);
      const servers=cell((row.servers || []).join(' / ') || '未记录');
      if (row.servers?.length) servers.append(element('small',row.serverEvidence==='release-history'?'发布历史涉及目标':'NAS 目录标记'));
      const identity=cell(row.version || (row.versionStatus==='conflict'?'版本冲突':row.versionStatus==='invalid'?'版本资料异常':'未记录'),'catalog-identity');
      if(row.baseVersion)identity.append(element('small','基线 '+row.baseVersion));
      cell(size(row.sizeBytes));
      const status=cell();status.append(element('span',statuses[row.status] || '待核对','catalog-state '+row.status));
      if(row.integrityState)status.append(element('small','归档记录 '+row.integrityState));
      const paths=cell(undefined,'catalog-path');
      for(const path of row.nasPaths || []) paths.append(element('div',path));
      const detail=element('details'), summary=element('summary','查看依据');detail.append(summary);
      const versionBasis={'archive-version-pin+runtime-images':'包内版本资料与归档镜像一致（摘要已核对）','archive-version-pin':'包内版本记录（摘要已核对；此包未记录容器快照）','archive-image-tag':'归档容器镜像标签',unrecorded:'未记录',invalid:'版本资料异常，见问题说明'};
      const values=[['包编号',row.packageId],['程序版本依据',versionBasis[row.versionBasis] || (row.category==='release'?'发布包清单':'未记录')],['时间依据',row.timeBasis],['大小依据',row.sizeBasis],['本机发布登记',row.registered?'有':'无'],['元数据 SHA256',row.manifestSha256 || '未记录'],['核对范围','只读取元数据与发布文件大小；本列表未执行全载荷校验或恢复验证。']];
      if(row.issues?.length)values.push(['问题',row.issues.join('；')]);
      if(row.releaseStage)values.push(['发布阶段记录',row.releaseStage]);
      if(row.restoreAdmission)values.push(['恢复准入记录',row.restoreAdmission]);
      for(const [label,value] of values)detail.append(element('p',label+'：'+value));
      paths.append(detail);body.append(tr);
      const operations=cell(undefined,'catalog-operation');
      const check=checks.get(row.checkKey),button=element('button',check?.status==='running'?'检查中…':'验证');
      button.type='button';button.disabled=!row.checkKey || check?.status==='running';
      button.addEventListener('click',()=>verify(row,true));operations.append(button);
      const restore=element('button','恢复');restore.type='button';
      const backup=['backup-full','backup-incremental'].includes(row.kind);
      restore.disabled=!backup || row.status!=='indexed';
      restore.title=!backup?'发布包不能用于数据备份恢复，请使用对应发布流程。':row.status!=='indexed'?'包清单尚未通过读取核对，不能发起恢复。':'选择目标服务器并确认恢复此备份包';
      restore.addEventListener('click',()=>openCatalogRestore(row));operations.append(restore);
      if(check){
        const labels={running:'正在检查文件是否存在…',exists:'文件存在',missing:'文件缺失',unavailable:'无法访问 NAS',changed:'包清单已变化，请刷新',unsupported:'无法识别包文件范围',error:'无法检查'};
        const status=element('div',labels[check.status] || '无法检查','catalog-check '+check.status);status.setAttribute('role','status');operations.append(status);
        if(check.checkedAt)operations.append(element('small',formatTime(check.checkedAt)));
        if(check.existingFiles!==undefined)operations.append(element('small','存在 '+check.existingFiles+' 个'+(check.missingFileCount?' · 缺失 '+check.missingFileCount+' 个':'')));
        if(check.status!=='running'){
          operations.append(element('small','仅检查文件存在，未校验内容或恢复。'));
          const evidence=element('details');evidence.append(element('summary','检查详情'));
          for(const copy of check.copies || []){
            evidence.append(element('p',copy.path+'：'+(labels[copy.status] || '无法检查')));
            if(copy.missingFiles?.length)evidence.append(element('p','缺失：'+copy.missingFiles.join('；')+(copy.missingFileCount>copy.missingFiles.length?'（仅列前10项）':'')));
            if(copy.code)evidence.append(element('p','原因：'+copy.code));
          }
          if(check.error || check.code)evidence.append(element('p',check.error || check.code));
          operations.append(evidence);
        }
      }
    }
    $('catalog-empty').hidden=selected.length>0;
    $('catalog-count').textContent='共 '+rows.length+' 个包 · 筛选 '+selected.length+' 个 · 第 '+page+' / '+pages+' 页';
    $('catalog-prev').disabled=page<=1;$('catalog-next').disabled=page>=pages;
  }
  async function verify(row,force=false) {
    if(force && checks.get(row.checkKey)?.status==='running')return;
    checks.set(row.checkKey,{status:'running'});render();
    try {
      const token=localStorage.getItem('token');if(!token)throw new Error('请重新登录 Spug 后再验证。');
      const response=await fetch('/release-center/api/applications/intruoyi/package-catalog/verify/'+row.checkKey+(force?'?refresh=1':''),{headers:{'X-Token':token},cache:'no-store'});
      const result=await response.json().catch(()=>{throw new Error('文件检查响应不是有效 JSON。');});
      if(!response.ok)throw new Error(response.status===401 || response.status===403?catalogFailure(response.status,result).message:result.error || '文件检查失败（HTTP '+response.status+'）。');
      if(result.schemaVersion!=='PackagePresence/v1' || !['running','exists','missing','unavailable','changed','unsupported','error'].includes(result.status))throw new Error('文件检查响应格式不符。');
      checks.set(row.checkKey,result);render();
      if(result.status==='running')setTimeout(()=>verify(row),1500);
    } catch(error) {checks.set(row.checkKey,{status:'error',error:error.message});render();}
  }
  async function load(force=false) {
    if(loading)return;loading=true;clearTimeout(timer);$('catalog-refresh').disabled=true;
    const problem=$('catalog-problem');
    try {
      const token=localStorage.getItem('token');if(!token)throw Object.assign(new Error('请先登录 Spug，返回此页后刷新包清单。'),{loginRequired:true});
      const response=await fetch('/release-center/api/applications/intruoyi/package-catalog'+(force?'?refresh=1':''),{headers:{'X-Token':token},cache:'no-store'});
      const data=await response.json().catch(()=>{throw new Error('包清单响应不是有效 JSON（HTTP '+response.status+'），请联系管理员检查服务。');});
      if(!response.ok){const failure=catalogFailure(response.status,data);throw Object.assign(new Error(failure.message),failure);}
      if(data.schemaVersion!=='PackageCatalog/v1' || !Array.isArray(data.items))throw new Error('包清单响应格式不符。');
      rows=data.items;choices('catalog-server',rows.flatMap(r=>r.servers || []),'全部服务器');choices('catalog-application',rows.map(r=>r.application),'全部应用');
      $('catalog-observed').textContent=(data.refreshing?'正在读取 NAS，当前显示最近一次结果。 ':'')+(data.observedAt?'最近核对 '+formatTime(data.observedAt)+'（北京时间）':'首次读取中…');
      problem.replaceChildren();
      if(!data.complete && !data.refreshing) problem.append(element('p','目录读取不完整，以下来源需要处理：'));
      for(const issue of data.errors || [])problem.append(element('p',(issue.path || '目录服务')+'：'+issue.code));
      problem.hidden=!problem.childNodes.length;
      $('catalog-sources').replaceChildren(...(data.sources || []).map(source=>element('p',source.path+' · '+(source.status==='ok'?'已读取':'读取异常')+' · '+source.packageCount+' 个目录包')));
      render();
      if(data.refreshing)timer=setTimeout(()=>load(),2000);
    } catch(error) {
      problem.replaceChildren(element('p',error.message));problem.hidden=false;
      if(error.loginRequired){const login=element('a','重新登录 Spug');login.href='/';problem.append(login);}
      $('catalog-observed').textContent=rows.length?'连接中断，以下是上次读取结果。':'包清单尚未读取成功。';
    } finally {loading=false;$('catalog-refresh').disabled=false;}
  }
  const dialog=$('catalog-filter-dialog');
  function writeDraft(values){for(const key of keys)$('catalog-'+key).value=values[key];$('catalog-filter-error').hidden=true;}
  $('catalog-filter-open').addEventListener('click',()=>{writeDraft(filters);dialog.showModal();$('catalog-kind').focus();});
  $('catalog-filter-cancel').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();dialog.close();}});
  dialog.addEventListener('close',()=>$('catalog-filter-open').focus());
  $('catalog-reset').addEventListener('click',()=>writeDraft(defaults()));
  $('catalog-filter-form').addEventListener('submit',event=>{
    event.preventDefault();const draft=Object.fromEntries(keys.map(key=>[key,$('catalog-'+key).value]));
    if(draft.from && draft.to && draft.from>draft.to){$('catalog-filter-error').hidden=false;$('catalog-from').focus();return;}
    filters=draft;page=1;render();dialog.close();
  });
  $('catalog-prev').addEventListener('click',()=>{page--;render();});$('catalog-next').addEventListener('click',()=>{page++;render();});
  $('catalog-refresh').addEventListener('click',()=>load(true));load();
})();
