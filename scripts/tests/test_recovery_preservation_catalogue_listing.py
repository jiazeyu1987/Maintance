"""Real bounded directory snapshots inside the existing one-request ledger."""
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
from recovery_preservation_source import PreservationCatalogueRead
from repository_records import RepositoryError
from test_recovery_preservation_source import put


@pytest.fixture
def state(tmp_path):
    root=tmp_path.resolve()
    control=put(root/'control.json',dict(schemaVersion='SmallAppExecutionServiceConfig/v2'))
    directory=root/'applications';directory.mkdir()
    (directory/'z-registration.private.json').write_bytes(b'{"notRead":true}')
    (directory/'a-selector').write_bytes(b'{"notRead":true}')
    (directory/'m-nonselector-directory').mkdir()
    return PreservationCatalogueRead(control,guard=lambda:None),directory


def test_listing_is_complete_sorted_and_metadata_bodies_are_not_opened(state,monkeypatch):
    session,directory=state
    import recovery_preservation_source as consumer
    def no_body(*args,**kwargs):raise AssertionError('LISTING_OPENED_METADATA_BODY')
    monkeypatch.setattr(consumer,'_read_file',no_body)
    assert session.listing(directory,3)==('a-selector','m-nonselector-directory','z-registration.private.json')
    assert session.listing(directory,3)==('a-selector','m-nonselector-directory','z-registration.private.json')


@pytest.mark.parametrize('limit',[0,-1,True,1.5])
def test_listing_requires_strict_positive_integer_before_enumeration(state,monkeypatch,limit):
    session,directory=state
    def no_listing(path):raise AssertionError('INVALID_LIMIT_ENUMERATED_DIRECTORY')
    monkeypatch.setattr(Path,'iterdir',no_listing)
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_POINT_LIMIT'):
        session.listing(directory,limit)


def test_listing_counts_nonselectors_and_directories_against_limit(state):
    session,directory=state
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_POINT_LIMIT'):
        session.listing(directory,2)


def test_listing_original_directory_snapshot_is_rechecked_at_finish(state):
    session,directory=state
    assert len(session.listing(directory,4))==3
    (directory/'new-entry').write_bytes(b'{}')
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_DIRECTORY_CHANGED'):
        session.finish()


def test_listing_after_finish_is_rejected_before_enumeration(state,monkeypatch):
    session,directory=state;session.finish()
    def no_listing(path):raise AssertionError('FINISHED_SESSION_ENUMERATED_DIRECTORY')
    monkeypatch.setattr(Path,'iterdir',no_listing)
    with pytest.raises(RepositoryError,match='PRESERVATION_SOURCE_SESSION_FINISHED'):
        session.listing(directory,3)
