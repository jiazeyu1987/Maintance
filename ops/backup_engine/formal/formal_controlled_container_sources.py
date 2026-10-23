"""Private, finite PROD A container originals. No action or presence authority.

Original stopped/created state is preserved. This contract neither proves
absence nor replaces complete writer scope, lease, boot or action guards.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import stat
import subprocess
import tempfile
import time
from datetime import datetime

import formal_boot_state as boot
import formal_original_launch as launch
import formal_snapshot_linux as snapshot

STATE_FIELDS=('Pid','Status','Running','Paused','Restarting','Dead','OOMKilled','ExitCode','StartedAt','FinishedAt')
STATIC_FIELDS={'Config':'config','HostConfig':'hostConfig','Image':'image','Path':'path','Args':'args','Mounts':'mounts'}
LIMIT=1048576

class ControlledSourceError(RuntimeError):
    pass

def _need(value,code):
    if not value:raise ControlledSourceError('CONTROLLED_CONTAINER_'+code)

def controlled_inspect_projection(raw,container_id,image_id,name):
    """Hash complete launch fields, retaining actual stable original state."""
    _need(type(container_id) is str and re.fullmatch('[0-9a-f]{64}',container_id),'IDENTITY_INVALID')
    _need(type(image_id) is str and re.fullmatch('sha256:[0-9a-f]{64}',image_id),'IDENTITY_INVALID')
    _need(type(name) is str and re.fullmatch('/[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',name),'IDENTITY_INVALID')
    _need(type(raw) is bytes and 0<len(raw)<=LIMIT,'OUTPUT_LIMIT')
    try:
        rows=json.loads(raw.decode('utf-8',errors='strict'),object_pairs_hook=launch._pairs,parse_constant=launch._nonfinite)
        _need(type(rows) is list and len(rows)==1 and type(rows[0]) is dict,'JSON_INVALID')
        value=rows[0]
        _need(all(k in value for k in (*STATIC_FIELDS,'Id','Name','State')),'FIELDS_MISSING')
        _need(value['Id']==container_id and value['Image']==image_id and value['Name']==name,'IDENTITY_CHANGED')
        _need(type(value['Config']) is dict and type(value['HostConfig']) is dict and type(value['Path']) is str and
            type(value['Args']) is list and all(type(a) is str for a in value['Args']) and
            type(value['Mounts']) is list and all(type(m) is dict for m in value['Mounts']),'FIELDS_INVALID')
        state=value['State']
        _need(type(state) is dict and all(k in state for k in STATE_FIELDS) and
            type(state['Pid']) is int and state['Pid']>=0 and type(state['ExitCode']) is int and
            0<=state['ExitCode']<=255 and all(type(state[k]) is bool for k in
                ('Running','Paused','Restarting','Dead','OOMKilled')) and
            not any(state[k] for k in ('Paused','Restarting','Dead')),'STATE_INVALID')
        _need((state['Running'] and state['Pid']>0 and state['Status']=='running') or
            (not state['Running'] and state['Pid']==0 and state['Status'] in ('created','exited')),'STATE_UNSTABLE')
        for key in ('StartedAt','FinishedAt'):
            _need(type(state[key]) is str and re.fullmatch(
                r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,9})?Z',state[key]),'STATE_INVALID')
            datetime.fromisoformat(state[key][:-1]+'+00:00')
        private={k:value[k] for k in STATIC_FIELDS}
        private['Mounts']=sorted(private['Mounts'],key=launch._canonical)
        digests={prefix+'Sha256':launch._sha(launch._canonical(private[k])) for k,prefix in STATIC_FIELDS.items()}
        digests['launchSha256']=launch._sha(launch._canonical(private))
        return dict(present=True,containerId=container_id,imageId=image_id,name=name,digests=digests,
            runtimeState={k:state[k] for k in STATE_FIELDS},productionEvidence=False,serviceActionsPerformed=False)
    except (ValueError,UnicodeError,TypeError,RecursionError,launch.LaunchObservationError):
        raise ControlledSourceError('CONTROLLED_CONTAINER_JSON_INVALID') from None

def _time(deadline):
    try:launch._remaining(deadline)
    except launch.LaunchObservationError:raise ControlledSourceError('CONTROLLED_CONTAINER_DEADLINE') from None

def _private_runtime(guard,deadline):
    _need(os.name=='posix' and os.geteuid()==0 and callable(guard),'NATIVE_OWNER_REQUIRED')
    snapshot.observation_timeout(1);_time(deadline)

def _parent(path):
    selected=boot._absolute(str(path))
    _need(selected.name not in ('','.','..'),'PATH_INVALID')
    return selected

def _summary(path,raw,signature):
    value=json.loads(raw.decode('utf-8'),object_pairs_hook=launch._pairs,parse_constant=launch._nonfinite)[0]
    projected=controlled_inspect_projection(raw,value['Id'],value['Image'],value['Name'])
    return dict(schemaVersion='formal-controlled-container-original/v1',path=str(path),
        rawSha256=hashlib.sha256(raw).hexdigest(),rawBytes=len(raw),signature=list(signature),source=projected)

def verify_controlled_inspect_original(path,expected,*,guard,deadline):
    """Read actual sealed bytes; return a pure identity/time check for late use."""
    _private_runtime(guard,deadline)
    try:
        selected=_parent(path);expected_raw=launch._canonical(expected)
        guard();_time(deadline)
        with boot._directory(selected.parent,no_atime=True) as (directory,identity):
            _need(stat.S_IMODE(os.fstat(directory).st_mode)==0o700,'DIRECTORY_UNTRUSTED')
            raw,signature=boot._read_at(directory,selected.name,0o600,LIMIT,no_atime=True)
            result=_summary(selected,raw,signature)
            _need(launch._canonical(result)==expected_raw,'ORIGINAL_CHANGED')
            guard();_time(deadline)
            _need(boot._read_at(directory,selected.name,0o600,LIMIT,no_atime=True)==(raw,signature),'ORIGINAL_CHANGED')
            def terminal():
                try:
                    _need(launch._canonical(expected)==expected_raw,'ORIGINAL_CHANGED')
                    boot._directory_unchanged(selected.parent,identity)
                    _need(boot._signature(os.stat(selected,follow_symlinks=False))==signature,'ORIGINAL_CHANGED')
                    _time(deadline)
                except (OSError,ValueError,TypeError,RecursionError,snapshot.FormalSnapshotError):
                    raise ControlledSourceError('CONTROLLED_CONTAINER_ORIGINAL_CHANGED') from None
            terminal()
            return result,terminal
    except (OSError,KeyError,IndexError,ValueError,UnicodeError,TypeError,RecursionError,
            snapshot.FormalSnapshotError,launch.LaunchObservationError):
        raise ControlledSourceError('CONTROLLED_CONTAINER_ORIGINAL_INVALID') from None

def seal_controlled_inspect_original(path,raw,container_id,image_id,name,*,guard,deadline):
    """Exclusive root-owned/fsynced original; uncertainty leaves it retained."""
    _private_runtime(guard,deadline)
    projected=controlled_inspect_projection(raw,container_id,image_id,name)
    try:
        selected=_parent(path);guard();_time(deadline)
        with boot._directory(selected.parent,no_atime=True) as (directory,identity):
            _need(stat.S_IMODE(os.fstat(directory).st_mode)==0o700,'DIRECTORY_UNTRUSTED')
            flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC
            _time(deadline)
            fd=os.open(selected.name,flags,0o600,dir_fd=directory)
            with os.fdopen(fd,'wb') as output:
                os.fchmod(output.fileno(),0o600);output.write(raw);output.flush();os.fsync(output.fileno())
            os.fsync(directory)
            copied,signature=boot._read_at(directory,selected.name,0o600,LIMIT,no_atime=True)
            _need(copied==raw,'ORIGINAL_CHANGED');boot._directory_unchanged(selected.parent,identity)
            result=_summary(selected,copied,signature)
            _need(result['source']==projected,'ORIGINAL_CHANGED')
        result,terminal=verify_controlled_inspect_original(selected,result,guard=guard,deadline=deadline)
        terminal();_time(deadline)
        return result
    except (OSError,snapshot.FormalSnapshotError):
        raise ControlledSourceError('CONTROLLED_CONTAINER_ORIGINAL_WRITE_FAILED') from None

class NativeControlledDockerSources:
    """Fixed endpoint readonly inputs. Private inspect is never logged."""
    def inventory(self,deadline):
        return launch._bounded_command(['/usr/bin/docker','--host','unix:///var/run/docker.sock',
            'ps','--all','--no-trunc','--format','{{.ID}}\t{{.Names}}'],deadline=deadline,limit=LIMIT)
    def inspect(self,identity,deadline):
        _need(type(identity) is str and re.fullmatch('[0-9a-f]{64}',identity),'IDENTITY_INVALID')
        return launch._bounded_command(['/usr/bin/docker','--host','unix:///var/run/docker.sock',
            'inspect',identity],deadline=deadline,limit=LIMIT)

def _selection(expected):
    _need(type(expected) is dict and set(expected)=={'present','containerId','imageId','name'} and
        type(expected['present']) is bool and type(expected['name']) is str and
        re.fullmatch('/[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',expected['name']),'SELECTION_INVALID')
    if expected['present']:
        _need(type(expected['containerId']) is str and re.fullmatch('[0-9a-f]{64}',expected['containerId']) and
            type(expected['imageId']) is str and re.fullmatch('sha256:[0-9a-f]{64}',expected['imageId']),'SELECTION_INVALID')
    else:_need(expected['containerId'] is None and expected['imageId'] is None,'SELECTION_INVALID')

def _selected_inventory(raw,expected):
    _need(type(raw) is bytes and len(raw)<=LIMIT and (not raw or raw.endswith(b'\n')),'INVENTORY_INVALID')
    names={};identities=set()
    for line in raw.decode('ascii',errors='strict').splitlines():
        columns=line.split('\t')
        _need(len(columns)==2 and re.fullmatch('[0-9a-f]{64}',columns[0]) and
            re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',columns[1]),'INVENTORY_INVALID')
        identity,name=columns
        _need(name not in names and identity not in identities,'INVENTORY_INVALID')
        names[name]=identity;identities.add(identity)
    selected=names.get(expected['name'][1:])
    _need(selected==expected['containerId'] if expected['present'] else selected is None,'PRESENCE_CHANGED')
    return selected

def _observe_controlled_container_source(expected,*,guard,deadline,transport=None):
    _need(os.name=='posix' and os.geteuid()==0 and callable(guard),'NATIVE_OWNER_REQUIRED')
    try:
        _selection(expected);binding=launch._canonical(expected)
        launch._remaining(deadline)
        native=NativeControlledDockerSources() if transport is None else transport
        observed=[];retained=None
        for _ in range(2):
            guard();launch._remaining(deadline)
            _need(launch._canonical(expected)==binding,'SELECTION_CHANGED')
            _selected_inventory(native.inventory(deadline),expected)
            if expected['present']:
                retained=native.inspect(expected['containerId'],deadline)
                source=controlled_inspect_projection(retained,expected['containerId'],expected['imageId'],expected['name'])
            else:source=dict(present=False,containerId=None,imageId=None,name=expected['name'],digests=None,
                runtimeState=None,productionEvidence=False,serviceActionsPerformed=False)
            observed.append(source)
        # No owner callback after the final native source read.
        _need(observed[0]==observed[1] and launch._canonical(expected)==binding,'SOURCE_CHANGED')
        launch._remaining(deadline)
        return retained,observed[-1]
    except (OSError,ValueError,UnicodeError,TypeError,RecursionError,launch.LaunchObservationError,
            snapshot.FormalSnapshotError):
        raise ControlledSourceError('CONTROLLED_CONTAINER_SOURCE_UNAVAILABLE') from None

def observe_controlled_container_source(expected,*,guard,deadline,transport=None):
    """Finite selected presence/launch observation, no secrets or action grant."""
    return _observe_controlled_container_source(expected,guard=guard,deadline=deadline,transport=transport)[1]

def capture_controlled_container_source(path,expected,*,guard,deadline,transport=None):
    """Seal actual present source; absent never becomes an invented inspect."""
    _selection(expected);_need(expected['present'],'PRESENT_ORIGINAL_REQUIRED')
    raw,observed=_observe_controlled_container_source(expected,guard=guard,deadline=deadline,transport=transport)
    result=seal_controlled_inspect_original(path,raw,expected['containerId'],expected['imageId'],expected['name'],guard=guard,deadline=deadline)
    result,terminal=verify_controlled_inspect_original(path,result,guard=guard,deadline=deadline)
    current=observe_controlled_container_source(expected,guard=guard,deadline=deadline,transport=transport)
    _need(current==observed==result['source'],'SOURCE_CHANGED')
    terminal()
    try:launch._remaining(deadline)
    except launch.LaunchObservationError:raise ControlledSourceError('CONTROLLED_CONTAINER_DEADLINE') from None
    return result


def _execute_controlled_script(argv,body,*,deadline,action):
    """Bound only the client. An uncertain action has no retry or completion."""
    _need(os.name=='posix' and os.geteuid()==0 and type(action) is bool,'NATIVE_OWNER_REQUIRED')
    _need(type(body) is bytes and 0<len(body)<=16384,'COMMAND_INVALID')
    _time(deadline)
    until=time.monotonic()+min(90 if action else 15,launch._remaining(deadline),snapshot.observation_timeout(90))
    child=None;selector=None;output=bytearray()
    try:
        # Private unnamed stdin avoids blocking an unbounded pipe write.
        with tempfile.TemporaryFile(dir='/tmp') as source:
            source.write(body);source.flush();source.seek(0)
            child=subprocess.Popen(argv,stdin=source,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LC_ALL':'C'})
            selector=selectors.DefaultSelector()
            selector.register(child.stdout,selectors.EVENT_READ,'stdout')
            selector.register(child.stderr,selectors.EVENT_READ,'stderr')
            while selector.get_map():
                events=selector.select(launch._remaining(until))
                _need(events,'COMMAND_UNCERTAIN')
                for key,_ in events:
                    raw=os.read(key.fileobj.fileno(),min(65536,LIMIT-len(output)+1) if key.data=='stdout' else 1)
                    if not raw:selector.unregister(key.fileobj);continue
                    _need(key.data=='stdout' and len(output)+len(raw)<=LIMIT,'COMMAND_UNCERTAIN')
                    output.extend(raw)
            _need(child.wait(timeout=launch._remaining(until))==0,'COMMAND_UNCERTAIN')
            _time(deadline)
            return bytes(output)
    except (OSError,ValueError,subprocess.TimeoutExpired,launch.LaunchObservationError,snapshot.FormalSnapshotError):
        raise ControlledSourceError('CONTROLLED_CONTAINER_COMMAND_UNCERTAIN') from None
    finally:
        if selector is not None:selector.close()
        if child is not None:
            if child.poll() is None:
                child.kill()  # Only this client; Docker's TERM grace remains unlimited.
                try:child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    raise ControlledSourceError('CONTROLLED_CONTAINER_CLIENT_TERMINATION_UNCERTAIN') from None
            for stream in (child.stdout,child.stderr):stream.close()


def _controlled_script(boot_id,*,remote,kind,identity=None,before=None,wire_sha=None):
    _need(type(boot_id) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',boot_id),'BOOT_INVALID')
    _need(kind in ('inventory','inspect','stop','start'),'ACTION_INVALID')
    body='set -euo pipefail\numask 077\nassert_peer() {\n'
    if remote is not None:
        body+=(' read -r caller_ip caller_port bound_ip bound_port extra <<< "${SSH_CONNECTION:-}"\n'
            ' test "$bound_ip" = '+shlex.quote(remote)+' || exit 61\n'
            ' test "$bound_port" = 22 && test -n "$caller_ip" && test -n "$caller_port" && test -z "$extra" || exit 61\n')
    body+=' test "$(cat /proc/sys/kernel/random/boot_id)" = '+shlex.quote(boot_id)+' || exit 61\n}\nassert_peer\n'
    docker=('env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin /usr/bin/timeout --signal=TERM --kill-after=5 90 '
        '/usr/bin/docker --host unix:///var/run/docker.sock ')
    inventory=docker+"ps --all --no-trunc --format "+shlex.quote('{{.ID}}\t{{.Names}}')
    if kind=='inventory':return (body+inventory+'\nassert_peer\n').encode()
    _need(type(identity) is str and re.fullmatch('[0-9a-f]{64}',identity),'IDENTITY_INVALID')
    # Mounts is first: replacement must not select a nested Config/HostConfig key.
    fields=['"Mounts":[]']+['"'+k+'":{{json .'+k+'}}' for k in ('Id','Name','Image','Config','HostConfig','Path','Args')]
    fields.append('"State":{'+','.join('"'+k+'":{{json .State.'+k+'}}' for k in STATE_FIELDS)+'}')
    template='[{'+','.join(fields)+'}]\n{{range .Mounts}}{{json .}}{{println}}{{end}}'
    body+=('normalized_inspect() {\n'
        ' dump=$('+docker+'inspect --format '+shlex.quote(template)+' '+identity+')\n'
        ' base="${dump%%$\x27\\n\x27*}"\n mounts=""\n'
        ' if [[ "$dump" == *$\x27\\n\x27* ]]; then\n'
        '  mounts=$(printf "%s\\n" "$dump" | /usr/bin/tail -n +2 | env LC_ALL=C /usr/bin/sort | /usr/bin/paste -sd, -)\n fi\n'
        ' printf "%s\\n" "${base/\\\"Mounts\\\":[]/\\\"Mounts\\\":[$mounts]}"\n}\n')
    if kind=='inspect':return (body+'normalized_inspect\nassert_peer\n').encode()
    _need(type(before) is dict and before.get('containerId')==identity and
        type(wire_sha) is str and re.fullmatch('[0-9a-f]{64}',wire_sha),'ACTION_INVALID')
    name=before['name'][1:]
    # Positive fixed inventory in this same execution rejects same-name replacement.
    body+=('inventory=$('+inventory+')\nselected=0\n'
        'while IFS=$\x27\\t\x27 read -r observed_id observed_name extra; do\n'
        ' [[ "$observed_id" =~ ^[0-9a-f]{64}$ && "$observed_name" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$ && -z "$extra" ]] || exit 62\n'
        ' if [[ "$observed_id" = '+identity+' || "$observed_name" = '+shlex.quote(name)+' ]]; then\n'
        '  test "$observed_id" = '+identity+' && test "$observed_name" = '+shlex.quote(name)+' || exit 62\n'
        '  selected=$((selected+1))\n fi\ndone <<< "$inventory"\ntest "$selected" = 1 || exit 62\n'
        'observed_row=$(normalized_inspect)\n'
        'observed_sha=$(printf "%s\\n" "$observed_row" | /usr/bin/sha256sum)\n'
        'test "${observed_sha%% *}" = '+wire_sha+' || exit 62\nassert_peer\n'+docker+
        ('stop --signal SIGTERM --timeout -1 ' if kind=='stop' else 'start ')+identity+'\nassert_peer\n')
    return body.encode()


class NativeControlledDockerActions:
    """Exact local boot/socket and one-shot, complete conditional action wire."""
    def __init__(self,boot_id):
        _controlled_script(boot_id,remote=None,kind='inventory')
        self._boot_id=boot_id;self._observations={}
    def _run(self,kind,deadline,*,identity=None,before=None,wire_sha=None):
        body=_controlled_script(self._boot_id,remote=None,kind=kind,identity=identity,before=before,wire_sha=wire_sha)
        return _execute_controlled_script(['/bin/bash','--noprofile','--norc','-s'],body,
            deadline=deadline,action=kind in ('stop','start'))
    def inventory(self,deadline):return self._run('inventory',deadline)
    def inspect(self,identity,deadline):
        raw=self._run('inspect',deadline,identity=identity)
        try:
            value=json.loads(raw.decode('utf-8'),object_pairs_hook=launch._pairs,parse_constant=launch._nonfinite)[0]
            observed=controlled_inspect_projection(raw,identity,value['Image'],value['Name'])
        except (ValueError,UnicodeError,TypeError,KeyError,IndexError,RecursionError,launch.LaunchObservationError):
            raise ControlledSourceError('CONTROLLED_CONTAINER_SOURCE_UNAVAILABLE') from None
        _need(raw.endswith(b'\n') and b'\n' not in raw[:-1],'WIRE_INVALID')
        self._observations[identity]=(launch._canonical(observed),hashlib.sha256(raw).hexdigest())
        return raw
    def action(self,before,action,deadline):
        _need(type(before) is dict and type(before.get('containerId')) is str and action in ('stop','start'),'ACTION_INVALID')
        observed=self._observations.pop(before['containerId'],None)
        _need(observed is not None and observed[0]==launch._canonical(before),'FRESH_OBSERVATION_REQUIRED')
        raw=self._run(action,deadline,identity=before['containerId'],before=before,wire_sha=observed[1])
        _need(raw==(before['containerId']+'\n').encode('ascii'),'ACTION_UNCERTAIN')


class SshControlledDockerActions(NativeControlledDockerActions):
    """Same SSH peer/boot/key/socket/full wire, without remote Python."""
    def __init__(self,connection):
        import formal_external_callers as callers
        try:
            _need(type(connection) is dict and connection.get('host') in set(callers.HOSTS.values()),'CONNECTION_INVALID')
            callers._connection(connection,connection['host'])
            self._connection=json.loads(launch._canonical(connection))
            self._connection_pin=launch._canonical(connection)
            self._keys=callers._known_hosts_bytes(self._connection)
            _need(hashlib.sha256(self._keys).hexdigest()==connection['knownHostsSha256'],'HOST_KEYS_CHANGED')
        except (OSError,snapshot.FormalSnapshotError,ValueError,TypeError):
            raise ControlledSourceError('CONTROLLED_CONTAINER_CONNECTION_INVALID') from None
        super().__init__(self._connection['bootId'])
    def _run(self,kind,deadline,*,identity=None,before=None,wire_sha=None):
        import formal_external_callers as callers
        try:
            connection=self._connection
            _need(launch._canonical(connection)==self._connection_pin and
                callers._known_hosts_bytes(connection)==self._keys,'HOST_KEYS_CHANGED')
            body=_controlled_script(self._boot_id,remote=connection['host'],kind=kind,
                identity=identity,before=before,wire_sha=wire_sha)
            argv=['/usr/bin/ssh','-F','/dev/null','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
                '-o','UserKnownHostsFile='+connection['knownHostsFile'],'-o','GlobalKnownHostsFile=/dev/null',
                '-o','UpdateHostKeys=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=10',
                '-o','ConnectionAttempts=1','-p','22','root@'+connection['host'],'/bin/bash --noprofile --norc -s']
            result=_execute_controlled_script(argv,body,deadline=deadline,action=kind in ('stop','start'))
            _need(launch._canonical(connection)==self._connection_pin and
                callers._known_hosts_bytes(connection)==self._keys,'HOST_KEYS_CHANGED')
            _time(deadline)
            return result
        except (OSError,snapshot.FormalSnapshotError,ValueError,TypeError):
            raise ControlledSourceError('CONTROLLED_CONTAINER_CONNECTION_UNCERTAIN') from None


def _same_launch(original,current):
    return all(current[k]==original[k] for k in ('present','containerId','imageId','name','digests'))


def _normal_stop(original,current):
    before=original['runtimeState'];after=current['runtimeState']
    return (not after['Running'] and after['Status']=='exited' and after['Pid']==0 and
        after['ExitCode']==0 and not after['OOMKilled'] and after['StartedAt']==before['StartedAt'] and
        datetime.fromisoformat(after['FinishedAt'][:-1]+'+00:00')>
            datetime.fromisoformat(before['StartedAt'][:-1]+'+00:00'))


def run_controlled_container_action(original,before,action,*,guard,deadline,transport):
    """Native action primitive, never approval/claim/complete-source authority.

    Normal owner must retain its owned intent before calling and supply its
    independent lease/ingress/host/resume guard. A failure leaves that intent
    uncertain; this primitive never retries, creates, removes or releases.
    """
    _private_runtime(guard,deadline);_need(action in ('stop','start'),'ACTION_INVALID')
    try:
        original_pin=launch._canonical(original);before_pin=launch._canonical(before)
        saved,terminal=verify_controlled_inspect_original(original['path'],original,guard=guard,deadline=deadline)
        source=saved['source'];state=source['runtimeState']
        _need(state['Running'] and not state['OOMKilled'] and state['ExitCode']==0,'ORIGINAL_RUNNING_REQUIRED')
        selected={k:source[k] for k in ('present','containerId','imageId','name')}
        current=observe_controlled_container_source(selected,guard=guard,deadline=deadline,transport=transport)
        _need(_same_launch(source,current) and current==before,'SOURCE_CHANGED')
        _need(current==source if action=='stop' else _normal_stop(source,current),'ACTION_STAGE_INVALID')
        terminal();_need(launch._canonical(before)==before_pin and launch._canonical(original)==original_pin,'SOURCE_CHANGED')
        _time(deadline)
        transport.action(current,action,deadline)
        _time(deadline)
        saved,terminal=verify_controlled_inspect_original(original['path'],original,guard=guard,deadline=deadline)
        after=observe_controlled_container_source(selected,guard=guard,deadline=deadline,transport=transport)
        _need(_same_launch(saved['source'],after),'SOURCE_CHANGED')
        if action=='stop':_need(_normal_stop(source,after),'ACTION_UNCERTAIN')
        else:
            restored=after['runtimeState']
            _need(restored['Running'] and not restored['OOMKilled'] and restored['ExitCode']==0 and
                datetime.fromisoformat(restored['StartedAt'][:-1]+'+00:00')>
                    datetime.fromisoformat(current['runtimeState']['FinishedAt'][:-1]+'+00:00'),'ACTION_UNCERTAIN')
        terminal();_need(launch._canonical(before)==before_pin and launch._canonical(original)==original_pin,'SOURCE_CHANGED')
        _time(deadline)
        return dict(state='CONTROLLED_CONTAINER_ACTION_OBSERVED',source=after,action=action,
            serviceActionsPerformed=True,productionEvidence=False,releaseReady=False)
    except (OSError,KeyError,ValueError,UnicodeError,TypeError,RecursionError,snapshot.FormalSnapshotError,launch.LaunchObservationError):
        raise ControlledSourceError('CONTROLLED_CONTAINER_ACTION_UNCERTAIN') from None


class ControlledSharedContainerActions:
    """Seven sealed originals joined to the existing owned shared journal.

    This is the real native source/action adapter, not a complete source owner,
    role approval or lease. The owner must pin the approved role selection and
    maintain all external/host/config/ingress guards independently.
    """
    ROLES={'mysql','frontend','backend','showroom','onlyoffice','redis','minio'}
    def __init__(self,originals,transport):
        try:
            _need(type(originals) is dict and set(originals)==self.ROLES,'SHARED_SCOPE_INVALID')
            self._originals=json.loads(launch._canonical(originals));self._pin=launch._canonical(self._originals)
            identities=[r['source']['containerId'] for r in self._originals.values()]
            paths=[r['path'] for r in self._originals.values()]
            _need(len(set(identities))==7 and len(set(paths))==7 and
                all(r['source']['present'] is True for r in self._originals.values()),'SHARED_SCOPE_INVALID')
            self._transport=transport
        except (KeyError,ValueError,TypeError,RecursionError):
            raise ControlledSourceError('CONTROLLED_CONTAINER_SHARED_SCOPE_INVALID') from None

    @staticmethod
    def _reduced_matches(row,source,private):
        snapshot._container_stable(row)
        return (row['id']==source['containerId'] and row['name']==source['name'] and row['image']==source['imageId'] and
            launch._canonical(sorted(row['mounts'],key=launch._canonical))==
                launch._canonical(sorted(private['Mounts'],key=launch._canonical)) and
            row['restartPolicy']==private['HostConfig']['RestartPolicy'] and
            row['state']=={k:source['runtimeState'][k] for k in row['state']})

    def assert_role(self,role,original,current,*,guard,deadline):
        _private_runtime(guard,deadline)
        try:
            _need(role in self.ROLES and launch._canonical(self._originals)==self._pin,'SHARED_SCOPE_CHANGED')
            receipt=self._originals[role]
            _,terminal=verify_controlled_inspect_original(receipt['path'],receipt,guard=guard,deadline=deadline)
            selected=_parent(receipt['path'])
            with boot._directory(selected.parent,no_atime=True) as (directory,_):
                raw,signature=boot._read_at(directory,selected.name,0o600,LIMIT,no_atime=True)
                _need(_summary(selected,raw,signature)==receipt,'ORIGINAL_CHANGED')
                private=json.loads(raw.decode('utf-8'),object_pairs_hook=launch._pairs,parse_constant=launch._nonfinite)[0]
            source=receipt['source']
            _need(self._reduced_matches(original,source,private),'SHARED_SCOPE_CHANGED')
            selection={k:source[k] for k in ('present','containerId','imageId','name')}
            observed=observe_controlled_container_source(selection,guard=guard,deadline=deadline,transport=self._transport)
            _need(_same_launch(source,observed) and self._reduced_matches(current,observed,private),'SHARED_SCOPE_CHANGED')
            if not source['runtimeState']['Running']:_need(observed==source,'ORIGINAL_STOPPED_CHANGED')
            elif observed['runtimeState']['Running'] and observed['runtimeState']['StartedAt']==source['runtimeState']['StartedAt']:
                _need(observed==source,'RUNTIME_CHANGED')
            terminal();_need(launch._canonical(self._originals)==self._pin,'SHARED_SCOPE_CHANGED');_time(deadline)
            return observed
        except (OSError,KeyError,ValueError,UnicodeError,TypeError,RecursionError,snapshot.FormalSnapshotError,launch.LaunchObservationError):
            raise ControlledSourceError('CONTROLLED_CONTAINER_SHARED_SCOPE_CHANGED') from None

    def action(self,role,action,original,current,*,guard,deadline):
        observed=self.assert_role(role,original,current,guard=guard,deadline=deadline)
        result=run_controlled_container_action(self._originals[role],observed,action,
            guard=guard,deadline=deadline,transport=self._transport)
        _need(launch._canonical(self._originals)==self._pin,'SHARED_SCOPE_CHANGED');_time(deadline)
        return result
