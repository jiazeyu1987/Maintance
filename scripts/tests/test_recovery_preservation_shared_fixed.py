"""Actual fixed-path caps and the one existing raw ledger, no native restore."""
from pathlib import Path

import pytest

from test_recovery_restore_inputs import sized_metadata
from repository_records import RepositoryError
import recovery_preservation_source as consumer


def observed_reads(monkeypatch):
    actual=consumer._read_file;opened=[]
    def observed(path,maximum):
        opened.append(Path(path));return actual(path,maximum)
    monkeypatch.setattr(consumer,'_read_file',observed)
    reads=consumer._Reads(lambda:None);reads.maximum=16*1024*1024
    return reads,opened


def test_exact_fixed_cap_and_old_default_share_original_cache_without_recharging(tmp_path,monkeypatch):
    path=tmp_path/'small.json';expected=sized_metadata(path,65536)
    reads,opened=observed_reads(monkeypatch)
    pin,value=reads.fixed(path,65536)
    assert pin['bytes']==expected['bytes'] and pin['sha256']==expected['sha256'] and value=={}
    assert reads.fixed(path)==(pin,value) and reads.fixed(path,65536)==(pin,value)
    assert reads.total==65536 and opened==[path]
    reads.finish();assert reads.total==65536


def test_unknown_fixed_file_above_explicit_cap_is_rejected_before_body_read(tmp_path,monkeypatch):
    path=tmp_path/'small.json';sized_metadata(path,65537)
    reads,opened=observed_reads(monkeypatch)
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_METADATA_LIMIT$'):reads.fixed(path,65536)
    assert opened==[] and reads.total==0 and reads.pins()==[]


def test_smaller_cap_also_applies_to_an_already_cached_file_without_body_read(tmp_path,monkeypatch):
    path=tmp_path/'small.json';sized_metadata(path,65536)
    reads,opened=observed_reads(monkeypatch);reads.fixed(path);opened.clear()
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_METADATA_LIMIT$'):reads.fixed(path,65535)
    assert opened==[] and reads.total==65536


@pytest.mark.parametrize('extra',[0,1],ids=['exact-remaining','remaining-plus-one'])
def test_unknown_fixed_small_file_uses_actual_outer_remaining_before_body(tmp_path,monkeypatch,extra):
    reads,opened=observed_reads(monkeypatch)
    sizes=[16*1024*1024]*3+[16*1024*1024-65536]
    for index,size in enumerate(sizes):reads.read(sized_metadata(tmp_path/('fill-'+str(index)+'.json'),size))
    path=tmp_path/'fixed.json';sized_metadata(path,65536+extra);opened.clear()
    if extra:
        with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_METADATA_LIMIT$'):reads.fixed(path,65537)
        assert opened==[] and reads.total==64*1024*1024-65536
    else:
        pin,value=reads.fixed(path,65536)
        assert pin['bytes']==65536 and value=={} and opened==[path]
        assert reads.total==sum(pin['bytes'] for pin in reads.pins())==64*1024*1024


@pytest.mark.parametrize('maximum',[True,0,-1,1.5])
def test_explicit_fixed_cap_is_strict_positive_integer(tmp_path,monkeypatch,maximum):
    path=tmp_path/'small.json';sized_metadata(path,32)
    reads,opened=observed_reads(monkeypatch)
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_METADATA_LIMIT$'):reads.fixed(path,maximum)
    assert opened==[] and reads.total==0


def test_explicit_cap_cannot_raise_the_existing_document_limit(tmp_path,monkeypatch):
    path=tmp_path/'small.json';sized_metadata(path,65537)
    reads,opened=observed_reads(monkeypatch);reads.maximum=65536
    with pytest.raises(RepositoryError,match='^PRESERVATION_SOURCE_METADATA_LIMIT$'):reads.fixed(path,16*1024*1024)
    assert opened==[] and reads.total==0
