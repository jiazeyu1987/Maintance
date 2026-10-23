"""Explicit task-owned Windows loopback -> pinned WSL business TCP; no Docker proxy.

Configuration and activation are supplied independently after runtime qualification.
--check never opens a socket, launches WSL, or joins a namespace.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import selectors
import socket
import subprocess
import sys
import threading
import time

TASK = '20261010-backup-restore-modular-development'
DISTRO = 'br20261010-w01w07-native'
WSL_ARGS = ['--distribution', DISTRO, '--user', 'root', '--exec']
DENIED_PORTS = {8081, 9000, 2375, 2376}


def need(value, code):
    if not value:
        raise RuntimeError(code)


def error_code(error):
    return str(error) if type(error) is RuntimeError and re.fullmatch('[A-Z][A-Z0-9_]{0,120}', str(error)) else type(error).__name__.upper()


def fields(value, names):
    need(type(value) is dict and set(value) == set(names.split()), 'LOOPBACK_FIELDS_INVALID')


def read_pin(reference):
    fields(reference, 'path bytes sha256')
    path = Path(reference['path'])
    need(type(reference['bytes']) is int and reference['bytes'] >= 0 and type(reference['sha256']) is str and
         len(reference['sha256']) == 64 and path.is_absolute() and path.resolve() == path and
         path.is_file() and not path.is_symlink(), 'LOOPBACK_PIN_INVALID')
    before = path.stat(); raw = path.read_bytes(); after = path.stat()
    key = lambda v: (v.st_dev, v.st_ino, v.st_size, v.st_mtime_ns, v.st_ctime_ns)
    need(key(before) == key(after) and path.resolve() == path and len(raw) == reference['bytes'] and
         hashlib.sha256(raw).hexdigest() == reference['sha256'], 'LOOPBACK_PIN_CHANGED')
    return raw


def parse(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            need(k not in result, 'LOOPBACK_DUPLICATE_JSON_KEY')
            result[k] = v
        return result
    need(len(raw) <= 1024 * 1024, 'LOOPBACK_DOCUMENT_SIZE_LIMIT')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(RuntimeError('LOOPBACK_INVALID_NUMBER')))


def document(reference):
    return parse(read_pin(reference))


def port(value):
    need(type(value) is int and 1024 <= value <= 65535 and value not in DENIED_PORTS, 'LOOPBACK_EXPLICIT_PRIVATE_PORT_REQUIRED')
    return value


def same_bytes(control, native):
    fields(native, 'path bytes sha256')
    need(control['bytes'] == native['bytes'] and control['sha256'] == native['sha256'] and
         type(native['path']) is str and native['path'].startswith('/') and '..' not in Path(native['path']).parts,
         'LOOPBACK_CONTROL_NATIVE_PIN_MISMATCH')


def binding(value, namespace_pin):
    fields(value, 'schemaVersion taskId sourceOrTargetRef role targetAddress targetPort namespaceRegistrationPin')
    need(value['schemaVersion'] == 'RecoveryControlBusinessService/v1' and value['taskId'] == TASK and
         value['role'] in ('ui', 'api', 'object') and value['targetAddress'] == '127.0.0.1' and
         value['namespaceRegistrationPin'] == namespace_pin, 'LOOPBACK_BUSINESS_BINDING_INVALID')
    fields(value['sourceOrTargetRef'], 'path bytes sha256')
    port(value['targetPort'])
    return value


def configuration(value):
    fields(value, 'schemaVersion taskId windowsHostIdentity windowsPythonPin windowsBridgePin launcherPin launcherArguments '
           'nativeConfigurationPath nativeBridgePin nativeExecutionProfilePin nativeExecutionProfileControlPin '
           'namespaceRegistrationControlPin activationPin activationControlPin endpoints connectionDeadlineMilliseconds '
           'maxConnectionBytes maxConnections')
    need(value['schemaVersion'] == 'RecoveryControlLoopbackConfiguration/v1' and value['taskId'] == TASK,
         'LOOPBACK_CONFIG_VERSION_INVALID')
    fields(value['windowsHostIdentity'], 'hostOs hostId bootId uid')
    need(value['windowsHostIdentity']['hostOs'] == 'Windows' and value['windowsHostIdentity']['uid'] is None and
         value['launcherArguments'] == WSL_ARGS and Path(value['launcherPin']['path']).name.lower() == 'wsl.exe',
         'LOOPBACK_FIXED_WSL_REQUIRED')
    need(type(value['nativeConfigurationPath']) is str and value['nativeConfigurationPath'].startswith('/') and
         '..' not in Path(value['nativeConfigurationPath']).parts, 'LOOPBACK_NATIVE_CONFIG_PATH_INVALID')
    for key, low, high in (('connectionDeadlineMilliseconds', 1000, 300000),
                           ('maxConnectionBytes', 1, 1024 * 1024 * 1024), ('maxConnections', 1, 64)):
        need(type(value[key]) is int and low <= value[key] <= high, 'LOOPBACK_FINITE_BUDGET_REQUIRED')
    need(type(value['endpoints']) is list and 1 <= len(value['endpoints']) <= 6, 'LOOPBACK_ENDPOINTS_REQUIRED')
    ids, ports = set(), set()
    for endpoint in value['endpoints']:
        fields(endpoint, 'endpointId listenAddress listenPort servicePin serviceControlPin')
        identifier = endpoint['endpointId']
        need(type(identifier) is str and identifier.isascii() and identifier.replace('-', '').isalnum() and
             1 <= len(identifier) <= 64 and identifier not in ids and endpoint['listenAddress'] == '127.0.0.1',
             'LOOPBACK_ENDPOINT_ID_OR_ADDRESS_INVALID')
        selected = port(endpoint['listenPort']); need(selected not in ports, 'LOOPBACK_PORT_COLLISION')
        ids.add(identifier); ports.add(selected)
        same_bytes(endpoint['serviceControlPin'], endpoint['servicePin'])
    for native, control in (('nativeExecutionProfilePin', 'nativeExecutionProfileControlPin'), ('activationPin', 'activationControlPin')):
        same_bytes(value[control], value[native])
    return value


def activation(value, config, namespace_pin):
    fields(value, 'schemaVersion taskId enabled validFromWallNs expiresWallNs namespaceRegistrationPin servicePins listenPorts')
    need(value['schemaVersion'] == 'RecoveryControlLoopbackActivation/v1' and value['taskId'] == TASK and
         value['enabled'] is True and type(value['validFromWallNs']) is int and type(value['expiresWallNs']) is int and
         value['validFromWallNs'] <= time.time_ns() < value['expiresWallNs'] and
         value['namespaceRegistrationPin'] == namespace_pin and
         value['servicePins'] == [e['servicePin'] for e in config['endpoints']] and
         value['listenPorts'] == [e['listenPort'] for e in config['endpoints']], 'LOOPBACK_ACTIVATION_NOT_RELEASED')


def load_dispatcher(profile):
    # Windows imports the same code from an explicit sibling only after its Pin is checked.
    # Native uses the trusted profile's dispatcher, never import search-path discovery.
    reference = profile['dispatcherPin']; read_pin(reference)
    spec = importlib.util.spec_from_file_location('w01_loopback_namespace_boundary', reference['path'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    read_pin(reference)
    return module


def windows_check(config):
    need(os.name == 'nt', 'LOOPBACK_WINDOWS_HOST_REQUIRED')
    read_pin(config['_configurationPin'])
    profile = document(config['nativeExecutionProfileControlPin'])
    need(profile.get('schemaVersion') == 'RecoveryControlExecutionHost/v2' and profile.get('transport') == 'WSL' and
         profile.get('launcherArguments') == WSL_ARGS and profile.get('launcherPin') == config['launcherPin'],
         'LOOPBACK_EXECUTION_PROFILE_MISMATCH')
    namespace_pin = profile['namespaceRegistrationPin']
    same_bytes(config['namespaceRegistrationControlPin'], namespace_pin)
    registration = document(config['namespaceRegistrationControlPin'])
    # Dispatcher may be native-only. Windows identity is obtained through this code's
    # explicitly pinned sibling, whose bytes must be the same native dispatcher bytes.
    local_dispatcher = Path(__file__).with_name('recovery_control_executor.py')
    local_pin = dict(path=local_dispatcher.as_posix(), bytes=namespace_bytes(local_dispatcher), sha256=file_sha(local_dispatcher))
    need(local_pin['bytes'] == profile['dispatcherPin']['bytes'] and local_pin['sha256'] == profile['dispatcherPin']['sha256'],
         'LOOPBACK_DISPATCHER_BYTES_MISMATCH')
    native = load_dispatcher({'dispatcherPin': local_pin})
    need(native.identity() == config['windowsHostIdentity'], 'LOOPBACK_WINDOWS_HOST_OR_BOOT_CHANGED')
    native.namespace_record(registration, {k: profile[k] for k in ('hostOs', 'hostId', 'bootId', 'uid')})
    for reference in (config['windowsPythonPin'], config['windowsBridgePin'], config['launcherPin']):
        read_pin(reference)
    need(Path(sys.executable).resolve() == Path(config['windowsPythonPin']['path']) and
         Path(__file__).resolve() == Path(config['windowsBridgePin']['path']), 'LOOPBACK_WINDOWS_EXECUTABLE_MISMATCH')
    need(config['windowsBridgePin']['bytes'] == config['nativeBridgePin']['bytes'] and
         config['windowsBridgePin']['sha256'] == config['nativeBridgePin']['sha256'], 'LOOPBACK_BRIDGE_BYTES_MISMATCH')
    activation(document(config['activationControlPin']), config, namespace_pin)
    for endpoint in config['endpoints']:
        binding(document(endpoint['serviceControlPin']), namespace_pin)
    return namespace_pin


def namespace_bytes(path):
    return Path(path).stat().st_size


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_check(config):
    need(sys.platform == 'linux', 'LOOPBACK_NATIVE_LINUX_REQUIRED')
    read_pin(config['_configurationPin'])
    profile = document(config['nativeExecutionProfilePin'])
    native = load_dispatcher(profile)
    native.execution_profile(profile, native.identity())
    need(Path(sys.executable).resolve() == Path(profile['pythonPin']['path']) and
         Path(__file__).resolve() == Path(config['nativeBridgePin']['path']) and profile['launcherArguments'] == WSL_ARGS,
         'LOOPBACK_NATIVE_EXECUTABLE_MISMATCH')
    for reference in (profile['pythonPin'], config['nativeBridgePin']):
        read_pin(reference)
    namespace = native.NativeNamespace(profile)
    try:
        proof = namespace.enter()
        activation(document(config['activationPin']), config, profile['namespaceRegistrationPin'])
        for endpoint in config['endpoints']:
            service = binding(document(endpoint['servicePin']), profile['namespaceRegistrationPin'])
            native.document(service['sourceOrTargetRef'])
        namespace.recheck(True)
        return native, namespace, proof
    except BaseException:
        namespace.close(); raise


def ready(config, proof, endpoint=None):
    return dict(schemaVersion='RecoveryControlLoopbackReady/v1', taskId=TASK,
                configurationSha256=config['_configurationSha256'], namespaceEntry=proof,
                endpointId=None if endpoint is None else endpoint['endpointId'],
                servicePin=None if endpoint is None else endpoint['servicePin'])


def native_peer(config, endpoint_id, check_only):
    # Remove local bookkeeping before exact configuration validation is reused.
    native, namespace, proof = native_check(config)
    try:
        endpoint = None if check_only else next(e for e in config['endpoints'] if e['endpointId'] == endpoint_id)
        if check_only:
            print(json.dumps(ready(config, proof), separators=(',', ':')), flush=True); return
        service = document(endpoint['servicePin'])
        deadline = time.monotonic() + config['connectionDeadlineMilliseconds'] / 1000
        with socket.create_connection((service['targetAddress'], service['targetPort']), timeout=min(5, deadline-time.monotonic())) as target:
            namespace.recheck(True)
            print(json.dumps(ready(config, proof, endpoint), separators=(',', ':')), flush=True)
            # Each connection is a single bounded bidirectional relay in the joined thread.
            inputs = sys.stdin.buffer.fileno(); outputs = sys.stdout.buffer.fileno()
            target.setblocking(False); os.set_blocking(inputs, False); os.set_blocking(outputs, False)
            to_target, to_output = bytearray(), bytearray(); total = 0; input_open = target_open = True
            next_check = 0
            with selectors.DefaultSelector() as selector:
                while target_open or to_output:
                    now = time.monotonic(); need(now < deadline, 'LOOPBACK_CONNECTION_DEADLINE')
                    if now >= next_check:
                        namespace.recheck(True); activation(document(config['activationPin']), config, proof['namespaceRegistrationPin'])
                        read_pin(config['_configurationPin']); read_pin(config['nativeExecutionProfilePin'])
                        read_pin(endpoint['servicePin']); native.document(service['sourceOrTargetRef']); next_check = now + 1
                    for key in list(selector.get_map().values()): selector.unregister(key.fileobj)
                    if input_open and len(to_target) < 65536: selector.register(inputs, selectors.EVENT_READ, 'input')
                    mask = (selectors.EVENT_READ if target_open and len(to_output) < 65536 else 0) | (selectors.EVENT_WRITE if to_target else 0)
                    if mask: selector.register(target, mask, 'target')
                    if to_output: selector.register(outputs, selectors.EVENT_WRITE, 'output')
                    for key, mask in selector.select(min(0.25, deadline-now)):
                        if key.data == 'input':
                            data = os.read(inputs, 65536)
                            if not data: input_open = False
                            else: to_target.extend(data); total += len(data)
                        elif key.data == 'output':
                            count = os.write(outputs, to_output); del to_output[:count]
                        else:
                            if mask & selectors.EVENT_READ:
                                data = target.recv(65536)
                                if not data: target_open = False
                                else: to_output.extend(data); total += len(data)
                            if mask & selectors.EVENT_WRITE and to_target:
                                count = target.send(to_target); del to_target[:count]
                        need(total <= config['maxConnectionBytes'], 'LOOPBACK_CONNECTION_BYTE_LIMIT')
                    if input_open is False and not to_target:
                        target.shutdown(socket.SHUT_WR); input_open = None
            namespace.recheck(True)
    finally:
        namespace.close()


def command(config, endpoint=None):
    profile = document(config['nativeExecutionProfileControlPin'])
    args = [config['launcherPin']['path'], *WSL_ARGS, profile['pythonPin']['path'], '-I', '-B',
            config['nativeBridgePin']['path'], '--config', config['nativeConfigurationPath'],
            '--config-sha256', config['_configurationSha256']]
    return args + (['--check-native'] if endpoint is None else ['--peer', endpoint['endpointId']])


def launch(config, endpoint=None):
    need(os.environ.get('SystemRoot'), 'LOOPBACK_SYSTEM_ROOT_REQUIRED')
    return subprocess.Popen(command(config, endpoint), env={'SystemRoot': os.environ['SystemRoot']},
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)


def handshake(process, config, namespace_pin, endpoint=None):
    values = []; done = threading.Event()
    def read():
        try: values.append(process.stdout.readline(65537))
        except OSError: values.append(b'')
        finally: done.set()
    thread = threading.Thread(target=read, daemon=True); thread.start()
    need(done.wait(min(10, config['connectionDeadlineMilliseconds']/1000)), 'LOOPBACK_READY_DEADLINE')
    raw = values[0]; need(len(raw) <= 65536 and raw.endswith(b'\n'), 'LOOPBACK_READY_MISSING')
    value = parse(raw)
    fields(value, 'schemaVersion taskId configurationSha256 namespaceEntry endpointId servicePin')
    need(value['schemaVersion'] == 'RecoveryControlLoopbackReady/v1' and value['taskId'] == TASK and
         value['configurationSha256'] == config['_configurationSha256'] and
         value['endpointId'] == (None if endpoint is None else endpoint['endpointId']) and
         value['servicePin'] == (None if endpoint is None else endpoint['servicePin']), 'LOOPBACK_READY_BINDING_MISMATCH')
    proof = value['namespaceEntry']; fields(proof, 'schemaVersion namespaceRegistrationPin hostId bootId daemon namespaces enteredMonotonicNs')
    registration = document(config['namespaceRegistrationControlPin'])
    need(proof['schemaVersion'] == 'RecoveryControlNamespaceEntry/v1' and proof['namespaceRegistrationPin'] == namespace_pin and
         all(proof[k] == registration[k] for k in ('hostId', 'bootId', 'daemon', 'namespaces')) and
         type(proof['enteredMonotonicNs']) is int and proof['enteredMonotonicNs'] > 0, 'LOOPBACK_NAMESPACE_PROOF_MISMATCH')


def relay(client, endpoint, config, namespace_pin):
    process = None; done = threading.Event(); errors = []; total = [0]; lock = threading.Lock()
    try:
        windows_check(config); process = launch(config, endpoint)
        handshake(process, config, namespace_pin, endpoint)
        deadline = time.monotonic() + config['connectionDeadlineMilliseconds']/1000
        def copy_input():
            try:
                while not done.is_set():
                    data = client.recv(65536)
                    if not data: break
                    with lock:
                        total[0] += len(data); need(total[0] <= config['maxConnectionBytes'], 'LOOPBACK_CONNECTION_BYTE_LIMIT')
                    process.stdin.write(data); process.stdin.flush()
                process.stdin.close()
            except Exception as error: errors.append(type(error).__name__); done.set()
        threading.Thread(target=copy_input, daemon=True).start()
        def copy_output():
            try:
                while not done.is_set():
                    data = process.stdout.read1(65536)
                    if not data: break
                    with lock:
                        total[0] += len(data); need(total[0] <= config['maxConnectionBytes'], 'LOOPBACK_CONNECTION_BYTE_LIMIT')
                    client.sendall(data)
            except Exception as error: errors.append(type(error).__name__)
            finally: done.set()
        threading.Thread(target=copy_output, daemon=True).start()
        while not done.wait(0.25):
            need(time.monotonic() < deadline, 'LOOPBACK_CONNECTION_DEADLINE'); windows_check(config)
        need(not errors, 'LOOPBACK_TRANSPORT_IO_FAILED')
        need(process.wait(timeout=5) == 0, 'LOOPBACK_NATIVE_PEER_FAILED')
    finally:
        done.set(); client.close()
        if process is not None:
            # Stops this connection's Windows transport only; never claims native/resource terminal proof.
            if process.poll() is None: process.kill(); process.wait(timeout=5)
            process.stdin.close(); process.stdout.close()


def serve(config):
    namespace_pin = windows_check(config); probe = launch(config)
    try:
        handshake(probe, config, namespace_pin)
        need(probe.wait(timeout=5) == 0, 'LOOPBACK_NATIVE_QUALIFICATION_FAILED')
    finally:
        if probe.poll() is None: probe.kill(); probe.wait(timeout=5)
        probe.stdin.close(); probe.stdout.close()
    listeners = []; workers = []; failures = []
    def worker(client, endpoint):
        try: relay(client, endpoint, config, namespace_pin)
        except Exception as error:
            failures.append(type(error).__name__)
            print('CONTROL_LOOPBACK_CONNECTION_' + error_code(error), file=sys.stderr, flush=True)
    try:
        for endpoint in config['endpoints']:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listeners.append((listener, endpoint))
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind(('127.0.0.1', endpoint['listenPort'])); listener.listen(config['maxConnections'])
        while True:
            windows_check(config); need(not failures, 'LOOPBACK_CONNECTION_FAILED')
            workers[:] = [t for t in workers if t.is_alive()]
            ready_sockets = select.select([s for s, e in listeners], [], [], 0.25)[0]
            for listener in ready_sockets:
                need(len(workers) < config['maxConnections'], 'LOOPBACK_CONNECTION_LIMIT')
                client, _ = listener.accept()
                endpoint = next(e for s, e in listeners if s is listener)
                thread = threading.Thread(target=worker, args=(client, endpoint), daemon=True)
                workers.append(thread); thread.start()
    finally:
        for listener, _ in listeners: listener.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True); parser.add_argument('--config-sha256', required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true'); mode.add_argument('--serve', action='store_true')
    mode.add_argument('--check-native', action='store_true'); mode.add_argument('--peer')
    args = parser.parse_args()
    try:
        path = Path(args.config)
        raw = read_pin(dict(path=path.as_posix(), bytes=path.stat().st_size, sha256=args.config_sha256))
        config = configuration(parse(raw)); config['_configurationSha256'] = args.config_sha256
        config['_configurationPin'] = dict(path=path.as_posix(), bytes=len(raw), sha256=args.config_sha256)
        if args.check:
            windows_check(config); print('CONTROL_LOOPBACK_CONFIG_CHECKED_NO_RUNTIME_START')
        elif args.serve: serve(config)
        else: native_peer(config, args.peer, args.check_native)
        return 0
    except Exception as error:
        print('CONTROL_LOOPBACK_' + error_code(error), file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
