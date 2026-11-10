"""Actual archive bytes at the schema boundary; no server or stage writes."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import main_program_control_staging as subject


TASK=Path(__file__).resolve().parent


@pytest.fixture
def actual():
    build=json.loads((TASK/'release-build-a4c279f.json').read_bytes())
    reference=build['variants']['standard']['packagePin']
    row=dict(variant='standard',packagePin=dict(reference,path='/evidence/inputs/backup-restore-standard.tgz'))
    return dict(build=build,delta=dict(schemaVersion='MainProgramChainPolicyPackageDelta/v1',packages=[row]))


def test_new_verified_delta_reads_the_actual_build_archive(actual):
    reference,raw=subject.read_covered_package(actual)
    assert reference==actual['build']['variants']['standard']['packagePin']
    assert hashlib.sha256(raw).hexdigest()==actual['build']['packageSha256']
    parsed=subject.verify_package(raw,actual['build'])
    assert len(parsed['payloadFiles'])==147


@pytest.mark.parametrize('change',['bytes','sha256','variant','schema','changed-file'])
def test_new_delta_refuses_substituted_or_changed_archive(actual,tmp_path,change):
    value=deepcopy(actual)
    row=value['delta']['packages'][0]
    if change=='bytes':row['packagePin']['bytes']+=1
    elif change=='sha256':row['packagePin']['sha256']='0'*64
    elif change=='variant':row['variant']='lightweight'
    elif change=='schema':value['delta']['schemaVersion']='unknown'
    else:
        destination=tmp_path/'changed.tgz'
        destination.write_bytes(b'changed real archive')
        value['build']['variants']['standard']['packagePin']['path']=str(destination)
    with pytest.raises(ValueError):subject.read_covered_package(value)


def test_old_delta_keeps_its_original_archive_path(actual):
    original=actual['build']['variants']['standard']['packagePin']
    actual['delta']=dict(schemaVersion='ArchiveCataloguePackageDelta/v2',packages=[dict(variant='standard',path=original['path'])])
    reference,raw=subject.read_covered_package(actual)
    assert reference==original and hashlib.sha256(raw).hexdigest()==original['sha256']
