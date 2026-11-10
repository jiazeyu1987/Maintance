"""Formal MAIN producer/clear/history wiring, real original metadata and locks.

External Docker/SQL replies remain finite protocol units, not server evidence.
"""
from copy import deepcopy
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_recovery_program_restore import (case,restore_case,run,freeze_inputs)
from recovery_engine import RecoveryError,write
from repository_records import RepositoryError


def test_registered_policy_is_admitted_before_first_protection_stop_import_or_clear(restore_case,monkeypatch):
    h=restore_case
    # Separate complete owner reservation; never rewrite the previous one.
    operations=h.case['root']/'preservation-contract-operations';operations.mkdir(mode=0o700)
    h.root=operations/h.request['operationId'];h.root.mkdir(mode=0o700)
    host=h.case['root']/'preservation-contract-host';host.mkdir(mode=0o700)
    import recovery_resource_admission as admission
    monkeypatch.setattr(admission,'HOST_ROOT',host)
    h.owner['operationsRoot']=str(operations)
    h.owner['targets']['target57']['replacement']['storage']['protectedRoots'].append(str(operations))
    h.case['policy']['baselineTargetPin']=write(h.case['root']/'preservation-contract-target.json',h.owner['targets']['target57'])
    h.owner['targetProgramPolicies']['target57']=deepcopy(h.case['policy'])
    invalid=write(h.root/'invalid-preservation-policy.json',{})
    h.owner['targetPreservationPolicies']={'target57':invalid}
    freeze_inputs(h)
    with pytest.raises(RepositoryError,match='REPOSITORY_CONFIG_SCHEMA_INVALID'):
        run(h)
    # Actual original producer and epoch entry were exercised; an invalid
    # policy must not dispatch any writer protection, stop, image load or DROP.
    assert h.events and any(row[0]=='begin-restore' for row in h.events)
    assert not any(len(row)==4 and row[-1] is True for row in h.events)


def test_first_clear_requires_final_proof_before_any_bound_or_write():
    import recovery_replace as replacement
    calls=[]
    class View:
        phase='RESTORE'
        _context=SimpleNamespace()
        def guard_native(self,native):calls.append('guard')
    native=SimpleNamespace(native_context=View(),bound=lambda:calls.append('bound'))
    with pytest.raises(RecoveryError,match='PRESERVATION_CONTEXT_REQUIRED'):
        replacement.clear(native,{})
    assert calls==['guard']
