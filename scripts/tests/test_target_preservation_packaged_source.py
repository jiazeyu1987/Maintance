"""Original FULL lifecycle assertions, actual SAFE worker, finite S3/SQL only.

No server is contacted; actualBusinessRestore=False. The original three tests
and their real exporter/restoration assertions are imported without changes.
"""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import time
import urllib.error

import pytest

from test_recovery_target_capture_session import (
    case, restore_case, capture_protocol as base_capture_protocol,
    test_original_full_real_material_path_always_restores_source as original_full_lifecycle)
from test_target_preservation_packaged_capture import builder, safe_payload, safe_candidate_directory


def absent_configuration(bucket, configuration, error_code, *, client_type=None, error_raw=None):
    # Same three finite 404/error payloads as publication_case. Use the real
    # read-only GET parser as well, so an unexpected error cannot become success.
    codes = {'lifecycle':'NoSuchLifecycleConfiguration',
        'replication':'ReplicationConfigurationNotFoundError',
        'encryption':'ServerSideEncryptionConfigurationNotFoundError'}
    assert bucket == 'private' and codes[configuration] == error_code
    raw = (('<Error><Code>'+error_code+'</Code></Error>').encode()
        if error_raw is None else error_raw)
    if client_type is None:
        from formal_s3_export import ReadOnlyS3
        client_type = ReadOnlyS3
    client = client_type('http://127.0.0.1:9000', 'finite-access', 'finite-secret')
    response = io.BytesIO(raw)
    def opened(request):
        assert request.get_method() == 'GET'
        assert request.full_url == 'http://127.0.0.1:9000/private?'+configuration+'='
        raise urllib.error.HTTPError(request.full_url, 404, 'finite absence', {}, response)
    client._open = opened
    result = client.absent_configuration(bucket, configuration, error_code)
    assert response.closed
    assert result == dict(bucket=bucket, configuration=configuration, httpStatus=404,
        errorCode=error_code, rawSha256=hashlib.sha256(raw).hexdigest(), rawBytes=len(raw)), \
        'FINITE_S3_ABSENCE_RAW_CHANGED'
    return result


@pytest.fixture
def capture_protocol(base_capture_protocol, monkeypatch):
    # External protocol extension only. All original budgets/commands/source
    # restoration semantics and all three imported test assertions remain.
    import minimal_capture_support as support
    original = support.ReadOnlyS3
    class SafeS3Protocol(original):
        def absent_configuration(self, bucket, configuration, error_code):
            return absent_configuration(bucket, configuration, error_code)
    monkeypatch.setattr(support, 'ReadOnlyS3', SafeS3Protocol)
    return base_capture_protocol


@pytest.mark.parametrize('failure', [None, 'dump', 'restore'])
def test_original_full_real_material_path_always_restores_source(capture_protocol, monkeypatch, failure):
    # Delegate the unchanged original assertions and actual SAFE worker. Keep
    # only the original code/stage, never SQL/credentials or an invented trace.
    import minimal_capture_worker as worker
    source = capture_protocol.capture_config['source']
    template = '{"id":{{json .Id}},"running":{{json .State.Running}},"ports":{{json .NetworkSettings.Ports}},"networks":{{json .NetworkSettings.Networks}}}'
    endpoint_commands = {('ip', '-o', 'address', 'show'):'IP_ADDRESS',
        ('docker', 'inspect', '--format', template, '--', source['minioContainerId']):'MINIO_INSPECT'}
    original_run = subprocess.run
    def endpoint_run(argv, *args, **kwargs):
        role = endpoint_commands.get(tuple(argv)) if type(argv) in (list, tuple) else None
        started = time.monotonic()
        try:
            return original_run(argv, *args, **kwargs)
        except (OSError, subprocess.TimeoutExpired) as error:
            if role is not None:
                facts = dict(commandRole=role,
                    category='TIMEOUT' if isinstance(error, subprocess.TimeoutExpired) else 'OS_ERROR',
                    errorClass=type(error).__name__, timeoutSeconds=kwargs.get('timeout'),
                    elapsedSeconds=round(time.monotonic()-started, 6))
                print('ACTUAL_ENDPOINT_PROCESS_FAILURE='+json.dumps(facts, sort_keys=True), flush=True)
            raise
    monkeypatch.setattr(subprocess, 'run', endpoint_run)
    original_capture = worker.capture
    failures = []
    def captured(*args, **kwargs):
        try:
            return original_capture(*args, **kwargs)
        except BaseException as error:
            diagnostic = getattr(error, 'diagnostic', None) or {}
            facts = dict(errorCode=getattr(error, 'code', None),
                captureStage=diagnostic.get('captureStage'))
            failures.append((error, facts))
            print('ACTUAL_SOURCE_CAPTURE_FAILURE='+json.dumps(facts, sort_keys=True), flush=True)
            raise
    monkeypatch.setattr(worker, 'capture', captured)
    original_full_lifecycle(capture_protocol, failure)
    if failure == 'dump':
        assert len(failures) == 1
        assert failures[0][1] == dict(errorCode='FORMAL_CAPTURE_CHILD_FAILED',
            captureStage='DATABASE_CAPTURE')


@pytest.mark.parametrize('problem', ['valid', 'error-code', 'raw-sha'])
def test_safe_finite_absence_protocol_preserves_actual_error_and_raw_pin(
        safe_candidate_directory, safe_payload, monkeypatch, problem):
    path = safe_candidate_directory/'formal/formal_s3_export.py'
    spec = importlib.util.spec_from_file_location('actual_safe_source_s3_protocol', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert Path(module.__file__).read_bytes() == safe_payload['formal/formal_s3_export.py']
    if problem == 'raw-sha':
        original = module.ReadOnlyS3._get
        def changed(self, *args, **kwargs):
            result = original(self, *args, **kwargs)
            return dict(result, rawSha256='f'*64)
        monkeypatch.setattr(module.ReadOnlyS3, '_get', changed)
    options = dict(client_type=module.ReadOnlyS3)
    if problem == 'error-code':
        options['error_raw'] = b'<Error><Code>AccessDenied</Code></Error>'
        with pytest.raises(module.FormalSnapshotError, match='^FORMAL_S3_CONFIG_ABSENCE_UNPROVEN$'):
            absent_configuration('private', 'lifecycle', 'NoSuchLifecycleConfiguration', **options)
    elif problem == 'raw-sha':
        with pytest.raises(AssertionError, match='FINITE_S3_ABSENCE_RAW_CHANGED'):
            absent_configuration('private', 'lifecycle', 'NoSuchLifecycleConfiguration', **options)
    else:
        for configuration, code in (
            ('lifecycle', 'NoSuchLifecycleConfiguration'),
            ('replication', 'ReplicationConfigurationNotFoundError'),
            ('encryption', 'ServerSideEncryptionConfigurationNotFoundError')):
            result = absent_configuration('private', configuration, code, **options)
            assert result['httpStatus'] == 404 and result['errorCode'] == code
