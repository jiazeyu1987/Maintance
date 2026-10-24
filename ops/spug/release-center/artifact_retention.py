"""Preview/select/confirm lifecycle for manifest-owned release artifacts."""
import copy
import hashlib
import json
from pathlib import Path
import secrets
import threading
import time

import artifact_files as files
from executor import require, stamp
from intruoyi_runtime import Runtime
from nas_connection import connect_nas
from release_precheck import safe_error

ACTIONS = ('scan-artifacts', 'clean-artifacts')
LOCATIONS = {'local':'本机','nas':'NAS','test':'测试服','prod':'正式服','backup':'备用服'}


def submit(executor, action, payload, actor):
    with executor.lock:
        selected=[]
        require(not any(j['status']=='running' for j in executor.state['jobs'])
                and not (executor.worker and executor.worker.is_alive()), '其他任务正在执行，请结束后再扫描或清理')
        if action == 'scan-artifacts':
            require(type(payload.get('keepLatest')) is int and 2<=payload['keepLatest']<=100, '最近保留版本数必须为2至100')
        else:
            require(payload.get('confirmation') == '确认清理', '请输入“确认清理”，删除后不能撤销')
            groups=payload.get('groups')
            require(isinstance(groups,list) and groups and all(isinstance(g,str) for g in groups) and len(set(groups))==len(groups), '请选择不重复的可清理产物组')
            original = next((j for j in executor.state['jobs'] if j['id']==payload.get('scanJobId') and j['action']=='scan-artifacts'),None)
            require(original and original['status']=='succeeded' and original['result']['complete'], '需要完整成功的扫描')
            require(time.time()-original['result']['scannedEpoch']<=1800, '扫描已超过30分钟，请重新扫描')
            require(not any(j['action']=='clean-artifacts' and j['payload'].get('scanJobId')==original['id'] for j in executor.state['jobs']), '此扫描已用于清理；请重新扫描实际剩余产物')
            eligible={r['location']+':'+r['releaseTag'] for r in original['result']['items'] if not r['reasons']}
            require(set(groups)<=eligible, '选择中包含全部受保护或未知的产物组')
            selected=[r['id'] for r in original['result']['items'] if not r['reasons'] and r['location']+':'+r['releaseTag'] in groups]
        job=dict(id='JOB-'+secrets.token_hex(5),requestId=payload['requestId'],action=action,payload=payload,
                 actor=actor,status='running',releaseTag=None,createdAt=stamp(),logs=[],selectedItems=selected)
        executor.state['jobs'].insert(0,job);executor.save()
        executor.worker=threading.Thread(target=executor.execute,args=(job,),daemon=True)
        executor.worker.start()
        return job


def protections(state, observations, keep):
    reasons={p['releaseTag']:[] for p in state['packages']}
    def hold(tag,reason):
        if tag in reasons and reason not in reasons[tag]:reasons[tag].append(reason)
    recent=sorted((p['releaseTag'] for p in state['packages'] if not p.get('artifactsPruned')),reverse=True)[:keep]
    for tag in recent:hold(tag,'最近保留的 '+str(keep)+' 个版本')
    for env in set(state['environments'])|set(observations):
        recorded=state['environments'].get(env,{})
        obs=dict(recorded,**observations.get(env,{}))
        hold(recorded.get('releaseTag'),env+' 登记版本')
        hold(obs.get('releaseTag'),env+' 当前版本/验证环境')
        if env in ('test','prod','backup') and (obs.get('recoveryPending') or obs.get('maintenanceUnknown') or obs.get('maintenance')):
            # Unresolved environment ownership prevents destructive cleanup entirely.
            for tag in reasons:hold(tag,env+' 处于维护、恢复待验收或状态待核对')
    prod=observations['prod']['releaseTag']
    deployed=[j for j in state['jobs'] if j['action']=='promote-prod' and j.get('releaseTag')==prod and j.get('originState')]
    if deployed:
        hold(deployed[0]['originState'].get('releaseTag'),'正式服上一稳定版本')
    else:
        for tag in reasons:hold(tag,'当前正式版本缺少可确认的上一稳定版本记录')
    for p in state['packages']:
        if p.get('baseline'):hold(p['releaseTag'],'初始基线')
        if not p.get('artifactsPruned') and not p.get('abandoned') and p['stage'] not in ('built','completed'):
            hold(p['releaseTag'],'发布或验收流程未结束')
    for job in state['jobs']:
        if job['action'] in (*ACTIONS,'check-prerequisites'):continue
        if not job.get('resolution') and (job['status'] in ('running','interrupted') or (job['status']=='failed' and not job.get('reconciledBy'))):
            hold(job.get('releaseTag'),'未结束或未解决任务 '+job['id'])
            hold(job.get('originState',{}).get('releaseTag'),'未结束任务的恢复起点 '+job['id'])
        plan=job.get('rollbackPlan',{})
        if plan.get('expiresAt',0)>time.time():
            for key in ('currentReleaseTag','targetReleaseTag'):hold(plan.get(key),'有效回滚预览 '+job['id'])
    return reasons


def scan(executor, keep, job):
    from intruoyi_executor import validate_origin
    state=copy.deepcopy(executor.state)
    runtime=Runtime(executor.c)  # inspections do not create remote operation journals
    result=dict(keepLatest=keep,scannedEpoch=time.time(),scannedAt=stamp(),complete=False,items=[],errors=[],versions=[])
    observations={};manifests={};packages={p['releaseTag']:p for p in state['packages']}
    def attempt(label,callback):
        executor.step(job,label)
        try:return callback()
        except Exception as error:result['errors'].append(dict(location=label,error=safe_error(error,executor)))
    for env in ('test','prod','backup'):
        obs=attempt(env+' 实际版本',lambda e=env:validate_origin(runtime.observe(e)))
        if obs:observations[env]=obs
    for tag in packages:
        pair=attempt('包清单 '+tag,lambda t=tag:executor.manifest(t))
        if pair:manifests[tag]=pair[1]
    if len(observations)!=3 or len(manifests)!=len(packages):return result
    result['origins']={env:{key:obs[key] for key in ('images','releaseTag')} for env,obs in observations.items()}
    protected=protections(state,observations,keep)
    result['versions']=[dict(releaseTag=tag,reasons=protected[tag],retired=bool(p.get('artifactsPruned'))) for tag,p in packages.items()]
    # Include every known retry root; never enumerate unrelated staging directories.
    def entries(env):
        rows=[]
        for tag,m in manifests.items():
            p=packages[tag]
            entry=dict(manifest=m,manifestSha256=p['manifestSha256'],packageSha256=p['packageSha256'],
                       ownerJobIds=[j['id'] for j in state['jobs'] if j.get('releaseTag')==tag and j.get('target')==env])
            rows.append(entry)
            for owner in state['jobs']:
                root=owner.get('runtimeStagingRoots',{}).get(env)
                if root and owner.get('releaseTag')==tag:
                    path=Path(root)
                    expected=Path(executor.c['targets'][env]['stagingRoot'])/'attempts'
                    require(path.parent==expected,'登记的备用重试目录不在所属暂存根下')
                    candidate=dict(entry,attempt=path.name)
                    if candidate not in rows:rows.append(candidate)
        return rows
    def add(location,tag,kind,**values):
        row=dict(location=location,releaseTag=tag,kind=kind,reasons=list(protected[tag]),**values)
        identity={k:row.get(k) for k in ('location','root','reference')}
        if 'file' in row:identity['relative']=row['file']['relative']
        row['id']=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:24]
        other=next((x for x in result['items'] if x['id']==row['id']),None)
        if other:
            other['tags']=sorted(set(other['tags']+[tag]));other['reasons']=sorted(set(other['reasons']+row['reasons']))
        else:
            row['tags']=[tag];result['items'].append(row)
    def directory(location,tag,root,rows):
        for row in rows:add(location,tag,'directory' if row.get('unmeasured') else 'file',root=str(root),file=row,bytes=row['bytes'],label=row['kind']+' · '+row['relative'])
    for tag,m in manifests.items():
        p=packages[tag];root=Path(p['directory'])
        require(root.resolve().parent==(executor.root/'packages').resolve(),'本地包不属于登记的发布包目录')
        rows=attempt('本机 '+tag,lambda:files.inventory(root,m,p['manifestSha256'],p['packageSha256']))
        if rows is not None:directory('local',tag,root,rows)
    def nas():
        connect_nas(executor.c['nasPath'],executor.c.get('nasCredentialsFile'))
        for tag,m in manifests.items():
            p=packages[tag];root=Path(executor.c['nasPath'])/tag
            directory('nas',tag,root,files.inventory(root,m,p['manifestSha256'],p['packageSha256'],archive_only=True))
        return True
    attempt('NAS',nas)
    image_sets={}
    local=attempt('本机 Docker',files.docker_inventory)
    if local:image_sets['local']=local
    for env in ('test','prod','backup'):
        remote=attempt(env+' 产物与镜像',lambda e=env:runtime.call(e,'artifact-inventory',entries=entries(e)))
        if remote:
            for d in remote['directories']:directory(env,d['releaseTag'],d['root'],d['files'])
            image_sets[env]=(remote['images'],set(remote['usedImages']),remote['usedMounts'])
    for location,(images,used,mounts) in image_sets.items():
        for row in result['items']:
            if row['location']==location and row['kind']=='file' and files.mounted(Path(row['root'])/row['file']['relative'],mounts):
                row['reasons'].append('容器仍挂载该产物路径')
        protected_ids={v.get('localImageId',v['id']) if location=='local' else v['id'] for t,m in manifests.items() if protected[t] for v in m['images'].values()}
        for tag,m in manifests.items():
            for image in m['images'].values():
                reference=image['name'];identity=image.get('localImageId',image['id']) if location=='local' else image['id']
                if reference not in images:continue
                add(location,tag,'image',reference=reference,imageId=identity,bytes=None,label='程序镜像 · '+reference)
                row=next(r for r in result['items'] if r.get('reference')==reference and r['location']==location)
                for condition,reason in ((images[reference]!=identity,'镜像标签身份与发布包不符'),(identity in used,'运行或停止的容器仍引用该镜像'),(identity in protected_ids,'受保护版本共用该镜像')):
                    if condition and reason not in row['reasons']:row['reasons'].append(reason)
    retained={r['releaseTag']:r['file']['retainedReason'] for r in result['items'] if r.get('file',{}).get('retainedReason')}
    for row in result['items']:
        row['reasons']=sorted(set(row['reasons']+[retained[t] for t in row['tags'] if t in retained]))
    for row in result['versions']:
        if row['releaseTag'] in retained:row['reasons'].append(retained[row['releaseTag']])
    result['complete']=not result['errors']
    return result


def execute(executor,job):
    if job['action']=='scan-artifacts':
        job['result']=scan(executor,job['payload']['keepLatest'],job)
        require(job['result']['complete'],'扫描未完成，禁止清理；请查看具体失败项')
    else:
        original=next(j for j in executor.state['jobs'] if j['id']==job['payload']['scanJobId'])
        old={r['id']:r for r in original['result']['items']}
        fresh=scan(executor,original['result']['keepLatest'],job)
        job['result']=dict(recheck=fresh,removed=[],failedItem=None)
        require(fresh['complete'],'清理前重新扫描失败，未开始删除')
        current={r['id']:r for r in fresh['items']}
        chosen=job['selectedItems']
        require(all(i in current and current[i]==old[i] and not current[i]['reasons'] for i in chosen),'所选产物或保护条件发生变化，请重新扫描选择')
        runtime=Runtime(executor.c)
        for identity in chosen:
            row=current[identity]
            job['result']['failedItem']=identity
            executor.step(job,'清理 '+LOCATIONS[row['location']]+' '+row['label'])
            # Persist retirement before deletion, including uncertain remote outcomes.
            for tag in row['tags']:
                p=next(p for p in executor.state['packages'] if p['releaseTag']==tag)
                p['artifactsPruned']=dict(jobId=job['id'],time=stamp(),reason='明确选择清理发布产物')
            executor.save()
            if row['location'] in ('local','nas'):
                if row['kind']=='image':files.remove_image(row['reference'],row['imageId'])
                else:
                    if row['location']=='local':
                        require(not files.mounted(Path(row['root'])/row['file']['relative'],files.docker_inventory()[2]),'容器已挂载该产物，未删除')
                    files.remove_file(row['root'],row['file'])
            else:
                p,m=executor.manifest(row['releaseTag'])
                entry=dict(manifest=m,manifestSha256=p['manifestSha256'],packageSha256=p['packageSha256'],
                           ownerJobIds=[j['id'] for j in executor.state['jobs'] if j.get('releaseTag')==row['releaseTag'] and j.get('target')==row['location']])
                if row.get('root'):
                    root=Path(row['root']);base=Path(executor.c['targets'][row['location']]['stagingRoot'])
                    if root.parent!=base:entry['attempt']=root.parent.name
                runtime.call(row['location'],'artifact-remove',entries=[entry],item=row,expectedImages=fresh['origins'][row['location']]['images'])
            job['result']['removed'].append(identity);job['result']['failedItem']=None;executor.save()
    job.update(status='succeeded',finishedAt=stamp());executor.save()
