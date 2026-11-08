"""Explicit Linux/Docker integration, run only in a task-owned test container."""
from copy import deepcopy
from contextlib import nullcontext
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
from recovery_engine import pin, write, RecoveryError
from recovery_backup_epoch import initialize, begin_restore
from recovery_program_containers import UnixDocker, switch_stopped_programs


def main():
    import fcntl
    prefix = 'spug-program-check-'+uuid.uuid4().hex[:16]
    engine = UnixDocker(guard=lambda: None, deadline=time.monotonic()+240, api_version=os.environ['PROGRAM_TEST_API'])
    containers, images, networks, volumes = [], [], [], []
    result = dict(schemaVersion='ProgramSwitchNativeCheck/v1', state='RUNNING', prefix=prefix)
    try:
        base = os.environ['PROGRAM_TEST_BASE_IMAGE']
        engine.image(base)
        for version in ('CURRENT', 'ARCHIVED'):
            seed = engine.request('POST', '/containers/create?name='+prefix+'-'+version.lower(),
                dict(Image=base, Entrypoint=['/bin/sh'], Cmd=['-ec', 'printf '+version+' > /program-version'],
                    Labels={'spug.program.integration': prefix},
                    HostConfig=dict(NetworkMode='none', AutoRemove=False)))['Id']
            containers.append(seed)
            engine.request('POST', '/containers/'+seed+'/start')
            assert engine.request('POST', '/containers/'+seed+'/wait?condition=not-running')['StatusCode'] == 0
            image_id = engine.request('POST', '/commit?container='+seed+'&pause=false&repo='+prefix+'&tag='+version.lower())['Id']
            images.append(image_id)
        network_name = prefix+'-net'
        network = engine.request('POST', '/networks/create', dict(Name=network_name, Driver='bridge',
            Internal=True, Labels={'spug.program.integration': prefix}))['Id']
        networks.append(network)
        network_config = engine.network(network)
        subnet = ipaddress.ip_network(network_config['IPAM']['Config'][0]['Subnet'])
        target_addresses = {role: str(subnet.network_address+index+2) for index, role in enumerate(('backend','frontend'))}
        target_ports = {role: str(44000+int(prefix[-4:],16)%15000+index) for index, role in enumerate(('backend','frontend'))}
        volume = engine.request('POST', '/volumes/create', dict(Name=prefix+'-data', Labels={'spug.program.integration': prefix}))['Name']
        volumes.append(volume)
        originals = {}
        for role in ('backend', 'frontend'):
            identity = engine.request('POST', '/containers/create?name='+prefix+'-'+role,
                dict(Image=images[0], Hostname=prefix+'-'+role, Entrypoint=['/bin/sh'], Cmd=['-ec', 'sleep 180'],
                    Env=['APPLICATION_ENDPOINT=retained-target'], Labels={'spug.program.integration': prefix},
                    HostConfig=dict(NetworkMode=network_name, AutoRemove=False, Privileged=False,
                        Binds=[volume+':/data:rw'], RestartPolicy={'Name': 'no', 'MaximumRetryCount': 0},
                        PortBindings={'80/tcp':[{'HostIp':'127.0.0.1','HostPort':target_ports[role]}]}),
                    NetworkingConfig=dict(EndpointsConfig={network_name: dict(Aliases=[role],
                        IPAMConfig={'IPv4Address':target_addresses[role]})})))['Id']
            containers.append(identity)
            # Exercise real previously running applications, then the caller's
            # explicit stopped state; the switch itself must never start them.
            engine.request('POST', '/containers/'+identity+'/start')
            if role == 'backend':
                command = engine.request('POST', '/containers/'+identity+'/exec', dict(AttachStdout=False,
                    AttachStderr=False, Cmd=['/bin/sh','-ec','printf ORIGINAL-TARGET-DATA > /data/sentinel']))['Id']
                engine.request('POST', '/exec/'+command+'/start', dict(Detach=True,Tty=False))
                until = time.monotonic()+10
                while True:
                    checked = engine.request('GET','/exec/'+command+'/json')
                    if not checked['Running']: break
                    assert time.monotonic() < until
                    time.sleep(.05)
                assert checked['ExitCode'] == 0
            engine.request('POST', '/containers/'+identity+'/stop?t=2')
            originals[role] = engine.inspect(identity)
        archived = engine.image(images[1])
        program = dict(schemaVersion='ArchivedProgramImages/v1', archivePin=None, images=[dict(role=role,
            imageId=archived['Id'], os=archived['Os'], architecture=archived['Architecture'],
            diffIds=archived['RootFS']['Layers']) for role in originals])
        with nullcontext(tempfile.mkdtemp(prefix='program-epoch-')) as directory:
            root = Path(directory); epoch_root = root/'epoch'; epoch_root.mkdir(mode=0o700)
            lock_path = root/'source.lock'; lock_path.touch(mode=0o600)
            policy = dict(schemaVersion='SourceBackupEpochPolicy/v1', root=str(epoch_root), sourceIdentity='native-program-test',
                databaseUuid='11111111-1111-1111-1111-111111111111', sourceLockPath=str(lock_path))
            operation = 'program-'+uuid.uuid4().hex
            lock_fd = os.open(lock_path, os.O_RDWR)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                initialize(policy, lock_fd); begin_restore(policy, operation, lock_fd)
                effects = []
                real_request = engine.request
                def tracked(method, path, body=None):
                    if method != 'GET': effects.append((method, path))
                    return real_request(method, path, body)
                engine.request = tracked
                for invalid in ('unlocked', 'wrong-operation', 'running'):
                    rejected = root/invalid; rejected.mkdir(mode=0o700)
                    selected_operation = operation
                    if invalid == 'unlocked': fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    if invalid == 'wrong-operation': selected_operation = 'different-operation'
                    if invalid == 'running': engine.request('POST', '/containers/'+originals['backend']['Id']+'/start')
                    prior = len(effects)
                    try:
                        switch_stopped_programs(originals, program, engine=engine, guard=lambda: None,
                            journal=rejected, operation_id=selected_operation, epoch_policy=policy, lock_fd=lock_fd)
                        raise AssertionError('unsafe switch accepted: '+invalid)
                    except (ValueError, RecoveryError) as error:
                        expected = {'unlocked':'BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED',
                            'wrong-operation':'PROGRAM_REPLACEMENT_EPOCH_REQUIRED',
                            'running':'PROGRAM_ORIGINAL_NOT_STOPPED'}[invalid]
                        assert str(error) == expected, str(error)
                    assert len(effects) == prior and not list(rejected.iterdir())
                    if invalid == 'unlocked': fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    if invalid == 'running': engine.request('POST', '/containers/'+originals['backend']['Id']+'/stop?t=2')
                journal = root/'switch'; journal.mkdir(mode=0o700)
                switched = switch_stopped_programs(originals, program, engine=engine, guard=lambda: None,
                    journal=journal, operation_id=operation, epoch_policy=policy, lock_fd=lock_fd)
                for role, row in switched['replacements'].items():
                    containers.append(row['created']['Id'])
                    assert row['created']['State']['Running'] is False
                    assert row['retained']['State']['Running'] is False
                    assert not row['retained']['NetworkSettings']['Networks']
                    # Real application execution proves the archived filesystem
                    # survived creation; it happens outside the switch executor.
                    new_id = row['created']['Id']
                    engine.request('POST', '/containers/'+new_id+'/start')
                    running = engine.inspect(new_id)
                    assert running['NetworkSettings']['Networks'][network_name]['IPAddress'] == target_addresses[role]
                    assert running['HostConfig']['PortBindings'] == originals[role]['HostConfig']['PortBindings']
                    command = engine.request('POST', '/containers/'+new_id+'/exec', dict(AttachStdout=False,
                        AttachStderr=False, Cmd=['/bin/sh', '-ec',
                            'test "$(cat /program-version)" = ARCHIVED; test "$(cat /data/sentinel)" = ORIGINAL-TARGET-DATA; '
                            'test "$APPLICATION_ENDPOINT" = retained-target']))['Id']
                    engine.request('POST', '/exec/'+command+'/start', dict(Detach=True, Tty=False))
                    deadline = time.monotonic()+10
                    while True:
                        checked = engine.request('GET', '/exec/'+command+'/json')
                        if not checked['Running']: break
                        assert time.monotonic() < deadline
                        time.sleep(.05)
                    assert checked['ExitCode'] == 0
                    engine.request('POST', '/containers/'+new_id+'/stop?t=2')
                try:
                    switch_stopped_programs(originals, program, engine=engine, guard=lambda: None,
                        journal=journal, operation_id=operation, epoch_policy=policy, lock_fd=lock_fd)
                    raise AssertionError('duplicate switch accepted')
                except RecoveryError as error:
                    assert error.code == 'PROGRAM_SWITCH_ALREADY_CLAIMED'
                result.update(state='PASS', oldContainersRetained=True, targetVolumePreserved=True,
                    newContainersCreatedStopped=True, archivedApplicationExecuted=True, duplicateRejected=True,
                    missingLockRejected=True, wrongOperationRejected=True, runningOriginalRejected=True,
                    fixedAddressesPreserved=True,fixedPublishedPortsPreserved=True,existingVolumeContentPreserved=True,
                    receipt= json.loads(Path(switched['receiptPin']['path']).read_text(encoding='utf-8')),
                    productionResourcesTouched=False)
            finally:
                os.close(lock_fd)
    finally:
        if 'root' in locals():
            shutil.copytree(root, Path(os.environ['PROGRAM_TEST_EVIDENCE_DIR'])/'native-evidence')
        # Discover only this random task prefix, so partial HTTP success is
        # cleaned up without guessing effects or touching another task.
        listed = engine.request('GET', '/containers/json?all=true')
        for row in listed:
            if any(name.startswith('/'+prefix+'-') for name in row['Names']):
                if row['Id'] not in containers: containers.append(row['Id'])
        for identity in reversed(containers):
            engine.request('DELETE', '/containers/'+identity+'?force=true&v=false')
        for network in networks: engine.request('DELETE', '/networks/'+network)
        for volume in volumes: engine.request('DELETE', '/volumes/'+volume)
        for row in engine.request('GET', '/images/json?all=true'):
            if (row.get('Labels') or {}).get('spug.program.integration') == prefix and row['Id'] not in images:
                images.append(row['Id'])
        for identity in reversed(images): engine.request('DELETE', '/images/'+identity)
        result['ownedResourcesRemoved'] = True
        print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
