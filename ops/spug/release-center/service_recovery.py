"""Linux host health observer with explicit arming and bounded, pinned restarts."""
import argparse
from contextlib import contextmanager, ExitStack
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import time
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request


class RecoveryBlocked(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise RecoveryBlocked(code)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


def checked_path(value, *, directory=False):
    path = Path(value)
    require(path.is_absolute() and '..' not in path.parts, 'ABSOLUTE_PATH_REQUIRED')
    for node in (path, *path.parents):
        info = node.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not info.st_mode & 0o022, 'UNSAFE_PATH')
    info = path.stat()
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
            and info.st_nlink == 1, 'REGULAR_PATH_REQUIRED')
    return path


def private_file(path):
    path = checked_path(path)
    info = path.stat()
    require(info.st_uid == os.geteuid() and not info.st_mode & 0o077, 'PRIVATE_FILE_REQUIRED')
    return path


def read_json(path):
    path = private_file(path)
    require(path.stat().st_size <= 8 * 1024 * 1024, 'STATE_LIMIT_EXCEEDED')
    return json.loads(path.read_text(encoding='utf-8'))


def atomic_json(path, value):
    path = Path(path)
    parent = checked_path(path.parent, directory=True)
    if path.exists() or path.is_symlink():
        private_file(path)
    temporary = parent / ('.' + path.name + '-' + secrets.token_hex(8))
    raw = json.dumps(value, sort_keys=True, allow_nan=False).encode('utf-8')
    require(len(raw) <= 8 * 1024 * 1024, 'STATE_LIMIT_EXCEEDED')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def exclusive(path, *, create=False, private=True):
    import fcntl
    path = Path(path)
    checked_path(path.parent, directory=True)
    if not create or path.exists() or path.is_symlink():
        if private:
            private_file(path)
        else:
            checked_path(path)
            require(path.stat().st_uid == os.geteuid(), 'LOCK_OWNER_MISMATCH')
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | (os.O_CREAT if create else 0), 0o600)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'INVALID_LOCK')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RecoveryBlocked('PROTECTION_LOCK_BUSY') from None
        require((info.st_dev, info.st_ino) == (path.stat().st_dev, path.stat().st_ino), 'LOCK_REPLACED')
        yield fd
    finally:
        os.close(fd)


def url(value):
    parsed = urlsplit(value)
    require(parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username
            and not parsed.password and not parsed.fragment and not parsed.query, 'INVALID_PROBE_URL')
    return parsed


def load_config(path):
    require(sys.platform.startswith('linux'), 'LINUX_HOST_REQUIRED')
    value = read_json(path)
    fields = {'schemaVersion', 'environment', 'stateDirectory', 'stagingRoot', 'backupEpochPolicyFile',
              'database', 'services', 'dependencies', 'intervalSeconds', 'failureThreshold',
              'startupGraceSeconds', 'cooldownSeconds', 'maxRestarts', 'windowSeconds',
              'requestTimeoutSeconds', 'stopTimeoutSeconds', 'notification'}
    require(set(value) == fields and value['schemaVersion'] == 'ServiceRecoveryConfig/v1', 'CONFIG_INVALID')
    require(value['environment'] in ('test', 'prod', 'backup'), 'ENVIRONMENT_REQUIRED')
    for key in ('stateDirectory', 'stagingRoot'):
        checked_path(value[key], directory=True)
    state = Path(value['stateDirectory']).stat()
    require(state.st_uid == os.geteuid() and not state.st_mode & 0o077, 'PRIVATE_STATE_REQUIRED')
    private_file(value['backupEpochPolicyFile'])
    require(set(value['services']) == {'backend', 'frontend'}, 'EXPLICIT_SERVICES_REQUIRED')
    for role, row in value['services'].items():
        require(set(row) == {'container', 'url', 'kind'} and row['kind'] == ('backend' if role == 'backend' else 'http'),
                'SERVICE_CONFIG_INVALID')
        url(row['url'])
    names = [row['container'] for row in value['services'].values()] + [value['database']]
    require(len(set(names)) == 3 and all(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', n or '')
                                      for n in names), 'CONTAINER_NAMES_INVALID')
    require(type(value['dependencies']) is list and len(value['dependencies']) <= 32, 'DEPENDENCIES_REQUIRED')
    for row in value['dependencies']:
        require(set(row) == {'container'} and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', row['container']),
                'DEPENDENCY_INVALID')
    bounds = {'intervalSeconds': (1, 300), 'failureThreshold': (2, 20), 'startupGraceSeconds': (1, 1800),
              'cooldownSeconds': (1, 3600), 'maxRestarts': (1, 5), 'windowSeconds': (60, 86400),
              'requestTimeoutSeconds': (1, 15), 'stopTimeoutSeconds': (1, 30)}
    for key, (low, high) in bounds.items():
        require(type(value[key]) is int and low <= value[key] <= high, 'INVALID_LIMIT_' + key)
    require(value['windowSeconds'] > value['cooldownSeconds'], 'INVALID_RESTART_WINDOW')
    notify = value['notification']
    require(set(notify) == {'url', 'tokenFile', 'retrySeconds', 'maxAttempts'}, 'NOTIFICATION_REQUIRED')
    url(notify['url'])
    require(type(notify['retrySeconds']) is int and 1 <= notify['retrySeconds'] <= 3600
            and type(notify['maxAttempts']) is int and 1 <= notify['maxAttempts'] <= 10, 'NOTIFICATION_LIMIT_INVALID')
    if notify['tokenFile'] is not None:
        token = private_file(notify['tokenFile']).read_text('utf-8').strip()
        require(token and len(token) <= 4096 and '\n' not in token and '\r' not in token, 'NOTIFICATION_TOKEN_INVALID')
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def http_request(address, timeout, *, payload=None, token=None):
    opener = build_opener(ProxyHandler({}), NoRedirect())
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = Request(address, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(65537)
        require(len(raw) <= 65536, 'HTTP_BODY_LIMIT')
        return response.status, raw


def operation_signature(root):
    root = Path(root)
    roots = [root]
    attempts = root / 'attempts'
    if attempts.exists() or attempts.is_symlink():
        checked_path(attempts, directory=True)
        for child in attempts.iterdir():
            require(len(roots) < 10000, 'OPERATION_HISTORY_LIMIT')
            if child.is_dir() or child.is_symlink():
                roots.append(checked_path(child, directory=True))
    journal = []
    for parent in roots:
        folder = parent / '.operations'
        if folder.exists() or folder.is_symlink():
            checked_path(folder, directory=True)
            for path in folder.iterdir():
                if path.suffix == '.json':
                    checked_path(path)
                    journal.append(str(path.relative_to(root)))
                    require(len(journal) <= 100000, 'OPERATION_HISTORY_LIMIT')
    return digest(sorted(journal))


def status(config, *, now=None):
    now = time.time() if now is None else now
    value = read_json(Path(config['stateDirectory']) / 'state.json')
    if value['paused']:
        result = 'PAUSED'
    elif value['configSha256'] != digest(config):
        result = 'CONFIG_CHANGED'
    elif not 0 <= now - value['observedAt'] <= max(3 * config['intervalSeconds'], 2 * config['requestTimeoutSeconds'] + 2):
        result = 'STALE'
    else:
        result = value['status']
    return dict(status=result, observedAt=value['observedAt'], environment=config['environment'],
                services={k: {'status': v['status'], 'failures': v['failures'], 'restarts': len(v['attempts'])}
                          for k, v in value['services'].items()},
                notifications={s: sum(e['delivery']['status'] == s for e in value['events'])
                               for s in ('PENDING', 'FAILED', 'DELIVERED', 'EXHAUSTED')})


class Recovery:
    def __init__(self, config, *, docker=None):
        from service_recovery_docker import Docker
        self.c = config
        self.docker = docker or Docker(timeout=config['requestTimeoutSeconds'] + config['stopTimeoutSeconds'] + 5)
        self.path = Path(config['stateDirectory']) / 'state.json'
        self.lock = self.path.parent / 'controller.lock'
        # Use the same authoritative backup epoch implementation as capture/restore.
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'recovery'))
        import recovery_backup_epoch
        self.epoch_module = recovery_backup_epoch

    def save(self, state):
        atomic_json(self.path, state)

    def event(self, state, kind, service, now, detail=None):
        require(len(state['events']) < 2000, 'EVENT_CAPACITY_REQUIRES_ARCHIVE_AND_REARM')
        state['events'].append(dict(id=secrets.token_hex(16), environment=self.c['environment'],
            kind=kind, service=service, observedAt=now, detail=detail,
            delivery=dict(status='PENDING', attempts=0, retryAfter=0)))

    def deliver(self, state, now):
        notify = self.c['notification']
        remaining = 4
        for event in state['events']:
            item = event['delivery']
            if item['status'] in ('DELIVERED', 'EXHAUSTED') or now < item['retryAfter']:
                continue
            if remaining == 0:
                break
            remaining -= 1
            item.update(status='FAILED', attempts=item['attempts'] + 1,
                        retryAfter=now + notify['retrySeconds'])
            self.save(state)  # The attempt is durable before sending; event id allows receiver deduplication.
            try:
                token = None if notify['tokenFile'] is None else private_file(notify['tokenFile']).read_text('utf-8').strip()
                code, _ = http_request(notify['url'], self.c['requestTimeoutSeconds'],
                                       payload={k: v for k, v in event.items() if k != 'delivery'}, token=token)
                require(200 <= code < 300, 'DELIVERY_REFUSED')
                item.update(status='DELIVERED', deliveredAt=now, error=None)
            except Exception as error:
                item.update(status='EXHAUSTED' if item['attempts'] >= notify['maxAttempts'] else 'FAILED',
                            error=type(error).__name__)
            self.save(state)

    @contextmanager
    def protected(self):
        epoch = self.epoch_module.validate_policy(read_json(self.c['backupEpochPolicyFile']))
        release_lock = Path(self.c['stagingRoot']) / 'runtime-operation.lock'
        with ExitStack() as stack:
            for path in sorted((release_lock, Path(epoch['sourceLockPath']))):
                stack.enter_context(exclusive(path, private=path != release_lock))
            current = self.epoch_module.read_current(epoch)
            require(current['state'] == 'READY', 'BACKUP_RESTORE_NOT_READY')
            database = self.docker.inspect(self.c['database'])
            self.docker.running(database)
            db_uuid, readonly = self.docker.database_state(database['Id'])
            require(db_uuid == epoch['databaseUuid'] and readonly is False, 'DATABASE_FENCED_OR_CHANGED')
            deps = {}
            for row in self.c['dependencies']:
                info = self.docker.inspect(row['container'])
                self.docker.running(info)
                require(info['State'].get('Health', {}).get('Status') == 'healthy', 'DEPENDENCY_NOT_HEALTHY')
                deps[row['container']] = self.docker.identity(info)
            services = {role: self.docker.inspect(row['container']) for role, row in self.c['services'].items()}
            for role, info in services.items():
                self.docker.running(info)
                target = url(self.c['services'][role]['url'])
                allowed = {self.c['services'][role]['container']}
                allowed.update(n['IPAddress'] for n in info['NetworkSettings']['Networks'].values())
                require(target.hostname in allowed, 'PROBE_NOT_BOUND_TO_CONTAINER')
            env = dict(v.split('=', 1) for v in services['backend']['Config'].get('Env', []))
            require(env.get('INTRUOYI_RELEASE_MAINTENANCE', 'false') == 'false', 'RELEASE_MAINTENANCE_ACTIVE')
            signature = dict(epoch=current, policySha256=digest(epoch), database=self.docker.identity(database),
                             dependencies=deps, operations=operation_signature(self.c['stagingRoot']),
                             locks={str(p): [p.stat().st_dev, p.stat().st_ino]
                                    for p in (release_lock, Path(epoch['sourceLockPath']))})
            yield services, signature

    def verify_before_restart(self, state):
        """Read live fences again while the original two lock descriptors stay held."""
        pinned = state['protection']
        policy = self.epoch_module.validate_policy(read_json(self.c['backupEpochPolicyFile']))
        require(digest(policy) == pinned['policySha256']
                and self.epoch_module.read_current(policy) == pinned['epoch'], 'BACKUP_EPOCH_CHANGED')
        require(operation_signature(self.c['stagingRoot']) == pinned['operations'], 'RELEASE_OPERATION_CHANGED')
        for name, identity in [(self.c['database'], pinned['database']),
                               *pinned['dependencies'].items()]:
            current = self.docker.inspect(name)
            self.docker.running(current)
            require(self.docker.identity(current) == identity, 'DEPENDENCY_IDENTITY_CHANGED')
            if name in pinned['dependencies']:
                require(current['State'].get('Health', {}).get('Status') == 'healthy', 'DEPENDENCY_NOT_HEALTHY')
        uuid, readonly = self.docker.database_state(pinned['database']['containerId'])
        require(uuid == policy['databaseUuid'] and readonly is False, 'DATABASE_FENCED_OR_CHANGED')
        for role, configured in self.c['services'].items():
            current = self.docker.inspect(configured['container'])
            self.docker.running(current)
            require(self.docker.identity(current) == state['services'][role]['identity'], 'SERVICE_IDENTITY_CHANGED')
        for path, identity in pinned['locks'].items():
            node = checked_path(path).stat()
            require([node.st_dev, node.st_ino] == identity, 'LOCK_REPLACED')

    def fault_evidence(self, info, now):
        folder = self.path.parent / 'evidence'
        if not folder.exists():
            folder.mkdir(mode=0o700)
        checked_path(folder, directory=True)
        require(len(list(folder.iterdir())) < 128, 'EVIDENCE_CAPACITY_REQUIRES_ARCHIVE')
        path = folder / (secrets.token_hex(16) + '.json')
        atomic_json(path, dict(observedAt=now, identity=self.docker.identity(info),
                               diagnostics=self.docker.evidence(info)))
        raw = private_file(path).read_bytes()
        return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

    def probe(self, role, info):
        try:
            code, raw = http_request(self.c['services'][role]['url'], self.c['requestTimeoutSeconds'])
            good = code == 200 and (role != 'backend' or json.loads(raw).get('status') == 'UP')
            return good, {'httpStatus': code, 'healthy': good}
        except Exception as error:
            return False, {'errorType': type(error).__name__, 'healthy': False}

    def arm(self, reason):
        require(isinstance(reason, str) and len(reason.strip()) >= 5, 'ARM_REASON_REQUIRED')
        with exclusive(self.lock, create=True), self.protected() as (services, signature):
            require(all(self.probe(role, info)[0] for role, info in services.items()), 'ARM_REQUIRES_HEALTHY_SERVICES')
            now = time.time()
            old = read_json(self.path) if self.path.exists() else None
            state = dict(schemaVersion='ServiceRecoveryState/v1', configSha256=digest(self.c), paused=False,
                reason=reason, observedAt=now, status='HEALTHY', protection=signature, events=old['events'] if old else [], services={})
            for role, info in services.items():
                previous = old['services'][role] if old else {}
                attempts = previous.get('attempts', [])
                require(not attempts or now >= max(attempts), 'CLOCK_INVALID')
                # Explicit re-arm acknowledges an unknown operation, but never clears a live budget.
                state['services'][role] = dict(identity=self.docker.identity(info), failures=0, status='HEALTHY',
                    attempts=attempts, pendingRestart=False, lastRestart=previous.get('lastRestart', 0), incident=False)
            self.event(state, 'ARMED', None, now)
            self.save(state)

    def pause(self, reason):
        require(isinstance(reason, str) and len(reason.strip()) >= 5, 'PAUSE_REASON_REQUIRED')
        with exclusive(self.lock, create=True):
            state = read_json(self.path)
            state.update(paused=True, status='PAUSED', reason=reason)
            self.save(state)

    def cycle(self, *, now=None):
        now = time.time() if now is None else now
        with exclusive(self.lock, create=True):
            state = read_json(self.path)
            require(state.get('schemaVersion') == 'ServiceRecoveryState/v1', 'STATE_INVALID')
            if not math.isfinite(now) or now < state['observedAt']:
                state.update(status='CLOCK_INVALID')
                self.save(state)
                return state
            state['observedAt'] = now
            if state['paused']:
                state['status'] = 'PAUSED'
            else:
                try:
                    require(state['configSha256'] == digest(self.c), 'CONFIG_CHANGED_REARM_REQUIRED')
                    with self.protected() as (services, protection):
                        require(state['protection'] == protection, 'PROTECTION_CHANGED_REARM_REQUIRED')
                        for role, info in services.items():
                            require(state['services'][role]['identity'] == self.docker.identity(info), 'SERVICE_IDENTITY_CHANGED')
                        for role, info in services.items():
                            self.check_service(state, role, info, now)
                    state['status'] = 'HEALTHY' if all(v['status'] == 'HEALTHY' for v in state['services'].values()) else 'DEGRADED'
                except (RecoveryBlocked, OSError, ValueError, KeyError) as error:
                    code = str(error) if isinstance(error, RecoveryBlocked) else type(error).__name__
                    if state.get('protectionError') != code:
                        self.event(state, 'PROTECTED', None, now, code)
                    for service in state['services'].values():
                        service['failures'] = 0
                    state.update(status='PROTECTED', protectionError=code)
            self.save(state)
            self.deliver(state, now)
            return state

    def check_service(self, state, role, info, now):
        service = state['services'][role]
        if service['pendingRestart']:
            service['status'] = 'OUTCOME_UNKNOWN'
            return
        started = datetime.fromisoformat(info['State']['StartedAt'].replace('Z', '+00:00')).timestamp()
        if now - started < self.c['startupGraceSeconds'] or now - service['lastRestart'] < self.c['cooldownSeconds']:
            service.update(status='STARTING', failures=0)
            return
        good, evidence = self.probe(role, info)
        service['lastProbe'] = evidence
        if good:
            if service['incident']:
                self.event(state, 'RECOVERED', role, now)
            service.update(status='HEALTHY', failures=0, incident=False)
            return
        if not service['incident']:
            self.event(state, 'UNHEALTHY', role, now, evidence)
            service['incident'] = True
        service['failures'] += 1
        if service['failures'] < self.c['failureThreshold']:
            service['status'] = 'FAILING'
            return
        service['attempts'] = [t for t in service['attempts'] if now - t < self.c['windowSeconds']]
        if len(service['attempts']) >= self.c['maxRestarts']:
            if service['status'] != 'LIMIT_REACHED':
                self.event(state, 'LIMIT_REACHED', role, now)
            service['status'] = 'LIMIT_REACHED'
            return
        diagnostic = self.fault_evidence(info, now)
        self.verify_before_restart(state)
        service.update(pendingRestart=True, lastRestart=now, failures=0, status='RESTARTING')
        service['attempts'].append(now)
        self.event(state, 'RESTART_REQUESTED', role, now,
                   {'containerId': info['Id'], 'imageId': info['Image'], 'probe': evidence, 'evidence': diagnostic})
        self.save(state)
        try:
            self.docker.restart(info, self.c['stopTimeoutSeconds'])
        except Exception as error:
            service['status'] = 'OUTCOME_UNKNOWN'
            self.event(state, 'RESTART_OUTCOME_UNKNOWN', role, now, type(error).__name__)
        else:
            service.update(pendingRestart=False, status='STARTING')
        self.save(state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('arm', 'pause'):
        sub.add_parser(action).add_argument('--reason', required=True)
    for action in ('run', 'once', 'status'):
        sub.add_parser(action)
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.action == 'status':
            result = status(config)
            print(json.dumps(result))
            return 0 if result['status'] == 'HEALTHY' else 2
        recovery = Recovery(config)
        if args.action in ('arm', 'pause'):
            getattr(recovery, args.action)(args.reason)
            print(json.dumps({'action': args.action, 'status': 'RECORDED'}))
            return 0
        with exclusive(Path(config['stateDirectory']) / 'daemon.lock', create=True):
            while True:
                require(load_config(args.config) == config, 'CONFIG_CHANGED_RESTART_AND_REARM_REQUIRED')
                value = recovery.cycle()
                print(json.dumps({'status': value['status'], 'observedAt': value['observedAt']}), flush=True)
                if args.action == 'once':
                    return 0 if value['status'] == 'HEALTHY' else 2
                time.sleep(config['intervalSeconds'])
    except Exception as error:
        print(json.dumps({'status': 'BLOCKED', 'error': str(error) if isinstance(error, RecoveryBlocked)
                         else type(error).__name__}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.modules['service_recovery'] = sys.modules[__name__]
    sys.exit(main())
