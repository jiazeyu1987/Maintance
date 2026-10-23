"""Remote-only IntRuoyi operations. Transport injects immutable source and JSON.

No credential-bearing Docker JSON, SQL output or stderr is returned to the caller.
Configuration snapshots and SQL recovery files stay mode0600 on the target.
"""
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import socket
import subprocess
import time
import tarfile
import io
from datetime import datetime, timezone
from urllib.parse import urlsplit, quote
from urllib.request import urlopen

import intruoyi_remote as remote
from intruoyi_runtime import audit_ledger, require, RuntimeBlocked, sha, migration_id, file_sha, package_identity, validate_release_state, validate_expected_schema, runtime_config_snapshot, validate_migration_handler, migration_execution_sql, validate_quiescence_recovery, validate_storage_budget, ROUTE_SNAPSHOT_MIGRATION, ROUTE_SNAPSHOT_HOOK, validate_snapshot_cli_report

PROTOCOL = 'intruoyi-quiescent-start-v1'


def private_json(path, value):
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(value, stream)


def check_fence(profile):
    fields = remote.sql(profile, 'SELECT @@global.read_only,@@global.super_read_only;').split('\t')
    require(fields == ['0', '0'], 'External read_only/super_read_only fence active; operation refused without changing protection')


def observe(profile):
    # Inspector performs SHOW TABLES/DESCRIBE before metadata/ledger queries.
    raw = remote.observe(profile)
    require(set(raw['migrationLedgers']) == {'infra_release_migration'}, 'Unexpected/missing IntRuoyi migration ledger')
    rows = remote.sql(profile, 'SELECT migration_id,sha256,status FROM infra_release_migration WHERE deleted=b\'0\' ORDER BY id;')
    ledger = []
    for row in rows.splitlines():
        fields = row.split('\t')
        require(len(fields) == 3, 'Malformed migration ledger identity')
        ledger.append(dict(zip(('migrationId', 'sha256', 'status'), fields)))
    readonly = remote.sql(profile, 'SELECT @@global.read_only,@@global.super_read_only;').split('\t')
    require(len(readonly) == 2 and all(v in ('0', '1') for v in readonly), 'Cannot determine database write protection')
    configs = {}
    for role in ('frontend', 'backend', 'database'):
        info = remote.inspect(profile[role])
        configs[role] = runtime_config_snapshot(info)
    backend_env = dict(v.split('=', 1) for v in remote.inspect(profile['backend'])['Config']['Env'])
    maintenance = backend_env.get('INTRUOYI_RELEASE_MAINTENANCE') == 'true'
    entry = profile.get('acceptanceUrl') if maintenance else profile['entryUrl']
    require(isinstance(entry, str) and entry, 'Maintenance observation requires registered acceptanceUrl')
    status, metadata_status, release_tag, backend_health = None, None, None, None
    metadata_error = None
    try:
        with urlopen(entry + '/', timeout=5) as response:
            status = response.status
    except Exception as error:
        status = getattr(error, 'code', None)
    try:
        with urlopen(entry + '/release-info.json', timeout=5) as response:
            metadata_status = response.status
            release_tag = json.load(response).get('releaseTag')
            require(isinstance(release_tag, str) and release_tag, 'Frontend releaseTag missing')
    except Exception as error:
        if metadata_status is None:
            metadata_status = getattr(error, 'code', None)
        metadata_error = type(error).__name__
    try:
        backend_addresses = [n['IPAddress'] for n in remote.inspect(profile['backend'])['NetworkSettings']['Networks'].values() if n.get('IPAddress')]
        require(len(backend_addresses) == 1, 'Backend health requires one explicit Docker IP')
        with urlopen('http://' + backend_addresses[0] + ':48081/actuator/health', timeout=5) as response:
            backend_health = {'status': json.load(response).get('status')}
    except Exception as error:
        backend_health = {'observationFailed': True, 'category': type(error).__name__}
    backend_env = dict(v.split('=', 1) for v in remote.inspect(profile['backend'])['Config']['Env'])
    images = {role: raw['components'][role]['imageId'] for role in ('backend', 'frontend')}
    fingerprint = sha({'images': images, 'schemaSha256': raw['schemaSha256'], 'ledgerSha256': sha(ledger), 'runtimeConfigSha256': sha(configs)})
    return dict(host=profile['host'], entryUrl=profile['entryUrl'], observedEntryUrl=entry, components=raw['components'],
                images={role: raw['components'][role]['imageId'] for role in ('backend', 'frontend')},
                schemaSha256=raw['schemaSha256'], ledger=ledger, ledgerSha256=sha(ledger),
                releaseTag=release_tag, ledgerRecords=ledger, imageIds=images, fingerprint=fingerprint,
                backendHealth=backend_health, frontendHttpStatus=status,
                metadataHTTPstatus=metadata_status, frontendObservationError=metadata_error,
                maintenance=maintenance,
                observedAt=datetime.now(timezone.utc).isoformat(),
                runtimeConfigSha256=sha(configs), databaseIdentity=raw['databaseIdentity'],
                readOnly=dict(zip(('read_only', 'super_read_only'), [v == '1' for v in readonly])),
                identityConflictCount=len(raw['identityConflicts'].splitlines()))


def dependencies(profile):
    result = {}
    for role in ('frontend', 'backend', 'database'):
        info = remote.inspect(profile[role])
        names = sorted(v.split('=', 1)[0] for v in info['Config']['Env'])
        networks = {}
        for name in info['NetworkSettings']['Networks']:
            net = json.loads(remote.run(['docker', 'network', 'inspect', name]))[0]
            networks[name] = {'internal': net['Internal'], 'containers': sorted(v['Name'] for v in net.get('Containers', {}).values())}
        result[role] = dict(envNames=names, mounts=[{k: m.get(k) for k in ('Type', 'Source', 'Destination', 'RW')} for m in info['Mounts']],
                            networks=networks, portBindings=info['HostConfig']['PortBindings'],
                            commandSha256=sha({'Entrypoint': info['Config']['Entrypoint'], 'Cmd': info['Config']['Cmd']}))
    return result


class DockerConnection(http.client.HTTPConnection):
    def __init__(self):
        super().__init__('localhost', timeout=180)
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect('/var/run/docker.sock')


def docker(method, path, value=None):
    connection = DockerConnection()
    try:
        connection.request(method, path, None if value is None else json.dumps(value), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read()
        require(response.status < 300, 'Docker API operation refused; HTTP=' + str(response.status))
        return json.loads(raw) if raw else None
    finally:
        connection.close()


def directory(profile, tag):
    require(isinstance(tag, str) and re.fullmatch(r'\d{4}(-\d{2}){5}', tag), 'Invalid releaseTag')
    base = profile.get('stagingRoot')
    require(isinstance(base, str) and base.startswith('/') and '..' not in Path(base).parts, 'Explicit stagingRoot required')
    return Path(base) / tag


def verify_files(root, files):
    for item in files:
        name = item['name']
        path = (root / name).resolve()
        require(root.resolve() in path.parents and path.is_file(), 'Staged artifact missing or unsafe')
        digest = file_sha(path)
        require(digest == item['sha256'], 'Staged artifact SHA256 mismatch: ' + name)


def unpack_original_package(root, manifest, evidence):
    """Verify the original transport archive; never extract links or arbitrary members."""
    archive_path = root / 'release.tar'
    require(not root.is_symlink() and archive_path.is_file() and not archive_path.is_symlink(),
            'Original release archive missing or unsafe')
    for key in ('sha256', 'manifestSha256'):
        require(isinstance(evidence.get(key), str) and re.fullmatch('[0-9a-f]{64}', evidence[key]),
                'Original archive and manifest checksums required')
    require(file_sha(archive_path) == evidence['sha256'], 'Original release archive checksum mismatch')
    expected = {'manifest.json': evidence['manifestSha256']}
    for item in manifest['files']:
        name = item['name']
        require(isinstance(name, str) and re.fullmatch('[A-Za-z0-9_./-]+', name)
                and name == PurePosixPath(name).as_posix() and not name.startswith('/')
                and '..' not in PurePosixPath(name).parts and name not in ('manifest.json', 'release.tar'),
                'Unsafe original package member')
        require(name not in expected, 'Duplicate manifest member: ' + name)
        require(re.fullmatch('[0-9a-f]{64}', item['sha256']), 'Invalid artifact checksum')
        expected[name] = item['sha256']
    require(not any(str(parent) in expected for name in expected for parent in PurePosixPath(name).parents
                    if str(parent) != '.'), 'Package file/directory member conflict')
    with tarfile.open(archive_path, 'r:') as archive:
        members = archive.getmembers()
        names = [item.name for item in members]
        require(len(names) == len(set(names)) and set(names) == set(expected),
                'Archive member list differs from the original manifest')
        require(all(item.isfile() and not item.issparse() for item in members),
                'Original archive must contain only regular non-sparse files; links and special members refused')
        manifest_member = archive.getmember('manifest.json')
        require(manifest_member.size <= 16 * 1024 * 1024, 'Original manifest exceeds bounded metadata size')
        manifest_bytes = archive.extractfile(manifest_member).read()
        require(hashlib.sha256(manifest_bytes).hexdigest() == evidence['manifestSha256']
                and json.loads(manifest_bytes) == manifest, 'Archive manifest identity differs from staging request')
        # All member identities/types are checked before writing any extracted file.
        for member in members:
            destination = root / member.name
            require(root.resolve() in destination.resolve().parents, 'Archive destination escapes staging root')
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            require(all(not parent.is_symlink() for parent in destination.parents if parent == root or root in parent.parents),
                    'Archive destination contains a link')
            checksum = hashlib.sha256()
            descriptor = os.open(str(destination), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as output, archive.extractfile(member) as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    checksum.update(chunk)
                    output.write(chunk)
            require(checksum.hexdigest() == expected[member.name], 'Archive artifact checksum mismatch: ' + member.name)
    return {'archiveSha256': evidence['sha256'], 'manifestSha256': evidence['manifestSha256'], 'fileCount': len(members)}


def migration_plan(profile, manifest, obs):
    audit = audit_ledger(obs, manifest)
    environment = profile.get('environment')
    effective_environment = profile.get('sourceEnvironment', environment)
    require(environment in ('test', 'prod', 'backup', 'rehearsal'), 'Explicit target environment required')
    planned = manifest.get('executionPlans', {}).get(environment)
    require(isinstance(planned, dict) and planned.get('status') == 'passed', 'Passed per-target IntRuoyi executionPlan missing')
    require(planned.get('targetEnvironment') == profile.get('sourceEnvironment', environment), 'Execution plan targets another environment')
    plan = planned.get('items')
    require(isinstance(plan, list), 'Audited executionPlan items missing')
    executable = {migration_id(m) for m in manifest['migrations'] if m.get('type') in ('schema', 'data', 'menu', 'config', 'permission', 'seed')}
    require(set(audit['missing']) & executable <= {entry.get('migrationId') for entry in plan}, 'Execution plan must explain each missing executable migration')
    require(len({e.get('migrationId') for e in plan}) == len(plan), 'Duplicate execution plan migration')
    known = {migration_id(m): m for m in manifest['migrations']}
    completed = set(audit['applied'])
    for entry in plan:
        mid = entry['migrationId']
        require(mid in known, 'Execution plan contains unknown migration')
        source = known[mid]
        action = entry.get('action')
        require(mid in known, 'Execution plan contains unknown migration')
        require(action in ('APPLY', 'SKIP_ALREADY_APPLIED', 'SKIP_ENV_NOT_ALLOWED', 'SKIP_SCOPE_EXCLUDED', 'SKIP_IMMUTABLE'), 'Unrecognized migration action: ' + mid)
        if action == 'SKIP_ALREADY_APPLIED':
            require(mid in completed, 'Migration claimed already applied without ledger proof: ' + mid)
        elif action == 'SKIP_ENV_NOT_ALLOWED':
            require(effective_environment not in source.get('allowedEnvironments', []), 'Invalid environment exclusion: ' + mid)
        elif action == 'SKIP_SCOPE_EXCLUDED':
            scopes = source.get('allowedPublishScopes', [])
            require(scopes and manifest.get('publishScope') not in scopes, 'Unexplained publish-scope exclusion: ' + mid)
        elif action == 'SKIP_IMMUTABLE':
            successors = [m for m in manifest['migrations'] if mid in m.get('supersedes', [])]
            require(successors and all(migration_id(m) in completed or any(e.get('migrationId') == migration_id(m) and e.get('action') == 'APPLY' for e in plan) for m in successors), 'Unexplained superseded migration: ' + mid)
        else:
            require(source.get('type') in ('schema', 'data', 'menu', 'config', 'permission', 'seed'), 'Evidence-only SQL cannot be executed as application migration')
            require(mid not in audit['applied'], 'Applied migration cannot be replayed')
            require(effective_environment in source.get('allowedEnvironments', []), 'Migration environment not allowed: ' + mid)
            validate_migration_handler(source)
            dependencies = {next((migration_id(m) for m in manifest['migrations'] if dep in m.get('supersedes', [])), dep) for dep in source.get('dependsOn', [])}
            require(dependencies <= completed, 'Migration dependency not applied before: ' + mid)
            require(not (source.get('requiresTargetPreflight') or source.get('type') != 'schema') or isinstance(entry.get('targetPreflight'), dict), 'Required target preflight missing: ' + mid)
            if entry.get('targetPreflight') is not None:
                require(entry['targetPreflight'] == source.get('targetPreflight'), 'Target preflight differs from immutable manifest: ' + mid)
            completed.add(mid)
    return plan


def acceptance_spec(profile):
    network = profile.get('acceptanceNetwork')
    require(isinstance(network, str) and re.fullmatch('[A-Za-z0-9_.-]+', network), 'Explicit acceptanceNetwork required before any application is stopped')
    net = json.loads(remote.run(['docker', 'network', 'inspect', network]))[0]
    require(net.get('Driver') == 'bridge', 'Acceptance network must be a registered bridge network')
    backend = remote.inspect(profile['backend'])
    addresses = [entry['IPAddress'] for entry in backend['NetworkSettings']['Networks'].values() if entry.get('IPAddress')]
    require(len(addresses) == 1 and network in backend['NetworkSettings']['Networks'], 'Acceptance network must reach the uniquely addressed backend')
    archive = remote.run(['docker', 'cp', profile['frontend'] + ':/etc/nginx/conf.d/default.conf', '-'])
    with tarfile.open(fileobj=io.BytesIO(archive)) as contents:
        members = [entry for entry in contents if entry.isfile()]
        require(len(members) == 1, 'Cannot identify exact frontend nginx configuration')
        nginx = contents.extractfile(members[0]).read().decode('utf-8')
    # Public host-network nginx may contain several independent HTTP servers.
    # The acceptance instance exposes only the registered public application's server.
    blocks = []
    for start in re.finditer(r'(?m)^\s*server\s*\{', nginx):
        opening = nginx.index('{', start.start())
        depth, ending = 1, opening + 1
        while ending < len(nginx) and depth:
            depth += (nginx[ending] == '{') - (nginx[ending] == '}')
            ending += 1
        require(depth == 0, 'Nginx server block is unbalanced')
        blocks.append(nginx[start.start():ending])
    public_port = 80 if profile.get('environment') == 'rehearsal' else (urlsplit(profile['entryUrl']).port or 80)
    selected = [block for block in blocks if re.search(r'\blisten\s+(?:[0-9.]+:)?' + str(public_port) + r'(?:\s|;)', block)]
    require(len(selected) == 1, 'Cannot identify unique public nginx server for registered entryUrl')
    nginx = selected[0]
    allowed = {addresses[0], '127.0.0.1', 'localhost', profile['host'], profile['backend']}
    replaced = [0]
    def upstream(match):
        host = match.group(1)
        require(host in allowed, 'Nginx backend upstream is not registered; acceptance configuration refused')
        replaced[0] += 1
        return 'http://' + addresses[0] + ':48081'
    nginx = re.sub(r'http://([A-Za-z0-9_.-]+):48081', upstream, nginx)
    require(replaced[0] > 0, 'No explicit registered backend :48081 upstream in nginx configuration')
    nginx, listens = re.subn(r'(?m)(\blisten\s+)(?:[0-9.]+:)?[0-9]+(\s*(?:default_server)?\s*;)', r'\g<1>80\2', nginx)
    require(listens > 0 and not re.search(r'\blisten\s+\[', nginx), 'Acceptance nginx listen configuration is unsupported')
    seen_listeners = set()
    def unique_listener(match):
        value = match.group(0)
        if value in seen_listeners:
            return ''
        seen_listeners.add(value)
        return value
    nginx = re.sub(r'\blisten\s+80\s*(?:default_server)?\s*;', unique_listener, nginx)
    return {'network': network, 'backendIp': addresses[0], 'nginx': nginx}


def check_storage(profile):
    base = Path(profile['stagingRoot'])
    require(base.is_absolute() and base.is_dir(), 'Registered staging filesystem directory must exist')
    filesystem = os.statvfs(str(base))
    validate_storage_budget(profile, filesystem.f_bavail * filesystem.f_frsize)


def preflight(profile, manifest):
    check_fence(profile)
    check_storage(profile)
    require(manifest.get('maintenanceProtocol') == PROTOCOL, 'Candidate lacks verified IntRuoyi quiescent startup protocol')
    writers = profile.get('writers')
    require(profile.get('writerInventoryConfirmed') is True and isinstance(writers, list) and profile['backend'] in writers,
            'All database/background writer containers must be explicitly registered and confirmed')
    for name in writers + [profile['frontend']]:
        require(re.fullmatch('[A-Za-z0-9_.-]+', name), 'Invalid registered writer')
        require(remote.inspect(name)['State']['Running'], 'Registered writer is not running; investigate current state')
    url = urlsplit(profile.get('acceptanceUrl', ''))
    require(url.scheme == 'http' and url.hostname == profile['host'] and url.port and url.port != urlsplit(profile['entryUrl']).port,
            'Explicit separate registered acceptanceUrl required')
    require(profile.get('acceptanceBindAddress') in ('0.0.0.0', '127.0.0.1', profile['host']), 'Explicit acceptance bind address required')
    require(re.fullmatch('[A-Za-z0-9_.-]+', profile.get('acceptanceFrontend', '')), 'Dedicated acceptance frontend container name required')
    # Inspect socket bindings on the actual host. Binding port 0 cannot prove availability of the requested port.
    if profile.get('environment') == 'rehearsal':
        gateway = remote.inspect('intruoyi-release-rehearsal-gateway')
        require(gateway['State']['Running'] and gateway['Config'].get('Labels', {}).get('intruoyi.release.rehearsal') == 'intruoyi-release-rehearsal',
                'Owned isolation ingress must be running')
    else:
        sock = socket.socket()
        try:
            sock.bind((profile['acceptanceBindAddress'], url.port))
        except OSError:
            raise RuntimeBlocked('Acceptance port is already bound; no container changed')
        finally:
            sock.close()
    require(profile['acceptanceFrontend'] not in remote.run(['docker', 'ps', '-a', '--format', '{{.Names}}']).decode().splitlines(), 'Acceptance container name already exists; reconcile before deployment')
    acceptance_spec(profile)
    obs = observe(profile)
    plan = migration_plan(profile, manifest, obs)
    snapshot_checks = snapshot_precheck(profile, manifest, plan)
    return {'migrationAudit': audit_ledger(obs, manifest), 'plan': plan, 'acceptanceUrl': profile['acceptanceUrl'],
            'snapshotChecks': snapshot_checks}


def snapshot_precheck(profile, manifest, plan):
    """Run the candidate's canonicalizer before stopping any business container."""
    if not any(entry['migrationId'] == ROUTE_SNAPSHOT_MIGRATION and entry['action'] == 'APPLY' for entry in plan):
        return []
    matches = [item for item in manifest['migrations'] if item['migrationId'] == ROUTE_SNAPSHOT_MIGRATION]
    require(len(matches) == 1, 'Reviewed route snapshot migration missing or duplicated')
    return [run_snapshot_cli(profile, directory(profile, manifest['releaseTag']), manifest, matches[0], 'PRECHECK')]


def run_snapshot_cli(profile, root, manifest, migration, mode, recovery=None):
    validate_migration_handler(migration)
    require(migration.get('approvedHook') == ROUTE_SNAPSHOT_HOOK and mode in ('PRECHECK', 'BACKFILL', 'READINESS'),
            'Reviewed route snapshot hook and explicit mode required')
    if mode != 'PRECHECK':
        require_migration_maintenance(profile, root, recovery)
    staged = json.loads((root/'stage-verified.json').read_text())
    require(staged['manifestSha256'] == package_identity(manifest), 'Route snapshot hook staged package identity differs')
    image = manifest['images']['backend']['id']
    require(re.fullmatch('sha256:[a-f0-9]{64}', image), 'Pinned candidate backend image required for snapshot hook')
    require(remote.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', image]).decode().strip() == image,
            'Route snapshot candidate image identity differs')
    database = remote.inspect(profile['database'])
    require(database['State']['Running'] and re.fullmatch('[a-f0-9]{64}', database['Id']), 'Registered database is not running')
    environment = dict(value.split('=', 1) for value in database['Config']['Env'])
    name = environment.get('MYSQL_DATABASE')
    require(isinstance(name, str) and re.fullmatch('[A-Za-z0-9_-]+', name), 'Explicit safe target database required')
    if environment.get('MYSQL_ROOT_PASSWORD_FILE'):
        password = remote.run(['docker', 'exec', profile['database'], 'cat', environment['MYSQL_ROOT_PASSWORD_FILE']]).decode().rstrip('\r\n')
    else:
        password = environment.get('MYSQL_ROOT_PASSWORD')
    require(isinstance(password, str) and password and not any(char in password for char in '\r\n\0'),
            'Supported private database credential source required for snapshot CLI')
    operation = secrets.token_hex(12)
    report_root = root/('snapshot-'+mode.lower()+'-'+operation)
    report_root.mkdir(mode=0o700)
    credential_path = report_root/'jdbc.private.env'
    descriptor = os.open(str(credential_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write('MES_SNAPSHOT_JDBC_URL=jdbc:mysql://127.0.0.1:3306/'+name+'?useSSL=false&allowPublicKeyRetrieval=true\n'
                     'MES_SNAPSHOT_JDBC_USER=root\nMES_SNAPSHOT_JDBC_PASSWORD='+password+'\n')
    expected = dict(mode=mode, releaseTag=manifest['releaseTag'], migrationId=migration['migrationId'], imageId=image,
                    operationId=operation, packageIdentity=package_identity(manifest), targetDatabase=name)
    container = 'intruoyi-snapshot-'+operation
    command = ['docker', 'run', '--rm', '--pull=never', '--name', container,
               '--network', 'container:'+database['Id'], '--read-only', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,nosuid,size=64m',
               '--env-file', str(credential_path), '--mount', 'type=bind,src='+str(report_root)+',dst=/runtime-reports',
               '--entrypoint', 'java', image,
               '-Dloader.main=cn.iocoder.yudao.module.mes.service.pro.route.MesRouteSnapshotMigrationCli',
               '-cp', '/yudao-server/app.jar', 'org.springframework.boot.loader.launch.PropertiesLauncher',
               '--mode='+mode, '--report=/runtime-reports/report.json', '--release-tag='+expected['releaseTag'],
               '--migration-id='+expected['migrationId'], '--image-id='+image, '--operation-id='+operation,
               '--package-identity='+expected['packageIdentity']]
    try:
        try:
            process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        except subprocess.TimeoutExpired:
            # Terminate only this invocation's owned standalone CLI, never a business container.
            remote.run(['docker', 'rm', '-f', container])
            raise RuntimeBlocked('Route snapshot CLI timed out; owned CLI stopped, no readiness granted') from None
    finally:
        credential_path.unlink()
    report_path = report_root/'report.json'
    require(report_path.is_file() and not report_path.is_symlink() and report_path.stat().st_size <= 1024*1024,
            'Route snapshot CLI did not return a bounded report; raw process output is not exposed')
    report_path.chmod(0o600)
    try:
        report = json.loads(report_path.read_text('utf-8'))
    except (ValueError, UnicodeError):
        raise RuntimeBlocked('Route snapshot CLI report is not valid JSON') from None
    report = validate_snapshot_cli_report(report, expected, process.returncode)
    evidence = dict(expected, reportSha256=file_sha(report_path), reportPath=str(report_path),
                    databaseContainerId=database['Id'], status=report['status'], scannedCount=report.get('scannedCount'),
                    updatedCount=report.get('updatedCount'), blockerCount=report.get('blockerCount'))
    private_json(report_root/'binding.json', evidence)
    reasons = sorted({entry['reasonCode'] for entry in report.get('blockers', [])})
    if report.get('errorCode'):
        reasons.append(report['errorCode'])
    require(report['status'] == 'READY', 'Route snapshot '+mode+' blocked: count='+str(report.get('blockerCount', 'unknown'))+
            '; reasons='+','.join(reasons)+'; report='+str(report_path))
    return evidence


def require_migration_maintenance(profile, root, recovery):
    require(recovery and recovery.get('path') == str(root/'recovery.sql')
            and re.fullmatch('[0-9a-f]{64}', recovery.get('sha256',''))
            and (root/'recovery-record.private.json').is_file(), 'Completed recovery record required for reviewed migration')
    check_fence(profile)
    require(all(not remote.inspect(name)['State']['Running'] for name in profile['writers']),
            'Writer restarted before reviewed migration')


def stop_writers(profile):
    names = list(dict.fromkeys([profile['frontend']] + profile['writers']))
    for name in names:
        remote.run(['docker', 'stop', '--time', '90', name], timeout=120)
        state = remote.inspect(name)['State']
        require(not state['Running'] and state['ExitCode'] != 137, 'Writer did not stop gracefully: ' + name)
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if remote.sql(profile, 'SELECT COUNT(*) FROM information_schema.INNODB_TRX;') == '0':
            return
        time.sleep(1)
    raise RuntimeBlocked('Database transactions still active; SQL migration refused')


def backup(profile, root):
    check_storage(profile)
    database = profile['database']
    # Credentials are expanded only in the existing container shell.
    env = dict(v.split('=', 1) for v in remote.inspect(database)['Config']['Env'])
    if 'MYSQL_ROOT_PASSWORD_FILE' in env:
        auth = 'export MYSQL_PWD="$(cat "$MYSQL_ROOT_PASSWORD_FILE")"; '
    elif env.get('MYSQL_ROOT_PASSWORD'):
        auth = 'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; '
    else:
        raise RuntimeBlocked('Root credential source not configured')
    path = root / 'recovery.sql'
    require(not path.exists(), 'Recovery snapshot already exists; reconcile earlier operation')
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as output:
        result = subprocess.run(['docker', 'exec', database, 'sh', '-c', auth +
                                 'exec mysqldump -uroot --single-transaction --routines --events --triggers --hex-blob --set-gtid-purged=OFF "$MYSQL_DATABASE"'],
                                stdout=output, stderr=subprocess.PIPE, timeout=3600)
    require(result.returncode == 0 and path.stat().st_size > 0, 'Full data recovery snapshot failed; applications remain stopped')
    digest = file_sha(path)
    return {'path': str(path), 'sha256': digest, 'includes': ['data', 'schema', 'triggers', 'events', 'routines']}


def clone_config(original, image, maintenance=None):
    config = copy.deepcopy(original['Config'])
    config['Image'] = image
    if maintenance is not None:
        # Environment is private, retained entirely on host. Property is explicit and overrides profile defaults.
        environment = [v for v in config['Env'] if not v.startswith('INTRUOYI_RELEASE_MAINTENANCE=')]
        environment.append('INTRUOYI_RELEASE_MAINTENANCE=' + str(maintenance).lower())
        config['Env'] = environment
    config['HostConfig'] = copy.deepcopy(original['HostConfig'])
    config['HostConfig'].pop('ContainerIDFile', None)
    endpoints = {}
    for name, entry in original['NetworkSettings']['Networks'].items():
        if name in ('host', 'none'):
            continue
        endpoint = {}
        if name != 'bridge':
            if entry.get('IPAddress'):
                endpoint['IPAMConfig'] = {'IPv4Address': entry['IPAddress']}
            if entry.get('Aliases'):
                endpoint['Aliases'] = entry['Aliases']
        endpoints[name] = endpoint
    if endpoints:
        config['NetworkingConfig'] = {'EndpointsConfig': endpoints}
    return config


def replace(profile, root, role, image, tag, maintenance=None, snapshot_suffix='initial'):
    name = profile[role]
    original = remote.inspect(name)
    require(not original['State']['Running'], 'Original application must be stopped before replacement')
    private_json(root / (role + '-before-' + snapshot_suffix + '.private.json'), original)
    config = clone_config(original, image, maintenance)
    # An unmounted default.conf would otherwise be replaced by the generic image config.
    if role == 'frontend' and not any(m['Destination'] == '/etc/nginx/conf.d/default.conf' for m in original['Mounts']):
        nginx = root / 'nginx.conf'
        remote.run(['docker', 'cp', name + ':/etc/nginx/conf.d/default.conf', str(nginx)])
        nginx.chmod(0o600)
        config['HostConfig']['Binds'] = (config['HostConfig'].get('Binds') or []) + [str(nginx) + ':/etc/nginx/conf.d/default.conf:ro']
    retained = name + '-before-' + tag
    docker('POST', '/containers/' + quote(name) + '/rename?name=' + quote(retained))
    for network in original['NetworkSettings']['Networks']:
        if network not in ('host', 'none'):
            docker('POST', '/networks/' + quote(network) + '/disconnect', {'Container': original['Id'], 'Force': True})
    created = docker('POST', '/containers/create?name=' + quote(name), config)
    actual = remote.inspect(created['Id'])
    require(actual['Image'] == image and actual['HostConfig']['PortBindings'] == original['HostConfig']['PortBindings'], 'Replacement identity/ports differ')
    require({json.dumps(m, sort_keys=True) for m in original['Mounts']} <=
            {json.dumps(m, sort_keys=True) for m in actual['Mounts']}, 'Replacement lost or changed a runtime mount')
    return created['Id']


def acceptance_frontend(profile, root):
    original = remote.inspect(profile['frontend'])
    spec = acceptance_spec(profile)
    path = root / 'acceptance-nginx.conf'
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        output.write(spec['nginx'])
    # Host-network public nginx gets a separate bridge instance and independent listen port.
    config = copy.deepcopy(original['Config'])
    config['Image'] = original['Image']
    config['Labels'] = dict(config.get('Labels') or {}, **{'intruoyi.release.acceptance': 'true'})
    config['ExposedPorts'] = {'80/tcp': {}}
    config['HostConfig'] = {'NetworkMode': spec['network'], 'Binds': [str(path) + ':/etc/nginx/conf.d/default.conf:ro'],
                          'PortBindings': {'80/tcp': [{'HostIp': profile['acceptanceBindAddress'], 'HostPort': str(urlsplit(profile['acceptanceUrl']).port)}]},
                          'RestartPolicy': {'Name': 'no'}}
    if profile.get('environment') == 'rehearsal':
        config['HostConfig']['PortBindings'] = {}
    config['NetworkingConfig'] = {'EndpointsConfig': {spec['network']: {}}}
    created = docker('POST', '/containers/create?name=' + quote(profile['acceptanceFrontend']), config)
    docker('POST', '/containers/' + created['Id'] + '/start')
    return created['Id']


def health(profile, tag, maintenance, through_acceptance=False):
    entry = profile['acceptanceUrl'] if maintenance or through_acceptance else profile['entryUrl']
    deadline = time.monotonic() + 180
    last_error = 'No observation attempted'
    while time.monotonic() < deadline:
        try:
            with urlopen(entry + '/release-info.json', timeout=5) as response:
                require(response.status == 200 and json.load(response)['releaseTag'] == tag, 'Frontend releaseTag mismatch')
            addresses = [n['IPAddress'] for n in remote.inspect(profile['backend'])['NetworkSettings']['Networks'].values() if n.get('IPAddress')]
            require(len(addresses) == 1, 'Candidate backend address is ambiguous')
            backend_url = 'http://' + addresses[0] + ':48081'
            with urlopen(backend_url + '/actuator/release', timeout=5) as response:
                state = json.load(response)
            validate_release_state(state, tag, maintenance)
            with urlopen(backend_url + '/actuator/health', timeout=5) as response:
                require(json.load(response).get('status') == 'UP', 'Backend database health not UP')
            return {'releaseTag': tag, 'maintenance': maintenance, 'entryUrl': entry, 'writerControls': state}
        except Exception as error:
            last_error = str(error) if isinstance(error, RuntimeBlocked) else type(error).__name__ + (':' + str(error.code) if hasattr(error, 'code') else '')
            time.sleep(2)
    raise RuntimeBlocked('Runtime verification timed out; last error: ' + last_error)


def deploy(profile, manifest):
    preflight(profile, manifest)
    root = directory(profile, manifest['releaseTag'])
    require((root / 'stage-verified.json').is_file(), 'Immutable package not staged')
    staged = json.loads((root / 'stage-verified.json').read_text())
    require(staged['manifestSha256'] == package_identity(manifest), 'Staged manifest identity differs')
    verify_files(root, staged['files'])
    for role in ('backend', 'frontend'):
        image = manifest['images'][role]['id']
        require(remote.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', image]).decode().strip() == image, 'Candidate image not loaded')
    expected_schema = manifest.get('expectedSchemaSha256')
    validate_expected_schema(profile['environment'], expected_schema)
    obs = observe(profile)
    plan = migration_plan(profile, manifest, obs)
    check_fence(profile)
    stop_writers(profile)
    recovery = backup(profile, root)
    private_json(root / 'recovery-record.private.json', recovery)
    # Repeat against stopped writers, immediately before any SQL mutation.
    plan = migration_plan(profile, manifest, observe(profile))
    apply_migration_plan(profile, root, manifest, plan, recovery=recovery)
    actual_schema = observe(profile)['schemaSha256']
    require(not expected_schema or actual_schema == expected_schema, 'Actual upgraded schema differs from accepted rehearsal; applications remain stopped')
    replace(profile, root, 'backend', manifest['images']['backend']['id'], manifest['releaseTag'], True)
    replace(profile, root, 'frontend', manifest['images']['frontend']['id'], manifest['releaseTag'])
    docker('POST', '/containers/' + quote(profile['backend']) + '/start')
    acceptance_frontend(profile, root)
    verified_health = health(profile, manifest['releaseTag'], True)
    private_json(root / 'deployment-pending.json', {'releaseTag': manifest['releaseTag'], 'images': manifest['images'], 'maintenanceProtocol': PROTOCOL})
    # Test users need the normal write path before functional acceptance. Formal
    # targets and the isolated rehearsal retain their explicit acceptance gate.
    result = reopen(profile) if profile['environment'] == 'test' else observe(profile)
    if profile['environment'] != 'test':
        result['verifiedHealth'] = verified_health
    result['recoveryPoint'] = recovery
    result['schemaSha256'] = actual_schema
    return result


def apply_migration_plan(profile, root, manifest, plan, recovery=None):
    """Execute target checks immediately before their migration, after earlier schema steps."""
    sources = {migration_id(m): m for m in manifest['migrations']}
    for entry in plan:
        if entry['action'] != 'APPLY':
            continue
        item = sources[entry['migrationId']]
        path = (root / item['file']).resolve()
        require(root.resolve() in path.parents and path.is_file(), 'Migration source not staged')
        require(file_sha(path) == item['sha256'], 'Migration source checksum changed')
        if item.get('approvedHook') == ROUTE_SNAPSHOT_HOOK:
            validate_migration_handler(item)
            run_snapshot_cli(profile, root, manifest, item, 'BACKFILL', recovery)
            run_snapshot_cli(profile, root, manifest, item, 'READINESS', recovery)
        if item.get('requiresTargetPreflight') or item.get('type') != 'schema':
            run_target_preflight(profile, root, item, entry['targetPreflight'])
        require(re.fullmatch('[A-Za-z0-9_.-]+', item['migrationId']), 'Invalid migration identity')
        sql_file = item['file']
        require(re.fullmatch('[A-Za-z0-9_./-]+', sql_file), 'Unsafe migration file name')
        tag, mid = manifest['releaseTag'], item['migrationId']
        op = tag + '-' + profile['environment']
        remote.sql(profile, "INSERT INTO infra_release_migration(release_tag,migration_id,file_name,sha256,target_environment,status,operation_id,creator,updater) VALUES('" + tag + "','" + mid + "','" + sql_file + "','" + item['sha256'] + "','" + profile['environment'] + "','RUNNING','" + op + "','release-center','release-center');")
        try:
            maintenance_ready = False
            if validate_migration_handler(item):
                require_migration_maintenance(profile, root, recovery)
                maintenance_ready = True
            remote.sql(profile, migration_execution_sql(item, path.read_text('utf-8-sig'), maintenance_ready))
        except Exception as error:
            remote.sql(profile, "UPDATE infra_release_migration SET status='FAILED',finished_at=NOW(),error_message='Target SQL or postcheck failed; investigate private snapshot' WHERE operation_id='" + op + "' AND migration_id='" + mid + "' AND status='RUNNING';")
            raise RuntimeBlocked('Migration execution failed: '+mid+'; '+str(error)) from error
        remote.sql(profile, "UPDATE infra_release_migration SET status='APPLIED',finished_at=NOW() WHERE operation_id='" + op + "' AND migration_id='" + mid + "' AND status='RUNNING';")

def run_target_preflight(profile, root, migration, check):
    """Use the existing release_target_data_preflight pass-sentinel contract."""
    relative = check.get('reference', check.get('file', ''))
    path = (root / relative).resolve()
    require(relative and root.resolve() in path.parents and path.is_file(), 'Target data preflight SQL not packaged')
    require(file_sha(path) == check.get('sha256'), 'Target data preflight checksum mismatch')
    staged = json.loads((root / 'stage-verified.json').read_text())
    approved = [value for value in staged.get('validatedPreflights', []) if value['file'] == relative]
    require(len(approved) == 1 and approved[0]['sha256'] == check.get('sha256') and approved[0]['migrationId'] == migration['migrationId'], 'Exact target preflight bytes were not validated by existing source contract during staging')
    content = path.read_text('utf-8')
    environment = profile.get('sourceEnvironment', profile['environment'])
    require(environment in approved[0]['allowedEnvironments'], 'Target preflight is not approved for this environment')
    try:
        output = remote.sql(profile, 'SET SESSION TRANSACTION READ ONLY;\nSTART TRANSACTION READ ONLY;\n' + content + '\nROLLBACK;')
    except RuntimeError as error:
        raise RuntimeBlocked('Target preflight query failed: '+migration['migrationId']+'; '+str(error)) from error
    require(output == 'TARGET_PREFLIGHT_PASS:' + migration['migrationId'], 'Target data preflight did not pass: '+migration['migrationId'])


def reopen(profile):
    check_fence(profile)
    backend = remote.inspect(profile['backend'])
    environment = dict(v.split('=', 1) for v in backend['Config']['Env'])
    require(environment.get('INTRUOYI_RELEASE_MAINTENANCE') == 'true', 'Candidate is not in maintenance; reconcile instead of blindly reopening')
    # Find exactly one pending immutable candidate for the current image.
    candidates = []
    for record in Path(profile['stagingRoot']).glob('*/deployment-pending.json'):
        value = json.loads(record.read_text())
        if value['images']['backend']['id'] == backend['Image']:
            candidates.append((record.parent, value))
    require(len(candidates) == 1, 'Pending candidate cannot be identified uniquely')
    root, candidate = candidates[0]
    require(not remote.inspect(profile['frontend'])['State']['Running'], 'Public frontend unexpectedly open during candidate acceptance')
    health(profile, candidate['releaseTag'], True)
    remote.run(['docker', 'stop', '--time', '90', profile['backend']], timeout=120)
    require(not remote.inspect(profile['backend'])['State']['Running'] and remote.inspect(profile['backend'])['State']['ExitCode'] != 137, 'Maintenance backend did not drain')
    replace(profile, root, 'backend', backend['Image'], candidate['releaseTag'] + '-maintenance', False, 'reopen')
    docker('POST', '/containers/' + quote(profile['backend']) + '/start')
    health(profile, candidate['releaseTag'], False, through_acceptance=True)
    for writer in profile['writers']:
        if writer != profile['backend']:
            docker('POST', '/containers/' + quote(writer) + '/start')
            require(remote.inspect(writer)['State']['Running'], 'Registered writer did not resume: ' + writer)
    # Only normal-mode healthy backend may expose public frontend again.
    docker('POST', '/containers/' + quote(profile['frontend']) + '/start')
    remote.run(['docker', 'stop', '--time', '30', profile['acceptanceFrontend']])
    try:
        verified_health = health(profile, candidate['releaseTag'], False)
    except Exception:
        remote.run(['docker', 'stop', '--time', '30', profile['frontend']])
        raise
    require(remote.inspect(profile['acceptanceFrontend'])['Config'].get('Labels', {}).get('intruoyi.release.acceptance') == 'true', 'Acceptance resource ownership cannot be proved')
    remote.run(['docker', 'rm', profile['acceptanceFrontend']])
    result = observe(profile)
    result['verifiedHealth'] = verified_health
    return result


def deployment_progress(profile, payload, phase):
    from intruoyi_rehearsal_agent import process_start_identity
    job_id = payload.get('jobId')
    require(isinstance(job_id, str) and re.fullmatch('JOB-[a-f0-9]{10}', job_id), 'Valid deployment job ID required')
    root = directory(profile, payload['manifest']['releaseTag'])
    path = root / 'deployment-progress.private.json'
    value = dict(jobId=job_id, releaseTag=payload['manifest']['releaseTag'], phase=phase,
                 pid=os.getpid(), processStart=process_start_identity(os.getpid()),
                 observedAt=datetime.now(timezone.utc).isoformat())
    require(value['processStart'], 'Remote deployment process identity cannot be recorded')
    if phase == 'running':
        private_json(path, value)
    else:
        previous = json.loads(path.read_text())
        require(previous['jobId'] == job_id and previous['processStart'] == value['processStart'],
                'Deployment progress belongs to another execution')
        temporary = path.with_suffix('.new')
        private_json(temporary, value)
        os.replace(str(temporary), str(path))
    return value


def verify_deployment_stopped(profile, payload):
    require(profile.get('environment') == 'rehearsal', 'Disposable deployment verification is restricted to isolated rehearsal')
    require(re.fullmatch('JOB-[a-f0-9]{10}', payload.get('jobId', '')), 'Original deployment job required')
    root = directory(profile, payload['releaseTag'])
    require((root / 'stage-verified.json').is_file() and (root / 'recovery-record.private.json').is_file(),
            'Original staged package and recovery evidence must remain before discarding isolation')
    import intruoyi_rehearsal_agent
    stopped = intruoyi_rehearsal_agent.dispatch(dict(payload, action='rehearsal-verify-stopped', checkProcessesOnly=True), globals())
    require(stopped.get('stopped') is True, 'Remote deployment workers not confirmed stopped')
    require(remote.sql(profile, 'SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID<>CONNECTION_ID() AND DB=DATABASE() AND COMMAND<>\'Sleep\';') == '0',
            'Active database statements prevent discarding the isolated deployment')
    require(remote.sql(profile, 'SELECT COUNT(*) FROM information_schema.INNODB_TRX;') == '0',
            'Active database transactions prevent discarding the isolated deployment')
    path = root / 'deployment-progress.private.json'
    evidence = dict(stopped=True, jobId=payload['jobId'], releaseTag=payload['releaseTag'],
                    recoveryRecord=str(root / 'recovery-record.private.json'), activeStatements=0, activeTransactions=0)
    if path.exists():
        progress = json.loads(path.read_text())
        require(progress.get('jobId') == payload['jobId'], 'Deployment progress belongs to another task')
        require(intruoyi_rehearsal_agent.process_start_identity(progress['pid']) != progress['processStart'],
                'Original remote deployment process remains active')
        evidence['progress'] = progress
    return evidence


def dispatch(payload):
    profile, action = payload['profile'], payload['action']
    if action.startswith('rehearsal-'):
        import intruoyi_rehearsal_agent
        try:
            return intruoyi_rehearsal_agent.dispatch(payload, globals())
        except Exception:
            if action in ('rehearsal-capture','rehearsal-restore'):
                intruoyi_rehearsal_agent.dispatch(dict(payload,action='rehearsal-job-progress',phase='failed'),globals())
            raise
    if action == 'observe':
        return observe(profile)
    if action == 'verify-deployment-stopped':
        return verify_deployment_stopped(profile, payload)
    if action == 'verify-restoration':
        root = directory(profile, payload['releaseTag'])
        record = json.loads((root/'manual-recovery-confirmed.private.json').read_text())
        require(record.get('jobId') == payload['jobId'] and record.get('restored') is True,
                'Explicit recovery evidence for this original job is required')
        result = observe(profile)
        if record.get('recoveryKind') == 'no-migrations-started':
            validate_quiescence_recovery(record, payload, result)
            require(not (root/'recovery-record.private.json').exists() and not (root/'recovery.sql').exists()
                    and not (root/'deployment-pending.json').exists(), 'Effects exceed incomplete-snapshot recovery')
            partial = Path(record['incompleteSnapshotPath'])
            require(partial.parent == Path('/var/lib/docker/intruoyi-release-workflow/recovery-evidence') / payload['jobId']
                    and partial.name == 'recovery.incomplete.sql' and partial.is_file()
                    and partial.stat().st_size == record['incompleteSnapshotBytes']
                    and file_sha(partial) == record['incompleteSnapshotSha256'], 'Retained incomplete snapshot differs')
            require(remote.sql(profile, "SELECT COUNT(*) FROM infra_release_migration WHERE release_tag='" + payload['releaseTag'] + "';") == '0',
                    'Migration records prevent no-SQL recovery')
        else:
            require(not record.get('recoveryKind'), 'Unrecognized recovery kind')
            recovery = json.loads((root/'recovery-record.private.json').read_text())
            require(recovery.get('path') == str(root/'recovery.sql')
                    and file_sha(root/'recovery.sql') == recovery.get('sha256') == record.get('snapshotSha256'),
                    'Recovery snapshot/evidence identity differs')
        require(result['fingerprint'] == payload['originFingerprint'] == record.get('restoredFingerprint'),
                'Actual restored origin differs from original job and recovery evidence')
        return dict(observation=result, recoveryEvidence=record)
    if action == 'dependencies':
        return dependencies(profile)
    if action == 'acceptance-check':
        value = acceptance_spec(profile)
        return {'network': value['network'], 'backendIp': value['backendIp'], 'nginxSha256': hashlib.sha256(value['nginx'].encode()).hexdigest(), 'mutations': False}
    if action == 'preflight':
        return preflight(profile, payload['manifest'])
    if action == 'stage-directory':
        check_fence(profile)
        check_storage(profile)
        root = Path(payload['directory'])
        require(root.parent == Path(profile['stagingRoot']) and re.fullmatch(r'\d{4}(-\d{2}){5}', root.name), 'Unregistered staging path')
        root.mkdir(mode=0o700, parents=True, exist_ok=False)
        for item in payload['files']:
            path = (root / item['name']).resolve()
            require(root.resolve() in path.parents, 'Unsafe staged path')
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        return {'directory': str(root)}
    if action == 'verify-stage':
        check_fence(profile)
        root = directory(profile, payload['manifest']['releaseTag'])
        require(str(root) == payload['directory'], 'Staging target mismatch')
        require(payload['files'] == [{'name': item['name'], 'sha256': item['sha256']} for item in payload['manifest']['files']],
                'Staging file list differs from manifest')
        archive_evidence = unpack_original_package(root, payload['manifest'], payload['archive'])
        verify_files(root, payload['files'])
        archives = [item for item in payload['files'] if item['name'].endswith(('.tar', '.tar.gz')) and 'image' in item['name']]
        require(len(archives) == 1, 'One explicit image archive required')
        remote.run(['docker', 'load', '-i', str(root / archives[0]['name'])], timeout=1800)
        for role in ('backend', 'frontend'):
            image = payload['manifest']['images'][role]['id']
            require(remote.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', image]).decode().strip() == image, 'Imported image identity mismatch')
        private_json(root / 'stage-verified.json', {'manifestSha256': package_identity(payload['manifest']), 'files': payload['files'], 'archive': archive_evidence, 'validatedPreflights': payload['validatedPreflights']})
        return {'directory': str(root), 'verified': True, 'manifestSha256': package_identity(payload['manifest'])}
    if action == 'deploy':
        deployment_progress(profile, payload, 'running')
        try:
            result = deploy(profile, payload['manifest'])
        except Exception:
            deployment_progress(profile, payload, 'failed')
            raise
        deployment_progress(profile, payload, 'succeeded')
        return result
    if action == 'health':
        backend = remote.inspect(profile['backend'])
        env = dict(value.split('=', 1) for value in backend['Config']['Env'])
        maintenance = env.get('INTRUOYI_RELEASE_MAINTENANCE') == 'true'
        return health(profile, payload['releaseTag'], maintenance)
    if action == 'maintenance':
        if payload['enabled'] is False:
            return reopen(profile)
        raise RuntimeBlocked('Maintenance closing requires a fixed deployment manifest, writer inventory and recovery workflow; use deploy')
    raise RuntimeBlocked('Unsupported IntRuoyi runtime operation')


if __name__ == '__main__':
    try:
        result = dispatch(json.loads(PAYLOAD))
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=True))
    except RuntimeBlocked as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=True))
    except Exception as error:
        # Never stringify exceptions that may contain SQL/credentials/configuration.
        print(json.dumps({'ok': False, 'error': 'Remote runtime operation failed: ' + type(error).__name__}))
