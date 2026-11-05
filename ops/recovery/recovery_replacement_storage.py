"""Explicit local storage custody for registered application replacement.

Replacement/v1 keeps the original independent named-volume policy. Versioned
storage contracts bind writable data to observed directories and Linux mounts;
storage/v2 additionally pins local-volume definitions and bind backing custody.
No function in this module mutates storage or provisions a missing resource.
"""
from pathlib import Path, PurePosixPath
import json
import os
import re
import stat

from recovery_engine import digest, require

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
            if row['filesystem'] == 'nsfs' and not row['root'].startswith('/'):
                require(re.fullmatch(r'(?:net|mnt|uts|ipc|user|pid|pid_for_children|cgroup|time|time_for_children):\[[0-9]+\]',
                                     row['root']), 'REPLACEMENT_MOUNTINFO_INVALID')
            else:
                _path(row['root'], root=True)
            _path(row['mountPoint'], root=True)
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
    require(value['filesystem'] in LOCAL_FILESYSTEMS, 'REPLACEMENT_FILESYSTEM_UNSUPPORTED')
    _path(value['root'], root=True); _path(value['mountPoint'], root=True)
    require(all('rw' in value[key] and 'ro' not in value[key]
                for key in ('options', 'superOptions')), 'REPLACEMENT_STORAGE_READ_ONLY')


def _mounted_path(path, mount):
    require(mount['filesystem'] != 'nsfs', 'REPLACEMENT_FILESYSTEM_UNSUPPORTED')
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


def _directory_contract(item):
    require(type(item['device']) is int and item['device'] >= 0 and
            type(item['inode']) is int and item['inode'] > 0,
            'REPLACEMENT_STORAGE_CONFIGURATION_INVALID')
    _path(item['source']); _mount_contract(item['mountIdentity'])


def _volume_contract(item):
    volume = item['volume']
    require(type(volume) is dict and set(volume) == {'name', 'driver', 'options', 'mountpoint', 'backing'} and
            type(volume['name']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', volume['name']) and
            volume['driver'] == 'local' and volume['mountpoint'] == item['source'] and
            (volume['options'] is None or type(volume['options']) is dict), 'REPLACEMENT_STORAGE_INVALID')
    options, backing = volume['options'], volume['backing']
    if not options and backing is None:
        return None
    if options:
        require(set(options) == {'type', 'o', 'device'} and options['type'] == 'none' and
                type(options['o']) is str and set(options['o'].split(',')) in ({'bind'}, {'bind', 'rw'}) and
                len(set(options['o'].split(','))) == len(options['o'].split(',')), 'REPLACEMENT_STORAGE_INVALID')
    require(type(backing) is dict and set(backing) == {'source', 'device', 'inode', 'mountIdentity'} and
            (not options or backing['source'] == options['device']), 'REPLACEMENT_STORAGE_INVALID')
    _directory_contract(backing)
    require(_path(backing['mountIdentity']['mountPoint'], root=True) in _path(backing['source']).parents and
            not overlaps(item['source'], backing['source']), 'REPLACEMENT_STORAGE_MOUNT_ROOT_REFUSED')
    _bound_directory(item, backing)
    return backing


def _bound_directory(item, backing):
    require(item['mountIdentity']['root'] != '/' and
            item['mountIdentity']['mountPoint'] == item['source'] and
            item['mountIdentity']['mountId'] != backing['mountIdentity']['mountId'] and
            item['mountIdentity']['filesystem'] == backing['mountIdentity']['filesystem'] and
            item['mountIdentity']['source'] == backing['mountIdentity']['source'] and
            item['device'] == backing['device'] and item['inode'] == backing['inode'] and
            item['mountIdentity']['device'] == backing['mountIdentity']['device'] and
            _mounted_path(item['source'], item['mountIdentity']) ==
            _mounted_path(backing['source'], backing['mountIdentity']), 'REPLACEMENT_VOLUME_BACKING_CHANGED')


def validate_storage(value):
    retained = type(value) is dict and value.get('schemaVersion') == 'RegisteredReplacementStorage/v3'
    require(type(value) is dict and set(value) == {'schemaVersion', 'protectedRoots', 'mounts'} |
            ({'preservedApplicationMounts', 'inactiveConsumers'} if retained else set()) and
            value['schemaVersion'] in ('RegisteredReplacementStorage/v1', 'RegisteredReplacementStorage/v2',
                                      'RegisteredReplacementStorage/v3') and
            type(value['protectedRoots']) is list and type(value['mounts']) is list and value['mounts'],
            'REPLACEMENT_STORAGE_CONFIGURATION_INVALID')
    protected = value['protectedRoots']
    require(len(set(protected)) == len(protected) and '/mnt/nas' in protected,
            'REPLACEMENT_PROTECTED_ROOT_REQUIRED')
    for path in protected:
        _path(path, root=True)
    sources, physical, bindings = [], [], set()
    for item in value['mounts']:
        has_volume = value['schemaVersion'] != 'RegisteredReplacementStorage/v1' and type(item) is dict and item.get('type') == 'volume'
        require(type(item) is dict and set(item) == STORAGE_FIELDS | ({'volume'} if has_volume else set()) and
                item['role'] in DATA_ROLES and item['type'] in ('bind', 'volume') and
                type(item['device']) is int and item['device'] >= 0 and
                type(item['inode']) is int and item['inode'] > 0,
                'REPLACEMENT_STORAGE_CONFIGURATION_INVALID')
        source = _path(item['source']); _path(item['destination'])
        _mount_contract(item['mountIdentity'])
        backing = _volume_contract(item) if has_volume else None
        mount = _path(item['mountIdentity']['mountPoint'], root=True)
        require(mount in source.parents or backing is not None and source == mount,
                'REPLACEMENT_STORAGE_MOUNT_ROOT_REFUSED')
        binding = (item['role'], item['destination'])
        paths = [item['source']] + ([backing['source']] if backing is not None else [])
        require(binding not in bindings and all(not overlaps(path, old) for path in paths for old in sources),
                'REPLACEMENT_STORAGE_OVERLAP')
        require(all(not overlaps(path, protected_path) for path in paths for protected_path in protected),
                'REPLACEMENT_PROTECTED_STORAGE_OVERLAP')
        mount_root = item['mountIdentity']['root']
        require(mount_root == '/' or all(not overlaps(mount_root, p) for p in protected),
                'REPLACEMENT_PROTECTED_STORAGE_OVERLAP')
        location = (item['mountIdentity']['device'], _mounted_path(item['source'], item['mountIdentity']))
        require(all(not _same_storage(location, old) for old in physical), 'REPLACEMENT_STORAGE_OVERLAP')
        sources.extend(paths); bindings.add(binding)
        physical.append(location)
    if retained:
        _validate_retained(value)
    return value


def _validate_retained(storage):
    entries, inactive = storage['preservedApplicationMounts'], storage['inactiveConsumers']
    require(type(entries) is list and entries and type(inactive) is list,
            'REPLACEMENT_RETAINED_CONFIGURATION_INVALID')
    bindings = set()
    identity_fields = {'resolvedPath', 'device', 'inode', 'mode', 'uid', 'gid', 'kind',
                       'mountIdentity', 'pathLinks', 'contentDigest'}
    for entry in entries:
        require(type(entry) is dict and set(entry) == {'role', 'mount', 'identity'} and
                type(entry['role']) is str and entry['role'] not in DATA_ROLES and entry['role'] and
                type(entry['mount']) is dict and entry['mount'].get('Type') == 'bind' and
                type(entry['mount'].get('RW')) is bool, 'REPLACEMENT_RETAINED_CONFIGURATION_INVALID')
        mount, observed = entry['mount'], entry['identity']
        _path(mount['Source']); _path(mount['Destination'])
        binding = (entry['role'], mount['Destination'])
        require(binding not in bindings, 'REPLACEMENT_RETAINED_BINDING_DUPLICATE')
        bindings.add(binding)
        require(type(observed) is dict and set(observed) == identity_fields and
                observed['kind'] in ('directory', 'file', 'socket') and
                all(type(observed[k]) is int and observed[k] >= 0 for k in ('device', 'mode', 'uid', 'gid')) and
                type(observed['inode']) is int and observed['inode'] > 0 and
                type(observed['mountIdentity']) is dict and set(observed['mountIdentity']) == MOUNT_FIELDS and
                type(observed['pathLinks']) is list and
                (observed['contentDigest'] is None if mount['RW'] else
                 type(observed['contentDigest']) is str and re.fullmatch('[0-9a-f]{64}', observed['contentDigest'])),
                'REPLACEMENT_RETAINED_CONFIGURATION_INVALID')
        _path(observed['resolvedPath'])
        for link in observed['pathLinks']:
            require(type(link) is dict and set(link) == {'path', 'target', 'device', 'inode'} and
                    type(link['target']) is str and link['target'] and
                    all(type(link[k]) is int and link[k] >= 0 for k in ('device', 'inode')),
                    'REPLACEMENT_RETAINED_CONFIGURATION_INVALID')
            _path(link['path'])
    ids = set()
    for item in inactive:
        require(type(item) is dict and set(item) == {'id', 'configurationDigest', 'mounts'} and
                type(item['id']) is str and item['id'] and item['id'] not in ids and
                type(item['configurationDigest']) is str and re.fullmatch('[0-9a-f]{64}', item['configurationDigest']) and
                type(item['mounts']) is list, 'REPLACEMENT_INACTIVE_CONFIGURATION_INVALID')
        ids.add(item['id'])


def _configuration_digest(row):
    return digest({key: row[key] for key in ('Path', 'Args', 'HostConfig', 'Config')})


def _inactive(row):
    state = row['State']
    require(state.get('Running') is False and state.get('Paused') is False and
            state.get('Restarting') is False and type(state.get('Pid')) is int and state['Pid'] == 0 and
            state.get('Status') in ('created', 'exited') and row.get('ExecIDs') in (None, []),
            'REPLACEMENT_HISTORICAL_CONSUMER_ACTIVE')


def observe_preserved_mount(mount):
    """Pin a retained bind, including explicit path aliases and read-only bytes.

    Read/write directory contents intentionally remain live. The directory itself
    and its mount stay pinned; it never enters the data replacement list.
    """
    import hashlib
    require(os.name == 'posix' and mount.get('Type') == 'bind', 'REPLACEMENT_RETAINED_PLATFORM_INVALID')
    _path(mount['Source'])
    source = Path(mount['Source'])
    try:
        links = []
        for part in reversed((source, *source.parents)):
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode):
                links.append(dict(path=str(part), target=os.readlink(part), device=info.st_dev, inode=info.st_ino))
        resolved = source.resolve(strict=True)
        info = resolved.lstat()
        kind = next((name for name, check in (('directory', stat.S_ISDIR), ('file', stat.S_ISREG),
                     ('socket', stat.S_ISSOCK)) if check(info.st_mode)), None)
        require(kind is not None, 'REPLACEMENT_RETAINED_TYPE_INVALID')
        mounts = parse_mountinfo(Path('/proc/self/mountinfo').read_text(encoding='utf-8'))
        selected = [m for m in mounts if str(resolved) == m['mountPoint'] or
                    _path(m['mountPoint'], root=True) in _path(str(resolved)).parents]
        require(selected, 'REPLACEMENT_STORAGE_MOUNT_MISSING')
        selected = max(selected, key=lambda m: len(_path(m['mountPoint'], root=True).parts))
        require(sum(m['mountPoint'] == selected['mountPoint'] for m in mounts) == 1,
                'REPLACEMENT_STORAGE_MOUNT_AMBIGUOUS')
        content = None
        if not mount['RW']:
            require(kind in ('directory', 'file'), 'REPLACEMENT_RETAINED_TYPE_INVALID')
            entries, size = [], 0
            paths = [resolved] if kind == 'file' else sorted(resolved.rglob('*'))
            require(len(paths) <= 10000, 'REPLACEMENT_RETAINED_TREE_LIMIT')
            for path in paths:
                before = path.lstat()
                require(stat.S_ISREG(before.st_mode) or stat.S_ISDIR(before.st_mode),
                        'REPLACEMENT_RETAINED_TREE_TYPE_INVALID')
                checksum = None
                if stat.S_ISREG(before.st_mode):
                    size += before.st_size
                    require(size <= 1024**3, 'REPLACEMENT_RETAINED_TREE_LIMIT')
                    checksum = hashlib.sha256()
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                    with os.fdopen(fd, 'rb') as stream:
                        require(_stat_identity(os.fstat(stream.fileno())) == _stat_identity(before),
                                'REPLACEMENT_RETAINED_CHANGED')
                        for block in iter(lambda: stream.read(1024**2), b''): checksum.update(block)
                    require(_stat_identity(path.lstat()) == _stat_identity(before), 'REPLACEMENT_RETAINED_CHANGED')
                    checksum = checksum.hexdigest()
                entries.append(dict(path=str(path.relative_to(resolved)) if kind == 'directory' else '.',
                    device=before.st_dev, inode=before.st_ino, mode=before.st_mode,
                    uid=before.st_uid, gid=before.st_gid, sha256=checksum))
            content = digest(entries)
        require(_stat_identity(resolved.lstat()) == _stat_identity(info) and source.resolve(strict=True) == resolved and
                all(Path(link['path']).is_symlink() and os.readlink(link['path']) == link['target'] and
                    Path(link['path']).lstat().st_ino == link['inode'] for link in links),
                'REPLACEMENT_RETAINED_CHANGED')
        return dict(resolvedPath=str(resolved), device=info.st_dev, inode=info.st_ino,
            mode=info.st_mode, uid=info.st_uid, gid=info.st_gid, kind=kind,
            mountIdentity=selected, pathLinks=links, contentDigest=content)
    except OSError as error:
        raise ValueError('REPLACEMENT_RETAINED_PATH_INVALID') from error


def _stat_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def snapshot_retained_storage(rows, protected_roots, inactive_consumers, **kwargs):
    """Select v3 explicitly. Inactive consumers must be supplied and verified anew."""
    from copy import deepcopy
    data = snapshot_mounts({r: row for r, row in rows.items() if r in DATA_ROLES}, protected_roots, **kwargs)
    data['schemaVersion'] = 'RegisteredReplacementStorage/v3'
    data['preservedApplicationMounts'] = [dict(role=role, mount=deepcopy(mount),
        identity=observe_preserved_mount(mount)) for role, row in rows.items() if role not in DATA_ROLES
        for mount in row['Mounts']]
    data['inactiveConsumers'] = []
    for row in inactive_consumers:
        _inactive(row)
        data['inactiveConsumers'].append(dict(id=row['Id'], configurationDigest=_configuration_digest(row),
            mounts=sorted(deepcopy(row['Mounts']), key=lambda m: m['Destination'])))
    return validate_storage(data)


def verify_preserved_mounts(storage, rows):
    """Return exact approved consumer/mount pairs, never replacement paths."""
    validate_storage(storage)
    expected = {(e['role'], e['mount']['Destination']): e for e in storage['preservedApplicationMounts']}
    observed = {(role, m['Destination']): (row['Id'], m) for role, row in rows.items()
                if role not in DATA_ROLES for m in row['Mounts']}
    require(set(expected) == set(observed), 'REPLACEMENT_RETAINED_BINDING_CHANGED')
    approved = []
    for key, entry in expected.items():
        identity, mount = observed[key]
        require(mount == entry['mount'] and observe_preserved_mount(mount) == entry['identity'],
                'REPLACEMENT_RETAINED_CHANGED')
        approved.append((identity, mount))
    return approved


def observe_directory(path, mountinfo_text=None, *, backing=None):
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
        require(path != selected['mountPoint'] or backing is not None,
                'REPLACEMENT_STORAGE_MOUNT_ROOT_REFUSED')
        require(not any(m['mountPoint'] != selected['mountPoint'] and
                        _path(path) in _path(m['mountPoint'], root=True).parents for m in mounts),
                'REPLACEMENT_STORAGE_NESTED_MOUNT')
        require(selected['device'] == '%s:%s' % (os.major(current.st_dev), os.minor(current.st_dev)),
                'REPLACEMENT_STORAGE_DEVICE_CHANGED')
        result = dict(device=current.st_dev, inode=current.st_ino, mountIdentity=selected)
        if backing is not None:
            _directory_contract(backing)
            require(_path(backing['mountIdentity']['mountPoint'], root=True) in _path(backing['source']).parents,
                    'REPLACEMENT_STORAGE_MOUNT_ROOT_REFUSED')
            _bound_directory(dict(source=path, **result), backing)
        return result
    except OSError as error:
        raise ValueError('REPLACEMENT_STORAGE_PATH_INVALID') from error


def snapshot_mounts(rows, protected_roots, *, volume_inspector=None, volume_backing_paths=None):
    """Observe storage; an explicit single-volume inspector selects storage/v2.

    volume_inspector(name) must return one Docker volume-inspect dictionary.
    Host-managed binds require explicit volume_backing_paths[name]; no path is inferred.
    Installation must still verify every Docker owner with verify_storage.
    """
    require(volume_inspector is None or callable(volume_inspector), 'REPLACEMENT_VOLUME_INSPECTOR_INVALID')
    require(volume_backing_paths is None or type(volume_backing_paths) is dict and volume_inspector is not None,
            'REPLACEMENT_VOLUME_BACKING_INPUT_INVALID')
    backing_paths = {} if volume_backing_paths is None else volume_backing_paths
    require(all(type(name) is str and name for name in backing_paths), 'REPLACEMENT_VOLUME_BACKING_INPUT_INVALID')
    for path in backing_paths.values(): _path(path)
    mounts, used_backings = [], set()
    for role, row in rows.items():
        for mount in row['Mounts']:
            if not mount['RW']:
                continue
            require(role in DATA_ROLES and mount['Type'] in ('bind', 'volume'), 'REPLACEMENT_STORAGE_INVALID')
            item = dict(role=role, type=mount['Type'], source=mount['Source'], destination=mount['Destination'])
            backing = None
            if mount['Type'] == 'volume' and volume_inspector is not None:
                volume = _volume_definition(volume_inspector(mount['Name']), mount)
                backing_path = backing_paths.get(mount['Name'])
                if backing_path is not None:
                    used_backings.add(mount['Name'])
                if volume['options']:
                    options = volume['options']
                    require(type(options) is dict and set(options) == {'type', 'o', 'device'} and
                            options['type'] == 'none' and type(options['o']) is str and
                            set(options['o'].split(',')) in ({'bind'}, {'bind', 'rw'}), 'REPLACEMENT_STORAGE_INVALID')
                    require(backing_path is None or backing_path == options['device'],
                            'REPLACEMENT_VOLUME_BACKING_INPUT_INVALID')
                    backing_path = options['device']
                if backing_path is not None:
                    backing = dict(source=backing_path, **observe_directory(backing_path))
                item['volume'] = dict(**volume, backing=backing)
            item.update(observe_directory(mount['Source'], backing=backing))
            mounts.append(item)
    require(used_backings == set(backing_paths), 'REPLACEMENT_VOLUME_BACKING_INPUT_INVALID')
    return validate_storage(dict(schemaVersion='RegisteredReplacementStorage/v2' if volume_inspector is not None
        else 'RegisteredReplacementStorage/v1',
        protectedRoots=list(protected_roots), mounts=mounts))


def _volume_definition(volume, mount):
    require(type(volume) is dict and volume.get('Name') == mount['Name'] and volume.get('Driver') == 'local' and
            volume.get('Mountpoint') == mount['Source'] and 'Options' in volume and
            (volume['Options'] is None or type(volume['Options']) is dict), 'REPLACEMENT_STORAGE_INVALID')
    return dict(name=volume['Name'], driver=volume['Driver'],
        options=None if volume['Options'] is None else dict(volume['Options']), mountpoint=volume['Mountpoint'])


def _volume(native, mount, expected=None):
    volume = json.loads(native.docker(['volume', 'inspect', mount['Name']]))
    if expected is not None:
        require(type(volume) is list and len(volume) == 1 and
                _volume_definition(volume[0], mount) == {k: v for k, v in expected.items() if k != 'backing'},
                'REPLACEMENT_VOLUME_CONFIGURATION_CHANGED')
        return
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
    preserved, inactive = [], {}
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
        if storage['schemaVersion'] == 'RegisteredReplacementStorage/v3':
            preserved = verify_preserved_mounts(storage, rows)
            inactive = {item['id']: item for item in storage['inactiveConsumers']}
            require(not set(inactive) & {row['Id'] for row in rows.values()},
                    'REPLACEMENT_INACTIVE_CONFIGURATION_INVALID')
    writable, used = {}, set()
    for role, row in rows.items():
        for mount in row['Mounts']:
            if (row['Id'], mount) in preserved:
                continue
            if not mount['RW']:
                continue
            require(role in DATA_ROLES and mount['Type'] in (('bind', 'volume') if v2 else ('volume',)) and
                    all(not overlaps(mount['Source'], path) for path in writable), 'REPLACEMENT_STORAGE_INVALID')
            expected = None
            if v2:
                key = (role, mount['Destination'])
                require(key in registered, 'REPLACEMENT_STORAGE_BINDING_CHANGED')
                expected = registered[key]
                require(all(expected[k] == mount[f] for k, f in [('type','Type'),('source','Source'),('destination','Destination')]),
                        'REPLACEMENT_STORAGE_BINDING_CHANGED')
                backing = expected.get('volume', {}).get('backing')
                if mount['Type'] == 'volume':
                    _volume(native, mount, expected.get('volume'))
                if backing is not None:
                    observed_backing = observe_directory(backing['source'])
                    require(all(backing[k] == observed_backing[k] for k in ('device', 'inode', 'mountIdentity')),
                            'REPLACEMENT_VOLUME_BACKING_CHANGED')
                observed = observe_directory(mount['Source'], backing=backing)
                require(all(expected[k] == observed[k] for k in ('device', 'inode', 'mountIdentity')),
                        'REPLACEMENT_STORAGE_DIRECTORY_CHANGED')
                used.add(key)
                location = physical_location(mount['Source'], mounts)
                require(all(not _same_storage(location, physical_location(p, mounts))
                            for p in storage['protectedRoots']), 'REPLACEMENT_PROTECTED_STORAGE_OVERLAP')
                require(all(not _same_storage(location, old) for old in physical.values()),
                        'REPLACEMENT_STORAGE_OVERLAP')
                physical[mount['Source']] = location
            elif mount['Type'] == 'volume':
                _volume(native, mount)
            writable[mount['Source']] = row['Id']
    require(not v2 or used == set(registered), 'REPLACEMENT_STORAGE_BINDING_CHANGED')
    consumers = _consumers(native, [row['Id'] for row in rows.values()])
    require(set(inactive) <= {row['Id'] for row in consumers}, 'REPLACEMENT_HISTORICAL_CONSUMER_MISSING')
    for consumer in consumers:
        identity = consumer['Id']
        if identity in inactive:
            expected = inactive[identity]
            _inactive(consumer)
            require(_configuration_digest(consumer) == expected['configurationDigest'] and
                    sorted(consumer['Mounts'], key=lambda m: m['Destination']) == expected['mounts'],
                    'REPLACEMENT_HISTORICAL_CONSUMER_CHANGED')
        for mount in consumer['Mounts']:
            if not mount.get('RW') or not mount.get('Source'):
                continue
            if identity in inactive or (identity, mount) in preserved:
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
