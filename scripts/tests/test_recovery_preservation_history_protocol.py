"""Actual consumer caps over one reader; no validator or history success fakes."""
from copy import deepcopy
from pathlib import Path

import pytest

from test_recovery_preservation_source import metadata, put
from test_recovery_preservation_source_publishers import unchanged
from test_recovery_restore_inputs import sized_metadata
import recovery_preservation_source as source
from recovery_preservation_inputs import _History
from recovery_engine import RecoveryError
from repository_records import RepositoryError


def reads_with_open_log(monkeypatch):
    reads=source._Reads(lambda:None);reads.maximum=16*1024*1024
    actual=source._read_file;opened=[]
    def read(path,maximum):
        opened.append(path);return actual(path,maximum)
    monkeypatch.setattr(source,'_read_file',read)
    return reads,opened


def test_explicit_read_cap_keeps_default_cache_and_exact_original_bytes(tmp_path,monkeypatch):
    reads,opened=reads_with_open_log(monkeypatch)
    path=tmp_path/'original.json';pin=sized_metadata(path,65536)
    assert reads.read(pin,65536)=={}
    assert reads.read(pin)=={} and reads.total==65536 and opened==[path]
    opened.clear()
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_METADATA_LIMIT'):
        reads.read(pin,65535)
    assert opened==[] and reads.total==65536
    reads.finish();assert reads.total==65536


@pytest.mark.parametrize('maximum',[65536,True,0],ids=['body-above-cap','bool','zero'])
def test_explicit_read_cap_rejects_before_unknown_body(tmp_path,monkeypatch,maximum):
    reads,opened=reads_with_open_log(monkeypatch)
    pin=sized_metadata(tmp_path/'original.json',65537)
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_METADATA_LIMIT'):
        reads.read(pin,maximum)
    assert opened==[] and reads.total==0


def active(history,h):
    pin=h['point_pin']
    pins={key:pin for key in ('sourcePolicyPin','pointPin','configurationPin','requestPin','intentPin','executionBindingPin')}
    pins['originals']={}
    return history.publication(h['root']/'operations','original_restore','target58',pins,derived=True)


def test_nested_policy_cannot_raise_current_caps_after_exit(unchanged):
    h=unchanged;reads=source._Reads(lambda:None);reads.maximum=65536;reads.total_limit=1024*1024
    state=_History()
    with active(state,h):
        policy,_=source._policy(reads,h['v2_pin'],history=state)
        assert policy['maxDocumentBytes']==16*1024*1024
        assert (reads.maximum,reads.total_limit)==(65536,1024*1024)
    assert state.depth==0 and (reads.maximum,reads.total_limit)==(65536,1024*1024)
    reads.finish()


@pytest.mark.parametrize('dimension',['document','aggregate'])
def test_nested_policy_rejects_prior_actual_originals_above_new_limits(unchanged,dimension):
    h=unchanged;reads=source._Reads(lambda:None);reads.maximum=16*1024*1024
    prior=sized_metadata(h['root']/'prior-unique-original.json',128*1024 if dimension=='document' else 1024*1024)
    reads.read(prior)
    policy=deepcopy(h['v2_policy'])
    policy['maxDocumentBytes']=65536 if dimension=='document' else 16*1024*1024
    policy['maxMetadataBytes']=64*1024*1024 if dimension=='document' else 16*1024*1024
    if dimension=='aggregate':
        # Same ledger, actual unique original bodies; no synthetic total assignment.
        for i in range(16):reads.read(sized_metadata(h['root']/('prior-'+str(i)+'.json'),1024*1024))
    reference=put(h['root']/'config/nested-policy.json',policy)
    state=_History()
    with active(state,h):
        with pytest.raises((RepositoryError,RecoveryError),match='METADATA_LIMIT'):
            source._policy(reads,reference,history=state)
    assert prior['bytes']<=reads.total==sum(p['bytes'] for p in reads.pins())
