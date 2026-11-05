"""Protect one registered archive mount without changing its shared superblock."""
from copy import deepcopy
from pathlib import Path
import re

from recovery_engine import absolute, check_pin, digest, load, require, utc, write
from recovery_replacement_storage import MOUNT_FIELDS, LOCAL_FILESYSTEMS, _path, parse_mountinfo


def validate(configuration):
    require(type(configuration) is dict and set(configuration) ==
            {'schemaVersion', 'mountIdentity', 'mountProgramPin'} and
            configuration['schemaVersion'] == 'RegisteredArchiveViewProtection/v1', 'ARCHIVE_VIEW_CONFIGURATION_INVALID')
    mount = configuration['mountIdentity']
    require(type(mount) is dict and set(mount) == MOUNT_FIELDS and
            type(mount['mountId']) is int and mount['mountId'] > 0 and
            type(mount['parentId']) is int and mount['parentId'] >= 0 and
            type(mount['device']) is str and re.fullmatch('[0-9]+:[0-9]+', mount['device']) and
            type(mount['source']) is str and mount['source'] and
            mount['filesystem'] in LOCAL_FILESYSTEMS | {'cifs', 'nfs', 'nfs4', 'tmpfs'} and
            all(type(mount[k]) is list and mount[k] and all(type(v) is str and v for v in mount[k])
                for k in ('options', 'superOptions')), 'ARCHIVE_VIEW_CONFIGURATION_INVALID')
    _path(mount['root'], root=True); _path(mount['mountPoint'])
    path = absolute(mount['mountPoint'])
    require(str(path) != '/' and str(path) != '/mnt/nas' and not path.is_relative_to('/mnt/nas') and
            'rw' in mount['options'] and 'ro' not in mount['options'], 'ARCHIVE_VIEW_CONFIGURATION_INVALID')
    program = configuration['mountProgramPin']
    require(type(program) is dict and set(program) == {'path', 'bytes', 'sha256'} and
            absolute(program['path']).name == 'mount', 'ARCHIVE_VIEW_PROGRAM_INVALID')
    return configuration


class ArchiveViewProtection:
    def __init__(self, configuration, operation_id, journal, execute):
        self.configuration = validate(configuration)
        self.operation_id, self.journal, self.execute = operation_id, absolute(str(journal)), execute
        self.original = self.configuration['mountIdentity']

    def _observed(self):
        point = self.original['mountPoint']
        require(absolute(point).resolve(strict=True) == absolute(point), 'ARCHIVE_VIEW_CHANGED')
        rows = [m for m in parse_mountinfo(Path('/proc/self/mountinfo').read_text(encoding='utf-8'))
                if m['mountPoint'] == point]
        require(len(rows) == 1, 'ARCHIVE_VIEW_CHANGED')
        return rows[0]

    def _readonly(self):
        result = deepcopy(self.original)
        result['options'] = ['ro' if v == 'rw' else v for v in result['options']]
        return result

    def _remount(self, mode):
        program = self.configuration['mountProgramPin']; check_pin(program)
        self.execute([program['path'], '-i', '-n', '-o', 'remount,bind,'+mode, '--',
                      self.original['mountPoint']], mutation=True)

    def preflight(self):
        check_pin(self.configuration['mountProgramPin'])
        require(not self.journal.exists(), 'ARCHIVE_VIEW_ALREADY_CLAIMED')
        require(self._observed() == self.original, 'ARCHIVE_VIEW_CHANGED')

    def install(self):
        self.preflight(); self.journal.mkdir(mode=0o700)
        write(self.journal/'intent.json', dict(schemaVersion='ArchiveViewProtectionIntent/v1',
            operationId=self.operation_id, configurationDigest=digest(self.configuration), startedAt=utc()))
        self._remount('ro')
        require(self._observed() == self._readonly(), 'ARCHIVE_VIEW_CHANGED')
        write(self.journal/'active.json', dict(schemaVersion='ArchiveViewProtectionActive/v1',
            operationId=self.operation_id, configurationDigest=digest(self.configuration),
            observedMountDigest=digest(self._observed())))
        self.verify()

    def verify(self):
        active = load(self.journal/'active.json')
        require(active['schemaVersion'] == 'ArchiveViewProtectionActive/v1' and
                active['operationId'] == self.operation_id and
                active['configurationDigest'] == digest(self.configuration) and
                not (self.journal/'released.json').exists(), 'ARCHIVE_VIEW_IDENTITY_CHANGED')
        require(self._observed() == self._readonly() and
                digest(self._observed()) == active['observedMountDigest'], 'ARCHIVE_VIEW_CHANGED')

    def release(self):
        self.verify(); self._remount('rw')
        require(self._observed() == self.original, 'ARCHIVE_VIEW_CHANGED')
        return write(self.journal/'released.json', dict(schemaVersion='ArchiveViewProtectionRelease/v1',
            operationId=self.operation_id, originalMountRestored=True, finishedAt=utc()))
