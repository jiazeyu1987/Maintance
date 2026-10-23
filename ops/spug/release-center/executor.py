"""Configuration-driven isolated release executor. No production IntRuoyi targets."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tarfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from state_store import StateStore, process_lock


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def stamp():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d-%H-%M-%S')


class Executor:
    def __init__(self, config):
        self.c = config
        # All demo health URLs are fixed host loopback ports. Never send them
        # through an environment/system proxy or the cached global HTTP opener.
        self.local_http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.root = Path(config['stateDir']).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.process_lock = process_lock(self.root)
        self.lock = threading.RLock()
        self.worker = None
        try:
            self.store = StateStore(self.root)
            self.state = self.store.load()
        except BaseException:
            self.process_lock.close()
            raise
        for job in self.state['jobs']:
            if job['status'] == 'running':
                job.update(status='interrupted', finishedAt=stamp(), error='Service restarted; effects require investigation. Automatic retry refused.')
                for package in self.state['packages']:
                    outcomes_to_reconcile = list(package.get('outcomes', {}).values()) + package.get('rehearsals', [])
                    for outcomes in outcomes_to_reconcile:
                        for outcome in outcomes.values():
                            if isinstance(outcome, dict) and outcome.get('jobId') == job['id'] and outcome.get('status') == 'running':
                                outcome.update(status='interrupted', error=job['error'])
        self.save()
        require(re.fullmatch(r'[a-z][a-z0-9-]{2,35}', self.c['applicationId']), 'Invalid applicationId')
        require(self.c['mysqlImage'] == 'mysql:8.0.39', 'MySQL must be pinned to 8.0.39')
        self.secret_file = self.root / 'db-password.txt'
        if not self.secret_file.exists():
            self.secret_file.write_text(secrets.token_hex(24), 'utf-8')
        self.password = self.secret_file.read_text('utf-8').strip()

    def save(self):
        with self.lock:
            self.ensure_persistence()
            try:
                self.store.save(self.state)
            except Exception:
                self.persistence_failed = True
                raise

    def ensure_persistence(self):
        require(not getattr(self, 'persistence_failed', False),
                'State persistence failed; service restart and investigation required, in-memory status is not authoritative')

    def run(self, args, data=None, cwd=None, timeout=900, env=None):
        result = subprocess.run(args, input=data, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if result.returncode:
            # Commands can contain credentials via environment; never echo argv or raw stderr.
            error = (result.stdout + result.stderr).decode('utf-8', errors='replace').replace(self.password, '[REDACTED]')
            raise RuntimeError(f'{Path(args[0]).name} {args[1] if len(args)>1 else ""} failed ({result.returncode}): {error[-2500:]}')
        return result.stdout

    def log(self, job, message):
        with self.lock:
            job['logs'].append(dict(time=stamp(), message=message))
            self.save()

    def step(self, job, name, effects=False):
        job['currentStep'] = name
        if effects:
            job['effectsStarted'] = True
        self.log(job, 'Step: ' + name)

    def active_rehearsal(self, p):
        rows = [r for r in p.get('rehearsals', []) if r['id'] == p.get('activeRehearsal')]
        require(len(rows) == 1, 'Active rehearsal record missing')
        return rows[0]

    def verified_origin(self, p, fingerprint):
        return any(r['status'] == 'passed' and r['originFingerprint'] == fingerprint
                   and r['packageSha256'] == p['packageSha256'] for r in p.get('rehearsals', []))

    def outcome(self, p, env, kind, status, job, **extra):
        value = dict(status=status, jobId=job['id'], step=job.get('currentStep'), time=stamp(), **extra)
        p.setdefault('outcomes', {}).setdefault(env, {})[kind] = value
        if env == 'rehearsal' and p.get('activeRehearsal'):
            record = self.active_rehearsal(p)
            if job['action'] != 'prepare-rehearsal' or record['jobId'] == job['id']:
                record[kind] = value
        self.save()

    def technical_verification_enabled(self):
        return False

    def failed_task_blocks(self, failed, action, payload, package):
        return failed['status'] == 'failed' and not failed.get('resolution') and failed.get('releaseTag') == package['releaseTag']

    def snapshot(self):
        with self.lock:
            self.ensure_persistence()
            return json.loads(json.dumps(dict(self.state, application=dict(id=self.c['applicationId'], name=self.c['displayName'], repo=self.c['repo'], ports=self.c['ports']))))

    def commits(self):
        raw = self.run(['git', '-C', self.c['repo'], 'log', '-20', '--format=%H%x09%s']).decode('utf-8')
        return [dict(commit=line.split('\t', 1)[0], message=line.split('\t', 1)[1]) for line in raw.splitlines()]

    def manifest(self, tag):
        rows = [p for p in self.state['packages'] if p['releaseTag'] == tag]
        require(len(rows) == 1, 'Package not found')
        p = rows[0]
        folder = Path(p['directory'])
        require(digest(folder / 'manifest.json') == p['manifestSha256'], 'Manifest checksum mismatch')
        manifest = json.loads((folder / 'manifest.json').read_text('utf-8'))
        return p, manifest

    def package(self, tag):
        p, manifest = self.manifest(tag)
        folder = Path(p['directory'])
        require(digest(folder / 'release.tar') == p['packageSha256'], 'Release archive checksum mismatch')
        for item in manifest['files']:
            require(digest(folder / item['name']) == item['sha256'], 'Package artifact checksum mismatch: ' + item['name'])
        return p, manifest

    def submit(self, action, payload, actor):
        self.ensure_persistence()
        with self.lock:
            remote_runtime = self.c.get('runtimeKind') == 'remote-intruoyi'
            allowed = {'build-release', 'initialize-baseline', 'publish-test', 'function-passed', 'prepare-rehearsal', 'upgrade-rehearsal', 'mark-tested', 'promote-prod', 'accept-prod', 'promote-backup', 'accept-backup', 'reject-acceptance', 'reset-rehearsal', 'audit-baseline', 'resolve-task'}
            if remote_runtime:
                allowed.add('accept-rehearsal')
            require(action in allowed, 'Unknown action')
            # Persist operation id to make a repeated browser request return its original job.
            request_id = payload.get('requestId')
            require(isinstance(request_id, str) and re.fullmatch('[a-zA-Z0-9-]{8,80}', request_id), 'requestId required')
            existing = [j for j in self.state['jobs'] if j['requestId'] == request_id]
            if existing:
                require(existing[0]['action'] == action and existing[0]['payload'] == payload, 'Request ID binding mismatch')
                return existing[0]
            require(not any(j['status'] == 'running' or (j['status'] == 'interrupted' and not j.get('resolution')) for j in self.state['jobs']) or
                    (action == 'resolve-task' and not any(j['status'] == 'running' for j in self.state['jobs'])), 'Running/interrupted task blocks execution; inspect original task')
            tag = payload.get('releaseTag')
            if action not in ('build-release', 'resolve-task'):
                # Full archive validation runs in execute before any side effect.
                # Do not hold the HTTP/state lock while hashing gigabyte images.
                p, _ = self.manifest(tag)
                require(action in ('reset-rehearsal', 'audit-baseline', 'prepare-rehearsal') or not any(self.failed_task_blocks(j, action, payload, p) for j in self.state['jobs']), 'Failed task requires investigation; blind retry refused')
                gates = {'initialize-baseline': None, 'publish-test': 'built', 'function-passed': 'test-deployed', 'prepare-rehearsal': None, 'upgrade-rehearsal': None, 'mark-tested': None, 'promote-prod': 'tested', 'accept-prod': 'prod-deployed', 'promote-backup': 'prod-accepted', 'accept-backup': 'backup-deployed', 'reject-acceptance': None, 'reset-rehearsal': None, 'audit-baseline': None}
                if remote_runtime:
                    gates.update({'mark-tested': 'test-deployed', 'accept-rehearsal': 'rehearsal-upgraded', 'promote-prod': 'rehearsal-passed'})
                technical_actions = {'mark-tested':('test-deployed','tested'), 'accept-rehearsal':('rehearsal-upgraded','rehearsal-passed'),
                                     'accept-prod':('prod-deployed','prod-accepted'), 'accept-backup':('backup-deployed','completed')}
                if self.technical_verification_enabled() and action in technical_actions:
                    require(p['stage'] in technical_actions[action], 'Workflow prerequisite not met')
                else:
                    require(gates[action] is None or p['stage'] == gates[action], 'Workflow prerequisite not met')
                require(not p['baseline'] or action in ('initialize-baseline', 'reset-rehearsal', 'audit-baseline'), 'Initial baseline cannot be promoted as a candidate')
                require(not p.get('abandoned') or action in ('audit-baseline', 'reset-rehearsal'), 'Candidate was explicitly abandoned; build a new package')
                if action == 'prepare-rehearsal':
                    source = payload.get('source', 'prod')
                    require(source in ('prod', 'backup') or (source == 'test' and self.c.get('runtimeKind') == 'remote-intruoyi'), 'Invalid rehearsal source')
                    stages = {'test': ('built',), 'prod': ('function-passed', 'tested'), 'backup': ('prod-accepted',)}
                    if remote_runtime:
                        require(source == 'prod', 'Only production baseline rehearsal is part of this workflow')
                        stages = {'prod': ('tested', 'rehearsal-passed')}
                    require(p['stage'] in stages[source], 'Source rehearsal prerequisite not met')
                    require(not p.get('activeRehearsal') or self.active_rehearsal(p)['status'] == 'passed', 'Finish or explicitly reset the pending rehearsal first')
                if action in ('upgrade-rehearsal', 'accept-rehearsal') or (action == 'mark-tested' and not remote_runtime):
                    statuses = ('upgraded','passed') if self.technical_verification_enabled() and action == 'accept-rehearsal' else (('ready',) if action == 'upgrade-rehearsal' else ('upgraded',))
                    require(self.active_rehearsal(p)['status'] in statuses, 'Rehearsal prerequisite not met')
                if action == 'reset-rehearsal':
                    require('rehearsal' in self.state['environments'], 'No registered rehearsal exists')
                    require(not any(x.get('activeRehearsal') and self.active_rehearsal(x)['status'] != 'passed' and x['releaseTag'] != tag for x in self.state['packages']), 'Another release owns a pending rehearsal')
                if action == 'reject-acceptance':
                    require(p['stage'] in ('test-deployed', 'rehearsal-upgraded', 'prod-deployed', 'backup-deployed') or
                            (p.get('activeRehearsal') and self.active_rehearsal(p)['status'] == 'upgraded'), 'No pending acceptance to reject')
                if action in ('function-passed', 'mark-tested', 'accept-rehearsal', 'accept-prod', 'accept-backup', 'reject-acceptance', 'audit-baseline') and not (self.technical_verification_enabled() and action in technical_actions):
                    require(isinstance(payload.get('note'), str) and len(payload['note'].strip()) >= 5, 'Acceptance note must describe real business verification')
            if action == 'resolve-task':
                require(payload.get('decision') in ('retry', 'abandon'), 'Explicit retry or abandon decision required')
                require(isinstance(payload.get('note'), str) and len(payload['note'].strip()) >= 5, 'Technical investigation note required')
            job = dict(id='JOB-' + secrets.token_hex(5), requestId=request_id, action=action, payload=payload, releaseTag=tag, actor=actor, status='running', createdAt=stamp(), logs=[])
            self.state['jobs'].insert(0, job)
            self.save()
            self.worker = threading.Thread(target=self.execute, args=(job,), daemon=True)
            self.worker.start()
            return job

    def execute(self, job):
        p, env = None, None
        remote_runtime = self.c.get('runtimeKind') == 'remote-intruoyi'
        try:
            action = job['action']
            self.log(job, 'Started ' + action)
            if action == 'build-release':
                self.build(job)
            elif action == 'resolve-task':
                self.resolve_task(job)
            else:
                self.step(job, 'verify-package')
                deploying = action in ('initialize-baseline', 'publish-test', 'upgrade-rehearsal', 'promote-prod', 'promote-backup')
                p, manifest = (self.package if deploying else self.manifest)(job['releaseTag'])
                if action == 'initialize-baseline':
                    require(not self.state['environments'], 'Baseline requires empty registered environments')
                    for env in ('test', 'prod', 'backup'):
                        job['target'] = env
                        self.step(job, 'initialize-' + env, effects=True)
                        self.deploy(env, p, manifest, job)
                    p['baseline'] = True
                elif action == 'reset-rehearsal':
                    self.step(job, 'remove-isolated-environment', effects=True)
                    self.reset_rehearsal(job)
                    if p.get('activeRehearsal'):
                        record = self.active_rehearsal(p)
                        if record['status'] != 'passed':
                            record['status'] = 'discarded'
                            if record['source'] == 'prod' and p['stage'] in ('rehearsal-ready', 'rehearsal-upgraded'):
                                p['stage'] = 'tested' if remote_runtime else 'function-passed'
                        p.pop('activeRehearsal')
                elif action == 'audit-baseline':
                    self.audit_baseline(p, manifest, job)
                elif action == 'reject-acceptance':
                    env = self.acceptance_env(p)
                    job['target'] = env
                    self.outcome(p, env, 'acceptance', 'failed', job, note=job['payload']['note'], actor=job['actor'])
                    p.setdefault('acceptances', []).append(dict(action=action, env=env, stage=p['stage'], note=job['payload']['note'], actor=job['actor'], time=stamp(), jobId=job['id']))
                    raise RuntimeError('Business acceptance rejected: ' + job['payload']['note'])
                elif action in ('publish-test', 'upgrade-rehearsal', 'promote-prod', 'promote-backup'):
                    env, stage = {'publish-test': ('test', 'test-deployed'), 'upgrade-rehearsal': ('rehearsal', 'rehearsal-upgraded'), 'promote-prod': ('prod', 'prod-deployed'), 'promote-backup': ('backup', 'backup-deployed')}[action]
                    job['target'] = env
                    self.outcome(p, env, 'deployment', 'running', job)
                    self.step(job, 'check-target-origin')
                    if env in self.state['environments']:
                        job['originState'] = dict(self.state['environments'][env])
                        job['originFingerprint'] = job['originState'].get('fingerprint')
                        self.save()
                        self.audit_target(env, p, manifest)
                        job['originFingerprint'] = self.fingerprint(env)
                    if env in ('prod', 'backup'):
                        if env == 'backup':
                            require(self.state['environments'].get('prod', {}).get('releaseTag') == p['releaseTag'], 'Production has moved to another package; this older release cannot update backup')
                        if env == 'prod' or not remote_runtime:
                            require(self.verified_origin(p, job['originFingerprint']), 'Target origin has no passed rehearsal for this immutable package; rehearse this origin first')
                    self.deploy(env, p, manifest, job)
                    if env == 'rehearsal':
                        self.active_rehearsal(p)['status'] = 'upgraded'
                        if self.active_rehearsal(p)['source'] == 'prod':
                            p['stage'] = stage
                    else:
                        p['stage'] = stage
                    extra = {'rehearsalId': job['rehearsalId']} if remote_runtime and env == 'prod' else {}
                    self.outcome(p, env, 'deployment', 'succeeded', job, **extra)
                    if self.technical_verification_enabled():
                        self.verify_technical(env, p, manifest, job)
                elif action == 'prepare-rehearsal':
                    env = 'rehearsal'
                    self.prepare(p, job)
                    self.outcome(p, env, 'preparation', 'succeeded', job)
                    if self.active_rehearsal(p)['source'] == 'prod':
                        p['stage'] = 'rehearsal-ready'
                elif self.technical_verification_enabled() and action in ('mark-tested','accept-rehearsal','accept-prod','accept-backup'):
                    env = {'mark-tested':'test','accept-rehearsal':'rehearsal','accept-prod':'prod','accept-backup':'backup'}[action]
                    job['target'] = env
                    self.verify_technical(env, p, manifest, job)
                else:
                    stage = {'function-passed': 'function-passed', 'mark-tested': 'tested', 'accept-rehearsal': 'rehearsal-passed', 'accept-prod': 'prod-accepted', 'accept-backup': 'completed'}[action]
                    env = {'function-passed': 'test', 'mark-tested': 'test' if remote_runtime else 'rehearsal', 'accept-rehearsal': 'rehearsal', 'accept-prod': 'prod', 'accept-backup': 'backup'}[action]
                    job['target'] = env
                    if remote_runtime and action == 'accept-prod':
                        deployed = p.get('outcomes', {}).get('prod', {}).get('deployment', {})
                        rehearsals = [r for r in p.get('rehearsals', []) if r.get('id') == deployed.get('rehearsalId')
                                      and r.get('source') == 'prod' and r.get('status') == 'passed'
                                      and r.get('packageSha256') == p['packageSha256']]
                        require(deployed.get('status') == 'succeeded' and len(rehearsals) == 1,
                                'Production deployment must bind its accepted rehearsal before business can reopen')
                    self.health(env, p['releaseTag'])
                    self.audit_target(env, p, manifest)
                    if env in ('prod', 'backup'):
                        self.maintenance(env, False)
                    self.outcome(p, env, 'acceptance', 'passed', job, note=job['payload']['note'], actor=job['actor'])
                    p.setdefault('acceptances', []).append(dict(action=action, env=env, note=job['payload']['note'], actor=job['actor'], time=stamp(), jobId=job['id']))
                    if env == 'rehearsal':
                        rehearsal = self.active_rehearsal(p)
                        rehearsal.update(status='passed', note=job['payload']['note'], actor=job['actor'], acceptedAt=stamp())
                        if rehearsal['source'] == 'prod':
                            p['stage'] = stage
                    else:
                        p['stage'] = stage
                    if remote_runtime and action == 'accept-prod':
                        p['validatedProductionRehearsal'] = rehearsals[0]['id']
                self.save()
            job['status'] = 'succeeded'
            self.log(job, 'Succeeded; all required checks passed')
        except Exception as exc:
            job.update(status='interrupted' if getattr(exc,'remoteStatusUnknown',False) else 'failed', error=str(exc).replace(self.password, '[REDACTED]'))
            if p and env and job['action'] != 'reject-acceptance' and not job.get('technicalVerification'):
                kind = 'preparation' if job['action'] == 'prepare-rehearsal' else ('acceptance' if job['action'].startswith('accept-') or job['action'] in ('mark-tested', 'function-passed') else 'deployment')
                self.outcome(p, env, kind, job['status'], job, error=job['error'])
            self.log(job, 'Stopped: ' + job['error'])
        finally:
            job['finishedAt'] = stamp()
            self.save()

    def acceptance_env(self, p):
        if p.get('activeRehearsal') and self.active_rehearsal(p)['status'] == 'upgraded':
            return 'rehearsal'
        return {'test-deployed': 'test', 'prod-deployed': 'prod', 'backup-deployed': 'backup'}[p['stage']]

    def resolve_task(self, job):
        payload = job['payload']
        originals = [j for j in self.state['jobs'] if j['id'] == payload.get('jobId')]
        require(len(originals) == 1, 'Original task not found')
        original = originals[0]
        require(original['status'] in ('failed', 'interrupted') and not original.get('resolution'), 'Task is not unresolved failed/interrupted')
        self.step(job, 'reconcile-original-task')
        if original['action'] == 'build-release':
            require(payload['decision'] == 'abandon', 'Interrupted build must be abandoned; build again as a new immutable package')
        else:
            p, manifest = self.manifest(original['releaseTag'])
            env = original.get('target')
            if original['action'] in ('reject-acceptance', 'accept-prod', 'accept-backup', 'function-passed', 'mark-tested'):
                env = env or {'accept-prod':'prod', 'accept-backup':'backup', 'function-passed':'test', 'mark-tested':'rehearsal'}.get(original['action'])
                if not env:
                    rows = [a for a in p.get('acceptances', []) if a.get('jobId') == original['id']]
                    require(len(rows) == 1 and rows[0].get('env'), 'Original acceptance target was not recorded; technician reconciliation required')
                    env = rows[0]['env']
                current_tag = self.state['environments'].get(env, {}).get('releaseTag')
                if env in ('prod', 'backup') and current_tag != p['releaseTag']:
                    require(payload['decision'] == 'abandon', 'Acceptance target was replaced; explicitly abandon the superseded task after replacement acceptance')
                    replacement, replacement_manifest = self.manifest(current_tag)
                    accepted = replacement.get('outcomes', {}).get(env, {}).get('acceptance', {})
                    require(accepted.get('status') == 'passed' and self.state['environments'][env].get('maintenance') is False and not self.state['environments'][env].get('maintenanceError'), 'Replacement release has not passed acceptance and reopened business')
                    self.audit_target(env, replacement, replacement_manifest)
                    self.health(env, current_tag)
                    original['resolution'] = dict(decision='abandon', note=payload['note'], actor=job['actor'], time=stamp(), jobId=job['id'], supersededBy=current_tag)
                    self.log(job, 'Original failed acceptance retained; explicitly superseded by accepted release ' + current_tag)
                    return
                require(payload['decision'] == 'retry' or env not in ('prod', 'backup'), 'Production/backup candidate remains installed; acceptance cannot be abandoned before explicit restoration')
                self.audit_target(env, p, manifest)
                self.health(env, p['releaseTag'])
                recorded = p.get('outcomes', {}).get(env, {}).get('acceptance', {})
                accepted = recorded.get('status') == 'passed' and recorded.get('jobId') == original['id']
                if accepted:
                    if env in ('prod', 'backup'):
                        marker = self.run(['docker', 'exec', self.prefix(env) + '-backend', 'sh', '-c', 'if test -f /tmp/release-maintenance; then echo closed; else echo open; fi']).decode().strip()
                        require(marker == 'open' and not self.state['environments'][env]['maintenance'], 'Accepted task has not completed reopening; investigate before reconciling')
                    if original['action'] == 'mark-tested':
                        record = self.active_rehearsal(p)
                        record.update(status='passed', note=recorded.get('note'), actor=recorded.get('actor'))
                        if record['source'] == 'prod':
                            p['stage'] = 'tested'
                    else:
                        p['stage'] = {'function-passed':'function-passed', 'accept-prod':'prod-accepted', 'accept-backup':'completed'}[original['action']]
                elif env in ('prod', 'backup'):
                    self.maintenance(env, True)
            elif original['action'] == 'prepare-rehearsal':
                records = [r for r in p.get('rehearsals', []) if r['jobId'] == original['id']]
                record = records[0] if records else None
                if record and record['status'] == 'ready':
                    require(payload['decision'] == 'retry', 'Ready rehearsal must be explicitly reset before abandonment')
                    self.audit_target('rehearsal', p, manifest)
                    require(self.fingerprint('rehearsal') == record['originFingerprint'], 'Prepared rehearsal origin changed')
                    if record['source'] == 'prod':
                        p['stage'] = 'rehearsal-ready'
                elif original.get('effectsStarted'):
                    require(self.resources_absent('rehearsal') and 'rehearsal' not in self.state['environments'], 'Partial rehearsal must be explicitly cleaned up before resolving')
                    if record:
                        record['status'] = 'discarded'
                        p.pop('activeRehearsal', None)
                else:
                    source_env = original['payload'].get('source', 'prod')
                    self.audit_target(source_env, p, manifest)
            elif original['action'] in ('initialize-baseline', 'reset-rehearsal'):
                targets = ('test', 'prod', 'backup') if original['action'] == 'initialize-baseline' else ('rehearsal',)
                require(all(self.resources_absent(target) and target not in self.state['environments'] for target in targets), 'Partial initialization/deletion requires explicit cleanup of its owned resources before resolving')
            elif env:
                self.audit_target(env, p, manifest)
                current = self.state['environments'][env]
                if current['releaseTag'] == p['releaseTag'] and original.get('effectsStarted'):
                    require(payload['decision'] == 'retry', 'Candidate is installed; abandon requires explicit manual restoration first')
                    self.health(env, p['releaseTag'])
                    self.check_contract(env, manifest, len(manifest['migrations']))
                    if env in ('prod', 'backup'):
                        self.maintenance(env, True)
                    else:
                        require(not current.get('maintenance'), 'Application remains in maintenance; investigate before reconciling')
                    if env == 'rehearsal':
                        self.active_rehearsal(p)['status'] = 'upgraded'
                        if self.active_rehearsal(p)['source'] == 'prod':
                            p['stage'] = 'rehearsal-upgraded'
                    else:
                        p['stage'] = {'test':'test-deployed','prod':'prod-deployed','backup':'backup-deployed'}[env]
                    self.outcome(p, env, 'deployment', 'succeeded', job, reconciles=original['id'])
                else:
                    if original.get('originFingerprint'):
                        require(self.fingerprint(env) == original['originFingerprint'], 'Origin cannot be proven unchanged; manually restore/investigate before resolving')
                    else:
                        origin = original.get('originState', {})
                        require(not original.get('effectsStarted') and origin.get('releaseTag') == current['releaseTag'] and origin.get('manifestSha256') == current['manifestSha256'], 'Original target identity cannot be proven; explicit restoration/audit required')
                    # A pre-migration stop can leave the old application paused. Explicitly
                    # reopening it is a separate technician decision after identity checks.
                    if original.get('effectsStarted'):
                        require(not current.get('maintenance'), 'Restore and explicitly reopen the original application before resolving')
            else:
                require(not original.get('effectsStarted'), 'Partial operation requires manual restoration and explicit target reconciliation')
        original['resolution'] = dict(decision=payload['decision'], note=payload['note'], actor=job['actor'], time=stamp(), jobId=job['id'])
        self.log(job, 'Original task retained; investigation recorded, no automatic SQL retry or rollback: ' + original['id'])

    def build(self, job):
        repo = self.c['repo']
        commit = job['payload'].get('commit', '')
        require(re.fullmatch('[0-9a-f]{40}', commit), 'Exact full Git commit required')
        require(self.run(['git', '-C', repo, 'rev-parse', commit + '^{commit}']).decode().strip() == commit, 'Commit does not exist')
        tag = stamp()
        folder = self.root / 'packages' / tag
        require(not folder.exists(), 'Release timestamp already exists')
        folder.mkdir(parents=True)
        worktree = self.root / 'worktrees' / tag
        worktree.parent.mkdir(parents=True, exist_ok=True)
        self.run(['git', '-c', 'core.autocrlf=false', '-C', repo, 'worktree', 'add', '--no-checkout', '--detach', str(worktree), commit])
        source_subdir = self.c.get('sourceSubdir', '.')
        if source_subdir != '.':
            self.run(['git', '-c', 'core.autocrlf=false', '-C', str(worktree), 'sparse-checkout', 'set', source_subdir])
        self.run(['git', '-c', 'core.autocrlf=false', '-C', str(worktree), 'checkout', '--detach', commit])
        require(not self.run(['git', '-C', str(worktree), 'status', '--porcelain']).strip(), 'Dedicated build worktree must be clean')
        app = worktree / self.c.get('sourceSubdir', '.')
        source_migrations = []
        for path in sorted((app / self.c['migrations']).glob('*.sql')):
            require(re.fullmatch(r'M[0-9]{6}__[a-z0-9_]+\.sql', path.name), 'Invalid numbered migration: ' + path.name)
            source_migrations.append(dict(id=path.name.split('__')[0], name=path.name, sha256=digest(path)))
        require(source_migrations and len({m['id'] for m in source_migrations}) == len(source_migrations), 'Migrations missing or duplicate')
        incoming = {m['id']:m for m in source_migrations}
        require(list(incoming) == ['M' + str(n).zfill(6) for n in range(1, len(incoming) + 1)], 'Migration numbers must be contiguous from M000001')
        prechecks = json.loads((app / self.c['migrations'] / 'prechecks.json').read_text('utf-8'))
        contracts = json.loads((app / self.c['migrations'] / 'schema-contracts.json').read_text('utf-8'))
        require(set(prechecks) == set(incoming) == set(contracts), 'Each migration requires explicit prechecks and a schema contract')
        for checks in prechecks.values():
            for check in checks:
                self.validate_precheck(check)
        for prior in self.state['packages']:
            _, previous = self.manifest(prior['releaseTag'])
            for m in previous['migrations']:
                require(digest(Path(prior['directory']) / 'migrations' / m['name']) == m['sha256'], 'Historical migration artifact was changed: ' + m['id'])
                require(m['id'] in incoming and incoming[m['id']] == m, 'Historical migration changed or removed: ' + m['id'])
        self.log(job, 'Migration number and historical checksum preflight passed before image build')
        build_mode = self.c.get('buildMode', 'docker-multistage')
        require(build_mode in ('docker-multistage', 'host-local-images'), 'Unknown buildMode')
        build_record = dict(mode=build_mode, executorSha256=digest(Path(__file__)))
        dockerfiles = {role: app / self.c['dockerfiles'][role] for role in ('backend', 'frontend')}
        if build_mode == 'host-local-images':
            bases = {}
            for role in ('backend', 'frontend'):
                reference = self.c['localRuntimeImages'][role]
                bases[role] = self.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', reference]).decode().strip()
            build_record['runtimeImages'] = bases
            mvn, npm = shutil.which('mvn.cmd' if os.name == 'nt' else 'mvn'), shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
            require(mvn and npm, 'Host Maven and npm are required')
            build_record['maven'] = self.run([mvn, '-version']).decode(errors='replace').strip()
            build_record['node'] = self.run(['node', '--version']).decode().strip()
            self.log(job, 'Compiling pinned source with host Maven and npm; packaging with existing local runtime image IDs')
            (app / 'backend/src/main/resources/release.properties').write_text('release.tag=' + tag + '\n', 'utf-8')
            self.run([mvn, '-B', '-ntp', 'package'], cwd=app / 'backend', timeout=1800)
            self.run([npm, 'ci', '--no-audit', '--no-fund'], cwd=app / 'frontend', timeout=900)
            build_env = dict(os.environ, RELEASE_TAG=tag)
            self.run([npm, 'run', 'build'], cwd=app / 'frontend', env=build_env, timeout=900)
            templates = {
                'backend': 'WORKDIR /app\nCOPY backend/target/app.jar /app/app.jar\nUSER 10001\nEXPOSE 8000\nENTRYPOINT ["java", "-jar", "/app/app.jar"]\n',
                'frontend': 'COPY nginx.conf /etc/nginx/conf.d/default.conf\nCOPY frontend/dist/ /usr/share/nginx/html/\nEXPOSE 80\n'}
            for role in ('backend', 'frontend'):
                dockerfiles[role] = folder / ('Dockerfile.' + role)
                # BuildKit parses a raw sha256 ID as a registry name. Give the
                # inspected local image a task-owned, content-derived tag.
                local_base = self.c['applicationId'] + '-local-base:' + bases[role].split(':')[1]
                self.run(['docker', 'tag', bases[role], local_base])
                require(self.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', local_base]).decode().strip() == bases[role], 'Local base identity changed')
                dockerfiles[role].write_text('FROM ' + local_base + '\n' + templates[role], 'utf-8')
                Path(str(dockerfiles[role]) + '.dockerignore').write_text('**/node_modules\n.git\n', 'utf-8')
            require(not self.run(['git', '-C', str(worktree), 'status', '--porcelain']).strip(), 'Compilation changed tracked source')
        images = {}
        for role in ('backend', 'frontend'):
            name = f'{self.c["applicationId"]}-{role}:{tag}'
            self.log(job, 'Building pinned ' + role + ' image from ' + commit)
            self.run(['docker', 'build', '--pull=false', '--build-arg', 'RELEASE_TAG=' + tag, '-f', str(dockerfiles[role]), '-t', name, str(app)], timeout=1800)
            images[role] = dict(name=name, id=self.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', name]).decode().strip())
        container = self.run(['docker', 'create', images['frontend']['name']]).decode().strip()
        try:
            self.run(['docker', 'cp', container + ':/usr/share/nginx/html/release-info.json', str(folder / 'release-info.json')])
            require(json.loads((folder / 'release-info.json').read_text('utf-8'))['releaseTag'] == tag, 'Image release-info.json mismatch')
            self.log(job, 'Read release-info.json from frontend image; releaseTag matches before export')
        finally:
            self.run(['docker', 'rm', container])
        self.run(['docker', 'save', '-o', str(folder / 'images.tar'), images['backend']['name'], images['frontend']['name']], timeout=1200)
        migration_dir = app / self.c['migrations']
        migrations = []
        (folder / 'migrations').mkdir()
        for path in sorted(migration_dir.glob('*.sql')):
            require(re.fullmatch(r'M[0-9]{6}__[a-z0-9_]+\.sql', path.name), 'Invalid numbered migration: ' + path.name)
            shutil.copyfile(path, folder / 'migrations' / path.name)
            migrations.append(dict(id=path.name.split('__')[0], name=path.name, sha256=digest(path)))
        require(migrations and len({m['id'] for m in migrations}) == len(migrations), 'Migrations missing or duplicate')
        files = [dict(name='images.tar', sha256=digest(folder / 'images.tar')), dict(name='release-info.json', sha256=digest(folder / 'release-info.json'))]
        files += [dict(name='migrations/' + m['name'], sha256=m['sha256']) for m in migrations]
        manifest = dict(applicationId=self.c['applicationId'], releaseTag=tag, gitCommit=commit, IMAGE_TAG=tag, images=images, migrations=migrations, prechecks=prechecks, schemaContracts=contracts, maintenanceProtocol='graceful-stop-v1', files=files, mysqlImage=self.c['mysqlImage'], build=build_record)
        (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), 'utf-8')
        with tarfile.open(folder / 'release.tar', 'w') as archive:
            for item in ['manifest.json'] + [f['name'] for f in files]:
                archive.add(folder / item, arcname=item)
        self.state['packages'].insert(0, dict(releaseTag=tag, gitCommit=commit, directory=str(folder), manifestSha256=digest(folder / 'manifest.json'), packageSha256=digest(folder / 'release.tar'), stage='built', baseline=False))
        job['releaseTag'] = tag
        self.save()
        self.log(job, 'Exported complete images and manifest; package SHA256 recorded')

    def prefix(self, env):
        require(env in ('test', 'prod', 'backup', 'rehearsal'), 'Unknown environment')
        return self.c['applicationId'] + '-' + env

    def resources_absent(self, env):
        prefix = self.prefix(env)
        containers = self.run(['docker', 'ps', '-a', '--filter', 'name=^/' + prefix + '-(db|backend|frontend)$', '--format', '{{.Names}}']).strip()
        volumes = self.run(['docker', 'volume', 'ls', '--filter', 'name=^' + prefix + '-data$', '--format', '{{.Name}}']).strip()
        networks = self.run(['docker', 'network', 'ls', '--filter', 'name=^' + prefix + '$', '--format', '{{.Name}}']).strip()
        return not (containers or volumes or networks)

    def sql(self, env, query, database=True):
        args = ['docker', 'exec', '-i', '-e', 'MYSQL_PWD=' + self.password, self.prefix(env) + '-db', 'mysql', '-uroot', '--batch', '--skip-column-names']
        if database:
            args.append('release_app')
        # Keep final empty tab-separated columns (e.g. EXTRA='') intact.
        return self.run(args, query.encode('utf-8'), timeout=180).decode('utf-8').rstrip('\r\n')

    @staticmethod
    def validate_precheck(check):
        require(isinstance(check, dict) and isinstance(check.get('query'), str), 'Invalid migration precheck')
        query = check['query'].strip()
        require(re.match(r'^SELECT\s', query, re.I) and not re.search(r';|--|/\*|\b(INTO|OUTFILE|DUMPFILE|FOR\s+UPDATE|GET_LOCK|SLEEP)\b', query, re.I), 'Prechecks must be a single read-only SELECT')
        require(isinstance(check.get('expected'), str) and isinstance(check.get('message'), str), 'Precheck expected result and explanation required')

    def history(self, env, manifest):
        tables = self.sql(env, 'SHOW TABLES;').splitlines()
        require('release_migration_history' in tables, 'Migration ledger missing; do not invent historical successes')
        self.sql(env, 'DESCRIBE release_migration_history;')
        ledger_columns = self.sql(env, "SELECT COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='release_app' AND TABLE_NAME='release_migration_history' ORDER BY ORDINAL_POSITION")
        require(ledger_columns == 'migration_id\tvarchar(20)\tNO\nchecksum\tchar(64)\tNO\nstatus\tvarchar(20)\tNO\napplied_at\ttimestamp\tYES', 'Migration ledger schema is not the executor contract')
        require(self.sql(env, "SELECT INDEX_NAME,NON_UNIQUE,SEQ_IN_INDEX,COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='release_app' AND TABLE_NAME='release_migration_history' ORDER BY INDEX_NAME,SEQ_IN_INDEX") == 'PRIMARY\t0\t1\tmigration_id', 'Migration ledger must have exactly its migration_id primary key')
        rows = self.sql(env, 'SELECT migration_id,checksum,status FROM release_migration_history ORDER BY migration_id;')
        existing = {r.split('\t')[0]: r.split('\t')[1:] for r in rows.splitlines() if r}
        require(len(existing) == len(rows.splitlines()), 'Duplicate migration records are not a valid baseline')
        known = {m['id']: m for m in manifest['migrations']}
        require(list(existing) == list(known)[:len(existing)], 'Migration history is not a contiguous known prefix')
        for mid, values in existing.items():
            require(len(values) == 2 and values[1] == 'succeeded', 'Failed/running migration requires investigation: ' + mid)
            require(values[0] == known[mid]['sha256'], 'Migration checksum mismatch: ' + mid)
        return existing

    def check_contract(self, env, manifest, count):
        require('schemaContracts' in manifest, 'Package lacks schema contracts; build a new audited candidate')
        require(count > 0, 'Existing database has no explained migration baseline')
        contract = manifest['schemaContracts'][manifest['migrations'][count - 1]['id']]
        tables = self.sql(env, 'SHOW TABLES;').splitlines()
        require(set(tables) == set(contract['columns']) | {'release_migration_history'}, 'Unexpected tables or missing tables in target')
        for table, expected in contract['columns'].items():
            require(re.fullmatch('[a-zA-Z0-9_]+', table), 'Invalid contract table')
            self.sql(env, 'DESCRIBE `' + table + '`;')
            options = self.sql(env, "SELECT ENGINE,TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA='release_app' AND TABLE_NAME='" + table + "'")
            table_options = contract['options'][table]
            require(re.fullmatch('[a-zA-Z0-9_]+', table_options['collation']), 'Invalid contract collation')
            require(options == table_options['engine'] + '\t' + table_options['collation'], 'Unexpected table engine or collation: ' + table)
            require(self.sql(env, "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='release_app' AND TABLE_NAME='" + table + "' AND ((COLLATION_NAME IS NOT NULL AND COLLATION_NAME <> '" + table_options['collation'] + "') OR GENERATION_EXPRESSION <> '')") == '0', 'Unexpected column collation/generated expression: ' + table)
            require(self.sql(env, "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA='release_app' AND TABLE_NAME='" + table + "' AND CONSTRAINT_TYPE='FOREIGN KEY'") == '0', 'Unexpected foreign key: ' + table)
            require(self.sql(env, "SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA='release_app' AND TABLE_NAME='" + table + "' AND CONSTRAINT_TYPE='CHECK' AND ENFORCED <> 'YES'") == '0', 'CHECK constraints must actually be enforced: ' + table)
            queries = {
                'columns': "SELECT COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COALESCE(COLUMN_DEFAULT,'<NULL>'),EXTRA FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='release_app' AND TABLE_NAME='" + table + "' ORDER BY ORDINAL_POSITION",
                'indexes': "SELECT INDEX_NAME,NON_UNIQUE,SEQ_IN_INDEX,COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='release_app' AND TABLE_NAME='" + table + "' ORDER BY INDEX_NAME,SEQ_IN_INDEX",
                'checks': "SELECT tc.CONSTRAINT_NAME,cc.CHECK_CLAUSE FROM information_schema.TABLE_CONSTRAINTS tc JOIN information_schema.CHECK_CONSTRAINTS cc ON tc.CONSTRAINT_SCHEMA=cc.CONSTRAINT_SCHEMA AND tc.CONSTRAINT_NAME=cc.CONSTRAINT_NAME WHERE tc.TABLE_SCHEMA='release_app' AND tc.TABLE_NAME='" + table + "' ORDER BY tc.CONSTRAINT_NAME"
            }
            for kind, query in queries.items():
                raw = self.sql(env, query)
                actual = [r.split('\t') for r in raw.splitlines()] if raw else []
                wanted = [[str(v) for v in row] for row in contract[kind][table]]
                if kind == 'checks':
                    actual = [[name, re.sub(r'\s+|`', '', value.lower())] for name, value in actual]
                    wanted = [[name, re.sub(r'\s+|`', '', value.lower())] for name, value in wanted]
                require(actual == wanted, 'Schema contract mismatch in ' + table + '/' + kind + ': inspect actual definitions before proceeding')
        for obj, clause in [('TRIGGERS', "TRIGGER_SCHEMA"), ('EVENTS', 'EVENT_SCHEMA'), ('ROUTINES', 'ROUTINE_SCHEMA')]:
            require(self.sql(env, "SELECT COUNT(*) FROM information_schema." + obj + " WHERE " + clause + "='release_app'") == '0', 'Unexpected database-side writer: ' + obj)

    def audit_target(self, env, p, manifest):
        require(env in self.state['environments'], 'Target is not registered; audit the baseline first')
        registered = self.state['environments'][env]
        self.health(env, registered['releaseTag'])
        existing = self.history(env, manifest)
        self.check_contract(env, manifest, len(existing))
        if registered.get('fingerprint'):
            require(self.fingerprint(env) == registered['fingerprint'], 'Actual schema/program/ledger drifted from registered state')

    def audit_baseline(self, p, manifest, job):
        env = job['payload'].get('target')
        require(env in ('test', 'prod', 'backup'), 'Explicit baseline target required')
        tag = job['payload'].get('currentReleaseTag')
        current, current_manifest = self.manifest(tag)
        for role in ('frontend', 'backend', 'db'):
            owner = self.run(['docker', 'inspect', '--format', '{{index .Config.Labels "release-center"}}', self.prefix(env) + '-' + role]).decode().strip()
            require(owner == self.c['applicationId'], 'Cannot adopt a resource not owned by this demo application')
        self.health(env, tag)
        existing = self.history(env, manifest)
        require(list(existing) == [m['id'] for m in current_manifest['migrations']], 'Running package and applied migrations disagree')
        self.check_contract(env, manifest, len(existing))
        registered = self.state['environments'].get(env)
        require(not registered or registered['releaseTag'] == tag, 'Registered target release conflicts with operator selection')
        # Read-only audit; never writes migration successes or changes the application.
        marker = self.run(['docker', 'exec', self.prefix(env) + '-backend', 'sh', '-c', 'if test -f /tmp/release-maintenance; then echo closed; else echo open; fi']).decode().strip()
        require(marker in ('closed', 'open'), 'Cannot determine actual maintenance state')
        entry = dict(registered) if registered else dict(releaseTag=tag, manifestSha256=current['manifestSha256'], port=self.c['ports'][env])
        entry['maintenance'] = marker == 'closed'
        entry['fingerprint'] = self.fingerprint(env, entry)
        entry['baselineAudit'] = dict(referencePackage=p['releaseTag'], jobId=job['id'], actor=job['actor'], note=job['payload']['note'], time=stamp())
        self.state['environments'][env] = entry
        self.log(job, env + ': program identity, full migration history and schema contract audited; no database changes')

    def preconditions(self, env, manifest, job, only=None):
        existing = self.history(env, manifest)
        require('prechecks' in manifest, 'Package lacks migration prechecks')
        for m in manifest['migrations']:
            if m['id'] in existing or (only is not None and m['id'] != only):
                continue
            for check in manifest['prechecks'][m['id']]:
                self.validate_precheck(check)
                result = self.sql(env, check['query'])
                require(result == check['expected'], 'Migration precondition failed ' + m['id'] + ': ' + check['message'] + '; actual=' + result)
            self.log(job, env + ': latest-data preconditions passed ' + m['id'])

    def images_ready(self, p, manifest, job):
        self.step(job, 'prepare-and-verify-images')
        available = set(self.run(['docker', 'image', 'ls', '--no-trunc', '--format', '{{.ID}}']).decode().splitlines())
        if any(manifest['images'][role]['id'] not in available for role in ('backend', 'frontend')):
            # Import missing images only from this exact package, never a registry pull.
            self.run(['docker', 'load', '-i', str(Path(p['directory']) / 'images.tar')], timeout=900)
        for role in ('backend', 'frontend'):
            identity = self.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', manifest['images'][role]['id']]).decode().strip()
            require(identity == manifest['images'][role]['id'], 'Required package image is not ready: ' + role)
        self.log(job, 'Both fixed image IDs are ready before stopping writers or migrating')

    def db(self, env):
        prefix = self.prefix(env)
        found = self.run(['docker', 'ps', '-a', '--filter', 'name=^/' + prefix + '-db$', '--format', '{{.Names}}']).decode().strip()
        if not found:
            require(self.resources_absent(env), 'Preexisting network/volume/application prevents empty-environment creation')
            self.run(['docker', 'network', 'create', '--label', 'release-center=' + self.c['applicationId'], prefix])
            self.run(['docker', 'volume', 'create', '--label', 'release-center=' + self.c['applicationId'], prefix + '-data'])
            envfile = self.root / (env + '-mysql.env')
            envfile.write_text('MYSQL_ROOT_PASSWORD=' + self.password + '\nMYSQL_DATABASE=release_app\nMYSQL_ROOT_HOST=%\n', 'utf-8')
            self.run(['docker', 'run', '-d', '--name', prefix + '-db', '--label', 'release-center=' + self.c['applicationId'], '--network', prefix, '--network-alias', 'db', '--env-file', str(envfile), '-v', prefix + '-data:/var/lib/mysql', self.c['mysqlImage']])
        else:
            require(env in self.state['environments'], 'Unregistered preexisting DB container; ownership conflict')
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            check = subprocess.run(['docker', 'exec', '-e', 'MYSQL_PWD=' + self.password, prefix + '-db', 'mysql', '-uroot', '--batch', '--skip-column-names', 'release_app', '-e', 'SELECT 1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if check.returncode == 0 and check.stdout.strip() == b'1':
                return
            time.sleep(2)
        raise RuntimeError('MySQL readiness deadline exceeded')

    def migrations(self, env, p, manifest, job):
        # Inspect schema before changing it; never register unknown historic SQL as success.
        tables = self.sql(env, 'SHOW TABLES;').splitlines()
        if 'release_migration_history' not in tables:
            require(not tables, 'Unknown existing schema: explicit baseline registration required')
            self.sql(env, 'CREATE TABLE release_migration_history (migration_id VARCHAR(20) PRIMARY KEY, checksum CHAR(64) NOT NULL, status VARCHAR(20) NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);')
        existing = self.history(env, manifest)
        for m in manifest['migrations']:
            if m['id'] in existing:
                self.log(job, env + ': skip matching succeeded migration ' + m['id'])
                continue
            self.step(job, 'migration-precheck-' + m['id'])
            self.preconditions(env, manifest, job, only=m['id'])
            self.step(job, 'migration-' + m['id'], effects=True)
            self.sql(env, f"INSERT INTO release_migration_history(migration_id,checksum,status) VALUES('{m['id']}','{m['sha256']}','running');")
            try:
                self.sql(env, (Path(p['directory']) / 'migrations' / m['name']).read_text('utf-8'))
            except Exception:
                self.sql(env, f"UPDATE release_migration_history SET status='failed' WHERE migration_id='{m['id']}';")
                raise
            self.sql(env, f"UPDATE release_migration_history SET status='succeeded' WHERE migration_id='{m['id']}';")
            self.check_contract(env, manifest, list(x['id'] for x in manifest['migrations']).index(m['id']) + 1)
            self.log(job, env + ': applied ' + m['id'])

    def maintenance(self, env, enabled):
        prefix = self.prefix(env)
        if not enabled:
            # Keep writes closed until the old process has fully drained. Only
            # report business reopening after the restarted candidate is healthy.
            try:
                self.stop_writers(env)
                marker = self.root / 'maintenance-marker'
                marker.write_text('Release acceptance pending', 'utf-8')
                self.run(['docker', 'cp', str(marker), prefix + '-backend:/tmp/release-maintenance'])
                self.run(['docker', 'start', prefix + '-backend'])
                self.health(env, self.state['environments'][env]['releaseTag'])
                self.run(['docker', 'exec', '-u', '0', prefix + '-backend', 'rm', '-f', '/tmp/release-maintenance'])
                self.stop_writers(env)
                self.run(['docker', 'start', prefix + '-backend'])
                self.health(env, self.state['environments'][env]['releaseTag'])
            except Exception as opening_error:
                try:
                    # A failed reopening must leave a stopped, durably closed
                    # backend. This closes admission; it never rolls back data.
                    self.stop_writers(env)
                    marker = self.root / 'maintenance-marker'
                    marker.write_text('Reopening failed; technician investigation required', 'utf-8')
                    self.run(['docker', 'cp', str(marker), prefix + '-backend:/tmp/release-maintenance'])
                    self.state['environments'][env]['maintenance'] = True
                except Exception as closing_error:
                    self.state['environments'][env].update(maintenance=None, maintenanceError=str(closing_error).replace(self.password, '[REDACTED]'))
                    self.save()
                    raise RuntimeError('Business reopening failed: ' + str(opening_error) + '; closing could not be confirmed: ' + str(closing_error)) from closing_error
                self.save()
                raise RuntimeError('Business reopening failed; backend stopped with durable maintenance marker: ' + str(opening_error)) from opening_error
            self.state['environments'][env]['maintenance'] = False
            self.state['environments'][env].pop('maintenanceError', None)
            self.save()
            return
        self.run(['docker', 'exec', '-u', '0', prefix + '-backend', 'sh', '-c', 'set -e; touch /tmp/release-maintenance; chown 10001 /tmp/release-maintenance'])
        self.state['environments'][env]['maintenance'] = enabled
        self.save()
        # Restart explicitly reloads the durable gate, including an explicit reopen.
        # During closing, graceful process termination also drains old application
        # versions which predate the internal control endpoint. Never migrate with
        # an old backend process still alive or with unfinished DB transactions.
        self.stop_writers(env)
        self.run(['docker', 'start', prefix + '-backend'])
        self.health(env, self.state['environments'][env]['releaseTag'])

    def stop_writers(self, env):
        prefix = self.prefix(env)
        self.run(['docker', 'stop', '--time', '60', prefix + '-backend'], timeout=90)
        info = json.loads(self.run(['docker', 'inspect', '--format', '{{json .State}}', prefix + '-backend']))
        require(not info['Running'] and info['ExitCode'] != 137, 'Backend did not stop gracefully; migration refused')
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            # This demo DB is dedicated to one app, with no background writers.
            if self.sql(env, 'SELECT COUNT(*) FROM information_schema.INNODB_TRX') == '0':
                return
            time.sleep(1)
        raise RuntimeError('Database write transactions have not drained; migration refused')

    def app_containers(self, env, manifest):
        prefix = self.prefix(env)
        for role in ('frontend', 'backend'):
            found = self.run(['docker', 'ps', '-a', '--filter', 'name=^/' + prefix + '-' + role + '$', '--format', '{{.Names}}']).decode().strip()
            if found:
                require(env in self.state['environments'], 'Unregistered app container conflict')
                self.run(['docker', 'rm', '-f', prefix + '-' + role])
        envfile = self.root / (env + '-app.env')
        envfile.write_text('\n'.join(['DB_HOST=db', 'DB_PORT=3306', 'DB_NAME=release_app', 'DB_USER=root', 'DB_PASSWORD=' + self.password, 'DEPLOY_ENV=' + env]), 'utf-8')
        for role in ('backend', 'frontend'):
            args = ['docker', 'create', '--name', prefix + '-' + role, '--label', 'release-center=' + self.c['applicationId'], '--network', prefix, '--network-alias', role]
            if role == 'backend':
                args += ['--env-file', str(envfile)]
            else:
                args += ['-p', '127.0.0.1:' + str(self.c['ports'][env]) + ':80']
            args.append(manifest['images'][role]['id'])
            self.run(args)
            if role == 'backend' and env in ('prod', 'backup') and self.state['environments'].get(env):
                marker = self.root / 'maintenance-marker'
                marker.write_text('Release acceptance pending', 'utf-8')
                self.run(['docker', 'cp', str(marker), prefix + '-backend:/tmp/release-maintenance'])
            self.run(['docker', 'start', prefix + '-' + role])
            if role == 'backend' and env in ('prod', 'backup') and self.state['environments'].get(env):
                self.run(['docker', 'exec', '-u', '0', prefix + '-backend', 'chown', '10001', '/tmp/release-maintenance'])

    def health(self, env, tag):
        url = 'http://127.0.0.1:' + str(self.c['ports'][env])
        deadline = time.monotonic() + 150
        error = ''
        endpoint = url
        while time.monotonic() < deadline:
            try:
                endpoint = url + '/release-info.json'
                with self.local_http.open(endpoint, timeout=3) as response:
                    require(response.status == 200 and json.load(response)['releaseTag'] == tag, 'Frontend version mismatch')
                endpoint = url + '/actuator/health'
                with self.local_http.open(endpoint, timeout=3) as response:
                    require(json.load(response)['status'] == 'UP', 'Backend not UP')
                endpoint = url + '/api/version'
                with self.local_http.open(endpoint, timeout=3) as response:
                    version = json.load(response)
                    require(version['releaseTag'] == tag and version['environment'] == env, 'Backend version/environment mismatch')
                _, manifest = self.manifest(tag)
                for role in ('backend', 'frontend'):
                    image_id = self.run(['docker', 'inspect', '--format', '{{.Image}}', self.prefix(env) + '-' + role]).decode().strip()
                    require(image_id == manifest['images'][role]['id'], 'Runtime image identity differs from fixed package')
                return
            except Exception as exc:
                error = str(exc)
                time.sleep(2)
        raise RuntimeError('Runtime health deadline ' + env + ' at ' + endpoint + ': ' + error)

    def deploy(self, env, p, manifest, job):
        self.images_ready(p, manifest, job)
        self.step(job, 'database-readiness')
        self.db(env)
        if env in self.state['environments']:
            self.step(job, 'latest-data-prechecks')
            self.preconditions(env, manifest, job)
            self.step(job, 'close-and-drain-writers', effects=True)
            self.maintenance(env, True)
            self.stop_writers(env)
            self.log(job, env + ': old backend stopped and database transactions drained before migrations')
            if env in ('prod', 'backup'):
                self.step(job, 'create-recovery-point', effects=True)
                self.recovery(env, p, job)
        self.migrations(env, p, manifest, job)
        self.step(job, 'replace-application-containers', effects=True)
        self.app_containers(env, manifest)
        pending = env in ('prod', 'backup') and env in self.state['environments']
        self.state['environments'][env] = dict(releaseTag=p['releaseTag'], manifestSha256=p['manifestSha256'], maintenance=pending, updatedAt=stamp(), port=self.c['ports'][env])
        self.save()
        self.step(job, 'verify-deployed-application')
        self.health(env, p['releaseTag'])
        for role in ('backend', 'frontend'):
            current = self.run(['docker', 'inspect', '--format', '{{.Image}}', self.prefix(env) + '-' + role]).decode().strip()
            require(current == manifest['images'][role]['id'], 'Running image identity mismatch')
        self.check_contract(env, manifest, len(manifest['migrations']))
        self.state['environments'][env]['fingerprint'] = self.fingerprint(env)
        self.save()
        self.log(job, env + ': frontend200 backendUP releaseTag and image identities verified')

    def fingerprint(self, env, registered=None):
        require(registered is not None or env in self.state['environments'], 'Registered baseline environment missing')
        registered = registered if registered is not None else self.state['environments'][env]
        self.health(env, registered['releaseTag'])
        definitions = {}
        for table in sorted(self.sql(env, 'SHOW TABLES;').splitlines()):
            require(re.fullmatch('[a-zA-Z0-9_]+', table), 'Unexpected table identifier')
            self.sql(env, 'DESCRIBE `' + table + '`;')
            definition = self.sql(env, 'SHOW CREATE TABLE `' + table + '`;').split('\t', 1)[1]
            # MySQL dump/restore can make an implicit column charset explicit.
            # COLLATE uniquely identifies that charset; preserve the collation
            # and compare column metadata as well, rather than raw DDL spelling.
            definition = re.sub(r' CHARACTER SET [a-zA-Z0-9_]+(?= COLLATE [a-zA-Z0-9_]+)', '', definition)
            columns = self.sql(env, "SELECT COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COALESCE(COLUMN_DEFAULT,'<NULL>'),COALESCE(CHARACTER_SET_NAME,''),COALESCE(COLLATION_NAME,''),EXTRA,GENERATION_EXPRESSION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='release_app' AND TABLE_NAME='" + table + "' ORDER BY ORDINAL_POSITION;")
            definitions[table] = dict(ddl=re.sub(r'AUTO_INCREMENT=\d+', 'AUTO_INCREMENT=<business-sequence>', definition), columns=columns)
        images = {role:self.run(['docker', 'inspect', '--format', '{{.Image}}', self.prefix(env) + '-' + role]).decode().strip() for role in ('backend','frontend')}
        data = dict(releaseTag=registered['releaseTag'], images=images, schema=definitions, migrations=self.sql(env, 'SELECT migration_id,checksum,status FROM release_migration_history ORDER BY migration_id;'))
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def reset_rehearsal(self, job):
        prefix = self.prefix('rehearsal')
        evidence = self.root / ('rehearsal-reset-' + job['id'] + '.json')
        evidence.write_text(json.dumps(self.state['environments']['rehearsal'], indent=2), 'utf-8')
        for role in ('frontend', 'backend', 'db'):
            name = prefix + '-' + role
            owner = self.run(['docker', 'inspect', '--format', '{{index .Config.Labels "release-center"}}', name]).decode().strip()
            require(owner == self.c['applicationId'], 'Rehearsal container ownership differs')
        for role in ('frontend', 'backend', 'db'):
            self.run(['docker', 'rm', '-f', prefix + '-' + role])
        self.run(['docker', 'volume', 'rm', prefix + '-data'])
        self.run(['docker', 'network', 'rm', prefix])
        del self.state['environments']['rehearsal']
        self.save()
        self.log(job, 'Only registered isolated rehearsal removed; snapshot and original task evidence retained')

    def recovery(self, env, p, job):
        args = ['docker', 'exec', '-e', 'MYSQL_PWD=' + self.password, self.prefix(env) + '-db', 'mysqldump', '-uroot', '--single-transaction', '--set-gtid-purged=OFF', 'release_app']
        raw = self.run(args)
        path = self.root / 'recovery' / (env + '-' + job['id'] + '.sql')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        job['recoveryPoint'] = dict(path=str(path), sha256=digest(path), originFingerprint=job.get('originFingerprint'), releaseTag=self.state['environments'][env]['releaseTag'])
        self.log(job, env + ': write maintenance enabled and recovery snapshot created')
        return raw

    def prepare(self, p, job):
        source_env = job['payload'].get('source', 'prod')
        job.update(target='rehearsal', sourceEnv=source_env)
        require(source_env in ('prod', 'backup') and source_env in self.state['environments'], 'Selected origin environment missing')
        _, candidate_manifest = self.manifest(p['releaseTag'])
        self.step(job, 'audit-rehearsal-origin')
        self.audit_target(source_env, p, candidate_manifest)
        source = dict(self.state['environments'][source_env])
        baseline, manifest = self.manifest(source['releaseTag'])
        fingerprint = self.fingerprint(source_env)
        job['originFingerprint'] = fingerprint
        if 'rehearsal' in self.state['environments']:
            # The explicit prepare action rebuilds this owned resource while retaining
            # passed evidence, including a production rehearsal used by this release.
            for other in self.state['packages']:
                if other.get('activeRehearsal'):
                    require(self.active_rehearsal(other)['status'] == 'passed', 'Another pending rehearsal must be explicitly completed/reset')
            self.step(job, 'replace-isolated-environment', effects=True)
            self.reset_rehearsal(job)
        self.step(job, 'snapshot-origin')
        raw = self.run(['docker', 'exec', '-e', 'MYSQL_PWD=' + self.password, self.prefix(source_env) + '-db', 'mysqldump', '-uroot', '--single-transaction', '--set-gtid-purged=OFF', 'release_app'])
        snapshot = self.root / 'rehearsals' / (job['id'] + '.sql')
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes(raw)
        require(self.fingerprint(source_env) == fingerprint, 'Origin version/schema/ledger changed while snapshotting')
        record = dict(id=job['id'], source=source_env, originFingerprint=fingerprint, originReleaseTag=source['releaseTag'], packageSha256=p['packageSha256'], status='preparing', jobId=job['id'], snapshot=str(snapshot), snapshotSha256=digest(snapshot), createdAt=stamp())
        p.setdefault('rehearsals', []).append(record)
        p['activeRehearsal'] = record['id']
        p.setdefault('outcomes', {})['rehearsal'] = {}
        self.step(job, 'restore-isolated-origin', effects=True)
        self.db('rehearsal')
        require(not self.sql('rehearsal', 'SHOW TABLES;'), 'Rehearsal restore requires an empty database')
        self.sql('rehearsal', raw.decode('utf-8'))
        self.app_containers('rehearsal', manifest)
        self.state['environments']['rehearsal'] = dict(source, maintenance=False, port=self.c['ports']['rehearsal'], source=source_env, snapshotAt=stamp())
        if source_env == 'prod':
            p['baselineFingerprint'] = fingerprint
        require(self.fingerprint('rehearsal') == fingerprint, 'Copied baseline fingerprint differs')
        self.health('rehearsal', baseline['releaseTag'])
        record['status'] = 'ready'
        self.log(job, 'Isolated rehearsal restored from ' + source_env + ' DB and its original application images; passed origin evidence retained')


def main(executor_type=Executor):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text('utf-8-sig'))
    executor = executor_type(config)
    key = config['bridgeKey']

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, code, value):
            raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(raw)

        def handle_request(self):
            try:
                require(secrets.compare_digest(self.headers.get('X-Release-Key', ''), key), 'Authenticated Spug bridge required')
                if self.command == 'GET' and self.path == '/state':
                    return self.reply(200, executor.snapshot())
                if self.command == 'GET' and self.path == '/commits':
                    return self.reply(200, executor.commits())
                require(self.command == 'POST' and self.path.startswith('/actions/'), 'Route not found')
                size = int(self.headers.get('Content-Length', '0'))
                require(0 < size < 16384, 'Invalid body length')
                payload = json.loads(self.rfile.read(size))
                return self.reply(202, executor.submit(self.path.rsplit('/', 1)[-1], payload, self.headers.get('X-Release-Actor', 'unknown')))
            except (ValueError, RuntimeError) as exc:
                self.reply(409, dict(error=str(exc)))
            except Exception as exc:
                self.reply(500, dict(error=str(exc).replace(executor.password, '[REDACTED]')))

        do_GET = handle_request
        do_POST = handle_request

    ThreadingHTTPServer((config.get('listenHost', '127.0.0.1'), config.get('port', 18110)), Handler).serve_forever()


if __name__ == '__main__':
    main()
