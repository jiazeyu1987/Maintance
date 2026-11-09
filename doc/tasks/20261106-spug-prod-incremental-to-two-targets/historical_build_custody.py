"""Explicit custody of original build inputs, independent of disposable checkouts.

This module does not verify installation success or grant installation admission.
Only original report-bound inputs are archived; no missing-path fallback exists.
"""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tarfile

MAX_INPUTS = 4096
MAX_GROUPS = 128
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_BYTES = 160 * 1024 * 1024
MAX_METADATA_BYTES = 16 * 1024 * 1024
INPUT_SCHEMA = 'HistoricalBuildCustodyInputs/v1'
SCHEMA = 'HistoricalBuildCustody/v1'


def _need(value, code):
    if not value:
        raise ValueError('BUILD_CUSTODY_' + code)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def _object(pairs):
    value = {}
    for key, item in pairs:
        _need(key not in value, 'JSON_DUPLICATE_KEY')
        value[key] = item
    return value


def _json(raw):
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError('BUILD_CUSTODY_JSON_CONSTANT')))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('BUILD_CUSTODY_JSON_INVALID') from error


def _fields(value, names, code='FORMAT_INVALID'):
    _need(type(value) is dict and set(value) == set(names.split()), code)


def _hex(value, length):
    return type(value) is str and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None


def _path(value):
    _need(type(value) is str and value and '\x00' not in value, 'PATH_INVALID')
    path = Path(value)
    _need(path.is_absolute() and '..' not in path.parts and str(path) == value, 'PATH_INVALID')
    return path


def _real(path, *, directory=False):
    path = _path(str(path))
    try:
        _need(path.resolve(strict=True) == path and not path.is_symlink(), 'PATH_ALIAS')
        mode = path.lstat().st_mode
        _need(stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode), 'FILE_TYPE_INVALID')
    except OSError as error:
        raise ValueError('BUILD_CUSTODY_INPUT_UNAVAILABLE') from error
    return path


def _pin(reference):
    _fields(reference, 'path bytes sha256', 'PIN_INVALID')
    _path(reference['path'])
    _need(type(reference['bytes']) is int and reference['bytes'] >= 0 and _hex(reference['sha256'], 64), 'PIN_INVALID')
    return reference


def _identity(info):
    # Windows fstat exposes change time while Path.stat may expose creation time
    # as ctime. Birth time is consistent across the two APIs; content is pinned.
    stamp = info.st_birthtime_ns if os.name == 'nt' else info.st_ctime_ns
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, stamp)


def _read(path, limit):
    path = _real(path)
    try:
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
        with os.fdopen(os.open(path, flags), 'rb') as stream:
            before = os.fstat(stream.fileno())
            _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'FILE_TYPE_INVALID')
            _need(before.st_size <= limit, 'FILE_LIMIT')
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        _need(len(raw) <= limit, 'FILE_LIMIT')
        _real(path)
        _need(before.st_ctime_ns == after.st_ctime_ns and
              _identity(before) == _identity(after) == _identity(path.stat()) and len(raw) == before.st_size,
              'INPUT_CHANGED_DURING_READ')
    except OSError as error:
        raise ValueError('BUILD_CUSTODY_INPUT_UNAVAILABLE') from error
    return raw


def _read_pin(reference, limit=MAX_METADATA_BYTES):
    _pin(reference)
    _need(reference['bytes'] <= limit, 'FILE_LIMIT')
    raw = _read(Path(reference['path']), limit)
    _need(len(raw) == reference['bytes'] and _sha(raw) == reference['sha256'], 'PIN_CHANGED')
    return raw


def _file_pin(path, limit=MAX_METADATA_BYTES):
    raw = _read(path, limit)
    return dict(path=str(path), bytes=len(raw), sha256=_sha(raw))


def _name(value):
    _need(type(value) is str and value and not any(c in value for c in ('\\', ':', '\x00', '\n', '\r')), 'MEMBER_NAME_INVALID')
    path = PurePosixPath(value)
    _need(not path.is_absolute() and '..' not in path.parts and str(path) == value and value != '.', 'MEMBER_NAME_INVALID')
    return value


def _git(repository, args, raw=None, *, limit=MAX_TOTAL_BYTES + 1024 * 1024):
    try:
        result = subprocess.run(['git', '-C', str(repository), *args], input=raw, capture_output=True,
                                env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'), timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError('BUILD_CUSTODY_GIT_FAILED') from error
    _need(result.returncode == 0 and len(result.stdout) <= limit, 'GIT_FAILED')
    return result.stdout


def _git_text(repository, args):
    return _git(repository, args).decode('utf-8').strip()


class _Reports:
    def __init__(self, task):
        self.task = task
        self.values = {}
        self.pins = {}

    def read(self, reference):
        _pin(reference)
        path = Path(reference['path'])
        _need(path.parent == self.task and path.suffix == '.json', 'REPORT_SCOPE_INVALID')
        if str(path) in self.pins:
            _need(self.pins[str(path)] == reference, 'PIN_CONFLICT')
        else:
            self.values[str(path)] = _json(_read_pin(reference))
            self.pins[str(path)] = deepcopy(reference)
        return self.values[str(path)]

    def finish(self):
        for reference in self.pins.values():
            _read_pin(reference)
        return deepcopy(list(self.pins.values()))


def _plan(task, inputs, repository):
    _fields(inputs, 'schemaVersion taskId builds sets')
    _need(inputs['schemaVersion'] == INPUT_SCHEMA and inputs['taskId'] == task.name, 'INPUT_IDENTITY_INVALID')
    _need(type(inputs['builds']) is list and 0 < len(inputs['builds']) <= MAX_GROUPS and
          type(inputs['sets']) is list and 0 < len(inputs['sets']) <= MAX_GROUPS, 'INPUT_LIMIT')
    reports = _Reports(task)
    builds = {}
    for item in inputs['builds']:
        _fields(item, 'id kind reportPin')
        identifier = item['id']
        _need(type(identifier) is str and re.fullmatch('[a-z][a-z0-9-]{0,63}', identifier) and identifier not in builds,
              'BUILD_ID_INVALID')
        _need(item['kind'] in ('ENGINE_PACKAGE', 'SPUG_RESOURCE'), 'BUILD_KIND_INVALID')
        report = reports.read(item['reportPin'])
        _need(type(report) is dict and report.get('status') == 'PASS', 'BUILD_REPORT_INVALID')
        commit = report.get('targetCommit' if item['kind'] == 'ENGINE_PACKAGE' else 'sourceCommit')
        _need(_hex(commit, 40), 'BUILD_COMMIT_INVALID')
        worktree = _path(report.get('worktree'))
        _need(_git_text(repository, ['rev-parse', '--verify', commit + '^{commit}']) == commit, 'GIT_BINDING_CHANGED')
        tree = _git_text(repository, ['rev-parse', '--verify', commit + '^{tree}'])
        _need(_hex(tree, 40), 'GIT_BINDING_CHANGED')
        builds[identifier] = dict(id=identifier, kind=item['kind'], reportPin=deepcopy(item['reportPin']),
                                 sourceCommit=commit, originalWorktree=str(worktree), treeId=tree)
    bindings = []
    originals = {}
    group_keys = set()
    used_builds = set()
    for group in inputs['sets']:
        _fields(group, 'reportPin field bindings')
        _need(group['field'] in ('inputPins', 'sourcePins', 'files'), 'REPORT_FIELD_INVALID')
        report = reports.read(group['reportPin'])
        expected = report.get(group['field']) if type(report) is dict else None
        _need(type(expected) is dict and expected and len(expected) <= MAX_INPUTS, 'REPORT_SET_INVALID')
        key = (group['reportPin']['path'], group['field'])
        _need(key not in group_keys, 'REPORT_SET_INVALID')
        group_keys.add(key)
        rows = group['bindings']
        _need(type(rows) is list and len(rows) == len(expected), 'REPORT_SET_INVALID')
        _need(all(type(row) is dict and type(row.get('name')) is str for row in rows) and
              len({row['name'] for row in rows}) == len(rows) and {row['name'] for row in rows} == set(expected),
              'REPORT_SET_INVALID')
        for row in sorted(rows, key=lambda r: r['name']):
            _fields(row, 'name purpose buildId originalPin')
            name = _name(row['name'])
            reference = _pin(row['originalPin'])
            if row['purpose'] in ('COMMITTED_SOURCE', 'REPOSITORY_SOURCE'):
                _need(type(row['buildId']) is str and row['buildId'] in builds, 'BUILD_ID_INVALID')
                base = (Path(builds[row['buildId']]['originalWorktree']) if row['purpose'] == 'COMMITTED_SOURCE'
                        else task.parents[2])
                used_builds.add(row['buildId'])
            else:
                _need(row['purpose'] == 'TASK_ORIGINAL' and row['buildId'] is None and
                      name.startswith('doc/tasks/' + task.name + '/'), 'SOURCE_PATH_INVALID')
                base = task.parents[2]
            _need(Path(reference['path']) == base.joinpath(*PurePosixPath(name).parts), 'SOURCE_PATH_INVALID')
            value = expected[name]
            if type(value) is str:
                _need(_hex(value, 64) and reference['sha256'] == value, 'SOURCE_PIN_CHANGED')
            else:
                _fields(value, 'bytes sha256', 'SOURCE_PIN_INVALID')
                _need(type(value['bytes']) is int and value['bytes'] >= 0 and _hex(value['sha256'], 64) and
                      all(reference[k] == value[k] for k in ('bytes', 'sha256')), 'SOURCE_PIN_CHANGED')
            _need(reference['bytes'] <= MAX_FILE_BYTES, 'FILE_LIMIT')
            previous = originals.setdefault(reference['path'], deepcopy(reference))
            _need(previous == reference, 'PIN_CONFLICT')
            bindings.append(dict(evidencePin=deepcopy(group['reportPin']), **deepcopy(row)))
    _need(len(bindings) <= MAX_INPUTS and sum(row['bytes'] for row in originals.values()) <= MAX_TOTAL_BYTES, 'INPUT_LIMIT')
    _need(used_builds == set(builds), 'BUILD_SET_INVALID')
    return reports, list(builds.values()), bindings, originals


def _check_checkouts(repository, builds):
    common = Path(_git_text(repository, ['rev-parse', '--path-format=absolute', '--git-common-dir'])).resolve(strict=True)
    for build in builds:
        root = _real(Path(build['originalWorktree']), directory=True)
        _need(root != repository, 'DEDICATED_CHECKOUT_REQUIRED')
        _need(Path(_git_text(root, ['rev-parse', '--show-toplevel'])) == root, 'CHECKOUT_ROOT_CHANGED')
        _need(Path(_git_text(root, ['rev-parse', '--path-format=absolute', '--git-common-dir'])).resolve(strict=True) == common,
              'CHECKOUT_REPOSITORY_CHANGED')
        _need(_git_text(root, ['rev-parse', 'HEAD']) == build['sourceCommit'], 'CHECKOUT_COMMIT_CHANGED')
        _need(_git(root, ['status', '--porcelain=v1', '--untracked-files=all', '--ignored']) == b'', 'CHECKOUT_NOT_CLEAN')


def _blobs(repository, builds, bindings):
    output = {}
    for build in builds:
        names = sorted({r['name'] for r in bindings if r['buildId'] == build['id']})
        requests = ''.join(build['sourceCommit'] + ':' + name + '\n' for name in names).encode('utf-8')
        raw = _git(repository, ['cat-file', '--batch'], requests)
        offset = 0
        for name in names:
            end = raw.find(b'\n', offset)
            _need(end >= offset, 'GIT_BINDING_CHANGED')
            header = raw[offset:end].split(b' ')
            _need(len(header) == 3 and header[1] == b'blob' and header[2].isdigit(), 'GIT_BINDING_CHANGED')
            identifier = header[0].decode('ascii')
            size = int(header[2]); offset = end + 1
            _need(_hex(identifier, 40) and size <= MAX_FILE_BYTES and len(raw) > offset + size and
                  raw[offset + size:offset + size + 1] == b'\n', 'GIT_BINDING_CHANGED')
            blob = raw[offset:offset + size]
            _need(hashlib.sha1(b'blob ' + str(size).encode('ascii') + b'\0' + blob).hexdigest() == identifier,
                  'GIT_BINDING_CHANGED')
            output[(build['id'], name)] = (identifier, blob)
            offset += size + 1
        _need(offset == len(raw), 'GIT_BINDING_CHANGED')
    return output


def _entries(bindings, contents, blobs):
    entries = []
    for row in bindings:
        raw = contents[row['originalPin']['sha256']]
        identifier = representation = None
        if row['purpose'] in ('COMMITTED_SOURCE', 'REPOSITORY_SOURCE'):
            identifier, blob = blobs[(row['buildId'], row['name'])]
            if raw == blob:
                representation = 'IDENTICAL'
            elif b'\r\n' in raw and raw.replace(b'\r\n', b'\n') == blob:
                representation = 'CRLF_TO_LF'
            else:
                raise ValueError('BUILD_CUSTODY_GIT_REPRESENTATION_CHANGED')
        entries.append(dict(row, member='objects/' + row['originalPin']['sha256'],
                            blobId=identifier, representation=representation))
    return entries


def _archive(raw, bindings):
    expected = {row['originalPin']['sha256']: row['originalPin']['bytes'] for row in bindings}
    contents = {}; total = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
            for row in archive:
                _need(row.isfile() and not row.pax_headers and re.fullmatch(r'objects/[0-9a-f]{64}', row.name) and
                      row.name[8:] not in contents and 0 <= row.size <= MAX_FILE_BYTES, 'ARCHIVE_MEMBER_INVALID')
                identifier = row.name[8:]
                _need(identifier in expected, 'ARCHIVE_SET_CHANGED')
                body = archive.extractfile(row).read(MAX_FILE_BYTES + 1)
                _need(len(body) == row.size == expected[identifier] and _sha(body) == identifier, 'ARCHIVE_CONTENT_CHANGED')
                total += len(body)
                _need(total <= MAX_TOTAL_BYTES and len(contents) < MAX_INPUTS, 'ARCHIVE_MEMBER_INVALID')
                contents[identifier] = body
            # tarfile stops at the first zero block; hidden records after it are
            # still part of the pinned archive and must not escape inspection.
            _need(len(raw) % 512 == 0 and len(raw) - archive.offset >= 1024 and
                  not any(raw[archive.offset:]), 'ARCHIVE_MEMBER_INVALID')
    except (tarfile.TarError, OSError, EOFError) as error:
        raise ValueError('BUILD_CUSTODY_ARCHIVE_MEMBER_INVALID') from error
    _need(set(contents) == set(expected), 'ARCHIVE_SET_CHANGED')
    return contents


def _destination(private, destination):
    destination = _path(str(destination))
    _need(destination.parent == private and re.fullmatch(r'historical-build-custody-[a-z0-9][a-z0-9-]{0,63}', destination.name),
          'DESTINATION_SCOPE_INVALID')
    return destination


def _write_exclusive(path, raw):
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
        with os.fdopen(os.open(path, flags, 0o600), 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    except OSError as error:
        raise ValueError('BUILD_CUSTODY_EXCLUSIVE_WRITE_FAILED') from error


def seal_build_custody(task, private, *, inputs, destination, repository):
    """Seal explicit original report-bound inputs; never clean up source checkouts."""
    task = _real(Path(task), directory=True); private = _real(Path(private), directory=True)
    repository = _real(Path(repository), directory=True)
    destination = _destination(private, destination)
    _need(not os.path.lexists(destination), 'DESTINATION_EXISTS')
    inputs = deepcopy(inputs)
    reports, builds, bindings, originals = _plan(task, inputs, repository)
    _check_checkouts(repository, builds)
    contents = {}
    for reference in originals.values():
        contents[reference['sha256']] = _read_pin(reference, MAX_FILE_BYTES)
    entries = _entries(bindings, contents, _blobs(repository, builds, bindings))
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:', format=tarfile.USTAR_FORMAT) as archive:
        for identifier, raw in sorted(contents.items()):
            info = tarfile.TarInfo('objects/' + identifier)
            info.size = len(raw); info.mode = 0o600
            archive.addfile(info, io.BytesIO(raw))
    raw_archive = stream.getvalue()
    _need(len(raw_archive) <= MAX_ARCHIVE_BYTES, 'ARCHIVE_LIMIT')
    reports.finish()
    for reference in originals.values(): _read_pin(reference, MAX_FILE_BYTES)
    _check_checkouts(repository, builds)
    try:
        destination.mkdir(mode=0o700)
    except OSError as error:
        raise ValueError('BUILD_CUSTODY_DESTINATION_EXISTS') from error
    archive_path = destination / 'inputs.tar'
    _write_exclusive(archive_path, raw_archive)
    archive_pin = _file_pin(archive_path, MAX_ARCHIVE_BYTES)
    manifest = dict(schemaVersion=SCHEMA, taskId=task.name, state='SEALED', inputs=inputs,
                    builds=builds, entries=entries, archivePin=archive_pin,
                    installationPerformed=False, testsExecuted=False, serverWrites=False)
    encoded = _canonical(manifest)
    _need(len(encoded) <= MAX_METADATA_BYTES, 'FILE_LIMIT')
    path = destination / 'manifest.json'
    _write_exclusive(path, encoded)
    reference = _file_pin(path)
    # A failed final guard leaves originals and partial output intact, never a returned success pin.
    reports.finish()
    for original in originals.values(): _read_pin(original, MAX_FILE_BYTES)
    _read_pin(archive_pin, MAX_ARCHIVE_BYTES)
    _check_checkouts(repository, builds)
    _read_pin(reference)
    return reference


class HistoricalBuildCustody:
    """Only the loader constructs an accepted explicit original-input reader."""
    def __init__(self, *, reference, archive_pin, reports, entries, contents, token):
        _need(token is _READER_TOKEN, 'READER_CONSTRUCTION_INVALID')
        self._reference = deepcopy(reference)
        self._archive_pin = deepcopy(archive_pin)
        self._reports = reports
        self._contents = contents
        self._registered = {}
        self._originals = set()
        for row in entries:
            key = (_canonical(row['originalPin']), _canonical(row['evidencePin']), row['purpose'])
            self._registered[key] = row['originalPin']['sha256']
            self._originals.add(key[0])

    def read_original(self, reference, *, evidence_pin, purpose):
        key = (_canonical(reference), _canonical(evidence_pin), purpose)
        _need(key in self._registered, 'ORIGINAL_NOT_REGISTERED')
        return self._contents[self._registered[key]]

    def verify_original_inputs(self, references):
        _need(type(references) is list, 'ORIGINAL_NOT_REGISTERED')
        for reference in references:
            _need(_canonical(reference) in self._originals, 'ORIGINAL_NOT_REGISTERED')

    def finish(self):
        _read_pin(self._reference)
        _read_pin(self._archive_pin, MAX_ARCHIVE_BYTES)
        return [deepcopy(self._reference), deepcopy(self._archive_pin), *self._reports.finish()]


_READER_TOKEN = object()


def load_build_custody(task, private, custody_pin, *, repository):
    """Read a caller-selected immutable custody; original checkout paths are not read."""
    task = _real(Path(task), directory=True); private = _real(Path(private), directory=True)
    repository = _real(Path(repository), directory=True)
    _pin(custody_pin)
    path = Path(custody_pin['path'])
    _destination(private, path.parent)
    _need(path.name == 'manifest.json', 'MANIFEST_SCOPE_INVALID')
    manifest = _json(_read_pin(custody_pin))
    _fields(manifest, 'schemaVersion taskId state inputs builds entries archivePin installationPerformed testsExecuted serverWrites')
    _need(manifest['schemaVersion'] == SCHEMA and manifest['taskId'] == task.name and manifest['state'] == 'SEALED' and
          all(manifest[key] is False for key in ('installationPerformed', 'testsExecuted', 'serverWrites')), 'MANIFEST_INVALID')
    reports, builds, bindings, _ = _plan(task, manifest['inputs'], repository)
    _need(manifest['builds'] == builds, 'BUILD_CHANGED')
    reference = _pin(manifest['archivePin'])
    _need(Path(reference['path']) == path.parent / 'inputs.tar', 'ARCHIVE_SCOPE_INVALID')
    contents = _archive(_read_pin(reference, MAX_ARCHIVE_BYTES), bindings)
    expected = _entries(bindings, contents, _blobs(repository, builds, bindings))
    actual = manifest['entries']
    _need(type(actual) is list and len(actual) == len(expected), 'MANIFEST_ENTRIES_CHANGED')
    for row, original in zip(actual, expected):
        _need(type(row) is dict and set(row) == set(original), 'MANIFEST_ENTRIES_CHANGED')
        _need(all(row[k] == original[k] for k in original if k not in ('blobId', 'representation')), 'MANIFEST_ENTRIES_CHANGED')
        _need(row['blobId'] == original['blobId'] and row['representation'] == original['representation'], 'GIT_BINDING_CHANGED')
    reader = HistoricalBuildCustody(reference=custody_pin, archive_pin=reference, reports=reports,
                                    entries=expected, contents=contents, token=_READER_TOKEN)
    reader.finish()
    return reader
