"""readGuardContract/v1: one repository byte lock and durable reader exclusion."""
import errno
import os
from pathlib import Path
import stat
import threading

from recovery_engine import (READ_GUARD, RecoveryError, absolute, canonical, check_pin, load,
                             parse, pin, require, utc, write)


_owners = set()
_owners_mutex = threading.Lock()
MARKER_ENV = 'RECOVERY_REPOSITORY_READ_GUARD_PIN'
LOCK_ENV = 'RECOVERY_REPOSITORY_LOCK_FD'
FIELDS = {'schemaVersion', 'repositoryId', 'operationId', 'requestId', 'requestPin',
          'candidatePin', 'state', 'createdAt'}


def repository_root(candidate, policy):
    require(type(candidate) is dict and set(candidate) == {'path', 'bytes', 'sha256'} and
            candidate in policy['repositoryPointPins'], 'READ_GUARD_CANDIDATE_NOT_APPROVED')
    path = absolute(candidate['path'])
    require(path.name == 'point.json' and path.parent.name == '.repository' and
            path.parents[2].name == 'archives', 'READ_GUARD_POINT_PATH_INVALID')
    require(type(policy.get('repositoryId')) is str and policy['repositoryId'], 'READ_GUARD_REPOSITORY_ID_REQUIRED')
    return path.parents[3]


def _inode(path, fd):
    actual, expected = os.fstat(fd), absolute(str(path)).stat()
    require(stat.S_ISREG(actual.st_mode) and actual.st_nlink == 1 and expected.st_nlink == 1 and
            (actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino), 'READ_GUARD_LOCK_REPLACED')
    return actual.st_dev, actual.st_ino


def _lock(fd, acquire):
    if os.name == 'posix':
        import fcntl
        fcntl.lockf(fd, (fcntl.LOCK_EX | fcntl.LOCK_NB) if acquire else fcntl.LOCK_UN, 1, 0, os.SEEK_SET)
    elif os.name == 'nt':
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK if acquire else msvcrt.LK_UNLCK, 1)
    else:
        raise RecoveryError('NATIVE_LOCK_PLATFORM_UNSUPPORTED')


def _exists(path):
    # Broken symlinks, malformed JSON and unreadable records are blockers too.
    try: path.lstat(); return True
    except FileNotFoundError: return False


def _sync_control_directory(path):
    if os.name == 'posix':
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)


class RepositoryReadGuard:
    def __init__(self, request, request_pin, policy, budget):
        self.root = repository_root(request['selectedPointPin'], policy)
        self.control = absolute(str(self.root/'.repository-control'))
        self.lock_path = self.control/'write.lock'
        self.path = self.control/'recovery-read-guard.json'
        self.budget, self.policy = budget, policy
        self.value = dict(schemaVersion='RepositoryRecoveryReadGuard/v1', repositoryId=policy['repositoryId'],
            operationId=request['operationId'], requestId=request['requestId'], requestPin=request_pin,
            candidatePin=request['selectedPointPin'], state='ACTIVE', createdAt=utc())
        self.stream = self.ref = self.token = None
        self.owner = (os.getpid(), threading.get_ident())
        self.completed = self.admitted = False

    def __enter__(self):
        self.budget.remaining()
        require(self.root.is_dir(), 'READ_GUARD_REPOSITORY_ROOT_MISSING')
        self.control.mkdir(mode=0o700, exist_ok=True)
        absolute(str(self.control))
        self.control_inode = (self.control.stat().st_dev, self.control.stat().st_ino)
        with _owners_mutex:
            require(str(self.lock_path) not in _owners, 'REPOSITORY_ALREADY_EXECUTING')
            _owners.add(str(self.lock_path))
        try:
            self.stream = self.lock_path.open('a+b')
            _inode(self.lock_path, self.fd)
            try: _lock(self.fd, True)
            except OSError as error:
                if error.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise RecoveryError('REPOSITORY_ALREADY_EXECUTING') from error
                raise
            self.locked = True
            require(not _exists(self.path), 'REPOSITORY_RECOVERY_RECONCILIATION_REQUIRED')
            require(not _exists(self.control/'write-unknown.json'), 'REPOSITORY_WRITE_RECONCILIATION_REQUIRED')
            self.budget.remaining()
            self.admitted = True
            self.ref = write(self.path, self.value)
            self.token = READ_GUARD.set(self)
            self.check()
            return self
        except Exception as error:
            if self.admitted: error.unknown = True  # Atomic replace may have succeeded before Pin/fsync failed.
            self._release()
            raise

    @property
    def fd(self):
        require(self.stream is not None, 'READ_GUARD_LOCK_NOT_HELD')
        return self.stream.fileno()

    def check(self):
        require(self.owner == (os.getpid(), threading.get_ident()), 'READ_GUARD_OWNER_CHANGED')
        _inode(self.lock_path, self.fd)
        require((self.control.stat().st_dev, self.control.stat().st_ino) == self.control_inode,
                'READ_GUARD_CONTROL_REPLACED')
        require(self.ref is not None and pin(self.path) == self.ref and load(self.path) == self.value and
                self.value['state'] == 'ACTIVE', 'READ_GUARD_MARKER_CHANGED')
        require(not _exists(self.control/'write-unknown.json'), 'REPOSITORY_WRITE_RECONCILIATION_REQUIRED')

    def check_read(self, path):
        self.check()
        # Authority/tool Pins can live outside the NAS; any archive Pin must
        # identify this exact repository, never an alias or sibling repository.
        if 'archives' in path.parts:
            require(self.root/'archives' in path.parents, 'READ_GUARD_CROSS_REPOSITORY_PIN')

    def point(self, ref):
        require(repository_root(ref, self.policy) == self.root, 'READ_GUARD_CROSS_REPOSITORY_POINT')
        self.check()

    def archive_pins(self, point_ref, refs):
        self.point(point_ref)
        archive = absolute(point_ref['path']).parents[1]
        for ref in refs:
            require(archive in absolute(ref['path']).parents, 'READ_GUARD_ARCHIVE_BINDING_INVALID')

    def original_pins(self, refs):
        self.check()
        for ref in refs:
            # Called only after trusted signed completions agree on this exact
            # originalProcessPin. W03 keeps that original in its separate
            # approved evidenceRoot; an archive copy is not a replacement Pin.
            # check_pin keeps byte identity and the active archive/root guard.
            check_pin(ref)

    def child_options(self, environment, fds=()):
        self.check(); require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
        return dict(pass_fds=tuple(dict.fromkeys((*fds, self.fd))),
                    env=dict(environment, **{MARKER_ENV: canonical(self.ref).decode('utf-8'), LOCK_ENV: str(self.fd)}))

    def finish(self, *, terminal_known):
        self.check()
        if terminal_known:
            # Identical owned marker only; called after durable final evidence.
            self.path.unlink()
            try:
                _sync_control_directory(self.control)
            except Exception as error:
                # The removal receipt is uncertain. Restore exclusion under
                # the still-held lock; never report a successful release.
                require(not _exists(self.path), 'READ_GUARD_MARKER_CHANGED')
                self.ref = write(self.path, dict(self.value, state='TERMINAL_UNKNOWN'))
                self.value['state'] = 'TERMINAL_UNKNOWN'; self.completed = True
                raise RecoveryError('READ_GUARD_REMOVAL_DURABILITY_UNKNOWN', unknown=True) from error
        else:
            self.ref = write(self.path, dict(self.value, state='TERMINAL_UNKNOWN'))
            self.value['state'] = 'TERMINAL_UNKNOWN'
        self.completed = True

    def _release(self):
        if self.token is not None: READ_GUARD.reset(self.token); self.token = None
        try:
            if self.stream is not None:
                try:
                    if getattr(self, 'locked', False): _lock(self.fd, False)
                finally: self.stream.close(); self.stream = None
        finally:
            with _owners_mutex: _owners.discard(str(self.lock_path))

    def __exit__(self, kind, error, traceback):
        try:
            if not self.completed:
                if error is not None: error.unknown = True
                try: self.finish(terminal_known=False)
                except Exception as recording:
                    failure = RecoveryError('READ_GUARD_RETAINED_RECONCILIATION_REQUIRED', unknown=True,
                        exit_code=getattr(error, 'exit_code', None))
                    failure.original_pins = getattr(error, 'original_pins', [])
                    raise failure from recording
        finally: self._release()


class InheritedReadGuard(RepositoryReadGuard):
    """A worker validates the supervisor marker and byte lock; it never removes either."""
    def __init__(self, request, request_pin, policy, budget):
        super().__init__(request, request_pin, policy, budget)
        text = os.environ.get(LOCK_ENV); marker = os.environ.get(MARKER_ENV)
        require(os.name == 'posix' and text and text.isdecimal() and marker, 'SUPERVISOR_READ_GUARD_REQUIRED')
        self.inherited_fd = int(text); self.ref = parse(marker.encode('utf-8'))
        require(self.ref['path'] == str(self.path), 'SUPERVISOR_READ_GUARD_PATH_INVALID')
        value = load(self.path)
        require(set(value) == FIELDS and all(value[k] == self.value[k] for k in FIELDS - {'createdAt'}) and
                type(value['createdAt']) is str and value['createdAt'], 'SUPERVISOR_READ_GUARD_BINDING_INVALID')
        self.value = value
        self.control_inode = (self.control.stat().st_dev, self.control.stat().st_ino)
        self.check()
        READ_GUARD.set(self)

    @property
    def fd(self): return self.inherited_fd

    def check(self):
        super().check()
        # POSIX record locks belong to the supervisor process, not the child's
        # inherited descriptor. An independent child lock must conflict.
        with self.lock_path.open('a+b') as probe:
            try: _lock(probe.fileno(), True)
            except OSError as error:
                if error.errno in (errno.EACCES, errno.EAGAIN): return
                raise
            _lock(probe.fileno(), False)
        raise RecoveryError('SUPERVISOR_REPOSITORY_LOCK_NOT_HELD', unknown=True)


def inherit_read_guard(request, request_pin, policy, budget):
    # Workers have no public opt-out; trust/authority validation precedes this.
    return InheritedReadGuard(request, request_pin, policy, budget)
