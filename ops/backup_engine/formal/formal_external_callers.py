"""Fixed four external callers of the formal store, with retained exact actions.

This controls only the registered Docker callers. A current stopped observation
does not exclude other clients, host writers or later administrator actions.
Full ingress/host exclusion, dependency health and final release remain separate.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import time
from datetime import datetime, timezone

import formal_snapshot_linux as snapshot

ROLES = ('test-backend', 'test-rehearsal', 'backup-backend', 'backup-rehearsal')
HOSTS = dict(zip(ROLES, ('172.30.30.58',) * 2 + ('172.30.30.59',) * 2))
NAMES = dict(zip(ROLES, ('/intruoyi-backend', '/intruoyi-rehearsal-backend') * 2))
CONNECTION_KEYS = {'host', 'port', 'user', 'bootId', 'knownHostsFile',
                   'knownHostsSha256', 'dockerEndpoint'}


def _known_hosts_bytes(connection):
    path = snapshot._existing_file(connection['knownHostsFile'])
    info = path.stat()
    snapshot.require(0 < info.st_size <= 1024 * 1024 and (os.name != 'posix' or
        info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) & 0o022 == 0),
        'FORMAL_CALLER_HOST_KEYS_INVALID')
    return path.read_bytes()


class SshDockerTransport:
    """Linux control-host SSH; exact peer, boot, socket and conditional action.

    Any timeout or disconnect is uncertain. No retry, alternate host key, Docker
    context, remote Python dependency, or raw SSH diagnostic is accepted.
    """
    def __init__(self):
        self._observations = {}

    @staticmethod
    def _key(connection, record):
        return hashlib.sha256(snapshot._canonical_bytes([connection, record])).hexdigest()

    def _run(self, connection, identity, *, action=None, before_sha=None,health_seconds=None):
        snapshot.require(type(connection) is dict and connection.get('host') in set(HOSTS.values()),
                         'FORMAL_CALLER_CONNECTION_INVALID')
        _connection(connection, connection['host'])
        snapshot.require(type(identity) is str and re.fullmatch('[0-9a-f]{64}', identity),
                         'FORMAL_CALLER_IDENTITY_CHANGED')
        keys = _known_hosts_bytes(connection)
        snapshot.require(hashlib.sha256(keys).hexdigest() == connection['knownHostsSha256'],
                         'FORMAL_CALLER_HOST_KEYS_CHANGED')
        # The remote checks run before every inspect/action in the same SSH call.
        # A full byte digest of the immediately observed inspect row is checked
        # again remotely just before a stop/start. Local observation is not enough.
        body = ('set -euo pipefail\n'
            'read -r caller_ip caller_port bound_ip bound_port extra <<< "${SSH_CONNECTION:-}"\n'
            'test "$bound_ip" = ' + shlex.quote(connection['host']) + ' || exit 61\n'
            'test -z "$extra" || exit 61\n'
            'test "$(cat /proc/sys/kernel/random/boot_id)" = ' + shlex.quote(connection['bootId']) + ' || exit 61\n')
        docker = ('env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin /usr/bin/timeout '
                  '--signal=TERM --kill-after=5 90 /usr/bin/docker --host unix:///var/run/docker.sock ')
        # Docker older daemons iterate mounts in unstable map order. Preserve
        # every mount byte/value but sort the complete JSON rows on this peer,
        # from a single inspect, before caching/conditionally checking its SHA.
        template=snapshot.CONTAINER_INSPECT_TEMPLATE.replace('{{json .Mounts}}','[]')+'\n{{range .Mounts}}{{json .}}{{println}}{{end}}'
        body+=('normalized_inspect() {\n'
            ' dump=$('+docker+'inspect --format '+shlex.quote(template)+' '+identity+')\n'
            ' base="${dump%%$\x27\\n\x27*}"\n'
            ' mounts=""\n'
            ' if [[ "$dump" == *$\x27\\n\x27* ]]; then\n'
            '  mounts=$(printf "%s\\n" "$dump" | /usr/bin/tail -n +2 | env LC_ALL=C /usr/bin/sort | /usr/bin/paste -sd, -)\n'
            ' fi\n'
            ' printf "%s\\n" "${base/\\\"mounts\\\":[]/\\\"mounts\\\":[$mounts]}"\n'
            '}\n')
        inspect='normalized_inspect'
        if health_seconds is not None:
            snapshot.require(action is None and type(before_sha) is str and re.fullmatch('[0-9a-f]{64}',before_sha),
                'FORMAL_CALLER_HEALTH_PROOF_INVALID')
            budget=snapshot.observation_timeout(health_seconds)
            snapshot.require(0<budget<=8,'FORMAL_CALLER_HEALTH_DEADLINE')
            # Fixed host nsenter/curl are required. No image-local tool, proxy,
            # SSH forwarding, alternate endpoint or remote Python is selected.
            body+=('assert_runtime() {\n observed_row=$('+inspect+')\n'
                ' observed_sha=$(printf "%s\\n" "$observed_row" | /usr/bin/sha256sum)\n'
                ' test "${observed_sha%% *}" = '+before_sha+' || exit 62\n}\nassert_runtime\n'
                'pid=$('+docker+'inspect --format '+shlex.quote('{{.State.Pid}}')+' '+identity+')\n'
                '[[ "$pid" =~ ^[1-9][0-9]*$ ]] || exit 63\n'
                'exec {health_ns_fd}<"/proc/$pid/ns/net"\n'
                'namespace=$(/usr/bin/stat -Lc %i "/proc/$$/fd/$health_ns_fd")\n'
                'host_namespace=$(/usr/bin/stat -Lc %i /proc/self/ns/net)\n'
                'test "$namespace" != "$host_namespace" || exit 63\n'
                'assert_namespace() {\n assert_runtime\n'
                ' test "$('+docker+'inspect --format '+shlex.quote('{{.State.Pid}}')+' '+identity+')" = "$pid" || exit 63\n'
                ' test "$(/usr/bin/stat -Lc %i "/proc/$pid/ns/net")" = "$namespace" || exit 63\n}\n'
                'assert_namespace\nprintf "%s %s\\n" "$pid" "$namespace"\n'
                'set +e\n'
                'env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin /usr/bin/timeout --signal=TERM --kill-after=5 '+str(budget)+' '
                '/usr/bin/nsenter --net="/proc/$$/fd/$health_ns_fd" '
                '/usr/bin/curl --disable --noproxy '+shlex.quote('*')+' --request GET --raw --include --silent '
                '--connect-timeout 2 --max-time '+str(max(1,int(budget)))+' '
                '--header '+shlex.quote('Accept-Encoding: identity')+' --header '+shlex.quote('Connection: close')+' '
                'http://127.0.0.1:48081/actuator/health | /usr/bin/head -c 98305\n'
                'pipeline=("${PIPESTATUS[@]}")\nset -e\n'
                'test "${pipeline[1]}" = 0 || exit 64\n'
                'test "${pipeline[0]}" = 0 || test "${pipeline[0]}" = 7 || exit 64\n'
                'assert_namespace\nprintf "\\nFORMAL_CURL_EXIT=%s\\n" "${pipeline[0]}"\n'
                'exec {health_ns_fd}<&-\n')
        elif action is None:
            body += inspect + '\n'
        else:
            snapshot.require(action in ('stop', 'start') and type(before_sha) is str and
                re.fullmatch('[0-9a-f]{64}', before_sha), 'FORMAL_CALLER_ACTION_INVALID')
            body += ('observed_row=$(' + inspect + ')\n'
                     'observed_sha=$(printf "%s\\n" "$observed_row" | sha256sum)\n'
                     'test "${observed_sha%% *}" = ' + before_sha + ' || exit 62\n' +
                     # Bound the CLI/SSH lifetime, never the daemon's TERM grace
                     # period. A disconnected stop remains uncertain and its
                     # retained intent blocks retry and following mutations.
                     docker + ('stop --timeout -1 --signal SIGTERM ' if action == 'stop' else 'start ') + identity + '\n')
        args = ['/usr/bin/ssh', '-F', '/dev/null', '-T', '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + connection['knownHostsFile'],
            '-o', 'GlobalKnownHostsFile=/dev/null', '-o', 'UpdateHostKeys=no',
            '-o', 'ClearAllForwardings=yes', '-o', 'ConnectTimeout=10', '-o', 'ConnectionAttempts=1',
            '-p', '22', 'root@' + connection['host'], '/bin/bash --noprofile --norc -s']
        try:
            result = subprocess.run(args, input=body.encode('utf-8'), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=snapshot.observation_timeout(110), check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise snapshot.FormalSnapshotError('FORMAL_CALLER_SSH_UNCERTAIN') from None
        snapshot.require(result.returncode == 0 and not result.stderr and len(result.stdout) <= (98400 if health_seconds is not None else 65536),
                         'FORMAL_CALLER_SSH_FAILED')
        snapshot.require(_known_hosts_bytes(connection) == keys, 'FORMAL_CALLER_HOST_KEYS_CHANGED')
        return result.stdout

    def inspect(self, connection, identity):
        raw = self._run(connection, identity)
        try: record = json.loads(raw)
        except (ValueError, UnicodeError):
            raise snapshot.FormalSnapshotError('FORMAL_CALLER_INSPECT_INVALID') from None
        snapshot._container_stable(record)
        snapshot.require(record['id'] == identity and raw.endswith(b'\n') and b'\n' not in raw[:-1],
                         'FORMAL_CALLER_INSPECT_INVALID')
        self._observations[self._key(connection, record)] = hashlib.sha256(raw).hexdigest()
        return record

    def action(self, connection, before, action):
        key = self._key(connection, before)
        snapshot.require(key in self._observations, 'FORMAL_CALLER_FRESH_OBSERVATION_REQUIRED')
        digest = self._observations.pop(key)
        raw = self._run(connection, before['id'], action=action, before_sha=digest)
        snapshot.require(raw == (before['id'] + '\n').encode('ascii'), 'FORMAL_CALLER_ACTION_UNCERTAIN')

    def observe_http(self,connection,record,role,seconds):
        snapshot.require(role in ROLES and record['name']==NAMES[role] and record['state']['Running'],
            'FORMAL_CALLER_HEALTH_PROOF_INVALID')
        deadline=_health_deadline(seconds);token=snapshot.observation_deadline.set(deadline)
        try:
            snapshot.require(self.inspect(connection,record['id'])==record,'FORMAL_CALLER_RUNTIME_CHANGED')
            digest=self._observations[self._key(connection,record)]
            raw=self._run(connection,record['id'],before_sha=digest,health_seconds=snapshot.observation_timeout(seconds))
            metadata,separator,payload=raw.partition(b'\n')
            snapshot.require(separator and re.fullmatch(rb'[1-9][0-9]* [1-9][0-9]*',metadata),
                'FORMAL_CALLER_HEALTH_PROOF_INVALID')
            wire,marker,code=payload.rpartition(b'\nFORMAL_CURL_EXIT=')
            snapshot.require(marker and code in (b'0\n',b'7\n'),'FORMAL_CALLER_HEALTH_PROOF_INVALID')
            snapshot.require(self.inspect(connection,record['id'])==record,'FORMAL_CALLER_RUNTIME_CHANGED')
            snapshot.observation_timeout(1)
            if code==b'7\n':
                snapshot.require(not wire,'FORMAL_CALLER_HEALTH_PROOF_INVALID');return None
            proof=_parse_http_wire(wire)
            if proof is None:return None
            pid,namespace=map(int,metadata.split())
            return {**proof,'port':48081,'pid':pid,'networkNamespaceInode':namespace}
        finally:snapshot.observation_deadline.reset(token)


def _connection(connection, host):
    snapshot.require(type(connection) is dict and set(connection) == CONNECTION_KEYS and
        connection['host'] == host and type(connection['port']) is int and connection['port'] == 22 and
        connection['user'] == 'root' and connection['dockerEndpoint'] == 'unix:///var/run/docker.sock' and
        type(connection['bootId']) is str and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', connection['bootId']) and
        type(connection['knownHostsSha256']) is str and re.fullmatch('[0-9a-f]{64}', connection['knownHostsSha256']) and
        type(connection['knownHostsFile']) is str and re.fullmatch('/[A-Za-z0-9_./-]+', connection['knownHostsFile']) and
        '..' not in connection['knownHostsFile'].split('/'), 'FORMAL_CALLER_CONNECTION_INVALID')


def _plan(plan):
    snapshot.require(type(plan) is dict and set(plan) == set(ROLES), 'FORMAL_CALLER_SCOPE_INVALID')
    identities = set()
    for role in ROLES:
        value = plan[role]
        snapshot.require(type(value) is dict and set(value) == {'connection', 'containerId'} and
            type(value['containerId']) is str and re.fullmatch('[0-9a-f]{64}', value['containerId']),
            'FORMAL_CALLER_SCOPE_INVALID')
        _connection(value['connection'], HOSTS[role])
        identities.add((HOSTS[role], value['containerId']))
    snapshot.require(len(identities) == 4 and
        plan[ROLES[0]]['connection'] == plan[ROLES[1]]['connection'] and
        plan[ROLES[2]]['connection'] == plan[ROLES[3]]['connection'], 'FORMAL_CALLER_SCOPE_INVALID')


def _has(claim, step):
    claim.assert_owned()
    return any(e['step'] == step for e in claim.events)


def _event(claim, step):
    return snapshot._claim_event(claim, step)['details']


def _names(role, action):
    snapshot.require(role in ROLES and action in ('stop', 'start'), 'FORMAL_CALLER_ACTION_INVALID')
    prefix = 'external-' + role
    return (prefix + ('-stop-intent' if action == 'stop' else '-restore-intent'),
            prefix + ('-stopped' if action == 'stop' else '-restored'))


def _live(claim):
    claim.assert_owned()
    snapshot.require(not _has(claim, 'released'), 'FORMAL_CALLER_CLAIM_RELEASED')


def bind_external_callers(claim, plan, transport):
    _live(claim); _plan(plan)
    snapshot.require(not _has(claim, 'external-caller-scope') and
        not any(e['step'].startswith(('db-', 'split-')) for e in claim.events), 'FORMAL_CALLER_STAGE_INVALID')
    originals = {}
    for role in ROLES:
        selected = plan[role]
        row = transport.inspect(selected['connection'], selected['containerId'])
        snapshot._container_stable(row)
        snapshot.require(row['id'] == selected['containerId'] and row['name'] == NAMES[role],
                         'FORMAL_CALLER_IDENTITY_CHANGED')
        originals[role] = row
    raw = snapshot._canonical_bytes({'plan': plan, 'originals': originals})
    snapshot.require(len(raw) <= 65536, 'FORMAL_CALLER_SCOPE_TOO_LARGE')
    # Reobserve before retaining the originals; binding itself performs no action.
    for role in ROLES:
        snapshot.require(transport.inspect(plan[role]['connection'], plan[role]['containerId']) == originals[role],
                         'FORMAL_CALLER_RUNTIME_CHANGED')
    _live(claim)
    claim._write(snapshot.safe_file(claim.root / 'external-callers-original.json'), raw)
    claim.record('external-caller-scope', {'scopeSha256': hashlib.sha256(raw).hexdigest()})
    return originals


def _scope(claim):
    _live(claim)
    path = snapshot._existing_file(claim.root / 'external-callers-original.json')
    snapshot.require(path.stat().st_size <= 65536 and (os.name != 'posix' or
        stat.S_IMODE(path.stat().st_mode) == 0o600), 'FORMAL_CALLER_SCOPE_CHANGED')
    raw = path.read_bytes(); digest = hashlib.sha256(raw).hexdigest()
    snapshot.require(_event(claim, 'external-caller-scope') == {'scopeSha256': digest},
                     'FORMAL_CALLER_SCOPE_CHANGED')
    value = json.loads(raw)
    snapshot.require(type(value) is dict and set(value) == {'plan', 'originals'} and
        type(value['originals']) is dict and set(value['originals']) == set(ROLES) and
        raw == snapshot._canonical_bytes(value), 'FORMAL_CALLER_SCOPE_CHANGED')
    _plan(value['plan'])
    return value['plan'], value['originals'], digest


def _observe(claim, transport, reconciling=None):
    plan, originals, digest = _scope(claim); current = {}
    for role in ROLES:
        before = originals[role]; selected = plan[role]
        row = transport.inspect(selected['connection'], selected['containerId'])
        snapshot.require(before['id'] == selected['containerId'] and before['name'] == NAMES[role] and
            snapshot._container_stable(row) == snapshot._container_stable(before),
            'FORMAL_CALLER_IDENTITY_CHANGED')
        expected = before['state']
        for action in ('stop', 'start'):
            intent, completed = _names(role, action)
            if _has(claim, intent) and not _has(claim, completed):
                snapshot.require(reconciling == (role, action), 'FORMAL_CALLER_PENDING_ACTION_REQUIRED')
                expected = None
            elif _has(claim, completed):
                result = _event(claim, completed)
                snapshot.require(result['scopeSha256'] == digest and result['intentSha256'] ==
                    hashlib.sha256(snapshot._canonical_bytes(_event(claim, intent))).hexdigest(),
                    'FORMAL_CALLER_SCOPE_CHANGED')
                expected = result['runtime']
        if expected is not None:
            snapshot.require(row['state'] == expected, 'FORMAL_CALLER_RUNTIME_CHANGED')
        current[role] = row
    _live(claim)
    snapshot.require(_scope(claim)[2] == digest, 'FORMAL_CALLER_SCOPE_CHANGED')
    return plan, originals, current, digest


def guard_external_callers(claim, transport):
    snapshot.require(not _has(claim, 'external-recovery-intent'), 'FORMAL_CALLER_STAGE_INVALID')
    _, _, current, digest = _observe(claim, transport)
    for role in ROLES:
        _event(claim, _names(role, 'stop')[1])
        snapshot.require(current[role]['state']['Running'] is False and current[role]['state']['ExitCode'] == 0,
                         'FORMAL_CALLER_NOT_STOPPED')
    return {'state': 'KNOWN_EXTERNAL_CALLERS_STOPPED_PENDING_FULL_EXCLUSION',
            'scopeSha256': digest, 'productionEvidence': False}


def begin_external_recovery(claim, transport, *, dependency_guard):
    snapshot.require(callable(dependency_guard) and not _has(claim, 'external-recovery-intent'),
                     'FORMAL_CALLER_ACTION_REPLAY_REFUSED')
    dependency_guard()
    _, _, _, digest = _observe(claim, transport)
    dependency_guard(); _live(claim)
    claim.record('external-recovery-intent', {'scopeSha256': digest})


def _order(claim, role, action, digest, dependency_guard):
    for prior in ROLES[:ROLES.index(role)]: _event(claim, _names(prior, action)[1])
    if action == 'stop':
        snapshot.require(not _has(claim, 'external-recovery-intent'), 'FORMAL_CALLER_STAGE_INVALID')
    else:
        snapshot.require(callable(dependency_guard) and
            _event(claim, 'external-recovery-intent') == {'scopeSha256': digest}, 'FORMAL_CALLER_RECOVERY_REQUIRED')
        dependency_guard()


def reconcile_external_caller(claim, role, action, transport, *, dependency_guard=None, guard=None):
    selected_guard=dependency_guard if action=='start' else guard
    snapshot.require(callable(selected_guard),'FORMAL_CALLER_MUTATION_GUARD_REQUIRED')
    snapshot.observation_timeout(1);claim.assert_owned();selected_guard();snapshot.observation_timeout(1)
    intent_name, complete_name = _names(role, action)
    snapshot.require(not _has(claim, complete_name), 'FORMAL_CALLER_ACTION_REPLAY_REFUSED')
    _, originals, current, digest = _observe(claim, transport, (role, action))
    _order(claim, role, action, digest, dependency_guard)
    intent = _event(claim, intent_name)
    snapshot.require(set(intent) == {'scopeSha256', 'before', 'actionRequired'} and
        intent['scopeSha256'] == digest and type(intent['actionRequired']) is bool,
        'FORMAL_CALLER_SCOPE_CHANGED')
    before = intent['before']; state = current[role]['state']
    if not intent['actionRequired']:
        valid = state == before
    elif action == 'stop':
        valid = state['Running'] is False and state['ExitCode'] == 0 and \
            state['StartedAt'] == before['StartedAt'] and state['FinishedAt'] != before['FinishedAt']
    else:
        valid = state['Running'] is True and state['StartedAt'] != before['StartedAt']
    snapshot.require(valid and state['Running'] == (False if action == 'stop' else originals[role]['state']['Running']),
                     'FORMAL_CALLER_RECONCILIATION_REQUIRED')
    _order(claim, role, action, digest, dependency_guard)
    snapshot.require(_observe(claim, transport, (role, action))[2] == current, 'FORMAL_CALLER_RUNTIME_CHANGED')
    selected_guard();claim.assert_owned();snapshot.observation_timeout(1)
    claim.record(complete_name, {'scopeSha256': digest, 'runtime': state,
        'actionPerformed': intent['actionRequired'],
        'intentSha256': hashlib.sha256(snapshot._canonical_bytes(intent)).hexdigest()})
    selected_guard();claim.assert_owned();snapshot.observation_timeout(1)
    return state


def _action(claim, role, action, transport, dependency_guard, *, guard):
    snapshot.require(callable(guard),'FORMAL_CALLER_MUTATION_GUARD_REQUIRED')
    snapshot.observation_timeout(1);claim.assert_owned();guard();snapshot.observation_timeout(1)
    intent_name, complete_name = _names(role, action)
    snapshot.require(not _has(claim, intent_name) and not _has(claim, complete_name),
                     'FORMAL_CALLER_ACTION_REPLAY_REFUSED')
    plan, originals, current, digest = _observe(claim, transport)
    _order(claim, role, action, digest, dependency_guard)
    required = originals[role]['state']['Running'] and (action == 'stop' or _has(claim, _names(role, 'stop')[1]))
    claim.record(intent_name, {'scopeSha256': digest, 'before': current[role]['state'], 'actionRequired': required})
    _order(claim, role, action, digest, dependency_guard)
    snapshot.require(_observe(claim, transport, (role, action))[2] == current, 'FORMAL_CALLER_RUNTIME_CHANGED')
    guard();claim.assert_owned();snapshot.observation_timeout(1)
    if required: transport.action(plan[role]['connection'], current[role], action)
    return reconcile_external_caller(claim, role, action, transport, dependency_guard=dependency_guard,guard=guard)


def stop_external_caller(claim, role, transport, *, guard):
    return _action(claim, role, 'stop', transport, None,guard=guard)


def restore_external_caller(claim, role, transport, *, dependency_guard):
    return _action(claim, role, 'start', transport, dependency_guard,guard=dependency_guard)


def verify_external_restoration(claim, transport, *, dependency_guard):
    snapshot.require(callable(dependency_guard), 'FORMAL_CALLER_RECOVERY_REQUIRED')
    dependency_guard()
    _, originals, current, digest = _observe(claim, transport)
    snapshot.require(_event(claim, 'external-recovery-intent') == {'scopeSha256': digest},
                     'FORMAL_CALLER_RECOVERY_REQUIRED')
    for role in ROLES:
        _event(claim, _names(role, 'start')[1])
        snapshot.require(current[role]['state']['Running'] == originals[role]['state']['Running'],
                         'FORMAL_CALLER_RUNTIME_CHANGED')
    dependency_guard()
    return {'state': 'EXTERNAL_CALLERS_RESTORED_PENDING_INGRESS_PROOF',
            'scopeSha256': digest, 'services': current, 'productionEvidence': False}


# Fixed container namespace endpoint; rehearsal host48082 maps internal48081.
HTTP_PORTS=dict.fromkeys(ROLES,48081)


def _parse_http_wire(raw):
    """Strict complete curl --raw/--include bytes, without redirect or decoding."""
    def require(value):snapshot.require(value,'FORMAL_CALLER_HTTP_FRAMING_INVALID')
    require(type(raw) is bytes and len(raw)<=98304)
    header,separator,body=raw.partition(b'\r\n\r\n')
    require(separator and len(header)<=16384)
    lines=header.split(b'\r\n')
    require(len(lines)<=128 and re.fullmatch(rb'HTTP/1\.[01] [1-5][0-9]{2} [\x20-\x7e]*',lines[0]))
    status=int(lines[0].split(b' ')[1]);headers={}
    for line in lines[1:]:
        name,colon,value=line.partition(b':')
        require(colon and re.fullmatch(rb'[A-Za-z0-9!#$%&\x27*+.^_`|~-]+',name) and
            all(32<=v<=126 or v==9 for v in value))
        headers.setdefault(name.lower(),[]).append(value.strip())
    lengths=headers.get(b'content-length',[]);transfers=headers.get(b'transfer-encoding',[])
    require(len(lengths)<=1 and len(transfers)<=1 and not (lengths and transfers) and
        headers.get(b'content-encoding',[]) in ([],[b'identity']))
    if lengths:
        require(re.fullmatch(rb'[0-9]{1,8}',lengths[0]) and int(lengths[0])==len(body))
    if transfers:
        require(transfers==[b'chunked']);decoded=bytearray();offset=0
        while True:
            end=body.find(b'\r\n',offset)
            require(end>=offset and re.fullmatch(rb'[0-9a-fA-F]{1,8}',body[offset:end]))
            size=int(body[offset:end],16);offset=end+2
            if size==0:
                require(body[offset:]==b'\r\n');break
            require(size<=65536-len(decoded) and offset+size+2<=len(body) and body[offset+size:offset+size+2]==b'\r\n')
            decoded.extend(body[offset:offset+size]);offset+=size+2
        body=bytes(decoded)
    require(len(body)<=65536)
    if status in (502,503):return None
    from formal_service_health import validate_http
    return validate_http('backend',status,body)


def _health_proof(role,proof):
    snapshot.require(type(proof) is dict and set(proof)=={'httpStatus','bytes','sha256','port','networkNamespaceInode','pid'} and
        type(proof['httpStatus']) is int and proof['httpStatus']==200 and
        type(proof['bytes']) is int and 0<proof['bytes']<=65536 and
        proof['port']==HTTP_PORTS[role] and type(proof['port']) is int and
        type(proof['sha256']) is str and re.fullmatch('[0-9a-f]{64}',proof['sha256']) and
        all(type(proof[k]) is int and proof[k]>0 for k in ('pid','networkNamespaceInode')),
        'FORMAL_CALLER_HEALTH_PROOF_INVALID')
    return proof


def _original_health(claim):
    snapshot.require(_has(claim,'external-health-scope'),'FORMAL_CALLER_HEALTH_REQUIRED')
    path=snapshot._existing_file(claim.root/'external-callers-health-original.json')
    snapshot.require(path.stat().st_size<=16384 and (os.name!='posix' or stat.S_IMODE(path.stat().st_mode)==0o600),
        'FORMAL_CALLER_HEALTH_SCOPE_CHANGED')
    raw=path.read_bytes()
    try:value=json.loads(raw)
    except (ValueError,UnicodeError):raise snapshot.FormalSnapshotError('FORMAL_CALLER_HEALTH_SCOPE_CHANGED') from None
    _,originals,digest=_scope(claim)
    snapshot.require(type(value) is dict and set(value)=={'schemaVersion','scopeSha256','claimBindingSha256','health','observedAt'} and
        raw==snapshot._canonical_bytes(value) and value['schemaVersion']=='formal-external-health-original/v1' and
        value['scopeSha256']==digest and value['claimBindingSha256']==hashlib.sha256(claim._plan).hexdigest() and
        _event(claim,'external-health-scope')=={'sha256':hashlib.sha256(raw).hexdigest()} and
        type(value['health']) is dict and set(value['health'])==set(ROLES),'FORMAL_CALLER_HEALTH_SCOPE_CHANGED')
    for role,row in value['health'].items():
        if originals[role]['state']['Running']:
            snapshot.require(type(row) is dict and set(row)=={'state','proof'} and row['state']=='HEALTHY',
                'FORMAL_CALLER_HEALTH_SCOPE_CHANGED')
            _health_proof(role,row['proof'])
        else:snapshot.require(row=={'state':'ORIGINALLY_STOPPED','healthObserved':False},'FORMAL_CALLER_HEALTH_SCOPE_CHANGED')
    return value


def _await_http(claim,transport,role,record,guard,deadline):
    plan,_,_,_=_observe(claim,transport)
    if not record['state']['Running']:
        guard();snapshot.observation_timeout(1)
        snapshot.require(_observe(claim,transport)[2][role]==record,'FORMAL_CALLER_RUNTIME_CHANGED')
        return {'state':'ORIGINALLY_STOPPED','healthObserved':False}
    while True:
        _live(claim);guard();snapshot.observation_timeout(1)
        snapshot.require(_observe(claim,transport)[2][role]==record,'FORMAL_CALLER_RUNTIME_CHANGED')
        seconds=min(8,deadline-time.monotonic(),snapshot.observation_timeout(8))
        snapshot.require(seconds>0,'FORMAL_CALLER_HEALTH_DEADLINE')
        proof=transport.observe_http(plan[role]['connection'],record,role,seconds)
        guard();_live(claim);snapshot.observation_timeout(1)
        snapshot.require(_observe(claim,transport)[2][role]==record,'FORMAL_CALLER_RUNTIME_CHANGED')
        if proof is not None:return {'state':'HEALTHY','proof':_health_proof(role,proof)}
        snapshot.require(time.monotonic()+.2<deadline,'FORMAL_CALLER_HEALTH_DEADLINE');time.sleep(.2)


def _health_deadline(seconds):
    snapshot.require(type(seconds) in (int,float) and 0<seconds<=300,'FORMAL_CALLER_HEALTH_DEADLINE')
    return time.monotonic()+snapshot.observation_timeout(seconds)


def bind_external_health_scope(claim,transport,*,guard,seconds=120):
    snapshot.require(callable(guard),'FORMAL_CALLER_HEALTH_GUARD_REQUIRED')
    snapshot.require(not _has(claim,'external-health-scope') and not any(
        e['step'].startswith(('db-','split-')) or e['step'].endswith('-stop-intent') or
        e['step']=='external-recovery-intent' for e in claim.events),'FORMAL_CALLER_HEALTH_STAGE_INVALID')
    deadline=_health_deadline(seconds);token=snapshot.observation_deadline.set(deadline)
    try:
        guard();_,originals,current,digest=_observe(claim,transport)
        snapshot.require(current==originals,'FORMAL_CALLER_RUNTIME_CHANGED')
        observed={role:_await_http(claim,transport,role,current[role],guard,deadline) for role in ROLES}
        guard();snapshot.observation_timeout(1)
        snapshot.require(_observe(claim,transport)[2]==current,'FORMAL_CALLER_RUNTIME_CHANGED')
        report={'schemaVersion':'formal-external-health-original/v1','scopeSha256':digest,'health':observed,
            'claimBindingSha256':hashlib.sha256(claim._plan).hexdigest(),
            'observedAt':datetime.now(timezone.utc).isoformat()}
        raw=snapshot._canonical_bytes(report)
        snapshot.require(len(raw)<=16384,'FORMAL_CALLER_HEALTH_SCOPE_CHANGED')
        claim._write(claim.root/'external-callers-health-original.json',raw)
        snapshot.observation_timeout(1)
        claim.record('external-health-scope',{'sha256':hashlib.sha256(raw).hexdigest()})
        snapshot.observation_timeout(1)
        return report
    finally:snapshot.observation_deadline.reset(token)


def _matches_health(role,observed,original):
    snapshot.require(observed['state']==original['state'],'FORMAL_CALLER_HEALTH_ORIGINAL_STATE_CHANGED')
    if observed['state']=='HEALTHY':
        snapshot.require(observed['proof']['port']==original['proof']['port'],'FORMAL_CALLER_HEALTH_NETWORK_CHANGED')


def restore_external_services_with_health(claim,transport,*,dependency_guard,seconds=120):
    snapshot.require(callable(dependency_guard),'FORMAL_CALLER_HEALTH_GUARD_REQUIRED')
    deadline=_health_deadline(seconds);token=snapshot.observation_deadline.set(deadline)
    try:
        dependency_guard();snapshot.observation_timeout(1);original=_original_health(claim)
        begin_external_recovery(claim,transport,dependency_guard=dependency_guard)
        for role in ROLES:
            dependency_guard();snapshot.observation_timeout(1)
            restore_external_caller(claim,role,transport,dependency_guard=dependency_guard)
            record=_observe(claim,transport)[2][role]
            observed=_await_http(claim,transport,role,record,dependency_guard,deadline)
            _matches_health(role,observed,original['health'][role])
        return observe_external_restoration_health(claim,transport,dependency_guard=dependency_guard,seconds=seconds)
    finally:snapshot.observation_deadline.reset(token)


def observe_external_restoration_health(claim,transport,*,dependency_guard,seconds=120):
    snapshot.require(callable(dependency_guard),'FORMAL_CALLER_HEALTH_GUARD_REQUIRED')
    deadline=_health_deadline(seconds);token=snapshot.observation_deadline.set(deadline)
    try:
        dependency_guard();snapshot.observation_timeout(1);original=_original_health(claim)
        restored=verify_external_restoration(claim,transport,dependency_guard=dependency_guard)
        health={}
        for role in ROLES:
            health[role]=_await_http(claim,transport,role,restored['services'][role],dependency_guard,deadline)
            _matches_health(role,health[role],original['health'][role])
        dependency_guard();snapshot.observation_timeout(1)
        snapshot.require(_observe(claim,transport)[2]==restored['services'],'FORMAL_CALLER_RUNTIME_CHANGED')
        _original_health(claim)
        snapshot.observation_timeout(1)
        return {'state':'EXTERNAL_CALLERS_HEALTHY_INGRESS_HELD','scopeSha256':restored['scopeSha256'],
            'health':health,'productionEvidence':False,'claimReleased':False}
    finally:snapshot.observation_deadline.reset(token)
