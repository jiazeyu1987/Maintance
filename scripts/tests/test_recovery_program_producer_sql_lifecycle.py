"""Negative SQL-lifecycle cases starting from the actual MAIN producer.

The imported fixture runs real worker/runtime/program producer, physical locks,
context/custody, SQL staging/expansion/import subprocesses and cleanup. External
SQL/Docker/object/kernel semantics remain finite local protocols with
actualBusinessRestore=False. Successful envelopes are never manufactured here.
Only the operation's real SQL staging or its real cleanup receipt is corrupted.
"""
from copy import deepcopy
import os
from pathlib import Path
import sys

import pytest

from test_recovery_program_generation import case
from test_recovery_program_restore import restore_case
from test_recovery_program_producer_contract import (
    producer_case, invoke, receipt_and_native, validate)
from recovery_engine import RecoveryError, pin, pinned_json, write


pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
    reason='real Linux SQL staging identity, context/custody and cleanup contracts')


@pytest.mark.parametrize('drift', ['contents', 'same-content-new-inode'])
def test_actual_imported_sql_drift_prevents_cleanup_success(producer_case, monkeypatch, drift):
    """BDD: actual importer succeeded; staged bytes/inode change -> retain failure, never clean as success."""
    h = producer_case
    original_import = h.native_type.import_sql
    h.sql_drift = None

    def import_then_drift(native, path, checksum):
        value = original_import(native, path, checksum)
        if h.sql_drift is None:
            before, raw = path.stat(), path.read_bytes()
            imported = h.sql_received[-1].read_bytes()
            assert raw == imported and raw.startswith(b'SET SESSION sql_log_bin=1;\n')
            if drift == 'contents':
                path.write_bytes(raw+b'-- changed after the actual successful importer\n')
                assert path.stat().st_ino == before.st_ino and path.read_bytes() != imported
            else:
                replacement = path.with_name(path.name+'.changed-inode')
                replacement.write_bytes(raw); replacement.chmod(0o600)
                os.replace(replacement, path)
                assert path.stat().st_ino != before.st_ino and path.read_bytes() == imported
            h.sql_drift = dict(path=path, original=deepcopy(h.sql_inputs[-1]),
                originalInode=before.st_ino, actual=pin(path))
        return value

    monkeypatch.setattr(h.native_type, 'import_sql', import_then_drift)
    actual_exit, result = invoke(h)
    assert h.sql_drift is not None
    # The local protocol test does not prescribe whether an external boundary
    # adds conservative uncertainty; neither permitted failure terminal grants
    # a success receipt, cleanup authorization, release or another data replay.
    assert (actual_exit, result['state']) in ((1, 'FAILED_RETAINED'), (2, 'TERMINAL_UNKNOWN'))
    assert result['data']['partialTargetRetained'] is True and result['data']['retryPermitted'] is False
    receipt, native = receipt_and_native(h, result)
    assert receipt['state'] == 'FAILED_RETAINED'
    sql = [row for row in native['invocations']
        if row['intentObservation']['schemaVersion'] == 'RecoverySqlImporter/v2']
    assert sql and sql[0]['terminalObservation']['actualExitCode'] == 0
    assert sql[0]['terminalObservation']['sqlPin'] == h.sql_drift['original']
    assert h.sql_drift['path'].is_file()
    assert not (h.root/'sql-staging-cleanup.json').exists()
    assert not (h.root/'resource-release.json').exists() and not h.transport.releases
    assert not any(row[:2] == ('data-chain', 'START_APPLICATION') for row in h.events)


@pytest.mark.parametrize('corruption', ['missing-result', 'wrong-operation', 'wrong-sql-pin', 'intent-as-result'])
def test_actual_cleanup_history_rejects_missing_or_corrupted_original_receipt(producer_case, corruption):
    """BDD: real producer cleaned SQL and validated; original cleanup receipt corruption -> history refuses."""
    h = producer_case
    actual_exit, result = invoke(h)
    assert actual_exit == 0 and result['state'] == 'SUCCEEDED'
    receipt, native = receipt_and_native(h, result)
    sql = [row['intentObservation']['sqlPin'] for row in native['invocations']
        if row['intentObservation']['schemaVersion'] == 'RecoverySqlImporter/v2']
    assert len(sql) == 2 and all(not os.path.lexists(item['path']) for item in sql)
    cleanup_path = h.root/'sql-staging-cleanup.json'
    cleanup_pin = pin(cleanup_path)
    cleanup = pinned_json(cleanup_pin)
    assert cleanup['state'] == 'SUCCEEDED' and cleanup['operationId'] == h.request['operationId']
    assert cleanup['deletedSqlPins'] == sql
    assert result['data']['programSqlCleanupPin'] == receipt['programSqlCleanupPin'] == cleanup_pin
    assert validate(h)['resultState'] == 'SUCCEEDED'
    fixed = {Path(reference['path']):Path(reference['path']).read_bytes() for reference in
        (result['data']['replacementReceiptPin'],result['data']['programNativeEvidencePin'],
         result['data']['programProtectionCustodyPin'])}
    if corruption == 'missing-result':
        cleanup_path.unlink()
        assert (h.root/'sql-staging-cleanup-intent.json').is_file()
    elif corruption == 'wrong-operation':
        cleanup['operationId'] = 'foreign-operation'
        write(cleanup_path, cleanup)
    elif corruption == 'wrong-sql-pin':
        cleanup['deletedSqlPins'][0] = dict(sql[0], sha256='0'*64)
        write(cleanup_path, cleanup)
    else:
        # An actual planned intent cannot replace the actual successful result.
        planned = pinned_json(pin(h.root/'sql-staging-cleanup-intent.json'))
        assert planned['state'] == 'PLANNED'
        write(cleanup_path, planned)
    with pytest.raises(RecoveryError):
        validate(h)
    assert all(path.read_bytes() == original for path,original in fixed.items())
    assert all(not os.path.lexists(item['path']) for item in sql)
    assert not (h.root/'resource-release.json').exists()
