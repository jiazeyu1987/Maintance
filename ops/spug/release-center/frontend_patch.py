"""Add frontend patches to the existing IntRuoyi executor and durable task store."""
import json
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import threading

from executor import digest,require,stamp

PREFIX='frontend-patch-'
ACTIONS={PREFIX+x for x in ('build','register-baseline','refresh','deploy','accept','restore')}
ENVS=('test','prod','backup')


class FrontendPatchMixin:
    def snapshot(self):
        value=super().snapshot()
        value['application']['capabilities']['frontendPatch']=True
        value.setdefault('frontendPatches',[])
        value.setdefault('frontendPatchBaselines',[])
        value.setdefault('frontendPatchEnvironments',{})
        return value

    def frontend_targets(self, package):
        if package.get('observedBaseline'):
            return self.state.get('frontendPatchEnvironments',{})
        return self.state['environments']

    def commits(self):
        raw=self.run(['git','-C',self.c['repo'],'log','--all','-30','--format=%H%x09%s']).decode('utf-8')
        return [dict(commit=line.split('\t',1)[0],message=line.split('\t',1)[1]) for line in raw.splitlines()]

    def frontend_package(self,tag):
        values=[p for p in self.state.get('frontendPatches',[]) if p['releaseTag']==tag]
        require(len(values)==1,'前端补丁不存在')
        p=values[0]
        root=Path(p['directory'])
        require(digest(root/'manifest.json')==p['manifestSha256'],'补丁清单摘要不一致')
        manifest=json.loads((root/'manifest.json').read_text('utf-8'))
        require(manifest.get('kind')=='frontend-patch' and set(manifest['images'])=={'frontend'},'前端补丁清单无效')
        require(manifest['releaseTag']==tag and manifest['baseReleaseTag']==p['baseReleaseTag'],'补丁版本绑定不一致')
        return p,manifest

    def frontend_gate(self,action,payload):
        if action in (PREFIX+'refresh', PREFIX+'register-baseline'):return
        if action==PREFIX+'build':
            from frontend_patch_baseline import build_base
            base,context=build_base(self,payload)
            if not context.get('observedBaseline'):
                require(all(self.state['environments'].get(env,{}).get('releaseTag')==base['releaseTag'] for env in ENVS),
                        '请先统一三服主版本，再选择该基础版本')
            from frontend_patch_build import validate_source
            validate_source(self,base,payload.get('commit'))
            return
        env=payload.get('target')
        require(env in ENVS,'请选择测试、正式或审查目标')
        p,_=self.frontend_package(payload.get('releaseTag'))
        targets=self.frontend_targets(p)
        require(isinstance(payload.get('note'),str) and len(payload['note'].strip())>=5,'请填写至少5字的实际验收或操作依据')
        if action==PREFIX+'restore':
            original=next((j for j in self.state['jobs'] if j['id']==payload.get('originalJobId')),None)
            require(original and original['action']==PREFIX+'deploy' and original.get('effectsStarted')
                    and original.get('target')==env and original.get('releaseTag')==p['releaseTag'] and not original.get('frontendRestoredBy'),
                    '没有本补丁在该目标的可恢复部署任务')
            return
        require(not p.get('rejected'),'该补丁已被拒绝')
        require(not any(self.frontend_failure_blocks(j,env) for j in self.state['jobs']),
                '目标有未处理的失败，请先核对或恢复原前端')
        if action==PREFIX+'accept':
            require(p.get('deployments',{}).get(env,{}).get('status')=='succeeded','尚未完成该目标部署')
        if action==PREFIX+'deploy':
            current=targets.get(env,{})
            require(current.get('releaseTag')==p['baseReleaseTag'],'目标主版本与补丁基础版本不符')
            require(not current.get('frontendPatchTag') or current['frontendPatchTag']<p['releaseTag'],'目标已安装相同或更新补丁')
            if env=='prod':require(p.get('accepted',{}).get('test') and targets.get('test',{}).get('frontendPatchTag')==p['releaseTag'],
                                    '请先完成测试服当前补丁验收')
            if env=='backup':
                require(p.get('accepted',{}).get('prod') and targets.get('prod',{}).get('frontendPatchTag')==p['releaseTag'],
                        '审查服只能使用正式服当前已验收的同一补丁')

    def frontend_failure_blocks(self,job,env):
        if not (job['status'] in ('failed','interrupted') and job.get('effectsStarted')
                and job.get('target')==env and not job.get('resolution')):
            return False
        if job.get('reconciledBy'):
            prior=next((p for p in self.state['packages'] if p['releaseTag']==job.get('releaseTag')),None)
            if prior and self.technical_passed(prior,env,job['reconciledBy']):
                return False
        # A later completed full deployment replaces the old program, without
        # claiming that its failed historical deployment ever succeeded.
        current=self.state['environments'].get(env,{})
        full=next((p for p in self.state['packages'] if p['releaseTag']==current.get('releaseTag')),None)
        action={'test':'publish-test','prod':'promote-prod','backup':'promote-backup'}.get(env)
        if (job.get('action')==action and full and full.get('stage')=='completed'
                and full['releaseTag']>(job.get('releaseTag') or full['releaseTag'])
                and current.get('baselineStatus')=='registered' and current.get('maintenance') is False
                and not current.get('maintenanceUnknown') and not current.get('recoveryPending')):
            _,manifest=self.manifest(full['releaseTag'])
            deployment=full.get('outcomes',{}).get(env,{}).get('deployment',{})
            owner=next((j for j in self.state['jobs'] if j['id']==deployment.get('jobId')),None)
            if (deployment.get('status')=='succeeded' and owner and owner.get('status')=='succeeded'
                    and owner.get('action')==action and owner.get('target')==env
                    and owner.get('releaseTag')==full['releaseTag']
                    and manifest.get('releaseTag')==full['releaseTag']
                    and current.get('images',{}).get('backend')==manifest['images']['backend']['id']
                    and job.get('finishedAt')
                    and owner.get('createdAt','')>job['finishedAt'] and self.technical_passed(full,env)):
                return False
        return True

    def submit(self,action,payload,actor):
        if action not in ACTIONS:
            if action=='build-release':
                active={e.get('frontendPatchTag') for e in self.state['environments'].values()}-{None}
                active.update(e['frontendPatchTag'] for e in self.state.get('frontendPatchEnvironments',{}).values()
                              if e.get('frontendPatchTag'))
                for p in self.state.get('frontendPatches',[]):
                    if p['releaseTag'] in active:
                        self.run(['git','-C',self.c['repo'],'merge-base','--is-ancestor',p['gitCommit'],payload.get('commit','')])
            return super().submit(action,payload,actor)
        with self.lock:
            self.ensure_persistence()
            require(not getattr(self,'draining',False),'执行器正在停止')
            require(not getattr(self,'cleanup_active',False),'发布收尾清理仍在执行，请等待其完成')
            require(payload.get('applicationId')==self.c['applicationId'],'应用身份不匹配')
            request_id=payload.get('requestId','')
            require(isinstance(request_id,str) and re.fullmatch('[a-zA-Z0-9-]{8,80}',request_id),'requestId required')
            for old in self.state['jobs']:
                if old.get('requestId')==request_id:
                    require(old['action']==action and old['payload']==payload,'请求编号已绑定其他操作')
                    return old
            require(not any(j['status']=='running' or j['status']=='interrupted' and not j.get('resolution') for j in self.state['jobs'])
                    or action==PREFIX+'restore' and not any(j['status']=='running' for j in self.state['jobs']),
                    '请等待或核对当前发布任务')
            self.frontend_gate(action,payload)
            job=dict(id='JOB-'+secrets.token_hex(5),requestId=request_id,action=action,payload=payload,actor=actor,
                     releaseTag=payload.get('releaseTag'),target=payload.get('target'),status='running',createdAt=stamp(),logs=[])
            self.state['jobs'].insert(0,job)
            self.save()
            self.worker=threading.Thread(target=self.frontend_job,args=(job,),daemon=True)
            self.worker.start()
            return job

    def frontend_call(self,job,env,action,**kwargs):
        self.runtime.operation_context.binding=(job,self.save)
        return self.runtime.call(env,PREFIX+action,**kwargs)

    def frontend_job(self,job):
        self.cleanup_active = job['action'] == PREFIX+'accept' and job.get('target') == 'backup'
        try:
            action,payload=job['action'],job['payload']
            self.step(job,action)
            self.frontend_gate(action,payload)
            if action==PREFIX+'build':
                from frontend_patch_build import build
                build(self,job)
            elif action==PREFIX+'register-baseline':
                from frontend_patch_baseline import target_binding,validate_observations
                origins={env:self.frontend_call(job,env,'observe') for env in ENVS}
                commit=validate_observations(origins)
                for env in ENVS:
                    require(self.frontend_call(job,env,'observe')==origins[env],
                            env+': 读取期间程序发生变化，未登记补丁基线')
                baseline=dict(id='FPB-'+secrets.token_hex(10),releaseTag=origins['prod']['releaseTag'],
                              gitCommit=commit,origins=origins,registeredAt=stamp(),jobId=job['id'],
                              targets={env:target_binding(self.runtime.profile(env)) for env in ENVS})
                self.state.setdefault('frontendPatchBaselines',[]).insert(0,baseline)
                self.state['frontendPatchEnvironments']={env:dict(releaseTag=v['releaseTag'],
                    frontendPatchTag=v.get('frontendPatchTag'),frontendPatchObservation=v,observedAt=stamp())
                    for env,v in origins.items()}
                job['result']=dict(baselineId=baseline['id'],releaseTag=baseline['releaseTag'],gitCommit=commit)
                self.log(job,'已从实际三服登记前端补丁基线；没有创建完整发布包或数据库基线。')
            elif action==PREFIX+'refresh':
                for env in ENVS:
                    actual=self.frontend_call(job,env,'observe')
                    self.record_frontend(env,actual,observed=bool(self.state.get('frontendPatchBaselines')))
            else:
                env=payload['target']
                p,manifest=self.frontend_package(payload['releaseTag'])
                root=Path(p['directory'])
                require(digest(root/'release.tar')==p['packageSha256'],'补丁包原件摘要不一致')
                archive=dict(sha256=p['packageSha256'],manifestSha256=p['manifestSha256'])
                if action==PREFIX+'deploy':
                    origin=self.frontend_call(job,env,'observe')
                    if p.get('observedBaseline'):
                        from frontend_patch_baseline import validate_live_origin
                        validate_live_origin(self,p['observedBaseline'],env,origin)
                    from frontend_patch_agent import validate_origin
                    validate_origin(origin,origin,manifest,{'require':require,'environment':env})
                    if env=='backup':
                        prod=self.frontend_call(job,'prod','verify',manifest=manifest)
                        require(prod['frontendPatchTag']==p['releaseTag'],'正式服实际补丁已改变')
                    job['frontendOrigin']=origin
                    profile=self.runtime.profile(env)
                    directory=profile['stagingRoot']+'/frontend-patches/'+p['releaseTag']+'/'+job['id']
                    ssh=['ssh',*self.runtime.ssh_options(),'root@'+profile['host']]
                    self.step(job,'transfer-frontend-patch')
                    self.run(ssh+['mkdir -p '+shlex.quote(directory)],timeout=30)
                    with (root/'release.tar').open('rb') as stream:
                        result=subprocess.run(ssh+['cat > '+shlex.quote(directory+'/release.tar')],stdin=stream,
                                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=900)
                    require(result.returncode==0,'补丁传输失败；尚未停止前端')
                    self.frontend_call(job,env,'stage',manifest=manifest,archive=archive)
                    self.step(job,'replace-frontend-only',effects=True)
                    result=self.frontend_call(job,env,'deploy',manifest=manifest,archive=archive,origin=origin)
                    job['result']=result
                    p['deployments'][env]=dict(status='succeeded',jobId=job['id'],time=stamp(),origin=origin)
                    p['accepted'].pop(env,None)
                    p['stage']=env+'-deployed'
                    self.record_frontend(env,result['observation'],observed=bool(p.get('observedBaseline')))
                elif action==PREFIX+'accept':
                    actual=self.frontend_call(job,env,'verify',manifest=manifest)
                    self.record_frontend(env,actual,observed=bool(p.get('observedBaseline')))
                    p['accepted'][env]=dict(jobId=job['id'],actor=job['actor'],note=payload['note'],time=stamp())
                    p['stage']={'test':'tested','prod':'prod-accepted','backup':'completed'}[env]
                elif action==PREFIX+'restore':
                    self.step(job,'restore-original-frontend',effects=True)
                    result=self.frontend_call(job,env,'restore',manifest=manifest,archive=archive,originalJobId=payload['originalJobId'])
                    job['result']=result
                    original=next(j for j in self.state['jobs'] if j['id']==payload['originalJobId'])
                    original['frontendRestoredBy']=job['id']
                    if original['status'] in ('failed','interrupted'):
                        original['resolution']=dict(decision='frontend-restored',jobId=job['id'],note=payload['note'],time=stamp())
                    p['deployments'].setdefault(env,{'jobId':original['id']})['status']='restored'
                    p['accepted'].pop(env,None)
                    p['stage']=env+'-restored'
                    self.record_frontend(env,result['observation'],observed=bool(p.get('observedBaseline')))
            job.update(status='succeeded',finishedAt=stamp())
            self.log(job,'前端补丁操作完成；后端及数据库保持原容器。')
            from post_release_cleanup import run as cleanup_after_acceptance
            cleanup_after_acceptance(self,job)
        except Exception as error:
            job.update(status='failed',error=str(error),finishedAt=stamp())
            self.log(job,'前端补丁操作失败：'+str(error))
        finally:
            self.cleanup_active = False
            self.runtime.operation_context.binding=None
            self.save()

    def record_frontend(self,env,actual,*,observed=False):
        if observed:
            self.state.setdefault('frontendPatchEnvironments',{})[env]=dict(releaseTag=actual['releaseTag'],
                frontendPatchTag=actual.get('frontendPatchTag'),frontendPatchObservation=actual,observedAt=stamp())
            self.save()
            return
        current=self.state['environments'].setdefault(env,{})
        require(current.get('releaseTag')==actual['releaseTag'],'主版本已变化，不能仅更新补丁状态')
        current.update(frontendPatchTag=actual['frontendPatchTag'],frontendPatchObservation=actual,observedAt=stamp())
        # Refresh the full runtime fingerprint so later full releases use the
        # actual patched frontend as their origin, never its replaced image.
        if actual['components']['frontend']['imageId']!=current.get('images',{}).get('frontend'):
            full=self.runtime.observe(env)
            require(full['images']['frontend']==actual['components']['frontend']['imageId'] and full['releaseTag']==actual['releaseTag'],
                    '完整状态观察与前端补丁身份不一致')
            current.update(full)
        self.save()
