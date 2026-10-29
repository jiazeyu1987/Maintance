"""IntRuoyi's remote adapter for the existing persistent release workflow."""
import json
from pathlib import Path
import re
import secrets
import threading

from executor import Executor, main, require, stamp
from release_order import deployment_blocks
from intruoyi_build import build, target_input_plan
from intruoyi_runtime import Runtime, audit_ledger, package_identity, rehearsal_profile, gxp_release_mode, validate_gxp_runtime
from intruoyi_rehearsal import active_remote_progress
from intruoyi_metadata import restore as restore_metadata, reference as metadata_reference, remote as metadata_remote


def validate_origin(value):
    require(value.get('schemaSha256') and value.get('fingerprint'), 'Incomplete schema/runtime origin')
    require(isinstance(value.get('ledgerRecords'), list), 'Migration records missing')
    require(value.get('backendHealth', {}).get('status') == 'UP' and value.get('frontendHttpStatus') == 200,
            'Actual backend UP and frontend 200 required for origin registration')
    images = value.get('images', {})
    require(all(re.fullmatch(r'sha256:[a-f0-9]{64}', images.get(role, '')) for role in ('backend','frontend')),
            'Actual frontend/backend image identities required')
    require(value.get('releaseTag'), 'Frontend release-info.json version identity is missing or invalid')
    return value


def validate_restored_origin(original, observation):
    require(original.get('effectsStarted') and original.get('action') in
            ('publish-test', 'upgrade-rehearsal', 'promote-prod', 'promote-backup'),
            'Explicitly restored deployment required; acceptance cannot be abandoned this way')
    require(original.get('originFingerprint') and observation.get('fingerprint') == original['originFingerprint'],
            'Restored program/schema/ledger/runtime origin differs')
    require(observation.get('releaseTag') == original.get('originState', {}).get('releaseTag'),
            'Restored program version differs')
    validate_origin(observation)
    require(observation.get('maintenance') is False and observation.get('readOnly') == dict(read_only=False, super_read_only=False),
            'Restored business access/write state not confirmed')


def passed_rehearsal(package, target, fingerprint):
    """A different source or a passed check for another package cannot authorize deployment."""
    passed = [r for r in package.get('rehearsals', [])
              if r.get('source') == target and r.get('status') == 'passed'
              and r.get('originFingerprint') == fingerprint
              and r.get('packageSha256') == package['packageSha256']
              and r.get('upgradedSchemaSha256')]
    require(passed, target + ': full-data rehearsal must pass for this package and current origin before deployment')
    return passed[-1]


def passed_rehearsal_schema(package, target, fingerprint):
    return passed_rehearsal(package, target, fingerprint)['upgradedSchemaSha256']


def validated_production_rehearsal(package):
    """Backup consumes the rehearsal explicitly bound to accepted production."""
    identity = package.get('validatedProductionRehearsal')
    rows = [r for r in package.get('rehearsals', []) if r.get('id') == identity
            and r.get('source') == 'prod' and r.get('status') == 'passed'
            and r.get('packageSha256') == package['packageSha256'] and r.get('upgradedSchemaSha256')]
    require(identity and len(rows) == 1, 'Accepted production rehearsal binding required for backup')
    return rows[0]


def backup_rehearsal_schema(package, observation):
    rehearsal = validated_production_rehearsal(package)
    origin = rehearsal.get('originState', {})
    for key in ('releaseTag', 'images', 'schemaSha256', 'ledgerSha256'):
        require(origin.get(key) and observation.get(key) == origin[key],
                'Backup origin differs from validated production origin: ' + key)
    return rehearsal['upgradedSchemaSha256']


from rollback_mixin import RollbackMixin

class _IntRuoyiExecutor(Executor):
    TECHNICAL_ACTIONS = {'mark-tested':'test','accept-rehearsal':'rehearsal','verify-prod':'prod','verify-backup':'backup'}

    def run(self, args, data=None, cwd=None, timeout=900, env=None):
        if self.c.get('executionMode') == 'windows-service' and Path(args[0]).name.lower() in ('git', 'git.exe'):
            # The configured source is user-owned; SCM runs as LocalSystem.
            # Trust only this explicit repository for this command, never all repos.
            repository = Path(self.c['repo']).resolve(strict=True).as_posix()
            args = [args[0], '-c', 'safe.directory='+repository, *args[1:]]
        return super().run(args, data=data, cwd=cwd, timeout=timeout, env=env)

    def technical_verification_enabled(self):
        return True

    def technical_passed(self, package, env, job_id=None):
        records = [package.get('outcomes', {}).get(env, {}).get('technical', {})]
        if job_id is not None:
            records = package.get('technicalHistory', []) + records
        for record in records:
            owner = next((j for j in self.state['jobs'] if j['id'] == record.get('jobId')), None)
            if (record.get('env') == env and record.get('status') == 'passed'
                    and record.get('releaseTag') == package['releaseTag'] and record.get('packageSha256') == package['packageSha256']
                    and (job_id is None or record.get('jobId') == job_id)
                    and all(record.get('checks', {}).get(key, {}).get('status') == 'passed' for key in ('version','upgrade','login'))
                    and owner and owner['status'] == 'succeeded' and owner.get('releaseTag') == package['releaseTag']
                    and owner.get('target') == env):
                return True
        return False

    def technical_retryable(self, original, package, env):
        if original.get('status') != 'failed' or original.get('releaseTag') != package['releaseTag'] or original.get('resolution'):
            return False
        if original.get('action') == 'reject-acceptance' and not original.get('effectsStarted'):
            if env in ('prod', 'backup'):
                return False
            rows = [row for row in package.get('acceptances', []) if row.get('jobId') == original['id']]
            return len(rows) == 1 and rows[0].get('env') == env and original.get('target') == env
        proof = original.get('technicalVerification', {})
        return (proof.get('env') == env and proof.get('jobId') == original['id']
                and proof.get('releaseTag') == package['releaseTag'] and proof.get('packageSha256') == package['packageSha256']
                and proof.get('status') == 'failed'
                and package.get('outcomes', {}).get(env, {}).get('deployment', {}).get('status') == 'succeeded')

    def failed_task_blocks(self, failed, action, payload, package):
        if failed.get('action') in ('check-prerequisites','scan-artifacts','clean-artifacts'):
            return False
        if not super().failed_task_blocks(failed, action, payload, package):
            return False
        reconciled = failed.get('reconciledBy')
        if reconciled and self.technical_passed(package, failed.get('target'), reconciled):
            return False
        env = self.TECHNICAL_ACTIONS.get(action)
        return not (env and self.technical_retryable(failed, package, env))

    def verified_origin(self, package, fingerprint):
        return any(record.get('status') == 'passed' and record.get('source') == 'prod'
                   and record.get('originFingerprint') == fingerprint and record.get('packageSha256') == package['packageSha256']
                   and self.technical_passed(package, 'rehearsal', record.get('technical', {}).get('jobId'))
                   and record.get('technical', {}).get('status') == 'passed' for record in package.get('rehearsals', []))

    def verify_technical(self, env, package, manifest, job, *, opening=False):
        require(not opening or job['action'] == 'reconcile-interruption', 'Explicit opening action required')
        binding = dict(jobId=job['id'], env=env, releaseTag=package['releaseTag'], packageSha256=package['packageSha256'])
        technical = dict(binding, status='running', phase='version', time=stamp(),
                         checks={name:{'status':'pending'} for name in ('version','upgrade','login')})
        package.setdefault('technicalHistory', []).append(technical)
        package.setdefault('outcomes', {}).setdefault(env, {})['technical'] = technical
        job['technicalVerification'] = technical
        if env == 'rehearsal':
            self.active_rehearsal(package)['technical'] = technical
        self.save()
        try:
            self.step(job, 'technical-version')
            technical['checks']['version']['status'] = 'running'
            self.save()
            verified_package, verified_manifest = self.package(package['releaseTag'])
            require(verified_package['packageSha256'] == binding['packageSha256'] and verified_manifest == manifest,
                    'Technical verification package binding changed')
            require(package.get('outcomes', {}).get(env, {}).get('deployment', {}).get('status') == 'succeeded',
                    'A confirmed deployment is required before technical verification')
            observation = self.runtime.observe(env)
            expected_images = {role:manifest['images'][role]['id'] for role in ('backend','frontend')}
            require(observation.get('releaseTag') == package['releaseTag'] and observation.get('images') == expected_images,
                    'Actual version or frontend/backend image differs from immutable package')
            technical['checks']['version'] = dict(status='passed', releaseTag=observation['releaseTag'], images=expected_images)
            technical['phase'] = 'upgrade'
            technical['checks']['upgrade']['status'] = 'running'
            self.step(job, 'technical-upgrade')
            audit = self.audit_target(env, package, manifest)
            current = audit['observation']
            require(current.get('releaseTag') == package['releaseTag'] and current.get('images') == expected_images,
                    'Candidate changed during technical verification')
            validate_origin(current)
            require(current.get('readOnly') == dict(read_only=False, super_read_only=False), 'Target write protection prevents technical acceptance')
            health = self.health(env, package['releaseTag'])
            validate_gxp_runtime(health['writerControls'], gxp_release_mode(manifest))
            plan_env = self.active_rehearsal(package)['source'] if env == 'rehearsal' else env
            plan = target_input_plan(manifest['migrations'], current['ledgerRecords'], plan_env)
            require(plan.get('status') == 'passed' and not any(item['action'] == 'APPLY' for item in plan['items']),
                    'Candidate still has unapplied required migrations')
            audit_ledger(current, manifest)
            if env == 'prod':
                deployed = package['outcomes']['prod']['deployment']
                rehearsals = [r for r in package.get('rehearsals', []) if r.get('id') == deployed.get('rehearsalId')
                              and r.get('source') == 'prod' and r.get('status') == 'passed'
                              and r.get('packageSha256') == package['packageSha256']
                              and r.get('technical', {}).get('status') == 'passed'
                              and self.technical_passed(package,'rehearsal',r.get('technical',{}).get('jobId'))]
                require(len(rehearsals) == 1 and current['schemaSha256'] == rehearsals[0]['upgradedSchemaSha256'],
                        'Production technical acceptance requires its bound successful rehearsal')
            elif env == 'backup':
                rehearsal = validated_production_rehearsal(package)
                require(self.technical_passed(package,'prod') and current['schemaSha256'] == rehearsal['upgradedSchemaSha256'],
                        'Backup technical acceptance requires the same accepted production package/schema')
            technical['checks']['upgrade'] = dict(status='passed', schemaSha256=current['schemaSha256'],
                ledgerSha256=current['ledgerSha256'], migrationCount=len(plan['items']), remainingApplyCount=0,
                backendHealth=current['backendHealth'], frontendHttpStatus=current['frontendHttpStatus'], health=health)
            technical['phase'] = 'login'
            technical['checks']['login']['status'] = 'running'
            self.step(job, 'technical-login')
            from intruoyi_login import verify_login
            profile = self.runtime.profile(env)
            target_url = profile['acceptanceUrl'] if current.get('maintenance') is True else profile['entryUrl']
            evidence_dir = self.root / 'technical-evidence' / job['id'] / env
            receipt = verify_login(self.c, target_url, evidence_dir, binding)
            require(receipt.get('status') == 'passed' and receipt.get('binding') == binding and receipt.get('authenticated') is True,
                    'Real browser login evidence does not match this technical verification')
            technical['checks']['login'] = dict(status='passed', evidence=receipt)
            self.save()
            # A technical check never substitutes for the operator's business
            # acceptance. Only the explicit acceptance job may open admission.
            opening = opening or job['action'] == {'prod':'accept-prod','backup':'accept-backup'}.get(env)
            if opening:
                technical['phase'] = 'opening'
                technical['opening'] = {'status':'running'}
                self.save()
                if current.get('maintenance') is True:
                    self.maintenance(env, False)
                else:
                    require(current.get('maintenance') is False, 'Formal target maintenance state is unknown')
                opened_health = self.health(env, package['releaseTag'])
                validate_gxp_runtime(opened_health['writerControls'], gxp_release_mode(manifest))
                opened = self.runtime.observe(env)
                validate_origin(opened)
                require(opened.get('maintenance') is False and opened.get('readOnly') == dict(read_only=False,super_read_only=False)
                        and opened['releaseTag'] == package['releaseTag'] and opened['images'] == expected_images
                        and opened['schemaSha256'] == current['schemaSha256'] and opened['ledgerSha256'] == current['ledgerSha256'],
                        'Formal target opening did not preserve verified package and migration state')
                self.state['environments'][env] = dict(opened, observedAt=stamp(), baselineStatus='registered', maintenanceUnknown=False)
                technical['opening'] = {'status':'passed'}
            stage = {'test':'tested','rehearsal':'rehearsal-passed','prod':'prod-deployed','backup':'backup-deployed'}[env]
            if opening:
                stage = 'prod-accepted' if env == 'prod' else 'completed'
            if env == 'rehearsal':
                record = self.active_rehearsal(package)
                require(record.get('source') == 'prod' and record.get('packageSha256') == package['packageSha256'],
                        'Technical rehearsal acceptance must bind the production origin and immutable package')
                record.update(status='passed', actor=job['actor'], acceptedAt=stamp())
            elif env == 'prod' and opening:
                package['validatedProductionRehearsal'] = rehearsals[0]['id']
            package['stage'] = stage
            technical.update(status='passed', phase='complete', finishedAt=stamp())
            reconciled = []
            for prior in self.state['jobs']:
                if prior['id'] != job['id'] and self.technical_retryable(prior, package, env):
                    prior.update(reconciledBy=job['id'], superseded=True)
                    reconciled.append(prior['id'])
            technical['reconcilesJobIds'] = reconciled
            if opening:
                note = job['payload']['note']
                package.setdefault('outcomes', {}).setdefault(env, {})['acceptance'] = dict(
                    status='passed', jobId=job['id'], step=job.get('currentStep'), time=stamp(),
                    actor=job['actor'], note=note)
                package.setdefault('acceptances', []).append(dict(action=job['action'], env=env,
                    note=note, actor=job['actor'], time=stamp(), jobId=job['id']))
                job['status'] = 'succeeded'
                job['finishedAt'] = stamp()
            self.save()
            self.log(job, 'Version/images, complete migration/startup and real browser login passed for ' + env)
        except Exception as error:
            phase = technical['phase']
            message = str(error).replace(self.password, '[REDACTED]')
            if phase in technical['checks']:
                technical['checks'][phase].update(status='failed', error=message)
            elif phase == 'opening':
                technical['opening'] = dict(status='failed', error=message)
            technical.update(status='failed', error=message, finishedAt=stamp())
            package['stage'] = {'test':'test-deployed','rehearsal':'rehearsal-upgraded','prod':'prod-deployed','backup':'backup-deployed'}[env]
            if env == 'rehearsal':
                self.active_rehearsal(package)['status'] = 'upgraded'
            self.save()
            raise

    def __init__(self, config):
        require(config.get('applicationId') == 'intruoyi', 'IntRuoyi application identity required')
        require(config.get('runtimeKind') == 'remote-intruoyi', 'Explicit remote IntRuoyi runtime required')
        require(set(config.get('targets', {})) >= {'test','prod','backup'}, 'All three real targets required')
        require(config.get('stateDir') and config.get('buildWorktreeRoot'), 'Dedicated state and worktree paths required')
        require(config.get('mysqlImage') == 'mysql:8.0.39', 'Pinned MySQL runtime required')
        super().__init__(config)
        self.track_local_processes = True
        self.runtime = Runtime(config)
        # An interrupted diagnostic has no deployment effects to reconcile.
        # Keep its failure visible and permit a fresh diagnostic; never mark it passed.
        for job in self.state['jobs']:
            if job['action']=='clean-artifacts' and job['status']=='interrupted':
                job.update(status='failed',error='清理中断，部分删除结果未确认；保留明细，请重新扫描实际剩余产物。')
            if job['action'] in ('check-prerequisites','scan-artifacts') and job['status'] == 'interrupted':
                job.update(status='failed', error='检查或扫描被中断，结果不完整，请重新执行。')
                if job.get('result'):
                    job['result']['status'] = 'interrupted'
        self.save()
        if 'rehearsal' in self.state['environments']:
            source = self.state['environments']['rehearsal'].get('sourceEnvironment')
            self.runtime.targets['rehearsal'] = rehearsal_profile(config, source)

    def snapshot(self):
        with self.lock:
            self.ensure_persistence()
            if active_remote_progress(self.state, self.c, self.runtime):
                self.save()
            targets = {env: {key:value for key,value in target.items() if key in ('label','url','acceptanceUrl')}
                       for env,target in self.c['targets'].items()}
            configured = bool(self.c.get('rehearsal'))
            application = dict(id=self.c['applicationId'], name=self.c['displayName'], repo=self.c['repo'],
                               runtimeKind='remote-intruoyi', targets=targets,
                               packageStoragePath=str(self.root/'packages'),
                               capabilities=dict(initializeBaseline=False, auditBaseline=False, registerTargets=True,
                                                 restoreMetadata=bool(self.c.get('metadataRepair')),
                                                 buildRelease=True, prepareRehearsal=configured, releaseRecovery=True,
                                                 businessAcceptance=True, interruptionReconciliation=True,
                                                 independentBackupRetry=True, releasePrecheck=True, artifactRetention=True, nasPackageRetry=True))
            if not configured:
                application['capabilityReasons'] = dict(prepareRehearsal='尚未配置独立数据副本、运行资源与外部接口隔离，不能准备演练。')
            if self.c.get('nasPath'):
                application['nasPath'] = self.c['nasPath']
            import os
            from backup_retry import available, test_retry_available
            return json.loads(json.dumps(dict(self.state, application=application, deploymentBlocks=deployment_blocks(self.state),
                backupRetries={p['releaseTag']: available(self.state, p) for p in self.state['packages']},
                testRetries={p['releaseTag']: test_retry_available(self.state, p) for p in self.state['packages']},
                executorRuntime=dict(pid=os.getpid(), mode=self.c.get('executionMode', 'console'),
                                     draining=getattr(self, 'draining', False)))))

    def submit(self, action, payload, actor):
        self.ensure_persistence()
        require(not getattr(self, 'draining', False), 'Executor is draining for service stop; no new task accepted')
        require(payload.get('applicationId') == self.c['applicationId'], 'Request application identity mismatch')
        require(action not in ('initialize-baseline','audit-baseline'), 'Remote databases must never use demo initialization')
        require(action != 'function-passed', 'Use mark-tested to accept the actual deployed test candidate')
        # A repeated request returns its original task even if a newer release now runs.
        require(isinstance(payload.get('requestId'), str) and re.fullmatch('[a-zA-Z0-9-]{8,80}', payload['requestId']),
                'requestId required')
        with self.lock:
            existing = next((j for j in self.state['jobs'] if j.get('requestId') == payload['requestId']), None)
            if existing:
                require(existing['action'] == action and existing['payload'] == payload, 'Request ID binding mismatch')
                return existing
        from intruoyi_recovery import RECOVERY_ACTIONS, submit_recovery
        if action == 'publish-test':
            from backup_retry import test_retry_available, validate_test_retry
            package, _ = self.manifest(payload.get('releaseTag'))
            original_id = test_retry_available(self.state, package)
            if original_id or payload.get('retryOf'):
                validate_test_retry(self, package, payload.get('retryOf'))
        if action in ('scan-artifacts','clean-artifacts'):
            from artifact_retention import submit
            return submit(self,action,payload,actor)
        if action == 'check-prerequisites':
            from release_precheck import submit
            return submit(self, payload, actor)
        from interruption import ACTIONS, submit as submit_interruption
        if action in ACTIONS:
            return submit_interruption(self, action, payload, actor)
        if action in RECOVERY_ACTIONS:
            return submit_recovery(self, action, payload, actor)
        if action in ('accept-prod', 'accept-backup'):
            require(isinstance(payload.get('note'), str) and len(payload['note'].strip()) >= 5,
                    'Explicit business acceptance note required before opening')
        if action == 'promote-backup':
            package, _ = self.manifest(payload.get('releaseTag'))
            if payload.get('retryOf'):
                from backup_retry import validate_retry
                validate_retry(self, package, payload['retryOf'])
            accepted = package.get('outcomes', {}).get('prod', {}).get('acceptance', {})
            require(accepted.get('status') == 'passed' and self.state['environments'].get('prod', {}).get('maintenance') is False,
                    'Production business acceptance and open admission required before backup')
        if action not in ('build-release','resolve-task','register-targets','restore-metadata'):
            require(not any(e.get('recoveryPending') for e in self.state['environments'].values()),
                    'Recovery must be accepted before another release operation')
        prerequisite = {'prepare-rehearsal':'test','promote-prod':'rehearsal','promote-backup':'prod'}.get(action)
        if prerequisite:
            package, _ = self.manifest(payload.get('releaseTag'))
            require(self.technical_passed(package, prerequisite), 'Passed technical verification required for ' + prerequisite)
        if action == 'prepare-rehearsal':
            require(not any(job.get('action') == 'prepare-rehearsal' and job.get('remoteStatusRequired')
                            and job.get('status') in ('failed','interrupted') and not job.get('resolution')
                            for job in self.state['jobs']), 'Previous rehearsal task requires remote-status reconciliation; do not start a duplicate copy')
        if action not in ('register-targets','restore-metadata'):
            if action in ('prepare-rehearsal','upgrade-rehearsal','accept-rehearsal'):
                require(self.c.get('rehearsal'), 'Independent full-data rehearsal configuration required')
            if action in ('upgrade-rehearsal', 'accept-rehearsal'):
                package, _ = self.manifest(payload.get('releaseTag'))
                require(self.active_rehearsal(package).get('source') == 'prod',
                        'Only production rehearsal may be upgraded or accepted; explicitly clear legacy isolation')
            if action == 'prepare-rehearsal':
                require(payload.get('source') == 'prod', 'Only the production origin is rehearsed')
                rehearsal_profile(self.c, payload.get('source'))
            return super().submit(action, payload, actor)
        if action == 'restore-metadata':
            require(self.c.get('metadataRepair'), 'Explicit proved historical package configuration required')
            require(not self.state['packages'] and not self.state['environments'], 'Metadata restoration is only for the initial unregistered origin')
        with self.lock:
            request_id = payload.get('requestId', '')
            require(isinstance(request_id, str) and re.fullmatch('[a-zA-Z0-9-]{8,80}', request_id), 'requestId required')
            rows = [j for j in self.state['jobs'] if j['requestId'] == request_id]
            if rows:
                require(rows[0]['action'] == action and rows[0]['payload'] == payload, 'Request ID binding mismatch')
                return rows[0]
            require(not any(j['status'] == 'running' or (j['status'] == 'interrupted' and not j.get('resolution'))
                            for j in self.state['jobs']), 'Running/interrupted task blocks registration')
            require(not any(j.get('effectsStarted') and j['status'] == 'failed' and not j.get('resolution')
                            for j in self.state['jobs']), 'Failed remote effects require reconciliation before registration')
            require(not any(e.get('maintenance') or e.get('maintenanceUnknown') for e in self.state['environments'].values()),
                    'Pending maintenance must be reconciled before replacing registered baselines')
            job = dict(id='JOB-'+secrets.token_hex(5), requestId=request_id, action=action, payload=payload,
                       releaseTag=None, actor=actor, status='running', createdAt=stamp(), logs=[])
            self.state['jobs'].insert(0, job)
            self.save()
            self.worker = threading.Thread(target=self.execute, args=(job,), daemon=True)
            self.worker.start()
            return job

    def execute(self, job):
        tracker = None
        context = getattr(self.runtime, 'operation_context', None)
        try:
            if getattr(self, 'track_local_processes', False):
                from backup_retry import bind_attempt_roots
                from local_processes import Tracker
                bind_attempt_roots(self, job)
                tracker = Tracker(self, job)
            if context is not None:
                context.binding = (job, self.save)
            return self.execute_bound(job)
        except Exception as error:
            job.update(status='interrupted' if getattr(error, 'remoteStatusUnknown', False) else 'failed',
                       error=str(error).replace(self.password, '[REDACTED]'), finishedAt=stamp())
            if job['action'] == 'check-prerequisites' and job.get('result'):
                job['result'].update(status='failed', finishedAt=stamp())
            self.log(job, 'Task stopped before dispatch completed: ' + job['error'])
        finally:
            if context is not None:
                context.binding = None
            if tracker:
                tracker.close()

    def execute_bound(self, job):
        if job['action'] == 'publish-test' and job.get('payload', {}).get('retryOf'):
            from backup_retry import validate_test_retry
            package, _ = self.manifest(job['releaseTag'])
            validate_test_retry(self, package, job['payload']['retryOf'])
            package.setdefault('testAttemptHistory', []).append(dict(originalJobId=job['payload']['retryOf'],
                retryJobId=job['id'], outcomes=json.loads(json.dumps(package.get('outcomes', {}).get('test', {})))))
            package.setdefault('outcomes', {})['test'] = {}
        if job['action'] in ('scan-artifacts','clean-artifacts'):
            from artifact_retention import execute
            return execute(self,job)
        if job['action'] == 'check-prerequisites':
            from release_precheck import execute
            return execute(self, job)
        if job['action'] == 'promote-backup' and job.get('payload', {}).get('retryOf'):
            # Preserve each backup attempt without carrying its acceptance or
            # recovery status into the next attempt. Production is untouched.
            package, _ = self.manifest(job['releaseTag'])
            from backup_retry import validate_retry
            validate_retry(self, package, job['payload']['retryOf'])
            package.setdefault('backupAttemptHistory', []).append(dict(
                originalJobId=job['payload']['retryOf'], retryJobId=job['id'],
                outcomes=json.loads(json.dumps(package.get('outcomes', {}).get('backup', {})))))
            package.setdefault('outcomes', {})['backup'] = {}
            self.save()
        from interruption import ACTIONS, execute as execute_interruption
        if job['action'] in ACTIONS:
            return execute_interruption(self, job)
        from intruoyi_recovery import RECOVERY_ACTIONS, execute_recovery
        if job['action'] in RECOVERY_ACTIONS:
            return execute_recovery(self, job)
        if job['action'] not in ('register-targets','restore-metadata'):
            return super().execute(job)
        try:
            if job['action'] == 'restore-metadata':
                restore_metadata(self, job)
                job['status'] = 'succeeded'
                return
            observations = {}
            errors = {}
            for env in ('test','prod','backup'):
                self.step(job, 'observe-'+env)
                value = self.runtime.observe(env)
                try:
                    validate_origin(value)
                    value.update(baselineStatus='registered', observedAt=stamp())
                except ValueError as error:
                    errors[env] = str(error)
                observations[env] = value
            job['result'] = {'targets': {env:{key:value.get(key) for key in
                             ('releaseTag','baselineId','imageIds','backendHealth','frontendHttpStatus','frontendObservationError')}
                             for env,value in observations.items()}, 'registrationErrors':errors}
            self.save()
            require(not errors, 'Origin registration refused: '+json.dumps(errors,ensure_ascii=False))
            # A partial read never replaces one or two baselines and appears complete.
            self.state['environments'].update(observations)
            self.save()
            job['status'] = 'succeeded'
            self.log(job, 'Three real target baselines registered read-only; no deployment or acceptance implied')
        except Exception as exc:
            job.update(status='failed', error=str(exc).replace(self.password, '[REDACTED]'))
            self.log(job, 'Registration stopped: '+job['error'])
        finally:
            job['finishedAt'] = stamp()
            self.save()

    def build(self, job):
        return build(self, job)

    def audit_target(self, env, p, manifest):
        require(env in self.state['environments'], 'Target origin has not been registered')
        return self.runtime.audit(env, self.runtime_manifest(env, manifest))

    def runtime_manifest(self, env, manifest):
        # Baselines follow confirmed deployments, not the first registration forever.
        require(env in self.state['environments'], 'Current registered target origin required')
        return dict(manifest, baselines={env:dict(self.state['environments'][env])})

    def fingerprint(self, env, registered=None):
        return self.runtime.observe(env)['fingerprint']

    def health(self, env, tag):
        return self.runtime.health(env, tag)

    def deploy(self, env, p, manifest, job):
        self.step(job, 'check-migration-plan')
        observation = self.runtime.observe(env)
        observed_environments = dict(self.state['environments'], **{env: observation})
        if env == 'backup':
            observed_environments['prod'] = self.runtime.observe('prod')
            require(observed_environments['prod'].get('images') == {
                role: manifest['images'][role]['id'] for role in ('backend', 'frontend')},
                'Production image identity changed; backup requires the currently accepted original package')
        self.check_deployment_order(job['action'], p, observed_environments)
        audit_ledger(observation, manifest)
        environment = self.active_rehearsal(p)['source'] if env == 'rehearsal' else env
        plan = target_input_plan(manifest['migrations'], observation['ledgerRecords'], environment)
        job['migrationPlan'] = plan
        self.save()
        runtime_manifest = dict(self.runtime_manifest(env, manifest), executionPlans={env:plan})
        if env == 'prod':
            rehearsal = passed_rehearsal(p, 'prod', observation['fingerprint'])
            job['rehearsalId'] = rehearsal['id']
            runtime_manifest['expectedSchemaSha256'] = rehearsal['upgradedSchemaSha256']
        elif env == 'backup':
            runtime_manifest['expectedSchemaSha256'] = backup_rehearsal_schema(p, observation)
        self.step(job, 'prepare-original-package')
        self.runtime.stage(env, p['directory'], manifest)
        def callback(name, effects=False):
            if effects:
                self.state['environments'][env]['maintenanceUnknown'] = True
            self.step(job, name, effects=effects)
        result = self.runtime.deploy(env, runtime_manifest, callback, job['id'])
        require(result.get('releaseTag') == p['releaseTag'], 'Runtime did not confirm deployed version')
        if env == 'rehearsal':
            result['sourceEnvironment'] = self.active_rehearsal(p)['source']
        self.state['environments'][env] = dict(result, observedAt=stamp(), baselineStatus='registered', maintenanceUnknown=False)
        if env == 'rehearsal':
            self.active_rehearsal(p)['upgradedSchemaSha256'] = result['schemaSha256']
        self.save()

    def maintenance(self, env, enabled):
        running = [job for job in self.state['jobs'] if job['status'] == 'running']
        require(len(running) == 1, 'Maintenance change must belong to one persisted workflow task')
        self.step(running[0], 'enable-maintenance' if enabled else 'open-business', effects=True)
        self.state['environments'][env]['maintenanceUnknown'] = True
        self.save()
        try:
            result = self.runtime.maintenance(env, enabled)
            require(result.get('maintenance') is enabled, 'Maintenance transition unconfirmed')
            self.state['environments'][env].update(result, maintenanceUnknown=False)
        finally:
            self.save()

    def prepare(self, p, job):
        source = job['payload'].get('source')
        require(source == 'prod', 'Only the production origin is rehearsed')
        require('rehearsal' not in self.state['environments'], 'Explicitly clear the registered isolated environment before preparing another origin; history is retained')
        self.runtime.targets['rehearsal'] = rehearsal_profile(self.c, source)
        require(source in self.state['environments'], 'Rehearsal origin is not registered')
        job.update(target='rehearsal', sourceEnv=source)
        _, manifest = self.manifest(p['releaseTag'])
        origin = self.runtime.observe(source)
        job['sourceOriginFingerprint'] = origin['fingerprint']
        self.save()
        def callback(name, effects=False):
            self.step(job, name, effects=effects)
            if name == 'stop-source-registered-writers-and-capture-real-full-data-before-side-effects':
                job['remoteStatusRequired'] = True
                job['sourceEnv'] = source
            if name == 'remote-full-data-capture-starting':
                job['remotePhase'] = 'capture-starting'
            elif name == 'remote-full-data-capture-complete':
                job['remotePhase'] = 'capture-complete'
            elif name == 'remote-isolated-restore-starting':
                job['remotePhase'] = 'restore-starting'
            self.save()
        result = self.runtime.prepare_rehearsal(source, manifest, callback, job['id'])
        job['remoteProgress'] = result.pop('remotePreparationProgress')
        job['remotePhase'] = 'completed'
        job.pop('remoteStatusError',None)
        self.register_prepared_rehearsal(p, job, source, origin, result)

    def register_prepared_rehearsal(self, p, job, source, origin, result):
        require(result.get('originFingerprint') == origin['fingerprint'] and result.get('verifiedOrigin') is True,
                'Isolated source provenance has not been verified')
        for key in ('images', 'schemaSha256', 'ledgerSha256'):
            require(result.get(key) == origin.get(key), 'Isolated origin differs from actual source: '+key)
        require(self.runtime.observe(source)['fingerprint'] == origin['fingerprint'], 'Source changed while preparing rehearsal')
        record = dict(id=job['id'], source=source, originFingerprint=origin['fingerprint'], originReleaseTag=origin['releaseTag'],
                      originBaselineId=origin.get('baselineId'),
                      originState={key:origin[key] for key in ('releaseTag', 'images', 'schemaSha256', 'ledgerSha256')},
                      packageSha256=p['packageSha256'], status='ready', jobId=job['id'], createdAt=stamp())
        p.setdefault('rehearsals', []).append(record)
        p['activeRehearsal'] = record['id']
        p.setdefault('outcomes', {})['rehearsal'] = {}
        self.state['environments']['rehearsal'] = dict(result, sourceEnvironment=source)
        self.save()

    def resume_rehearsal_preparation(self, job, selected):
        root_id = selected.get('originalPreparationJobId') if selected['action'] == 'resolve-task' else selected['id']
        original = next((item for item in self.state['jobs'] if item['id'] == root_id), None)
        phase = original.get('continuationRemotePhase', original.get('remotePhase')) if original else None
        require(original and original['action'] == 'prepare-rehearsal' and original.get('target') == 'rehearsal'
                and original.get('sourceEnv') == 'prod' and original.get('effectsStarted')
                and original.get('remoteStatusRequired') and phase in ('capture-complete', 'restore-starting')
                and original['status'] in ('failed', 'interrupted') and not original.get('resolution'),
                'Unresolved production-origin preparation with a completed capture or interrupted restore tail required')
        require(job['releaseTag'] == selected['releaseTag'] == original['releaseTag'], 'Preparation continuation must use the original immutable package')
        require(not any(item['status'] == 'running' and item['id'] != job['id'] for item in self.state['jobs']),
                'Another task is still running')
        if selected is not original:
            require(selected.get('target') == 'rehearsal' and selected.get('sourceEnv') == 'prod'
                    and selected.get('payload', {}).get('decision') == 'retry', 'Only a linked preparation continuation can be retried')
        job.update(target='rehearsal', sourceEnv='prod', originalPreparationJobId=original['id'], previousResolutionJobId=selected['id'])
        self.save()
        self.step(job, 'verify-original-rehearsal-preparation-evidence')
        package, manifest = self.package(original['releaseTag'])
        require(package['stage'] in ('tested', 'rehearsal-passed') and not package.get('baseline') and not package.get('abandoned'),
                'Candidate stage changed after failed preparation')
        require(self.technical_passed(package, 'test'), 'Original candidate must retain passed test technical evidence')
        require('rehearsal' not in self.state['environments'] and not package.get('activeRehearsal'),
                'An isolated environment is already registered; original preparation cannot overwrite it')
        outcome = package.get('outcomes', {}).get('rehearsal', {}).get('preparation', {})
        require(outcome.get('jobId') == original['id'] and outcome.get('status') in ('failed', 'interrupted'),
                'Original failed preparation must own the candidate outcome')
        self.runtime.targets['rehearsal'] = rehearsal_profile(self.c, 'prod')
        origin = validate_origin(self.runtime.observe('prod'))
        require(origin['fingerprint'] == original.get('sourceOriginFingerprint'), 'Original production source changed since capture')
        require(origin.get('maintenance') is False and origin.get('readOnly') == dict(read_only=False, super_read_only=False),
                'Original production source must be healthy and open before resuming isolation')
        audit_ledger(origin, manifest)
        if phase == 'restore-starting':
            entry = self.runtime.call('rehearsal', 'rehearsal-restore-entry-state',
                                      releaseTag=manifest['releaseTag'], jobId=original['id'])
            require(entry.get('state') in ('not-started','started') and entry.get('mutations') is False,
                    'Explicit read-only restore entry evidence required')
            job['restoreEntryEvidence'] = entry
            self.save()
            if entry['state'] == 'not-started':
                phase = 'capture-complete'
                self.log(job, 'Original restore failed before creating resources; continue verified capture restoration.')
        def continued_step(name, effects=False):
            if name == 'continue-original-capture-restore':
                original['continuationRemotePhase'] = 'restore-starting'
            self.step(job, name, effects=effects)
        resume = self.runtime.resume_rehearsal_transfer if phase == 'capture-complete' else self.runtime.resume_rehearsal_tail
        result = resume('prod', manifest, original['id'], job['id'],
                    package['packageSha256'], package['manifestSha256'], original['sourceOriginFingerprint'],
                    continued_step)
        attempts = [item for item in self.state['jobs'] if item.get('originalPreparationJobId') == original['id']
                    and item.get('releaseTag') == original['releaseTag'] and item.get('target') == 'rehearsal'
                    and item.get('sourceEnv') == 'prod' and item['action'] == 'resolve-task'
                    and item.get('payload', {}).get('decision') == 'retry']
        receipt = result.get('resumeReceipt', {})
        require(receipt.get('status') == 'completed' and receipt.get('phase') == 'complete'
                and receipt.get('originalJobId') == original['id'] and receipt.get('source') == 'prod'
                and receipt.get('releaseTag') == package['releaseTag']
                and receipt.get('packageSha256') == package['packageSha256']
                and receipt.get('manifestSha256') == package['manifestSha256']
                and receipt.get('retryJobId') in {item['id'] for item in attempts},
                'Bound completed rehearsal startup-tail receipt required')
        validate_origin(result)
        require(result['releaseTag'] == origin['releaseTag'], 'Recovered isolation must run the original source version')
        audit_ledger(result, manifest)
        progress = result.get('remotePreparationProgress', {})
        expected_worker = original['id'] if phase == 'capture-complete' else receipt['retryJobId']
        if phase == 'capture-complete':
            require(receipt.get('kind') == 'captured-transfer' and re.fullmatch('[a-f0-9]{64}', receipt.get('captureSha256', '')),
                    'Completed original capture transfer receipt required')
        require(progress.get('status') == 'succeeded' and progress.get('phase') == 'completed'
                and progress.get('jobId') == expected_worker, 'Completed preparation continuation worker evidence required')
        job.update(remoteProgress=result.pop('remotePreparationProgress'), remotePhase='completed')
        self.register_prepared_rehearsal(package, job, 'prod', origin, result)
        self.active_rehearsal(package)['originalPreparationJobId'] = original['id']
        package['stage'] = 'rehearsal-ready'
        for prior in [original, *attempts]:
            if prior['id'] != job['id'] and prior['status'] in ('failed', 'interrupted') and not prior.get('resolution'):
                prior['resolution'] = dict(decision='retry', note=job['payload']['note'], actor=job['actor'], time=stamp(),
                                           jobId=job['id'], originalPreparationJobId=original['id'], resumeReceipt=receipt)
        job['result'] = dict(originalPreparationJobId=original['id'], stage='rehearsal-ready', resumeReceipt=receipt)
        self.outcome(package, 'rehearsal', 'preparation', 'succeeded', job, originalPreparationJobId=original['id'])
        self.log(job, ('Original captured artifacts transferred and baseline restored; production was not recaptured.'
                      if phase == 'capture-complete' else
                      'Retained original isolation startup tail verified; no capture, import or migration replayed.')
                     + ' Original failure preserved; candidate upgrade remains a separate action.')

    def reset_rehearsal(self, job):
        self.runtime.reset_rehearsal(lambda name, effects=False:self.step(job,name,effects=effects))
        self.state['environments'].pop('rehearsal', None)
        self.save()

    def resume_test_deployment(self, job, selected):
        """Explicit same-package tail only; never invoke the deployment/SQL path."""
        root_id = selected.get('originalDeploymentJobId') if selected['action'] == 'resolve-task' else selected['id']
        original = next((j for j in self.state['jobs'] if j['id'] == root_id), None)
        require(original and original['action'] == 'publish-test' and original.get('target') == 'test'
                and original['status'] in ('failed', 'interrupted') and original.get('effectsStarted')
                and not original.get('resolution'), 'Unresolved original test deployment required for tail continuation')
        require(selected['releaseTag'] == original['releaseTag'] == job['releaseTag'], 'Continuation must use the original immutable package')
        require(not any(j['status'] == 'running' and j['id'] != job['id'] for j in self.state['jobs']),
                'Another task is still running')
        if selected is not original:
            require(selected.get('target') == 'test' and selected.get('payload', {}).get('decision') == 'retry',
                    'Only a linked failed test continuation can be retried')
        job.update(target='test', originalDeploymentJobId=original['id'], previousResolutionJobId=selected['id'])
        self.save()
        self.step(job, 'verify-original-test-package-and-migration-evidence')
        package, manifest = self.package(original['releaseTag'])
        require(package['stage'] == 'built' and not package.get('baseline') and not package.get('abandoned'),
                'Test candidate stage changed after the failed deployment')
        outcome = package.get('outcomes', {}).get('test', {}).get('deployment', {})
        require(outcome.get('jobId') == original['id'] and outcome.get('status') in ('failed', 'interrupted'),
                'Original failed deployment no longer owns this candidate')
        original_plan = original.get('migrationPlan', {})
        require(original_plan.get('status') == 'passed' and original_plan.get('targetEnvironment') == 'test'
                and isinstance(original_plan.get('items'), list), 'Original passed test migration plan required')
        sources = {m['migrationId']: m for m in manifest['migrations']}
        planned = original_plan['items']
        require(len({m.get('migrationId') for m in planned}) == len(planned), 'Original migration plan contains duplicate identities')
        applied = [m for m in planned if m.get('action') == 'APPLY']
        require(applied and all(m.get('migrationId') in sources and m.get('sha256') == sources[m['migrationId']]['sha256']
                                for m in applied), 'Original APPLY identities differ from the immutable package')
        origin_records = original.get('originState', {}).get('ledgerRecords')
        require(isinstance(origin_records, list) and
                original_plan == target_input_plan(manifest['migrations'], origin_records, 'test'),
                'Original full migration plan differs from its immutable package and origin ledger')
        observation = self.runtime.observe('test')
        audit = audit_ledger(observation, manifest)
        require(all(m['migrationId'] in audit['applied'] for m in applied), 'Original test migrations are not all APPLIED')
        require(observation.get('images') == {role: manifest['images'][role]['id'] for role in ('backend', 'frontend')},
                'Both installed test images must be the original candidate')
        plan = target_input_plan(manifest['migrations'], observation['ledgerRecords'], 'test')
        require(plan['status'] == 'passed' and not any(m['action'] == 'APPLY' for m in plan['items']),
                'Continuation requires zero pending migrations')
        job['migrationPlan'] = plan
        self.save()
        require(original.get('originState'), 'Original deployment origin evidence required')
        runtime_manifest = dict(manifest, baselines={'test': original['originState']}, executionPlans={'test': plan})
        def callback(name, effects=False):
            if effects:
                self.state['environments']['test']['maintenanceUnknown'] = True
            self.step(job, name, effects=effects)
        result = self.runtime.resume_test_deployment_tail('test', runtime_manifest, planned, original['id'], job['id'],
                                                         package['packageSha256'], package['manifestSha256'], callback)
        receipt = result.get('resumeReceipt', {})
        attempts = [j for j in self.state['jobs'] if j.get('originalDeploymentJobId') == original['id']
                    and j.get('releaseTag') == original['releaseTag'] and j.get('target') == 'test'
                    and j['action'] == 'resolve-task' and j.get('payload', {}).get('decision') == 'retry']
        require(receipt.get('status') == 'completed' and receipt.get('phase') == 'complete'
                and receipt.get('originalJobId') == original['id'] and receipt.get('releaseTag') == package['releaseTag']
                and receipt.get('packageIdentity') == package_identity(manifest)
                and receipt.get('packageSha256') == package['packageSha256']
                and receipt.get('manifestSha256') == package['manifestSha256']
                and receipt.get('completedByJobId') in {j['id'] for j in attempts},
                'Same-package completed test continuation receipt required')
        validate_origin(result)
        require(result['releaseTag'] == package['releaseTag'] and result.get('images') == observation['images']
                and result.get('maintenance') is False
                and result.get('readOnly') == dict(read_only=False, super_read_only=False),
                'Test continuation did not confirm the candidate open for functional verification')
        require(result['schemaSha256'] == observation['schemaSha256'] and result['ledgerSha256'] == observation['ledgerSha256'],
                'Schema or migration history changed during deployment tail continuation')
        audit_ledger(result, manifest)
        require(not any(item['action'] == 'APPLY' for item in
                        target_input_plan(manifest['migrations'], result['ledgerRecords'], 'test')['items']),
                'Completed continuation still has pending migrations')
        self.state['environments']['test'] = dict(result, observedAt=stamp(), baselineStatus='registered', maintenanceUnknown=False)
        package['stage'] = 'test-deployed'
        # Resolve only this explicit continuation family; the original failure is retained.
        for prior in [original, *attempts]:
            if prior['id'] != job['id'] and prior['status'] in ('failed', 'interrupted') and not prior.get('resolution'):
                prior['resolution'] = dict(decision='retry', note=job['payload']['note'], actor=job['actor'],
                                           time=stamp(), jobId=job['id'], originalDeploymentJobId=original['id'],
                                           resumeReceipt=receipt)
        job['result'] = dict(originalDeploymentJobId=original['id'], stage='test-deployed', resumeReceipt=receipt)
        self.outcome(package, 'test', 'deployment', 'succeeded', job, originalDeploymentJobId=original['id'])
        self.verify_technical('test', package, manifest, job)
        job['result']['stage'] = package['stage']
        self.log(job, 'Same immutable test package deployment tail and technical verification completed; original failure retained, no migrations or backup rerun.')

    def resolve_task(self, job):
        original = next((j for j in self.state['jobs'] if j['id'] == job['payload'].get('jobId')), None)
        require(original and original['status'] in ('failed','interrupted') and not original.get('resolution'), 'Original unresolved task required')
        require(not original.get('technicalVerification') and original.get('action') != 'reject-acceptance',
                'Installed deployment or historical business rejection requires a new technical verification action, not restoration or a fabricated resolution')
        if job['payload']['decision'] == 'retry':
            if original['action'] == 'build-release' or original.get('originalBuildJobId'):
                from nas_package_retry import resume
                return resume(self, job, original)
            if original['action'] == 'prepare-rehearsal' or original.get('originalPreparationJobId'):
                return self.resume_rehearsal_preparation(job, original)
            return self.resume_test_deployment(job, original)
        if original['action'] == 'resolve-task' and original.get('originalPreparationJobId'):
            selected = original
            original = next((item for item in self.state['jobs'] if item['id'] == selected['originalPreparationJobId']), None)
            require(original and original['action'] == 'prepare-rehearsal' and original.get('sourceEnv') == 'prod'
                    and original['status'] in ('failed', 'interrupted') and not original.get('resolution')
                    and original['releaseTag'] == selected['releaseTag'] == job['releaseTag'],
                    'Original unresolved preparation required before abandoning its continuation')
        if original['action'] == 'resolve-task' and original.get('originalDeploymentJobId'):
            selected = original
            original = next((j for j in self.state['jobs'] if j['id'] == selected['originalDeploymentJobId']), None)
            require(original and original['action'] == 'publish-test' and original.get('target') == 'test'
                    and original['status'] in ('failed', 'interrupted') and not original.get('resolution')
                    and original['releaseTag'] == selected['releaseTag'] == job['releaseTag'],
                    'Original unresolved test deployment required before abandoning its continuation')
        if original['action'] in ('mark-tested', 'function-passed', 'accept-rehearsal'):
            require(job['payload']['decision'] == 'abandon', 'Failed read-only acceptance must be explicitly abandoned before a fresh acceptance')
            require(not original.get('effectsStarted'), 'Acceptance has remote effects; explicit operational reconciliation required')
            package, manifest = self.manifest(original['releaseTag'])
            target = original.get('target')
            require(target in ('test', 'rehearsal'), 'Original acceptance target is missing or invalid; historical action names cannot infer it')
            require(package['stage'] == ('test-deployed' if target == 'test' else 'rehearsal-upgraded'),
                    'Candidate stage changed; original acceptance cannot be abandoned as a pending check')
            if target == 'rehearsal':
                record = self.active_rehearsal(package)
                require(record.get('status') == 'upgraded' and record.get('packageSha256') == package['packageSha256']
                        and record.get('acceptance', {}).get('jobId') == original['id'],
                        'Original acceptance must own the pending isolated upgrade')
            self.health(target, package['releaseTag'])
            self.audit_target(target, package, manifest)
            original['resolution'] = dict(decision='abandon', note=job['payload']['note'], actor=job['actor'],
                                          time=stamp(), jobId=job['id'])
            self.save()
            self.log(job, 'Current candidate health and registered origin verified; original failed acceptance retained. Fresh explicit acceptance is still required.')
            return
        if original['action'] in ('accept-prod', 'accept-backup'):
            raise ValueError('Business opening acceptance requires explicit operational reconciliation; no automatic restoration, reopening or acceptance is performed')
        if original['action'] == 'upgrade-rehearsal' and original.get('target') == 'rehearsal':
            require(job['payload']['decision'] == 'abandon', 'Failed isolated upgrades can only be explicitly discarded')
            package = next((p for p in self.state['packages'] if p['releaseTag'] == original['releaseTag']), None)
            require(package is not None, 'Original isolated upgrade package required')
            record = self.active_rehearsal(package)
            require(record.get('packageSha256') == package['packageSha256'] and
                    record.get('deployment', {}).get('jobId') == original['id'],
                    'Failed upgrade must own the current isolated environment')
            source = record['source']
            require(source in ('test', 'prod', 'backup') and
                    self.state['environments'].get('rehearsal', {}).get('sourceEnvironment') == source,
                    'Registered isolation source differs from failed upgrade evidence')
            status = self.runtime.call('rehearsal', 'verify-deployment-stopped',
                                       releaseTag=original['releaseTag'], jobId=original['id'])
            require(status.get('stopped') is True, 'Remote isolated upgrade is not confirmed stopped')
            observation = validate_origin(self.runtime.observe(source))
            require(observation['fingerprint'] == record['originFingerprint'], 'Original source changed since isolation capture')
            require(observation.get('maintenance') is False and
                    observation.get('readOnly') == dict(read_only=False, super_read_only=False),
                    'Original source business and write access must be healthy before discarding isolation')
            self.runtime.reset_rehearsal(lambda name, effects=False:self.step(job, name, effects=effects))
            self.state['environments'].pop('rehearsal', None)
            record.update(status='abandoned', abandonedAt=stamp(), abandonedBy=job['id'])
            package.pop('activeRehearsal', None)
            if source == 'prod' and package['stage'] in ('rehearsal-ready', 'rehearsal-upgraded'):
                package['stage'] = 'tested'
            original['resolution'] = dict(decision='abandon', note=job['payload']['note'], actor=job['actor'],
                                          time=stamp(), jobId=job['id'], remoteEvidence=status,
                                          sourceOriginFingerprint=observation['fingerprint'])
            self.save()
            self.log(job, 'Confirmed isolated worker stopped and unchanged healthy source; discarded labelled isolation only. Original failed upgrade retained.')
            return
        # Prerequisite failures precede stage creation/capture and use the
        # pre-effect abandon path below; either persisted marker keeps cleanup gated.
        if original['action'] == 'prepare-rehearsal' and (original.get('effectsStarted') or original.get('remoteStatusRequired')):
            require(job['payload']['decision']=='abandon','Failed preparation can only be explicitly discarded')
            source=original['sourceEnv']
            self.runtime.targets['rehearsal']=rehearsal_profile(self.c,source)
            status=self.runtime.call(source,'rehearsal-verify-stopped',releaseTag=original['releaseTag'],
                                     expectedOriginFingerprint=original.get('sourceOriginFingerprint'))
            if self.runtime.profile(source)['host'] != self.runtime.profile('rehearsal')['host']:
                self.runtime.call('rehearsal','rehearsal-verify-stopped',checkProcessesOnly=True)
            observation=validate_origin(self.runtime.observe(source))
            require(observation['fingerprint']==status['originFingerprint'],'Source origin differs from completed capture')
            require(not observation['maintenance'],'Source business must be restored before discarding isolation')
            self.runtime.reset_rehearsal(lambda name,effects=False:self.step(job,name,effects=effects))
            self.state['environments'].pop('rehearsal',None)
            original['resolution']=dict(decision='abandon',note=job['payload']['note'],actor=job['actor'],
                time=stamp(),jobId=job['id'],remoteEvidence=status)
            for attempt in self.state['jobs']:
                if (attempt['action'] == 'resolve-task' and attempt.get('originalPreparationJobId') == original['id']
                        and attempt.get('releaseTag') == original['releaseTag'] and attempt.get('target') == 'rehearsal'
                        and attempt['status'] in ('failed', 'interrupted') and not attempt.get('resolution')):
                    attempt['resolution'] = dict(original['resolution'], originalPreparationJobId=original['id'])
            self.log(job,'Remote terminal phase and original source health verified; discarded only labelled isolated resources. Original failure retained.')
            return
        if original['action'] == 'restore-metadata':
            require(job['payload']['decision'] == 'abandon', 'Metadata reconciliation only closes the failed attempt; it does not declare repair success')
            config = self.c['metadataRepair']
            manifest, images, info = metadata_reference(config)
            evidence = {}
            for env in ('test','prod','backup'):
                evidence[env] = metadata_remote(self.runtime,env,config['directories'][env],manifest,images,info)
                observed = self.runtime.observe(env)
                for key, value in original.get('originEvidence',{}).get(env,{}).items():
                    require(observed[key] == value, env+': metadata origin changed: '+key)
            original['resolution'] = dict(decision='abandon',note=job['payload']['note'],actor=job['actor'],
                                          time=stamp(),jobId=job['id'],metadataEvidence=evidence)
            self.log(job,'Historical metadata locations reconciled with original images/package; original failure retained. No SQL or release acceptance performed.')
            return
        if original.get('effectsStarted'):
            require(job['payload']['decision'] == 'abandon', 'Restored deployments can only be explicitly abandoned')
            result = self.runtime.call(original['target'], 'verify-restoration', releaseTag=original['releaseTag'],
                                       jobId=original['id'], originFingerprint=original.get('originFingerprint'))
            observation = result['observation']
            validate_restored_origin(original, observation)
            self.state['environments'][original['target']] = dict(observation, baselineStatus='registered', maintenanceUnknown=False)
            original['resolution'] = dict(decision='abandon', note=job['payload']['note'], actor=job['actor'],
                                          time=stamp(), jobId=job['id'], recoveryEvidence=result['recoveryEvidence'])
            if original['action'] == 'publish-test' and original['target'] == 'test':
                for attempt in self.state['jobs']:
                    if (attempt['action'] == 'resolve-task' and attempt.get('originalDeploymentJobId') == original['id']
                            and attempt.get('releaseTag') == original['releaseTag'] and attempt.get('target') == 'test'
                            and attempt['status'] in ('failed', 'interrupted') and not attempt.get('resolution')):
                        attempt['resolution'] = dict(original['resolution'], originalDeploymentJobId=original['id'])
            self.log(job, 'Explicit recovery evidence and actual original origin verified; failed deployment retained, no SQL replayed or acceptance granted')
            return
        require(job['payload']['decision'] == 'abandon', 'Only a confirmed pre-effect task may be abandoned here')
        if original.get('target') and original.get('originFingerprint'):
            require(self.fingerprint(original['target']) == original['originFingerprint'], 'Original remote origin changed')
        original['resolution'] = dict(decision='abandon', note=job['payload']['note'], actor=job['actor'], time=stamp(), jobId=job['id'])
        self.log(job, 'Original pre-effect task retained and abandoned; no SQL replayed')


from frontend_patch import FrontendPatchMixin

class IntRuoyiExecutor(FrontendPatchMixin, RollbackMixin, _IntRuoyiExecutor):
    """Run rollback hooks before the concrete release adapter."""
    pass


if __name__ == '__main__':
    main(IntRuoyiExecutor)
