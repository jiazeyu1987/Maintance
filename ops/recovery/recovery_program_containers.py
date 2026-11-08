"""Replace stopped application containers while retaining their original resources.

Only the existing target configuration and content-addressed, locally inspected
images supply creation inputs. The caller owns archive custody, the replacement
epoch and the physical source lock. No application is started or removed here.
"""
from copy import deepcopy
import hashlib
import http.client
import json
import re
import socket
import time
from urllib.parse import quote

from recovery_engine import absolute, canonical, pin, require, utc, write


def snapshot(row):
    value = {key: deepcopy(row[key]) for key in ('Id', 'Name', 'Image', 'Config', 'HostConfig', 'Mounts')}
    value['Mounts'].sort(key=lambda mount: mount['Destination'])
    value['networks'] = {name: {key: deepcopy(item.get(key)) for key in
        ('NetworkID', 'IPAMConfig', 'Aliases', 'Links', 'DriverOpts')}
        for name, item in row['NetworkSettings']['Networks'].items()}
    return value


def _stopped(row, code):
    require(all(row['State'].get(key) is False for key in ('Running', 'Paused', 'Restarting', 'Dead')), code)


def _explicit_mounts(row):
    host = row['HostConfig']
    destinations = set()
    for mount in row['Mounts']:
        target = mount['Destination']
        require(target not in destinations, 'PROGRAM_MOUNT_NOT_EXPLICIT')
        destinations.add(target)
        source = mount.get('Name') if mount['Type'] == 'volume' else mount['Source']
        bindings = [value.split(':') for value in host.get('Binds') or []]
        from_bind = any(len(parts) in (2, 3) and parts[:2] == [source, target] and
            mount['RW'] is ('ro' not in (parts[2].split(',') if len(parts) == 3 else [])) for parts in bindings)
        from_mount = any(value.get('Type') == mount['Type'] and value.get('Source') == source and
            value.get('Target') == target and mount['RW'] is not value.get('ReadOnly', False)
            for value in host.get('Mounts') or [])
        from_tmpfs = mount['Type'] == 'tmpfs' and target in (host.get('Tmpfs') or {})
        require(mount['Type'] in ('bind', 'volume', 'tmpfs') and (from_bind or from_mount or from_tmpfs),
                'PROGRAM_MOUNT_NOT_EXPLICIT')
    require(set(row['Config'].get('Volumes') or {}) <= destinations, 'PROGRAM_MOUNT_NOT_EXPLICIT')
    return destinations


def create_request(original, image):
    """Return an explicit Engine create body, without side effects or secrets in argv."""
    _stopped(original, 'PROGRAM_ORIGINAL_NOT_STOPPED')
    require(re.fullmatch('[0-9a-f]{64}', original['Id']) and
            re.fullmatch('/[A-Za-z0-9][A-Za-z0-9_.-]{0,199}', original['Name']), 'PROGRAM_ORIGINAL_INVALID')
    require(type(image) is dict and re.fullmatch('sha256:[0-9a-f]{64}', image['Id']) and
            image['Os'] == 'linux', 'PROGRAM_IMAGE_INVALID')
    host = deepcopy(original['HostConfig'])
    if 'OomKillDisable' in host and host['OomKillDisable'] is None:
        host['OomKillDisable'] = False
    require(host.get('Privileged') is False and host.get('AutoRemove', False) is False and
            host.get('NetworkMode') not in ('host', 'none') and
            not host.get('NetworkMode', '').startswith('container:') and not host.get('Links'),
            'PROGRAM_HOST_CONFIGURATION_INVALID')
    require(not host.get('PublishAllPorts') and all(type(binding.get('HostPort')) is str and
            binding['HostPort'].isdigit() and 0 < int(binding['HostPort']) <= 65535
            for bindings in (host.get('PortBindings') or {}).values() for binding in bindings or []),
            'PROGRAM_FIXED_PORT_REQUIRED')
    destinations = _explicit_mounts(original)
    require(set(image['Config'].get('Volumes') or {}) <= destinations, 'PROGRAM_IMAGE_IMPLICIT_VOLUME')
    config = deepcopy(original['Config']); config['Image'] = image['Id']
    # Docker inherits image defaults even with an explicit Config. Calculate
    # that merge up front, retaining every target environment override.
    environment = {}
    for item in [*(image['Config'].get('Env') or []), *(config.get('Env') or [])]:
        require(type(item) is str and '=' in item and '\0' not in item, 'PROGRAM_ENVIRONMENT_INVALID')
        key, value = item.split('=', 1)
        require(key, 'PROGRAM_ENVIRONMENT_INVALID')
        environment[key] = value
    config['Env'] = [key+'='+value for key, value in environment.items()]
    config['Labels'] = {**(image['Config'].get('Labels') or {}), **(config.get('Labels') or {})}
    endpoints = {}
    for name, endpoint in original['NetworkSettings']['Networks'].items():
        require(re.fullmatch('[0-9a-f]{64}', endpoint['NetworkID']) and not endpoint.get('Links'),
                'PROGRAM_NETWORK_INVALID')
        endpoints[name] = {key: deepcopy(endpoint.get(key)) for key in ('IPAMConfig', 'Aliases', 'Links', 'DriverOpts')}
        if endpoints[name]['Aliases'] is not None:
            endpoints[name]['Aliases'] = [alias for alias in endpoints[name]['Aliases']
                if alias not in (original['Id'], original['Id'][:12])]
    require(endpoints and host['NetworkMode'] in {*endpoints, *(row['NetworkID'] for row in
            original['NetworkSettings']['Networks'].values())}, 'PROGRAM_NETWORK_INVALID')
    return dict(Config=config, HostConfig=host, NetworkingConfig=dict(EndpointsConfig=endpoints))


def verify_created(original, request, row, *, networks=None, engine_metadata=None):
    require(re.fullmatch('[0-9a-f]{64}', row['Id']) and row['Id'] != original['Id'] and
            row['Name'] == original['Name'] and row['Image'] == request['Config']['Image'],
            'PROGRAM_CREATED_IDENTITY_CHANGED')
    _stopped(row, 'PROGRAM_CREATED_STATE_CHANGED')
    expected_config = deepcopy(request['Config'])
    # Docker Desktop installs this platform bookkeeping label at first start,
    # and strips it on create. It conveys no application/container permission.
    # This exact, independently observed platform case never relaxes user labels.
    label = 'desktop.docker.io/ports.scheme'
    if (engine_metadata or {}).get('OperatingSystem') == 'Docker Desktop' and row['State'].get('Status') == 'created' and \
            expected_config.get('Labels', {}).get(label) == 'v2' and label not in (row['Config'].get('Labels') or {}):
        del expected_config['Labels'][label]
    require(row['Config'] == expected_config and row['HostConfig'] == request['HostConfig'],
            'PROGRAM_CREATED_CONFIGURATION_CHANGED')
    require(sorted(row['Mounts'], key=lambda m: m['Destination']) ==
            sorted(original['Mounts'], key=lambda m: m['Destination']), 'PROGRAM_CREATED_MOUNTS_CHANGED')
    observed = row['NetworkSettings']['Networks']; expected = request['NetworkingConfig']['EndpointsConfig']
    require(set(observed) == set(expected), 'PROGRAM_CREATED_NETWORK_CHANGED')
    for name, endpoint in expected.items():
        actual = observed[name]
        identity = original['NetworkSettings']['Networks'][name]['NetworkID']
        unallocated = row['State'].get('Status') == 'created' and actual['NetworkID'] == '' and \
            (networks or {}).get(name, {}).get('Id') == identity and (networks or {})[name].get('Name') == name
        require((actual['NetworkID'] == identity or unallocated) and
                all(actual.get(key) == endpoint[key] for key in ('IPAMConfig', 'Links', 'DriverOpts')),
                'PROGRAM_CREATED_NETWORK_CHANGED')
        aliases = [value for value in actual.get('Aliases') or [] if value not in (row['Id'], row['Id'][:12])]
        require(sorted(aliases) == sorted(endpoint['Aliases'] or []), 'PROGRAM_CREATED_NETWORK_CHANGED')
    return snapshot(row)


class UnixDocker:
    """Bounded local Engine requests; a failed mutation is never retried."""
    def __init__(self, *, guard, deadline, api_version):
        require(re.fullmatch(r'1\.[0-9]{2,3}', api_version), 'PROGRAM_DOCKER_API_INVALID')
        self.guard, self.deadline, self.version = guard, deadline, api_version

    def request(self, method, path, body=None):
        self.guard()
        remaining = self.deadline-time.monotonic()
        require(remaining > 0, 'PROGRAM_DOCKER_DEADLINE')
        connection = http.client.HTTPConnection('localhost', timeout=min(30, remaining))
        transport = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            transport.settimeout(min(30, remaining)); transport.connect('/var/run/docker.sock')
            connection.sock = transport
            connection.request(method, '/v'+self.version+path,
                body=None if body is None else canonical(body), headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            output = bytearray()
            while True:
                self.guard(); remaining = self.deadline-time.monotonic()
                require(remaining > 0, 'PROGRAM_DOCKER_DEADLINE')
                transport.settimeout(min(30, remaining))
                chunk = response.read1(min(65536, 16*1024*1024-len(output)+1))
                if not chunk: break
                output.extend(chunk)
                require(len(output) <= 16*1024*1024, 'PROGRAM_DOCKER_OUTPUT_LIMIT')
            require(200 <= response.status < 300, 'PROGRAM_DOCKER_HTTP_FAILED')
            self.guard()
            return json.loads(output) if output else None
        finally:
            connection.close(); transport.close()

    def inspect(self, identity):
        require(re.fullmatch('[0-9a-f]{64}', identity), 'PROGRAM_CONTAINER_ID_INVALID')
        return self.request('GET', '/containers/'+identity+'/json')

    def image(self, identity):
        require(re.fullmatch('sha256:[0-9a-f]{64}', identity), 'PROGRAM_IMAGE_INVALID')
        return self.request('GET', '/images/'+identity+'/json')

    def network(self, identity):
        require(re.fullmatch('[0-9a-f]{64}', identity), 'PROGRAM_NETWORK_INVALID')
        return self.request('GET', '/networks/'+identity)

    def metadata(self):
        value = self.request('GET', '/info')
        return {key: value[key] for key in ('ID', 'OperatingSystem', 'ServerVersion')}


def switch_stopped_programs(originals, program, *, engine, guard, journal, operation_id, epoch_policy, lock_fd):
    """Return proved new stopped containers; activation belongs to full restore.

    The original image archive must already have been inspected and loaded.
    Matching local config IDs and layer digests are independently checked here.
    An existing intent, partial switch or unknown HTTP result blocks replay.
    """
    from recovery_backup_epoch import _assert_lock, read_current
    require(type(originals) is dict and set(originals) == {'backend', 'frontend'}, 'PROGRAM_APPLICATION_ROLES_INVALID')
    require(type(operation_id) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,127}', operation_id),
            'PROGRAM_OPERATION_INVALID')
    root = absolute(str(journal)); require(root.is_dir() and not any(root.iterdir()), 'PROGRAM_SWITCH_ALREADY_CLAIMED')
    def held():
        guard(); _assert_lock(epoch_policy, lock_fd)
        epoch = read_current(epoch_policy)
        require(epoch['state'] == 'REPLACING' and epoch['operationId'] == operation_id, 'PROGRAM_REPLACEMENT_EPOCH_REQUIRED')
    held()
    require(program.get('schemaVersion') == 'ArchivedProgramImages/v1', 'PROGRAM_IMAGE_PROOF_INVALID')
    images = {item['role']: item for item in program['images']}
    require(len(images) == len(program['images']) and set(originals) <= set(images), 'PROGRAM_IMAGE_PROOF_INVALID')
    plans = {}; engine_metadata = engine.metadata()
    def networks_for(original):
        observed = {name: engine.network(row['NetworkID']) for name, row in original['NetworkSettings']['Networks'].items()}
        require(all(observed[name]['Name'] == name and observed[name]['Id'] == row['NetworkID']
            for name, row in original['NetworkSettings']['Networks'].items()), 'PROGRAM_NETWORK_CHANGED')
        return observed
    for role, original in originals.items():
        held(); observed = engine.inspect(original['Id'])
        require(snapshot(observed) == snapshot(original), 'PROGRAM_ORIGINAL_CHANGED')
        archived = images[role]; image = engine.image(archived['imageId'])
        require(image['Id'] == archived['imageId'] and image['Os'] == archived['os'] == 'linux' and
                image['Architecture'] == archived['architecture'] and image['RootFS']['Type'] == 'layers' and
                image['RootFS']['Layers'] == archived['diffIds'], 'PROGRAM_LOADED_IMAGE_CHANGED')
        plans[role] = create_request(observed, image)
        networks_for(original)
    intent = write(root/'intent.json', dict(schemaVersion='MainProgramSwitchIntent/v1', operationId=operation_id,
        originals=originals, program=program, requests=plans, engineMetadata=engine_metadata, startedAt=utc()))
    sequence = 0
    def mutation(method, path, body=None):
        nonlocal sequence
        held()
        for original in originals.values():
            _stopped(engine.inspect(original['Id']), 'PROGRAM_ORIGINAL_NOT_STOPPED')
        for item in replacements.values():
            _stopped(engine.inspect(item['created']['Id']), 'PROGRAM_CREATED_STATE_CHANGED')
        sequence += 1
        attempt = write(root/('%04d-intent.json' % sequence), dict(method=method, path=path,
            bodySha256=None if body is None else hashlib.sha256(canonical(body)).hexdigest(), startedAt=utc()))
        result = engine.request(method, path, body)
        write(root/('%04d-result.json' % sequence), dict(intentPin=attempt, result=result, finishedAt=utc()))
        held()
        return result
    replacements = {}
    try:
        for role in ('frontend', 'backend'):
            original = originals[role]
            observed = engine.inspect(original['Id'])
            require(snapshot(observed) == snapshot(original), 'PROGRAM_ORIGINAL_CHANGED')
            _stopped(observed, 'PROGRAM_ORIGINAL_NOT_STOPPED')
            retained = original['Name'][1:]+'-retained-'+hashlib.sha256(operation_id.encode()).hexdigest()[:16]
            mutation('POST', '/containers/'+original['Id']+'/rename?name='+quote(retained, safe=''))
            for endpoint in original['NetworkSettings']['Networks'].values():
                mutation('POST', '/networks/'+endpoint['NetworkID']+'/disconnect', dict(Container=original['Id'], Force=False))
            held(); saved = engine.inspect(original['Id']); _stopped(saved, 'PROGRAM_RETAINED_STATE_CHANGED')
            expected = snapshot(original); expected['Name'] = '/'+retained; expected['networks'] = {}
            require(snapshot(saved) == expected, 'PROGRAM_RETAINED_CONFIGURATION_CHANGED')
            request = plans[role]
            body = dict(request['Config'], HostConfig=request['HostConfig'], NetworkingConfig=request['NetworkingConfig'])
            result = mutation('POST', '/containers/create?name='+quote(original['Name'][1:], safe=''), body)
            require(type(result) is dict and not result.get('Warnings') and
                    type(result.get('Id')) is str and re.fullmatch('[0-9a-f]{64}', result['Id']), 'PROGRAM_CREATE_RESPONSE_INVALID')
            held(); created = engine.inspect(result['Id'])
            write(root/(role+'-created-observation.json'), created)
            verify_created(original, request, created, networks=networks_for(original), engine_metadata=engine_metadata)
            replacements[role] = dict(original=original, retained=saved, created=created)
            write(root/(role+'-verified.json'), replacements[role])
        held()
        for role, item in replacements.items():
            verify_created(item['original'], plans[role], engine.inspect(item['created']['Id']),
                networks=networks_for(item['original']), engine_metadata=engine_metadata)
            saved = engine.inspect(item['retained']['Id'])
            _stopped(saved, 'PROGRAM_RETAINED_STATE_CHANGED')
            require(snapshot(saved) == snapshot(item['retained']), 'PROGRAM_RETAINED_CONFIGURATION_CHANGED')
        receipt = write(root/'result.json', dict(schemaVersion='MainProgramSwitchResult/v1',
            state='CREATED_STOPPED', operationId=operation_id, intentPin=intent,
            applicationPins={role: pin(root/(role+'-verified.json')) for role in replacements}, finishedAt=utc()))
        return dict(receiptPin=receipt, replacements=replacements)
    except BaseException as error:
        write(root/'failure.json', dict(schemaVersion='MainProgramSwitchFailure/v1', state='FAILED_RETAINED',
            operationId=operation_id, intentPin=intent, attemptedMutations=sequence,
            failureCode=getattr(error, 'code', type(error).__name__), finishedAt=utc()))
        raise
