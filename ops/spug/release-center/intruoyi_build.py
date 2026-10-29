"""Build one immutable IntRuoyi candidate from a clean, pinned worktree."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

from executor import digest, require, stamp
from intruoyi_runtime import bind_reviewed_session_profile, validate_migration_handler, rehearsal_profile
from nas_connection import connect_nas
from intruoyi_login import verify_login

MAINTENANCE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(MAINTENANCE_ROOT))
from ops.release.release_source_catalog import release_paths
from ops.release.release_migration_policy_gate import run_migration_policy_gate
from ops.release.release_target_preflight_contract import validate
from ops.release.release_preflight_plan import _order_migrations_by_dependencies, build_preflight_plan


def build_python(config):
    if config.get('executionMode') == 'windows-service':
        executable = config.get('pythonExecutable')
        require(isinstance(executable, str) and Path(executable).is_file()
                and Path(executable).name.lower() == 'python.exe',
                'Windows service requires an explicit pythonExecutable pointing to python.exe; pythonservice.exe cannot run build scripts')
        return executable
    return sys.executable


def check_local_space(executor, phase='build'):
    """Explicit simultaneous budgets, summed when paths share a filesystem."""
    budgets = executor.c.get('localBuildSpaceBytes')
    require(isinstance(budgets, dict) and set(budgets) == {'worktree', 'package', 'state'}
            and all(type(v) is int and v > 0 for v in budgets.values()),
            'Explicit positive localBuildSpaceBytes for worktree/package/state required')
    require(phase in ('build', 'export'), 'Unknown build space phase')
    paths = dict(worktree=Path(executor.c['buildWorktreeRoot']), package=executor.root/'packages', state=executor.root)
    groups = {}
    for key in ('worktree', 'package', 'state') if phase == 'build' else ('package', 'state'):
        path = paths[key].resolve()
        while not path.exists():
            require(path.parent != path, 'Build storage volume is unavailable: '+str(path))
            path = path.parent
        device = path.stat().st_dev
        group = groups.setdefault(device, dict(path=str(path), requiredBytes=0, purposes=[]))
        group['requiredBytes'] += budgets[key]
        group['purposes'].append(key)
    for group in groups.values():
        group['freeBytes'] = shutil.disk_usage(group['path']).free
        require(group['freeBytes'] >= group['requiredBytes'],
                'Local build storage insufficient for '+','.join(group['purposes'])+': '+group['path']+
                '; required='+str(group['requiredBytes'])+', free='+str(group['freeBytes']))
    return list(groups.values())


def frontend_dependency_store(executor, frontend):
    """Use a local content store; prove hardlinks before pnpm touches dependencies.

    The machine-wide store can live on a USB disk. Reading every cached package
    there and copying it across volumes took 42--49 minutes per clean checkout.
    This store contains dependency content only, never prior application output.
    """
    store = executor.root/'pnpm-store'
    store.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.link-probe-', dir=store) as source_dir, \
            tempfile.TemporaryDirectory(prefix='.link-probe-', dir=frontend) as target_dir:
        source = Path(source_dir)/'content'
        source.write_bytes(b'pnpm-hardlink-preflight')
        try:
            target = Path(target_dir)/'content'
            os.link(source, target)
        except OSError as error:
            raise ValueError('Frontend dependency store must support hardlinks to the build worktree; '
                             'place stateDir and buildWorktreeRoot on the same local volume') from error
        require(os.path.samefile(source, target), 'Frontend dependency store hardlink verification failed')
    return store


def install_frontend(executor, job, pnpm, frontend, timeout=3600):
    """Keep dependency progress visible; full diagnostics stay outside the package."""
    store = frontend_dependency_store(executor, frontend)
    executor.log(job, 'Frontend dependency store: '+str(store)+'; hardlink import, integrity verification enabled')
    log_root = executor.root/'build-logs'
    log_root.mkdir(exist_ok=True)
    diagnostic = log_root/(job['id']+'-pnpm.private.log')
    progress_pattern = re.compile(r'^Progress: resolved \d+, reused \d+, downloaded \d+, added \d+')
    started = time.monotonic()
    last_report = started
    last_progress = None
    reported = None
    with diagnostic.open('wb') as output, diagnostic.open('rb') as reader:
        process = subprocess.Popen([pnpm, 'install', '--frozen-lockfile', '--reporter=append-only',
                                    '--store-dir', str(store), '--package-import-method=hardlink',
                                    '--verify-store-integrity=true'],
                                   cwd=frontend, stdout=output, stderr=subprocess.STDOUT)
        while True:
            try:
                code = process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                code = None
            for line in reader.readlines():
                message = line.decode('utf-8', errors='replace').strip()
                match = progress_pattern.match(message)
                if match:
                    last_progress = match.group(0)
            now = time.monotonic()
            if last_progress != reported and (now-last_report >= 15 or code is not None):
                executor.log(job, 'Frontend dependencies: '+last_progress)
                reported, last_report = last_progress, now
            if code is not None:
                require(code == 0, 'Frontend dependency installation failed ('+str(code)+'); private diagnostic: '+str(diagnostic))
                executor.log(job, 'Frontend dependency installation completed in '+format(now-started, '.1f')+' seconds')
                return
            if now-started >= timeout:
                if os.name == 'nt':
                    # Killing only cmd.exe leaves its node child alive on Windows.
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                else:
                    process.kill()
                process.wait(timeout=15)
                raise TimeoutError('Frontend dependency installation exceeded '+str(timeout)+' seconds; private diagnostic: '+str(diagnostic))


def migration_inputs(worktree):
    sql_root = worktree/'IntRuoyiBackend/sql/mysql'
    paths, references = release_paths(sql_root)
    result = run_migration_policy_gate(sql_root, sql_paths=paths)
    # Moving an immutable source into historical/ must not move its execution
    # behind newer SQL. IDs establish the stable input order; dependencies and
    # explicit applyOrder then control the final topological order.
    migrations = _order_migrations_by_dependencies(sorted(result['migrations'], key=lambda item: item['migrationId']))
    artifacts = {entry['file']: sql_root/Path(entry['file']).relative_to('sql/mysql') for entry in migrations}
    for entry in migrations:
        bind_reviewed_session_profile(entry)
        if entry['type'] not in {'schema', 'data', 'menu', 'config', 'permission', 'seed'}:
            continue
        if entry['requiresTargetPreflight'] or entry['type'] != 'schema':
            relative = 'sql/mysql/target-preflight/'+entry['migrationId']+'.preflight.sql'
            path = sql_root/'target-preflight'/(entry['migrationId']+'.preflight.sql')
            # Old, already-applied SQL stays in the cumulative package. Its
            # target-data check is required only when a target must APPLY it.
            # The remote preflight refuses a pending required check if absent.
            if path.is_file():
                validate(path, entry['migrationId'])
                entry['targetPreflight'] = dict(reference=relative, sha256=digest(path), readOnly=True)
                artifacts[relative] = path
    artifacts['sql/mysql/release-sources.json'] = sql_root/'release-sources.json'
    catalog = json.loads((sql_root/'release-sources.json').read_text('utf-8-sig'))
    for entry in catalog.get('historicalMigrations', []):
        artifacts['sql/mysql/reviewed-sources/'+entry['file']] = sql_root/entry['file']
    if catalog.get('historicalMigrations'):
        # Keep the original manifest's byte protection in every clean checkout.
        require((sql_root/'historical/.gitattributes').read_text('utf-8').strip() == '*.sql -text',
                'Historical SQL must disable Git newline conversion')
    for reference in references:
        artifacts['sql/mysql/source-references/'+reference['file']] = sql_root/reference['file']
    return migrations, references, artifacts


def historical_integrity(migrations, baseline_records):
    """A same-named migration cannot change bytes or disappear after execution."""
    incoming = {m['migrationId']: m for m in migrations}
    conflicts = []
    for row in baseline_records:
        identity = row['migrationId']
        require(row['status'] in ('APPLIED', 'SKIPPED_ALREADY_APPLIED'), 'Unresolved baseline migration: '+identity)
        if identity not in incoming:
            conflicts.append(identity+': source missing')
        elif incoming[identity]['sha256'] != row['sha256']:
            conflicts.append(identity+': checksum changed')
    require(not conflicts, 'Historical migration source conflict ('+str(len(conflicts))+'): '+'; '.join(conflicts))


def historical_package_integrity(migrations, references, previous):
    """Preserve sealed candidate bytes without inventing target execution history.

    A reviewed rollback-only source may leave the forward plan while its exact
    original remains packaged. This exception never applies to an actual ledger.
    """
    incoming = {m['migrationId']: m['sha256'] for m in migrations}
    require(len(incoming) == len(migrations), 'Duplicate candidate migration identity')
    for reference in references:
        if reference.get('kind') != 'rollback-only':
            continue
        name = reference.get('file', '')
        require(isinstance(name, str) and re.fullmatch(r'20\d{6}_[A-Za-z0-9_]+_rollback\.sql', name)
                and not reference.get('replacement'), 'Explicit rollback-only archive identity required')
        identity = Path(name).stem
        require(identity not in incoming, 'Conflicting archived rollback identity: '+identity)
        incoming[identity] = reference['sha256']
    sealed = [(m['migrationId'], m['sha256']) for m in previous['migrations']]
    # Once retained as a reference, later packages must continue retaining it.
    sealed += [(Path(r['file']).stem, r['sha256']) for r in previous.get('sourceReferences', [])
               if r.get('kind') == 'rollback-only']
    conflicts = [identity+(': source missing' if identity not in incoming else ': checksum changed')
                 for identity, checksum in sealed if incoming.get(identity) != checksum]
    require(not conflicts, 'Historical package source conflict ('+str(len(conflicts))+'): '+'; '.join(conflicts))


def target_input_plan(migrations, records, environment):
    """Reject missing checks and blocked dependencies before expensive compilation."""
    state = {}
    for row in records:
        mid = row['migrationId']
        previous = state.get(mid)
        require(previous is None or previous['sha256'] == row['sha256'], 'Conflicting historical migration: '+mid)
        require(row['status'] in {'APPLIED', 'SKIPPED_ALREADY_APPLIED', 'SKIPPED_ENV_NOT_ALLOWED',
                                  'SKIPPED_SCOPE_EXCLUDED', 'SKIPPED_IMMUTABLE'}, 'Unresolved historical migration: '+mid)
        if previous is None or previous['status'] not in {'APPLIED', 'SKIPPED_ALREADY_APPLIED'}:
            state[mid] = row
    executable = [m for m in migrations if m['type'] in {'schema', 'data', 'menu', 'config', 'permission', 'seed'}]
    plan = build_preflight_plan(executable, state, target_environment=environment, publish_scope='app-release')
    blocked = [x['migrationId']+': '+x['reason'] for x in plan['items'] if x['action'].startswith('BLOCKED')]
    require(not blocked, environment+': migration plan blocked: '+'; '.join(blocked))
    by_id = {m['migrationId']:m for m in executable}
    for item in plan['items']:
        if item['action'] == 'APPLY':
            validate_migration_handler(by_id[item['migrationId']])
    missing = [x['migrationId'] for x in plan['items'] if x['action'] == 'APPLY'
               and (by_id[x['migrationId']]['type'] != 'schema' or by_id[x['migrationId']].get('requiresTargetPreflight'))
               and not isinstance(by_id[x['migrationId']].get('targetPreflight'), dict)]
    require(not missing, environment+': required target preflight missing ('+str(len(missing))+'): '+'; '.join(missing))
    return plan


def archive_image_identities(archive_path, images):
    """Docker Desktop's index ID differs from the classic engine's config ID.

    Declare both explicitly; the transported config bytes define the remote ID.
    """
    with tarfile.open(archive_path, 'r') as archive:
        stream = archive.extractfile('manifest.json')
        require(stream is not None, 'Docker save manifest is missing')
        entries = json.load(stream)
        for role, image in images.items():
            matches = [entry for entry in entries if image['name'] in (entry.get('RepoTags') or [])]
            require(len(matches) == 1, role+': Docker save image identity is ambiguous')
            config = archive.extractfile(matches[0]['Config'])
            require(config is not None, role+': Docker image config is missing')
            content = config.read()
            require(isinstance(json.loads(content).get('rootfs'), dict), role+': invalid Docker config')
            image['localImageId'] = image['id']
            image['id'] = 'sha256:'+hashlib.sha256(content).hexdigest()


def copy_original_package(folder, manifest, nas_path):
    """Publish and read back the exact sealed archive, never rebuild on NAS."""
    destination = Path(nas_path)/manifest['releaseTag']
    destination.mkdir(parents=True, exist_ok=False)
    original = folder/'release.tar'
    partial = destination/'release.tar.partial'
    shutil.copyfile(original, partial)
    require(digest(partial) == digest(original), 'NAS original package checksum mismatch')
    partial.rename(destination/'release.tar')
    shutil.copyfile(folder/'manifest.json', destination/'manifest.json')
    require(digest(destination/'manifest.json') == digest(folder/'manifest.json'), 'NAS manifest checksum mismatch')
    return str(destination)


def publish_nas(folder, manifest, nas_path, credentials_file):
    """Reauthenticate explicitly before publishing; never prompt for a login."""
    connect_nas(nas_path, credentials_file)
    return copy_original_package(folder, manifest, nas_path)


def build(executor, job):
    c = executor.c
    commit = job['payload'].get('commit', '')
    require(re.fullmatch('[0-9a-f]{40}', commit), 'Exact full Git commit required')
    require(executor.run(['git', '-C', c['repo'], 'rev-parse', commit+'^{commit}']).decode().strip() == commit,
            'Requested source commit does not exist')
    executor.step(job, 'capture-saved-gxp-mode')
    require(c.get('gxpConfigurationSourceUrl'), 'Configure the source application URL for the saved GxP setting')
    gxp_evidence = verify_login(c, c['gxpConfigurationSourceUrl'],
                               executor.root/'technical-evidence'/job['id']/'source-configuration',
                               dict(jobId=job['id'], gitCommit=commit), read_gxp_mode=True)
    release_settings = dict(gxpAuditMode=gxp_evidence['gxpAuditMode'])
    job['releaseSettings'] = release_settings
    job['gxpConfigurationEvidence'] = gxp_evidence
    executor.save()
    require(all(executor.state['environments'].get(env, {}).get('baselineStatus') == 'registered' for env in ('test', 'prod', 'backup')),
            'Register the real three-server baselines before building')
    executor.step(job, 'check-rehearsal-registration')
    rehearsal_profile(c, 'prod')
    executor.step(job, 'check-local-build-storage')
    job['localBuildStorage'] = check_local_space(executor)
    executor.save()
    executor.step(job, 'authenticate-package-storage')
    connect_nas(c.get('nasPath', ''), c.get('nasCredentialsFile'))
    tag = stamp()
    folder = executor.root/'packages'/tag
    require(not folder.exists(), 'Release timestamp already reserved')
    folder.mkdir(parents=True)
    worktree = Path(c['buildWorktreeRoot'])/tag
    job.update(releaseTag=tag, buildDirectory=str(folder), buildWorktree=str(worktree))
    executor.save()
    worktree.parent.mkdir(parents=True, exist_ok=True)
    executor.step(job, 'freeze-source')
    executor.run(['git', '-c', 'core.autocrlf=false', '-C', c['repo'], 'worktree', 'add', '--detach', str(worktree), commit], timeout=900)
    require(not executor.run(['git', '-C', str(worktree), 'status', '--porcelain']).strip(), 'Dedicated source is not clean')
    executor.step(job, 'migration-policy-and-history')
    migrations, references, artifacts = migration_inputs(worktree)
    readiness = {'verification': 'static-only', 'fullDataRehearsalRequired': True,
                 'requiredRehearsalSources': ['prod'], 'targets': {}}
    for env in ('test', 'prod', 'backup'):
        records = executor.state['environments'][env].get('ledgerRecords')
        require(isinstance(records, list), env+': registered migration records are missing')
        historical_integrity(migrations, records)
        readiness['targets'][env] = target_input_plan(migrations, records, env)
    for prior in executor.state['packages']:
        _, previous = executor.manifest(prior['releaseTag'])
        historical_package_integrity(migrations, references, previous)
    (folder/'migration-readiness.json').write_text(json.dumps(readiness, ensure_ascii=False, indent=2), 'utf-8')
    menu_gate = worktree/'scripts/preflight/check-menu-migrations.py'
    require(menu_gate.is_file(), 'Pinned menu migration gate missing')
    packaged_sql = folder/'packaged-sql-inputs.json'
    packaged_sql.write_text(json.dumps([m['file'] for m in migrations]), 'utf-8')
    executor.run([build_python(c), str(menu_gate), '--repo', str(worktree), '--packaged-sql', str(packaged_sql)], timeout=120)
    for relative, source in artifacts.items():
        destination = folder/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    bases = {}
    for role in ('backend', 'frontend'):
        reference = c['localRuntimeImages'][role]
        image_id = executor.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', reference]).decode().strip()
        require(re.fullmatch(r'sha256:[a-f0-9]{64}', image_id), 'Invalid local runtime image identity')
        pinned = 'intruoyi-release-base:'+role+'-'+image_id.split(':')[1]
        executor.run(['docker', 'tag', image_id, pinned])
        bases[role] = dict(id=image_id, name=pinned)
    mvn = shutil.which('mvn.cmd' if os.name == 'nt' else 'mvn')
    pnpm = shutil.which('pnpm.cmd' if os.name == 'nt' else 'pnpm')
    require(mvn and pnpm, 'Maven and pnpm required')
    executor.step(job, 'compile-backend')
    executor.run([mvn, '-B', '-ntp', '-f', str(worktree/'IntRuoyiBackend/pom.xml'), '-pl', 'yudao-server', '-am',
                  '-DskipTests', 'clean', 'package'], timeout=5400)
    frontend = worktree/'IntRuoyiFronted'
    executor.step(job, 'install-frontend-dependencies')
    install_frontend(executor, job, pnpm, frontend)
    executor.step(job, 'compile-frontend')
    build_env = dict(os.environ, NODE_OPTIONS='--max-old-space-size=8192', VITE_BASE_URL='', VITE_BASE_PATH='/', VITE_OUT_DIR='dist-intruoyi-test')
    executor.run(['node', 'node_modules/vite/bin/vite.js', 'build', '--mode', 'prod'], cwd=frontend, env=build_env, timeout=2700)
    info = dict(releaseTag=tag, sourceCommit=commit, builtAt=dt.datetime.now(dt.timezone.utc).isoformat())
    (frontend/'dist-intruoyi-test/release-info.json').write_text(json.dumps(info, ensure_ascii=False), 'utf-8')
    require(not executor.run(['git', '-C', str(worktree), 'status', '--porcelain']).strip(), 'Build changed frozen source')
    executor.step(job, 'build-complete-images')
    context = folder/'build-context'
    context.mkdir()
    shutil.copyfile(worktree/'IntRuoyiBackend/yudao-server/target/yudao-server-exec.jar', context/'app.jar')
    shutil.copytree(frontend/'dist-intruoyi-test', context/'frontend')
    shutil.copyfile(worktree/'IntRuoyiBackend/script/deploy/int-ruoyi-test/nginx.conf', context/'nginx.conf')
    (context/'release-info.json').write_text(json.dumps(info), 'utf-8')
    templates = {
        'backend': 'WORKDIR /yudao-server\nCOPY app.jar app.jar\nCOPY release-info.json release-info.json\nENV TZ=Asia/Shanghai JAVA_OPTS="-Xms512m -Xmx512m" ARGS="" INTRUOYI_EXTRA_ARGS=""\nEXPOSE 48081\nCMD ["sh","-c","exec java ${JAVA_OPTS} -jar app.jar ${ARGS} ${INTRUOYI_EXTRA_ARGS}"]\n',
        'frontend': 'COPY nginx.conf /etc/nginx/conf.d/default.conf\nCOPY frontend/ /usr/share/nginx/html/\nEXPOSE 80\n'}
    images = {}
    for role in ('backend', 'frontend'):
        dockerfile = context/('Dockerfile.'+role)
        dockerfile.write_text('FROM '+bases[role]['name']+'\n'+templates[role], 'utf-8')
        name = 'intruoyi-'+role+':'+tag
        executor.run(['docker', 'build', '--pull=false', '-f', str(dockerfile), '-t', name, str(context)], timeout=1800)
        images[role] = dict(name=name, id=executor.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', name]).decode().strip())
    executor.step(job, 'verify-image-release-identity')
    for role, image in images.items():
        container = executor.run(['docker', 'create', '--network', 'none', image['id']]).decode().strip()
        destination = folder/(role+'-release-info.json')
        try:
            image_path = '/usr/share/nginx/html/release-info.json' if role == 'frontend' else '/yudao-server/release-info.json'
            executor.run(['docker', 'cp', container+':'+image_path, str(destination)])
            require(json.loads(destination.read_text('utf-8')) == info, role+': image release-info mismatch')
        finally:
            executor.run(['docker', 'rm', container])
    executor.step(job, 'export-original-package')
    job['localExportStorage'] = check_local_space(executor, 'export')
    executor.save()
    executor.run(['docker', 'save', '-o', str(folder/'images.tar'), images['backend']['name'], images['frontend']['name']], timeout=1800)
    archive_image_identities(folder/'images.tar', images)
    files = [dict(name=path.relative_to(folder).as_posix(), sha256=digest(path))
             for path in sorted(folder.rglob('*')) if path.is_file() and 'build-context' not in path.relative_to(folder).parts]
    manifest = dict(applicationId=c['applicationId'], releaseTag=tag, IMAGE_TAG=tag, gitCommit=commit,
                    releaseSettings=release_settings,
                    images=images, migrations=migrations, sourceReferences=references,
                    maintenanceProtocol='intruoyi-quiescent-start-v1', files=files,
                    build=dict(runtimeImages=bases, executorSha256=digest(Path(__file__))))
    (folder/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), 'utf-8')
    with tarfile.open(folder/'release.tar', 'w') as archive:
        for item in ['manifest.json']+[f['name'] for f in files]:
            archive.add(folder/item, arcname=item)
    package = dict(releaseTag=tag, gitCommit=commit, directory=str(folder), manifestSha256=digest(folder/'manifest.json'),
                   packageSha256=digest(folder/'release.tar'), stage='built', baseline=False)
    require(c.get('nasPath'), 'Explicit NAS release package destination required')
    job['sealedPackage'] = dict(package)
    executor.step(job, 'publish-original-package-to-nas')
    package['nasDirectory'] = publish_nas(folder, manifest, c['nasPath'], c.get('nasCredentialsFile'))
    executor.state['packages'].insert(0, package)
    job['releaseTag'] = tag
    executor.save()
    executor.log(job, 'Complete immutable images, cumulative SQL and original package sealed; no target deployed')
