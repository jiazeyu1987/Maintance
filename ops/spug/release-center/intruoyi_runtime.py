"""Pinned SSH transport and fail-closed runtime contract for registered IntRuoyi hosts.

This adapter never reads credentials out of a remote container. JSON responses contain
identities and hashes only. The independent agent performs target-side operations.
"""
import hashlib
import gzip
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import threading


class RuntimeBlocked(RuntimeError):
    pass


class RuntimeUncertain(RuntimeBlocked):
    remoteStatusUnknown = True


def require(condition, message):
    if not condition:
        raise RuntimeBlocked(message)


def gxp_release_mode(manifest):
    """The package freezes the source configuration; targets never choose a default."""
    mode = manifest.get('releaseSettings', {}).get('gxpAuditMode')
    require(mode in ('FORMAL', 'DEVELOPMENT_DISABLED'),
            'Release must explicitly capture FORMAL or DEVELOPMENT_DISABLED GxP mode')
    return mode


def gxp_migration_sql(manifest, migration, text):
    if migration.get('migrationId') == '20261026_gxp_audit_mode_config':
        return "SET @intruoyi_gxp_audit_initial_mode='" + gxp_release_mode(manifest) + "';\n" + text
    return text


def validate_gxp_runtime(state, expected_mode):
    require(expected_mode in ('FORMAL', 'DEVELOPMENT_DISABLED'), 'Invalid expected GxP release mode')
    require(state.get('gxpAuditMode') == expected_mode,
            'Running GxP mode differs from the release configuration')
    require(state.get('configuredGxpAuditMode') == expected_mode,
            'Persisted GxP mode differs from the release configuration')


WORKBENCH_MAINTENANCE_MIGRATIONS = frozenset({
    '20261009_system_workbench_visibility_context',
    '20261009_system_workbench_visibility_stable_keys',
})
WORKBENCH_S4_MAINTENANCE_MIGRATIONS = {
    '20261010_system_workbench_projection': '5f871809e326411bb81474d595107df0f6c9919452483050d8e82dc191bdc8d7',
    '20261011_system_workbench_projection_retention': 'f746f0bd2cc1c405ac66840d7acab1903cc11d743885e18a46476a8debe61c7a',
    '20261011_system_workbench_projection_history': '21227efe50649c3cc85bb17db34ea4b22917c9c8436ad5381dc7c0c49c9c45dd',
    '20261023_system_workbench_projection_check_identity': '84b43c989ff779b8304eb27ab63fd0cc5ef3efa455a2a9db3d8d0b043cf7d8cb',
    '20261023_system_workbench_retention_check_identity': '68c1f172aac414e74d947dfcf46920560e83c38b23e6d46b3642d485f19a4c38',
    '20261023_system_workbench_history_check_identity': '2a278c5bb250aab2b8661e77a5581fa83004012f7c414d775dd2460afb6873c1',
}
ROUTE_SNAPSHOT_MIGRATION = '20260812_mes_route_version_snapshot_identity_enforce'
ROUTE_SNAPSHOT_SHA256 = '1cd2f6c77346c10c6ebfda2a8b5f5ed5686deac7d7a17212f9560c875e21a236'
ROUTE_SNAPSHOT_HOOK = 'route-snapshot-identity-v1'
ROUTE_LEGACY_MIGRATION = '20261023_mes_route_snapshot_legacy_summary_enforce'
ROUTE_LEGACY_SHA256 = '8668832bc8a52de84b39f451c0324c821e95b073a52c668f3bdbf6491fe30a7a'
ROUTE_LEGACY_HOOK = 'route-snapshot-identity-v2'
ROUTE_SNAPSHOT_HOOKS = frozenset({ROUTE_SNAPSHOT_HOOK, ROUTE_LEGACY_HOOK})
LEGACY_FORM_SWITCH_MIGRATION = '20260829_mes_old_form_template_binding_switch'
LEGACY_FORM_SWITCH_SHA256 = 'aa6797eddcf1d0331bad1516a0e1b1a85b10ba992d3c757b41e2858fb14917db'


def bind_reviewed_session_profile(migration):
    """Declare the reviewed S4 session contract without changing immutable SQL."""
    if migration.get('migrationId') in WORKBENCH_S4_MAINTENANCE_MIGRATIONS:
        require(migration.get('sessionProfile', '') in ('', 'workbench-s4-maintenance'),
                'Conflicting reviewed S4 session profile: '+migration['migrationId'])
        migration['sessionProfile'] = 'workbench-s4-maintenance'
        validate_migration_handler(migration)


def validate_migration_handler(migration):
    """Only reviewed S3/S4 identities may set their specific maintenance variable."""
    mid = migration.get('migrationId')
    if mid == LEGACY_FORM_SWITCH_MIGRATION:
        require(migration.get('sha256') == LEGACY_FORM_SWITCH_SHA256, 'Reviewed legacy form conversion bytes changed')
    hook = migration.get('approvedHook', '')
    if mid == ROUTE_SNAPSHOT_MIGRATION:
        require(migration.get('sha256') == ROUTE_SNAPSHOT_SHA256 and hook == ROUTE_SNAPSHOT_HOOK,
                'Reviewed route snapshot migration identity and hook required')
    elif mid == ROUTE_LEGACY_MIGRATION:
        require(migration.get('sha256') == ROUTE_LEGACY_SHA256 and hook == ROUTE_LEGACY_HOOK and
                migration.get('supersedes') == [ROUTE_SNAPSHOT_MIGRATION] and
                migration.get('type') == 'schema' and migration.get('requiresTargetPreflight') is True and
                isinstance(migration.get('dependsOn'), list) and
                {'20260812_mes_route_version_snapshot_identity', '20260718_controlled_content_lifecycle'} <= set(migration['dependsOn']),
                'Reviewed legacy summary migration identity, hook and exact supersession required')
    else:
        require(not hook, 'Special migration hook requires a reviewed handler: '+str(mid))
    profile = migration.get('sessionProfile', '')
    expected = 'workbench-s3-maintenance' if mid in WORKBENCH_MAINTENANCE_MIGRATIONS else ''
    if mid in WORKBENCH_S4_MAINTENANCE_MIGRATIONS:
        require(migration.get('sha256') == WORKBENCH_S4_MAINTENANCE_MIGRATIONS[mid],
                'Reviewed S4 migration bytes changed: '+str(mid))
        expected = 'workbench-s4-maintenance'
    require(profile == expected, 'Unsupported or missing migration session profile: '+str(mid))
    return profile


def migration_execution_sql(migration, text, maintenance_ready=False):
    profile = validate_migration_handler(migration)
    if profile:
        require(maintenance_ready is True, 'Workbench migration requires stopped writers and a completed recovery snapshot')
        statement = {'workbench-s3-maintenance': 'SET @profile_workbench_s3_maintenance=1;\n',
                     'workbench-s4-maintenance': 'SET @profile_workbench_s4_maintenance=1;\n'}[profile]
        return statement+text
    return text


def validate_snapshot_cli_report(report, expected, exit_code):
    """Consume only the reviewed non-data report, never process output or SQL text."""
    require(isinstance(report, dict), 'Route snapshot CLI report must be an object')
    fields = {'schemaVersion', 'releaseTag', 'migrationId', 'imageId', 'operationId', 'packageIdentity',
              'targetDatabase', 'mode', 'status', 'scannedCount', 'updatedCount', 'blockerCount', 'blockers'}
    if report.get('status') == 'ERROR':
        error_fields = fields - {'scannedCount', 'updatedCount', 'blockerCount', 'blockers'} | {'errorCode'}
        require(set(report) in (error_fields, error_fields - {'targetDatabase'}) and exit_code == 3,
                'Route snapshot CLI error report differs from reviewed contract')
        require(report['schemaVersion'] == 'route-snapshot-migration/v1' and
                report['errorCode'] in ('DATABASE_COMMAND_FAILED', 'COMMAND_FAILED'), 'Invalid route snapshot CLI failure category')
        for key, value in expected.items():
            require(key == 'targetDatabase' and key not in report or report.get(key) == value,
                    'Route snapshot CLI error binding mismatch: '+key)
        return report
    require(set(report) == fields, 'Route snapshot CLI report fields differ from reviewed contract')
    require(report['schemaVersion'] == 'route-snapshot-migration/v1', 'Route snapshot CLI report schema mismatch')
    for key, value in expected.items():
        require(report.get(key) == value, 'Route snapshot CLI report binding mismatch: '+key)
    for key in ('scannedCount', 'updatedCount', 'blockerCount'):
        require(type(report[key]) is int and report[key] >= 0, 'Invalid route snapshot CLI report count: '+key)
    require(report['updatedCount'] <= report['scannedCount'], 'Route snapshot CLI updated count exceeds scan')
    require(isinstance(report['blockers'], list) and report['blockerCount'] == len(report['blockers']),
            'Route snapshot CLI blocker evidence count differs')
    for blocker in report['blockers']:
        require(isinstance(blocker, dict) and set(blocker) == {'routeVersionId', 'routeId', 'tenantId', 'reasonCode'},
                'Invalid route snapshot blocker fields')
        require(all(value is None or (type(value) is int and value >= 0)
                    for key, value in blocker.items() if key != 'reasonCode'), 'Invalid route snapshot blocker identity')
        require(isinstance(blocker['reasonCode'], str) and re.fullmatch('[A-Z][A-Z0-9_]{0,79}', blocker['reasonCode']),
                'Invalid route snapshot blocker reason code')
    require(report['status'] in ('READY', 'BLOCKED', 'ERROR') and
            exit_code == {'READY':0, 'BLOCKED':2, 'ERROR':3}[report['status']],
            'Route snapshot CLI exit status and report disagree')
    require(report['mode'] == 'BACKFILL' or report['updatedCount'] == 0, 'Read-only route snapshot mode reported writes')
    require(report['status'] == 'READY' or report['updatedCount'] == 0, 'Blocked route snapshot transaction reported writes')
    require(report['status'] != 'READY' or report['blockerCount'] == 0, 'Ready route snapshot report contains blockers')
    return report


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


DATABASE_SNAPSHOT_NAMES = ('recovery.sql', 'recovery.sql.gz')


def database_snapshot_path(root, record):
    path = Path(record.get('path', ''))
    require(path.parent == Path(root) and path.name in DATABASE_SNAPSHOT_NAMES,
            'Unregistered database recovery artifact')
    return path


def capture_sql_snapshot(args, path, timeout=3600):
    """Stream every SQL byte into gzip; no uncompressed temporary copy.

    A failed producer or compressor must not yield a usable recovery record.
    stderr can contain SQL/credentials and is deliberately not returned.
    """
    path = Path(path)
    require(path.name == 'recovery.sql.gz', 'Compressed snapshot filename required')
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    size = 0
    with os.fdopen(descriptor, 'wb') as raw:
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        expired = threading.Event()
        def abort():
            expired.set()
            if process.poll() is None:
                process.kill()
        timer = threading.Timer(timeout, abort)
        timer.start()
        try:
            # Level 1 prioritizes release latency over maximum compression.
            with gzip.GzipFile(filename='', mode='wb', compresslevel=1, fileobj=raw, mtime=0) as output:
                for block in iter(lambda: process.stdout.read(1024 * 1024), b''):
                    output.write(block)
                    size += len(block)
            require(process.wait() == 0 and not expired.is_set() and size > 0,
                    'Full database capture failed; applications remain stopped')
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()
    return dict(path=str(path), sha256=file_sha(path), encoding='gzip',
                uncompressedBytes=size, bytes=path.stat().st_size,
                includes=['data', 'schema', 'triggers', 'events', 'routines'])


def restore_sql_snapshot(path, args, timeout=3600):
    """Read the explicitly named historical SQL or new gzip artifact.

    gzip streams must be piped: passing GzipFile as subprocess stdin would
    pass its underlying *compressed* file descriptor to MySQL.
    """
    path = Path(path)
    require(path.name in DATABASE_SNAPSHOT_NAMES, 'Unregistered database recovery artifact')
    if path.name == 'recovery.sql':
        with path.open('rb') as source:
            result = subprocess.run(args, stdin=source, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, timeout=timeout)
        require(result.returncode == 0, 'Database restore failed; business remains closed')
        return
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    expired = threading.Event()
    def abort():
        expired.set()
        if process.poll() is None:
            process.kill()
    timer = threading.Timer(timeout, abort)
    timer.start()
    try:
        with gzip.open(str(path), 'rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                process.stdin.write(block)
        process.stdin.close()
        require(process.wait() == 0 and not expired.is_set(),
                'Database restore failed; business remains closed')
    finally:
        timer.cancel()
        if process.poll() is None:
            process.kill()
        process.wait()
        if not process.stdin.closed:
            process.stdin.close()


def runtime_config_snapshot(info):
    """Docker Mounts is an unordered observation; preserve every mount field."""
    mounts = sorted(info['Mounts'], key=lambda mount: (
        mount.get('Destination') or '', mount.get('Source') or '', mount.get('Type') or '',
        json.dumps(mount, sort_keys=True, separators=(',', ':'))))
    return {'Config': info['Config'], 'HostConfig': info['HostConfig'],
            'Mounts': mounts, 'Networks': sorted(info['NetworkSettings']['Networks'])}


def package_identity(manifest):
    """Runtime evidence is job metadata, never part of the immutable release package."""
    return sha({key: value for key, value in manifest.items()
                if key not in ("baselines", "executionPlans", "expectedSchemaSha256")})


def validate_release_state(state, tag, maintenance):
    require(state.get('status') == 'available', 'Backend release status is not available')
    require(state.get('releaseTag') == tag and state.get('maintenance') is maintenance, 'Backend release/maintenance mismatch')
    if maintenance:
        require(state.get('schedulingDisabled') is True and state.get('consumersDisabled') is True,
                'Backend scheduling/consumer controls are not disabled')


def validate_expected_schema(environment, expected_schema):
    if environment in ('prod', 'backup') or expected_schema is not None:
        require(isinstance(expected_schema, str) and re.fullmatch('[0-9a-f]{64}', expected_schema),
                'Accepted production baseline rehearsal schema fingerprint required before formal target upgrade')


def migration_id(item):
    value = item.get('migrationId')
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.-]+', value), 'Invalid migrationId')
    return value


def audit_ledger(obs, manifest):
    """Validate actual IntRuoyi history; repeated identical applied evidence is allowed.

    Exclusion statuses are historical evidence, never proof a migration was applied.
    Unknown/failed/running/conflicting records block; nothing registers past SQL.
    """
    known = {}
    migrations = manifest.get('migrations')
    require(isinstance(migrations, list), 'Manifest migrations required')
    history = manifest.get('initialBaseline', {}).get('ledgerRecords', [])
    for item in migrations + manifest.get('knownMigrations', []) + history:
        mid = migration_id(item)
        checksum = item.get('sha256')
        require(isinstance(checksum, str) and re.fullmatch('[0-9a-f]{64}', checksum), 'Invalid migration SHA256: ' + mid)
        require(mid not in known or known[mid] == checksum, 'Conflicting manifest migration identity: ' + mid)
        known[mid] = checksum
    applied = set()
    records = obs.get('ledgerRecords', obs.get('ledger'))
    require(isinstance(records, list), 'Observed infra_release_migration ledger required')
    skipped = {'SKIPPED_ENV_NOT_ALLOWED', 'SKIPPED_SCOPE_EXCLUDED', 'SKIPPED_IMMUTABLE'}
    for row in records:
        mid = migration_id(row)
        require(mid in known, 'Unknown target migration: ' + mid)
        require(row.get('sha256') == known[mid], 'Target migration checksum conflict: ' + mid)
        status = row.get('status')
        require(status in {'APPLIED', 'SKIPPED_ALREADY_APPLIED'} | skipped,
                'Unresolved target migration status: ' + mid + '/' + str(status))
        if status in {'APPLIED', 'SKIPPED_ALREADY_APPLIED'}:
            applied.add(mid)
    missing = [item for item in migrations if migration_id(item) not in applied]
    require(len({migration_id(m) for m in migrations}) == len(migrations), 'Duplicate manifest migrationId')
    return {'applied': sorted(applied), 'missing': [migration_id(m) for m in missing],
            'ledgerSha256': sha(records), 'recordCount': len(records)}


def validate_storage_budget(profile, free_bytes):
    minimum = profile.get('minimumStagingFreeBytes')
    require(isinstance(minimum, int) and not isinstance(minimum, bool) and minimum > 0,
            'Explicit staging/recovery free-space budget required')
    require(free_bytes >= minimum, 'Insufficient staging/recovery space before stopping writers: freeBytes='
            + str(free_bytes) + ', requiredBytes=' + str(minimum))


def rehearsal_profile(config, source):
    require(source in ('test', 'prod', 'backup'), 'Explicit rehearsal origin required')
    roots = config.get('rehearsalStagingRoots')
    require(isinstance(roots, dict) and set(roots) <= {'test', 'prod', 'backup'} and source in roots,
            'Separate registered rehearsal staging roots required for the selected source')
    for path in roots.values():
        require(isinstance(path, str) and path.startswith('/') and '..' not in PurePosixPath(path).parts,
                'Absolute rehearsal staging root required')
    require(len(set(roots.values())) == len(roots), 'Rehearsal origins cannot share staging evidence directories')
    profile = dict(config['targets']['rehearsal'])
    for env, other in config['targets'].items():
        if env != 'rehearsal' and other['host'] == profile['host']:
            require(other['stagingRoot'] not in roots.values(), 'Rehearsal staging conflicts with a deployed target')
    # rehearsal-restore creates these two owned volumes at /data. Keep the
    # recovery inventory beside the generated profile so upgrade preflight
    # never depends on an operator guessing the generated mount destinations.
    mounts=[dict(role='redis',destination='/data'),dict(role='minio',destination='/data')]
    if 'recoveryDataMounts' in profile:
        require(profile['recoveryDataMounts']==mounts, 'Rehearsal recovery inventory conflicts with generated volumes')
    if 'recoveryInventoryConfirmed' in profile:
        require(profile['recoveryInventoryConfirmed'] is True, 'Generated rehearsal recovery inventory must be confirmed')
    return dict(profile, sourceEnvironment=source, stagingRoot=roots[source],
                recoveryInventoryConfirmed=True,recoveryDataMounts=mounts)


def validate_quiescence_recovery(record, payload, observation):
    require(record.get('recoveryKind') in ('no-migrations-started', 'capture-not-sealed') and record.get('restored') is True
            and record.get('snapshotComplete') is False, 'Explicit incomplete-snapshot recovery evidence required')
    require(record.get('jobId') == payload.get('jobId'), 'Recovery belongs to another task')
    require(record.get('restoredFingerprint') == payload.get('originFingerprint') == observation.get('fingerprint'),
            'Original schema/ledger/images/runtime fingerprint differs')
    identities = record.get('originalContainerIds', {})
    require(set(identities) == {'backend', 'frontend', 'database'} and all(
        identities[role] == observation.get('components', {}).get(role, {}).get('containerId') for role in identities),
        'Original application/database containers differ')


class Runtime:
    def __init__(self, config):
        import threading
        self.operation_context = threading.local()
        self.config = config
        require(isinstance(config.get('targets'), dict), 'Explicit registered targets required')
        self.targets = config['targets']
        self.sources = Path(__file__).resolve().parent

    def profile(self, env):
        require(env in self.targets, 'Unregistered IntRuoyi target: ' + env)
        profile = dict(self.targets[env])
        context = getattr(getattr(self, 'operation_context', None), 'binding', None)
        if context:
            selected_root = context[0].get('runtimeStagingRoots', {}).get(env)
            if selected_root:
                expected_root = PurePosixPath(profile['stagingRoot']) / 'attempts'
                require(PurePosixPath(selected_root).parent == expected_root
                        and re.fullmatch(r'JOB-[a-f0-9]{10}', PurePosixPath(selected_root).name),
                        'Retry staging root is outside the registered target')
                profile['stagingRoot'] = selected_root
        for key in ('host', 'python', 'entryUrl', 'frontend', 'backend', 'database'):
            require(isinstance(profile.get(key), str) and profile[key], 'Registered target missing ' + key)
        require(re.fullmatch(r'[A-Za-z0-9.-]+', profile['host']), 'Invalid registered SSH host')
        require(re.fullmatch(r'[/A-Za-z0-9_.-]+', profile['python']), 'Invalid remote Python')
        for key in ('frontend', 'backend', 'database'):
            require(re.fullmatch(r'[A-Za-z0-9_.-]+', profile[key]), 'Invalid registered container name')
        return profile

    def ssh_options(self):
        # System/user SSH configs cannot silently redirect a registered target.
        options = ['-F', 'NUL' if os.name == 'nt' else '/dev/null', '-o', 'BatchMode=yes',
                   '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10']
        if self.config.get('executionMode') == 'windows-service':
            identity, hosts = self.config.get('sshIdentityFile'), self.config.get('sshKnownHostsFile')
            require(identity and hosts and Path(identity).is_file() and Path(hosts).is_file(),
                    'Windows service requires explicit SSH identity and known-hosts files')
            options += ['-i', identity, '-o', 'IdentitiesOnly=yes', '-o', 'UserKnownHostsFile='+hosts]
        return options

    def call(self, env, action, **arguments):
        import secrets
        context = getattr(getattr(self, 'operation_context', None), 'binding', None)
        if context and action != 'inspect-operation':
            job, persist = context
            operation = dict(operationId='OP-' + secrets.token_hex(10), env=env, action=action)
            job.setdefault('remoteOperations', []).append(operation)
            persist()
            arguments.update(operationId=operation['operationId'], workflowJobId=job['id'])
        uncertain_on_disconnect = action in ('frontend-patch-deploy','frontend-patch-restore','deploy', 'maintenance', 'recover-release', 'accept-recovery', 'resume-test-deployment-tail', 'rehearsal-capture', 'rehearsal-restore', 'rehearsal-resume-tail', 'rehearsal-reset')
        profile = self.profile(env)
        payload = json.dumps({'action': action, 'profile': profile, **arguments}, ensure_ascii=True)
        inspector = (self.sources / 'intruoyi_remote.py').read_text('utf-8')
        agent = (self.sources / 'intruoyi_runtime_agent.py').read_text('utf-8')
        contract = Path(__file__).read_text('utf-8')
        rehearsal = (self.sources / 'intruoyi_rehearsal_agent.py').read_text('utf-8')
        recovery = (self.sources / 'intruoyi_recovery_agent.py').read_text('utf-8')
        journal = (self.sources / 'operation_journal.py').read_text('utf-8')
        artifacts = (self.sources / 'artifact_files.py').read_text('utf-8')
        frontend_patch = (self.sources / 'frontend_patch_agent.py').read_text('utf-8')
        source = ('import types,sys\n'
                  '_patch=types.ModuleType("frontend_patch_agent")\n'
                  'sys.modules["frontend_patch_agent"]=_patch\n'
                  'exec(compile(' + repr(frontend_patch) + ',"frontend_patch_agent.py","exec"),_patch.__dict__)\n'
                  '_artifacts=types.ModuleType("artifact_files")\n'
                  'sys.modules["artifact_files"]=_artifacts\n'
                  'exec(compile(' + repr(artifacts) + ',"artifact_files.py","exec"),_artifacts.__dict__)\n'
                  '_journal=types.ModuleType("operation_journal")\n'
                  'sys.modules["operation_journal"]=_journal\n'
                  'exec(compile(' + repr(journal) + ',"operation_journal.py","exec"),_journal.__dict__)\n'
                  '_remote=types.ModuleType("intruoyi_remote")\n'
                  'sys.modules["intruoyi_remote"]=_remote\n'
                  'exec(compile(' + repr(inspector) + ',"intruoyi_remote.py","exec"),_remote.__dict__)\n'
                  '_contract=types.ModuleType("intruoyi_runtime")\n'
                  'sys.modules["intruoyi_runtime"]=_contract\n'
                  'exec(compile(' + repr(contract) + ',"intruoyi_runtime.py","exec"),_contract.__dict__)\n'
                  '_rehearsal=types.ModuleType("intruoyi_rehearsal_agent")\n'
                  'sys.modules["intruoyi_rehearsal_agent"]=_rehearsal\n'
                  'exec(compile(' + repr(rehearsal) + ',"intruoyi_rehearsal_agent.py","exec"),_rehearsal.__dict__)\n'
                  '_recovery=types.ModuleType("intruoyi_recovery_agent")\n'
                  'sys.modules["intruoyi_recovery_agent"]=_recovery\n'
                  'exec(compile(' + repr(recovery) + ',"intruoyi_recovery_agent.py","exec"),_recovery.__dict__)\n'
                  'PAYLOAD=' + repr(payload) + '\n' + agent)
        try:
            proc = subprocess.run(['ssh', *self.ssh_options(), 'root@' + profile['host'],
                               shlex.quote(profile['python']) + ' -'], input=source.encode('utf-8'),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=self.config.get('rehearsalOperationTimeout', 21600)
                              if action in ('rehearsal-capture', 'rehearsal-restore')
                              else max(1800, self.config.get('operationTimeout', 3600)) if action == 'resume-test-deployment-tail'
                              else self.config.get('operationTimeout', 3600))
        except subprocess.TimeoutExpired:
            if uncertain_on_disconnect:
                raise RuntimeUncertain('Client wait timed out; remote '+action+' outcome must be verified using the original task ID') from None
            raise RuntimeBlocked('Remote '+action+' response timed out') from None
        if proc.returncode != 0 and uncertain_on_disconnect:
            raise RuntimeUncertain('SSH disconnected; remote '+action+' outcome is unconfirmed. Do not replay the task')
        require(proc.returncode == 0, 'Remote ' + action + ' failed on registered ' + env + '; exit=' + str(proc.returncode))
        try:
            response = json.loads(proc.stdout)
        except (ValueError, UnicodeError) as exc:
            if uncertain_on_disconnect:
                raise RuntimeUncertain('Remote '+action+' returned invalid JSON; effects require investigation') from exc
            raise RuntimeBlocked('Remote operation returned invalid JSON') from exc
        if not isinstance(response, dict) or type(response.get('ok')) is not bool or (response.get('ok') and 'result' not in response):
            failure = RuntimeUncertain if uncertain_on_disconnect else RuntimeBlocked
            raise failure('Remote '+action+' returned an incomplete response; outcome cannot be confirmed')
        require(response.get('ok') is True, response.get('error', 'Remote operation refused'))
        return response['result']

    def observe(self, env):
        return self.call(env, 'observe')

    def dependencies(self, env):
        return self.call(env, 'dependencies')

    def fingerprint(self, env):
        obs = self.observe(env)
        return sha({key: obs[key] for key in ('images', 'schemaSha256', 'ledgerSha256', 'runtimeConfigSha256')})

    def audit(self, env, manifest):
        obs = self.observe(env)
        result = audit_ledger(obs, manifest)
        baseline = manifest.get('baselines', {}).get(env, manifest.get('baseline', manifest.get('initialBaseline')))
        require(isinstance(baseline, dict), 'Explicit baseline identity required for ' + env)
        for key in ('schemaSha256', 'ledgerSha256', 'images'):
            require(key in baseline and obs[key] == baseline[key], 'Registered baseline mismatch: ' + env + '/' + key)
        return {'observation': obs, 'migrationAudit': result}

    def preflight(self, env, manifest):
        audit = self.audit(env, manifest)
        require(not any(audit['observation']['readOnly'].values()), 'Target has read_only/super_read_only protection; do not release another task fence')
        audit['remotePreflight'] = self.call(env, 'preflight', manifest=manifest)
        return audit

    def stage(self, env, packageDirectory, manifest):
        root = Path(packageDirectory).resolve()
        require(root.is_dir(), 'Release package directory missing')
        profile = self.profile(env)
        tag = manifest.get('releaseTag', '')
        require(re.fullmatch(r'\d{4}(-\d{2}){5}', tag), 'Invalid release tag')
        staging = profile.get('stagingRoot')
        require(isinstance(staging, str) and staging.startswith('/') and '..' not in PurePosixPath(staging).parts,
                'Explicit absolute remote stagingRoot required')
        remote = str(PurePosixPath(staging) / tag)
        files = manifest.get('files')
        require(isinstance(files, list) and files, 'Manifest package files required')
        validated = []
        preflight_contract_path = self.sources.parents[1] / 'release/release_target_preflight_contract.py'
        spec = importlib.util.spec_from_file_location('intruoyi_existing_readonly_contract', preflight_contract_path)
        readonly_contract = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(readonly_contract)
        checked_preflights = []
        for item in files:
            name = item.get('name', item.get('path', ''))
            require(re.fullmatch(r'[A-Za-z0-9_./-]+', name) and '..' not in PurePosixPath(name).parts and not name.startswith('/'), 'Unsafe package file')
            path = (root / name).resolve()
            require(root == path or root in path.parents, 'Package path escapes root')
            require(path.is_file(), 'Package file missing: ' + name)
            require(file_sha(path) == item['sha256'], 'Package file SHA mismatch: ' + name)
            validated.append({'name': name, 'sha256': item['sha256']})
            if name.endswith('.preflight.sql'):
                mid = path.name.removesuffix('.preflight.sql')
                readonly_contract.validate(path, mid)
                match = readonly_contract.METADATA_PATTERN.search(path.read_text('utf-8'))
                checked_preflights.append({'file': name, 'sha256': item['sha256'], 'migrationId': mid,
                                           'allowedEnvironments': match.group('environments').split(',')})
        archive = root / 'release.tar'
        manifest_path = root / 'manifest.json'
        require(archive.is_file() and manifest_path.is_file(), 'Original release.tar and manifest.json required')
        require(json.loads(manifest_path.read_text('utf-8')) == manifest, 'Original package manifest differs from staging request')
        archive_evidence = dict(sha256=file_sha(archive), manifestSha256=file_sha(manifest_path))
        prepared = self.call(env, 'stage-directory', directory=remote, files=validated, manifest=manifest,
                             archive=archive_evidence, validatedPreflights=checked_preflights)
        if prepared.get('reused') is True:
            require(prepared.get('verified') is True and prepared.get('manifestSha256') == package_identity(manifest)
                    and prepared.get('directory') == remote, 'Reused stage verification identity differs')
            return prepared
        destination = 'root@' + profile['host'] + ':' + shlex.quote(str(PurePosixPath(remote) / 'release.tar'))
        proc = subprocess.run(['scp', *self.ssh_options(), str(archive), destination],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3600)
        require(proc.returncode == 0, 'Pinned original package upload failed: release.tar')
        return self.call(env, 'verify-stage', directory=remote, files=validated, manifest=manifest,
                         archive=archive_evidence, validatedPreflights=checked_preflights)

    def deploy(self, env, manifest, jobcallback, job_id):
        jobcallback('check-executor-acceptance-ingress')
        self.check_acceptance_ingress(env)
        self.preflight(env, manifest)
        jobcallback('remote-deploy-starting-side-effects', effects=True)
        return self.call(env, 'deploy', manifest=manifest, jobId=job_id)

    def check_acceptance_ingress(self, env):
        from acceptance_probe import check
        return check(self, env)

    def resume_test_deployment_tail(self, env, manifest, original_plan, original_job_id, retry_job_id,
                                    package_sha256, manifest_sha256, jobcallback):
        require(env == 'test', 'Deployment tail continuation is restricted to test')
        jobcallback('resume-original-test-deployment-tail', effects=True)
        return self.call(env, 'resume-test-deployment-tail', manifest=manifest, originalPlan=original_plan,
                         originalJobId=original_job_id, retryJobId=retry_job_id,
                         packageSha256=package_sha256, manifestSha256=manifest_sha256)

    def health(self, env, tag):
        return self.call(env, 'health', releaseTag=tag)

    def maintenance(self, env, enabled):
        return self.call(env, 'maintenance', enabled=enabled)

    def prepare_rehearsal(self, source, manifest, jobcallback, job_id, verify_data=False):
        require(source in ('test', 'prod', 'backup'), 'Rehearsal source must be an explicitly registered target')
        require('rehearsal' in self.targets, 'Full-data rehearsal target/network/dependencies not registered; schema-only rehearsal forbidden')
        jobcallback('inspect-full-data-rehearsal-prerequisites')
        from intruoyi_rehearsal import prepare
        return prepare(self, source, manifest, jobcallback, job_id, verify_data=verify_data)

    def reset_rehearsal(self, jobcallback):
        from intruoyi_rehearsal import reset
        return reset(self, jobcallback)

    def resume_rehearsal_tail(self, source, manifest, original_job_id, retry_job_id, package_sha256,
                              manifest_sha256, expected_origin_fingerprint, jobcallback):
        from intruoyi_rehearsal import resume_tail
        return resume_tail(self, source, manifest, original_job_id, retry_job_id, package_sha256,
                           manifest_sha256, expected_origin_fingerprint, jobcallback)

    def resume_rehearsal_transfer(self, source, manifest, original_job_id, retry_job_id, package_sha256,
                                  manifest_sha256, expected_origin_fingerprint, jobcallback):
        from intruoyi_rehearsal import resume_transfer
        return resume_transfer(self, source, manifest, original_job_id, retry_job_id, package_sha256,
                               manifest_sha256, expected_origin_fingerprint, jobcallback)
