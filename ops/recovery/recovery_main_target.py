"""Explicit custody for restoring data into an existing main application.

This replaces rehearsal-only isolation assumptions with a registered identity
contract. It never provisions a resource or changes images, mounts or settings.
Only the authenticated safe-engine package installs the runtime mixin.
"""
from pathlib import Path
import ipaddress
import hashlib
import json
import re
import stat
import subprocess
from types import SimpleNamespace

from recovery_engine import absolute, check_pin, digest, pin, pinned_json, require, utc

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
    published = role in DATA_ROLES and published_endpoint(native.config, role) is not None
    if role in DATA_ROLES and not published or row['NetworkSettings']['Networks'][name].get('IPAMConfig'):
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
    if not fixed and not published:
        return False
    try:
        loopback = ipaddress.ip_address(service['ip']).is_loopback
    except ValueError:
        return False
    if not published and service['ip'] not in fixed and not (loopback and _published_host_port(row)):
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
                             configuration_pins, writer_evidence_pin, *, redis_authentication=None,
                             published_data_endpoints=None):
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
    if target.get('replacement', {}).get('storage', {}).get('schemaVersion') == 'RegisteredReplacementStorage/v3':
        require(redis_authentication is not None, 'MAIN_REDIS_AUTHENTICATION_REQUIRED')
        candidate.update(schemaVersion='RegisteredMainApplication/v2',
                         publishedDataEndpoints=[] if published_data_endpoints is None else published_data_endpoints,
                         redisAuthentication=redis_authentication)
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
    retained = type(value) is dict and value.get('schemaVersion') == 'RegisteredMainApplication/v2'
    require(target.get('replacement', {}).get('schemaVersion') == 'RegisteredApplicationReplacement/v2',
            'MAIN_TARGET_REPLACEMENT_V2_REQUIRED')
    require(type(value) is dict and set(value) == MAIN_FIELDS |
            ({'publishedDataEndpoints', 'redisAuthentication'} if retained else set()) |
            ({'archiveMountProtection'} if retained and 'archiveMountProtection' in value else set()) and
            value['schemaVersion'] in ('RegisteredMainApplication/v1', 'RegisteredMainApplication/v2'),
            'MAIN_TARGET_CONFIGURATION_INVALID')
    if retained:
        require(target['replacement'].get('storage', {}).get('schemaVersion') == 'RegisteredReplacementStorage/v3',
                'MAIN_RETAINED_STORAGE_V3_REQUIRED')
        auth = value['redisAuthentication']
        require(type(auth) is dict and (auth == dict(mode='PASSWORD') or
                set(auth) == {'mode', 'aclSha256'} and auth['mode'] == 'NONE' and
                type(auth['aclSha256']) is str and re.fullmatch('[0-9a-f]{64}', auth['aclSha256'])),
                'MAIN_REDIS_AUTHENTICATION_INVALID')
        require(auth['mode'] != 'NONE' or not target.get('secrets', {}).get('redis'),
                'MAIN_REDIS_UNEXPECTED_SECRET')
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
                (services[role]['ip'] in {a['ipAddress'] for a in value['networkAttachments'][role].values()} or
                 retained and published_endpoint(target, role) is not None)
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
    if retained:
        _published_contract(target)
        if 'archiveMountProtection' in value:
            from recovery_archive_view import validate as archive_contract
            archive_contract(value['archiveMountProtection'])
    return value


def published_endpoint(target, role):
    value = target.get('mainApplication', {})
    if value.get('schemaVersion') != 'RegisteredMainApplication/v2': return None
    rows = value.get('publishedDataEndpoints', [])
    return next((row for row in rows if type(row) is dict and row.get('role') == role), None)


def _published_contract(target):
    from recovery_published_fence import validate as fence_contract
    value = target['mainApplication']; entries = value['publishedDataEndpoints']
    require(type(entries) is list and len(entries) <= 1, 'MAIN_PUBLISHED_SCOPE_INVALID')
    services = {row['role']: row for row in target['services']}
    writers = value['writerAdmission']['approvedWriterContainerIds']
    approved = sorted(services[role]['ip'] for role in services if services[role]['id'] in writers)
    for entry in entries:
        require(type(entry) is dict and set(entry) == {'role', 'ip', 'port', 'containerPort', 'bindings', 'writeFence'} and
                entry['role'] == 'minio' and entry['ip'] == services['minio']['ip'] == '127.0.0.1' and
                type(entry['port']) is int and entry['port'] == 9000 and entry['containerPort'] == '9000/tcp',
                'MAIN_PUBLISHED_SCOPE_INVALID')
        bindings = entry['bindings']; ports = []
        require(type(bindings) is dict and entry['containerPort'] in bindings, 'MAIN_PUBLISHED_BINDING_INVALID')
        for port, rows in bindings.items():
            require(type(port) is str and re.fullmatch('[0-9]+/tcp', port) and 0 < int(port.split('/')[0]) <= 65535 and
                    type(rows) is list and len(rows) == 1 and type(rows[0]) is dict and
                    set(rows[0]) == {'HostIp', 'HostPort'} and rows[0]['HostIp'] in ('', '0.0.0.0') and
                    type(rows[0]['HostPort']) is str and rows[0]['HostPort'].isdigit() and
                    0 < int(rows[0]['HostPort']) <= 65535, 'MAIN_PUBLISHED_BINDING_INVALID')
            ports.append(int(rows[0]['HostPort']))
        require(len(set(ports)) == len(ports) and bindings['9000/tcp'][0]['HostPort'] == '9000',
                'MAIN_PUBLISHED_BINDING_INVALID')
        fence = fence_contract(entry['writeFence'])
        require(fence['ports'] == sorted(ports) and fence['allowedWriterIPv4'] == approved,
                'MAIN_PUBLISHED_FENCE_SCOPE_MISMATCH')


def published_fence(native):
    entry = published_endpoint(native.config, 'minio')
    if entry is None: return None
    from recovery_published_fence import PublishedFence
    return PublishedFence(entry['writeFence'], native.original['operationId'],
        Path(native.config['replacement']['stateRoot'])/native.original['operationId']/'published-fence', native.command)


def archive_view(native):
    value = native.config.get('mainApplication', {})
    configuration = value.get('archiveMountProtection')
    if configuration is None: return None
    from recovery_archive_view import ArchiveViewProtection, validate as archive_contract
    from recovery_replacement_storage import overlaps
    archive_contract(configuration)
    point = Path(configuration['mountIdentity']['mountPoint'])
    require(native.source['archiveRoots'] and all(Path(root) != point and Path(root).is_relative_to(point)
            for root in native.source['archiveRoots']) and
            all(not overlaps(str(point), path) for path in native.config['dataPaths']) and
            all(not overlaps(str(point), mount['Source']) for row in native.config['replacement']['storage'].get(
                'preservedApplicationMounts', []) for mount in [row['mount']]), 'ARCHIVE_VIEW_SCOPE_INVALID')
    return ArchiveViewProtection(configuration, native.original['operationId'],
        Path(native.config['replacement']['stateRoot'])/native.original['operationId']/'archive-view', native.command)


def mysql_scheduler(native, *, query=None):
    from recovery_mysql_scheduler import MainMysqlScheduler
    state = absolute(native.config['replacement']['stateRoot'])
    inherited = []
    for path in state.glob('*/recovery-consumption.json'):
        consumption = pinned_json(pin(path))
        if consumption['replacementOperationId'] != native.original['operationId']: continue
        clearance = pinned_json(consumption['clearancePin'])
        require(consumption['clearancePin']['path'] == str(path.parent/'recovery-clearance.json') and
                all(clearance[k] == native.original[k] for k in
                    ('sourceConfigRef', 'recoveryPointRef', 'targetConfigRef')), 'MAIN_SCHEDULER_CLEARANCE_CHANGED')
        if 'schedulerCustodyPin' in clearance: inherited.append(clearance['schedulerCustodyPin'])
    require(len(inherited) <= 1, 'MAIN_SCHEDULER_CLEARANCE_CHANGED')
    return MainMysqlScheduler(native.config, native.original['operationId'],
        state/native.original['operationId']/'mysql-scheduler',
        query or (lambda statement, mutation=False: mysql_query(native, statement, mutation=mutation)),
        inherited=inherited[0] if inherited else None)


def release_retained_protections(configuration, request, root, claim):
    """Called under both recovery locks after terminated-failure observation.

    Writers stay stopped. Only their exact original mount/rules are restored;
    scheduler custody stays paused and is carried into the next operation.
    """
    target = configuration['targets'][request['targetConfigRef']]
    if not enabled(target): return {}
    from recovery_retained_retry import ReadOnlyTarget, append
    native = ReadOnlyTarget(configuration, request, root)
    native.original = request
    native.policy = dict(native.policy, environmentMysqlClientPath=configuration['environmentMysqlClientPath'])
    native.secret = lambda role, name: check_pin(target['secrets'][role][name]).decode('utf-8')
    rows = {role: native.inspect(service['id']) for role, service in native.config_services.items()}
    require(all(row['State']['Running'] is (role in ('mysql', 'redis')) for role, row in rows.items()),
            'RECOVERY_TARGET_MUST_REMAIN_QUIESCED')
    journal = claim/'protection-recovery'; journal.mkdir(mode=0o700)
    def command(arguments, *, mutation=False):
        index = len(list(journal.glob('*-intent.json')))+1
        intent = append(journal/('%04d-intent.json' % index), dict(arguments=arguments,
            mutation=mutation, startedAt=utc()))
        response = subprocess.run(arguments, input=None, capture_output=True, timeout=30)
        append(journal/('%04d-exit.json' % index), dict(intentPin=intent,
            actualExitCode=response.returncode, stdoutSha256=hashlib.sha256(response.stdout).hexdigest(),
            stderrSha256=hashlib.sha256(response.stderr).hexdigest(), finishedAt=utc()))
        require(response.returncode == 0 and not response.stderr, 'RECOVERY_PROTECTION_COMMAND_FAILED')
        return response.stdout
    native.command = command
    protections = [(name, value) for name, value in
        (('archive', archive_view(native)), ('published', published_fence(native))) if value is not None]
    for _, value in protections: value.verify()
    original = [pin(path) for _, value in protections for path in sorted(value.journal.iterdir()) if path.is_file()]
    extra = {}
    if (claim/'mysql-scheduler').exists():
        def scheduler_query(statement, *, mutation=False):
            require(not mutation, 'RECOVERY_OBSERVATION_WRITE_REJECTED')
            return (native.query(statement)+'\n').encode('utf-8')
        extra['schedulerCustodyPin'] = mysql_scheduler(native, query=scheduler_query).recovery_custody()
    append(journal/'handoff-intent.json', dict(operationId=request['operationId'],
        targetConfigurationSha256=digest(target), originalPins=original, **extra, startedAt=utc()))
    released = [dict(kind=name, pin=value.release()) for name, value in protections]
    receipt = append(claim/'main-protection-recovery.json', dict(schemaVersion='RetainedMainProtectionRecovery/v1',
        operationId=request['operationId'], targetConfigurationSha256=digest(target),
        originalPins=original, releasePins=released, **extra, finishedAt=utc()))
    return dict(mainProtectionRecoveryPin=receipt, **extra)


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
    if value['schemaVersion'] == 'RegisteredMainApplication/v2':
        from recovery_replacement_storage import verify_preserved_mounts
        rows = {role: native.inspect(service['id']) for role, service in services.items()}
        verify_preserved_mounts(native.config['replacement']['storage'], rows)
        return
    for role in set(services) - DATA_ROLES:
        for mount in native.inspect(services[role]['id'])['Mounts']:
            # Main settings stay installed. A mount identity alone does not
            # prove the bytes of a configuration bind or a mounted artifact.
            require(not mount['RW'], 'MAIN_APPLICATION_WRITABLE_MOUNT_REJECTED')
            require(mount['Type'] == 'bind' and mount['Source'] in pins,
                    'MAIN_CONFIGURATION_MOUNT_UNPINNED')


def redis_password(native):
    """Use explicit existing authentication, never an empty or invented secret."""
    value = native.config.get('mainApplication', {})
    if value.get('schemaVersion') != 'RegisteredMainApplication/v2' or \
            value.get('redisAuthentication', {}).get('mode') != 'NONE':
        return native.secret('redis', 'REDIS_PASSWORD')
    import hashlib
    validate(native.config)
    row = native.inspect(native.config_services['redis']['id'])
    require(not row['HostConfig'].get('PortBindings') and not row['HostConfig'].get('PublishAllPorts') and
            row['HostConfig'].get('NetworkMode') != 'host', 'MAIN_REDIS_NOAUTH_PUBLISHED')
    prefix = ['exec', row['Id'], native.config['redisClientPath'], '--raw']
    require(native.docker([*prefix, 'CONFIG', 'GET', 'requirepass']) == b'requirepass\n\n',
            'MAIN_REDIS_AUTHENTICATION_CHANGED')
    acl = native.docker([*prefix, 'ACL', 'LIST'])
    require(hashlib.sha256(acl).hexdigest() == value['redisAuthentication']['aclSha256'],
            'MAIN_REDIS_ACL_CHANGED')
    return None


def redis_command(native, arguments, *, mutation=False):
    password = redis_password(native)
    if password is None:
        return native.docker(['exec', native.config_services['redis']['id'], native.config['redisClientPath'],
            *arguments], mutation=mutation)
    script = 'IFS= read -r REDISCLI_AUTH; export REDISCLI_AUTH; exec "$@"'
    return native.docker(['exec', '-i', native.config_services['redis']['id'], 'sh', '-ec', script,
        'recovery-redis', native.config['redisClientPath'], *arguments],
        input_bytes=(password+'\n').encode(), mutation=mutation)


def verify_redis_authentication(native):
    value = native.config.get('mainApplication', {})
    if value.get('schemaVersion') == 'RegisteredMainApplication/v2' and \
            value.get('redisAuthentication', {}).get('mode') == 'NONE':
        redis_password(native)


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
        if value['schemaVersion'] == 'RegisteredMainApplication/v2' and role in DATA_ROLES:
            endpoint = published_endpoint(native.config, role)
            require((row['HostConfig'].get('PortBindings') or {}) == (endpoint['bindings'] if endpoint else {}) and
                    not row['HostConfig'].get('PublishAllPorts') and row['HostConfig'].get('NetworkMode') != 'host',
                    'MAIN_PUBLISHED_BINDING_CHANGED')
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
    if published_endpoint(native.config, 'minio') is not None:
        writers = value['writerAdmission']['approvedWriterContainerIds']
        require(all(any((attachment.get('IPAMConfig') or {}).get('IPv4Address') ==
                        native.config_services[role]['ip'] for attachment in row['NetworkSettings']['Networks'].values())
                    for role, row in rows.items() if row['Id'] in writers), 'MAIN_PUBLISHED_WRITER_ADDRESS_NOT_FIXED')
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
                verify_redis_authentication(self)
                verify_services(self, self.config['replacement']); verify_runtime(self, states=False)
                fence = published_fence(self)
                if fence is not None: fence.preflight()
                archive = archive_view(self)
                if archive is not None: archive.preflight()
                mysql_scheduler(self).preflight()

        def replacement_write_fence(self):
            if enabled(self.config):
                archive = archive_view(self)
                if archive is not None: archive.install()
                fence = published_fence(self)
                if fence is not None: fence.install()

        def replacement_quiescence(self):
            if enabled(self.config): mysql_scheduler(self).install()
            if enabled(self.config) and self.config['mainApplication']['schemaVersion'] == 'RegisteredMainApplication/v2':
                fence = published_fence(self)
                if fence is not None: fence.verify()
                archive = archive_view(self)
                if archive is not None: archive.verify()
                database = self.config['database']
                queries = ("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID<>CONNECTION_ID() "
                           "AND USER NOT IN ('event_scheduler','mysql.infoschema','mysql.session','mysql.sys') "
                           "AND HOST NOT LIKE 'localhost%';", "SELECT COUNT(*) FROM information_schema.EVENTS WHERE "
                           "EVENT_SCHEMA='"+database+"' AND STATUS='ENABLED';")
                require(all(self.mysql.query(query).strip() == '0' for query in queries), 'MAIN_DATABASE_WRITERS_NOT_QUIESCED')
                clients = redis_command(self, ['--raw', 'CLIENT', 'LIST']).decode('utf-8')
                clients = [dict(part.split('=', 1) for part in line.split() if '=' in part) for line in clients.splitlines()]
                require(clients and all(row.get('addr', '').startswith('127.0.0.1:') for row in clients),
                        'MAIN_REDIS_WRITERS_NOT_QUIESCED')

        def replacement_finish(self):
            result = {}
            if enabled(self.config):
                archive = archive_view(self)
                if archive is not None: result['archiveViewReleasePin'] = archive.release()
                fence = published_fence(self)
                if fence is not None:
                    result['publishedWriteFenceReleasePin'] = fence.release()
                result['mysqlSchedulerReleasePin'] = mysql_scheduler(self).release()
            return result

        def bound(self, *, importing=False, minio_stopped=False):
            if not enabled(self.config):
                return super().bound(importing=importing, minio_stopped=minio_stopped)
            from recovery_replace import verify_services
            self.guard()
            verify_services(self, self.config['replacement'])
            verify_runtime(self)
            self.application_inputs()
            verify_redis_authentication(self)
            fence = published_fence(self)
            if fence is not None: fence.verify()
            archive = archive_view(self)
            if archive is not None: archive.verify()
            mysql_scheduler(self).verify()
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
            raw = redis_command(self, ['-n', str(self.config['redisRebuild']['database']), '--raw', 'DBSIZE'])
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
    verify_redis_authentication(native)
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
