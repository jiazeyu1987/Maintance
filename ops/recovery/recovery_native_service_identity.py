"""W05-only read-only native Docker identity producer, explicitly lab selected.

The protected launch and target lease supply exact owned IDs. No discovery,
container exec, mutation, socket forwarding or manager identity substitution.
Go-template projections are literal commands whose unchanged raw stdout is
retained. Env/health logs and unselected labels are never requested.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import ipaddress
from pathlib import Path
import re
from urllib.parse import urlsplit

from recovery_environment_contract import canonical, decode, exact, require, utc_now
from recovery_native_process import (LAB_ROOT, REHEARSAL_ID, lab_path, persist_bytes,
                                     pinned_bytes, signed_payload)

PROFILE = 'w05-native-readonly-docker-inspect-v1'
SERVICE_FIELDS = set(('schemaVersion rehearsalId operationId restoreId targetIdentityPin sourceScopePin '
    'environmentConfigPin resourcesProofPin applicationStartPin role endpointUrl dockerPin probeSourcePin '
    'probeRuntimeProofPin infoResultPin inspectResultPin networkResultPin invocationPins machineId '
    'dockerEngineId containerId imageId networkId endpointId ipAddress issuedAt expiresAt').split())
BINDING_FIELDS = set(('schemaVersion targetIdentityPin sourceScopePin environmentConfigPin resourcesProofPin '
    'dockerPin machineIdPath role endpointUrl applicationStartPin identityProfile nativeIdentityProofPin').split())
INFO_FORMAT = '{"ID":{{json .ID}}}'
INSPECT_FORMAT = ('[{"Id":{{json .Id}},"Image":{{json .Image}},"Name":{{json .Name}},'
    '"State":{"Running":{{json .State.Running}}},"Config":{"Labels":{'
    '"intruoyi.recovery.target":{{json (index .Config.Labels "intruoyi.recovery.target")}},'
    '"intruoyi.recovery.operation":{{json (index .Config.Labels "intruoyi.recovery.operation")}}}},'
    '"NetworkSettings":{"Networks":{{json .NetworkSettings.Networks}}}}]')
NETWORK_FORMAT = '[{"Id":{{json .Id}},"Containers":{{json .Containers}}}]'


def probe_commands(docker_pin, container_id, network_id):
    require(re.fullmatch(r'[0-9a-f]{64}', container_id) is not None and
            re.fullmatch(r'[0-9a-f]{64}', network_id) is not None, 'NATIVE_SERVICE_FULL_ID_REQUIRED')
    base = [docker_pin['path'], '--host', 'unix:///var/run/docker.sock']
    return [base + ['info', '--format', INFO_FORMAT],
            base + ['inspect', '--format', INSPECT_FORMAT, container_id],
            base + ['network', 'inspect', '--format', NETWORK_FORMAT, network_id]]


def expected_identity(binding, reader, operation_id):
    """Bind the original protected start, not a caller-selected IP/container."""
    config = reader(binding['environmentConfigPin'])
    target = reader(binding['targetIdentityPin'])
    source = reader(binding['sourceScopePin'])
    proof = reader(binding['resourcesProofPin'])
    application = reader(binding['applicationStartPin'])
    require(config['schemaVersion'] == 'RecoveryEnvironmentConfig/v1' and
            target['schemaVersion'] == 'RecoveryTargetIdentity/v1' and
            source['schemaVersion'] == 'RecoverySourceScope/v1' and
            proof['schemaVersion'] == 'RecoveryEnvironmentProof/v1' and
            application['schemaVersion'] == 'ApplicationStartResult/v1', 'NATIVE_SERVICE_INPUT_SCHEMA')
    require(config['targetIdentityPin'] == proof['targetIdentityPin'] == application['targetIdentityPin'] ==
            binding['targetIdentityPin'] and config['sourceScopePin'] == binding['sourceScopePin'] and
            proof['configurationRef'] == binding['environmentConfigPin'] and
            config['dockerPin'] == binding['dockerPin'] and
            proof['operationId'] == application['operationId'] == operation_id and
            application['state'] == 'SUCCEEDED' and
            proof['resources']['machineId'] == target['machineId'] and
            proof['resources']['dockerEngineId'] == target['dockerEngineId'], 'NATIVE_SERVICE_INPUT_BINDING')
    services = [item for item in config['services'] if item['role'] == binding['role']]
    require(len(services) == 1, 'NATIVE_SERVICE_ROLE_UNBOUND')
    spec = services[0]
    services = [item for item in proof['services'] if item['name'] == '/' + spec['name']]
    require(len(services) == 1, 'NATIVE_SERVICE_RESOURCE_UNBOUND')
    service = services[0]
    require(service['id'] not in source['containerIds'] and
            service['name'].lstrip('/') not in source['containerNames'], 'NATIVE_SERVICE_SOURCE_REJECTED')
    launches = [record for pin in application['originalStartResultPins']
                if (record := reader(pin)).get('schemaVersion') == 'RecoveryApplicationLaunch/v1']
    require(len(launches) == 1, 'NATIVE_SERVICE_LAUNCH_UNBOUND')
    launch = launches[0]
    network_id = proof['network']['networkId']
    require(launch['operationId'] == operation_id and launch['targetIdentityPin'] == binding['targetIdentityPin'] and
            launch['network']['networkId'] == network_id, 'NATIVE_SERVICE_LAUNCH_CHANGED')
    endpoint = launch['network']['containers'][service['id']]
    require(endpoint['Name'] == spec['name'], 'NATIVE_SERVICE_LAUNCH_CONTAINER_CHANGED')
    address = str(ipaddress.ip_address(endpoint['IPv4Address'].split('/')[0]))
    parsed = urlsplit(binding['endpointUrl'])
    require(parsed.scheme in ('http', 'https', 'redis', 'amqp', 'amqps') and
            not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and
            parsed.path in ('', '/') and parsed.hostname == address and address not in source['endpointHosts'] and
            parsed.port == (6379 if binding['role'] == 'redis' else spec['health']['port']),
            'NATIVE_SERVICE_ENDPOINT_CHANGED')
    require(proof['network']['name'].startswith('brlab-20261012') and
            service['name'].lstrip('/').startswith('brlab-20261012'), 'NATIVE_SERVICE_RESOURCE_NOT_TASK_OWNED')
    return target, service, proof['network'], endpoint, address


def validate_observations(info, inspected, networks, *, target, service, network, endpoint, address, operation_id):
    exact(info, {'ID'}, 'NATIVE_SERVICE_INFO_SHAPE')
    require(info['ID'] == target['dockerEngineId'], 'NATIVE_SERVICE_ENGINE_CHANGED')
    require(type(inspected) is list and len(inspected) == 1 and type(networks) is list and len(networks) == 1,
            'NATIVE_SERVICE_INSPECT_AMBIGUOUS')
    actual, actual_network = inspected[0], networks[0]
    exact(actual, {'Id', 'Image', 'Name', 'State', 'Config', 'NetworkSettings'}, 'NATIVE_SERVICE_INSPECT_SHAPE')
    exact(actual_network, {'Id', 'Containers'}, 'NATIVE_SERVICE_NETWORK_SHAPE')
    labels = {'intruoyi.recovery.target': target['targetId'], 'intruoyi.recovery.operation': operation_id}
    require(actual['Id'] == service['id'] and actual['Image'] == service['imageId'] and
            actual['Name'] == service['name'] and actual['State'] == {'Running': True} and
            actual['Config'] == {'Labels': labels} and actual_network['Id'] == network['networkId'],
            'NATIVE_SERVICE_INSTANCE_CHANGED')
    matches = [item for item in actual['NetworkSettings']['Networks'].values()
               if item['NetworkID'] == network['networkId']]
    require(len(matches) == 1 and matches[0]['EndpointID'] == endpoint['EndpointID'] and
            matches[0]['IPAddress'] == address and actual_network['Containers'].get(service['id']) == endpoint,
            'NATIVE_SERVICE_NETWORK_CHANGED')


class NativeServiceIdentityProducer:
    def __init__(self, *, process_producer, record_reader, target_lease_guard, probe_source_pin,
                 machine_id_path, maximum_age_milliseconds):
        require(callable(target_lease_guard) and type(maximum_age_milliseconds) is int and
                0 < maximum_age_milliseconds <= 300000, 'NATIVE_SERVICE_CURRENT_GUARD_REQUIRED')
        self.process, self.reader, self.lease_guard = process_producer, record_reader, target_lease_guard
        self.source_pin, self.machine_path = probe_source_pin, machine_id_path
        self.max_age = maximum_age_milliseconds

    def produce(self, binding, *, operation_binding, command_prefix, cwd):
        exact(binding, BINDING_FIELDS, 'NATIVE_SERVICE_BINDING_SHAPE')
        require(binding['schemaVersion'] == 'RecoveryServiceBinding/v2' and binding['identityProfile'] == PROFILE,
                'NATIVE_SERVICE_EXPLICIT_PROFILE_REQUIRED')
        require(binding['nativeIdentityProofPin'] is None, 'NATIVE_SERVICE_PROOF_ALREADY_SELECTED')
        require(binding['targetIdentityPin'] == operation_binding['targetIdentityPin'] and
                binding['machineIdPath'] == self.machine_path, 'NATIVE_SERVICE_CURRENT_BINDING')
        self.lease_guard(); self.process.guard()
        target, service, network, endpoint, address = expected_identity(binding, self.reader, operation_binding['operationId'])
        # This literal host machine ID is read by the authorized probe boundary.
        # Never substitute the manager's machine ID when it differs.
        machine = Path(self.machine_path)
        require(machine.is_absolute() and self.machine_path == '/etc/machine-id', 'NATIVE_SERVICE_HOST_MACHINE_PATH')
        metadata = machine.lstat()
        import stat
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == 0 and not metadata.st_mode & 0o022,
                'NATIVE_SERVICE_MACHINE_ID_UNSAFE')
        observed_machine = machine.read_text(encoding='ascii').strip()
        require(observed_machine == target['machineId'], 'NATIVE_SERVICE_HOST_MACHINE_CHANGED')
        manifest, trust, _, _ = self.process.runtime()
        require(trust['runtimeRole'] == 'EXECUTOR', 'NATIVE_SERVICE_PROBE_RUNTIME_ROLE')
        source_pins = [pin for pin in manifest['filePins'] if pin['path'].endswith('.py')]
        for pin in (manifest['pythonPin'], binding['dockerPin']):
            if pin not in source_pins:
                source_pins.append(pin)
        require(self.source_pin in source_pins, 'NATIVE_SERVICE_PROBE_NOT_INSTALLED')
        commands = probe_commands(binding['dockerPin'], service['id'], network['networkId'])
        invocation_pins, originals = [], []
        for index, argv in enumerate(commands):
            self.lease_guard()
            invocation = self.process.run(command_id=f'{command_prefix}-{index}', argv=argv, cwd=cwd,
                source_pins=source_pins, binding=operation_binding)
            record = decode(pinned_bytes(invocation))
            require(record['state'] == 'SUCCEEDED' and record['actualExitCode'] == 0,
                    'NATIVE_SERVICE_COMMAND_FAILED')
            process_result = signed_payload(record['processResultPin'], self.process.authority_pin)
            require(process_result['stderrPin']['bytes'] == 0 and
                    pinned_bytes(process_result['stderrPin']) == b'', 'NATIVE_SERVICE_STDERR_NOT_EMPTY')
            raw = pinned_bytes(record['resultPin'])
            originals.append((record['resultPin'], decode(raw))); invocation_pins.append(invocation)
        validate_observations(*(item[1] for item in originals), target=target, service=service,
            network=network, endpoint=endpoint, address=address, operation_id=operation_binding['operationId'])
        self.lease_guard(); self.process.guard()
        after = machine.lstat()
        require(machine.read_text(encoding='ascii').strip() == observed_machine and
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) ==
                (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns),
                'NATIVE_SERVICE_HOST_MACHINE_CHANGED')
        # Re-read the protected target/launch and every selected raw original.
        require(expected_identity(binding, self.reader, operation_binding['operationId']) ==
                (target, service, network, endpoint, address), 'NATIVE_SERVICE_PROTECTED_LAUNCH_CHANGED')
        manifest, _, runtime, _ = self.process.runtime()
        issued = utc_now()
        expiry = min(datetime.fromisoformat(issued.replace('Z', '+00:00')) + timedelta(milliseconds=self.max_age),
                     datetime.fromisoformat(runtime['expiresAt'].replace('Z', '+00:00')))
        record = dict(schemaVersion='RecoveryNativeServiceIdentity/v1', rehearsalId=REHEARSAL_ID,
            operationId=operation_binding['operationId'], restoreId=operation_binding['restoreId'],
            **{key: binding[key] for key in ('targetIdentityPin', 'sourceScopePin', 'environmentConfigPin',
                'resourcesProofPin', 'applicationStartPin', 'role', 'endpointUrl', 'dockerPin')},
            probeSourcePin=self.source_pin, probeRuntimeProofPin=manifest['nativeRuntimeProofPin'],
            infoResultPin=originals[0][0], inspectResultPin=originals[1][0], networkResultPin=originals[2][0],
            invocationPins=invocation_pins, machineId=observed_machine, dockerEngineId=originals[0][1]['ID'],
            containerId=service['id'], imageId=service['imageId'], networkId=network['networkId'],
            endpointId=endpoint['EndpointID'], ipAddress=address, issuedAt=issued,
            expiresAt=expiry.isoformat().replace('+00:00', 'Z'))
        exact(record, SERVICE_FIELDS, 'NATIVE_SERVICE_PROOF_SHAPE')
        for pin, value in originals:
            require(decode(pinned_bytes(pin)) == value, 'NATIVE_SERVICE_ORIGINAL_CHANGED')
        original = persist_bytes(self.process.root / (command_prefix + '-identity-original.json'),
                                 canonical(record))
        signed = self.process.signer.sign(original, deadline=self.process.deadline, worker_uid=self.process.uid)
        self.lease_guard(); self.process.guard()
        return signed
