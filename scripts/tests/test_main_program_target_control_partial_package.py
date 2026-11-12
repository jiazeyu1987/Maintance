"""Bounded package growth preserves the admitted predecessor byte contract."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from test_main_program_target_control_successor import subject, package_build
from test_main_program_target_control_successor_repeat import repeated_inputs, payload


def package154(k):
    files=payload(k['package_raw']);files['common/recovery_program_retry.py']=b'RETRY=True\n'
    build,raw,_=package_build(files,'9'*40);build['packages'][0]['fileCount']=154
    return build,raw


def test_safe_tar_requires_explicit_bounded_154_count(repeated_inputs):
    import main_program_target_control_staging as staging
    build,raw=package154(repeated_inputs)
    actual=staging._target_package(raw,build,payload_count=154)
    assert len(actual['payloadFiles'])==154 and len(actual['files'])==155
    with pytest.raises(ValueError):staging._target_package(raw,build)


@pytest.mark.parametrize('count',[0,147,152,155,True,'154'])
def test_safe_tar_rejects_unapproved_counts(repeated_inputs,count):
    import main_program_target_control_staging as staging
    build,raw=package154(repeated_inputs)
    with pytest.raises(ValueError):staging._target_package(raw,build,payload_count=count)


def test_runtime_row_uses_verified_v3_new_count_without_relabeling_old_row():
    import main_program_target_control_runtime as runtime
    obj=object.__new__(runtime.TargetControlRuntimeTransition)
    old=dict(pid=10,fileCount=153,service='target.service',engine='/old',controlConfigurationPin={'old':1},
        ownerConfigurationPin={'old':2},dropinPin={'old':3})
    obj.old=deepcopy(old);obj.original=SimpleNamespace(spec=dict(current=dict(controllers=[old])))
    obj.dropin={'new':3};obj.candidate=dict(schemaVersion='MainProgramTargetControlSuccessorCandidate/v3',
        controller=dict(engine='/new',controlPin={'new':1},ownerPin={'new':2}),sourceCommit='9'*40,
        package=dict(fileCount=154,fileManifestSha256='f'*64))
    new=obj._row(20)
    assert new['fileCount']==154 and obj.old==old and old['fileCount']==153


@pytest.mark.parametrize('version,count',[('v2',154),('v3',153),('v3',155)])
def test_runtime_row_rejects_schema_count_mismatch(version,count):
    import main_program_target_control_runtime as runtime
    obj=object.__new__(runtime.TargetControlRuntimeTransition)
    obj.old=dict(pid=10);obj.original=SimpleNamespace(spec=dict(current=dict(controllers=[obj.old])))
    obj.dropin={};obj.candidate=dict(schemaVersion='MainProgramTargetControlSuccessorCandidate/'+version,
        controller=dict(engine='/new',controlPin={},ownerPin={}),sourceCommit='9'*40,
        package=dict(fileCount=count,fileManifestSha256='f'*64))
    with pytest.raises(ValueError):obj._row(20)
