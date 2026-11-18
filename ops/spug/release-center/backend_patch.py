"""Durable backend patch workflow, sharing the executor's global admission lock."""
import json
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import threading

from executor import digest,require,stamp
from backend_patch_contract import validate_manifest

PREFIX='backend-patch-'
ACTIONS={PREFIX+x for x in ('register-baseline','build','retry-upload','refresh','deploy','accept','restore')}
ENVS=('test','prod','backup')


class BackendPatchMixin:
    def snapshot(self):
        value=super().snapshot()
        value['application']['capabilities']['backendPatch']=True
        for key in ('backendPatches','backendPatchBaselines'):value.setdefault(key,[])
        value.setdefault('backendPatchEnvironments',{})
        return value

    def backend_baseline(self,identity):
        rows=[b for b in self.state.get('backendPatchBaselines',[]) if b['id']==identity]
        require(len(rows)==1,'请先读取并登记三服后端补丁基线')
        return rows[0]

    def backend_package(self,tag):
        rows=[p for p in self.state.get('backendPatches',[]) if p['releaseTag']==tag]
        require(len(rows)==1,'后端补丁包不存在')
        p=rows[0];root=Path(p['directory'])
        require(digest(root/'manifest.json')==p['manifestSha256'],'补丁清单摘要不一致')
        manifest=validate_manifest(json.loads((root/'manifest.json').read_text('utf-8')))
        require(manifest['releaseTag']==tag and manifest['gitCommit']==p['gitCommit'],'补丁身份不一致')
        return p,manifest

    def backend_gate(self,action,payload):
        if action in (PREFIX+'refresh',PREFIX+'register-baseline'):return
        require(isinstance(payload.get('note'),str) and len(payload['note'].strip())>=5,'请填写至少5字的兼容性评审或实际验收结论')
        if action==PREFIX+'build':
            from backend_patch_build import validate_source
            base=self.backend_baseline(payload.get('baselineId'))
            validate_source(self,base,payload.get('commit'))
            return
        if action==PREFIX+'retry-upload':
            old=next((j for j in self.state['jobs'] if j['id']==payload.get('originalJobId')),None)
            require(old and old['action']==PREFIX+'build' and old['status']=='failed' and old.get('sealedPackage'),
                    '没有可校验重传的已封包构建任务')
            return
        env=payload.get('target');require(env in ENVS,'请选择明确目标')
        p,_=self.backend_package(payload.get('releaseTag'))
        if action in (PREFIX+'deploy',PREFIX+'restore') and env in ('prod','backup'):
            require(payload.get('confirmation')=='PROD','正式/审查后端变更需要输入 PROD 确认')
        if action==PREFIX+'restore':
            original=next((j for j in self.state['jobs'] if j['id']==payload.get('originalJobId')),None)
            require(original and original['action']==PREFIX+'deploy' and original.get('effectsStarted')
                    and original.get('target')==env and original.get('releaseTag')==p['releaseTag'] and not original.get('backendRestoredBy'),
                    '没有该目标该补丁的原程序恢复任务')
            return
        require(not any(self.frontend_failure_blocks(j,env) for j in self.state['jobs']), '目标存在未处理失败，请核对或恢复')
        current=self.state.get('backendPatchEnvironments',{}).get(env,{})
        if action==PREFIX+'accept':
            require(p['deployments'].get(env,{}).get('status')=='succeeded','尚未完成该目标部署')
        if action==PREFIX+'deploy':
            require(current.get('releaseTag')==p['baseReleaseTag'],'目标主版本不一致，请刷新基线')
            require(current.get('backendPatchTag')!=p['releaseTag'],'目标已安装此补丁')
            previous={'prod':'test','backup':'prod'}.get(env)
            if previous:
                require(p['accepted'].get(previous) and self.state['backendPatchEnvironments'].get(previous,{}).get('backendPatchTag')==p['releaseTag'],
                        '请先验收前一服当前同一后端补丁')

    def submit(self,action,payload,actor):
        if action not in ACTIONS:
            if action=='build-release':
                active={e.get('backendPatchTag') for e in self.state.get('backendPatchEnvironments',{}).values()}-{None}
                active.update(e.get('backendPatchTag') for e in self.state.get('environments',{}).values() if e.get('backendPatchTag'))
                for tag in active:
                    p,_=self.backend_package(tag)
                    self.run(['git','-C',self.c['repo'],'merge-base','--is-ancestor',p['gitCommit'],payload.get('commit','')])
            return super().submit(action,payload,actor)
        with self.lock:
            self.ensure_persistence()
            require(not getattr(self,'draining',False) and not getattr(self,'cleanup_active',False),'执行器正在停止或清理')
            require(payload.get('applicationId')==self.c['applicationId'],'应用身份不匹配')
            request=payload.get('requestId','');require(re.fullmatch('[a-zA-Z0-9-]{8,80}',request),'requestId required')
            for old in self.state['jobs']:
                if old.get('requestId')==request:
                    require(old['action']==action and old['payload']==payload,'请求编号已绑定其他操作');return old
            require(not any(j['status']=='running' or j['status']=='interrupted' and not j.get('resolution')
                            for j in self.state['jobs']) or action==PREFIX+'restore' and not any(j['status']=='running' for j in self.state['jobs']),
                    '请等待或核对当前任务')
            self.backend_gate(action,payload)
            job=dict(id='JOB-'+secrets.token_hex(5),action=action,requestId=request,payload=payload,actor=actor,
                     releaseTag=payload.get('releaseTag'),target=payload.get('target'),status='running',createdAt=stamp(),logs=[])
            self.state['jobs'].insert(0,job);self.save()
            self.worker=threading.Thread(target=self.backend_job,args=(job,),daemon=True);self.worker.start()
            return job

    def backend_call(self,job,env,action,**kwargs):
        self.runtime.operation_context.binding=(job,self.save)
        return self.runtime.call(env,PREFIX+action,**kwargs)

    def execute(self,job):
        result=super().execute(job)
        if job.get('status')=='succeeded' and job['action'] in ('publish-test','promote-prod','promote-backup','accept-backup'):
            for env,current in self.state.get('environments',{}).items():
                if env in ENVS and 'backendPatchTag' in current and not current['backendPatchTag']:
                    self.state.get('backendPatchEnvironments',{}).pop(env,None)
            self.save()
        return result

    def record_backend(self,env,actual):
        self.state.setdefault('backendPatchEnvironments',{})[env]=actual
        current=self.state['environments'].get(env)
        if current and current.get('releaseTag')==actual['releaseTag']:
            # A fresh full observation incorporates the actual mount/config in
            # the full-release origin fingerprint; do not invent a baseline.
            full=self.runtime.observe(env)
            require(full.get('backendJarSha256')==actual['backendJarSha256'],'完整观察与实际 JAR 不一致')
            current.update(full)
        self.save()

    def backend_job(self,job):
        tracker=None
        self.cleanup_active=job['action']==PREFIX+'accept' and job.get('target')=='backup'
        try:
            if getattr(self,'track_local_processes',False):
                from local_processes import Tracker
                tracker=Tracker(self,job)
            action,payload=job['action'],job['payload'];self.step(job,action);self.backend_gate(action,payload)
            if action==PREFIX+'build':
                from backend_patch_build import build
                build(self,job)
            elif action==PREFIX+'retry-upload':
                from backend_patch_build import publish_original
                old=next(j for j in self.state['jobs'] if j['id']==payload['originalJobId'])
                job['releaseTag']=old['releaseTag']
                publish_original(self,old,old['sealedPackage'])
                old['resolution']=dict(decision='original-package-uploaded',jobId=job['id'],time=stamp())
            elif action==PREFIX+'register-baseline':
                from backend_patch_agent import validate_baseline
                from frontend_patch_baseline import target_binding
                origins={env:self.backend_call(job,env,'observe') for env in ENVS}
                commit=validate_baseline(origins)
                front=origins['prod']['frontendMetadata'].get('sourceCommit')
                if front and front!=commit:
                    git=['git','-C',self.c['repo']]
                    try:self.run(git+['merge-base','--is-ancestor',commit,front]);commit=front
                    except Exception:self.run(git+['merge-base','--is-ancestor',front,commit])
                for env in ENVS:
                    require(self.backend_call(job,env,'observe')==origins[env],'读取期间实际程序发生变化')
                    self.record_backend(env,origins[env])
                b=dict(id='BPB-'+secrets.token_hex(10),releaseTag=origins['prod']['releaseTag'],gitCommit=commit,
                       origins=origins,targets={env:target_binding(self.runtime.profile(env)) for env in ENVS},registeredAt=stamp(),jobId=job['id'])
                self.state.setdefault('backendPatchBaselines',[]).insert(0,b);job['result']={'baselineId':b['id']}
            elif action==PREFIX+'refresh':
                for env in ENVS:self.record_backend(env,self.backend_call(job,env,'observe'))
            else:
                p,manifest=self.backend_package(payload['releaseTag']);env=payload['target'];root=Path(p['directory'])
                require(digest(root/'release.tar')==p['packageSha256'],'原补丁包摘要不一致')
                archive=dict(sha256=p['packageSha256'],manifestSha256=p['manifestSha256'],bytes=(root/'release.tar').stat().st_size)
                from frontend_patch_baseline import target_binding
                require(target_binding(self.runtime.profile(env))==manifest['baseline']['targets'][env],'目标配置漂移，请重新登记基线')
                if action==PREFIX+'deploy':
                    origin=self.backend_call(job,env,'observe')
                    require(origin==manifest['baseline']['origins'][env],'现场起点偏离封包基线')
                    previous={'prod':'test','backup':'prod'}.get(env)
                    if previous:self.backend_call(job,previous,'verify',manifest=manifest)
                    job['backendOrigin']=origin
                    directory=self.runtime.profile(env)['stagingRoot']+'/backend-patches/'+p['releaseTag']+'/'+job['id']
                    ssh=['ssh',*self.runtime.ssh_options(),'root@'+self.runtime.profile(env)['host']]
                    self.step(job,'transfer-single-jar-package')
                    prepared=self.backend_call(job,env,'prepare',manifest=manifest,archive=archive)
                    require(prepared['directory']==directory,'补丁暂存目录不一致')
                    with (root/'release.tar').open('rb') as stream:
                        result=subprocess.run(ssh+['cat > '+shlex.quote(directory+'/release.tar')],stdin=stream,
                                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=900)
                    require(result.returncode==0,'补丁传输失败，尚未停服')
                    self.backend_call(job,env,'stage',manifest=manifest,archive=archive)
                    self.step(job,'switch-backend-with-readonly-startup',effects=True)
                    result=self.backend_call(job,env,'deploy',manifest=manifest,archive=archive,origin=origin)
                    job['result']=result;p['deployments'][env]=dict(status='succeeded',jobId=job['id'],origin=origin)
                    p['accepted'].pop(env,None);p['stage']=env+'-deployed';self.record_backend(env,result['observation'])
                elif action==PREFIX+'accept':
                    actual=self.backend_call(job,env,'verify',manifest=manifest)
                    self.record_backend(env,actual)
                    p['accepted'][env]=dict(jobId=job['id'],actor=job['actor'],note=payload['note'],time=stamp())
                    p['stage']={'test':'tested','prod':'prod-accepted','backup':'completed'}[env]
                elif action==PREFIX+'restore':
                    self.step(job,'restore-original-backend-only',effects=True)
                    result=self.backend_call(job,env,'restore',manifest=manifest,archive=archive,originalJobId=payload['originalJobId'])
                    job['result']=result
                    old=next(j for j in self.state['jobs'] if j['id']==payload['originalJobId']);old['backendRestoredBy']=job['id']
                    if old['status'] in ('failed','interrupted'):old['resolution']=dict(decision='backend-restored',jobId=job['id'],time=stamp())
                    p['deployments'][env]=dict(status='restored',jobId=old['id']);p['accepted'].pop(env,None);p['stage']=env+'-restored'
                    self.record_backend(env,result['observation'])
            job.update(status='succeeded',finishedAt=stamp());self.log(job,'后端补丁操作完成；未执行数据库结构/数据/配置迁移。')
            from post_release_cleanup import run as cleanup_after_acceptance
            cleanup_after_acceptance(self,job)
        except Exception as error:
            message=str(error)
            if isinstance(getattr(self,'password',None),str) and self.password:message=message.replace(self.password,'[REDACTED]')
            job.update(status='interrupted' if getattr(error,'remoteStatusUnknown',False) else 'failed',error=message,finishedAt=stamp())
            self.log(job,'后端补丁失败：'+message)
        finally:
            self.cleanup_active=False
            if tracker:tracker.close()
            self.runtime.operation_context.binding=None;self.save()
