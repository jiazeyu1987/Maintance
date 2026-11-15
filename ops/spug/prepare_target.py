"""One fixed-host preparation task, using Spug authentication and host transport.

This operation ends at a registered empty target; it never starts a restore.
"""
import base64
from copy import deepcopy
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import threading
import time
import uuid

from smallapp_adapter import Refused
import smallapp_adapter as adapter

HOST = '172.30.30.59'
CONFIG = Path('/var/lib/intruoyi-spug/prepare-target.private.json')
STAGES = ('dependencies', 'cleanup', 'initialize')
ACTIVE = ('PENDING', 'RUNNING', 'UNKNOWN')
PROCESS = uuid.uuid4().hex


def need(ok, code):
    if not ok:
        raise Refused(code)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def configuration(path=None):
    path = CONFIG if path is None else Path(path)
    need(path.is_file(), 'PREPARATION_NOT_CONFIGURED')
    value = adapter.read_json(path)
    need(value.get('schemaVersion') == 'SpugPrepareTarget/v1' and value.get('host') == HOST,
         'PREPARATION_CONFIGURATION_INVALID')
    for key in ('applicationId', 'sourceConfigRef'):
        need(adapter.reference(value.get(key)), 'PREPARATION_CONFIGURATION_INVALID')
    for key in ('stateRoot', 'pythonPath'):
        need(isinstance(value.get(key), str) and value[key].startswith('/'),
             'PREPARATION_CONFIGURATION_INVALID')
    for key in ('nativeProgramPin', 'nativeConfigurationPin'):
        pin = value.get(key, {})
        need(isinstance(pin, dict) and set(pin) == {'path', 'bytes', 'sha256'} and
             isinstance(pin['path'], str) and pin['path'].startswith('/') and
             type(pin['bytes']) is int and pin['bytes'] > 0 and
             re.fullmatch('[a-f0-9]{64}', pin.get('sha256', '')), 'PREPARATION_CONFIGURATION_INVALID')
    return value


def public_configuration(path=None):
    try:
        configuration(path)
        return dict(configured=True, host=HOST, errorCode=None)
    except Refused as error:
        return dict(configured=False, host=HOST, errorCode=str(error))


def selection(value, config):
    need(type(value) is dict and set(value) == {'applicationId', 'recoveryPointRef'},
         'PREPARATION_REQUEST_INVALID')
    need(value['applicationId'] == config['applicationId'] and
         adapter.reference(value['recoveryPointRef']), 'PREPARATION_SELECTION_INVALID')
    return value


def request(value, config=None):
    need(type(value) is dict and set(value) == {'operationId', 'applicationId', 'recoveryPointRef',
                                              'planDigest', 'confirmed'}, 'PREPARATION_REQUEST_INVALID')
    need(adapter.reference(value['operationId']) and len(value['operationId']) >= 8 and
         adapter.reference(value['applicationId']) and adapter.reference(value['recoveryPointRef']) and
         isinstance(value['planDigest'], str) and re.fullmatch('[a-f0-9]{64}', value['planDigest']) and
         value['confirmed'] is True, 'PREPARATION_REQUEST_INVALID')
    if config is not None:
        need(value['applicationId'] == config['applicationId'], 'PREPARATION_SELECTION_INVALID')


class Tasks:
    def __init__(self, root):
        self.root = Path(root)

    def path(self, operation_id):
        need(adapter.reference(operation_id), 'PREPARATION_OPERATION_INVALID')
        return self.root / (hashlib.sha256(operation_id.encode()).hexdigest() + '.json')

    def get(self, operation_id):
        path = self.path(operation_id)
        need(path.is_file(), 'PREPARATION_OPERATION_NOT_FOUND')
        return adapter.read_json(path)

    def save(self, row):
        adapter.write_json(self.path(row['operationId']), row)

    def history(self):
        return sorted((adapter.read_json(p) for p in self.root.glob('*.json')),
                      key=lambda r:r['startedAt'], reverse=True)

    def reserve(self, value, user_id):
        request(value)
        path = self.path(value['operationId'])
        if path.exists():
            original = self.get(value['operationId'])
            need(original['request'] == value, 'PREPARATION_REQUEST_CHANGED')
            return original, False
        need(not any(r['state'] in ACTIVE for r in self.history()), 'PREPARATION_TARGET_BUSY')
        row = dict(operationId=value['operationId'], host=HOST, applicationId=value['applicationId'],
                   recoveryPointRef=value['recoveryPointRef'], request=deepcopy(value), ownerUserId=user_id,
                   workerProcess=PROCESS, state='PENDING', startedAt=now(), finishedAt=None, errorCode=None, targetConfigRef=None,
                   stages=[dict(name=name, state='PENDING', startedAt=None, finishedAt=None, errorCode=None)
                           for name in STAGES])
        self.root.mkdir(parents=True, exist_ok=True)
        adapter.write_json(path, row, exclusive=True)
        return row, True


def public_record(row):
    return {key:row.get(key) for key in ('operationId', 'host', 'applicationId', 'recoveryPointRef', 'state',
                                       'startedAt', 'finishedAt', 'errorCode', 'stages', 'targetConfigRef')}


def remote(config, action, value, emit=None):
    """Read small JSON events over the already registered Spug SSH identity."""
    from apps.host.models import Host
    hosts = Host.objects.filter(hostname=HOST, is_verified=True)
    need(hosts.count() == 1, 'PREPARATION_HOST_NOT_REGISTERED')
    payload = dict(action=action, request=value, configurationPin=config['nativeConfigurationPin'])
    bootstrap = '''import hashlib,importlib.util,json,sys
p=json.loads(sys.stdin.readline())
pin=p.pop('programPin'); raw=open(pin['path'],'rb').read()
if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise RuntimeError('PREPARATION_PROGRAM_CHANGED')
spec=importlib.util.spec_from_file_location('prepare_target_native',pin['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def emit(v):print(json.dumps(v,ensure_ascii=False),flush=True)
result=m.handle(p,emit)
if p['action']!='execute':emit(dict(type='result',record=result))
'''
    ssh = hosts.first().get_ssh()
    if config.get('sshTransport'):
        transport = config['sshTransport']
        need(transport == dict(host='host.docker.internal', port=18559), 'PREPARATION_TRANSPORT_INVALID')
        ssh.arguments.update(hostname=transport['host'], port=transport['port'])
    channel = None
    try:
        ssh.get_client()
        channel = ssh.client.get_transport().open_session(timeout=10)
        channel.settimeout(20)
        code = 'import base64;exec(compile(base64.b64decode(%r),"<prepare-target>","exec"))' % base64.b64encode(bootstrap.encode()).decode()
        channel.exec_command(shlex.quote(config['pythonPath']) + ' -B -c ' + shlex.quote(code))
        channel.sendall((json.dumps(dict(payload,programPin=config['nativeProgramPin']))+'\n').encode())
        channel.shutdown_write()
        buffer = b''
        result = None
        deadline = time.monotonic() + (7200 if action == 'execute' else 25)
        while True:
            need(time.monotonic() < deadline, 'PREPARATION_TRANSPORT_TIMEOUT')
            if channel.recv_ready():
                buffer += channel.recv(65536)
                need(len(buffer) <= 2*1024*1024, 'PREPARATION_RESPONSE_TOO_LARGE')
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if event.get('type') == 'result':
                        result = event['record']
                    elif event.get('type') == 'stage' and emit:
                        emit(event)
            elif channel.exit_status_ready():
                break
            else:
                time.sleep(.1)
        need(channel.recv_exit_status() == 0 and result is not None, 'PREPARATION_REMOTE_FAILED')
        return result
    finally:
        if channel is not None:
            channel.close()
        if ssh.client is not None:
            ssh.client.close()


def preview(value):
    config = configuration()
    selection(value, config)
    from prepare_target_registration import preflight
    preflight(config, value)
    import smallapp_entry as entry
    apps = entry.application_catalogue(entry.settings(), value['applicationId'])
    apps = [app for app in apps if app['applicationId'] == value['applicationId']]
    need(len(apps) == 1 and apps[0].get('validated') and
         value['recoveryPointRef'] in apps[0]['validated']['recoveryPointRefs'],
         'PREPARATION_POINT_UNAVAILABLE')
    plan = remote(config, 'preview', value)
    need(plan.get('host') == HOST and re.fullmatch('[a-f0-9]{64}',plan.get('planDigest','')),
         'PREPARATION_PLAN_INVALID')
    return {key:plan[key] for key in ('host','applicationId','recoveryPointRef','planDigest',
                                     'cleanupSummary','preserveSummary','stages')}


def block_while_preparing(value):
    """Called under the existing source submission lock by the restore entry."""
    if value.get('action') != 'RESTORE' or not CONFIG.is_file():
        return
    config = configuration()
    if value.get('targetConfigRef') in target_refs():
        need(not any(row['state'] in ACTIVE for row in Tasks(config['stateRoot']).history()),
             'PREPARATION_TARGET_BUSY')


def target_refs():
    import smallapp_simple
    refs = set()
    for binding in smallapp_simple.configuration()['bindings']:
        for name in ('targetServers','overwriteTargetServers'):
            target = binding.get(name,{}).get(HOST)
            if target:
                refs.add(target)
        refs.update(ref for ref, progress in binding.get('restoreProgressBindings',{}).items()
                    if progress.get('server') == HOST)
    return refs


def submit(value, user_id):
    config = configuration()
    request(value, config)
    import smallapp_entry as entry
    store = Tasks(config['stateRoot'])
    with entry.source_reservation_lock(config['sourceConfigRef'], entry.ENTRIES):
        if store.path(value['operationId']).exists():
            row, _ = store.reserve(value,user_id)
            return public_record(row)
        # Only this destination matters; do not re-query unrelated source history.
        targets = target_refs()
        for path in entry.ENTRIES.glob('*.json'):
            row = adapter.read_json(path)
            original = row.get('request',{})
            if original.get('action') != 'RESTORE' or original.get('targetConfigRef') not in targets or row.get('dispatchState') == 'CANCELLED_UNACCEPTED':
                continue
            journal = adapter.RECORDS / (hashlib.sha256(original['operationId'].encode()).hexdigest()+'.json')
            need(journal.is_file(), 'PREPARATION_TARGET_BUSY')
            result = adapter.execute(original,adapter.request_bridge(original),root=adapter.RECORDS,
                                     query_only=True,refresh_terminal=False)
            need(result.get('state') in ('SUCCEEDED','FAILED'), 'PREPARATION_TARGET_BUSY')
        from prepare_target_registration import preflight
        preflight(config,value)
        # Native execution checks the confirmed digest before its first stage.
        # Do not run source selection or remote preview a second time here.
        row, first = store.reserve(value,user_id)
    if first:
        from prepare_target_registration import publish
        threading.Thread(target=run_task,
            args=(store,value,config,lambda action,request,emit:remote(config,action,request,emit),publish),
            daemon=False).start()
    return public_record(row)


def run_task(store, value, config, invoke, publish):
    row = store.get(value['operationId'])
    row['state'] = 'RUNNING'
    store.save(row)
    def event(message):
        stage = message.get('stage',{})
        name = stage.get('name')
        need(name in STAGES and stage.get('state') in ('RUNNING','SUCCEEDED','FAILED'),
             'PREPARATION_PROGRESS_INVALID')
        current = row['stages'][STAGES.index(name)]
        current['state'] = stage['state']
        current['startedAt'] = current['startedAt'] or now()
        if stage['state'] != 'RUNNING':
            current['finishedAt'] = now()
        current['errorCode'] = stage.get('errorCode')
        need(current['errorCode'] is None or isinstance(current['errorCode'],str) and re.fullmatch('[A-Z0-9_:-]{1,160}',current['errorCode']),
             'PREPARATION_PROGRESS_INVALID')
        store.save(row)
    try:
        result = invoke('execute', value, event)
        for stage in result.get('stages',[]):
            event(dict(type='stage',stage=stage))
        need(result.get('state') == 'INITIALIZED', result.get('errorCode') or 'PREPARATION_NATIVE_FAILED')
        registered = publish(config,value,result)
        need(all(s['state']=='SUCCEEDED' for s in row['stages']), 'PREPARATION_STAGES_INCOMPLETE')
        row.update(state='READY',targetConfigRef=registered['targetConfigRef'],finishedAt=now())
    except Refused as error:
        unknown = str(error) in ('PREPARATION_TRANSPORT_TIMEOUT','PREPARATION_REMOTE_FAILED','PREPARATION_RESPONSE_TOO_LARGE')
        row.update(state='UNKNOWN' if unknown else 'FAILED',errorCode=str(error),finishedAt=now())
    except Exception:
        # A broken SSH response cannot prove whether the remote deletion stopped.
        row.update(state='UNKNOWN',errorCode='PREPARATION_CONNECTION_LOST',finishedAt=now())
    store.save(row)


def history():
    config = configuration()
    return [public_record(row) for row in Tasks(config['stateRoot']).history()]


def query(operation_id):
    config = configuration()
    store = Tasks(config['stateRoot'])
    row = store.get(operation_id)
    if row['state'] in ('PENDING','RUNNING') and row.get('workerProcess') != PROCESS:
        row.update(state='UNKNOWN',errorCode='PREPARATION_ENTRY_RESTARTED',finishedAt=now())
        store.save(row)
    return public_record(row)
