"""Explicit transport protocol fixtures, not real stage or server acceptance."""
import hashlib
import json

import pytest

import main_program_control_staging as subject
from test_main_program_control_staging_finalize import DIAGNOSTIC, recorded, prepared_records, originals


@pytest.mark.parametrize('stderr,accepted', [(DIAGNOSTIC, True), (b'permission denied\r\n', False),
                                          (DIAGNOSTIC + b'other warning\r\n', False)])
def test_new_dispatch_preserves_diagnostic_and_rejects_unknown_stderr(recorded, stderr, accepted):
    case = recorded
    journal = case['private'] / 'explicit-new-attempt'
    journal.mkdir()
    original_attempt = (case['private'] / (case['stem'] + '-attempt.private.json')).read_bytes()
    calls = []

    def transport(host, payload):
        calls.append(host)
        return dict(stdout=subject.canonical(case['result']) + b'\n', stderr=stderr, returncode=0, timedOut=False)

    if accepted:
        reply = subject.dispatch_prepared(case['task'], journal, case['prepared'], transport=transport)
        assert reply['status'] == 'STAGED_NOT_ACTIVATED'
        for name in ('engineReportFile', 'configurationReportFile'):
            core = json.loads((case['task'] / case['prepared'][name]).read_bytes())
            evidence = core['transportEvidencePin']
            raw = (journal / (case['stem'] + '-transport.private.json')).read_bytes()
            assert evidence['sha256'] == hashlib.sha256(raw).hexdigest()
            assert evidence['bytes'] == len(raw)
    else:
        with pytest.raises(ValueError, match='REMOTE_STAGE_FAILED'):
            subject.dispatch_prepared(case['task'], journal, case['prepared'], transport=transport)
        assert not (case['task'] / case['prepared']['engineReportFile']).exists()
        assert not (case['task'] / case['prepared']['configurationReportFile']).exists()
    assert calls == ['172.30.30.58']
    assert (journal / (case['stem'] + '-stderr.private.log')).read_bytes() == stderr
    assert (case['private'] / (case['stem'] + '-attempt.private.json')).read_bytes() == original_attempt
    with pytest.raises(ValueError, match='ATTEMPT_OR_REPORT_EXISTS'):
        subject.dispatch_prepared(case['task'], journal, case['prepared'], transport=transport)
    assert calls == ['172.30.30.58']
