"""Container creation preserves explicit target settings and rejects drift."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
from recovery_engine import RecoveryError
from recovery_program_containers import create_request, verify_created, snapshot


def original():
    return dict(Id='a'*64, Name='/program-backend', Image='sha256:'+'1'*64,
        Path='/bin/sh', Args=['-c', 'sleep 600'],
        Config=dict(Hostname='program', Image='old:version', Env=['APP=target'],
            Cmd=['-c', 'sleep 600'], Entrypoint=['/bin/sh'], Labels={'owner': 'task'}, Volumes=None),
        HostConfig=dict(Privileged=False, AutoRemove=False, NetworkMode='task-network',
            Binds=['/target/data:/data:rw'], Mounts=[], PortBindings={'8080/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '18000'}]}),
        Mounts=[dict(Type='bind', Source='/target/data', Destination='/data', RW=True,
                     Mode='rw', Propagation='rprivate')],
        State=dict(Running=False, Paused=False, Restarting=False, Dead=False),
        NetworkSettings=dict(Networks={'task-network': dict(NetworkID='f'*64,
            IPAMConfig={'IPv4Address': '172.29.1.20'}, Aliases=['program-backend', 'a'*12],
            Links=None, DriverOpts=None, IPAddress='172.29.1.20', GlobalIPv6Address='')}))


def image():
    return dict(Id='sha256:'+'2'*64, Os='linux', Architecture='amd64',
                Config=dict(Env=[], Labels={}, Volumes=None), RootFS=dict(Type='layers', Layers=[]))


def created(request):
    row = original()
    row.update(Id='b'*64, Image=image()['Id'], Config=deepcopy(request['Config']), HostConfig=deepcopy(request['HostConfig']))
    row['NetworkSettings']['Networks']['task-network']['Aliases'] = ['program-backend', 'b'*12]
    return row


def test_create_keeps_target_credentials_ports_mounts_and_command():
    before = original(); kept = deepcopy(before)
    request = create_request(before, image())
    assert before == kept
    assert request['Config'] == dict(before['Config'], Image=image()['Id'])
    assert request['HostConfig'] == before['HostConfig']
    endpoint = request['NetworkingConfig']['EndpointsConfig']['task-network']
    assert endpoint == dict(IPAMConfig={'IPv4Address': '172.29.1.20'}, Aliases=['program-backend'], Links=None, DriverOpts=None)
    verify_created(before, request, created(request))


@pytest.mark.parametrize('field', ['Running', 'Paused', 'Restarting', 'Dead'])
def test_original_must_be_stopped_and_stable(field):
    row = original(); row['State'][field] = True
    with pytest.raises(RecoveryError, match='PROGRAM_ORIGINAL_NOT_STOPPED'):
        create_request(row, image())


@pytest.mark.parametrize('field', ['Privileged', 'AutoRemove'])
def test_unsafe_or_disappearing_container_refused(field):
    row = original(); row['HostConfig'][field] = True
    with pytest.raises(RecoveryError, match='PROGRAM_HOST_CONFIGURATION_INVALID'):
        create_request(row, image())


def test_implicit_volume_cannot_create_empty_replacement_data():
    row = original(); row['HostConfig']['Binds'] = []
    with pytest.raises(RecoveryError, match='PROGRAM_MOUNT_NOT_EXPLICIT'):
        create_request(row, image())


def test_new_image_implicit_volume_is_rejected():
    archived = image(); archived['Config']['Volumes'] = {'/new-data': {}}
    with pytest.raises(RecoveryError, match='PROGRAM_IMAGE_IMPLICIT_VOLUME'):
        create_request(original(), archived)


def test_image_environment_and_labels_are_explicitly_merged():
    archived = image(); archived['Config'].update(Env=['NEW=from-image', 'APP=image'], Labels={'version': 'old', 'owner': 'image'})
    request = create_request(original(), archived)
    assert request['Config']['Env'] == ['NEW=from-image', 'APP=target']
    assert request['Config']['Labels'] == {'version': 'old', 'owner': 'task'}


@pytest.mark.parametrize('mutation', [
    lambda row: row.update(Image='sha256:'+'3'*64),
    lambda row: row.update(Id='a'*64),
    lambda row: row.update(Name='/another-program'),
    lambda row: row['Config'].update(Env=['APP=other']),
    lambda row: row['HostConfig'].update(Binds=['/other:/data:rw']),
    lambda row: row['Mounts'][0].update(Source='/other'),
    lambda row: row['State'].update(Running=True),
    lambda row: row['NetworkSettings']['Networks']['task-network']['IPAMConfig'].update(IPv4Address='172.29.1.21'),
    lambda row: row['NetworkSettings']['Networks']['task-network'].update(NetworkID='e'*64),
    lambda row: row['NetworkSettings']['Networks']['task-network'].update(Aliases=['unexpected']),
])
def test_created_drift_never_passes(mutation):
    before = original(); request = create_request(before, image()); after = created(request); mutation(after)
    with pytest.raises(RecoveryError, match='PROGRAM_CREATED_'):
        verify_created(before, request, after)


def test_snapshot_ignores_lifecycle_counters_but_keeps_configuration():
    before = original(); after = deepcopy(before)
    after['State']['FinishedAt'] = 'later'
    assert snapshot(before) == snapshot(after)
    after['Config']['Env'] = ['APP=changed']
    assert snapshot(before) != snapshot(after)


def test_creation_canonicalizes_explicit_nullable_oom_setting():
    before = original(); before['HostConfig']['OomKillDisable'] = None
    assert create_request(before, image())['HostConfig']['OomKillDisable'] is False


def test_unstarted_network_requires_independent_network_identity():
    before = original(); request = create_request(before, image()); row = created(request)
    row['State']['Status'] = 'created'
    row['NetworkSettings']['Networks']['task-network']['NetworkID'] = ''
    with pytest.raises(RecoveryError, match='PROGRAM_CREATED_NETWORK_CHANGED'):
        verify_created(before, request, row)
    verify_created(before, request, row, networks={'task-network': {'Id': 'f'*64, 'Name': 'task-network'}})


def test_desktop_managed_creation_label_needs_exact_platform_and_created_state():
    before = original(); before['Config']['Labels']['desktop.docker.io/ports.scheme'] = 'v2'
    request = create_request(before, image()); row = created(request)
    del row['Config']['Labels']['desktop.docker.io/ports.scheme']
    row['State']['Status'] = 'created'
    with pytest.raises(RecoveryError, match='PROGRAM_CREATED_CONFIGURATION_CHANGED'):
        verify_created(before, request, row)
    verify_created(before, request, row, engine_metadata={'OperatingSystem': 'Docker Desktop'})
    row['State']['Status'] = 'exited'
    with pytest.raises(RecoveryError, match='PROGRAM_CREATED_CONFIGURATION_CHANGED'):
        verify_created(before, request, row, engine_metadata={'OperatingSystem': 'Docker Desktop'})


@pytest.mark.parametrize('port', ['0', '', '70000'])
def test_dynamic_or_invalid_published_port_refused(port):
    before = original(); before['HostConfig']['PortBindings']['8080/tcp'][0]['HostPort'] = port
    with pytest.raises(RecoveryError, match='PROGRAM_FIXED_PORT_REQUIRED'):
        create_request(before, image())


def test_publish_all_cannot_reassign_application_ports():
    before = original(); before['HostConfig']['PublishAllPorts'] = True
    with pytest.raises(RecoveryError, match='PROGRAM_FIXED_PORT_REQUIRED'):
        create_request(before, image())
