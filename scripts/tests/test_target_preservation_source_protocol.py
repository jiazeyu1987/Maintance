"""Finite CLIENT protocol only; actual Python processes, no Docker/server.

The original Linux FULL assertions remain the lifecycle acceptance. These
tests isolate the dump fault's argv scope; actualBusinessRestore=False.
"""
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'scripts/tests/test_recovery_target_capture_session.py'
MYSQL = 'a'*64
PROBE = ['exec', MYSQL, 'sh', '-ec',
    'for program in mysql sh timeout mysqldump; do command -v "$program" >/dev/null || exit 1; done']


def client_literal():
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    values = [ast.literal_eval(node.value) for node in tree.body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
            and target.id == 'CLIENT' for target in node.targets)]
    assert len(values) == 1
    return values[0]


def dump_arguments():
    # Execute the actual formal argument builder, preserving its credential
    # shell, exec -i shape and formal-mysql marker. No SQL/client is invoked here.
    path = ROOT/'ops/backup_engine/formal/formal_snapshot_linux.py'
    spec = importlib.util.spec_from_file_location('full_source_protocol_formal', path)
    formal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(formal)
    mysql = object.__new__(formal.PrivateDockerMySql)
    mysql.container = MYSQL
    argv = mysql._command('timeout --signal=TERM --kill-after=5 10s mysqldump',
        ['-uroot', '--single-transaction', '--routines', '--triggers', '--events',
         '--hex-blob', '--set-gtid-purged=OFF', '--default-character-set=utf8mb4', 'app'])
    assert argv[0] == 'docker'
    return argv[1:]


def run_client(tmp_path, argv, *, failure):
    state = tmp_path/'state.json'
    original = json.dumps(dict(dumpFailure=failure, flags=['0', '0'], actions=[],
        containers={MYSQL: dict(running=True)}), sort_keys=True).encode('utf-8')
    state.write_bytes(original)
    script = tmp_path/'finite-client.py'
    script.write_text(client_literal().replace('#!PYTHON', '#!'+sys.executable)
        .replace('STATE', repr(str(state))), encoding='utf-8')
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(script), *argv],
        input=b'finite-protocol-password\n', stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=10, check=False)
    assert state.read_bytes() == original, 'PROBE_OR_DUMP_MUTATED_SOURCE_STATE'
    return result


def test_full_dump_failure_does_not_fail_the_real_dependency_probe(tmp_path):
    result = run_client(tmp_path, PROBE, failure=True)
    assert (result.returncode, result.stdout, result.stderr) == (0, b'', b''), \
        'DEPENDENCY_PROBE_WRONGLY_INJECTED_AS_DUMP_FAILURE'


def test_real_dump_failure_keeps_actual_exit_9(tmp_path):
    result = run_client(tmp_path, dump_arguments(), failure=True)
    assert (result.returncode, result.stdout, result.stderr) == (9, b'', b'')


def test_real_dump_success_keeps_original_sql_bytes(tmp_path):
    result = run_client(tmp_path, dump_arguments(), failure=False)
    assert (result.returncode, result.stdout, result.stderr) == (
        0, b'-- finite SQL protocol; no real database'+os.linesep.encode('ascii'), b'')


def test_unknown_mysqldump_text_is_not_an_export(tmp_path):
    result = run_client(tmp_path, ['exec', MYSQL, 'sh', '-ec',
        'printf "%s" mysqldump'], failure=False)
    assert result.returncode != 0, 'UNKNOWN_EXEC_COMMAND_RETURNED_FAKE_DUMP_SUCCESS'
    assert result.stdout == b''
    assert b'unhandled SQL protocol' in result.stderr


def test_actual_ip_protocol_uses_fixed_5_second_limit_without_state_changes(tmp_path):
    state = tmp_path/'state.json'
    original = b'{"containers":{},"actions":[],"flags":["0","0"]}'
    state.write_bytes(original)
    script = tmp_path/'ip'
    script.write_text(client_literal().replace('#!PYTHON', '#!'+sys.executable)
        .replace('STATE', repr(str(state))), encoding='utf-8')
    started = time.monotonic()
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(script),
        '-o', 'address', 'show'], input=b'', stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=5, check=False)
    elapsed = time.monotonic()-started
    assert (result.returncode, result.stdout, result.stderr) == (
        0, b'1: lo inet 127.0.0.1/8 scope host lo'+os.linesep.encode(), b'')
    assert elapsed < 5 and state.read_bytes() == original
    print('ACTUAL_IP_PROTOCOL_SECONDS=%.6f'%elapsed)


@pytest.mark.parametrize('failure', ['os-error', 'timeout'])
def test_endpoint_preserves_launch_and_timeout_failure_contract(monkeypatch, failure):
    # Finite transport-error classification only. The real endpoint method,
    # source address/parser and unchanged five-second limit remain in use;
    # this unit seam cannot identify the exception discarded by old r5.
    formal = ROOT/'ops/backup_engine/formal'
    monkeypatch.syspath_prepend(str(formal))
    import formal_capture_semantics as semantics
    import formal_filesystem_watchdog as watchdog
    assert Path(semantics.__file__).resolve().parent == formal.resolve()
    monkeypatch.setattr(watchdog, 'require_native_runtime', lambda:None)
    source = dict(endpoint='http://127.0.0.1:9000', containerPort=9000,
        minioContainerId='a'*64)
    seen = []
    def run(argv, **kwargs):
        seen.append((argv, kwargs))
        assert kwargs['timeout'] <= 5 and kwargs['check'] is False
        if argv[0] == 'docker':
            return subprocess.CompletedProcess(argv, 0, json.dumps(dict(
                id=source['minioContainerId'], running=True, networks={},
                ports={'9000/tcp':[dict(HostIp='127.0.0.1', HostPort='9000')]})).encode(), b'')
        assert argv == ['ip', '-o', 'address', 'show']
        if failure == 'os-error':
            raise OSError('finite endpoint launch refusal')
        raise subprocess.TimeoutExpired(argv, kwargs['timeout'], output=b'')
    monkeypatch.setattr(semantics.subprocess, 'run', run)
    with pytest.raises(semantics.snapshot.FormalSnapshotError,
            match='^FORMAL_CAPTURE_SEMANTIC_ENDPOINT_OBSERVATION_FAILED$'):
        semantics.SemanticCapture.verify_endpoint(
            type('EndpointProtocol', (), {'source':source})(), lambda:None)
    assert len(seen) == 2


@pytest.mark.parametrize('failure', ['os-error', 'timeout'])
@pytest.mark.parametrize('endpoint', [True, False])
def test_endpoint_diagnostic_rethrows_identical_error_without_recording_other_commands(
        capsys, failure, endpoint):
    path = ROOT/'scripts/tests/test_target_preservation_packaged_source.py'
    tree = ast.parse(path.read_bytes())
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name=='endpoint_run']
    assert len(nodes) == 1
    method = ast.Module(body=nodes, type_ignores=[])
    command = ['ip', '-o', 'address', 'show'] if endpoint else ['unrelated-protocol']
    error = (OSError('private diagnostic must not be printed') if failure=='os-error'
        else subprocess.TimeoutExpired(command, 5, output=b'private partial output'))
    def refused(argv, *args, **kwargs):
        assert argv is command and kwargs == {'timeout':5}
        raise error
    namespace = dict(subprocess=subprocess, time=time, json=json,
        endpoint_commands={('ip', '-o', 'address', 'show'):'IP_ADDRESS'}, original_run=refused)
    exec(compile(method, str(path), 'exec'), namespace)
    with pytest.raises(type(error)) as caught:
        namespace['endpoint_run'](command, timeout=5)
    assert caught.value is error
    output = capsys.readouterr()
    assert output.err == ''
    if not endpoint:
        assert output.out == ''
    else:
        assert output.out.startswith('ACTUAL_ENDPOINT_PROCESS_FAILURE=')
        facts = json.loads(output.out.split('=', 1)[1])
        assert set(facts) == {'commandRole', 'category', 'errorClass', 'timeoutSeconds', 'elapsedSeconds'}
        assert facts['commandRole']=='IP_ADDRESS' and facts['timeoutSeconds']==5
        assert facts['category']==('OS_ERROR' if failure=='os-error' else 'TIMEOUT')
        assert 0 <= facts['elapsedSeconds'] < 1
        assert 'private' not in output.out and 'unrelated' not in output.out
