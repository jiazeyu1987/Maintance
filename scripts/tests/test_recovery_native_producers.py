"""Local producer refusal/status tests; not Linux/runtime acceptance evidence."""
from copy import deepcopy
from pathlib import Path
import os
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))
from recovery_environment_contract import EnvironmentFailure
from recovery_native_process import IndependentAuthoritySigner, NativeProcessProducer, terminal_status
from recovery_native_service_identity import probe_commands, validate_observations
from recovery_native_signer import verify_parent_terminal


def terminal(status=0, code=0):
    return {'workerPid': 123, 'actualExitCode': code,
            'unknown': False, 'treeTerminated': True,
            'children': [{'pid': 123, 'actualWaitStatus': status, 'reaped': True}]}


@pytest.mark.parametrize('status,kind,code', [(0, 'EXITED', 0), (768, 'EXITED', 3), (9, 'SIGNALED', -9)])
def test_actual_wait_decoding_keeps_nonzero_and_signal(status, kind, code):
    assert terminal_status(terminal(status, code), 0) == (kind, status, code, 'REAPED')


@pytest.mark.parametrize('damage', ['lost-supervisor', 'unknown', 'wrong-exit', 'missing-wait'])
def test_missing_original_never_infers_zero(damage):
    record = terminal()
    supervisor_exit = 0
    if damage == 'lost-supervisor': supervisor_exit = 1
    if damage == 'unknown': record['unknown'] = True
    if damage == 'wrong-exit': record['actualExitCode'] = 4
    if damage == 'missing-wait': del record['children'][0]['actualWaitStatus']
    assert terminal_status(record, supervisor_exit) == ('UNKNOWN', None, None, 'UNKNOWN')


def test_remaining_child_does_not_establish_reap():
    record = terminal()
    record['children'].append({'pid': 124, 'reaped': False})
    record['treeTerminated'] = False
    assert terminal_status(record, 0)[3] == 'UNKNOWN'


@pytest.mark.parametrize('status', [128, 65535, 4991, 32777, -1, 65536])
def test_nonterminal_or_malformed_linux_wait_status_is_unknown(status):
    assert terminal_status(terminal(status), 0) == ('UNKNOWN', None, None, 'UNKNOWN')


@pytest.mark.parametrize('damage', ['argv', 'cwd', 'start', 'namespace', 'wait'])
def test_a_signer_rejects_changed_independent_parent_original(damage):
    payload = {'supervisorPid': 122, 'supervisorStartTicks': 10, 'childPid': 123, 'childStartTicks': 11,
               'uid': 24001, 'gid': 24000, 'bootId': 'boot', 'pidNamespace': 'pid:1',
               'mountNamespace': 'mnt:2', 'networkNamespace': 'net:3', 'userNamespace': 'user:4',
               'argv': ['/usr/bin/tool'], 'cwd': '/lab', 'stdoutPin': {'a': 1}, 'stderrPin': {'b': 2},
               'terminationKind': 'EXITED', 'waitStatus': 0, 'actualExitCode': 0, 'descendantState': 'REAPED'}
    term = dict(terminal(), model='linux-owned-child-subreaper-v1', supervisorPid=122,
                supervisorIdentity={'startTicks': 10, 'uid': 24001, 'gid': 24000, 'bootId': 'boot',
                    'namespaces': {'pid': 'pid:1', 'mnt': 'mnt:2', 'net': 'net:3', 'user': 'user:4'}},
                dispatch={'argv': ['/usr/bin/tool'], 'cwd': '/lab', 'uid': 24001, 'gid': 24000})
    term['children'][0]['startTicks'] = 11
    term['children'][0].update(uid=24001, gid=24000)
    original = {'terminal': term, 'supervisorExitCode': 0, 'failureCode': None,
                'stdoutPin': {'a': 1}, 'stderrPin': {'b': 2}}
    if damage == 'argv': term['dispatch']['argv'] = ['/usr/bin/other']
    if damage == 'cwd': term['dispatch']['cwd'] = '/other'
    if damage == 'start': term['children'][0]['startTicks'] = 12
    if damage == 'namespace': term['supervisorIdentity']['namespaces']['net'] = 'net:other'
    if damage == 'wait': term['children'][0]['actualWaitStatus'] = 768
    with pytest.raises(EnvironmentFailure):
        verify_parent_terminal(payload, original)


def test_docker_identity_commands_are_fixed_readonly_projections():
    commands = probe_commands({'path': '/usr/bin/docker'}, 'a' * 64, 'b' * 64)
    assert all(command[:3] == ['/usr/bin/docker', '--host', 'unix:///var/run/docker.sock'] for command in commands)
    assert commands[0][3:5] == ['info', '--format']
    assert commands[1][3:5] == ['inspect', '--format']
    assert commands[2][3:6] == ['network', 'inspect', '--format']
    assert all('.Env' not in ' '.join(command) and '.Health' not in ' '.join(command) for command in commands)
    assert commands[1][-1] == 'a' * 64 and commands[2][-1] == 'b' * 64


@pytest.mark.parametrize('value', ['name', 'abc', '--privileged', 'a' * 63, 'A' * 64])
def test_no_container_name_discovery_or_option_injection(value):
    with pytest.raises(EnvironmentFailure, match='NATIVE_SERVICE_FULL_ID_REQUIRED'):
        probe_commands({'path': '/usr/bin/docker'}, value, 'b' * 64)


def observations():
    labels = {'intruoyi.recovery.target': 't', 'intruoyi.recovery.operation': 'op'}
    endpoint = {'Name': 'brlab-20261012-app', 'EndpointID': 'endpoint', 'IPv4Address': '10.9.0.2/24', 'IPv6Address': ''}
    service = {'id': 'a' * 64, 'imageId': 'sha256:image', 'name': '/brlab-20261012-app'}
    network = {'networkId': 'b' * 64, 'name': 'brlab-20261012-net'}
    actual = {'Id': service['id'], 'Image': service['imageId'], 'Name': service['name'],
              'State': {'Running': True}, 'Config': {'Labels': labels},
              'NetworkSettings': {'Networks': {network['name']: {'NetworkID': network['networkId'],
                    'EndpointID': endpoint['EndpointID'], 'IPAddress': '10.9.0.2'}}}}
    inspected_network = {'Id': network['networkId'], 'Containers': {service['id']: endpoint}}
    args = dict(target={'targetId': 't', 'dockerEngineId': 'engine'}, service=service, network=network,
                endpoint=endpoint, address='10.9.0.2', operation_id='op')
    return {'ID': 'engine'}, [actual], [inspected_network], args


@pytest.mark.parametrize('damage', ['stopped', 'image', 'operation', 'engine', 'endpoint', 'network', 'env'])
def test_changed_protected_identity_is_rejected(damage):
    info, inspected, networks, args = observations()
    if damage == 'stopped': inspected[0]['State']['Running'] = False
    if damage == 'image': inspected[0]['Image'] = 'sha256:other'
    if damage == 'operation': inspected[0]['Config']['Labels'] = {'intruoyi.recovery.target': 't', 'intruoyi.recovery.operation': 'other'}
    if damage == 'engine': info['ID'] = 'other'
    if damage == 'endpoint': inspected[0]['NetworkSettings']['Networks']['brlab-20261012-net']['EndpointID'] = 'other'
    if damage == 'network': networks[0]['Id'] = 'c' * 64
    if damage == 'env': inspected[0]['Config']['Env'] = ['PASSWORD=never-persist']
    with pytest.raises(EnvironmentFailure):
        validate_observations(info, inspected, networks, **args)


def test_worker_cannot_share_signer_uid():
    def unreachable(*_):
        raise AssertionError('No guard or runtime selection may execute for the same UID')
    signer = IndependentAuthoritySigner('/not-opened', 1, 2, 24110, {}, unreachable, unreachable,
                                       peer_gid=24110, runtime_selector=unreachable)
    with pytest.raises(EnvironmentFailure, match='NATIVE_SIGNER_ROLE_NOT_SEPARATE'):
        signer.check_worker(24110, {})


@pytest.mark.parametrize('uid', [0, 24001])
def test_worker_uid_never_substitutes_for_measured_key_denial(uid):
    def unreachable(*_):
        raise AssertionError('No runtime admission is performed by this denial check')
    signer = IndependentAuthoritySigner('/not-opened', 1, 2, 24110, {}, unreachable, lambda *_: False,
                                       peer_gid=24110, runtime_selector=unreachable)
    with pytest.raises(EnvironmentFailure, match='NATIVE_WORKER_KEY_ACCESS_NOT_DENIED'):
        signer.check_worker(uid, {})


def test_missing_independent_key_denial_guard_is_a_failed_prerequisite():
    with pytest.raises(EnvironmentFailure, match='NATIVE_WORKER_KEY_DENIAL_GUARD_REQUIRED'):
        IndependentAuthoritySigner('/not-opened', 1, 2, 24110, {}, lambda: None, None,
                                   peer_gid=24110, runtime_selector=None)


def test_producer_consumer_literal_docker_projection_alignment():
    import ast
    consumer = Path(__file__).resolve().parents[2] / 'scripts/recovery_verification/service_identity.py'
    tree = ast.parse(consumer.read_text(encoding='utf-8'))
    selected = [node for node in tree.body if
                isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in
                    ('INFO_FORMAT', 'INSPECT_FORMAT', 'NETWORK_FORMAT') for t in node.targets) or
                isinstance(node, ast.FunctionDef) and node.name == 'native_identity_argv']
    namespace = {'need': lambda condition, *_: condition or pytest.fail('consumer rejected verb')}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(consumer), 'exec'), namespace)
    expected = [namespace['native_identity_argv']('/usr/bin/docker', verb, 'a' * 64, 'b' * 64)
                for verb in ('info', 'inspect', 'network')]
    assert probe_commands({'path': '/usr/bin/docker'}, 'a' * 64, 'b' * 64) == expected


@pytest.mark.skipif(sys.platform == 'linux', reason='This refusal targets the local Windows host')
def test_windows_cannot_publish_a_native_linux_original():
    with pytest.raises(EnvironmentFailure, match='NATIVE_LINUX_REQUIRED'):
        NativeProcessProducer(evidence_root='.', installation_pin={}, authority_pin={}, signer=None,
            authority_guard=None, dispatch_guard=None, worker_uid=1, worker_gid=1, deadline=0)
