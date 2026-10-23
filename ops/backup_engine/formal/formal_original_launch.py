"""Finite read-only original launch source. Private fields never leave memory.

No service action, CLI, saved-OPEN author or startup-byte claim.
"""
import hashlib
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import sys
import time


class LaunchObservationError(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise LaunchObservationError('ORIGINAL_LAUNCH_' + code)


def _remaining(deadline):
    require(type(deadline) in (int, float) and math.isfinite(deadline), 'DEADLINE_INVALID')
    remaining = deadline - time.monotonic()
    require(remaining > 0, 'DEADLINE')
    return remaining


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'JSON_INVALID')
        result[key] = value
    return result


def _nonfinite(value):
    raise LaunchObservationError('ORIGINAL_LAUNCH_JSON_INVALID')


def inspect_projection(raw, container_id, image_id):
    """Preserve every Config/HostConfig field and every array element/order."""
    require(type(container_id) is str and re.fullmatch('[0-9a-f]{64}', container_id), 'CONTAINER_ID_INVALID')
    require(type(image_id) is str and re.fullmatch('sha256:[0-9a-f]{64}', image_id), 'IMAGE_ID_INVALID')
    require(type(raw) is bytes and 0 < len(raw) <= 1048576, 'OUTPUT_LIMIT')
    try:
        value = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=_pairs, parse_constant=_nonfinite)
        require(type(value) is list and len(value) == 1 and type(value[0]) is dict, 'JSON_INVALID')
        value = value[0]
        require(all(k in value for k in ('Id', 'Image', 'Path', 'Args', 'Config', 'HostConfig', 'Mounts', 'State')), 'FIELDS_MISSING')
        require(value['Id'] == container_id, 'CONTAINER_CHANGED')
        require(value['Image'] == image_id, 'IMAGE_CHANGED')
        require(type(value['Config']) is dict and type(value['HostConfig']) is dict
                and type(value['Path']) is str and type(value['Args']) is list
                and all(type(a) is str for a in value['Args'])
                and type(value['Mounts']) is list and all(type(m) is dict for m in value['Mounts']), 'FIELDS_INVALID')
        state = value['State']
        require(type(state) is dict and type(state.get('Pid')) is int and state['Pid'] > 0
                and type(state.get('StartedAt')) is str and bool(state['StartedAt'])
                and state.get('Running') is True
                and all(state.get(k) is False for k in ('Paused', 'Restarting', 'Dead', 'OOMKilled')), 'CONTAINER_UNSTABLE')
        private = {k: value[k] for k in ('Config', 'HostConfig', 'Image', 'Path', 'Args', 'Mounts')}
        private['Mounts'] = sorted(private['Mounts'], key=_canonical)
        fields = {'Config': 'config', 'HostConfig': 'hostConfig', 'Image': 'image',
                  'Path': 'path', 'Args': 'args', 'Mounts': 'mounts'}
        digests = {prefix + 'Sha256': _sha(_canonical(private[k])) for k, prefix in fields.items()}
        digests['launchSha256'] = _sha(_canonical(private))
        return {'containerId': container_id, 'imageId': image_id, 'pid': state['Pid'],
                'startedAt': state['StartedAt'], 'digests': digests}
    except (ValueError, UnicodeError, TypeError, RecursionError):
        raise LaunchObservationError('ORIGINAL_LAUNCH_JSON_INVALID') from None


def _bounded_command(argv, *, deadline, limit):
    """Internal transport. Production caller supplies one fixed readonly argv."""
    require(type(limit) is int and 0 < limit <= 1048576, 'OUTPUT_LIMIT')
    _remaining(deadline)
    child = None
    selector = None
    output = bytearray()
    command_deadline = time.monotonic() + min(15, _remaining(deadline))
    try:
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C'})
        selector = selectors.DefaultSelector()
        selector.register(child.stdout, selectors.EVENT_READ, 'stdout')
        selector.register(child.stderr, selectors.EVENT_READ, 'stderr')
        while selector.get_map():
            events = selector.select(_remaining(command_deadline))
            require(events, 'COMMAND_TIMEOUT')
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), min(65536, limit - len(output) + 1) if key.data == 'stdout' else 1)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                require(key.data == 'stdout', 'COMMAND_FAILED_OR_WARNING')
                require(len(output) + len(chunk) <= limit, 'OUTPUT_LIMIT')
                output.extend(chunk)
        require(child.wait(timeout=_remaining(command_deadline)) == 0, 'COMMAND_FAILED_OR_WARNING')
        _remaining(deadline)
        return bytes(output)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise LaunchObservationError('ORIGINAL_LAUNCH_COMMAND_FAILED') from None
    finally:
        if selector is not None:
            selector.close()
        if child is not None:
            if child.poll() is None:
                child.kill()
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    raise LaunchObservationError('ORIGINAL_LAUNCH_COMMAND_TERMINATION_UNCERTAIN') from None
            for stream in (child.stdout, child.stderr):
                stream.close()


def _proc_bytes(directory, name, limit, deadline):
    require(name in ('stat', 'cgroup', 'cmdline', 'environ'), 'PROC_INPUT_INVALID')
    _remaining(deadline)
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'PROC_INPUT_INVALID')
        result = bytearray()
        while True:
            _remaining(deadline)
            raw = os.read(fd, min(65536, limit - len(result) + 1))
            if not raw:
                break
            require(len(result) + len(raw) <= limit, 'OUTPUT_LIMIT')
            result.extend(raw)
        _remaining(deadline)
        return bytes(result)
    finally:
        os.close(fd)


def process_snapshot(pid, *, deadline):
    require(sys.platform == 'linux' and type(pid) is int and pid > 0, 'NATIVE_PROCESS_REQUIRED')
    _remaining(deadline)
    directory = None
    try:
        directory = os.open('/proc/' + str(pid), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        before = _proc_bytes(directory, 'stat', 8192, deadline)
        def identity(raw):
            text = raw.decode('ascii', errors='strict'); end = text.rfind(') ')
            require(end > 0 and text.startswith(str(pid) + ' ('), 'PROCESS_INVALID')
            fields = text[end + 2:].split()
            require(len(fields) >= 20 and fields[1].isdigit() and fields[19].isdigit()
                    and fields[0] not in ('Z', 'X', 'x'), 'PROCESS_UNSTABLE')
            return {'pid': pid, 'parentPid': int(fields[1]), 'startTicks': int(fields[19])}
        observed = identity(before)
        for name, limit in (('cgroup', 65536), ('cmdline', 65536), ('environ', 1048576)):
            raw = _proc_bytes(directory, name, limit, deadline)
            require(bool(raw) and (name == 'cgroup' or raw.endswith(b'\0')), 'PROCESS_' + name.upper() + '_SOURCE_MISSING')
            observed[name + 'Sha256'] = _sha(raw)
        for name in ('cwd', 'exe', 'ns/pid', 'ns/mnt'):
            value = os.readlink(name, dir_fd=directory)
            require(bool(value) and len(os.fsencode(value)) <= 4096, 'PROCESS_LINK_INVALID')
            observed[name.replace('/', '_') + 'Sha256'] = _sha(os.fsencode(value))
        require(identity(_proc_bytes(directory, 'stat', 8192, deadline)) == observed_identity(observed), 'PROCESS_CHANGED')
        _remaining(deadline)
        return observed
    except (OSError, UnicodeError, ValueError):
        raise LaunchObservationError('ORIGINAL_LAUNCH_PROCESS_UNAVAILABLE') from None
    finally:
        if directory is not None:
            os.close(directory)


def observed_identity(value):
    return {k: value[k] for k in ('pid', 'parentPid', 'startTicks')}


def require_same_observation(before, after):
    require(before == after, 'SOURCE_CHANGED')


def _boot(deadline):
    _remaining(deadline)
    with Path('/proc/sys/kernel/random/boot_id').open('rb') as stream:
        raw = stream.read(129)
    require(len(raw) <= 128, 'OUTPUT_LIMIT')
    value = raw.decode('ascii', errors='strict').strip()
    require(re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', value), 'BOOT_INVALID')
    _remaining(deadline)
    return value


def java_jar_entry(raw, executable, cwd):
    """Recognize the first Java entry; later tokens are application arguments.

    Only self-contained -X/-XX/-D JVM options are supported before -jar.
    Other launch grammars need an explicit reviewed contract, never inference.
    """
    require(type(raw) is bytes and 0 < len(raw) <= 65536 and raw.endswith(b'\0'), 'JAVA_LAUNCH_UNAVAILABLE')
    require(type(executable) is str and Path(executable).name == 'java'
            and cwd == '/yudao-server', 'JAVA_LAUNCH_UNAVAILABLE')
    try:
        args = raw[:-1].decode('utf-8', errors='strict').split('\0')
    except UnicodeError:
        raise LaunchObservationError('ORIGINAL_LAUNCH_JAVA_LAUNCH_UNAVAILABLE') from None
    require(bool(args[0]) and Path(args[0]).name == 'java', 'JAVA_LAUNCH_UNAVAILABLE')
    for index in range(1, len(args)):
        token = args[index]
        if token == '-jar':
            require(index + 1 < len(args) and args[index + 1] in
                    ('app.jar', '/yudao-server/app.jar'), 'JAVA_LAUNCH_UNAVAILABLE')
            return '/yudao-server/app.jar'
        require((token.startswith('-XX:') and len(token) > 4)
                or (token.startswith('-X') and not token.startswith('-XX') and len(token) > 2)
                or (token.startswith('-D') and len(token) > 2), 'JAVA_LAUNCH_UNAVAILABLE')
    raise LaunchObservationError('ORIGINAL_LAUNCH_JAVA_LAUNCH_UNAVAILABLE')


class NativeJarSource:
    """Fixed current app.jar through a pinned proc directory, never loaded bytes.

    The caller owns the actual /proc/PID descriptor and validates its process.
    Only proc's root magic link is followed. Every following component uses
    NOFOLLOW; nonblocking open rejects FIFOs before a content read can wait.
    """
    def __init__(self, proc_directory, *, deadline):
        require(sys.platform == 'linux' and os.geteuid() == 0, 'LINUX_ROOT_REQUIRED')
        require(type(proc_directory) is int and proc_directory >= 0, 'PROC_INPUT_INVALID')
        require(all(hasattr(os, name) for name in ('O_NOATIME', 'O_NOFOLLOW', 'O_DIRECTORY', 'ST_RDONLY')),
                'ARTIFACT_NATIVE_FLAGS_REQUIRED')
        self.proc = proc_directory; self.deadline = deadline; self.fds = []; self.observed = None
        self.retained = False

    @staticmethod
    def signature(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
                info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    def _remaining(self):
        _remaining(self.deadline)

    @staticmethod
    def _trusted_directory(fd):
        info = os.fstat(fd)
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and info.st_mode & 0o022 == 0,
                'ARTIFACT_DIRECTORY_UNTRUSTED')
        return info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid

    def _file_signature(self, info):
        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1
                and info.st_mode & 0o022 == 0 and 0 < info.st_size <= 1073741824,
                'ARTIFACT_FILE_UNTRUSTED')
        return self.signature(info)

    def __enter__(self):
        self._remaining()
        try:
            self.root_link = self.signature(os.stat('root', dir_fd=self.proc, follow_symlinks=False))
            require(stat.S_ISLNK(self.root_link[2]), 'ARTIFACT_PROC_ROOT_INVALID')
            self.root_target = os.readlink('root', dir_fd=self.proc)
            require(bool(self.root_target) and len(os.fsencode(self.root_target)) <= 4096, 'ARTIFACT_PROC_ROOT_INVALID')
            self.root = os.open('root', os.O_RDONLY | os.O_DIRECTORY | os.O_NOATIME, dir_fd=self.proc)
            self.fds.append(self.root); self.root_identity = self._trusted_directory(self.root)
            self.directory = os.open('yudao-server', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NOATIME,
                                     dir_fd=self.root)
            self.fds.append(self.directory); self.directory_identity = self._trusted_directory(self.directory)
            self.fd = os.open('app.jar', os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_NONBLOCK,
                              dir_fd=self.directory)
            self.fds.append(self.fd); self.file_identity = self._file_signature(os.fstat(self.fd))
            self.readonly = bool(os.fstatvfs(self.fd).f_flag & os.ST_RDONLY)
            self.assert_unchanged()
            return self
        except OSError:
            self.__exit__(None, None, None)
            raise LaunchObservationError('ORIGINAL_LAUNCH_ARTIFACT_UNAVAILABLE') from None
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        for fd in reversed(self.fds):
            os.close(fd)
        self.fds.clear()

    def assert_unchanged(self):
        self._remaining()
        try:
            require(self.signature(os.stat('root', dir_fd=self.proc, follow_symlinks=False)) == self.root_link
                    and os.readlink('root', dir_fd=self.proc) == self.root_target, 'ARTIFACT_ROOT_CHANGED')
            require(self._trusted_directory(self.root) == self.root_identity, 'ARTIFACT_ROOT_CHANGED')
            root = os.stat('root', dir_fd=self.proc, follow_symlinks=True)
            require((root.st_dev, root.st_ino, root.st_mode, root.st_uid, root.st_gid) == self.root_identity,
                    'ARTIFACT_ROOT_CHANGED')
            directory = os.stat('yudao-server', dir_fd=self.root, follow_symlinks=False)
            require((directory.st_dev, directory.st_ino, directory.st_mode, directory.st_uid, directory.st_gid)
                    == self.directory_identity and self._trusted_directory(self.directory) == self.directory_identity,
                    'ARTIFACT_DIRECTORY_CHANGED')
            require(self._file_signature(os.fstat(self.fd)) == self.file_identity
                    and self._file_signature(os.stat('app.jar', dir_fd=self.directory, follow_symlinks=False))
                    == self.file_identity and bool(os.fstatvfs(self.fd).f_flag & os.ST_RDONLY) == self.readonly,
                    'ARTIFACT_CHANGED')
            self._remaining()
        except OSError:
            raise LaunchObservationError('ORIGINAL_LAUNCH_ARTIFACT_UNAVAILABLE') from None

    def observe(self):
        require(self.observed is None, 'ARTIFACT_ALREADY_READ')
        self.assert_unchanged(); digest = hashlib.sha256(); count = 0
        try:
            while True:
                self._remaining(); raw = os.read(self.fd, 65536)
                if not raw:
                    break
                count += len(raw); require(count <= self.file_identity[6], 'ARTIFACT_CHANGED'); digest.update(raw)
            require(count == self.file_identity[6], 'ARTIFACT_CHANGED'); self.assert_unchanged()
            keys = ('device', 'inode', 'mode', 'uid', 'gid', 'links', 'size', 'mtimeNs', 'ctimeNs')
            self.observed = dict(identity=dict(zip(keys, self.file_identity)), sha256=digest.hexdigest(), bytes=count,
                                readOnlyFilesystem=self.readonly, atimeWritesAvoided=True, loadedAtStartupBytesProven=False)
            return json.loads(_canonical(self.observed))
        except OSError:
            raise LaunchObservationError('ORIGINAL_LAUNCH_ARTIFACT_UNAVAILABLE') from None


    def retain(self):
        """Pin the observed readonly file independently of the old proc entry.

        This native capability is valid only while its owning process lives;
        a receipt or an image digest cannot recreate it after holder loss.
        """
        require(self.observed is not None and self.readonly is True,
                'ARTIFACT_OBSERVED_READONLY_REQUIRED')
        require(not self.retained, 'ARTIFACT_ALREADY_RETAINED')
        self.assert_unchanged()
        retained = _RetainedJarSource(self)
        try:
            self.assert_unchanged()
            retained.assert_unchanged(deadline=self.deadline)
        except BaseException:
            retained.close()
            raise
        self.retained = True
        return retained


class _RetainedJarSource:
    """In-process FDs for one observed original JAR, never a reopen contract."""
    signature = staticmethod(NativeJarSource.signature)
    _file_signature = NativeJarSource._file_signature

    def __init__(self, source):
        self.fds = []
        self.root_identity = source.root_identity
        self.directory_identity = source.directory_identity
        self.file_identity = source.file_identity
        self.original = json.loads(_canonical(source.observed))
        try:
            for fd in (source.root, source.directory, source.fd):
                self.fds.append(os.dup(fd))
        except OSError:
            self.close()
            raise LaunchObservationError('ORIGINAL_LAUNCH_ARTIFACT_RETAIN_UNAVAILABLE') from None

    def close(self):
        for fd in reversed(self.fds):
            os.close(fd)
        self.fds.clear()

    def assert_unchanged(self, *, deadline):
        require(0 < _remaining(deadline) <= 90, 'DEADLINE_INVALID')
        require(len(self.fds) == 3, 'ARTIFACT_RETAINED_CLOSED')
        root, directory, fd = self.fds
        try:
            require(NativeJarSource._trusted_directory(root) == self.root_identity,
                    'ARTIFACT_ROOT_CHANGED')
            link = os.stat('yudao-server', dir_fd=root, follow_symlinks=False)
            require((link.st_dev, link.st_ino, link.st_mode, link.st_uid, link.st_gid)
                    == self.directory_identity
                    and NativeJarSource._trusted_directory(directory) == self.directory_identity,
                    'ARTIFACT_DIRECTORY_CHANGED')
            require(self._file_signature(os.fstat(fd)) == self.file_identity
                    and self._file_signature(os.stat('app.jar', dir_fd=directory, follow_symlinks=False))
                    == self.file_identity and bool(os.fstatvfs(fd).f_flag & os.ST_RDONLY),
                    'ARTIFACT_CHANGED')
            _remaining(deadline)
        except OSError:
            raise LaunchObservationError('ORIGINAL_LAUNCH_ARTIFACT_RETAIN_UNAVAILABLE') from None

    def observe(self, *, deadline):
        self.assert_unchanged(deadline=deadline)
        digest = hashlib.sha256(); count = 0
        try:
            while True:
                _remaining(deadline)
                raw = os.pread(self.fds[2], 65536, count)
                if not raw:
                    break
                count += len(raw)
                require(count <= self.file_identity[6], 'ARTIFACT_CHANGED')
                digest.update(raw)
            require(count == self.file_identity[6] and digest.hexdigest() == self.original['sha256'],
                    'ARTIFACT_CHANGED')
            self.assert_unchanged(deadline=deadline)
            result = json.loads(_canonical(self.original))
            result.update(retainedSource=True, coldStartConfirmed=False, releaseReady=False)
            return result
        except OSError:
            raise LaunchObservationError('ORIGINAL_LAUNCH_ARTIFACT_RETAIN_UNAVAILABLE') from None


def observe_original_launch(role, container_id, image_id, expected_boot_id, *, deadline):
    """Internal root source observation; does not authorize any following action."""
    require(sys.platform == 'linux' and os.geteuid() == 0, 'LINUX_ROOT_REQUIRED')
    require(type(role) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', role), 'ROLE_INVALID')
    require(type(container_id) is str and re.fullmatch('[0-9a-f]{64}', container_id), 'CONTAINER_ID_INVALID')
    require(type(image_id) is str and re.fullmatch('sha256:[0-9a-f]{64}', image_id), 'IMAGE_ID_INVALID')
    require(0 < _remaining(deadline) <= 90, 'DEADLINE_INVALID')
    def inspect():
        raw = _bounded_command(['/usr/bin/docker', '--host', 'unix:///var/run/docker.sock', 'inspect',
                                '--type', 'container', container_id], deadline=deadline, limit=1048576)
        return inspect_projection(raw, container_id, image_id)
    try:
        require(_boot(deadline) == expected_boot_id, 'BOOT_CHANGED')
        first = inspect(); pid = first['pid']
        process = process_snapshot(pid, deadline=deadline)
        directory = os.open('/proc/' + str(pid), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            groups = _proc_bytes(directory, 'cgroup', 65536, deadline)
            argv = _proc_bytes(directory, 'cmdline', 65536, deadline)
            require(_sha(groups) == process['cgroupSha256'] and _sha(argv) == process['cmdlineSha256'], 'PROCESS_CHANGED')
            paths = [line.split(':', 2)[2] for line in groups.decode('utf-8', errors='strict').splitlines()]
            require(any(segment in (container_id, 'docker-' + container_id + '.scope')
                        for path in paths for segment in path.split('/')), 'PROCESS_SCOPE_UNAVAILABLE')
            executable = os.readlink('exe', dir_fd=directory); cwd = os.readlink('cwd', dir_fd=directory)
            require(_sha(os.fsencode(executable)) == process['exeSha256'] and _sha(os.fsencode(cwd)) == process['cwdSha256'], 'PROCESS_CHANGED')
            java_jar_entry(argv, executable, cwd)
            with NativeJarSource(directory, deadline=deadline) as artifact:
                current_jar = artifact.observe()
                require_same_observation({'inspect': first, 'process': process},
                    {'inspect': inspect(), 'process': process_snapshot(pid, deadline=deadline)})
                require(_boot(deadline) == expected_boot_id, 'BOOT_CHANGED')
                artifact.assert_unchanged()
        finally:
            os.close(directory)
        _remaining(deadline)
        return {'schemaVersion': 'formal-original-launch-observation/v1', 'role': role,
            'bootId': expected_boot_id, 'inspect': first, 'process': process,
            'currentJar': current_jar,
            'loadedAtStartupBytesProven': False, 'runtimeCapabilitiesVerified': False,
            'serverWritesPerformed': False, 'secretValuesEmitted': False,
            'productionEvidence': False, 'releaseReady': False}
    except (OSError, UnicodeError, ValueError, IndexError):
        raise LaunchObservationError('ORIGINAL_LAUNCH_SOURCE_UNAVAILABLE') from None


@contextmanager
def hold_original_launch(role, container_id, image_id, expected_boot_id, *, deadline):
    """Bind the full running observation to native original artifact FDs.

    The same caller must keep this scope alive through the stop and recovery.
    It performs no action, writes no receipt and supplies no restart fallback.
    """
    retained = None
    try:
        original = observe_original_launch(role, container_id, image_id, expected_boot_id, deadline=deadline)
        directory = os.open('/proc/' + str(original['inspect']['pid']),
                            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with NativeJarSource(directory, deadline=deadline) as source:
                require_same_observation(original['currentJar'], source.observe())
                retained = source.retain()
                final = observe_original_launch(role, container_id, image_id, expected_boot_id, deadline=deadline)
                require_same_observation(original, final)
                source.assert_unchanged()
                retained.assert_unchanged(deadline=deadline)
        finally:
            os.close(directory)
    except BaseException as error:
        if retained is not None:
            retained.close()
        if isinstance(error, OSError):
            raise LaunchObservationError('ORIGINAL_LAUNCH_ARTIFACT_RETAIN_UNAVAILABLE') from None
        raise
    try:
        yield original, retained
    finally:
        retained.close()


def stopped_inspect_projection(raw, container_id, image_id):
    """Explicit stopped source grammar, never fabricate a running PID/state."""
    from datetime import datetime
    require(type(container_id) is str and re.fullmatch('[0-9a-f]{64}',container_id), 'CONTAINER_ID_INVALID')
    require(type(image_id) is str and re.fullmatch('sha256:[0-9a-f]{64}',image_id), 'IMAGE_ID_INVALID')
    require(type(raw) is bytes and 0<len(raw)<=1048576, 'OUTPUT_LIMIT')
    try:
        rows=json.loads(raw.decode('utf-8',errors='strict'),object_pairs_hook=_pairs,parse_constant=_nonfinite)
        require(type(rows) is list and len(rows)==1 and type(rows[0]) is dict,'JSON_INVALID')
        value=rows[0]
        require(all(k in value for k in ('Id','Image','Path','Args','Config','HostConfig','Mounts','State')),'FIELDS_MISSING')
        require(value['Id']==container_id and value['Image']==image_id,'SOURCE_CHANGED')
        require(type(value['Config']) is dict and type(value['HostConfig']) is dict and type(value['Path']) is str and
                type(value['Args']) is list and all(type(a) is str for a in value['Args']) and
                type(value['Mounts']) is list and all(type(m) is dict for m in value['Mounts']),'FIELDS_INVALID')
        state=value['State']
        require(type(state) is dict and type(state.get('Pid')) is int and state['Pid']==0 and
            all(state.get(k) is False for k in ('Running','Paused','Restarting','Dead','OOMKilled')) and
            type(state.get('ExitCode')) is int and state['ExitCode']==0,'CONTAINER_UNSTABLE')
        timestamps=[]
        for key in ('StartedAt','FinishedAt'):
            selected=state.get(key)
            require(type(selected) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,9})?Z',selected),
                    'CONTAINER_UNSTABLE')
            timestamps.append(datetime.fromisoformat(selected[:-1]+'+00:00'))
        require(timestamps[0].year>1 and timestamps[1]>timestamps[0],'CONTAINER_UNSTABLE')
        private={k:value[k] for k in ('Config','HostConfig','Image','Path','Args','Mounts')}
        private['Mounts']=sorted(private['Mounts'],key=_canonical)
        fields={'Config':'config','HostConfig':'hostConfig','Image':'image','Path':'path','Args':'args','Mounts':'mounts'}
        digests={prefix+'Sha256':_sha(_canonical(private[k])) for k,prefix in fields.items()}
        digests['launchSha256']=_sha(_canonical(private))
        return {'containerId':container_id,'imageId':image_id,'pid':0,'digests':digests,
                'state':{k:state[k] for k in ('Running','Paused','Restarting','Dead','OOMKilled','ExitCode','StartedAt','FinishedAt')}}
    except (ValueError,UnicodeError,TypeError,RecursionError):
        raise LaunchObservationError('ORIGINAL_LAUNCH_JSON_INVALID') from None


def observe_stopped_original_launch(role, container_id, image_id, expected_boot_id, *, deadline):
    """Only static launch observation; does not read proc or authorize OPEN/start."""
    require(sys.platform=='linux' and os.geteuid()==0,'LINUX_ROOT_REQUIRED')
    require(role=='backend','ROLE_INVALID')
    require(0<_remaining(deadline)<=90,'DEADLINE_INVALID')
    def inspect():
        return stopped_inspect_projection(_bounded_command(['/usr/bin/docker','--host','unix:///var/run/docker.sock',
            'inspect','--type','container',container_id],deadline=deadline,limit=1048576),container_id,image_id)
    try:
        require(_boot(deadline)==expected_boot_id,'BOOT_CHANGED')
        first=inspect();require_same_observation(first,inspect())
        require(_boot(deadline)==expected_boot_id,'BOOT_CHANGED');_remaining(deadline)
        return {'schemaVersion':'formal-original-stopped-launch-observation/v1','role':role,'bootId':expected_boot_id,
            'inspect':first,'processObserved':False,'loadedAtStartupBytesProven':False,'runtimeCapabilitiesVerified':False,
            'serverWritesPerformed':False,'secretValuesEmitted':False,'productionEvidence':False,'releaseReady':False}
    except (OSError,UnicodeError,ValueError):
        raise LaunchObservationError('ORIGINAL_LAUNCH_SOURCE_UNAVAILABLE') from None


class OriginalLaunchRecoveryChecks:
    """Live original-FD and JVM source checks for one in-process restoration.

    Construct while the original is running inside its held launch scope.
    Observe STOPPED before STARTED and pin the first successful new runtime;
    observations never authorize or issue an action. The caller still owns
    claim, approval, durable once intent, exclusion, drain and health gates.
    """
    def __init__(self, original, retained, binding, instance, *, deadline):
        import formal_jvm_identity as jvm
        require(sys.platform == 'linux' and os.getuid() == os.geteuid() == 0,
                'LINUX_ROOT_REQUIRED')
        require(0 < _remaining(deadline) <= 60, 'DEADLINE_INVALID')
        require(type(retained) is _RetainedJarSource and type(original) is dict
                and original.get('schemaVersion') == 'formal-original-launch-observation/v1'
                and original.get('role') == 'backend', 'RECOVERY_INPUT_INVALID')
        self.original = json.loads(_canonical(original))
        self.retained = retained
        self.binding = json.loads(_canonical(binding))
        self.instance = instance
        self.phase = 'RUNNING'
        self.stop_observation = None
        self.start_observation = None
        self.start_identity = None
        self.start_socket = None
        try:
            require_same_observation(self.original['currentJar'], retained.original)
            retained.observe(deadline=deadline)
            jvm._input(self.binding, self.original['process'], instance,
                retained.original['sha256'], self.original['bootId'])
            require(self.binding['pid'] == self.original['inspect']['pid'], 'RECOVERY_PEER_CHANGED')
            signature = jvm._socket_signature(self.binding)
            self.previous = self._identity(self.binding, self.original, deadline)
            require_same_observation(self.original, self._running(deadline))
            require(jvm._socket_signature(self.binding) == signature, 'RECOVERY_SOCKET_CHANGED')
            retained.assert_unchanged(deadline=deadline)
        except jvm.JvmIdentityError:
            raise LaunchObservationError('ORIGINAL_LAUNCH_RECOVERY_JVM_SOURCE_UNAVAILABLE') from None

    def _running(self, deadline):
        selected = self.original['inspect']
        return observe_original_launch('backend', selected['containerId'], selected['imageId'],
            self.original['bootId'], deadline=deadline)

    def _identity(self, binding, observed, deadline):
        import formal_jvm_identity as jvm
        value = jvm.observe_jvm_identity(binding, observed['process'], self.instance,
            self.retained.original['sha256'], self.original['bootId'], deadline=deadline)
        require(type(value) is dict and type(value.get('peerPid')) is int
                and value['peerPid'] == binding['pid'] == observed['inspect']['pid'], 'RECOVERY_PEER_CHANGED')
        identity = value.get('identity')
        require(type(identity) is dict, 'RECOVERY_IDENTITY_INVALID')
        native = {name: identity.get(name) for name in
            ('pid', 'startTicks', 'hostBootId', 'pidNamespace', 'mountNamespace')}
        jvm._response(_canonical({key:item for key,item in value.items() if key != 'peerPid'}),
            value.get('nonce'), native, self.instance, self.retained.original['sha256'])
        require(type(native['pid']) is int and native['pid'] > 0
                and type(native['startTicks']) is int and native['startTicks'] == observed['process']['startTicks']
                and native['hostBootId'] == observed['bootId']
                and all(type(native[name]) is str and re.fullmatch(prefix+r':\[[0-9]+\]', native[name])
                    and _sha(os.fsencode(native[name])) == observed['process'][digest]
                    for name,prefix,digest in (('pidNamespace','pid','ns_pidSha256'),
                                              ('mountNamespace','mnt','ns_mntSha256'))), 'RECOVERY_IDENTITY_CHANGED')
        return json.loads(_canonical(value))

    def stopped(self, expected_runtime, *, deadline):
        require(self.phase in ('RUNNING', 'STOPPED') and 0 < _remaining(deadline) <= 60,
                'RECOVERY_PHASE_INVALID')
        selected = self.original['inspect']
        self.retained.observe(deadline=deadline)
        observed = observe_stopped_original_launch('backend', selected['containerId'], selected['imageId'],
            self.original['bootId'], deadline=deadline)
        require_same_observation(observed['inspect']['digests'], selected['digests'])
        require_same_observation(observed['inspect']['state'], expected_runtime)
        require(observed['inspect']['state']['StartedAt'] == selected['startedAt'], 'RECOVERY_STOP_CHANGED')
        if self.stop_observation is not None:
            require_same_observation(observed, self.stop_observation)
        final = observe_stopped_original_launch('backend', selected['containerId'], selected['imageId'],
            self.original['bootId'], deadline=deadline)
        require_same_observation(observed, final)
        self.retained.assert_unchanged(deadline=deadline)
        self.stop_observation = json.loads(_canonical(observed))
        self.phase = 'STOPPED'
        return dict(stoppedLaunchMatched=True, originalArtifactSha256=self.retained.original['sha256'],
            coldStartConfirmed=False, fullDrain=False, fullHostFence=False, releaseReady=False)

    def started(self, binding, *, deadline):
        import formal_jvm_identity as jvm
        require(self.phase in ('STOPPED', 'STARTED') and 0 < _remaining(deadline) <= 60,
                'RECOVERY_PHASE_INVALID')
        require(type(binding) is dict and all(binding.get(name) == self.binding[name]
                and type(binding.get(name)) is type(self.binding[name]) for name in ('path','uid','gid')),
                'RECOVERY_SOCKET_SCOPE_CHANGED')
        try:
            self.retained.observe(deadline=deadline)
            observed = self._running(deadline)
            selected = observed['inspect']
            require_same_observation(selected['digests'], self.original['inspect']['digests'])
            require_same_observation(observed['currentJar'], self.retained.original)
            require(selected['startedAt'] != self.original['inspect']['startedAt'], 'RECOVERY_START_REQUIRED')
            require(all(observed['process'][name] == self.original['process'][name] for name in
                ('cgroupSha256', 'cmdlineSha256', 'exeSha256', 'cwdSha256')), 'RECOVERY_PROCESS_LAUNCH_CHANGED')
            jvm._input(binding, observed['process'], self.instance, self.retained.original['sha256'], self.original['bootId'])
            require(binding['pid'] == selected['pid'], 'RECOVERY_PEER_CHANGED')
            signature = jvm._socket_signature(binding)
            current = self._identity(binding, observed, deadline)
            jvm.require_new_jvm(self.previous, current)
            if self.start_observation is not None:
                require_same_observation(observed, self.start_observation)
                require_same_observation(current['identity'], self.start_identity)
                require(signature == self.start_socket, 'RECOVERY_SOCKET_CHANGED')
            require_same_observation(observed, self._running(deadline))
            require(jvm._socket_signature(binding) == signature, 'RECOVERY_SOCKET_CHANGED')
            self.retained.assert_unchanged(deadline=deadline)
            self.start_observation = json.loads(_canonical(observed))
            self.start_identity = json.loads(_canonical(current['identity']))
            self.start_socket = signature
            self.phase = 'STARTED'
            return dict(newProcessIdentityMatched=True, originalLaunchMatched=True,
                originalArtifactSha256=self.retained.original['sha256'], coldStartConfirmed=False,
                fullDrain=False, fullHostFence=False, releaseReady=False, productionEvidence=False,
                serviceActionsPerformed=False)
        except jvm.JvmIdentityError:
            raise LaunchObservationError('ORIGINAL_LAUNCH_RECOVERY_JVM_SOURCE_UNAVAILABLE') from None
