"""Custody of typed MAIN SQL from its original pin through bounded deletion.

This does not change SQL/FAST/SAFE semantics or replay a command. Its private
receipts prove only that the exact file observed by a completed SQL invocation
remained unchanged until this operation deleted it. Archive and business
verification remain the caller's existing responsibilities.
"""
from copy import deepcopy
import os
from pathlib import Path
import re
import stat

from recovery_archive_guard import ArchivePathGuard
from recovery_backup_epoch import _path
from recovery_engine import canonical, pin, require, utc
from recovery_program_activation import _exclusive
from recovery_program_generation import document


INTENT_NAME = 'sql-staging-cleanup-intent.json'
RESULT_NAME = 'sql-staging-cleanup.json'
IDENTITY_FIELDS = {'device', 'inode', 'mode', 'uid', 'links', 'bytes', 'mtimeNs', 'ctimeNs'}
MAX_ENTRIES = 10000


def _need(value, suffix):
    require(value, 'PROGRAM_SQL_STAGING_' + suffix)


def file_identity(info):
    return dict(device=info.st_dev, inode=info.st_ino, mode=info.st_mode, uid=info.st_uid,
        links=info.st_nlink, bytes=info.st_size, mtimeNs=info.st_mtime_ns, ctimeNs=info.st_ctime_ns)


def cleanup_relative(root, path):
    """Only runtime's exact expanded SQL names are eligible for deletion."""
    path = _path(str(path)); root = _path(str(root))
    _need(path.is_relative_to(root), 'CLEANUP_SCOPE_INVALID')
    parts = path.relative_to(root).parts
    _need(len(parts) == 2 and re.fullmatch(r'database-[0-9]{3}', parts[0]) and
        (parts[1] in ('full.sql', 'incremental.sql', 'expanded.sql') or
         re.fullmatch(r'binlog-[0-9]{3}\.sql', parts[1])), 'CLEANUP_SCOPE_INVALID')
    return parts


def _directory(path):
    path = _path(str(path)); value = path.stat()
    _need(stat.S_ISDIR(value.st_mode) and stat.S_IMODE(value.st_mode) == 0o700 and
        value.st_uid == os.geteuid(), 'DIRECTORY_INVALID')
    return value.st_dev, value.st_ino, value.st_mode, value.st_uid


def _file(path):
    value = _path(str(path)).stat()
    _need(stat.S_ISREG(value.st_mode) and value.st_nlink == 1 and
        stat.S_IMODE(value.st_mode) == 0o600 and value.st_uid == os.geteuid(), 'FILE_INVALID')
    return file_identity(value)


class _SqlStaging:
    def __init__(self, native):
        view = native.native_context
        view.guard_native(native)
        self.context, self.native = view._context, native
        self.root = self.context._root
        self.root_identity = _directory(self.root)
        self.binding = deepcopy(self.context._binding)
        self.generation = deepcopy(self.context.generation_pin)
        self.operation = self.context._request['operationId']
        self.entries = {}
        self.closed = False
        self.result = None

    def check(self):
        """Local observation only: never call native/view/context guards."""
        _need(not self.closed, 'CLOSED')
        _need(_directory(self.root) == self.root_identity, 'ROOT_CHANGED')
        for path, entry in self.entries.items():
            if entry['state'] == 'DELETED':
                _need(not os.path.lexists(path), 'DELETED_SQL_REAPPEARED')
                continue
            _need(entry['state'] == 'HELD', 'CLEANUP_INCOMPLETE')
            entry['lease'].check()
            _need(_file(path) == entry['fileIdentity'] and
                _directory(path.parent) == entry['parentIdentity'], 'FILE_CHANGED')

    def capture(self, path):
        self.check()
        path = _path(str(path))
        _need(path not in self.entries and len(self.entries) < MAX_ENTRIES and
            (self.root in path.parents or self.context._claim in path.parents), 'SQL_SCOPE_INVALID')
        before, parent = _file(path), _directory(path.parent)
        lease = ArchivePathGuard.capture([path])
        try:
            # Reuse the importer's existing full pin read; the lease starts
            # before that read and stays alive through stream and cleanup.
            reference = pin(path, budget=self.context.budget)
            lease.check()
            _need(_file(path) == before and _directory(path.parent) == parent and
                reference['bytes'] == before['bytes'], 'FILE_CHANGED')
            self.entries[path] = dict(sqlPin=reference, importerPin=None, terminal=None,
                fileIdentity=before, parentIdentity=parent, lease=lease, state='HELD')
            self.check()
            return deepcopy(reference)
        except BaseException:
            lease.close()
            raise

    def terminal(self, reference):
        """Retain a real terminal even if the execution guard has expired."""
        value = document(reference)
        path = _path(value['sqlPin']['path'])
        _need(path in self.entries, 'SQL_NOT_OWNED')
        entry = self.entries[path]
        _need(entry['importerPin'] is None and value.get('schemaVersion') == 'RecoverySqlImporter/v2' and
            value.get('operationId') == self.operation and value['sqlPin'] == entry['sqlPin'] and
            any(row['terminalPin'] == reference and row.get('terminalObservation') == value
                for row in self.context._invocations), 'IMPORTER_BINDING_INVALID')
        entry['importerPin'], entry['terminal'] = deepcopy(reference), deepcopy(value)

    def cleanup(self, native, root):
        _need(native is self.native and _path(str(root)) == self.root and
            native.native_context._context is self.context, 'OWNER_CHANGED')
        native.guard(); self.check()
        _need(self.result is None and self.generation is not None and
            self.context.generation_pin == self.generation and native.native_context.phase == 'RESTORE',
            'CLEANUP_PHASE_INVALID')
        if not self.entries: return None
        _need(not os.path.lexists(self.root/INTENT_NAME) and not os.path.lexists(self.root/RESULT_NAME),
            'CLEANUP_ALREADY_CLAIMED')
        rows = []
        for path, entry in self.entries.items():
            native.guard(); cleanup_relative(self.root, path)
            terminal = entry['terminal']
            _need(terminal is not None and terminal['state'] == 'SUCCEEDED' and
                type(terminal['actualExitCode']) is int and terminal['actualExitCode'] == 0 and
                terminal['action'] in ('DATABASE_FULL', 'DATABASE_INCREMENTAL') and
                document(entry['importerPin']) == terminal, 'IMPORTER_NOT_SUCCEEDED')
            rows.append({key: deepcopy(entry[key]) for key in ('sqlPin', 'importerPin', 'fileIdentity')})
        intent = dict(schemaVersion='MainSqlStagingCleanupIntent/v1', state='PLANNED',
            operationId=self.operation, bindingPin=self.binding, generationPin=self.generation,
            operationRoot=str(self.root), entries=rows, startedAt=utc())
        _need(len(canonical(intent)) <= 4*1024*1024, 'EVIDENCE_LIMIT')
        descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            _need((os.fstat(descriptor).st_dev, os.fstat(descriptor).st_ino,
                os.fstat(descriptor).st_mode, os.fstat(descriptor).st_uid) == self.root_identity,
                'ROOT_CHANGED')
            native.guard(); intent_pin = _exclusive(self.root/INTENT_NAME, intent, native.guard)
            for path, entry in self.entries.items():
                native.guard(); self.check()
                directory, name = cleanup_relative(self.root, path)
                parent = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                try:
                    info = os.fstat(parent)
                    _need((info.st_dev, info.st_ino, info.st_mode, info.st_uid) == entry['parentIdentity'],
                        'DIRECTORY_CHANGED')
                    held = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
                    try:
                        entry['lease'].check()
                        _need(file_identity(os.fstat(held)) == entry['fileIdentity'] ==
                            file_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)), 'FILE_CHANGED')
                        # No guard can observe our planned unlink as outside
                        # interference. The held parent/file identities remain
                        # exact while this one file's watcher is closed.
                        entry['lease'].close(); entry['state'] = 'DELETING'
                        _need(file_identity(os.fstat(held)) == entry['fileIdentity'] ==
                            file_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)), 'FILE_CHANGED')
                        os.unlink(name, dir_fd=parent); os.fsync(parent)
                        _need(not os.path.lexists(path), 'DELETE_UNCONFIRMED')
                        entry['state'] = 'DELETED'
                    finally: os.close(held)
                finally: os.close(parent)
            native.guard(); self.check()
            result = dict(schemaVersion='MainSqlStagingCleanup/v1', state='SUCCEEDED',
                operationId=self.operation, intentPin=intent_pin,
                deletedSqlPins=[deepcopy(entry['sqlPin']) for entry in self.entries.values()], finishedAt=utc())
            _need(len(canonical(result)) <= 4*1024*1024, 'EVIDENCE_LIMIT')
            self.result = _exclusive(self.root/RESULT_NAME, result, native.guard)
            os.fsync(descriptor)
            native.guard(); self.check()
            return deepcopy(self.result)
        finally: os.close(descriptor)

    def close(self):
        if self.closed: return
        self.closed = True
        failure = None
        for entry in self.entries.values():
            try: entry['lease'].close()
            except OSError as error:
                if failure is None: failure = error
        if failure is not None: raise failure


def sql_staging(native):
    """Create only for the already admitted typed MAIN view."""
    from recovery_program_native import _NativeView
    view = getattr(native, 'native_context', None)
    _need(type(view) is _NativeView, 'CONTEXT_REQUIRED')
    manager = getattr(native, 'program_sql_staging', None)
    if manager is None:
        manager = _SqlStaging(native)
        native.program_sql_staging = manager
        view._context._sql_staging_managers.append(manager)
    _need(type(manager) is _SqlStaging and manager.native is native and manager.context is view._context,
        'OWNER_CHANGED')
    return manager


def cleanup_sql_staging(native, root):
    manager = getattr(native, 'program_sql_staging', None)
    return None if manager is None else manager.cleanup(native, root)


def close_sql_staging(native):
    manager = getattr(native, 'program_sql_staging', None)
    if manager is not None: manager.close()
