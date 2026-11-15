"""Publish one prepared .59 target through the existing restore configuration."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import uuid

import smallapp_adapter as adapter
import smallapp_entry as entry

HOST = '172.30.30.59'


def require(condition, code):
    if not condition:
        raise adapter.Refused(code)


def preflight(config, request):
    """Check the local publication inputs before the remote cleanup starts."""
    publication = config.get('publication', {})
    require(all(isinstance(publication.get(k), str) and Path(publication[k]).is_absolute()
                for k in ('entrySettings', 'bridgeSettings', 'simpleSettings')),
            'PREPARE_REGISTRATION_CONFIGURATION_REQUIRED')
    documents = {name: adapter.read_json(publication[name])
                 for name in ('entrySettings', 'bridgeSettings', 'simpleSettings')}
    entry.settings(publication['entrySettings'])
    app_id = request.get('applicationId')
    apps = [a for a in documents['entrySettings']['applications'] if a['applicationId'] == app_id]
    bindings = [b for b in documents['simpleSettings'].get('bindings', []) if b.get('applicationId') == app_id]
    require(len(apps) == len(bindings) == 1 and bindings[0].get('mode') == 'safe'
            and adapter.reference(apps[0].get('sourceConfigRef')),
            'PREPARE_REGISTRATION_APPLICATION_INVALID')
    credential = publication.get('credentialRef')
    require(isinstance(credential, str) and re.fullmatch(r'[A-Za-z0-9_.-]+\.json', credential)
            and isinstance(adapter.read_json(Path(publication['bridgeSettings']).parent / credential).get('headers'), dict),
            'PREPARE_REGISTRATION_CREDENTIAL_REQUIRED')
    require(publication.get('sshTransport') == {'host': 'host.docker.internal', 'port': 18559},
            'PREPARE_REGISTRATION_TRANSPORT_INVALID')
    return documents


def publish(config, request, result):
    """Expose READY only after the ordinary restore admission accepts the target.

    The caller holds the preparation job lock. A failed publication is reported
    as failed, without rerunning cleanup or attempting an automatic rollback.
    """
    documents = preflight(config, request)
    publication = config['publication']
    target = result.get('targetConfigRef')
    source = result.get('sourceConfigRef')
    port = result.get('listenPort')
    require(result.get('state') == 'INITIALIZED' and adapter.reference(target)
            and result.get('listenAddress') == HOST and type(port) is int and 1024 <= port <= 65535
            and re.fullmatch(r'[0-9a-f]{64}', result.get('registrationSha256', '')),
            'PREPARE_REGISTRATION_TARGET_INVALID')
    require(all(isinstance(result.get(k), str) and result[k].startswith('/')
                for k in ('progressRoot', 'pythonPath')), 'PREPARE_REGISTRATION_PROGRESS_INVALID')
    app = next(a for a in documents['entrySettings']['applications'] if a['applicationId'] == request['applicationId'])
    require(source == app['sourceConfigRef'], 'PREPARE_REGISTRATION_SOURCE_MISMATCH')
    paths = {key: Path(publication[key]) for key in documents}
    originals = {key: path.read_bytes() for key, path in paths.items()}
    require(all(json.loads(originals[key]) == documents[key] for key in documents),
            'PREPARE_REGISTRATION_CONFIGURATION_CHANGED')
    updated = deepcopy(documents)
    updated_app = next(a for a in updated['entrySettings']['applications'] if a['applicationId'] == request['applicationId'])
    if target not in updated_app['targetConfigRefs']:
        updated_app['targetConfigRefs'].append(target)
    updated_app['registrationSha256'] = result['registrationSha256']
    origin = f'http://{HOST}:{port}'
    filename = 'prepared-target-' + hashlib.sha256(target.encode()).hexdigest()[:24] + '.json'
    connection = dict(sourceConfigRefs=[source], targetConfigRefs=[target],
                      submitUrl=origin + '/operations', queryUrlTemplate=origin + '/operations/{operationId}',
                      selectionUrl=origin + '/selections', credentialRef=publication['credentialRef'],
                      selectedTargetPreflight=True)
    connection_path = paths['bridgeSettings'].parent / filename
    if connection_path.exists():
        require(adapter.read_json(connection_path) == connection, 'PREPARE_REGISTRATION_ROUTE_CONFLICT')
    else:
        adapter.write_json(connection_path, connection, exclusive=True)
    bridge = updated['bridgeSettings']
    bridge.setdefault('targetConnections', {})[target] = filename
    for binding in bridge.get('registrationBindings', []):
        if binding.get('applicationId') == request['applicationId']:
            binding['registrationSha256'] = result['registrationSha256']
    binding = next(b for b in updated['simpleSettings']['bindings'] if b['applicationId'] == request['applicationId'])
    binding.setdefault('targetServers', {})[HOST] = target
    binding.setdefault('restoreProgressBindings', {})[target] = dict(server=HOST,
        progressRoot=result['progressRoot'], pythonPath=result['pythonPath'], sshTransport=publication['sshTransport'])

    # A private staged routing file exercises the real bridge without publishing
    # a visible target before the controller has proved that it is usable.
    staged = paths['bridgeSettings'].with_name('prepare-routing-' + uuid.uuid4().hex + '.json')
    adapter.write_json(staged, bridge, exclusive=True)
    try:
        restore = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId=request['operationId'],
                       action='RESTORE', sourceConfigRef=source, parentChainRef=None,
                       recoveryPointRef=request['recoveryPointRef'], targetConfigRef=target)
        entry.admit_selection(restore, updated['entrySettings'], adapter.HttpBridge(staged, source, target))
    finally:
        staged.unlink()
    for key in ('bridgeSettings', 'entrySettings', 'simpleSettings'):
        require(paths[key].read_bytes() == originals[key], 'PREPARE_REGISTRATION_CONFIGURATION_CHANGED')
        adapter.write_json(paths[key], updated[key])
    return dict(targetConfigRef=target, sourceConfigRef=source, registered=True)
