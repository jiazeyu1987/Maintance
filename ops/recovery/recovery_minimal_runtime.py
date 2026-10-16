"""Single-operator Linux restore using the existing SQL and object engines."""
from __future__ import annotations

import importlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import sys
import time

from recovery_data import NativeData
from recovery_engine import (Budget, absolute, canonical, check_pin, digest, pin,
    pinned_json, RecoveryError, require, signature, utc, write)
from recovery_minimal_plan import disjoint, selected_chain, target_configuration


def modules_from(root):
    root = absolute(root)
    require(root.is_dir(), 'FORMAL_MODULE_DIRECTORY_MISSING')
    sys.path.insert(0, str(root))
    names = ('formal_sql_restore', 'formal_data_evidence', 'formal_s3_export',
             'formal_physical_restore_readback')
    modules = {name: importlib.import_module(name) for name in names}
    # Check actual import origins, without requiring a signed module closure.
    for name, module in tuple(sys.modules.items()):
        if name.startswith('formal_') and getattr(module, '__file__', None):
            require(Path(module.__file__).resolve().parent == root, 'FORMAL_MODULE_WRONG_ORIGIN')
    return modules


def json_value(reference, path):
    value = pinned_json(reference)
    require(type(path) is list, 'VERSION_VALUE_PATH_INVALID')
    for key in path:
        require(type(key) in (str, int), 'VERSION_VALUE_PATH_INVALID')
        value = value[key]
    return value


class MinimalData(NativeData):
    """Reuse native data methods; the new main path has no legacy trust calls."""

    def __init__(self, configuration, request, source, policy, chain, target, root, input_pins):
        require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
        self.original = request
        self.request = dict(request, requestId=request['operationId'])
        self.source, self.chain, self.config = source, chain, target
        self.policy = dict(policy, **{key: configuration[key] for key in
            ('environmentMysqlClientPath', 'maxExpandedBytes', 'dataLimits')})
        self.policy.update(target['dataPolicy'])
        # Read-only query recipes are local configuration, not approval records.
        self.policy['approvedReadOnlyQueryPins'] = [row['queryPin'] for row in self.policy['businessInvariants']]
        self.plan = {'recoveryPoint': chain[-1][2]['recoveryPoint']}
        self.material = chain[-1][2]
        self.budget = Budget(configuration['deadlineMilliseconds'])
        self.root = root
        self.input_pins = input_pins
        self.original_pins = []
        self.last_exit = None
        self.mutation_dispatched = False
        self.modules = modules_from(configuration['formalModuleDirectory'])
        self.config_services = {row['role']: row for row in target['services']}
        self.storage_running = chain[0][2]['objects']['method'] != 'PHYSICAL_FILES'
        self.running_applications = set()
        self.snapshots = {}
        self.payload_signatures = {}
        for step in chain:
            for ref in step[2]['payloadPins'] + step[2]['versionPins'] + [step[0], step[3]]:
                check_pin(ref, content=False)
                self.payload_signatures[ref['path']] = signature(absolute(ref['path']).stat())
        for ref in (target['dockerPin'], target['iptablesPin']):
            check_pin(ref, content=False)
            self.payload_signatures[ref['path']] = signature(absolute(ref['path']).stat())
        self.target = {'targetIdentityPin': write(root/'target-configuration.json', target)}
        self.db_container = self.config_services['mysql']['id']
        self.db_uuid = self.database_uuid()
        require(self.db_uuid != self.material['sourceDatabaseUuid'], 'SOURCE_DATABASE_TARGET_REJECTED')
        sql = self.modules['formal_sql_restore']; native = self

        class BoundMySql(sql.IsolatedTargetMySql):
            def _command(self, program, arguments):
                command = super()._command(program, arguments)
                return [native.config['dockerPin']['path'], '--host', 'unix:///var/run/docker.sock', *command[1:]]

            def query(self, statement):
                return native.docker(['exec', native.db_container, native.policy['environmentMysqlClientPath'],
                    '--defaults-extra-file=/run/recovery/mysql-client.cnf', '--protocol=SOCKET', '--host=localhost',
                    '--batch', '--skip-column-names',
                    '-e', statement]).decode('utf-8')

        self.mysql = BoundMySql(self.db_container, self.secret('mysql', 'MYSQL_ROOT_PASSWORD'), timeout=self.seconds())
        self.db_target = dict(database=target['database'], databaseUuid=self.db_uuid)

    def secret(self, role, environment):
        ref = self.config['secrets'][role][environment]
        raw = check_pin(ref)
        require(absolute(ref['path']).stat().st_mode & 0o077 == 0, 'SECRET_NOT_PRIVATE')
        value = raw.decode('utf-8')
        require(value and not any(char in value for char in '\r\n\0'), 'SECRET_FORMAT_INVALID')
        return value

    def service(self, role):
        item = self.config_services[role]
        return dict(id=item['id'], imageId=item['imageId'], mounts=self.snapshots[role]['Mounts'])

    def guard(self):
        self.budget.remaining()
        for ref in self.input_pins:
            check_pin(ref, content=False)
        for path, expected in self.payload_signatures.items():
            require(signature(absolute(path).stat()) == expected, 'ARCHIVED_PAYLOAD_CHANGED')

    def inspect(self, identity):
        rows = json.loads(self.docker(['inspect', identity]))
        require(type(rows) is list and len(rows) == 1, 'TARGET_INSPECT_INVALID')
        return rows[0]

    def docker(self, args, **kwargs):
        # Hash executables once, then detect inode/size/time drift on every use.
        return self.command([self.config['dockerPin']['path'], '--host', 'unix:///var/run/docker.sock', *args], **kwargs)

    def database_uuid(self):
        raw = self.docker(['exec', self.db_container, self.policy['environmentMysqlClientPath'],
            '--defaults-extra-file=/run/recovery/mysql-client.cnf', '--protocol=SOCKET', '--host=localhost',
            '--batch', '--skip-column-names', '-e', 'SELECT @@server_uuid;'])
        value = raw.decode('ascii').strip()
        require(re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', value), 'TARGET_DATABASE_UUID_INVALID')
        return value

    def bound(self, *, importing=False, minio_stopped=False):
        self.guard()
        require(absolute('/etc/machine-id').read_text().strip() == self.config['machineId'], 'TARGET_MACHINE_CHANGED')
        info = json.loads(self.docker(['info', '--format', '{{json .}}']))
        require(info['ID'] == self.config['dockerEngineId'], 'TARGET_DOCKER_ENGINE_CHANGED')
        network = json.loads(self.docker(['network', 'inspect', self.config['networkId']]))[0]
        require(network['Id'] == self.config['networkId'] and network['Internal'] is True and
                network['Driver'] == 'bridge' and network['EnableIPv6'] is False and
                len(network['IPAM']['Config']) == 1, 'TARGET_NETWORK_NOT_ISOLATED')
        subnet = ipaddress.ip_network(network['IPAM']['Config'][0]['Subnet'])
        require(subnet.version == 4, 'TARGET_NETWORK_NOT_ISOLATED')
        running = set()
        for role, expected in self.config_services.items():
            row = self.inspect(expected['id'])
            host = row['HostConfig']
            app = role not in ('mysql', 'minio', 'redis')
            want_running = role in ('mysql', 'redis') or role == 'minio' and self.storage_running or role in self.running_applications
            require(row['Id'] == expected['id'] and row['Image'] == expected['imageId'] and
                    row['Config']['Labels'].get('intruoyi.recovery.target') == self.config['targetId'] and
                    row['State']['Running'] is want_running and not row['State']['Paused'] and
                    not row['State']['Restarting'] and row['RestartCount'] == 0 and
                    not host['Privileged'] and not host['Devices'] and not host['CapAdd'] and
                    host['PidMode'] != 'host' and host['IpcMode'] != 'host' and
                    host['NetworkMode'] not in ('host', 'none') and
                    host['RestartPolicy']['Name'] in ('no', '') and
                    set(row['NetworkSettings']['Networks']) == {network['Name']}, 'TARGET_CHANGED_OR_EXPOSED')
            ports = host['PortBindings'] or {}
            require(not ports or app and all(bindings and all(binding['HostIp'] == '127.0.0.1'
                    for binding in bindings) for bindings in ports.values()), 'NON_LOOPBACK_TARGET_PORT')
            if want_running:
                running.add(row['Id'])
            for mount in row['Mounts']:
                require(mount['Type'] in ('volume', 'bind') and
                        any(absolute(mount['Source']).is_relative_to(absolute(path)) for path in self.config['dataPaths']) and
                        all(disjoint(mount['Source'], path) for path in self.source['sourcePaths']) and
                        mount.get('Name') not in self.source['sourceVolumeNames'], 'SOURCE_OR_HOST_MOUNT_REJECTED')
                require(mount['Type'] != 'bind' or mount['RW'] is False, 'WRITABLE_HOST_BIND_REJECTED')
            current = {key: row[key] for key in ('Id', 'Image', 'Mounts', 'Path', 'Args', 'HostConfig', 'Config')}
            # Docker returns Mounts in map iteration order; compare each mount's
            # full configuration using its unique container destination.
            current['Mounts'] = sorted(row['Mounts'], key=lambda item: item['Destination'])
            if role in self.snapshots:
                require(current == self.snapshots[role], 'TARGET_SERVICE_CONFIGURATION_CHANGED')
            else:
                self.snapshots[role] = current
        require(set(network['Containers']) == running, 'TARGET_NETWORK_NOT_EXCLUSIVE')
        # Real local firewall rules isolate container egress and host services.
        rules = [
            ['INPUT', '-s', str(subnet), '-m', 'conntrack', '--ctstate', 'NEW', '-j', 'REJECT',
             '--reject-with', 'icmp-port-unreachable'],
            ['DOCKER-USER', '-s', str(subnet), '!', '-d', str(subnet), '-m', 'conntrack', '--ctstate', 'NEW', '-j', 'REJECT',
             '--reject-with', 'icmp-port-unreachable']]
        for rule in rules:
            self.command([self.config['iptablesPin']['path'], '-w', '5', '-C', *rule])
            raw = self.command([self.config['iptablesPin']['path'], '-w', '5', '-S', rule[0]])
            first = next((line for line in raw.decode().splitlines() if line.startswith('-A ')), None)
            require(first and shlex.split(first) == ['-A', *rule], 'TARGET_FIREWALL_CHANGED')
        sql = self.modules['formal_sql_restore']
        (sql.import_database_state if importing else sql.database_state)(self.mysql, self.db_target)

    def fresh_target(self):
        self.bound()
        self.application_inputs()
        self.modules['formal_sql_restore'].empty_database(self.mysql, self.db_target)
        writable = {}
        for role, snapshot in self.snapshots.items():
            for mount in snapshot['Mounts']:
                if mount['RW']:
                    require(mount['Type'] == 'volume' and mount['Source'] not in writable, 'SHARED_TARGET_DATA_VOLUME')
                    writable[mount['Source']] = self.config_services[role]['id']
                    volume = json.loads(self.docker(['volume', 'inspect', mount['Name']]))[0]
                    require(volume['Driver'] == 'local' and not volume['Options'] and
                            volume['Mountpoint'] == mount['Source'] and
                            (volume['Labels'] or {}).get('intruoyi.recovery.target') == self.config['targetId'],
                            'TASK_OWNED_LOCAL_VOLUME_REQUIRED')
        for identity in self.docker(['ps', '--all', '--no-trunc', '--format', '{{.ID}}']).decode().splitlines():
            for mount in self.inspect(identity)['Mounts']:
                require(mount['Source'] not in writable or writable[mount['Source']] == identity, 'TARGET_VOLUME_SHARED')
        if not self.storage_running:
            from recovery_data_files import inventory
            mounts = [item for item in self.snapshots['minio']['Mounts']
                      if item['Destination'] == self.policy['minioDataMount']]
            require(len(mounts) == 1 and mounts[0]['RW'], 'DEDICATED_MINIO_DATA_VOLUME_REQUIRED')
            require(inventory(absolute(mounts[0]['Source']), self.guard) == {}, 'PHYSICAL_TARGET_VOLUME_NOT_EMPTY')
        else:
            from recovery_data_objects import _get, _xml
            raw, _ = _get(self.object_client(), '', None, self.bound)
            listing = _xml(raw, 'ListAllMyBucketsResult')
            buckets = [node for node in listing if node.tag.split('}')[-1] == 'Buckets']
            require(len(buckets) == 1 and not list(buckets[0]), 'OBJECT_TARGET_NOT_EMPTY')
        # Authenticate over stdin; never place Redis credentials in argv/logs.
        password = self.secret('redis', 'REDIS_PASSWORD')
        script = 'IFS= read -r REDISCLI_AUTH; export REDISCLI_AUTH; exec "$@"'
        raw = self.docker(['exec', '-i', self.config_services['redis']['id'], 'sh', '-ec', script,
            'recovery-redis', self.config['redisClientPath'], '--raw', 'DBSIZE'],
            input_bytes=(password+'\n').encode())
        require(raw.strip() == b'0', 'REDIS_TARGET_NOT_EMPTY')

    def check_bucket_permissions(self):
        from recovery_data_objects import protection
        observed = protection(self.object_client(), self.config['buckets'], self.config['bucketProtection'], guard=self.guard)
        self.bound()
        return write(self.root/'bucket-permissions.json', observed)

    def physical_object_chain(self):
        from recovery_data_files import apply_tree, inventory, physical_chain_inputs
        from recovery_data_objects import compare_indexed_restore
        require(all(key == value for key, value in self.policy['bucketMapping'].items()),
                'PHYSICAL_BUCKET_RENAME_UNSUPPORTED')
        self.bound()
        row = self.inspect(self.config_services['minio']['id'])
        mounts = [item for item in row['Mounts'] if item['Destination'] == self.policy['minioDataMount']]
        require(len(mounts) == 1 and mounts[0]['Type'] == 'volume' and mounts[0]['RW'],
                'DEDICATED_MINIO_DATA_VOLUME_REQUIRED')
        mount = mounts[0]
        volume = json.loads(self.docker(['volume', 'inspect', mount['Name']]))[0]
        require(volume['Driver'] == 'local' and not volume['Options'] and volume['Mountpoint'] == mount['Source'],
                'PHYSICAL_TARGET_VOLUME_INVALID')
        root = absolute(mount['Source'])
        # This main path never deletes an initialized or existing target tree.
        require(inventory(root, self.guard) == {}, 'PHYSICAL_TARGET_VOLUME_NOT_EMPTY')
        for identity in self.docker(['ps', '--all', '--no-trunc', '--format', '{{.ID}}']).decode().splitlines():
            if identity != row['Id']:
                require(all(item.get('Name') != mount['Name'] and item['Source'] != mount['Source']
                    for item in self.inspect(identity)['Mounts']), 'PHYSICAL_VOLUME_SHARED')
        steps = []
        for index, (material_ref, prior, expected, payloads, changed, deleted) in enumerate(physical_chain_inputs(self.chain)):
            self.bound()
            self.mutation_dispatched = True
            intent = write(self.root/('physical-step-%03d-intent.json' % index),
                dict(materialPin=material_ref, changedPaths=sorted(changed), deletedPaths=sorted(deleted)))
            self.original_pins.append(intent)
            value = apply_tree(root, prior, expected, payloads, full=index == 0, guard=self.guard,
                               ownership=self.policy['minioFileOwnership'])
            self.bound()
            steps.append(write(self.root/('physical-step-%03d-readback.json' % index), value))
        # The isolated network/firewall is checked before the only storage start.
        self.bound()
        self.docker(['start', row['Id']], mutation=True)
        self.storage_running = True
        self.wait_healthy('minio')
        self.bound()
        export = self.modules['formal_s3_export'].export_s3_versions(self.object_client(), self.config['buckets'],
            self.root/'physical-export', guard=self.guard, timeout=self.seconds())
        self.bound()
        comparison = compare_indexed_restore(self.chain, self.policy, self.root/'physical-export', export,
            self.modules['formal_physical_restore_readback'], self.guard)
        self.bound()
        mapping = self.root/'physical-version-mapping.jsonl'
        with mapping.open('xb') as output:
            os.chmod(mapping, 0o600)
            for line in check_pin(self.material['objects']['inventoryPin']).splitlines():
                entry = json.loads(line)
                output.write(canonical(dict(sourceBucket=entry['bucket'], targetBucket=entry['bucket'], key=entry['key'],
                    sourceVersionId=entry['versionId'], targetVersionId=entry['versionId'], kind=entry['kind'],
                    isLatest=entry['isLatest']))+b'\n')
            output.flush(); os.fsync(output.fileno())
        return dict(recoveryPoint=self.plan['recoveryPoint'], versionMappingPin=pin(mapping),
            physicalStepEvidencePins=steps, comparisonPin=write(self.root/'physical-comparison.json', comparison),
            permissionEvidencePin=self.check_bucket_permissions(), originalVersionIdsPreserved=True)

    def wait_healthy(self, role):
        # Poll actual Docker health; never repeat a start or data mutation.
        self.bound()
        while True:
            self.guard()
            row = self.inspect(self.config_services[role]['id'])
            health = row['State'].get('Health')
            require(type(health) is dict, 'ACTUAL_CONTAINER_HEALTHCHECK_REQUIRED')
            require(health['Status'] in ('starting', 'healthy'), 'APPLICATION_OR_STORAGE_UNHEALTHY')
            if health['Status'] == 'healthy':
                self.bound()
                return dict(containerId=row['Id'], imageId=row['Image'], status='healthy', observedAt=utc())
            time.sleep(min(0.25, self.budget.remaining()))

    def application_inputs(self):
        """Map archived version/configuration into the explicitly provisioned target."""
        app = self.config['application']
        all_payloads = self.material['payloadPins']
        versions = self.material['versionPins']
        covered = set()
        for binding in app['imageBindings']:
            require(binding['versionPin'] in versions and
                    json_value(binding['versionPin'], binding['valuePath']) == binding['imageId'] and
                    binding['imageId'] == self.config_services[binding['role']]['imageId'],
                    'ARCHIVED_IMAGE_VERSION_MISMATCH')
            covered.add(binding['role'])
        require(covered == set(self.config_services), 'ARCHIVED_IMAGE_VERSIONS_INCOMPLETE')
        applications = set(self.config_services) - {'mysql', 'minio', 'redis'}
        require(set(app['startOrder']) == applications and len(app['startOrder']) == len(applications),
                'APPLICATION_START_ORDER_INVALID')
        configurations = set()
        require(app['configurationBindings'], 'ARCHIVED_APPLICATION_CONFIGURATION_REQUIRED')
        for kind in ('configurationBindings', 'artifactBindings'):
            for binding in app[kind]:
                archived, target = binding['archivePin'], binding['targetPin']
                require(archived in all_payloads and absolute(archived['path']).name != '', 'APPLICATION_INPUT_NOT_ARCHIVED')
                check_pin(archived, content=False); check_pin(target, content=False)
                role = binding['role']; require(role in applications, 'APPLICATION_INPUT_ROLE_INVALID')
                mounts = self.inspect(self.config_services[role]['id'])['Mounts']
                require(any(item['Source'] == target['path'] and item['Destination'] == binding['destination'] and
                    item['RW'] is False for item in mounts), 'APPLICATION_INPUT_NOT_MOUNTED_READONLY')
                if kind == 'artifactBindings':
                    require((archived['bytes'], archived['sha256']) == (target['bytes'], target['sha256']),
                            'ARCHIVED_APPLICATION_ARTIFACT_CHANGED')
                else:
                    require('original-configs' in Path(archived['path']).parts,
                            'ORIGINAL_APPLICATION_CONFIGURATION_NOT_ARCHIVED')
                    configurations.add(role)
        require(configurations == applications, 'APPLICATION_CONFIGURATION_INCOMPLETE')

    def start_application(self):
        self.bound(); self.application_inputs()
        observations = {}
        for role in self.config['application']['startOrder']:
            self.bound()
            self.docker(['start', self.config_services[role]['id']], mutation=True)
            self.running_applications.add(role)
            observations[role] = self.wait_healthy(role)
        self.bound(); self.application_inputs()
        return dict(services=observations, archivedVersionPins=self.material['versionPins'],
                    configurationBindings=self.config['application']['configurationBindings'],
                    state='SUCCEEDED', businessAcceptance='NOT_PERFORMED', isolation='ENFORCED')


def execute(configuration, request, root, input_pins):
    source, policy, chain = selected_chain(configuration, request)
    target = target_configuration(configuration, request, source)
    require(os.name == 'posix', 'NATIVE_LINUX_REQUIRED')
    # A permanent local reservation prevents a second operation overwriting a
    # target even when the first process has ended or its result is unknown.
    reservation = absolute(target['dataRoot'])/'.recovery-operation.json'
    try:
        with reservation.open('xb') as stream:
            os.chmod(reservation, 0o600)
            stream.write(canonical(dict(operationId=request['operationId'], startedAt=utc())))
            stream.flush(); os.fsync(stream.fileno())
    except FileExistsError as error:
        raise RecoveryError('TARGET_ALREADY_RESERVED') from error
    native = MinimalData(configuration, request, source, policy, chain, target, root, input_pins)
    try:
        native.fresh_target()
        db_pins, object_pins = [], []
        for index, step in enumerate(chain):
            native.material = step[2]
            native.root = root/('database-%03d' % index); native.root.mkdir(mode=0o700)
            native.request.update(action='DATABASE_FULL' if index == 0 else 'DATABASE_INCREMENTAL',
                                  previousDatabaseResultPin=db_pins[-1] if db_pins else None)
            result = native.full_database() if index == 0 else native.incremental_database()
            db_pins.append(write(native.root/'result.json', result))
        native.material = chain[-1][2]
        if chain[0][2]['objects']['method'] == 'PHYSICAL_FILES':
            native.root = root/'objects'; native.root.mkdir(mode=0o700)
            native.request['action'] = 'OBJECT_CHAIN_PHYSICAL'
            object_pins.append(write(native.root/'result.json', native.physical_object_chain()))
        else:
            for index, step in enumerate(chain):
                native.material = step[2]
                native.root = root/('objects-%03d' % index); native.root.mkdir(mode=0o700)
                native.request.update(action='OBJECT_FULL' if index == 0 else 'OBJECT_INCREMENTAL',
                    previousObjectResultPin=object_pins[-1] if object_pins else None,
                    parentRecoveryPoint=chain[index-1][2]['recoveryPoint'] if index else None)
                result = native.full_objects() if index == 0 else native.incremental_objects()
                object_pins.append(write(native.root/'result.json', result))
        native.material = chain[-1][2]
        native.root = root/'final'; native.root.mkdir(mode=0o700)
        native.request.update(action='CONSISTENCY', databaseResultPin=db_pins[-1], objectResultPin=object_pins[-1])
        consistent = write(native.root/'consistency.json', native.consistency())
        from recovery_minimal_derived import rebuild
        derived = write(native.root/'derived.json', rebuild(native))
        native.request['action'] = 'START_APPLICATION'
        application = write(native.root/'application-start.json', native.start_application())
        for step in chain:
            for ref in step[2]['payloadPins']:
                check_pin(ref, content=False)
        return dict(recoveryPoint=chain[-1][2]['recoveryPoint'], targetConfigRef=request['targetConfigRef'],
            orderedChainPins=[step[0] for step in chain], databaseResultPins=db_pins, objectResultPins=object_pins,
            consistencyPin=consistent, derivedPin=derived, applicationStartPin=application,
            businessAcceptance='NOT_PERFORMED'), native
    except Exception as error:
        error.native = native
        raise
