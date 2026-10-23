"""Pinned whole-chain retention plans and explicitly authorized deletion."""
from datetime import datetime, timezone
import os
import hashlib
from pathlib import Path
import shutil
import stat
import threading

from repository_records import (RepositoryError, canonical, document, exact, pin_file, read_pin, require,
                                safe_path, utc, write_new)


class RepositoryLock:
    """Shared byte lock; recovery read guards also exclude repository mutation."""
    local_guard = threading.Lock()
    local_owners = set()
    def __init__(self, config, request):
        # Every installer targeting this repository locks the same server file.
        # Local evidence roots cannot provide cross-installer exclusion.
        control = config.root / '.repository-control'
        control.mkdir(exist_ok=True)
        safe_path(control)
        self.control = control
        self.path = control / 'write.lock'
        self.unknown_path = control / 'write-unknown.json'
        self.recovery_guard_path = control / 'recovery-read-guard.json'
        self.local_key = (control.stat().st_dev, control.stat().st_ino)
        self.owner_identity = (os.getpid(), threading.get_ident())
        with self.local_guard:
            if self.local_key in self.local_owners:
                raise BlockingIOError('REPOSITORY_OWNER_ALREADY_HELD')
            self.local_owners.add(self.local_key)
        self.stream = None
        try:
            if self.path.exists():
                safe_path(self.path)
            self.stream = self.path.open('a+b')
            if self.path.stat().st_size == 0:
                self.stream.write(b'\0')
                self.stream.flush()
                os.fsync(self.stream.fileno())
            self.stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.lockf(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB, 1, 0)
        except BaseException:
            if self.stream is not None:
                self.stream.close()
            with self.local_guard:
                self.local_owners.remove(self.local_key)
            raise
        held = os.fstat(self.stream.fileno())
        self.identity = (held.st_dev, held.st_ino)
        self.config, self.request = config, request
        self.request_raw = canonical(request)
        try:
            self._check_owned()
            self._refuse_recovery_read_guard()
            try:
                self.unknown_path.lstat()
            except FileNotFoundError:
                pass
            else:
                raise RepositoryError('REPOSITORY_PREVIOUS_WRITE_TERMINAL_UNKNOWN', unknown=True)
            self._check_owned()
        except BaseException:
            self.close()
            raise

    def _check_owned(self):
        require(self.owner_identity == (os.getpid(), threading.get_ident()), 'REPOSITORY_OWNER_LOST')
        safe_path(self.control)
        control = self.control.stat()
        require((control.st_dev, control.st_ino) == self.local_key, 'REPOSITORY_OWNER_LOST')
        safe_path(self.path)
        value = self.path.stat()
        held = os.fstat(self.stream.fileno())
        require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1 and
                (value.st_dev, value.st_ino) == self.identity and
                (held.st_dev, held.st_ino) == self.identity, 'REPOSITORY_OWNER_LOST')
        require(canonical(self.request) == self.request_raw, 'REPOSITORY_OWNER_LOST')

    def _refuse_recovery_read_guard(self):
        # readGuardContract/v1: even a crashed ACTIVE reader is unresolved.
        # Presence alone blocks; malformed bytes, links and unknown states can
        # never authorize deletion. Only the owning recovery may remove it.
        try:
            self.recovery_guard_path.lstat()
        except FileNotFoundError:
            return
        except OSError as error:
            raise RepositoryError('REPOSITORY_RECOVERY_READ_GUARD_UNREADABLE', unknown=True) from error
        raise RepositoryError('REPOSITORY_RECOVERY_READ_GUARD_PRESENT', unknown=True)

    def check(self):
        self.config.current()
        self._check_owned()
        self._refuse_recovery_read_guard()
        self._check_owned()

    def close(self):
        try:
            self._check_owned()
            self.stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.lockf(self.stream.fileno(), fcntl.LOCK_UN, 1, 0)
        finally:
            self.stream.close()
            with self.local_guard:
                self.local_owners.remove(self.local_key)
    def __enter__(self):
        return self
    def __exit__(self, kind, value, trace):
        try:
            if isinstance(value, RepositoryError) and value.unknown:
                write_new(self.unknown_path, dict(schemaVersion='RepositoryUnknownWrite/v1',
                    repositoryId=self.config.value['repositoryId'], request=self.request,
                    state='TERMINAL_UNKNOWN', failureCode=value.code, at=utc()))
        finally:
            self.close()


def inventory(catalog):
    points = []
    for point_pin, point in catalog.list():
        require(point_pin is not None and point['integrityState'] == 'COMPLETE' and point['rehearsalEligible'], 'REPOSITORY_RETENTION_UNKNOWN_ARCHIVE')
        chain = catalog.chain(point_pin)
        manifest = chain[-1][2]
        points.append({'pointPin': point_pin, 'createdAt': manifest['createdAt'], 'pointType': point['pointType'], 'chainPins': [row[0] for row in chain], 'payloadBytes': sum(pin['bytes'] for pin in point['payloadRefs'])})
    points.sort(key=lambda row: row['createdAt'], reverse=True)
    return points


def plan_retention(catalog, request):
    config = catalog.config
    points = inventory(catalog)
    require(points, 'REPOSITORY_RETENTION_EMPTY')
    policy = config.policy
    now = datetime.now(timezone.utc)
    protected = set()
    by_path = {row['pointPin']['path']: row for row in points}
    def protect(row):
        for pin in row['chainPins']:
            protected.add(pin['path'])
    for row in points[:policy['retainNewestPoints']]:
        protect(row)
    full = [row for row in points if row['pointType'] == 'FULL']
    require(len(full) >= policy['minValidFullPoints'], 'REPOSITORY_RETENTION_MINIMUM_FULL_UNSATISFIED')
    for row in full[:policy['minValidFullPoints']]:
        protect(row)
    from repository_records import timestamp
    for row in points:
        if (now - timestamp(row['createdAt'])).total_seconds() < policy['retentionSeconds']:
            protect(row)
    for pin in policy['legalHoldPointPins']:
        require(pin['path'] in by_path and by_path[pin['path']]['pointPin'] == pin, 'REPOSITORY_LEGAL_HOLD_UNRESOLVED')
        protect(by_path[pin['path']])
    deletion = [row for row in points if row['pointPin']['path'] not in protected]
    # Delete descendants before ancestors. The plan preserves every retained dependency.
    deletion.sort(key=lambda row: len(row['chainPins']), reverse=True)
    planned = {'schemaVersion': 'RepositoryRetentionPlan/v1', 'repositoryId': config.value['repositoryId'], 'operationId': request['operationId'], 'policyPin': request['policyPin'], 'inventory': points, 'keepPointPins': [row['pointPin'] for row in points if row['pointPin']['path'] in protected], 'deletePointPins': [row['pointPin'] for row in deletion], 'deleteBytes': sum(row['payloadBytes'] for row in deletion), 'requiresExplicitAuthorization': True}
    return planned


def execute_retention(catalog, request, plan_pin, evidence_dir):
    config = catalog.config
    planned = document(read_pin(plan_pin))
    exact(planned, 'schemaVersion repositoryId operationId policyPin inventory keepPointPins deletePointPins deleteBytes requiresExplicitAuthorization', 'RepositoryRetentionPlan/v1')
    require(planned['repositoryId'] == config.value['repositoryId'] and planned['policyPin'] == request['policyPin'] and planned['requiresExplicitAuthorization'] is True, 'REPOSITORY_RETENTION_PLAN_SCOPE_MISMATCH')
    config.authorization(request, plan_pin)
    with RepositoryLock(config, request) as owner:
        owner.check()
        current = plan_retention(catalog, dict(request, operationId=planned['operationId']))
        require(current == planned, 'REPOSITORY_RETENTION_PLAN_STALE')
        completed = []
        for pin in planned['deletePointPins']:
            catalog.deadline.check()
            owner.check()
            config.authorization(request, plan_pin)
            # Verify a complete current point immediately before each deletion.
            point, manifest = catalog.load(pin)
            archive = Path(point['manifestPin']['path']).parent.parent
            safe_path(archive)
            require(archive.parent == catalog.archives and archive != catalog.archives and archive.name not in ('', '.', '..'), 'REPOSITORY_DELETE_TARGET_ESCAPED')
            require(pin not in planned['keepPointPins'], 'REPOSITORY_DELETE_RETAINED_POINT')
            # Re-enumerate under the common server lock. A point outside the
            # original plan must never lose a newly referenced parent.
            current_rows = inventory(catalog)
            remaining_deletes = planned['deletePointPins'][len(completed):]
            expected_paths = {p['path'] for p in planned['keepPointPins'] + remaining_deletes}
            require({row['pointPin']['path'] for row in current_rows} == expected_paths,
                    'REPOSITORY_RETENTION_PLAN_STALE')
            for retained in current_rows:
                if retained['pointPin'] not in remaining_deletes:
                    require(pin not in retained['chainPins'], 'REPOSITORY_DELETE_REQUIRED_PARENT')
            owner.check()
            journal = {'schemaVersion': 'RepositoryRetentionStep/v1', 'operationId': request['operationId'], 'planPin': plan_pin, 'pointPin': pin, 'archivePath': archive.as_posix(), 'state': 'DELETE_INTENT', 'at': utc()}
            write_new(evidence_dir / ('delete-' + pin['sha256'] + '-intent.json'), journal)
            owner.check()
            # shutil uses the current platform end to end. No command-built shell deletion.
            shutil.rmtree(archive)
            require(not archive.exists(), 'REPOSITORY_DELETE_INCOMPLETE')
            completed.append(pin)
            write_new(evidence_dir / ('delete-' + pin['sha256'] + '-complete.json'), dict(journal, state='DELETED', at=utc()))
        return {'schemaVersion': 'RepositoryRetentionResult/v1', 'planPin': plan_pin, 'deletedPointPins': completed, 'preservedPointPins': planned['keepPointPins']}


def capacity_observation(catalog):
    budget, maximum, reserve = 1099511627776, 274877906944, 274877906944
    if catalog.config.native_lab:
        workspace = document(read_pin(pin_file(catalog.config.root / 'workspace-config.json')))
        exact(workspace, 'schemaVersion repositoryId root rootIdentityPin budgetBytes reserveBytes maxAttemptBytes allocationProofPin resourceObservationPin',
            'RepositoryNativeWorkspace/v1')
        require(workspace['repositoryId'] == catalog.config.value['repositoryId'] and workspace['root'] == str(catalog.config.root) and
            all(type(workspace[k]) is int and workspace[k] > 0 for k in ('budgetBytes','maxAttemptBytes','reserveBytes')) and
            workspace['budgetBytes'] <= 80*1024**3 and workspace['maxAttemptBytes']+workspace['reserveBytes'] <= workspace['budgetBytes'],
            'REPOSITORY_NATIVE_WORKSPACE_BUDGET_INVALID')
        budget, maximum, reserve = (workspace[k] for k in ('budgetBytes','maxAttemptBytes','reserveBytes'))
    points = inventory(catalog)
    usage = 0
    for root, dirs, names in os.walk(catalog.config.root):
        for name in dirs + names:
            path = safe_path(Path(root) / name)
            if path.is_file():
                usage += path.stat().st_size
            catalog.deadline.check()
    device = shutil.disk_usage(catalog.config.root)
    from repository_records import timestamp
    ordered = list(reversed(points))
    interval = (timestamp(points[0]['createdAt']) - timestamp(points[-1]['createdAt'])).total_seconds() if len(points) > 1 else 0
    growth = sum(row['payloadBytes'] for row in ordered[1:])
    return {'schemaVersion': 'RepositoryCapacityObservation/v1', 'observedAt': utc(), 'workspaceUsageBytes': usage, 'availableBytes': device.free, 'totalBytes': device.total, 'pointPayloadBytes': sum(row['payloadBytes'] for row in points), 'observedPeakPayloadBytes': max((row['payloadBytes'] for row in points), default=0), 'growthBytesPerSecond': growth / interval if interval > 0 else None, 'workspaceBudgetBytes': budget, 'maxAttemptBytes': maximum, 'reserveBytes': reserve, 'preCaptureAdmissionRequired': True, 'points': [{'pointPin': row['pointPin'], 'createdAt': row['createdAt'], 'payloadBytes': row['payloadBytes']} for row in ordered], 'spaceGuaranteed': False, 'automaticDeletion': False}
