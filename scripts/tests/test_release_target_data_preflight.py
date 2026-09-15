import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / 'ops/release/release_target_data_preflight.py'
spec = importlib.util.spec_from_file_location('build_inputs', ROOT / 'scripts/tests/test_release_build_preflight_cache.py')
inputs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inputs)


def prepare(tmp_path, migration_type='data', needs_check=False):
    manifest, state = inputs._write_inputs(tmp_path)
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    for entry in (payload['requiredSql'][0], payload['database']['schemaMigrations'][0]):
        entry['type'] = migration_type
        entry['requiresTargetPreflight'] = needs_check
    manifest.write_text(json.dumps(payload), encoding='utf-8')
    evidence = tmp_path / 'build-preflight-evidence.json'
    result = inputs._run_existing_inputs(manifest, state, evidence)
    assert result.returncode == 0, result.stderr
    return manifest, state, evidence


def command(tmp_path, files):
    manifest, state, evidence = files
    return [sys.executable, '-X', 'utf8', str(RUNNER),
            '--prospective-manifest', str(manifest), '--target-state', str(state),
            '--build-evidence', str(evidence), '--package-root', str(tmp_path),
            '--checks-root', str(tmp_path / 'target-preflight'),
            '--server', '127.0.0.1', '--user', 'fixture',
            '--output', str(tmp_path / 'result.json')]


@pytest.mark.parametrize('kind,flag', [('data', False), ('menu', False), ('permission', False),
                                     ('config', False), ('seed', False), ('schema', True)])
def test_missing_check_blocks_before_any_ssh(tmp_path, kind, flag):
    result = subprocess.run(command(tmp_path, prepare(tmp_path, kind, flag)), capture_output=True, text=True, encoding='utf-8')
    assert result.returncode != 0
    report = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    assert report['status'] == 'failed'
    assert report['errorCode'] == 'TARGET_PREFLIGHT_MISSING'
    assert report['requiredCount'] == 1
    assert report['passedCount'] == 0
    assert report['sshStarted'] is False


def test_schema_only_plan_needs_no_target_data_connection(tmp_path):
    result = subprocess.run(command(tmp_path, prepare(tmp_path, 'schema')), capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    assert report['requiredCount'] == 0 and report['sshStarted'] is False


def test_tampered_plan_cannot_remove_required_checks(tmp_path):
    files = prepare(tmp_path)
    evidence = files[2]
    value = json.loads(evidence.read_text(encoding='utf-8'))
    value['planner']['items'] = []
    evidence.write_text(json.dumps(value), encoding='utf-8')
    result = subprocess.run(command(tmp_path, files), capture_output=True, text=True, encoding='utf-8')
    assert result.returncode != 0
    report = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    assert report['sshStarted'] is False
    assert report['errorCode'] == 'TARGET_PREFLIGHT_INPUT_INVALID'


def test_existing_reference_without_executed_result_never_passes():
    from ops.release.release_migration_preflight import MigrationPreflightError, run_migration_preflight
    migration = {'migrationId': 'm1', 'file': 'required-sql/m1.sql', 'type': 'data',
                 'targetPreflight': {'reference': 'target-preflight/m1.sql', 'sha256': 'a'*64, 'readOnly': True}}
    with pytest.raises(MigrationPreflightError, match='TARGET_PREFLIGHT_RESULT_MISSING'):
        run_migration_preflight([migration])


def load_runner(monkeypatch):
    monkeypatch.syspath_prepend(str(RUNNER.parent))
    import importlib
    return importlib.import_module('release_target_data_preflight')


def write_check(tmp_path, query):
    folder = tmp_path / 'target-preflight'
    folder.mkdir(exist_ok=True)
    path = folder / '20260908_contract.preflight.sql'
    path.write_text('-- release-target-preflight: migrationId=20260908_contract; allowedEnvironments=test,prod,backup\n' + query, encoding='utf-8')
    return path


@pytest.mark.parametrize('query', [
    "SELECT 'TARGET_PREFLIGHT_PASS:20260908_contract'; DELETE FROM t;",
    "SELECT 'TARGET_PREFLIGHT_PASS:20260908_contract' INTO OUTFILE '/tmp/stolen';",
    "SELECT 'TARGET_PREFLIGHT_PASS:20260908_contract'; /*!50000 DELETE FROM t */",
    "SELECT 'TARGET_PREFLIGHT_PASS:20260908_contract' WHERE GET_LOCK('r', 0);",
    "SELECT 'TARGET_PREFLIGHT_PASS:20260908_contract'\n\\! mysql -uroot -e 'DELETE FROM probe'\n;",
    "SELECT 'TARGET_PREFLIGHT_PASS:20260908_contract'\n\\. /tmp/write.sql\n;",
    "SELECT 'TARGET_PREFLIGHT_PASS:20260908_contract'\nDELIMITER //\n;",
    "SELECT 'TARGET_PREFLIGHT_PASS:20260908_contract'\n# '\n;\nROLLBACK;\nSET SESSION TRANSACTION READ WRITE;\nCREATE TABLE unexpected_write(id INT);\n# '\n",
    "SELECT 'TARGET_PREFLIGHT_PASS:20260908_contract' -- '\n;\nROLLBACK;\nDELETE FROM probe;\n-- '\n",
])
def test_write_and_executable_comment_queries_rejected_before_ssh(tmp_path, monkeypatch, query):
    module = load_runner(monkeypatch)
    files = prepare(tmp_path)
    write_check(tmp_path, query)
    def forbidden_query(*args):
        pytest.fail('Unsafe SQL reached SSH')
    monkeypatch.setattr(module, '_query', forbidden_query)
    assert module.main(command(tmp_path, files)[4:]) != 0
    report = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    assert report['sshStarted'] is False


@pytest.mark.parametrize('reply', ['', 'TARGET_PREFLIGHT_BLOCKED:20260908_contract',
                                  'TARGET_PREFLIGHT_PASS:another',
                                  'TARGET_PREFLIGHT_PASS:20260908_contract\nextra-row'])
def test_only_exact_executed_pass_marker_is_accepted(tmp_path, monkeypatch, reply):
    module = load_runner(monkeypatch)
    files = prepare(tmp_path)
    write_check(tmp_path, "SELECT CASE WHEN (SELECT COUNT(*) FROM system_menu)=1 THEN 'TARGET_PREFLIGHT_PASS:20260908_contract' ELSE 'BLOCKED' END;")
    monkeypatch.setattr(module, '_query', lambda *args: reply)
    assert module.main(command(tmp_path, files)[4:]) == 2
    report = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    assert report['errorCode'] == 'TARGET_PREFLIGHT_FAILED'
    assert report['passedCount'] == 0


def test_success_binds_sql_plan_and_actual_result(tmp_path, monkeypatch):
    import hashlib
    module = load_runner(monkeypatch)
    files = prepare(tmp_path)
    query = write_check(tmp_path, "SELECT CASE WHEN (SELECT COUNT(*) FROM system_menu)=1 THEN 'TARGET_PREFLIGHT_PASS:20260908_contract' ELSE 'BLOCKED' END;")
    calls = []
    def query_result(server, user, content):
        calls.append(content)
        return 'TARGET_PREFLIGHT_PASS:20260908_contract'
    monkeypatch.setattr(module, '_query', query_result)
    assert module.main(command(tmp_path, files)[4:]) == 0
    report = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    assert len(calls) == report['passedCount'] == report['requiredCount'] == 1
    assert report['checks'][0]['checkSha256'] == hashlib.sha256(query.read_bytes()).hexdigest()
    assert report['preflightFingerprint'] == json.loads(files[2].read_text(encoding='utf-8'))['bindings']['preflightFingerprint']


def test_ssh_executes_utf8_query_in_readonly_transaction_without_inline_secrets(monkeypatch):
    import base64
    import re
    module = load_runner(monkeypatch)
    calls = []
    def process(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, b'TARGET_PREFLIGHT_PASS:m1\n', b'')
    monkeypatch.setattr(module.subprocess, 'run', process)
    query = "SELECT '中文';".encode('utf-8')
    assert module._query('127.0.0.1', 'fixture', query) == 'TARGET_PREFLIGHT_PASS:m1'
    args, kwargs = calls[0]
    assert args[-1] == 'bash -s' and 'StrictHostKeyChecking=yes' in args
    script = kwargs['input'].decode('utf-8')
    assert '--binary-mode' in script
    encoded = re.search("printf '%s' '([^']+)'", script)[1]
    sql = base64.b64decode(encoded)
    assert sql.startswith(b'SET SESSION TRANSACTION READ ONLY;\nSTART TRANSACTION READ ONLY;\n')
    assert query in sql and sql.endswith(b'ROLLBACK;\n')
    assert kwargs['timeout'] == 90


def test_target_data_preflight_is_invoked_before_rehearsal_and_packaging():
    script = (ROOT / 'ops/deploy/publish-int-ruoyi.ps1').read_text(encoding='utf-8')
    flow = script[script.index("if ($Mode -ne 'deploy-release')"):]
    assert flow.index('\nInvoke-BuildReleaseTargetPreflight') < flow.index('\nInvoke-BuildReleaseTargetDataPreflight')
    assert flow.index('\nInvoke-BuildReleaseTargetDataPreflight') < flow.index('\nInvoke-BuildReleaseSchemaOnlyMigrationRehearsal')
    assert flow.index('\nInvoke-BuildReleaseTargetDataPreflight') < flow.index("Info 'Building backend jar'")


def test_new_runtime_regressions_are_mandatory_build_gates():
    script = (ROOT / 'ops/deploy/publish-int-ruoyi.ps1').read_text(encoding='utf-8')
    start = script.index('function Invoke-StandardReleaseContractTests')
    body = script[start:script.index('\nfunction ', start + 1)]
    assert 'Assert-ApplicationMigrationTestsDiscovered' in body
    assert 'MIGRATION_TEST_MISSING' in script
    assert 'test_test_tenant1_all_role_permission_sync_sql.py' not in body
    for name in ('test_release_docker_context_cleanup.py', 'test_release_target_data_preflight.py',
                 'test_release_migration_preflight_matrix.py', 'test_release_schema_rehearsal.py',
                 'test_release_build_preflight_cache.py'):
        assert name in body


def test_application_migration_discovery_ignores_target_preflight_support_sql():
    script = (ROOT / 'ops/deploy/publish-int-ruoyi.ps1').read_text(encoding='utf-8')
    start = script.index('function Assert-ApplicationMigrationTestsDiscovered')
    body = script[start:script.index('\nfunction ', start + 1)]
    assert "IntRuoyiBackend/sql/mysql/target-preflight/" in body
    assert "-notmatch" in body


def test_source_approval_commits_are_required_and_forwarded_to_release_script():
    script = (ROOT / 'ops/deploy/publish-int-ruoyi.ps1').read_text(encoding='utf-8')
    assert '[string]$ExpectedMaintenanceCommit' in script
    assert '[string]$ExpectedApplicationCommit' in script
    assert '[string]$ExpectedFrontendCommit' in script
    assert '[string]$SourceSelectionId' in script
    assert 'SOURCE_APPROVED_COMMIT_MISMATCH' in script
    assert 'SOURCE_APPROVAL_REQUIRED' in script
