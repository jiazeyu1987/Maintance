"""Real per-mount readonly protection, independent of a writable sibling view."""
import errno
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ops/recovery'))


def test_archive_view_is_readonly_and_original_mount_returns(tmp_path):
    first,second=tmp_path/'view',tmp_path/'other'
    first.mkdir();second.mkdir()
    def command(args,**kwargs):
        p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
        return p.stdout
    command(['mount','-t','tmpfs','-o','size=1m','spug-archive-view-test',str(first)])
    try:
        command(['mount','--bind',str(first),str(second)])
        try:
            (first/'archives').mkdir();(first/'archives/file').write_bytes(b'original')
            module=importlib.import_module('recovery_archive_view')
            from recovery_engine import pin
            from recovery_replacement_storage import parse_mountinfo
            def observed():
                return next(m for m in parse_mountinfo(Path('/proc/self/mountinfo').read_text()) if m['mountPoint']==str(first))
            original=observed()
            config=dict(schemaVersion='RegisteredArchiveViewProtection/v1',mountIdentity=original,
                mountProgramPin=pin(str(Path('/usr/bin/mount').resolve())))
            guard=module.ArchiveViewProtection(config,'test-archive-view',tmp_path/'journal',command)
            guard.preflight();guard.install();guard.verify()
            with pytest.raises(OSError) as failure:(first/'archives/forbidden').write_bytes(b'bad')
            assert failure.value.errno==errno.EROFS
            (second/'archives/sibling').write_bytes(b'allowed')
            assert (first/'archives/sibling').read_bytes()==b'allowed'
            assert (tmp_path/'journal/active.json').is_file()
            command(['mount','-i','-n','-o','remount,bind,rw','--',str(first)])
            with pytest.raises(Exception,match='ARCHIVE_VIEW_CHANGED'):guard.verify()
            command(['mount','-i','-n','-o','remount,bind,ro','--',str(first)])
            guard.verify();receipt=guard.release()
            assert observed()==original and Path(receipt['path']).is_file()
            (first/'archives/restored').write_bytes(b'yes')
            assert (second/'archives/restored').read_bytes()==b'yes'
            assert json.loads((tmp_path/'journal/intent.json').read_bytes())['operationId']=='test-archive-view'
            assert json.loads(Path(receipt['path']).read_bytes())['originalMountRestored'] is True
            with pytest.raises(Exception,match='ARCHIVE_VIEW_IDENTITY_CHANGED'):guard.verify()
        finally:command(['umount',str(second)])
    finally:command(['umount',str(first)])
