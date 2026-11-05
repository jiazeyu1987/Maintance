"""Explicit custody for restoring data into an existing main application.

This replaces rehearsal-only isolation assumptions with a registered identity
contract. It never provisions a resource or changes images, mounts or settings.
Only the authenticated safe-engine package installs the runtime mixin.
"""
from pathlib import Path
import ipaddress
import json
import re
import stat
import subprocess
from types import SimpleNamespace

from recovery_engine import absolute, check_pin, digest, pin, pinned_json, require

DATA_ROLES = frozenset(('mysql', 'minio', 'redis'))
MAIN_FIELDS = frozenset(('schemaVersion', 'serviceConfigurationDigests', 'networks',
    'networkAttachments', 'archiveImageBindings', 'configurationPins', 'writerAdmission'))
NETWORK_FIELDS = frozenset(('id', 'name', 'driver', 'internal', 'enableIPv6', 'ipam',
    'options', 'labels', 'memberContainerIds'))


def enabled(target):
    return 'mainApplication' in target


def service_configuration_digest(row):
    return digest({key: row[key] for key in ('Path', 'Args', 'HostConfig', 'Config')})


def network_attachments(row):
    return {name: dict(networkId=item['NetworkID'], ipAddress=item.get('IPAddress') or (item.get('IPAMConfig') or {}).get('IPv4Address', ''),
        globalIPv6Address=item.get('GlobalIPv6Address') or (item.get('IPAMConfig') or {}).get('IPv6Address', ''), aliases=sorted(item.get('Aliases') or []),
        links=sorted(item.get('Links') or []), driverOpts=item.get('DriverOpts') or {})
        for name, item in row['NetworkSettings']['Networks'].items()}


def network_configuration(row, members):
    return dict(id=row['Id'], name=row['Name'], driver=row['Driver'], internal=row['Internal'],
        enableIPv6=row['EnableIPv6'], ipam=row['IPAM'], options=row.get('Options') or {},
        labels=row.get('Labels') or {}, memberContainerIds=sorted(members))


def _published_host_port(row):
    for bindings in (row['HostConfig'].get('PortBindings') or {}).values():
        for binding in bindings or []:
            host = binding.get('HostIp') or '0.0.0.0'
            port = binding.get('HostPort', '')
            if type(host) is not str or type(port) is not str or not port.isdigit():
                continue
            try:
                ipaddress.ip_address(host)
            except ValueError:
                continue
            if 0 < int(port) <= 65535:
                return True
    return False


def _dynamic_application_attachment(native, role, row, name, observed, expected, attachments):
    """Bind ancillary Docker allocations to lifecycle and real network membership."""
    if role in DATA_ROLES or row['NetworkSettings']['Networks'][name].get('IPAMConfig'):
        return False
    addresses = ('ipAddress', 'globalIPv6Address')
    if {k: v for k, v in observed.items() if k not in addresses} != \
            {k: v for k, v in expected.items() if k not in addresses}:
        return False
    service = native.config_services[role]
    if service['ip'] in {expected[key] for key in addresses}:
        return False
    fixed = set()
    for other, item in row['NetworkSettings']['Networks'].items():
        configured = item.get('IPAMConfig') or {}
        saved = native.config['mainApplication']['networkAttachments'][role].get(other)
        if other != name and saved == attachments[other]:
            fixed.update(value for field, key in (('IPv4Address', 'ipAddress'),
                         ('IPv6Address', 'globalIPv6Address'))
                         if (value := configured.get(field)) and value == saved[key])
    if not fixed:
        return False
    try:
        loopback = ipaddress.ip_address(service['ip']).is_loopback
    except ValueError:
        return False
    if service['ip'] not in fixed and not (loopback and _published_host_port(row)):
        return False
    registered = next((network for network in native.config['mainApplication']['networks']
                       if network['name'] == name and network['id'] == observed['networkId']), None)
    if registered is None or registered['driver'] != 'bridge':
        return False
    if not row['State']['Running']:
        return all(observed[key] == '' for key in addresses)
    networks = json.loads(native.docker(['network', 'inspect', registered['id']]))
    if type(networks) is not list or len(networks) != 1 or networks[0]['Id'] != registered['id']:
        return False
    member = networks[0]['Containers'].get(row['Id'])
    if not member:
        return False
    for field, key in (('IPv4Address', 'ipAddress'), ('IPv6Address', 'globalIPv6Address')):
        allocated = member.get(field) or ''
        try:
            address = str(ipaddress.ip_interface(allocated).ip) if allocated else ''
        except ValueError:
            return False
        if address != observed[key]:
            return False
    return any(observed[key] for key in addresses)


def verify_network_attachments(native, role, row, expected):
    observed = network_attachments(row)
    require(set(observed) == set(expected), 'MAIN_SERVICE_NETWORK_CHANGED')
    for name, attachment in observed.items():
        require(attachment == expected[name] or _dynamic_application_attachment(
                native, role, row, name, attachment, expected[name], observed),
                'MAIN_SERVICE_NETWORK_CHANGED')


def capture_main_application(target, rows, networks, archive_image_bindings,
                             configuration_pins, writer_evidence_pin):
    """Build the versioned contract from explicit observations, never invent evidence."""
    evidence = _document(writer_evidence_pin)
    candidate = dict(schemaVersion='RegisteredMainApplication/v1',
        serviceConfigurationDigests={role: service_configuration_digest(row) for role, row in rows.items()},
        networkAttachments={role: network_attachments(row) for role, row in rows.items()},
        networks=[network_configuration(network, sorted(set(network['Containers']) |
            {row['Id'] for row in rows.values() if network['Name'] in row['NetworkSettings']['Networks']}))
            for network in networks],
        archiveImageBindings=archive_image_bindings, configurationPins=configuration_pins,
        writerAdmission=dict(schemaVersion='RegisteredMainWriterCustody/v1',
            approvedWriterContainerIds=evidence['writerContainerIds'],
            exclusiveResources=evidence['exclusiveResources'], evidencePin=writer_evidence_pin))
    validate(dict(target, mainApplication=candidate))
    native = SimpleNamespace(config=dict(target, mainApplication=candidate),
        config_services={s['role']: s for s in target['services']},
        inspect=lambda identity: next(row for row in rows.values() if row['Id'] == identity))
    _writer_evidence(native, candidate)
    return candidate


def _document(reference):
    require(pin(reference['path']) == reference, 'MAIN_PIN_CHANGED')
    return pinned_json(reference)


def _writer_evidence(native, value):
    writers = value['writerAdmission']
    evidence = _document(writers['evidencePin'])
    require(evidence == dict(schemaVersion='RegisteredMainWriterEvidence/v1',
            database=native.config['database'], redisDatabase=native.config['redisRebuild']['database'],
            objectBuckets=native.config['buckets'], writerContainerIds=writers['approvedWriterContainerIds'],
            exclusiveResources=writers['exclusiveResources']), 'MAIN_WRITER_EVIDENCE_SCOPE_MISMATCH')


def validate(target):
    value = target['mainApplication']
    require(target.get('replacement', {}).get('schemaVersion') == 'RegisteredApplicationReplacement/v2',
            'MAIN_TARGET_REPLACEMENT_V2_REQUIRED')
    require(type(value) is dict and set(value) == MAIN_FIELDS and
            value['schemaVersion'] == 'RegisteredMainApplication/v1', 'MAIN_TARGET_CONFIGURATION_INVALID')
    services = {row['role']: row for row in target['services']}
    roles = set(services); applications = roles - DATA_ROLES
    require(len(services) == len(target['services']) and len({s['id'] for s in target['services']}) == len(target['services']) and
            {'backend', 'frontend'} <= applications and
            DATA_ROLES <= roles and set(value['serviceConfigurationDigests']) == roles and
            set(value['networkAttachments']) == roles and
            all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v)
                for v in value['serviceConfigurationDigests'].values()), 'MAIN_SERVICE_BINDINGS_INVALID')
    require(set(target['application']['startOrder']) == applications and
            len(target['application']['startOrder']) == len(applications), 'APPLICATION_START_ORDER_INVALID')
    bindings = value['archiveImageBindings']
    require(type(bindings) is list and {b['role'] for b in bindings} == applications and
            len(bindings) == len(applications), 'MAIN_ARCHIVED_IMAGES_INCOMPLETE')
    for binding in bindings:
        require(set(binding) == {'role', 'versionPath', 'imageId'} and
                type(binding['versionPath']) is list and binding['versionPath'] and
                all(type(k) in (str, int) for k in binding['versionPath']) and
                type(binding['imageId']) is str and re.fullmatch('sha256:[0-9a-f]{64}', binding['imageId']),
                'MAIN_ARCHIVED_IMAGE_BINDING_INVALID')
    networks = value['networks']
    require(type(networks) is list and networks and
            len({n['id'] for n in networks}) == len(networks) and
            len({n['name'] for n in networks}) == len(networks), 'MAIN_NETWORK_BINDINGS_INVALID')
    ids = {row['id'] for row in services.values()}
    for network in networks:
        require(set(network) == NETWORK_FIELDS and re.fullmatch('[0-9a-f]{64}', network['id']) and
                network['driver'] in ('bridge', 'host') and type(network['internal']) is bool and
                type(network['enableIPv6']) is bool and
                type(network['memberContainerIds']) is list and
                len(set(network['memberContainerIds'])) == len(network['memberContainerIds']) and
                all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v)
                    for v in network['memberContainerIds']), 'MAIN_NETWORK_BINDINGS_INVALID')
        attached = {services[role]['id'] for role, attachments in value['networkAttachments'].items()
                    if network['name'] in attachments and attachments[network['name']]['networkId'] == network['id']}
        require(set(network['memberContainerIds']) & ids == attached, 'MAIN_NETWORK_BINDINGS_INVALID')
    known = {n['name']: n['id'] for n in networks}
    require(all(attachments and all(name in known and row['networkId'] == known[name]
                for name, row in attachments.items()) for attachments in value['networkAttachments'].values()),
            'MAIN_NETWORK_BINDINGS_INVALID')
    require(all(type(services[role].get('ip')) is str and services[role]['ip'] and
                services[role]['ip'] in {a['ipAddress'] for a in value['networkAttachments'][role].values()}
                for role in DATA_ROLES), 'MAIN_DATA_ENDPOINT_UNBOUND')
    require(type(value['configurationPins']) is list, 'MAIN_CONFIGURATION_PINS_INVALID')
    writers = value['writerAdmission']
    require(type(writers) is dict and set(writers) == {'schemaVersion', 'approvedWriterContainerIds',
            'exclusiveResources', 'evidencePin'} and writers['schemaVersion'] == 'RegisteredMainWriterCustody/v1' and
            writers['exclusiveResources'] == dict(database=True, objects=True, redis=True) and
            type(writers['approvedWriterContainerIds']) is list and writers['approvedWriterContainerIds'] and
            len(set(writers['approvedWriterContainerIds'])) == len(writers['approvedWriterContainerIds']) and
            set(writers['approvedWriterContainerIds']) <= {services[r]['id'] for r in applications} and
            services['backend']['id'] in writers['approvedWriterContainerIds'], 'MAIN_WRITER_CUSTODY_REQUIRED')
    return value


def application_inputs(native):
    value = validate(native.config)
    services = native.config_services
    for binding in value['archiveImageBindings']:
        matches = []
        for reference in native.material['versionPins']:
            item = _document(reference)
            try:
                for key in binding['versionPath']:
                    item = item[key]
            except (KeyError, IndexError, TypeError):
                continue
            matches.append(item)
        require(matches == [binding['imageId']] and
                services[binding['role']]['imageId'] == binding['imageId'], 'MAIN_ARCHIVED_IMAGE_MISMATCH')
    _writer_evidence(native, value)
    pins = {p['path']: p for p in value['configurationPins']}
    require(len(pins) == len(value['configurationPins']), 'MAIN_CONFIGURATION_PINS_INVALID')
    for reference in pins.values():
        require(pin(reference['path']) == reference, 'MAIN_PIN_CHANGED')
    for role in set(services) - DATA_ROLES:
        for mount in native.inspect(services[role]['id'])['Mounts']:
            # Main settings stay installed. A mount identity alone does not
            # prove the bytes of a configuration bind or a mounted artifact.
            require(not mount['RW'], 'MAIN_APPLICATION_WRITABLE_MOUNT_REJECTED')
            require(mount['Type'] == 'bind' and mount['Source'] in pins,
                    'MAIN_CONFIGURATION_MOUNT_UNPINNED')


def database_identity(native):
    if not enabled(native.config):
        require(native.db_uuid != native.material['sourceDatabaseUuid'], 'SOURCE_DATABASE_TARGET_REJECTED')
        return
    validate(native.config)
    require(native.db_uuid == native.config['replacement']['databaseUuid'], 'MAIN_DATABASE_IDENTITY_CHANGED')


def object_endpoint(native, endpoint):
    if not enabled(native.config):
        require(endpoint not in pinned_json(native.material['sourceScopePin'])['endpointHosts'], 'SOURCE_ENDPOINT_REJECTED')
        return
    validate(native.config)
    require(endpoint == 'http://' + native.config_services['minio']['ip'] + ':9000', 'MAIN_OBJECT_ENDPOINT_CHANGED')


def mysql_query(native, statement, *, mutation=False):
    return mysql_arguments(native, ['--batch', '--skip-column-names', '-e', statement], mutation=mutation)


def mysql_arguments(native, arguments, *, mutation=False):
    """Use a registered existing container without provisioning a client file."""
    script = ('test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; '
              'test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; '
              'IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"')
    return native.docker(['exec', '-i', native.db_container, 'sh', '-ec', script, 'registered-main-mysql',
        native.policy['environmentMysqlClientPath'], '--no-defaults', '--protocol=SOCKET', '--host=localhost',
        *arguments], input_bytes=(native.secret('mysql', 'MYSQL_ROOT_PASSWORD')+'\n').encode(), mutation=mutation)


def physical_mount(native, row):
    from recovery_replace import verify_services
    validate(native.config)
    verify_services(native, native.config['replacement'])
    mounts = [m for m in row['Mounts'] if m['Destination'] == native.policy['minioDataMount']]
    require(len(mounts) == 1 and mounts[0]['RW'] and mounts[0]['Type'] in ('volume', 'bind'),
            'MAIN_PHYSICAL_STORAGE_INVALID')
    return mounts[0]


def target_configuration(configuration, request, source):
    from recovery_minimal_plan import disjoint
    from recovery_replace import validate as replacement
    target = configuration['targets'][request['targetConfigRef']]
    validate(target); replacement(target)
    require(target['sourceConfigRef'] == request['sourceConfigRef'], 'TARGET_SOURCE_MISMATCH')
    root = absolute(target['dataRoot'])
    state = absolute(target['replacement']['stateRoot'])
    require(root.is_dir() and root != state and root.is_relative_to(state), 'MAIN_RUNTIME_ROOT_INVALID')
    require(all(disjoint(str(root), path) and all(disjoint(data, path) for data in target['dataPaths'])
                for path in [*source['archiveRoots'], configuration['operationsRoot']]),
            'MAIN_ARCHIVE_OR_OPERATION_OVERLAP')
    return target


def verify_runtime(native, *, states=True):
    value = validate(native.config)
    rows = {}
    for role, service in native.config_services.items():
        row = native.inspect(service['id']); rows[role] = row
        require(row['Id'] == service['id'] and row['Image'] == service['imageId'] and
                service_configuration_digest(row) == value['serviceConfigurationDigests'][role],
                'MAIN_SERVICE_CONFIGURATION_CHANGED')
        verify_network_attachments(native, role, row, value['networkAttachments'][role])
        require(not row['State']['Paused'] and not row['State']['Restarting'], 'MAIN_SERVICE_UNSTABLE')
        if states:
            running = role in ('mysql', 'redis') or role == 'minio' and native.storage_running or role in native.running_applications
            require(row['State']['Running'] is running, 'MAIN_SERVICE_RUNNING_STATE_CHANGED')
        current = {key: row[key] for key in ('Id', 'Image', 'Mounts', 'Path', 'Args', 'HostConfig', 'Config')}
        current['Mounts'] = sorted(row['Mounts'], key=lambda m: m['Destination'])
        if role in native.snapshots:
            require(current == native.snapshots[role], 'MAIN_SERVICE_CONFIGURATION_CHANGED')
        native.snapshots[role] = current
    for expected in value['networks']:
        network = json.loads(native.docker(['network', 'inspect', expected['id']]))
        require(type(network) is list and len(network) == 1 and
                network_configuration(network[0], expected['memberContainerIds']) ==
                    dict(expected, memberContainerIds=sorted(expected['memberContainerIds'])),
                'MAIN_NETWORK_CONFIGURATION_CHANGED')
        if expected['driver'] == 'bridge':
            running = {row['Id'] for role, row in rows.items() if row['State']['Running'] and
                       expected['name'] in value['networkAttachments'][role]}
            ambient = set(expected['memberContainerIds']) - {row['Id'] for row in rows.values()}
            require(set(network[0]['Containers']) == running | ambient, 'MAIN_NETWORK_MEMBERS_CHANGED')


def guarded_type(original):
    """Compose the explicit main contract without modifying the rehearsal path."""
    class MainData(original):
        supports_registered_main_targets = True

        def docker(self, args, **kwargs):
            if enabled(self.config) and args[:3] == ['exec', self.db_container,
                    self.policy['environmentMysqlClientPath']] and \
                    '--defaults-extra-file=/run/recovery/mysql-client.cnf' in args:
                arguments = [arg for arg in args[3:] if arg not in (
                    '--defaults-extra-file=/run/recovery/mysql-client.cnf', '--protocol=SOCKET', '--host=localhost')]
                require(kwargs.get('input_bytes') is None, 'MAIN_MYSQL_INPUT_CONFLICT')
                return mysql_arguments(self, arguments, mutation=kwargs.get('mutation', False))
            return super().docker(args, **kwargs)

        def replacement_preflight(self):
            if enabled(self.config):
                from recovery_replace import verify_services
                self.guard(); application_inputs(self); database_identity(self)
                verify_services(self, self.config['replacement']); verify_runtime(self, states=False)

        def bound(self, *, importing=False, minio_stopped=False):
            if not enabled(self.config):
                return super().bound(importing=importing, minio_stopped=minio_stopped)
            from recovery_replace import verify_services
            self.guard()
            verify_services(self, self.config['replacement'])
            verify_runtime(self)
            self.application_inputs()
            sql = self.modules['formal_sql_restore']
            (sql.import_database_state if importing else sql.database_state)(self.mysql, self.db_target)

        def application_inputs(self):
            if not enabled(self.config):
                return super().application_inputs()
            return application_inputs(self)

        def fresh_target(self):
            if not enabled(self.config):
                return super().fresh_target()
            from recovery_data_files import inventory
            self.bound(); self.application_inputs()
            self.modules['formal_sql_restore'].empty_database(self.mysql, self.db_target)
            mounts = [m for m in self.snapshots['minio']['Mounts'] if m['Destination'] == self.policy['minioDataMount']]
            require(len(mounts) == 1 and mounts[0]['RW'] and
                    inventory(absolute(mounts[0]['Source']), self.guard) == {}, 'MAIN_PHYSICAL_TARGET_NOT_EMPTY')
            script = 'IFS= read -r REDISCLI_AUTH; export REDISCLI_AUTH; exec "$@"'
            raw = self.docker(['exec', '-i', self.config_services['redis']['id'], 'sh', '-ec', script,
                'recovery-redis', self.config['redisClientPath'], '-n', str(self.config['redisRebuild']['database']),
                '--raw', 'DBSIZE'], input_bytes=(self.secret('redis', 'REDIS_PASSWORD')+'\n').encode())
            require(raw.strip() == b'0', 'REDIS_TARGET_NOT_EMPTY')

        def start_application(self):
            result = super().start_application()
            if enabled(self.config):
                result['isolation'] = 'REGISTERED_MAIN_RESOURCE_CUSTODY'
                result['configurationBindings'] = self.config['mainApplication']['configurationPins']
                result['programImagesChanged'] = False
            return result

    return MainData


def observe_main_target(control, value, selection):
    """Read-only control-plane identity observation; never return environment values."""
    configuration = control.document(selection['ownerConfigurationPin'])
    target = configuration['targets'][value['targetConfigRef']]
    validate(target); check_pin(target['dockerPin'], content=False)
    def docker(args, **kwargs):
        response = subprocess.run([target['dockerPin']['path'], '--host', 'unix:///var/run/docker.sock', *args],
            input=kwargs.get('input_bytes'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
        require(response.returncode == 0 and not response.stderr, 'MAIN_TARGET_OBSERVATION_FAILED')
        return response.stdout
    def inspect(identity):
        rows = json.loads(docker(['inspect', identity]))
        require(type(rows) is list and len(rows) == 1, 'MAIN_TARGET_OBSERVATION_FAILED')
        return rows[0]
    def secret(role, environment):
        reference = target['secrets'][role][environment]
        require(pin(reference['path']) == reference and
                stat.S_IMODE(absolute(reference['path']).stat().st_mode) == 0o600, 'MAIN_SECRET_CHANGED')
        raw = check_pin(reference).decode('utf-8')
        require(raw and not any(c in raw for c in '\r\n\0'), 'SECRET_FORMAT_INVALID')
        return raw
    services = {s['role']: s for s in target['services']}
    native = SimpleNamespace(config=target, config_services=services, docker=docker, inspect=inspect,
        source=configuration['sources'][value['sourceConfigRef']], secret=secret,
        db_container=services['mysql']['id'],
        policy=dict(target['dataPolicy'], environmentMysqlClientPath=configuration['environmentMysqlClientPath']),
        root=Path(configuration['operationsRoot']) / value['operationId'], snapshots={})
    native.database_uuid = lambda: mysql_query(native, 'SELECT @@server_uuid;').decode('ascii').strip()
    from recovery_replace import verify_services
    verify_services(native, target['replacement']); verify_runtime(native, states=False)
    observations = {}
    for role, service in services.items():
        row = inspect(service['id'])
        observations[service['id']] = dict(role=role, imageId=row['Image'], labels=row['Config']['Labels'],
            mounts=row['Mounts'], networks={k: v['networkId'] for k, v in network_attachments(row).items()},
            networkAttachments={k: v['networkId'] for k, v in network_attachments(row).items()},
            configuredNetworkMode=row['HostConfig'].get('NetworkMode'), configurationDigest=service_configuration_digest(row),
            state=row['State'], execIds=row.get('ExecIDs'))
    return dict(operationId=value['operationId'], targetConfigRef=value['targetConfigRef'],
        configurationPin=selection['ownerConfigurationPin'], targetId=target['targetId'],
        bootId=Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip(),
        machineId=target['machineId'], dockerEngineId=target['dockerEngineId'], services=observations)
