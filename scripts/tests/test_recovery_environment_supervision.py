"""W05 helper source admission and FD lifetime regression checks."""
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ops/recovery'))
from recovery_environment import validate_configuration
from recovery_environment_contract import EnvironmentFailure
from recovery_environment_supervisor import OwnedChildSupervisor
from test_recovery_environment_fixtures import LocalRecords


def test_new_helper_must_be_selected_before_any_runtime_dispatch(tmp_path):
    records=LocalRecords(tmp_path)
    records.policy['moduleSourcePins']=[ref for ref in records.policy['moduleSourcePins']
        if not ref['path'].endswith('recovery_environment_supervisor.py')]
    with pytest.raises(EnvironmentFailure,match='EXECUTOR_SOURCE_PINS_INCOMPLETE'):
        validate_configuration(records.config,records.policy,records.trust,lambda:None)


@pytest.mark.skipif(sys.platform!='linux',reason='Native socket/FD reuse check runs in .59 fixture')
def test_invalid_pass_fd_cannot_become_private_control_channel(monkeypatch):
    called=[]
    import recovery_environment_supervisor as module
    monkeypatch.setattr(module.socket,'socketpair',lambda:called.append(True))
    supervisor=OwnedChildSupervisor([sys.executable,'-c','pass'],env={},stdin=None,pass_fds=(1000000,))
    with pytest.raises(OSError):
        supervisor.spawn()
    assert not called and supervisor.process is None
