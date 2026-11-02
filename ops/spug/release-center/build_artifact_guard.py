"""Checks for the exact committed inputs and actual backend image, before sealing."""
import io
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

from executor import digest, require

MES_PREFIX = 'cn/iocoder/yudao/module/mes/service/pro/route/'
MES_CLASSES = ('MesRouteSnapshotMigrationCli', 'MesRouteLegacySummaryIdentity', 'MesRouteLegacySummaryMigration')
RUNTIME_CLASS = 'cn/iocoder/yudao/framework/tracer/config/ReleaseRuntimeEndpoint'
SOURCE_FILES = (
    'IntRuoyiBackend/pom.xml', 'IntRuoyiFronted/package.json', 'IntRuoyiFronted/pnpm-lock.yaml',
    'IntRuoyiBackend/sql/mysql/release-sources.json', 'scripts/preflight/check-menu-migrations.py',
    'IntRuoyiBackend/yudao-framework/yudao-spring-boot-starter-monitor/src/main/java/'+RUNTIME_CLASS+'.java',
    *('IntRuoyiBackend/yudao-module-mes/src/main/java/'+MES_PREFIX+name+'.java' for name in MES_CLASSES),
)


def validate_source_contract(executor, commit):
    command = ['git', '-C', executor.c['repo']]
    require(executor.run(command+['rev-parse', commit+'^{commit}'], timeout=30).decode().strip() == commit,
            'Requested source commit does not exist')
    entries = executor.run(command+['ls-tree', '-r', '-z', commit, '--', *SOURCE_FILES], timeout=30)
    available = {}
    for row in entries.split(b'\0'):
        if row:
            identity, name = row.split(b'\t', 1)
            mode, kind, _ = identity.split()
            if kind == b'blob' and mode in (b'100644', b'100755'):
                available[name.decode('utf-8')] = True
    missing = sorted(set(SOURCE_FILES)-available.keys())
    require(not missing, 'Selected committed source lacks required release contracts: '+', '.join(missing)+
            '; select or integrate a commit containing the release fixes; uncommitted repairs are excluded')
    return dict(commit=commit, requiredFiles=len(SOURCE_FILES), uncommittedChangesIncluded=False)


def validate_required_gxp_mode(config, actual):
    require(actual in ('FORMAL', 'DEVELOPMENT_DISABLED'), 'Saved GxP mode is invalid')
    if 'requiredGxpAuditMode' in config:
        expected = config['requiredGxpAuditMode']
        require(expected in ('FORMAL', 'DEVELOPMENT_DISABLED'), 'Required GxP mode is invalid')
        require(actual == expected, 'Saved GxP mode differs from requiredGxpAuditMode; configuration was not changed')


def verify_backend_jar(path):
    require(Path(path).is_file(), 'Actual backend image JAR is missing')
    requirements = {'yudao-module-mes-': [MES_PREFIX+n for n in MES_CLASSES],
                    'yudao-spring-boot-starter-monitor-': [RUNTIME_CLASS]}
    with zipfile.ZipFile(path) as outer:
        names = outer.namelist()
        require(names.count('org/springframework/boot/loader/launch/PropertiesLauncher.class') == 1,
                'Packaged Boot PropertiesLauncher is missing or ambiguous')
        for module, classes in requirements.items():
            matches = [n for n in names if n.startswith('BOOT-INF/lib/'+module) and n.endswith('.jar')]
            owners = {name:[] for name in classes}
            for candidate in matches:
                with zipfile.ZipFile(io.BytesIO(outer.read(candidate))) as nested:
                    for name in classes:
                        owners[name].extend([candidate]*nested.namelist().count(name+'.class'))
            for name, found in owners.items():
                require(len(found) == 1, 'Packaged backend class missing or ambiguous: '+name)
            owner = owners[classes[0]][0]
            require(all(found == [owner] for found in owners.values()), 'Packaged CLI support classes span ambiguous modules')
            require(outer.getinfo(owner).compress_type == zipfile.ZIP_STORED,
                    'Boot nested module must be stored without compression: '+module)
    return dict(status='passed', jarSha256=digest(path), requiredClassCount=4)


def validate_offline_cli_report(report, binding, exit_code):
    require(exit_code == 3, 'Offline packaged CLI must return its bounded credential-free error (exit 3)')
    expected = dict(binding, schemaVersion='route-snapshot-migration/v1', mode='READINESS',
                    status='ERROR', errorCode='COMMAND_FAILED')
    require(isinstance(report, dict) and all(report.get(key) == value for key, value in expected.items()),
            'Offline packaged CLI report identity or error contract differs')
    require('updatedCount' not in report, 'Offline CLI must not report database updates')


def verify_backend_image(executor, job, image, source_jar, evidence_root):
    """Inspect bytes from the real image and exercise its Java with no network.

    The probe has no application configuration, database credentials or business
    service startup. Only its random evidence directory is writable.
    """
    evidence_root = Path(evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='backend-contract-', dir=evidence_root) as temporary:
        root = Path(temporary)
        container = executor.run(['docker', 'create', '--network', 'none', image['id']]).decode().strip()
        require(container, 'Backend artifact inspection container was not created')
        jar = root/'app.jar'
        try:
            executor.run(['docker', 'cp', container+':/yudao-server/app.jar', str(jar)], timeout=120)
        finally:
            executor.run(['docker', 'rm', container], timeout=30)
        result = verify_backend_jar(jar)
        require(result['jarSha256'] == digest(source_jar), 'Backend image JAR differs from compiled frozen source')
        # The future archive digest does not exist yet. Bind this build probe to
        # the exact image JAR instead; this is not a deployment attestation.
        binding = dict(releaseTag=job['releaseTag'], migrationId='20261023_mes_route_snapshot_legacy_summary_enforce',
                       imageId=image['id'], operationId=job['id'], packageIdentity=result['jarSha256'])
        report_file = root/'report.json'
        command = ['docker', 'create', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                   '--security-opt', 'no-new-privileges', '--mount', 'type=bind,src='+str(root)+',dst=/release-preflight',
                   '--env', 'MES_SNAPSHOT_JDBC_URL=', '--env', 'MES_SNAPSHOT_JDBC_USER=',
                   '--env', 'MES_SNAPSHOT_JDBC_PASSWORD=', '--entrypoint', 'java', image['id'],
                   '-Dloader.main='+MES_PREFIX.replace('/', '.')+'MesRouteSnapshotMigrationCli',
                   '-cp', '/yudao-server/app.jar', 'org.springframework.boot.loader.launch.PropertiesLauncher',
                   '--mode=READINESS', '--report=/release-preflight/report.json',
                   '--release-tag='+binding['releaseTag'], '--migration-id='+binding['migrationId'],
                   '--image-id='+binding['imageId'], '--operation-id='+binding['operationId'],
                   '--package-identity='+binding['packageIdentity']]
        # Never copy raw Java/Docker output into public job errors.
        probe = executor.run(command, timeout=30).decode().strip()
        require(probe, 'Offline CLI probe container was not created')
        try:
            try:
                completed = subprocess.run(['docker', 'start', '--attach', probe], capture_output=True, timeout=45)
            except subprocess.TimeoutExpired:
                raise ValueError('Offline packaged CLI timed out; package was not sealed') from None
        finally:
            executor.run(['docker', 'rm', '--force', probe], timeout=30)
        require(report_file.is_file(), 'Offline packaged CLI did not produce its report')
        try:
            report = json.loads(report_file.read_text(encoding='utf-8'))
        except (ValueError, UnicodeError):
            raise ValueError('Offline packaged CLI report is invalid') from None
        validate_offline_cli_report(report, binding, completed.returncode)
        return dict(result, imageId=image['id'], offlineCli='passed', network='none', databaseCredentials=False,
                    probeBinding=binding, expectedExitCode=3)
