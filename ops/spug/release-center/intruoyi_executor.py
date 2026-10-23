"""IntRuoyi's remote adapter for the existing persistent release workflow."""
import json
from pathlib import Path
import re
import secrets
import threading

from executor import Executor, main, require, stamp
from intruoyi_build import build, target_input_plan
from intruoyi_runtime import Runtime, audit_ledger, rehearsal_profile
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


class IntRuoyiExecutor(Executor):
    def __init__(self, config):
        require(config.get('applicationId') == 'intruoyi', 'IntRuoyi application identity required')
        require(config.get('runtimeKind') == 'remote-intruoyi', 'Explicit remote IntRuoyi runtime required')
        require(set(config.get('targets', {})) >= {'test','prod','backup'}, 'All three real targets required')
        require(config.get('stateDir') and config.get('buildWorktreeRoot'), 'Dedicated state and worktree paths required')
        require(config.get('mysqlImage') == 'mysql:8.0.39', 'Pinned MySQL runtime required')
        super().__init__(config)
        self.runtime = Runtime(config)
        if 'rehearsal' in self.state['environments']:
            source = self.state['environments']['rehearsal'].get('sourceEnvironment')
            self.runtime.targets['rehearsal'] = rehearsal_profile(config, source)

    def snapshot(self):
        with self.lock:
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
                                                 buildRelease=True, prepareRehearsal=configured))
            if not configured:
                application['capabilityReasons'] = dict(prepareRehearsal='尚未配置独立数据副本、运行资源与外部接口隔离，不能准备演练。')
            if self.c.get('nasPath'):
                application['nasPath'] = self.c['nasPath']
            return json.loads(json.dumps(dict(self.state, application=application)))

    def submit(self, action, payload, actor):
        require(payload.get('applicationId') == self.c['applicationId'], 'Request application identity mismatch')
        require(action not in ('initialize-baseline','audit-baseline'), 'Remote databases must never use demo initialization')
        require(action != 'function-passed', 'Use mark-tested to accept the actual deployed test candidate')
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

    def reset_rehearsal(self, job):
        self.runtime.reset_rehearsal(lambda name, effects=False:self.step(job,name,effects=effects))
        self.state['environments'].pop('rehearsal', None)
        self.save()

    def resolve_task(self, job):
        original = next((j for j in self.state['jobs'] if j['id'] == job['payload'].get('jobId')), None)
        require(original and original['status'] in ('failed','interrupted') and not original.get('resolution'), 'Original unresolved task required')
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
        if original['action'] == 'prepare-rehearsal':
            require(job['payload']['decision']=='abandon','Failed preparation can only be explicitly discarded')
            source=original['sourceEnv']
            self.runtime.targets['rehearsal']=rehearsal_profile(self.c,source)
            status=self.runtime.call(source,'rehearsal-verify-stopped',releaseTag=original['releaseTag'])
            if self.runtime.profile(source)['host'] != self.runtime.profile('rehearsal')['host']:
                self.runtime.call('rehearsal','rehearsal-verify-stopped',checkProcessesOnly=True)
            observation=validate_origin(self.runtime.observe(source))
            require(observation['fingerprint']==status['originFingerprint'],'Source origin differs from completed capture')
            require(not observation['maintenance'],'Source business must be restored before discarding isolation')
            self.runtime.reset_rehearsal(lambda name,effects=False:self.step(job,name,effects=effects))
            self.state['environments'].pop('rehearsal',None)
            original['resolution']=dict(decision='abandon',note=job['payload']['note'],actor=job['actor'],
                time=stamp(),jobId=job['id'],remoteEvidence=status)
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
            self.log(job, 'Explicit recovery evidence and actual original origin verified; failed deployment retained, no SQL replayed or acceptance granted')
            return
        require(job['payload']['decision'] == 'abandon', 'Only a confirmed pre-effect task may be abandoned here')
        if original.get('target') and original.get('originFingerprint'):
            require(self.fingerprint(original['target']) == original['originFingerprint'], 'Original remote origin changed')
        original['resolution'] = dict(decision='abandon', note=job['payload']['note'], actor=job['actor'], time=stamp(), jobId=job['id'])
        self.log(job, 'Original pre-effect task retained and abandoned; no SQL replayed')


if __name__ == '__main__':
    main(IntRuoyiExecutor)
