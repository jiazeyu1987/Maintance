"""Separate already-verified unknown causes without granting resource release.

The shared fixture runs the actual Linux context, locks, private journals,
native/SQL subprocesses and ProtectionCustody. Its external database, Docker
and worker envelopes remain explicit protocol boundaries, not a live restore.
"""
from pathlib import Path
import sys

import pytest

from test_recovery_program_evidence import history_factory, publish_envelopes, validate
from recovery_engine import pinned_json, write


pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
    reason='actual Linux program history, private files, flock and subprocesses')


def causes(*, native=False, outer=False):
    return dict(native=native, programSwitch=False, programImport=False,
        outerConservative=outer)


def same_protection(h, proof):
    assert h.custody is not None
    assert proof['protectionState'] == h.custody['state']
    assert proof['protectionStates'] == h.custody['protections']
    assert not any('unknown' in step or 'terminalUnknown' in step
        for step in proof['protectionStates'].values())
    for kind, original in h.custody['protections'].items():
        for field in ('failedMethod', 'errorCode'):
            assert (field in proof['protectionStates'][kind]) == (field in original)


@pytest.mark.parametrize('outcome,is_unknown', [('sql-failure', False), ('unknown', True)])
def test_actual_sql_failure_and_unknown_have_separate_verified_cause_facts(history_factory, outcome, is_unknown):
    h = history_factory(outcome=outcome)
    sql = next(row['terminalObservation'] for row in h.native['invocations']
        if row['intentObservation']['schemaVersion'] == 'RecoverySqlImporter/v2')
    assert sql['actualExitCode'] == (None if is_unknown else 7)
    assert h.native['terminalUnknown'] is is_unknown
    proof = validate(h)
    assert proof['unknownCauses'] == causes(native=is_unknown)
    assert proof['terminalUnknown'] is is_unknown
    assert proof['protectionState'] == 'ACTIVE'
    assert proof['protectionStates']['scheduler']['state'] == 'INSTALLED'
    same_protection(h, proof)


def test_constructor_before_custody_does_not_invent_absent_or_successful_protection(history_factory):
    h = history_factory(outcome='constructor-before-custody')
    assert h.native['invocations'] == [] and h.custody is None
    proof = validate(h)
    assert proof['unknownCauses'] == causes()
    assert proof['protectionState'] is None and proof['protectionStates'] is None
    assert proof['phase'] == 'PREPARATION' and proof['terminalUnknown'] is False


def test_outer_conservative_unknown_does_not_relabel_known_native_exit(history_factory):
    h = history_factory(outcome='sql-failure', complete_epoch=False)
    assert h.native['lastExitCode'] == 7 and h.native['terminalUnknown'] is False
    # Explicit producer-envelope protocol: preserve the original native/custody
    # snapshots, while recording an additional conservative terminal unknown.
    publish_envelopes(h, receipt_changes={'terminalUnknown': True})
    worker = pinned_json(h.result_pin)
    worker.update(state='TERMINAL_UNKNOWN', actualExitCode=2)
    worker['data']['terminalUnknown'] = True
    h.result_pin = write(Path(h.result_pin['path']), worker)
    proof = validate(h)
    assert proof['unknownCauses'] == causes(outer=True)
    assert proof['terminalUnknown'] is True and proof['lastExitCode'] == 7
    same_protection(h, proof)
    assert not any(key in proof for key in ('releasePermitted', 'retryPermitted', 'targetReady'))


def test_released_protection_facts_are_exact_copies_of_real_custody_journals(history_factory):
    h = history_factory()
    assert h.custody['state'] == 'RELEASED'
    proof = validate(h)
    assert proof['unknownCauses'] == causes()
    same_protection(h, proof)
    assert proof['protectionStates']['scheduler']['state'] == 'RELEASED'
    assert proof['protectionStates']['scheduler']['releasePin'] == h.custody['protections']['scheduler']['releasePin']
