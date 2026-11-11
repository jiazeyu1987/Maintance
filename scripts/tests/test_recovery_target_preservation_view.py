"""Actual Linux non-CIFS rejection, never a fabricated CIFS positive fixture."""
from copy import deepcopy
import os
from pathlib import Path

import pytest

from test_recovery_target_preservation_template import (
    publication_case,capture_protocol,case,restore_case,
    register_v2,original_context,assert_no_repository_or_business_writes)
from recovery_engine import RecoveryError
from repository_records import RepositoryError
import recovery_target_preservation as preservation
import recovery_replacement_storage as storage
_ORIGINAL_PARSE_MOUNTINFO = storage.parse_mountinfo
_ORIGINAL_VISIBLE_MOUNT = storage.visible_mount


def test_real_non_cifs_directory_is_rejected_before_repository_lock(publication_case,monkeypatch):
    h = register_v2(publication_case,monkeypatch)
    with original_context(h) as (native,_):
        # Undo only the old input-storage fixture's explicit parsing seam.
        # New view observations must use this process's actual kernel facts.
        monkeypatch.setattr(storage,'parse_mountinfo',_ORIGINAL_PARSE_MOUNTINFO)
        rows = _ORIGINAL_PARSE_MOUNTINFO(Path('/proc/self/mountinfo').read_text(encoding='utf-8'))
        observed = _ORIGINAL_VISIBLE_MOUNT(str(h.repository),rows)
        assert observed['filesystem'] != 'cifs', 'TEST_EXPECTS_REAL_NON_CIFS_TEMP_ROOT'
        fd = os.open(h.repository,os.O_PATH|os.O_CLOEXEC|os.O_NOFOLLOW)
        try:
            info = Path('/proc/self/fdinfo')/str(fd)
            assert any(line.startswith('mnt_id:') for line in info.read_text(encoding='ascii').splitlines())
            assert os.fstat(fd).st_ino == h.repository.stat().st_ino
        finally:
            os.close(fd)
        before = deepcopy(h.engine.actions)
        with pytest.raises((RepositoryError,RecoveryError),
                match='PRESERVATION_WRITE_VIEW_MOUNT_MISMATCH|PRESERVATION_WRITE_VIEW_CIFS_REQUIRED'):
            preservation.TargetPreservation.prepare(native,policy_pin=h.v2_policy_pin,
                reservation_pin=h.reservation)
        assert_no_repository_or_business_writes(h,before)
        assert not (h.root/'target-preservation'/'write-view.json').exists()


def test_real_view_parser_is_independent_of_business_storage_fixture(publication_case,monkeypatch):
    h=register_v2(publication_case,monkeypatch)
    with original_context(h) as (native,_):
        protocol_parser=storage.parse_mountinfo
        assert protocol_parser is not _ORIGINAL_PARSE_MOUNTINFO
        assert preservation._parse_mountinfo is _ORIGINAL_PARSE_MOUNTINFO
        assert preservation._visible_mount is _ORIGINAL_VISIBLE_MOUNT
        before=deepcopy(h.engine.actions)
        with pytest.raises(RepositoryError,match='PRESERVATION_WRITE_VIEW_CIFS_REQUIRED'):
            preservation.TargetPreservation.prepare(native,policy_pin=h.v2_policy_pin,reservation_pin=h.reservation)
        assert storage.parse_mountinfo is protocol_parser
        assert_no_repository_or_business_writes(h,before)


@pytest.mark.parametrize('changed',[False,True])
def test_preparation_scope_chains_real_context_guard_and_restores_identity(publication_case,monkeypatch,changed):
    h=register_v2(publication_case,monkeypatch)
    with original_context(h) as (native,ctx):
        calls=[]
        def original_guard():calls.append('original')
        ctx._outer_guard=original_guard
        directory=h.case['root']/'guard-fd-scope';directory.mkdir(mode=0o700)
        descriptor=os.open(directory,os.O_PATH|os.O_DIRECTORY|os.O_NOFOLLOW)
        class DirectoryLeaseProtocol:
            # Finite orchestration boundary only: no fabricated CIFS admission.
            def check(self):
                calls.append('view')
                left=os.fstat(descriptor);right=directory.stat()
                if (left.st_dev,left.st_ino)!=(right.st_dev,right.st_ino):
                    raise RepositoryError('FINITE_VIEW_CHANGED',unknown=True)
        try:
            before=len(calls)
            with pytest.raises(RepositoryError,match='FINITE_VIEW_CHANGED') if changed else __import__('contextlib').nullcontext():
                with preservation._preparation_view_guard(ctx,DirectoryLeaseProtocol()):
                    if changed:
                        directory.rename(directory.with_name('retained-guard-fd-scope'))
                        directory.mkdir(mode=0o700)
                    native.native_context.guard_native(native)
            assert ctx._outer_guard is original_guard
            sequence=calls[before:]
            assert sequence and all(sequence[index:index+2]==['original','view']
                for index in range(0,len(sequence),2))
            assert not (h.repository/'.repository-control').exists()
        finally:
            os.close(descriptor)
            ctx._outer_guard=None
        with pytest.raises(OSError):os.fstat(descriptor)
