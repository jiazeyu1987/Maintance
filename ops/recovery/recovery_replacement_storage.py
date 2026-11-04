"""Explicit local storage custody for registered application replacement.

v1 keeps the original independent named-volume policy. v2 additionally binds
every writable data mount to an observed local directory and Linux mount.
No function in this module mutates storage or provisions a missing resource.
"""
from pathlib import Path, PurePosixPath
import json
import os
import re
import stat

from recovery_engine import require

LOCAL_FILESYSTEMS = frozenset(('ext2', 'ext3', 'ext4', 'xfs', 'btrfs', 'zfs'))
DATA_ROLES = frozenset(('mysql', 'minio', 'redis'))
MOUNT_FIELDS = frozenset(('mountId', 'parentId', 'device', 'root', 'mountPoint',
                         'filesystem', 'source', 'options', 'superOptions'))
STORAGE_FIELDS = frozenset(('role', 'type', 'source', 'destination', 'device', 'inode', 'mountIdentity'))


def _path(value, *, root=False):
    require(type(value) is str and value and '\\' not in value and
            not any(ord(c) < 32 for c in value), 'REPLACEMENT_STORAGE_PATH_INVALID')
    result = PurePosixPath(value)
    require(result.is_absolute() and str(result) == value and
            '..' not in result.parts and not value.startswith('//') and
            (root or value != '/'), 'REPLACEMENT_STORAGE_PATH_INVALID')
    return result


def overlaps(left, right):
    a, b = _path(left, root=True), _path(right, root=True)
    return a == b or a in b.parents or b in a.parents


def _decode_mount_field(value):
    decoded = re.sub(r'\\(040|011|012|134)', lambda m: chr(int(m.group(1), 8)), value)
    return decoded


def parse_mountinfo(text):
    """Parse the identity-bearing fields; optional propagation tags are ignored."""
    require(type(text) is str and text.strip(), 'REPLACEMENT_MOUNTINFO_INVALID')
    rows, seen = [], set()
    try:
        for line in text.splitlines():
            fields = line.split()
            separator = fields.index('-')
            require(separator >= 6 and len(fields) == separator + 4,
                    'REPLACEMENT_MOUNTINFO_INVALID')
            mid, parent = int(fields[0]), int(fields[1])
            require(mid > 0 and parent >= 0 and mid not in seen and
                    re.fullmatch(r'[0-9]+:[0-9]+', fields[2]), 'REPLACEMENT_MOUNTINFO_INVALID')
            seen.add(mid)
            row = dict(mountId=mid, parentId=parent, device=fields[2],
                root=_decode_mount_field(fields[3]), mountPoint=_decode_mount_field(fields[4]),
                filesystem=fields[separator+1], source=_decode_mount_field(fields[separator+2]),
                options=fields[5].split(','), superOptions=fields[separator+3].split(','))
            _path(row['root'], root=True); _path(row['mountPoint'], root=True)
            rows.append(row)
    except (ValueError, IndexError, TypeError) as error:
        raise ValueError('REPLACEMENT_MOUNTINFO_INVALID') from error
    return rows


def _mount_contract(value):
    require(type(value) is dict and set(value) == MOUNT_FIELDS and
            type(value['mountId']) is int and value['mountId'] > 0 and
            type(value['parentId']) is int and value['parentId'] >= 0 and
            type(value['device']) is str and re.fullmatch(r'[0-9]+:[0-9]+', value['device']) and
            type(value['source']) is str and value['source'] and
            all(type(value[k]) is list and value[k] and
                all(type(v) is str and v for v in value[k]) for k in ('options', 'superOptions')),
            'REPLACEMENT_STORAGE_CONFIGURATION_INVALID')
    _path(value['root'], root=True); _path(value['mountPoint'], root=True)
    require(value['filesystem'] in LOCAL_FILESYSTEMS, 'REPLACEMENT_FILESYSTEM_UNSUPPORTED')
    require(all('rw' in value[key] and 'ro' not in value[key]
                for key in ('options', 'superOptions')), 'REPLACEMENT_STORAGE_READ_ONLY')


def _mounted_path(path, mount):
    value = _path(path, root=True)
    point = _path(mount['mountPoint'], root=True)
    require(value == point or point in value.parents, 'REPLACEMENT_STORAGE_MOUNT_MISSING')
    relative = value.relative_to(point)
    return str(_path(mount['root'], root=True) / relative)


def physical_location(path, mounts):
    """Resolve bind aliases through mountinfo to a device plus filesystem path."""
    value = _path(path, root=True)
    matching = [m for m in mounts if value == _path(m['mountPoint'], root=True) or
                _path(m['mountPoint'], root=True) in value.parents]
    require(matching, 'REPLACEMENT_STORAGE_MOUNT_MISSING')
    selected = max(matching, key=lambda m: len(_path(m['mountPoint'], root=True).parts))
    require(sum(m['mountPoint'] == selected['mountPoint'] for m in matching) == 1,
            'REPLACEMENT_STORAGE_MOUNT_AMBIGUOUS')
    return selected['device'], _mounted_path(path, selected)


def _same_storage(left, right):
    return left[0] == right[0] and overlaps(left[1], right[1])


def validate_storage(value):
    require(type(value) is dict and set(value) == {'schemaVersion', 'protectedRoots', 'mounts'} and
            value['schemaVersion'] == 'RegisteredReplacementStorage/v1' and
            type(value['protectedRoots']) is list and type(value['mounts']) is list and value['mounts'],
            'REPLACEMENT_STORAGE_CONFIGURATION_INVALID')
    protected = value['protectedRoots']
    require(len(set(protected)) == len(protected) and '/mnt/nas' in protected,
            'REPLACEMENT_PROTECTED_ROOT_REQUIRED')
    for path in protected:
        _path(path, root=True)
    sources, physical, bindings = [], [], set()
    for item in value['mounts']:
        require(type(item) is dict and set(item) == STORAGE_FIELDS and
                item['role'] in DATA_ROLES and item['type'] in ('bind', 'volume') and
                type(item['device']) is int and item['device'] >= 0 and
                type(item['inode']) is int and item['inode'] > 0,
                'REPLACEMENT_STORAGE_CONFIGURATION_INVALID')
        source = _path(item['source']); _path(item['destination'])
        _mount_contract(item['mountIdentity'])
        mount = _path(item['mountIdentity']['mountPoint'], root=True)
        require(source != mount and mount in source.parents, 'REPLACEMENT_STORAGE_MOUNT_ROOT_REFUSED')
        binding = (item['role'], item['destination'])
        require(binding not in bindings and all(not overlaps(item['source'], old) for old in sources),
                'REPLACEMENT_STORAGE_OVERLAP')
        require(all(not overlaps(item['source'], path) for path in protected),
                'REPLACEMENT_PROTECTED_STORAGE_OVERLAP')
        mount_root = item['mountIdentity']['root']
        require(mount_root == '/' or all(not overlaps(mount_root, p) for p in protected),
                'REPLACEMENT_PROTECTED_STORAGE_OVERLAP')
        location = (item['mountIdentity']['device'], _mounted_path(item['source'], item['mountIdentity']))
        require(all(not _same_storage(location, old) for old in physical), 'REPLACEMENT_STORAGE_OVERLAP')
        sources.append(item['source']); bindings.add(binding)
        physical.append(location)
    return value


def observe_directory(path, mountinfo_text=None):
    """Return a real existing directory's custody identity without following links."""
    require(os.name == 'posix', 'REPLACEMENT_STORAGE_PLATFORM_INVALID')
    _path(path)
    directory = Path(path)
    try:
        ancestors = list(reversed((directory, *directory.parents)))
        before = []
        for part in ancestors:
            info = part.lstat()
            require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode),
                    'REPLACEMENT_STORAGE_PATH_INVALID')
            before.append((info.st_dev, info.st_ino))
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            current = os.fstat(fd)
            require(before[-1] == (current.st_dev, current.st_ino), 'REPLACEMENT_STORAGE_DIRECTORY_CHANGED')
            require(before == [(p.lstat().st_dev, p.lstat().st_ino) for p in ancestors],
                    'REPLACEMENT_STORAGE_DIRECTORY_CHANGED')
        finally:
            os.close(fd)
        text = Path('/proc/self/mountinfo').read_text(encoding='utf-8') if mountinfo_text is None else mountinfo_text
        mounts = parse_mountinfo(text)
        matching = [m for m in mounts if overlaps(path, m['mountPoint']) and
                    (_path(m['mountPoint'], root=True) in _path(path).parents or path == m['mountPoint'])]
        require(matching, 'REPLACEMENT_STORAGE_MOUNT_MISSING')
        selected = max(matching, key=lambda m: len(_path(m['mountPoint'], root=True).parts))
        require(sum(m['mountPoint'] == selected['mountPoint'] for m in matching) == 1,
                'REPLACEMENT_STORAGE_MOUNT_AMBIGUOUS')
        _mount_contract(selected)
        require(path != selected['mountPoint'], 'REPLACEMENT_STORAGE_MOUNT_ROOT_REFUSED')
        require(not any(m['mountPoint'] != selected['mountPoint'] and
                        _path(path) in _path(m['mountPoint'], root=True).parents for m in mounts),
                'REPLACEMENT_STORAGE_NESTED_MOUNT')
        require(selected['device'] == '%s:%s' % (os.major(current.st_dev), os.minor(current.st_dev)),
                'REPLACEMENT_STORAGE_DEVICE_CHANGED')
        return dict(device=current.st_dev, inode=current.st_ino, mountIdentity=selected)
    except OSError as error:
        raise ValueError('REPLACEMENT_STORAGE_PATH_INVALID') from error


def snapshot_mounts(rows, protected_roots):
    """Collect a proposed v2 contract; installation must still verify Docker owners."""
    mounts = []
    for role, row in rows.items():
        for mount in row['Mounts']:
            if not mount['RW']:
                continue
            require(role in DATA_ROLES and mount['Type'] in ('bind', 'volume'), 'REPLACEMENT_STORAGE_INVALID')
            mounts.append(dict(role=role, type=mount['Type'], source=mount['Source'],
                destination=mount['Destination'], **observe_directory(mount['Source'])))
    return validate_storage(dict(schemaVersion='RegisteredReplacementStorage/v1',
        protectedRoots=list(protected_roots), mounts=mounts))


def _volume(native, mount):
    volume = json.loads(native.docker(['volume', 'inspect', mount['Name']]))
    require(type(volume) is list and len(volume) == 1 and volume[0]['Driver'] == 'local' and
            not volume[0]['Options'] and volume[0]['Mountpoint'] == mount['Source'],
            'REPLACEMENT_STORAGE_INVALID')


def _consumers(native, target_ids):
    identities = native.docker(['ps', '--all', '--no-trunc', '--format', '{{.ID}}']).decode().splitlines()
    require(identities and all(identities) and len(set(identities)) == len(identities) and
            set(target_ids) <= set(identities), 'REPLACEMENT_CONSUMER_INVENTORY_CHANGED')
    rows = json.loads(native.docker(['inspect', *identities]))
    require(type(rows) is list and len(rows) == len(identities) and
            all(type(row) is dict and type(row.get('Id')) is str and type(row.get('Mounts')) is list
                for row in rows), 'REPLACEMENT_CONSUMER_INVENTORY_CHANGED')
    returned = [row['Id'] for row in rows]
    require(len(set(returned)) == len(returned) and set(returned) == set(identities),
            'REPLACEMENT_CONSUMER_INVENTORY_CHANGED')
    return rows


def verify_storage(native, value, rows):
    """Validate all registered write mounts and every container, including stopped ones."""
    v2 = value['schemaVersion'] == 'RegisteredApplicationReplacement/v2'
    registered, physical, mounts = {}, {}, None
    if v2:
        storage = validate_storage(value['storage'])
        required = [*native.source['archiveRoots'], str(native.root), value.get('stateRoot', native.config['replacement']['stateRoot']),
                    native.config['dataRoot']]
        require(all(any(_path(path, root=True) == _path(root, root=True) or
                        _path(root, root=True) in _path(path, root=True).parents
                        for root in storage['protectedRoots']) for path in required),
                'REPLACEMENT_PROTECTED_ROOT_REQUIRED')
        registered = {(m['role'], m['destination']): m for m in storage['mounts']}
        mounts = parse_mountinfo(Path('/proc/self/mountinfo').read_text(encoding='utf-8'))
    writable, used = {}, set()
    for role, row in rows.items():
        for mount in row['Mounts']:
            if not mount['RW']:
                continue
            require(role in DATA_ROLES and mount['Type'] in (('bind', 'volume') if v2 else ('volume',)) and
                    all(not overlaps(mount['Source'], path) for path in writable), 'REPLACEMENT_STORAGE_INVALID')
            if mount['Type'] == 'volume':
                _volume(native, mount)
            if v2:
                key = (role, mount['Destination'])
                require(key in registered, 'REPLACEMENT_STORAGE_BINDING_CHANGED')
                expected = registered[key]
                require(all(expected[k] == mount[f] for k, f in [('type','Type'),('source','Source'),('destination','Destination')]),
                        'REPLACEMENT_STORAGE_BINDING_CHANGED')
                observed = observe_directory(mount['Source'])
                require(all(expected[k] == observed[k] for k in ('device', 'inode', 'mountIdentity')),
                        'REPLACEMENT_STORAGE_DIRECTORY_CHANGED')
                used.add(key)
                location = physical_location(mount['Source'], mounts)
                require(all(not _same_storage(location, physical_location(p, mounts))
                            for p in storage['protectedRoots']), 'REPLACEMENT_PROTECTED_STORAGE_OVERLAP')
                require(all(not _same_storage(location, old) for old in physical.values()),
                        'REPLACEMENT_STORAGE_OVERLAP')
                physical[mount['Source']] = location
            writable[mount['Source']] = row['Id']
    require(not v2 or used == set(registered), 'REPLACEMENT_STORAGE_BINDING_CHANGED')
    for consumer in _consumers(native, [row['Id'] for row in rows.values()]):
        identity = consumer['Id']
        for mount in consumer['Mounts']:
            if not mount.get('RW') or not mount.get('Source'):
                continue
            require(all(not overlaps(mount['Source'], path) or
                        identity == owner and mount['Source'] == path for path, owner in writable.items()),
                    'REPLACEMENT_VOLUME_SHARED')
            if v2:
                location = physical_location(mount['Source'], mounts)
                require(all(not _same_storage(location, physical[path]) or
                            identity == owner and mount['Source'] == path for path, owner in writable.items()),
                        'REPLACEMENT_VOLUME_SHARED')
    return writable
