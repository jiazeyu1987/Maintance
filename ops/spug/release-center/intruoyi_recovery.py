"""Persisted operator actions for recovery and separate formal technical checks."""
import re
import secrets
import threading

from executor import require, stamp

RECOVERY_ACTIONS = frozenset(('inspect-release-recovery','recover-release','accept-recovery','verify-prod','verify-backup'))
DEPLOYMENTS = {'publish-test':'test','promote-prod':'prod','promote-backup':'backup'}


def original_deployment(executor, package, payload):
    original = next((j for j in executor.state['jobs'] if j['id'] == payload.get('jobId')), None)
    require(original and original.get('releaseTag') == package['releaseTag']
            and original.get('action') in DEPLOYMENTS and original.get('effectsStarted')
            and original.get('target') == DEPLOYMENTS[original['action']], 'Select the original deployment with recorded effects')
    resolution = original.get('resolution', {})
    verified_only = resolution.get('decision') == 'reconciled' and resolution.get('disposition') == 'verify-deployment'
    require(original['status'] in ('failed','interrupted','succeeded') and (not resolution or verified_only),
            'Original deployment is active or already resolved')
    require(original.get('originFingerprint') and original.get('originState'), 'Recorded original deployment origin required')
    return original


def submit_recovery(executor, action, payload, actor):
    with executor.lock:
        request_id = payload.get('requestId')
        require(isinstance(request_id,str) and re.fullmatch('[a-zA-Z0-9-]{8,80}',request_id), 'requestId required')
        existing = next((j for j in executor.state['jobs'] if j['requestId'] == request_id),None)
        if existing:
            require(existing['action'] == action and existing['payload'] == payload, 'Request ID binding mismatch')
            return existing
        require(not any(j['status']=='running' for j in executor.state['jobs']), 'Another task is still executing')
        package,_ = executor.manifest(payload.get('releaseTag'))
        require(not package.get('baseline'), 'A baseline cannot be recovered as a deployment')
        if action in ('verify-prod','verify-backup'):
            env = 'prod' if action == 'verify-prod' else 'backup'
            require(package['stage'] == env+'-deployed' and not package.get('abandoned'), 'Pending formal deployment required')
            require(not executor.state['environments'][env].get('recoveryPending'), 'Recovery is awaiting acceptance')
            require(package.get('outcomes',{}).get(env,{}).get('deployment',{}).get('status') == 'succeeded',
                    'Completed deployment required for technical recheck')
            require(not any(j['status']=='interrupted' and not j.get('resolution') for j in executor.state['jobs']),
                    'Interrupted remote operation must be reconciled before technical checks')
            require(not any(executor.failed_task_blocks(j,action,payload,package) for j in executor.state['jobs']),
                    'Unresolved failure prevents technical recheck')
            original = None
        else:
            original = original_deployment(executor,package,payload)
            env = original['target']
            require(package.get('outcomes',{}).get(env,{}).get('deployment',{}).get('jobId') == original['id'],
                    'A newer deployment superseded the selected task')
            require(package.get('outcomes',{}).get(env,{}).get('acceptance',{}).get('status') != 'passed',
                    'Business accepted releases cannot restore pre-release data')
            recovery = package.get('outcomes',{}).get(env,{}).get('recovery',{})
            if action == 'recover-release':
                require(recovery.get('status') != 'pending-acceptance',
                        'Recovery already completed; accept the restored version instead of restoring data again')
            if action != 'inspect-release-recovery':
                require(isinstance(payload.get('note'),str) and len(payload['note'].strip())>=5,
                        'Explicit recovery reason or acceptance note required')
            for task in executor.state['jobs']:
                if task['status']=='interrupted' and not task.get('resolution'):
                    require(task['id']==original['id'] or task.get('originalDeploymentJobId')==original['id'],
                            'Another interrupted operation requires reconciliation')
        job=dict(id='JOB-'+secrets.token_hex(5),requestId=request_id,action=action,payload=payload,
                 releaseTag=package['releaseTag'],actor=actor,status='running',createdAt=stamp(),logs=[],target=env)
        if original:
            job['originalDeploymentJobId']=original['id']
        executor.state['jobs'].insert(0,job)
        executor.save()
        executor.worker=threading.Thread(target=executor.execute,args=(job,),daemon=True)
        executor.worker.start()
        return job


def execute_recovery(executor,job):
    package,env=None,job['target']
    try:
        executor.log(job,'Started '+job['action'])
        package,manifest=executor.package(job['releaseTag'])
        action=job['action']
        if action in ('verify-prod','verify-backup'):
            executor.verify_technical(env,package,manifest,job)
        else:
            original=original_deployment(executor,package,job['payload'])
            binding=dict(releaseTag=package['releaseTag'],originalJobId=original['id'],
                         packageSha256=package['packageSha256'],originFingerprint=original['originFingerprint'])
            if action=='inspect-release-recovery':
                executor.step(job,'inspect-original-migration-progress')
                result=executor.runtime.call(env,action,**binding,plan=original['migrationPlan']['items'])
                original['migrationExecution']=result
                job['result']=result
            elif action=='recover-release':
                executor.step(job,'restore-original-release-checkpoint',effects=True)
                executor.state['environments'][env].update(maintenanceUnknown=True,recoveryPending=True)
                executor.save()
                result=executor.runtime.call(env,action,**binding,jobId=job['id'])
                observed,receipt=result['observation'],result['receipt']
                require(receipt['originalJobId']==original['id'] and receipt['phase']=='restored'
                        and receipt['packageSha256']==package['packageSha256'], 'Recovery receipt binding differs')
                for key in ('releaseTag','images','schemaSha256','ledgerSha256'):
                    require(observed[key]==original['originState'][key], 'Restored origin differs: '+key)
                require(observed['maintenance'] is True and observed['backendHealth']['status']=='UP'
                        and observed['frontendHttpStatus']==200, 'Restored version must remain healthy in maintenance')
                executor.state['environments'][env]=dict(observed,baselineStatus='registered',maintenanceUnknown=False,recoveryPending=True)
                package.setdefault('outcomes',{}).setdefault(env,{})['recovery']=dict(
                    status='pending-acceptance',jobId=job['id'],step=job.get('currentStep'),time=stamp(),
                    originalJobId=original['id'],receipt=receipt)
                package['stage']=env+'-recovered'
                job['result']=dict(releaseTag=observed['releaseTag'],receipt=receipt,maintenance=True)
                job.update(status='succeeded',finishedAt=stamp())
                executor.log(job,'Original data/program restored; business remains closed until explicit recovery acceptance')
            else:
                recovery=package.get('outcomes',{}).get(env,{}).get('recovery',{})
                require(recovery.get('status')=='pending-acceptance' and recovery.get('originalJobId')==original['id'],
                        'Verified recovery awaiting acceptance required')
                executor.step(job,'accept-restored-origin-and-open-business',effects=True)
                executor.state['environments'][env]['maintenanceUnknown']=True
                executor.save()
                result=executor.runtime.call(env,action,**binding,jobId=job['id'],recoveryJobId=recovery['receipt']['jobId'])
                observed,receipt=result['observation'],result['receipt']
                require(receipt['phase']=='opened' and receipt.get('confirmedByJobId',receipt['openingJobId'])==job['id'] and observed['maintenance'] is False,
                        'Recovery opening has not been confirmed')
                for key in ('releaseTag','images','schemaSha256','ledgerSha256'):
                    require(observed[key]==original['originState'][key], 'Opened origin differs: '+key)
                executor.state['environments'][env]=dict(observed,baselineStatus='registered',maintenanceUnknown=False,recoveryPending=False)
                package.setdefault('outcomes',{}).setdefault(env,{})['recovery']=dict(
                    status='accepted',jobId=job['id'],step=job.get('currentStep'),time=stamp(),
                    originalJobId=original['id'],receipt=receipt,note=job['payload']['note'],actor=job['actor'])
                # Keep failures and SQL diagnostics. Resolution records what was
                # restored; it never converts a failed migration into success.
                resolution=dict(decision='restored',jobId=job['id'],actor=job['actor'],time=stamp(),
                                originalDeploymentJobId=original['id'],note=job['payload']['note'],restoredReleaseTag=observed['releaseTag'])
                original['resolution']=resolution
                for prior in executor.state['jobs']:
                    if prior['id']!=job['id'] and prior.get('releaseTag')==package['releaseTag'] and prior.get('target')==env \
                            and prior['status'] in ('failed','interrupted') and not prior.get('resolution') \
                            and (prior.get('originalDeploymentJobId')==original['id']
                                 or prior.get('action') in ('reject-acceptance','verify-prod','verify-backup','accept-prod','accept-backup')
                                 and prior.get('createdAt','')>=original['createdAt']):
                        prior['resolution']=dict(resolution)
                package['stage']=env+'-restored'
                if env!='backup':
                    package['abandoned']=True
                job['result']=dict(releaseTag=observed['releaseTag'],receipt=receipt,maintenance=False)
                # One durable state includes opening, original-task resolution,
                # candidate abandonment and completion. No save may split them.
                job.update(status='succeeded',finishedAt=stamp())
                executor.log(job,'Recovery accepted and original version opened; original failure records retained')
        job['status']='succeeded'
        executor.save()
    except Exception as error:
        job.update(status='interrupted' if getattr(error,'remoteStatusUnknown',False) else 'failed',
                   error=str(error).replace(executor.password,'[REDACTED]'))
        executor.log(job,'Recovery/check stopped: '+job['error'])
    finally:
        job['finishedAt']=stamp()
        executor.save()
