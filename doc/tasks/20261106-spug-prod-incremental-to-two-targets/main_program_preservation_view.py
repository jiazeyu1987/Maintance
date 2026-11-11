"""Pinned, independent preservation CIFS bind view; no business lifecycle actions.

install_once owns only two directory leaves. startup requires those leaves to
exist. Neither entry point retries, unmounts, repairs, or edits existing mounts.
The system boundary is injectable for protocol tests; native success requires
O_PATH/fdinfo verification against the current kernel mount table.
"""
from collections import Counter
from copy import deepcopy
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import subprocess
import sys


SCHEMA = 'MainProgramPreservationView/v1'
UNC = '//172.30.30.4/IT共享'
PARENTS = {
    '57': '/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3',
    '58': '/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3',
    '59': '/mnt/intruoyi-data/spug-main-restore-20261104-v3',
}
_KEYS = {'schemaVersion', 'host', 'targetParent', 'sourceMountPoint',
         'repositoryRelativePath', 'viewPath', 'source', 'pins'}
_SHA = re.compile(r'[0-9a-f]{64}\Z')


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _absolute(value):
    _require(isinstance(value, str) and value.startswith('/') and value != '/',
             'VIEW_PATH_NOT_ABSOLUTE')
    _require(str(PurePosixPath(value)) == value and not any(
        part in ('.', '..') for part in value.split('/')),
        'VIEW_PATH_NOT_NORMALIZED')
    _require(not any(ord(char) < 33 or ord(char) == 127 or char in '%$\\"\''
                     for char in value), 'VIEW_PATH_UNSAFE_FOR_PINNED_UNIT')
    return value


def _pin(value):
    _require(isinstance(value, dict) and set(value) == {'path', 'bytes', 'sha256'},
             'VIEW_PIN_SHAPE')
    _absolute(value['path'])
    _require(type(value['bytes']) is int and 0 < value['bytes'] <= 512 * 1024 * 1024,
             'VIEW_PIN_BYTES')
    _require(isinstance(value['sha256'], str) and _SHA.fullmatch(value['sha256']),
             'VIEW_PIN_SHA256')


def validate_configuration(config):
    """Validate the complete fixed-scope document without I/O or mutation."""
    _require(isinstance(config, dict) and set(config) == _KEYS, 'VIEW_CONFIG_SHAPE')
    _require(config['schemaVersion'] == SCHEMA, 'VIEW_CONFIG_SCHEMA')
    host = config['host']
    _require(isinstance(host, str) and host in PARENTS, 'VIEW_HOST')
    _require(config['targetParent'] == PARENTS[host], 'VIEW_TARGET_PARENT')
    _require(config['repositoryRelativePath'] ==
             'Backup/BackupPackage/spug-target-preservation/main-' + host + '-20261111-r1',
             'VIEW_REPOSITORY_PATH')
    _require(config['viewPath'] == config['targetParent'] + '/preservation-nas-view',
             'VIEW_LOCATION')
    _absolute(config['sourceMountPoint'])
    _require(config['source'] == dict(filesystem='cifs', source=UNC, root='/', writable=True)
             and type(config['source'].get('writable')) is bool, 'VIEW_SOURCE_CONTRACT')
    pins = config['pins']
    _require(isinstance(pins, dict) and set(pins) == {'python', 'mount', 'helper'},
             'VIEW_TOOL_PINS')
    for reference in pins.values():
        _pin(reference)
    expected = (config['targetParent'] + '/installed-tools/main-preservation-view-' +
                pins['helper']['sha256'][:12] + '/main_program_preservation_view.py')
    _require(pins['helper']['path'] == expected, 'VIEW_HELPER_LOCATION')
    _require(len({value['path'] for value in pins.values()}) == 3, 'VIEW_TOOL_ALIAS')
    source, parent = config['sourceMountPoint'], config['targetParent']
    _require(not _within(source, parent) and not _within(parent, source),
             'VIEW_SOURCE_TARGET_OVERLAP')
    return deepcopy(config)


def _within(path, parent):
    return path == parent or path.startswith(parent.rstrip('/') + '/')


def _unescape(value):
    # mountinfo escapes these four bytes even when the original pathname
    # contains a literal backslash followed by digits. Decode exactly once.
    return re.sub(r'\\(040|011|012|134)', lambda match: chr(int(match[1], 8)), value)


def parse_mountinfo(raw):
    """Parse complete kernel rows while retaining their exact original lines."""
    _require(isinstance(raw, bytes) and len(raw) <= 8 * 1024 * 1024,
             'VIEW_MOUNTINFO_BYTES')
    text = raw.decode('utf-8', errors='strict')
    _require(text.endswith('\n') and text.strip(), 'VIEW_MOUNTINFO_INCOMPLETE')
    rows, ids = [], set()
    for line in text.splitlines():
        _require(line.count(' - ') == 1, 'VIEW_MOUNTINFO_SEPARATOR')
        left, right = (part.split(' ') for part in line.split(' - '))
        _require(len(left) >= 6 and len(right) == 3 and all(left + right),
                 'VIEW_MOUNTINFO_FIELDS')
        _require(left[0].isdigit() and left[1].isdigit() and int(left[0]) > 0
                 and re.fullmatch(r'[0-9]+:[0-9]+', left[2]), 'VIEW_MOUNTINFO_ID')
        identifier = int(left[0])
        _require(identifier not in ids, 'VIEW_DUPLICATE_MOUNT_ID')
        ids.add(identifier)
        root, point = _unescape(left[3]), _unescape(left[4])
        # Linux nsfs exposes an inode name, such as net:[4026531992], as
        # mountinfo root. These unrelated Docker mounts are not CIFS paths.
        nsfs_root = right[0] == 'nsfs' and re.fullmatch(r'net:\[[0-9]+\]', root) is not None
        _require((root.startswith('/') or nsfs_root) and point.startswith('/'), 'VIEW_MOUNTINFO_PATH')
        rows.append(dict(mountId=identifier, parentId=int(left[1]), device=left[2],
            root=root, mountPoint=point, options=left[5].split(','),
            optionalFields=left[6:], filesystem=right[0], source=_unescape(right[1]),
            superOptions=right[2].split(','), line=line))
    return rows


def _identity(item):
    return dict(device=item.st_dev, inode=item.st_ino, mode=item.st_mode,
                uid=item.st_uid, gid=item.st_gid)


def _file_identity(item):
    # Reading can update atime. Content/mode/link/size/mtime/ctime identity
    # must remain stable throughout a pinned read.
    return (_identity(item), item.st_nlink, item.st_size,
            item.st_mtime_ns, item.st_ctime_ns)


class NativeSystem:
    """The only operating-system boundary; no implicit subprocess shell."""
    native = True

    def euid(self):
        _require(os.name == 'posix' and hasattr(os, 'O_PATH'), 'VIEW_REQUIRES_LINUX_O_PATH')
        return os.geteuid()

    def lstat(self, path):
        return os.lstat(path)

    def exists(self, path):
        return os.path.lexists(path)

    def read_pin(self, reference):
        _pin(reference)
        _directories(str(PurePosixPath(reference['path']).parent), self)
        before = self.lstat(reference['path'])
        _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                 before.st_uid == 0 and not stat.S_IMODE(before.st_mode) & 0o022,
                 'VIEW_PIN_FILE_IDENTITY')
        fd = os.open(reference['path'], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            opened = os.fstat(fd)
            _require(_file_identity(opened) == _file_identity(before), 'VIEW_PIN_OPEN_CHANGED')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                raw = stream.read(reference['bytes'] + 1)
            _require(_file_identity(os.fstat(fd)) == _file_identity(before) and
                     _file_identity(self.lstat(reference['path'])) == _file_identity(before),
                     'VIEW_PIN_READ_CHANGED')
        finally:
            os.close(fd)
        _require(len(raw) == reference['bytes'] and
                 hashlib.sha256(raw).hexdigest() == reference['sha256'], 'VIEW_PIN_CHANGED')
        return raw

    def verify_runtime(self, config):
        _require(os.path.abspath(__file__) == config['pins']['helper']['path'],
                 'VIEW_EXECUTING_HELPER_PATH')
        _require(os.path.abspath(sys.executable) == config['pins']['python']['path'],
                 'VIEW_EXECUTING_PYTHON_PATH')
        for name, reference in config['pins'].items():
            self.read_pin(reference)
            mode = stat.S_IMODE(self.lstat(reference['path']).st_mode)
            _require(mode == 0o400 if name == 'helper' else mode & 0o111 != 0,
                     'VIEW_TOOL_MODE')

    def mkdir(self, path, mode):
        os.mkdir(path, mode)

    def mountinfo(self):
        with open('/proc/self/mountinfo', 'rb') as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        parse_mountinfo(raw)
        return raw

    def visible(self, path):
        fd = os.open(path, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            identity = _identity(os.fstat(fd))
            with open('/proc/self/fdinfo/' + str(fd), 'r', encoding='utf-8') as stream:
                matches = re.findall(r'^mnt_id:\s*([0-9]+)$', stream.read(65537), re.M)
            _require(len(matches) == 1, 'VIEW_FDINFO_MOUNT_ID')
            rows = [row for row in parse_mountinfo(self.mountinfo())
                    if row['mountId'] == int(matches[0])]
            _require(len(rows) == 1, 'VIEW_VISIBLE_MOUNT_NOT_UNIQUE')
            row = rows[0]
            _require(row['device'] == str(os.major(identity['device'])) + ':' +
                     str(os.minor(identity['device'])), 'VIEW_VISIBLE_DEVICE')
            return dict(row, identity=identity)
        finally:
            os.close(fd)

    def run(self, argv, timeout):
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=timeout, check=False)
        return dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


def _directories(path, system):
    current = PurePosixPath(path)
    items = {}
    for part in reversed((current, *current.parents)):
        text = str(part)
        item = system.lstat(text)
        _require(stat.S_ISDIR(item.st_mode) and item.st_uid == 0 and
                 not stat.S_IMODE(item.st_mode) & 0o022, 'VIEW_UNSAFE_DIRECTORY:' + text)
        items[text] = _identity(item)
    return items


def _source_view(config, system):
    value = system.visible(config['sourceMountPoint'])
    _require(value['mountPoint'] == config['sourceMountPoint'] and
             value['filesystem'] == 'cifs' and value['source'] == UNC and value['root'] == '/' and
             'rw' in value['options'] and 'ro' not in value['options'] and
             'rw' in value['superOptions'] and 'ro' not in value['superOptions'],
             'VIEW_SOURCE_MOUNT_CONTRACT')
    return value


def _topology(config, rows):
    source, view = config['sourceMountPoint'], config['viewPath']
    counts = Counter(row['mountPoint'] for row in rows)
    source_rows = [row for row in rows if row['mountPoint'] == source]
    automount = [row for row in source_rows if row['filesystem'] == 'autofs' and
                 row['source'] == 'systemd-1' and row['root'] == '/']
    cifs = [row for row in source_rows if row['filesystem'] == 'cifs' and
            row['source'] == UNC and row['root'] == '/']
    known_automount = (len(source_rows) == 2 and len(automount) == len(cifs) == 1 and
                       cifs[0]['parentId'] == automount[0]['mountId'])
    paths = (source, view, config['pins']['helper']['path'],
             config['pins']['python']['path'], config['pins']['mount']['path'])
    for point, count in counts.items():
        if any(_within(path, point) for path in paths):
            _require(count == 1 or (point == source and known_automount),
                     'VIEW_STACKED_ANCESTOR_MOUNT:' + point)
    _require(counts[source] == 1 or known_automount, 'VIEW_SOURCE_MOUNT_NOT_UNIQUE')
    _require(not any(_within(row['mountPoint'], view) for row in rows),
             'VIEW_ALREADY_MOUNTED')
    _require(not any(_within(row['mountPoint'], source) and row['mountPoint'] != source
                     for row in rows), 'VIEW_NESTED_SOURCE_MOUNT')


def _preflight(config, mode, system):
    value = validate_configuration(config)
    _require(system.euid() == 0, 'VIEW_REQUIRES_ROOT')
    system.verify_runtime(value)
    raw = system.mountinfo()
    rows = parse_mountinfo(raw)
    _topology(value, rows)
    source = _source_view(value, system)
    _require(source['line'] in {row['line'] for row in rows}, 'VIEW_SOURCE_OBSERVATION_CHANGED')
    backing = value['sourceMountPoint'] + '/' + value['repositoryRelativePath']
    # Existing shared ancestors are mandatory. This helper never manufactures
    # missing shared hierarchy, adjusts NAS modes, or changes an original mount.
    _directories(str(PurePosixPath(backing).parent), system)
    _directories(value['targetParent'], system)
    if mode == 'install_once':
        _require(not system.exists(backing) and not system.exists(value['viewPath']),
                 'VIEW_INSTALL_DIRECTORY_ALREADY_EXISTS')
    else:
        _directories(backing, system)
        _directories(value['viewPath'], system)
        _require(stat.S_IMODE(system.lstat(value['viewPath']).st_mode) == 0o700,
                 'VIEW_LOCAL_DIRECTORY_MODE')
    _require(system.mountinfo() == raw, 'VIEW_PREFLIGHT_MOUNT_TABLE_CHANGED')
    return value, backing, raw, source


class ViewFailure(RuntimeError):
    """A mutation failed. Retained state must be examined, never auto-retried."""
    def __init__(self, phase, created_paths, commands):
        self.phase = phase
        self.created_paths = tuple(created_paths)
        self.commands = tuple(tuple(argv) for argv in commands)
        super().__init__('PRESERVATION_VIEW_FAILED_RETAINED:' + json.dumps(dict(
            phase=phase, createdPaths=self.created_paths, commands=self.commands), sort_keys=True))


def _new_view(config, backing, original, source, system, expected_mount_id=None,
              require_private=False):
    raw = system.mountinfo()
    rows = parse_mountinfo(raw)
    before, after = Counter(line for line in original.decode('utf-8').splitlines()), Counter(
        row['line'] for row in rows)
    _require(not before - after, 'VIEW_ORIGINAL_MOUNT_CHANGED')
    additions = list((after - before).elements())
    value = system.visible(config['viewPath'])
    _require(len(additions) == 1 and additions[0] == value['line'], 'VIEW_NEW_MOUNT_NOT_UNIQUE')
    _require(sum(row['mountPoint'] == config['viewPath'] for row in rows) == 1 and
             value['mountPoint'] == config['viewPath'] and value['filesystem'] == 'cifs' and
             value['source'] == UNC and value['root'] == '/' + config['repositoryRelativePath'] and
             value['device'] == source['device'] and 'rw' in value['options'] and
             'ro' not in value['options'] and 'rw' in value['superOptions'] and
             'ro' not in value['superOptions'], 'VIEW_BOUND_MOUNT_CONTRACT')
    item = system.lstat(backing)
    _require(value['identity']['device'] == item.st_dev and
             value['identity']['inode'] == item.st_ino, 'VIEW_BOUND_ROOT_IDENTITY')
    if expected_mount_id is not None:
        _require(value['mountId'] == expected_mount_id, 'VIEW_PRIVATE_MOUNT_ID_CHANGED')
    if require_private:
        _require(value['optionalFields'] == [], 'VIEW_NOT_PRIVATE_OR_UNKNOWN_FLAGS')
    _require(system.mountinfo() == raw and _source_view(config, system) == source,
             'VIEW_POSTCHECK_MOUNT_TABLE_CHANGED')
    return value


def _apply(config, mode, system):
    system = NativeSystem() if system is None else system
    config, backing, original, source = _preflight(config, mode, system)
    created, commands, phase = [], [], 'create-backing' if mode == 'install_once' else 'bind'
    try:
        if mode == 'install_once':
            for path in (backing, config['viewPath']):
                phase = 'create-backing' if path == backing else 'create-view'
                system.mkdir(path, 0o700)
                created.append(path)
        phase = 'verify-directories-before-bind'
        _directories(backing, system)
        _directories(config['viewPath'], system)
        _require(stat.S_IMODE(system.lstat(config['viewPath']).st_mode) == 0o700,
                 'VIEW_LOCAL_DIRECTORY_MODE')
        _require(system.mountinfo() == original and _source_view(config, system) == source,
                 'VIEW_BEFORE_BIND_MOUNT_CHANGED')
        system.verify_runtime(config)
        for phase, argv in (
            ('bind', [config['pins']['mount']['path'], '-i', '-n', '-o', 'bind', '--',
                      backing, config['viewPath']]),
            ('make-private', [config['pins']['mount']['path'], '-i', '-n', '--make-private',
                              '--', config['viewPath']])):
            system.verify_runtime(config)
            commands.append(argv)
            result = system.run(argv, timeout=12)
            _require(result['returncode'] == 0 and not result['stderr'],
                     'VIEW_MOUNT_COMMAND_FAILED:' + phase + ':' + repr(result))
            phase += '-kernel-verification'
            visible = _new_view(config, backing, original, source, system,
                expected_mount_id=mount_id if len(commands) == 2 else None,
                require_private=len(commands) == 2)
            mount_id = visible['mountId']
        return dict(schemaVersion='MainProgramPreservationViewResult/v1',
            status='VIEW_BOUND_KERNEL_VERIFIED', host=config['host'], mode=mode,
            nativeSystem=system.native, createdPaths=created, viewPath=config['viewPath'],
            backingPath=backing, visibleMount=visible, originalMountsUnchanged=True,
            commands=commands, businessActions=False)
    except Exception as error:
        raise ViewFailure(phase, created, commands) from error


def install_once(config, *, system=None):
    """Exclusively create only owned leaves, then bind and verify their view."""
    return _apply(config, 'install_once', system)


def startup(config, *, system=None):
    """Bind only pre-existing validated leaves; never create or repair them."""
    return _apply(config, 'startup', system)


def _configuration_pin(config, reference):
    _pin(reference)
    _require(reference['path'] == str(PurePosixPath(config['pins']['helper']['path']).parent) +
             '/view.json' and reference['bytes'] <= 65536, 'VIEW_CONFIG_PIN_LOCATION')


def _bootstrap(config, reference):
    # Runs in the pinned interpreter BEFORE executing any helper code. The
    # helper repeats identity checks, including the actual executing file paths.
    refs = {key: config['pins'][key] for key in ('python', 'helper')}
    refs['configuration'] = reference
    source = '''import hashlib, os, pathlib, stat, sys
pins = PINS
def identity(item):
    return (item.st_dev, item.st_ino, item.st_mode, item.st_uid, item.st_gid, item.st_nlink, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
def read(reference):
    path = pathlib.Path(reference['path'])
    for parent in reversed(path.parents):
        item = parent.lstat()
        if not stat.S_ISDIR(item.st_mode) or item.st_uid != 0 or stat.S_IMODE(item.st_mode) & 0o022:
            raise ValueError('VIEW_BOOTSTRAP_DIRECTORY')
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_uid != 0 or stat.S_IMODE(before.st_mode) & 0o022:
        raise ValueError('VIEW_BOOTSTRAP_FILE_IDENTITY')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        if identity(os.fstat(fd)) != identity(before):
            raise ValueError('VIEW_BOOTSTRAP_OPEN_CHANGED')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(reference['bytes'] + 1)
        if identity(os.fstat(fd)) != identity(before) or identity(path.lstat()) != identity(before):
            raise ValueError('VIEW_BOOTSTRAP_READ_CHANGED')
    finally:
        os.close(fd)
    if len(raw) != reference['bytes'] or hashlib.sha256(raw).hexdigest() != reference['sha256']:
        raise ValueError('VIEW_BOOTSTRAP_PIN_CHANGED')
    return raw
if os.name != 'posix' or os.geteuid() != 0 or os.path.abspath(sys.executable) != pins['python']['path']:
    raise ValueError('VIEW_BOOTSTRAP_RUNTIME')
read(pins['python'])
helper = read(pins['helper'])
read(pins['configuration'])
for name in ('helper', 'configuration'):
    if stat.S_IMODE(os.lstat(pins[name]['path']).st_mode) != 0o400:
        raise ValueError('VIEW_BOOTSTRAP_PRIVATE_MODE')
sys.argv[0] = pins['helper']['path']
exec(compile(helper, pins['helper']['path'], 'exec'), {'__name__': '__main__', '__file__': pins['helper']['path']})
'''.replace('PINS', repr(refs))
    return 'exec(' + repr(source) + ')'


def _unit_word(value):
    # systemd and a shell-like parser both preserve this quoted argument.
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def render_service(config, *, configuration_pin, mode='startup'):
    """Return a standalone oneshot unit. Does not write, enable, or reload it."""
    config = validate_configuration(config)
    _configuration_pin(config, configuration_pin)
    _require(mode in ('startup', 'install_once'), 'VIEW_SERVICE_MODE')
    argv = [config['pins']['python']['path'], '-I', '-B', '-c', _bootstrap(config, configuration_pin),
            '--config', configuration_pin['path'], '--config-bytes', str(configuration_pin['bytes']),
            '--config-sha256', configuration_pin['sha256'], '--mode', mode]
    return ('[Unit]\nDescription=Pinned preservation NAS view ' + config['host'] + '\n'
        'RequiresMountsFor=' + config['sourceMountPoint'] + '\n'
        'After=network-online.target remote-fs.target\n\n[Service]\nType=oneshot\n'
        'RemainAfterExit=yes\nTimeoutStartSec=70\nExecStart=' +
        ' '.join(_unit_word(value) for value in argv) + '\n')


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'VIEW_DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _alarm(signum, frame):
    raise TimeoutError('VIEW_FINITE_65_SECOND_BUDGET')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--config-bytes', required=True, type=int)
    parser.add_argument('--config-sha256', required=True)
    parser.add_argument('--mode', required=True, choices=('install_once', 'startup'))
    args = parser.parse_args(argv)
    system = NativeSystem()
    _require(system.euid() == 0, 'VIEW_REQUIRES_ROOT')
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(65)
    try:
        reference = dict(path=args.config, bytes=args.config_bytes, sha256=args.config_sha256)
        _pin(reference)
        _require(reference['bytes'] <= 65536, 'VIEW_CONFIG_TOO_LARGE')
        raw = system.read_pin(reference)
        _require(stat.S_IMODE(system.lstat(reference['path']).st_mode) == 0o400,
                 'VIEW_CONFIG_FILE_MODE')
        config = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=_unique_keys)
        validate_configuration(config)
        _configuration_pin(config, reference)
        result = (install_once if args.mode == 'install_once' else startup)(config, system=system)
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
