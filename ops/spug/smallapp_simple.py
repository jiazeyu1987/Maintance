"""Registered simple-page choices and read-only progress via existing Spug host SSH."""
import base64
import json
from pathlib import Path
import shlex

import smallapp_adapter as adapter

CONFIG = Path('/var/lib/intruoyi-spug/smallapp-simple-settings.json')


def configuration():
    value = adapter.read_json(CONFIG)
    if set(value) != {'nas', 'servers', 'bindings'} or len(value['servers']) != 3:
        raise adapter.Refused('SIMPLE_CONFIGURATION_INVALID')
    if any(type(row.get('selectable')) is not bool for row in value['bindings']):
        raise adapter.Refused('SIMPLE_BINDING_SELECTION_STATE_REQUIRED')
    if any(not isinstance(row.get('overwriteTargetServers'), dict) for row in value['bindings']):
        raise adapter.Refused('SIMPLE_REPLACEMENT_MAPPING_REQUIRED')
    current = [(row['product'], row['server'], row['mode'])
               for row in value['bindings'] if row['selectable']]
    identities = [row['applicationId'] for row in value['bindings']]
    if len(current) != len(set(current)) or len(identities) != len(set(identities)):
        raise adapter.Refused('SIMPLE_BINDING_AMBIGUOUS')
    return value


def public_configuration():
    value = configuration()
    return dict(nas=value['nas'], servers=value['servers'], bindings=[{
        k: row[k] for k in ('product', 'server', 'mode', 'applicationId', 'targetServers', 'overwriteTargetServers', 'selectable')
    } for row in value['bindings']])


def progress_binding(record, config):
    rows = [row for row in config['bindings'] if row['applicationId'] == record['applicationId']]
    if len(rows) != 1 or not rows[0].get('progressRoot'):
        raise adapter.Refused('STEP_TELEMETRY_NOT_REGISTERED')
    binding = rows[0]
    request = record['request']
    if request['action'] == 'RESTORE':
        target = request['targetConfigRef']
        routes = binding.get('restoreProgressBindings', {})
        if not isinstance(routes, dict):
            raise adapter.Refused('RESTORE_TELEMETRY_BINDING_INVALID')
        if target in routes:
            route = routes[target]
            if not isinstance(route, dict) or set(route) != {'server', 'progressRoot', 'pythonPath', 'sshTransport'}:
                raise adapter.Refused('RESTORE_TELEMETRY_BINDING_INVALID')
            # targetServers selects today's fresh target for a server. Original
            # operations keep their explicit per-target telemetry route after
            # that selector advances to another fresh target on the same host.
            if route['server'] not in binding['targetServers']:
                raise adapter.Refused('RESTORE_TELEMETRY_TARGET_MISMATCH')
            binding = dict(binding, **route)
        elif binding['targetServers'].get(binding['server']) != target:
            raise adapter.Refused('RESTORE_TELEMETRY_NOT_REGISTERED')
    return binding


def progress(record):
    from apps.host.models import Host
    binding = progress_binding(record, configuration())
    hosts = Host.objects.filter(hostname=binding['server'], is_verified=True)
    if hosts.count() != 1:
        raise adapter.Refused('PROGRESS_HOST_NOT_REGISTERED')
    source = Path(__file__).with_name('smallapp_progress_remote.py').read_bytes()
    payload = json.dumps(dict(root=binding['progressRoot'], request=record['request'])).encode()
    # Code and JSON are encoded separately; no user-controlled shell interpolation.
    code = "import base64,io,sys;sys.stdin=io.StringIO(base64.b64decode(%r).decode());exec(compile(base64.b64decode(%r),'<progress>','exec'))" % (
        base64.b64encode(payload).decode(), base64.b64encode(source).decode())
    ssh = hosts.first().get_ssh()
    if 'sshTransport' in binding:
        transport = binding['sshTransport']
        if transport['host'] != 'host.docker.internal' or transport['port'] not in (18557, 18558, 18559):
            raise adapter.Refused('PROGRESS_TRANSPORT_INVALID')
        ssh.arguments.update(hostname=transport['host'], port=transport['port'])
    try:
        ssh.get_client()
        channel = ssh.client.get_transport().open_session(timeout=10)
        channel.settimeout(15)
        channel.exec_command(shlex.quote(binding['pythonPath']) + ' -B -c ' + shlex.quote(code))
        raw = bytearray()
        while True:
            data = channel.recv(4096)
            if not data:
                break
            raw.extend(data)
            if len(raw) > 262144:
                channel.close()
                raise adapter.Refused('STEP_TELEMETRY_TOO_LARGE')
        status = channel.recv_exit_status()
        channel.close()
    except (OSError, TimeoutError):
        raise adapter.Refused('STEP_TELEMETRY_CONNECTION_FAILED') from None
    finally:
        if ssh.client is not None:
            ssh.client.close()
    if status != 0:
        raise adapter.Refused('STEP_TELEMETRY_READ_FAILED')
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise adapter.Refused('STEP_TELEMETRY_INVALID') from None
    if value.get('operationId') != record['request']['operationId']:
        raise adapter.Refused('STEP_TELEMETRY_OPERATION_MISMATCH')
    return value
