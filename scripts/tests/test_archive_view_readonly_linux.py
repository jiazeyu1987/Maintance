"""Permanent RO views on real Linux mounts, isolated per scenario.

Requires network none and CAP_SYS_ADMIN; unavailable prerequisites fail. The
product command transport must never run. Setup and drift use actual mount
commands, and all observations come from real mountinfo/fdinfo/fstat.
"""
from contextlib import ExitStack
from copy import deepcopy
import errno
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ('lifecycle', 'external-rw', 'overmount')


def _command(argv):
    result = subprocess.run(argv, capture_output=True, text=True,
                            encoding='utf-8', timeout=20)
    assert result.returncode == 0, (argv, result.returncode, result.stdout, result.stderr)
    return result.stdout


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_permanent_readonly_archive_view_uses_real_mount_identity(tmp_path, scenario):
    assert sys.platform == 'linux', 'Real Linux mount namespaces are required'
    unshare = shutil.which('unshare')
    assert unshare, 'util-linux unshare is required'
    parent_namespace = os.readlink('/proc/self/ns/mnt')
    result = subprocess.run(
        [unshare, '--mount', '--propagation', 'private', '--', sys.executable,
         '-B', str(Path(__file__).resolve()), '--scenario', scenario,
         str(tmp_path), parent_namespace],
        capture_output=True, text=True, encoding='utf-8', timeout=90)
    assert result.returncode == 0, (
        f'{scenario}: child exit {result.returncode}\n{result.stdout}\n{result.stderr}')
    assert result.stdout.strip() == f'PASS {scenario}'
    assert os.readlink('/proc/self/ns/mnt') == parent_namespace


def _exercise(scenario, directory, parent_namespace):
    assert os.readlink('/proc/self/ns/mnt') != parent_namespace
    assert set(os.listdir('/sys/class/net')) <= {'lo'}, 'Run with network none'
    sys.path.insert(0, str(ROOT / 'ops/recovery'))
    from recovery_archive_view import ArchiveViewProtection
    from recovery_engine import RecoveryError, digest, pin
    from recovery_replacement_storage import parse_mountinfo

    mount_path, umount_path = shutil.which('mount'), shutil.which('umount')
    assert mount_path and umount_path, 'util-linux mount and umount are required'
    mount = str(Path(mount_path).resolve(strict=True))
    umount = str(Path(umount_path).resolve(strict=True))
    root = Path(directory)
    source, view = root / 'source', root / 'view'
    source.mkdir(); view.mkdir()

    def record(mount_id):
        rows = parse_mountinfo(Path('/proc/self/mountinfo').read_text(encoding='utf-8'))
        matches = [row for row in rows if row['mountId'] == mount_id]
        assert len(matches) == 1
        return matches[0]

    def visible(path):
        fd = os.open(path, os.O_PATH | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            assert not stat.S_ISLNK(info.st_mode)
            ids = re.findall(r'^mnt_id:\s*([0-9]+)\s*$',
                Path(f'/proc/self/fdinfo/{fd}').read_text(encoding='ascii'), re.MULTILINE)
            assert len(ids) == 1
            value = record(int(ids[0]))
            assert value['device'] == f'{os.major(info.st_dev)}:{os.minor(info.st_dev)}'
            assert value['mountPoint'] == str(path)
            return value
        finally:
            os.close(fd)

    def assert_readonly():
        with pytest.raises(OSError) as blocked:
            (view / 'archives/forbidden').write_bytes(b'forbidden')
        assert blocked.value.errno == errno.EROFS

    with ExitStack() as cleanup:
        def mounted(arguments, destination):
            _command([mount, *arguments, str(destination)])
            cleanup.callback(_command, [umount, '--', str(destination)])

        mounted(['-t', 'tmpfs', '-o', 'size=1m', 'archive-permanent-ro'], source)
        (source / 'archives').mkdir()
        (source / 'archives/original').write_bytes(b'original')
        mounted(['--bind', str(source)], view)
        _command([mount, '-i', '-n', '-o', 'remount,bind,ro', '--', str(view)])
        original, source_original = visible(view), visible(source)
        assert 'ro' in original['options'] and 'rw' not in original['options']
        assert 'rw' in source_original['options'] and 'ro' not in source_original['options']
        assert_readonly()
        configuration = dict(schemaVersion='RegisteredArchiveViewProtection/v2',
            mountIdentity=deepcopy(original), mountProgramPin=pin(mount))
        original_configuration = deepcopy(configuration)
        journal, dispatched = root / 'journal', []

        def forbidden_transport(argv, *, mutation):
            dispatched.append((list(argv), mutation))
            raise AssertionError('Permanent RO protection dispatched a mount command')

        guard = ArchiveViewProtection(configuration, scenario, journal, forbidden_transport)
        guard.preflight(); guard.install(); guard.verify()
        assert visible(view) == original and visible(source) == source_original
        assert_readonly()
        evidence = {name: (journal / name).read_bytes() for name in ('intent.json', 'active.json')}
        intent, active = (json.loads(evidence[name]) for name in ('intent.json', 'active.json'))
        assert intent['schemaVersion'] == 'ArchiveViewProtectionIntent/v1'
        assert active['schemaVersion'] == 'ArchiveViewProtectionActive/v1'
        assert intent['operationId'] == active['operationId'] == scenario
        assert intent['configurationDigest'] == active['configurationDigest'] == digest(configuration)
        assert active['observedMountDigest'] == digest(original)

        if scenario == 'lifecycle':
            receipt = guard.release()
            terminal = json.loads(Path(receipt['path']).read_text(encoding='utf-8'))
            assert terminal['schemaVersion'] == 'ArchiveViewProtectionRelease/v1'
            assert terminal['operationId'] == scenario and terminal['originalMountRestored'] is True
            assert visible(view) == original
            assert_readonly()
            (source / 'archives/sibling-write').write_bytes(b'allowed')
            assert (view / 'archives/sibling-write').read_bytes() == b'allowed'
        else:
            if scenario == 'external-rw':
                _command([mount, '-i', '-n', '-o', 'remount,bind,rw', '--', str(view)])
                assert visible(view)['mountId'] == original['mountId']
            else:
                assert scenario == 'overmount'
                mounted(['--bind', str(source)], view)
                assert visible(view)['mountId'] != original['mountId']
                assert record(original['mountId']) == original
            assert 'rw' in visible(view)['options'] and 'ro' not in visible(view)['options']
            for action in (guard.verify, guard.release):
                with pytest.raises(RecoveryError, match='ARCHIVE_VIEW_CHANGED'):
                    action()
            assert not (journal / 'released.json').exists()
            if scenario == 'overmount':
                assert record(original['mountId']) == original
        assert not dispatched
        assert configuration == original_configuration
        assert {name: (journal / name).read_bytes() for name in evidence} == evidence
        assert visible(source) == source_original
        assert (source / 'archives/original').read_bytes() == b'original'


if __name__ == '__main__':
    assert len(sys.argv) == 5 and sys.argv[1] == '--scenario'
    assert sys.argv[2] in SCENARIOS
    _exercise(sys.argv[2], sys.argv[3], sys.argv[4])
    print('PASS ' + sys.argv[2])
