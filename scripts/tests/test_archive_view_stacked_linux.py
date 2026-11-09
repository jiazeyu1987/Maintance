"""Real stacked mounts; each case owns a separate Linux mount namespace.

Run with network none and CAP_SYS_ADMIN. Missing permissions are failures, not
skips. Only the two negative identity cases alter a parsed *real* snapshot;
mounts, file descriptors and every lifecycle command remain real.
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
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ('lifecycle', 'unknown-mount-id', 'wrong-device', 'symlink',
             'external-rw', 'overmount')


def _command(argv):
    result = subprocess.run(argv, capture_output=True, text=True,
                            encoding='utf-8', timeout=20)
    assert result.returncode == 0, (argv, result.returncode, result.stdout, result.stderr)
    return result.stdout


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_archive_view_uses_kernel_visible_stacked_mount(tmp_path, scenario):
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
    import recovery_archive_view as module
    from recovery_engine import RecoveryError, pin
    from recovery_replacement_storage import parse_mountinfo

    mount_path, umount_path = shutil.which('mount'), shutil.which('umount')
    assert mount_path and umount_path, 'util-linux mount and umount are required'
    mount = str(Path(mount_path).resolve(strict=True))
    umount = str(Path(umount_path).resolve(strict=True))
    root = Path(directory)
    lower, upper, view = (root / name for name in ('lower', 'upper', 'view'))
    for path in (lower, upper, view):
        path.mkdir()

    def rows():
        return parse_mountinfo(Path('/proc/self/mountinfo').read_text(encoding='utf-8'))

    def record(mount_id):
        matches = [row for row in rows() if row['mountId'] == mount_id]
        assert len(matches) == 1
        return matches[0]

    def visible(path):
        # Independent oracle: no list ordering or numerical mount-ID choice.
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

    with ExitStack() as cleanup:
        def mounted(arguments, destination):
            _command([mount, *arguments, str(destination)])
            cleanup.callback(_command, [umount, '--', str(destination)])

        for source, name in ((lower, 'lower'), (upper, 'upper')):
            mounted(['-t', 'tmpfs', '-o', 'size=1m', 'archive-stack-' + name], source)
            (source / 'archives').mkdir()
            (source / 'archives/origin').write_bytes(name.encode('ascii'))
        mounted(['--bind', str(lower)], view)
        hidden = visible(view)
        mounted(['--bind', str(upper)], view)
        original = visible(view)
        assert original['mountId'] != hidden['mountId']
        assert original['device'] != hidden['device']
        assert len([row for row in rows() if row['mountPoint'] == str(view)]) == 2
        assert record(hidden['mountId']) == hidden
        assert (view / 'archives/origin').read_bytes() == b'upper'
        assert 'rw' in original['options'] and 'ro' not in original['options']
        configuration = dict(schemaVersion='RegisteredArchiveViewProtection/v1',
            mountIdentity=deepcopy(original), mountProgramPin=pin(mount))
        journal, dispatched = root / 'journal', []

        def execute(argv, *, mutation):
            assert mutation is True
            dispatched.append(list(argv))
            return _command(argv)

        if scenario == 'symlink':
            alias = root / 'alias'
            alias.symlink_to(view, target_is_directory=True)
            configuration['mountIdentity']['mountPoint'] = str(alias)
            with pytest.raises(RecoveryError, match='PATH_ALIAS_REJECTED|ARCHIVE_VIEW_CHANGED'):
                module.ArchiveViewProtection(configuration, scenario, journal, execute).preflight()
            assert not dispatched and not journal.exists()
            assert visible(view) == original and record(hidden['mountId']) == hidden
            return

        guard = module.ArchiveViewProtection(configuration, scenario, journal, execute)
        if scenario in ('unknown-mount-id', 'wrong-device'):
            actual = rows()
            damaged = deepcopy(actual)
            top = next(row for row in damaged if row['mountId'] == original['mountId'])
            if scenario == 'unknown-mount-id':
                top['mountId'] = max(row['mountId'] for row in actual) + 1000000
            else:
                top['device'] = '0:0' if original['device'] != '0:0' else '0:1'
            # This is evidence-loss injection, never a simulated mount success.
            with patch.object(module, 'parse_mountinfo', return_value=damaged):
                with pytest.raises(RecoveryError, match=
                        'ARCHIVE_VIEW_CHANGED|REPLACEMENT_STORAGE_MOUNT_AMBIGUOUS'):
                    guard._observed()
                with pytest.raises(RecoveryError, match=
                        'ARCHIVE_VIEW_CHANGED|REPLACEMENT_STORAGE_MOUNT_AMBIGUOUS'):
                    guard.preflight()
            assert not dispatched and not journal.exists()
            assert rows() == actual
            assert visible(view) == original and record(hidden['mountId']) == hidden
            return

        assert guard._observed() == original
        guard.preflight()
        guard.install()
        guard.verify()
        readonly = deepcopy(original)
        readonly['options'] = ['ro' if option == 'rw' else option for option in original['options']]
        assert visible(view) == readonly
        assert record(hidden['mountId']) == hidden
        with pytest.raises(OSError) as blocked:
            (view / 'archives/forbidden').write_bytes(b'forbidden')
        assert blocked.value.errno == errno.EROFS
        (lower / 'archives/still-writable').write_bytes(b'lower')
        (upper / 'archives/sibling-write').write_bytes(b'upper')
        assert (view / 'archives/sibling-write').read_bytes() == b'upper'
        assert record(hidden['mountId']) == hidden

        if scenario == 'lifecycle':
            receipt = guard.release()
            assert visible(view) == original and record(hidden['mountId']) == hidden
            assert len(dispatched) == 2
            (view / 'archives/restored').write_bytes(b'restored')
            assert (upper / 'archives/restored').read_bytes() == b'restored'
            assert json.loads(Path(receipt['path']).read_text(encoding='utf-8'))['originalMountRestored'] is True
            assert json.loads((journal / 'intent.json').read_text(encoding='utf-8'))['operationId'] == scenario
            return

        evidence = {name: (journal / name).read_bytes() for name in ('intent.json', 'active.json')}
        if scenario == 'external-rw':
            _command([mount, '-i', '-n', '-o', 'remount,bind,rw', '--', str(view)])
            assert visible(view) == original
        else:
            assert scenario == 'overmount'
            mounted(['--bind', str(lower)], view)
            replacement = visible(view)
            assert replacement['mountId'] not in (hidden['mountId'], original['mountId'])
            assert 'rw' in replacement['options'] and 'ro' not in replacement['options']
            assert record(original['mountId']) == readonly
        for action in (guard.verify, guard.release):
            with pytest.raises(RecoveryError, match='ARCHIVE_VIEW_CHANGED'):
                action()
        assert len(dispatched) == 1, 'Failure must not dispatch an automatic RW release'
        assert not (journal / 'released.json').exists()
        assert {name: (journal / name).read_bytes() for name in evidence} == evidence
        assert record(hidden['mountId']) == hidden
        if scenario == 'overmount':
            assert record(original['mountId']) == readonly


if __name__ == '__main__':
    assert len(sys.argv) == 5 and sys.argv[1] == '--scenario'
    assert sys.argv[2] in SCENARIOS
    _exercise(sys.argv[2], sys.argv[3], sys.argv[4])
    print('PASS ' + sys.argv[2])
