#!/usr/bin/env python3
"""Native bounded thaw watchdog, not evidence that a freeze was acquired.

The caller must independently authorize maintenance and prove capture remained
under the fence. Explicit acquisition is an approved native stage only, never
COMPLETE. Its journal must live on a different filesystem.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
import time


class WatchdogError(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def require(condition, code):
    if not condition:
        raise WatchdogError(code)


def require_native_runtime():
    """Refuse unsupported host runtime before journals or acquisition."""
    require(os.name == 'posix' and sys.version_info >= (3, 7) and
            type(getattr(time, 'CLOCK_BOOTTIME', None)) is int and
            callable(getattr(time, 'clock_gettime', None)) and
            all(type(getattr(os, flag, None)) is int for flag in ('O_NOFOLLOW', 'O_DIRECTORY')),
            'WATCHDOG_RUNTIME_UNSUPPORTED')


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def private_directory(path):
    path = Path(path).absolute()
    require(path.is_dir() and path.resolve() == path and not path.is_symlink() and
            stat.S_IMODE(path.stat().st_mode) == 0o700, 'WATCHDOG_CONTROL_PATH_INVALID')
    for parent in path.parents:
        require(parent.is_dir() and not parent.is_symlink(), 'WATCHDOG_CONTROL_PATH_INVALID')
    return path


def write_exclusive(root, name, value):
    data = canonical(value)
    require(len(data)<=16384 and type(name) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',name),
            'WATCHDOG_CONTROL_OUTPUT_LIMIT')
    require(sum(1 for path in Path(root).iterdir() if path.is_file())<16,'WATCHDOG_CONTROL_FILE_LIMIT')
    fd = os.open(root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as output:
            output.write(data)
            output.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def observe_mount(mount, expected, *, timeout=5):
    require(type(timeout) in (int,float) and 0<timeout<=5,'WATCHDOG_MOUNT_DEADLINE_INVALID')
    require(type(expected) is dict and set(expected) == {'source', 'device', 'fstype', 'target'},
            'WATCHDOG_MOUNT_BINDING_INVALID')
    require(type(expected['source']) is str and expected['source'].startswith('/dev/') and
            type(expected['device']) is str and re.fullmatch(r'[0-9]+:[0-9]+', expected['device']) and
            expected['fstype'] == 'ext4' and expected['target'] == str(mount),
            'WATCHDOG_MOUNT_BINDING_INVALID')
    try:
        result = subprocess.run(['findmnt', '--json', '--mountpoint', str(mount), '--output',
                                 'SOURCE,MAJ:MIN,FSTYPE,TARGET'], capture_output=True, timeout=timeout)
    except (OSError,subprocess.TimeoutExpired):
        raise WatchdogError('WATCHDOG_MOUNT_OBSERVATION_FAILED') from None
    require(result.returncode == 0 and len(result.stdout) <= 16384,
            'WATCHDOG_MOUNT_OBSERVATION_FAILED')
    try:
        rows = json.loads(result.stdout)['filesystems']
    except (ValueError, KeyError):
        raise WatchdogError('WATCHDOG_MOUNT_OBSERVATION_INVALID') from None
    require(rows == [{'source': expected['source'], 'maj:min': expected['device'],
                      'fstype': expected['fstype'], 'target': expected['target']}],
            'WATCHDOG_MOUNT_CHANGED')
    actual = mount.stat().st_dev
    require(f'{os.major(actual)}:{os.minor(actual)}' == expected['device'], 'WATCHDOG_DEVICE_CHANGED')


def run_watchdog(root, mount, binding, seconds, control_fd, *, acquire=False):
    require_native_runtime()
    require(type(seconds) is int and 1 <= seconds <= 300, 'WATCHDOG_DEADLINE_INVALID')
    require(type(acquire) is bool, 'WATCHDOG_ACQUIRE_INVALID')
    require(type(binding) is dict and set(binding) == {'operationId', 'bootId', 'mount'} and
            type(binding['operationId']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', binding['operationId']),
            'WATCHDOG_BINDING_INVALID')
    require(binding['bootId'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'WATCHDOG_BOOT_CHANGED')
    root = private_directory(root)
    mount = Path(mount).absolute()
    require(mount.is_dir() and mount.resolve() == mount and not mount.is_symlink(), 'WATCHDOG_MOUNT_PATH_INVALID')
    observe_mount(mount, binding['mount'])
    require(root.stat().st_dev != mount.stat().st_dev, 'WATCHDOG_CONTROL_ON_FROZEN_DEVICE')
    identity = (root.stat().st_dev, root.stat().st_ino)
    require(not list(root.iterdir()), 'WATCHDOG_EXISTING_EVIDENCE')
    started = time.clock_gettime(time.CLOCK_BOOTTIME)
    deadline = started + seconds
    digest = hashlib.sha256(canonical(binding)).hexdigest()
    write_exclusive(root, '000-ready.json', {'status': 'READY_NOT_FENCE_PROOF', 'binding': binding,
        'bindingSha256': digest, 'startedBootSeconds': started, 'deadlineBootSeconds': deadline,
        'pid': os.getpid(), 'productionEvidence': False})
    # An SSH/session hangup must not disable the independently running recovery process.
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    abort = []
    signal.signal(signal.SIGTERM, lambda signum, frame: abort.append('termination'))
    if acquire:
        write_exclusive(root, '003-freeze-intent.json', {'status': 'ACQUIRE_INTENT_NOT_FENCE_PROOF',
            'bindingSha256': digest, 'observedBootSeconds': time.clock_gettime(time.CLOCK_BOOTTIME)})
        # This independent process owns the acquisition command. The business
        # owner never issues a late freeze after watchdog expiry. A hung kernel
        # acquisition cannot be promised a bounded automatic recovery: retain
        # recovery-required intent, and do not acknowledge readiness.
        try:
            freeze = subprocess.run(['fsfreeze', '--freeze', str(mount)], capture_output=True,
                                    timeout=min(seconds, 5))
        except subprocess.SubprocessError:
            write_exclusive(root, '004-acquire-uncertain.json', {'status': 'RECOVERY_REQUIRED_ACQUIRE_UNCERTAIN',
                'bindingSha256': digest, 'notCaptureCompletion': True})
            raise WatchdogError('WATCHDOG_ACQUIRE_UNCERTAIN_RETAINED') from None
        require(freeze.returncode == 0, 'WATCHDOG_ACQUIRE_FAILED_RETAINED')
        # No READY acknowledgement once the deadline is consumed. In that case
        # proceed directly to invalidation/thaw using the same exact binding.
        if time.clock_gettime(time.CLOCK_BOOTTIME) < deadline and not abort:
            write_exclusive(root, '005-freeze-acquired.json', {'status': 'ACTUAL_FREEZE_ACQUIRED_STAGE_ONLY',
                'bindingSha256': digest, 'observedBootSeconds': time.clock_gettime(time.CLOCK_BOOTTIME),
                'notFullFormalEvidence': True})
    if not acquire or (time.clock_gettime(time.CLOCK_BOOTTIME) < deadline and not abort):
        print('WATCHDOG_READY_NOT_FENCE_PROOF', flush=True)
    else:
        abort.append('acquire-deadline-or-termination')
    data = b''
    accepted = None
    while not abort and time.clock_gettime(time.CLOCK_BOOTTIME) < deadline:
        remaining = deadline - time.clock_gettime(time.CLOCK_BOOTTIME)
        ready, _, _ = select.select([control_fd], [], [], min(0.1, max(0, remaining)))
        if not ready:
            continue
        chunk = os.read(control_fd, 128)
        if not chunk:
            abort.append('owner-control-eof')
            break
        data += chunk
        if len(data) > 128 or b'\n' in data:
            finish = re.fullmatch(rb'CAPTURE_FINISH ([0-9a-f]{64})\n', data)
            if finish and acquire and time.clock_gettime(time.CLOCK_BOOTTIME) < deadline:
                try:
                    path = root / 'physical-capture.json'
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                    try:
                        info = os.fstat(fd)
                        require(stat.S_ISREG(info.st_mode) and info.st_size <= 16384 and stat.S_IMODE(info.st_mode) == 0o600,
                                'WATCHDOG_CAPTURE_RECORD_INVALID')
                        raw = os.read(fd, 16385)
                    finally:
                        os.close(fd)
                    require(hashlib.sha256(raw).hexdigest() == finish[1].decode(), 'WATCHDOG_CAPTURE_DIGEST_CHANGED')
                    capture = json.loads(raw)
                    require(raw == canonical(capture) and set(capture) == {'bindingSha256','sourceRoot','destination','physical'} and
                            capture['bindingSha256'] == digest, 'WATCHDOG_CAPTURE_BINDING_CHANGED')
                    source = Path(capture['sourceRoot'])
                    destination = Path(capture['destination'])
                    require(source.resolve() == source and destination.resolve() == destination and
                            (source == mount or mount in source.parents) and source.stat().st_dev == mount.stat().st_dev and
                            destination.stat().st_dev == root.stat().st_dev and destination.stat().st_dev != source.stat().st_dev,
                            'WATCHDOG_CAPTURE_FILESYSTEM_CHANGED')
                    observe_mount(mount, binding['mount'])
                    require(time.clock_gettime(time.CLOCK_BOOTTIME) < deadline, 'WATCHDOG_LEASE_EXPIRED')
                    accepted = {'status':'COPY_ACCEPTED_UNDER_NATIVE_LEASE_PENDING_FORMAL_BARRIERS',
                                'bindingSha256':digest, 'captureSha256':finish[1].decode(),
                                'observedBootSeconds':time.clock_gettime(time.CLOCK_BOOTTIME), 'productionEvidence':False}
                    write_exclusive(root, '010-copy-accepted.json', accepted)
                    if time.clock_gettime(time.CLOCK_BOOTTIME) >= deadline:
                        accepted = None
                    break
                except (WatchdogError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
                    accepted = None
                    abort.append('capture-receipt-rejected')
                    break
            if data == b'THAW_VERIFIED_CANCEL\n' and not acquire and time.clock_gettime(time.CLOCK_BOOTTIME) < deadline:
                require(private_directory(root).stat().st_dev == identity[0] and root.stat().st_ino == identity[1],
                        'WATCHDOG_CONTROL_PATH_CHANGED')
                observe_mount(mount, binding['mount'])
                write_exclusive(root, '010-cancelled.json', {'status': 'CALLER_REPORTED_THAW_CANCELLED',
                    'bindingSha256': digest, 'observedBootSeconds': time.clock_gettime(time.CLOCK_BOOTTIME),
                    'notCaptureCompletion': True})
                return
            abort.append('invalid-owner-control')
    require(private_directory(root).stat().st_dev == identity[0] and root.stat().st_ino == identity[1],
            'WATCHDOG_CONTROL_PATH_CHANGED')
    # Invalidation is durable before thaw. Neither thaw success nor finished copy
    # can turn this operation into a successful capture.
    if accepted is None:
        write_exclusive(root, '010-invalidated.json', {'status': 'CAPTURE_INVALIDATED', 'bindingSha256': digest,
            'reason': abort[0] if abort else 'deadline', 'observedBootSeconds': time.clock_gettime(time.CLOCK_BOOTTIME)})
    observe_mount(mount, binding['mount'])
    result = subprocess.run(['fsfreeze', '--unfreeze', str(mount)], capture_output=True, timeout=5)
    require(result.returncode == 0, 'WATCHDOG_THAW_FAILED_RETAINED')
    write_exclusive(root, '020-thawed.json', {'status': 'THAWED_COPY_ACCEPTED_PENDING_FORMAL_BARRIERS' if accepted else 'THAWED_CAPTURE_REMAINS_INVALID',
        'bindingSha256': digest, 'observedBootSeconds': time.clock_gettime(time.CLOCK_BOOTTIME)})
    print('WATCHDOG_THAW_COPY_ACCEPTED_PENDING_FORMAL_BARRIERS' if accepted else 'WATCHDOG_THAW_CAPTURE_INVALIDATED', flush=True)


def require_uncancelled_lease(root, binding):
    """Expiry refusal only. This does not prove the actual kernel fence."""
    require_native_runtime()
    root = private_directory(root)
    require(not (root / '010-invalidated.json').exists() and not (root / '020-thawed.json').exists(),
            'WATCHDOG_CAPTURE_INVALIDATED')
    require(not (root / '010-cancelled.json').exists(), 'WATCHDOG_LEASE_CANCELLED')
    path = root / '000-ready.json'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= 16384 and stat.S_IMODE(info.st_mode) == 0o600,
                'WATCHDOG_RECORD_INVALID')
        data = os.read(fd, 16385)
    finally:
        os.close(fd)
    try:
        receipt = json.loads(data)
    except ValueError:
        raise WatchdogError('WATCHDOG_RECORD_INVALID') from None
    require(data == canonical(receipt) and receipt['binding'] == binding and
            receipt['bindingSha256'] == hashlib.sha256(canonical(binding)).hexdigest(), 'WATCHDOG_BINDING_CHANGED')
    require(binding['bootId'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'WATCHDOG_BOOT_CHANGED')
    require(time.clock_gettime(time.CLOCK_BOOTTIME) < receipt['deadlineBootSeconds'], 'WATCHDOG_LEASE_EXPIRED')
    require(not (root / '010-invalidated.json').exists(), 'WATCHDOG_CAPTURE_INVALIDATED')


def capture_physical_with_native_fence(control_root, mount, binding, source_root, destination, seconds, *, deadline=None, guard=None):
    """Actual finite native capture lifecycle; never full formal completion.

    Called only under separately authorized maintenance with all shared writers
    quiesced. Source/control/mount identity is required, not guessed. No Docker
    or database query is made while their shared filesystem might be frozen.
    """
    require_native_runtime()
    require(callable(guard), 'WATCHDOG_OWNER_GUARD_REQUIRED')
    import formal_snapshot_linux as snapshot
    outer = snapshot.observation_deadline.get()
    if outer is not None:deadline = min(deadline,outer) if deadline is not None else outer
    def check_owner():
        # The trusted caller checks only unfrozen control inputs here. SQL,
        # Docker and a post-thaw receipt are not available during this phase.
        snapshot.current_owner_guard(guard, code='WATCHDOG_OWNER_GUARD_REQUIRED')
    def remaining(seconds):
        check_owner()
        if deadline is None:return seconds
        require(type(deadline) in (int,float) and __import__('math').isfinite(deadline),'WATCHDOG_DEADLINE_INVALID')
        value=min(seconds,deadline-time.monotonic())
        require(value>0,'WATCHDOG_LEASE_EXPIRED')
        return value
    check_owner()
    root = Path(control_root).absolute()
    mount = Path(mount).absolute()
    source = Path(source_root).absolute()
    target = Path(destination).absolute()
    require(not root.exists() and not root.is_symlink(), 'WATCHDOG_EXISTING_EVIDENCE')
    require(root.parent.resolve() == root.parent and root.parent.is_dir(), 'WATCHDOG_CONTROL_PATH_INVALID')
    require(source.is_dir() and source.resolve() == source and (source == mount or mount in source.parents),
            'WATCHDOG_CAPTURE_SOURCE_INVALID')
    observe_mount(mount, binding['mount'],timeout=remaining(5))
    require(source.stat().st_dev == mount.stat().st_dev and root.parent.stat().st_dev != mount.stat().st_dev and
            target.parent.resolve() == target.parent and target.parent.stat().st_dev == root.parent.stat().st_dev,
            'WATCHDOG_CAPTURE_FILESYSTEM_CHANGED')
    require(not target.exists() and not target.is_symlink(), 'WATCHDOG_EXISTING_CAPTURE')
    if deadline is not None:
        require(remaining(7200)>seconds+12,'WATCHDOG_LEASE_EXPIRED')
    check_owner()
    from formal_capture_budget import active_budget
    output_budget=active_budget.get()
    if output_budget is None:root.mkdir(mode=0o700)
    else:
        output_budget.reserve_watchdog(root)
        output_budget.mkdir(root)
    check_owner()
    watchdog = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), str(root), str(mount), str(seconds),
                                 '--acquire-freeze'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        remaining(7200)
        watchdog.stdin.write(json.dumps(binding)+'\n'); watchdog.stdin.flush()
        ready_deadline = time.monotonic() + remaining(min(seconds + 6, 12))
        response = b''
        while b'\n' not in response:
            budget = min(remaining(7200), ready_deadline-time.monotonic())
            require(budget>0, 'WATCHDOG_ACQUIRE_NOT_ACKNOWLEDGED')
            ready, _, _ = select.select([watchdog.stdout], [], [], min(0.05, budget))
            if not ready:continue
            chunk = os.read(watchdog.stdout.fileno(), 128)
            require(chunk and len(response)+len(chunk)<=128, 'WATCHDOG_ACQUIRE_NOT_ACKNOWLEDGED')
            response += chunk
        require(response == b'WATCHDOG_READY_NOT_FENCE_PROOF\n', 'WATCHDOG_ACQUIRE_NOT_ACKNOWLEDGED')
        def fence_guard():
            remaining(7200)
            require(watchdog.poll() is None, 'WATCHDOG_PROCESS_LOST')
            require_uncancelled_lease(root, binding)
            remaining(7200)
        fence_guard()
        acquired = json.loads((root / '005-freeze-acquired.json').read_bytes())
        require(acquired['bindingSha256'] == hashlib.sha256(canonical(binding)).hexdigest(),
                'WATCHDOG_ACQUIRE_BINDING_CHANGED')
        token=snapshot.observation_deadline.set(deadline)
        try:
            from formal_capture_incremental import active_series
            series = active_series.get()
            if series is None:
                physical = snapshot.copy_physical_minio_tree(source, target, lease_guard=fence_guard)
            else:
                physical = series.files(source, target, guard=fence_guard)
        finally:snapshot.observation_deadline.reset(token)
        fence_guard()
        capture = {'bindingSha256':hashlib.sha256(canonical(binding)).hexdigest(),
                   'sourceRoot':str(source),'destination':str(target),'physical':physical}
        write_exclusive(root, 'physical-capture.json', capture)
        digest = hashlib.sha256(canonical(capture)).hexdigest()
        fence_guard()
        watchdog.stdin.write('CAPTURE_FINISH '+digest+'\n'); watchdog.stdin.flush()
        wait_deadline = time.monotonic() + remaining(seconds+6)
        while watchdog.poll() is None:
            budget=min(remaining(7200),wait_deadline-time.monotonic())
            require(budget>0,'WATCHDOG_LEASE_EXPIRED')
            try:watchdog.wait(timeout=min(0.05,budget))
            except subprocess.TimeoutExpired:continue
        remaining(7200)
        out, err = watchdog.communicate(timeout=remaining(2))
        remaining(7200)
        require(watchdog.returncode == 0 and not err and
                out.strip() == 'WATCHDOG_THAW_COPY_ACCEPTED_PENDING_FORMAL_BARRIERS' and
                not (root/'010-invalidated.json').exists(), 'WATCHDOG_CAPTURE_NOT_ACCEPTED')
        accepted = json.loads((root/'010-copy-accepted.json').read_bytes())
        thawed = json.loads((root/'020-thawed.json').read_bytes())
        require(accepted['captureSha256'] == digest and accepted['bindingSha256'] == capture['bindingSha256'] and
                thawed['bindingSha256'] == capture['bindingSha256'] and
                thawed['status'] == 'THAWED_COPY_ACCEPTED_PENDING_FORMAL_BARRIERS', 'WATCHDOG_CAPTURE_RECEIPT_CHANGED')
        remaining(7200)
        return {'state':'RAW_CAPTURED_AND_THAWED_PENDING_FORMAL_BARRIERS','physical':physical,
                'captureSha256':digest,'productionEvidence':False}
    except Exception as error:
        # Closing only this owner's pipe requests native invalidation and thaw;
        # do not kill the independent recovery process or claim restoration.
        uncertain = False
        try:
            if watchdog.stdin is not None and not watchdog.stdin.closed:
                watchdog.stdin.close(); watchdog.stdin = None
        except (OSError, ValueError):
            uncertain = True
        try:
            watchdog.wait(timeout=seconds+6)
        except subprocess.TimeoutExpired:
            uncertain = True
            try:
                write_exclusive(root, '900-owner-recovery-required.json', {'status':'RECOVERY_REQUIRED_NATIVE_PROCESS_UNCONFIRMED',
                    'bindingSha256':hashlib.sha256(canonical(binding)).hexdigest(),'productionEvidence':False})
            except OSError:
                error.evidenceWriteUncertain = True
        except OSError:
            uncertain = True
        if uncertain:error.ownerCleanupUncertain = True
        raise


def main():
    # Binding is private stdin; argv contains only the task-owned paths/deadline.
    require_native_runtime()
    require(len(sys.argv) == 4 or (len(sys.argv) == 5 and sys.argv[4] == '--acquire-freeze'),
            'WATCHDOG_ARGUMENTS_INVALID')
    line = sys.stdin.buffer.readline(16385)
    require(len(line) <= 16384 and line.endswith(b'\n'), 'WATCHDOG_INPUT_INVALID')
    try:
        binding = json.loads(line)
        seconds = int(sys.argv[3])
    except ValueError:
        raise WatchdogError('WATCHDOG_INPUT_INVALID') from None
    # Use the same unbuffered descriptor for binding and later cancellation/EOF.
    # Buffered readline may consume control bytes; the caller sends no control
    # message until READY. A single binding line is the only startup input.
    run_watchdog(sys.argv[1], sys.argv[2], binding, seconds, sys.stdin.fileno(), acquire=len(sys.argv) == 5)


if __name__ == '__main__':
    try:
        main()
    except WatchdogError as error:
        # Only module-owned fixed codes cross the CLI boundary, never private
        # input, paths or arbitrary exception text.
        code = error.code if re.fullmatch('WATCHDOG_[A-Z_]+', error.code) else 'WATCHDOG_FAILED_RETAINED'
        print(code, file=sys.stderr, flush=True)
        raise SystemExit(1)
    except (OSError, subprocess.SubprocessError, KeyError, TypeError):
        print('WATCHDOG_FAILED_RETAINED', file=sys.stderr, flush=True)
        raise SystemExit(1)
