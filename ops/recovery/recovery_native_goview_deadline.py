"""Explicit Linux3.10 owned-child/subreaper GoView execution, no pidfd fallback.

The dedicated controller is the only parent/waiter. It ACKs established native
supervision before child CONNECT, publishes actual observation, asks the real
private issuer for binding, and retains that one child connection. Parent exit,
result and IPC cleanup precede final current authentication. Missing provision
blocks use; no default issuer/SQL callback exists.
"""
from __future__ import annotations

import base64
import ctypes
import hashlib
import math
import os
from pathlib import Path
import signal
import socket
import struct
import sys
import threading
import time
import uuid

from recovery_environment_contract import EnvironmentFailure, canonical, decode, exact, require, utc_now
from recovery_environment_supervisor import MODEL, identity, prepare_local_supervision
from recovery_native_process import persist_bytes, open_lab_file, file_metadata
from recovery_native_goview_errors import GoViewFailure, remember, safe_failure

_OWNED = None
_UNREAPED = {}  # Only this dedicated sole parent's still-unreaped children.
DRIVER_CLASS = 'pymysql.connections.Connection'
CURSOR_CLASS = 'pymysql.cursors.Cursor'
MAX_FRAME = 65536


def remaining(deadline):
    value = deadline-time.monotonic()
    require(math.isfinite(deadline) and value > 0, 'GOVIEW_CONSUMER_DEADLINE')
    return value


class SelectedPyMySQLDeadline:
    def __init__(self, scope):
        s = scope.selection; c = scope.connection
        require(s['driverClass'] == DRIVER_CLASS and s['cursorClass'] == CURSOR_CLASS,
                'GOVIEW_SELECTED_PYMYSQL_DRIVER_REQUIRED')
        require(_OWNED is not None and _OWNED['pid'] == os.getpid() and _OWNED['parent'] == os.getppid() and
                _OWNED['deadline'] == scope.deadline and _OWNED['acknowledged'] is True and
                identity(os.getppid())['startTicks'] == _OWNED['parentStartTicks'],
                'GOVIEW_OWNED_TOTAL_DEADLINE_REQUIRED')
        source = Path(__file__).resolve(); raw = source.read_bytes()
        source_pin = dict(path=str(source),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        require(source_pin in scope.manifest['filePins']+scope.manifest['dependencyPins'], 'GOVIEW_DEADLINE_PROVIDER_NOT_SELECTED')
        scope.raw(source_pin)
        require(type(c._sock) is socket.socket and c._read_timeout is not None and c._write_timeout is not None and
                0 < c._read_timeout <= 300 and 0 < c._write_timeout <= 300, 'GOVIEW_FINITE_DRIVER_IO_REQUIRED')
        self.scope = scope; self.socket = c._sock

    def invoke(self, target, method, *args, **kwargs):
        scope = self.scope; c = scope.connection
        try:
            require(method in ('execute','fetchall','fetchone','fetchmany','close'), 'GOVIEW_DRIVER_OPERATION_UNSELECTED')
            require(target is c and method == 'close' or
                type(target).__module__+'.'+type(target).__qualname__ == CURSOR_CLASS and target.connection is c,
                'GOVIEW_REAL_DRIVER_OPERATION_REQUIRED')
            require(c._sock is self.socket and type(self.socket) is socket.socket, 'GOVIEW_DRIVER_SOCKET_CHANGED')
            budget = remaining(scope.deadline)
            c._read_timeout = budget; c._write_timeout = budget; self.socket.settimeout(budget)
            remaining(scope.deadline)
            result = getattr(target,method)(*args,**kwargs)
            remaining(scope.deadline)
            return result
        except BaseException as error:
            remember(scope,error,'driver-'+method if method in ('execute','fetchall','fetchone','fetchmany','close') else 'driver-unselected')
            raise


def send(channel, value, deadline):
    raw = canonical(value); require(len(raw) <= MAX_FRAME, 'GOVIEW_OWNED_FRAME_LIMIT')
    channel.settimeout(remaining(deadline))
    require(channel.send(raw) == len(raw), 'GOVIEW_OWNED_FRAME_SHORT_WRITE')


def receive(channel, expected, deadline):
    channel.settimeout(remaining(deadline))
    raw, ancillary, flags, _ = channel.recvmsg(MAX_FRAME,socket.CMSG_SPACE(12))
    require(raw and not flags & (socket.MSG_TRUNC|socket.MSG_CTRUNC), 'GOVIEW_OWNED_FRAME_TRUNCATED_OR_LOST')
    credentials = [struct.unpack('3i',value) for level,kind,value in ancillary
                   if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS and len(value) == 12]
    require(credentials == [expected], 'GOVIEW_OWNED_ACTUAL_IPC_PEER_CHANGED')
    return decode(raw)


def private_original(path, raw):
    pin = persist_bytes(Path(path),raw)
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try: os.fchmod(fd,0o400); os.fsync(fd)
    finally: os.close(fd)
    return pin


def observation_original(connect, observation):
    path = connect.selection['observationRoot']+'/connection-'+uuid.uuid4().hex+'.json'
    pin = persist_bytes(Path(path),canonical(observation))
    fd,directory = open_lab_file(path,os.O_RDONLY)
    try:
        os.fchown(fd,0,connect.issuer['identity']['gid']);os.fchmod(fd,0o440);os.fsync(fd);os.fsync(directory)
    finally: os.close(fd);os.close(directory)
    from recovery_native_goview_authority import read_observation
    require(read_observation(connect,pin) == observation, 'GOVIEW_OBSERVATION_ORIGINAL_READBACK')
    return pin


def dedicated_subreaper():
    prepare_local_supervision()
    require(signal.getsignal(signal.SIGCHLD) == signal.SIG_DFL and
        not Path('/proc/self/task/'+str(os.getpid())+'/children').read_text(encoding='ascii').strip(),
        'GOVIEW_DEDICATED_SOLE_PARENT_REQUIRED')
    libc = ctypes.CDLL(None,use_errno=True)
    require(libc.prctl(36,1,0,0,0) == 0, 'GOVIEW_SUBREAPER_SET_FAILED')
    actual = ctypes.c_int()
    require(libc.prctl(37,ctypes.byref(actual),0,0,0) == 0 and actual.value == 1, 'GOVIEW_SUBREAPER_ACK_UNPROVEN')


def worker_security(issuer):
    libc = ctypes.CDLL(None,use_errno=True)
    require(libc.prctl(38,1,0,0,0) == 0, 'GOVIEW_WORKER_NO_NEW_PRIVILEGES_FAILED')
    last = int(Path('/proc/sys/kernel/cap_last_cap').read_text(encoding='ascii'))
    require(0 <= last <= 63, 'GOVIEW_WORKER_CAPABILITY_RANGE_INVALID')
    for cap in range(last+1):
        require(libc.prctl(24,cap,0,0,0) == 0, 'GOVIEW_WORKER_CAPABILITY_BOUNDING_DROP_FAILED')
    class Header(ctypes.Structure): _fields_ = [('version',ctypes.c_uint32),('pid',ctypes.c_int)]
    class Data(ctypes.Structure): _fields_ = [('effective',ctypes.c_uint32),('permitted',ctypes.c_uint32),('inheritable',ctypes.c_uint32)]
    header = Header(0x20080522,0); data = (Data*2)()
    require(libc.capset(ctypes.byref(header),ctypes.byref(data)) == 0, 'GOVIEW_WORKER_CAPABILITY_DROP_FAILED')
    status = dict(line.split(':',1) for line in Path('/proc/self/status').read_text(encoding='ascii').splitlines())
    security = dict(uid=os.geteuid(),gid=os.getegid(), **{k:int(status[k].strip(),16) for k in ('CapInh','CapPrm','CapEff','CapBnd')},
                    NoNewPrivs=int(status['NoNewPrivs'].strip()))
    require(security['uid'] == security['gid'] == 0 and all(security[k] == 0 for k in ('CapInh','CapPrm','CapEff','CapBnd')) and
            security['NoNewPrivs'] == 1, 'GOVIEW_ACTUAL_CAPABILITY_DENIAL_UNPROVEN')
    denial = []
    for path in (issuer['privateKeyReference']['path'],'/proc/'+str(issuer['identity']['pid'])+'/root',
                 '/proc/'+str(issuer['identity']['pid'])+'/mem'):
        # /proc/<issuer>/root is deliberately a kernel link. Follow it for the
        # access-denial measurement; O_NOFOLLOW/ELOOP would prove nothing.
        flags = os.O_RDONLY|os.O_NONBLOCK
        if path == issuer['privateKeyReference']['path']: flags |= os.O_NOFOLLOW
        try: fd = os.open(path,flags)
        except OSError as error:
            require(error.errno in (2,13), 'GOVIEW_KEY_DENIAL_PROBE_INVALID'); denial.append(dict(path=path,errno=error.errno))
        else:
            os.close(fd); raise EnvironmentFailure('GOVIEW_SQL_WORKER_KEY_ACCESS_NOT_DENIED')
    return security,denial


def direct_children():
    return [int(v) for v in Path('/proc/self/task/'+str(os.getpid())+'/children').read_text(encoding='ascii').split()]


class OwnedTree:
    """Never signal a PID after reaping. Only kernel direct-child custody."""
    def __init__(self, pid, owner, deadline):
        self.pid,self.owner,self.deadline = pid,owner,deadline
        self.held = {} if pid is None else {pid:dict(pid=pid,soleParentPid=os.getpid(),reaped=False)}
        self.history = []; self.wait_status = None; self.extra_children = False
        self.terminal_proven = False

    def inspect(self):
        ids = direct_children()
        require(set(self.held) <= set(ids), 'GOVIEW_OWNED_CHILD_CUSTODY_LOST')
        for pid in ids:
            item = identity(pid); require(item['parent'] == os.getpid(), 'GOVIEW_OWNED_CHILD_PARENT_CHANGED')
            if pid not in self.held:
                self.held[pid] = dict(item,reaped=False)
                if pid != self.pid: self.extra_children = True
            prior = self.held[pid]
            require('startTicks' not in prior or prior['startTicks'] == item['startTicks'], 'GOVIEW_OWNED_CHILD_CHANGED')
            prior.update(item)
        return ids

    def exited(self,pid): return os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)

    def reap(self,pid):
        got,status = os.waitpid(pid,os.WNOHANG)
        require(got == pid, 'GOVIEW_OWNED_REAP_UNPROVEN')
        item = self.held.pop(pid); item.update(reaped=True,actualWaitStatus=status); self.history.append(item)
        if pid == self.pid: self.wait_status = status

    def wait_worker(self,deadline):
        while time.monotonic() < deadline:
            require(self.inspect() == [self.pid], 'GOVIEW_UNEXPECTED_OWNED_DESCENDANT')
            if self.exited(self.pid) is not None:
                self.reap(self.pid); require(not self.inspect(), 'GOVIEW_OWNED_TREE_NOT_EMPTY')
                self.terminal_proven = True; return
            time.sleep(min(.01,remaining(deadline)))
        raise EnvironmentFailure('GOVIEW_OWNED_EXIT_DEADLINE')

    def cleanup(self):
        failures = []
        self.terminal_proven = False
        until = min(self.deadline,time.monotonic()+5)
        try:
            self.inspect()  # Includes a just-forked child before its first ACK.
            while self.held and time.monotonic() < until:
                ids = self.inspect()
                for pid in ids:
                    try:
                        if self.exited(pid) is None:
                            self.held[pid]['signalOwnership'] = 'SOLE_PARENT_UNREAPED_CHILD'
                            os.kill(pid,signal.SIGKILL); self.held[pid]['signalSent'] = True
                    except BaseException as error: failures.append(error)
                for pid in ids:
                    try:
                        if pid != self.pid and self.exited(pid) is not None: self.reap(pid)
                    except BaseException as error: failures.append(error)
                ids = self.inspect()
                if ids == [self.pid] and self.exited(self.pid) is not None: self.reap(self.pid)
                if self.held: time.sleep(min(.01,max(0,until-time.monotonic())))
            require(not self.held and not self.inspect(), 'GOVIEW_OWNED_TERMINATION_UNKNOWN')
            self.terminal_proven = True
        except BaseException as error: failures.append(error)
        if not self.terminal_proven: _UNREAPED[self.pid] = self
        return failures

    def proof(self):
        return dict(model=MODEL,soleParentIdentity=self.owner,childPid=self.pid,actualWaitStatus=self.wait_status,
            state='REAPED' if self.terminal_proven else 'UNKNOWN',heldChildren=list(self.held.values()),reapedChildren=self.history,
            unexpectedChildren=self.extra_children)


def current_scope(connect, selection_pin, authority_pin, deadline, initial=None):
    from consume_goview import GoViewScope, BINDING_FIELDS, SELECTION_FIELDS
    scope = object.__new__(GoViewScope)
    scope.deadline,scope.selection_pin,scope.authority_pin = deadline,selection_pin,authority_pin
    scope.publication_root = connect.selection['evidenceRoot']
    scope.selection = scope.signed(selection_pin); exact(scope.selection,SELECTION_FIELDS,'GOVIEW_SELECTION_SHAPE')
    scope.binding = {k:scope.selection[k] for k in BINDING_FIELDS}; scope.initial_context = initial
    context = scope.guard(physical=False)
    return scope,context


def publish_unknown(connect, tree, primary, cleanup, frame, issued, observation_pin):
    diagnostic = dict(schemaVersion='W05GoViewOwnedExecution/v2',state='UNKNOWN',retryAllowed=False,
        connectPin=connect.connect_pin,operationId=connect.selection['binding']['operationId'],
        batchId=connect.selection['binding']['batchId'],selectionPin=issued['selectionPin'] if issued else None,
        intentPin=issued['intentPin'] if issued else None,observationPin=observation_pin,
        terminal=tree.proof(),primary=safe_failure(primary) if primary else None,
        cleanup=[safe_failure(e) for e in cleanup],childFailure=frame if frame and frame.get('state') == 'UNKNOWN' else None,
        observedAt=utc_now())
    # Read any child-owned retained diagnostic even if IPC send/close failed.
    # This is failure evidence only, never a substitute PASSED result.
    prefix = connect.selection['evidenceRoot']+'/child-'+connect.connect_pin['sha256']+'-'+str(tree.pid)
    for suffix, key in (('-failure.json','childFailureOriginal'),
                        ('-terminal-failure.json','childTerminalFailureOriginal')):
        failure_path = prefix+suffix
        try:
          if Path(failure_path).exists():
              from recovery_native_browser import descriptor_read
              import stat
              fd,directory = open_lab_file(failure_path,os.O_RDONLY)
              try:
                  info = os.fstat(fd)
                  require(stat.S_ISREG(info.st_mode) and info.st_uid == info.st_gid == 0 and info.st_nlink == 1 and
                      stat.S_IMODE(info.st_mode) == 0o400 and 0 < info.st_size <= MAX_FRAME, 'GOVIEW_CHILD_FAILURE_ORIGINAL_LIMIT')
                  raw = os.read(fd,MAX_FRAME+1)
                  require(file_metadata(os.fstat(fd)) == file_metadata(info), 'GOVIEW_CHILD_FAILURE_ORIGINAL_CHANGED')
              finally: os.close(fd);os.close(directory)
              failure_pin = dict(path=failure_path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
              held = descriptor_read(failure_pin,owners={0},deadline=connect.deadline,readonly=False,modes=(0o400,))
              require(held == raw, 'GOVIEW_CHILD_FAILURE_ORIGINAL_CHANGED')
              retained = decode(held)
              require(retained['state'] == 'UNKNOWN' and retained['retryAllowed'] is False and
                  retained['connectPin'] == connect.connect_pin and retained['childPid'] == tree.pid,
                  'GOVIEW_CHILD_FAILURE_ORIGINAL_CHANGED')
              if issued is not None:
                  require(retained['intentPin'] == issued['intentPin'], 'GOVIEW_CHILD_FAILURE_INTENT_CHANGED')
              if observation_pin is not None:
                  observed = decode(descriptor_read(observation_pin,owners={0},deadline=connect.deadline,
                      readonly=False,modes=(0o400,0o440)))
                  require(observed['connectPin'] == connect.connect_pin and
                      observed['workerIdentity']['pid'] == tree.pid and
                      retained['observedEngine'] == observed['engine'], 'GOVIEW_CHILD_FAILURE_OBSERVATION_CHANGED')
              diagnostic[key] = dict(pin=failure_pin,diagnostic=retained)
        except BaseException as error:
          diagnostic['childFailureReadError' if key == 'childFailureOriginal' else 'childTerminalFailureReadError'] = safe_failure(error)
    pin = None
    try:
        require(time.monotonic() < connect.deadline, 'GOVIEW_UNKNOWN_PUBLICATION_DEADLINE')
        pin = private_original(connect.selection['evidenceRoot']+'/owned-'+uuid.uuid4().hex+'-unknown.json',canonical(diagnostic))
    except BaseException as error: diagnostic['publicationFailure'] = safe_failure(error)
    return GoViewFailure('GOVIEW_EXECUTION_UNKNOWN_NO_RETRY',diagnostic,result=pin)


def child_entry(channel, connect_pin, authority_pin, options, parent, deadline, execution_deadline):
    global _OWNED
    connection = None; primary = None; cleanup = []; result = None; observation = None; issued = None
    try:
        require(os.getppid() == parent['pid'], 'GOVIEW_CHILD_PARENT_CHANGED')
        ack = receive(channel,(parent['pid'],parent['uid'],parent['gid']),execution_deadline)
        exact(ack,{'kind','supervision'},'GOVIEW_SUPERVISION_ACK_SHAPE')
        require(ack['kind'] == 'SUPERVISION_ACK' and ack['supervision']['subreaper'] is True and
            ack['supervision']['model'] == MODEL and ack['supervision']['workerIdentity']['pid'] == os.getpid() and
            ack['supervision']['parentIdentity'] == parent, 'GOVIEW_REAL_SUPERVISION_ACK_REQUIRED')
        _OWNED = dict(pid=os.getpid(),parent=os.getppid(),parentStartTicks=parent['startTicks'],deadline=execution_deadline,acknowledged=True)
        from recovery_native_goview_authority import ConnectScope, host_identity, stable_identity, validate_bundle
        connect = ConnectScope.__new__(ConnectScope)
        connect.connect_pin,connect.authority_pin,connect.deadline,connect.issuer_role = connect_pin,authority_pin,execution_deadline,False
        connect.selection = connect.signed(connect_pin); connect.issuer = connect.signed(connect.selection['issuerSelectionPin'])
        connect.permit = connect.signed(connect.selection['issuancePermitPin'])
        security,denial = worker_security(connect.issuer)
        connect.guard(controller=False)
        from pymysql.connections import Connection
        from pymysql.cursors import Cursor
        budget = remaining(execution_deadline)
        connection = Connection(**options,connect_timeout=max(1,math.ceil(budget)),read_timeout=budget,write_timeout=budget,
                                cursorclass=Cursor,defer_connect=False)
        cursor = connection.cursor(); identity_error = None; identity_cleanup = []
        try:
            cursor.execute('SELECT DATABASE(), @@server_uuid, CONNECTION_ID()'); rows = cursor.fetchall()
            require(type(rows) in (list,tuple) and len(rows) == 1 and len(rows[0]) == 3, 'GOVIEW_ENGINE_OBSERVATION_INVALID')
        except BaseException as error: identity_error = error
        finally:
            try: cursor.close()
            except BaseException as error: identity_cleanup.append(error)
        if identity_error is not None or identity_cleanup:
            raise GoViewFailure('GOVIEW_OBSERVATION_UNKNOWN_NO_RETRY',dict(primary=safe_failure(identity_error) if identity_error else None,
                cleanup=[safe_failure(e) for e in identity_cleanup],state='UNKNOWN',retryAllowed=False))
        observation = dict(schemaVersion='W05GoViewOwnedConnectionObservation/v1',connectPin=connect_pin,
            controllerIdentity=parent,workerIdentity=stable_identity(os.getpid()),hostIdentity=host_identity(),supervision=ack['supervision'],
            engine=dict(schema=rows[0][0],serverUuid=rows[0][1],connectionId=rows[0][2]),workerSecurity=security,
            keyDenial=denial,observedAt=utc_now())
        send(channel,dict(kind='OBSERVED',observation=observation),execution_deadline)
        release = receive(channel,(parent['pid'],parent['uid'],parent['gid']),execution_deadline)
        exact(release,{'kind','issued','observationPin'},'GOVIEW_OBSERVED_RELEASE_SHAPE')
        require(release['kind'] == 'ISSUED', 'GOVIEW_REAL_POSTCONNECT_RELEASE_REQUIRED')
        issued = release['issued']; validate_bundle(connect,issued,release['observationPin'],observation)
        for item in issued['documents']:
            require(private_original(item['pin']['path'],canonical(item['envelope'])) == item['pin'], 'GOVIEW_ISSUED_PUBLICATION_CHANGED')
        from consume_goview import execute_selected
        result = execute_selected(issued['selectionPin'],authority_pin,connection,deadline=execution_deadline,
                                  publication_root=connect.selection['evidenceRoot'])
        connection = None
    except BaseException as error: primary = error
    finally:
        if connection is not None:
            try: remaining(execution_deadline); connection.close()
            except BaseException as error: cleanup.append(error)
    frame = dict(state='PASSED',result=result) if primary is None and not cleanup else dict(state='UNKNOWN',retryAllowed=False,
        primary=safe_failure(primary) if primary else None,cleanup=[safe_failure(e) for e in cleanup],
        observedEngine=observation['engine'] if observation else None,intentPin=issued['intentPin'] if issued else None)
    code = 0 if frame['state'] == 'PASSED' else 71
    if code:
        try:
            remaining(deadline)
            retained = dict(frame,connectPin=connect_pin,childPid=os.getpid())
            frame['failureOriginalPin'] = private_original(connect.selection['evidenceRoot']+'/child-'+
                connect_pin['sha256']+'-'+str(os.getpid())+'-failure.json',canonical(retained))
        except BaseException as error:
            frame['publicationFailure'] = safe_failure(error)
    try: send(channel,dict(kind='RESULT',frame=frame),deadline)
    except BaseException as error:
        cleanup.append(error); code = 72
    try: channel.close()
    except BaseException as error:
        cleanup.append(error); code = 73
    if code in (72,73):
        retained = dict(state='UNKNOWN',retryAllowed=False,connectPin=connect_pin,childPid=os.getpid(),
            primary=safe_failure(primary) if primary else None,cleanup=[safe_failure(e) for e in cleanup],
            observedEngine=observation['engine'] if observation else None,intentPin=issued['intentPin'] if issued else None)
        try:
            remaining(deadline)
            private_original(connect.selection['evidenceRoot']+'/child-'+connect_pin['sha256']+'-'+str(os.getpid())+'-terminal-failure.json',canonical(retained))
        except BaseException: code = 75  # Parent preserves UNKNOWN and original IPC frame, if delivered.
    os._exit(code)


def validate_result(scope, result, issued, observation_pin, observation):
    s = scope.selection; c = scope.initial_context
    require(type(result) is dict and result['state'] == 'SINGLE_TABLE_SEQUENCE_PASSED' and result['fullSchemaAccepted'] is False and
        all(result[k] == s[k] for k in ('operationId','batchId','connectionId')) and
        result['fenceId'] == c['fenceId'] and result['fenceGeneration'] == c['fenceGeneration'] and
        result['actualSqlPin'] == s['inputPins']['sql'], 'GOVIEW_OWNED_RESULT_BINDING_CHANGED')
    paths = set(); events = {}
    for key,label in (('intentReceiptPin','create-intent'),('executionReceiptPin','create-result'),('completionReceiptPin','sequence-complete')):
        pin = result[key]; event = decode(scope.raw(pin))
        require(pin['path'] not in paths and event['sequenceId'] == result['sequenceId'] and event['scope'] == c and
            event['label'] == label, 'GOVIEW_OWNED_REAL_RECEIPT_CHAIN_CHANGED')
        paths.add(pin['path']); events[key] = event
    engine = events['intentReceiptPin']['data']['engine']
    require(engine['selected_database'] == s['schema'] and engine['server_uuid'] == s['serverUuid'] and
        engine['connection_id'] == s['connectionId'] and all(v['data']['engine'] == engine for v in events.values()),
        'GOVIEW_OWNED_RECEIPT_ENGINE_CHANGED')
    raw_sql = scope.raw(s['inputPins']['sql'])
    encoded_sql = dict(encoding='base64',value=base64.b64encode(raw_sql).decode('ascii'))
    execution = events['executionReceiptPin']['data']
    completion = events['completionReceiptPin']['data']
    require(events['intentReceiptPin']['data']['sqlPin'] == execution['actualSqlPin'] == completion['actualSqlPin'] == s['inputPins']['sql'] and
        events['executionReceiptPin']['sql'] == execution['actualSqlBytes'] == encoded_sql and execution['scope'] == c and
        execution['outcome'] == 'SUCCEEDED' and type(execution['rowcount']) is int and execution['rowcount'] == 0 and
        (execution['executeReturn'] is None or type(execution['executeReturn']) is int and execution['executeReturn'] == 0) and
        completion['fullSchemaAccepted'] is False, 'GOVIEW_OWNED_ACTUAL_EXECUTION_ORIGINAL_CHANGED')
    require(events['executionReceiptPin']['data']['intentReceiptPin'] == result['intentReceiptPin'] and
        events['completionReceiptPin']['data']['intentReceiptPin'] == result['intentReceiptPin'] and
        events['completionReceiptPin']['data']['executionReceiptPin'] == result['executionReceiptPin'],
        'GOVIEW_OWNED_REAL_RECEIPT_REFERENCES_CHANGED')
    intent = scope.signed(issued['intentPin'])
    require(intent['selectionPin'] == scope.selection_pin and intent['observationPin'] == observation_pin and
        intent['connectionId'] == observation['engine']['connectionId'] == s['connectionId'] and
        intent['operationId'] == s['operationId'] and intent['batchId'] == s['batchId'] and
        intent['leaseId'] == c['fenceId'] and intent['fenceGeneration'] == c['fenceGeneration'], 'GOVIEW_OWNED_INTENT_CHANGED')


def execute_selected_owned(connect_pin, authority_pin, *, connection_options, deadline):
    """Root-only dedicated controller; actual issuer provision mandatory.

    Takes CONNECT authorization, never a live socket/final selection. No SQL,
    callback, success flag or connection-id argument is accepted.
    """
    require(sys.platform == 'linux' and os.geteuid() == os.getegid() == 0 and threading.active_count() == 1 and
        _OWNED is None and not _UNREAPED and 2 < remaining(deadline) <= 300, 'GOVIEW_OWNED_ENTRY_PREREQUISITE')
    from recovery_native_goview_authority import ConnectScope, IssuerClient, stable_identity, validate_observation, issued_context
    connect = ConnectScope(connect_pin,authority_pin,deadline=deadline); issuer = IssuerClient(connect); issuer.preflight()
    c = connect.selection
    require(c['driverClass'] == DRIVER_CLASS and c['cursorClass'] == CURSOR_CLASS, 'GOVIEW_SELECTED_PYMYSQL_DRIVER_REQUIRED')
    allowed = {'host','port','user','password','database','unix_socket','charset','ssl','ssl_ca','ssl_cert','ssl_key',
               'ssl_verify_cert','ssl_verify_identity','bind_address'}
    require(type(connection_options) is dict and set(connection_options) <= allowed and
        {k:v for k,v in connection_options.items() if k not in ('user','password')} == c['connectionPublicOptions'] and
        connection_options.get('database') == c['binding']['schema'], 'GOVIEW_SELECTED_CONNECTION_OPTIONS_REQUIRED')
    from pymysql.connections import Connection
    from pymysql.cursors import Cursor
    for cls,key in ((Connection,'driverClassPin'),(Cursor,'cursorClassPin')):
        require(sys.modules[cls.__module__].__file__ == c[key]['path'], 'GOVIEW_DRIVER_MODULE_UNSELECTED'); connect.raw(c[key])
    for entry in Path('/proc/self/fd').iterdir():
        try: value = os.readlink(entry)
        except FileNotFoundError: continue  # Kernel iterator closed its own enumeration FD.
        require(not value.startswith('socket:['), 'GOVIEW_INHERITED_LIVE_SOCKET_REFUSED')
    dedicated_subreaper(); connect.guard()
    parent = stable_identity(os.getpid()); execution_deadline = deadline-1.0
    reader,writer = socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
    connect.deadline = execution_deadline
    tree = OwnedTree(None,parent,deadline-.25)
    primary = None; cleanup = []; frame = None; issued = None; observation_pin = None; observation = None
    result = None; scope = None; context = None
    try:
        reader.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1); writer.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
        connect.guard()
        pid = os.fork()
        if pid == 0:
            try:
                reader.close()
                child_entry(writer,connect_pin,authority_pin,connection_options,parent,deadline,execution_deadline)
            except BaseException as error:
                try: send(writer,dict(kind='RESULT',frame=dict(state='UNKNOWN',retryAllowed=False,primary=safe_failure(error),cleanup=[])),deadline)
                except BaseException: pass  # Actual nonzero exit/lost frame remains UNKNOWN.
                os._exit(74)
        # Preallocated owner: the first postfork parent operation retains the
        # actual direct-child PID. Even subsequent setup failures enter cleanup.
        tree.pid = pid
        writer.close(); worker = stable_identity(pid)
        require(worker['parent'] == parent['pid'], 'GOVIEW_POSTFORK_CHILD_PARENT_UNPROVEN')
        supervision = dict(model=MODEL,parentIdentity=parent,workerIdentity=worker,subreaper=True,acknowledged=True)
        connect.guard(); send(reader,dict(kind='SUPERVISION_ACK',supervision=supervision),execution_deadline)
        message = receive(reader,(pid,worker['uid'],worker['gid']),execution_deadline)
        if message.get('kind') == 'RESULT': frame = message['frame']; raise EnvironmentFailure('GOVIEW_CONNECT_OBSERVATION_FAILED')
        exact(message,{'kind','observation'},'GOVIEW_OWNED_OBSERVATION_FRAME_SHAPE')
        require(message['kind'] == 'OBSERVED', 'GOVIEW_ACTUAL_CONNECTION_OBSERVATION_REQUIRED')
        observation = message['observation']; validate_observation(connect,observation)
        require(observation['workerIdentity'] == worker and stable_identity(pid) == worker, 'GOVIEW_ACTUAL_OBSERVING_CHILD_CHANGED')
        observation_pin = observation_original(connect,observation)
        issued = issuer.issue(observation_pin,observation)
        context = issued_context(connect,issued)
        send(reader,dict(kind='ISSUED',issued=issued,observationPin=observation_pin),execution_deadline)
        message = receive(reader,(pid,worker['uid'],worker['gid']),execution_deadline)
        exact(message,{'kind','frame'},'GOVIEW_OWNED_RESULT_FRAME_SHAPE')
        require(message['kind'] == 'RESULT', 'GOVIEW_OWNED_RESULT_REQUIRED'); frame = message['frame']
        tree.wait_worker(execution_deadline)
        require(tree.wait_status == 0 and not tree.extra_children and frame.get('state') == 'PASSED', 'GOVIEW_OWNED_CHILD_NOT_PASSED')
        exact(frame,{'state','result'},'GOVIEW_OWNED_PASSED_FRAME_SHAPE'); result = frame['result']
        scope,current = current_scope(connect,issued['selectionPin'],authority_pin,execution_deadline,initial=context)
        require(current == context, 'GOVIEW_OWNED_APPROVED_CONTEXT_CHANGED')
        validate_result(scope,result,issued,observation_pin,observation)
        # Positive terminal/originals evidence is published before IPC cleanup
        # and final authentication. It is an observation, not result permission.
        terminal_record = dict(schemaVersion='W05GoViewOwnedTerminalOriginal/v1',connectPin=connect_pin,
            selectionPin=issued['selectionPin'],intentPin=issued['intentPin'],observationPin=observation_pin,
            terminal=tree.proof(),result=result,observedAt=utc_now())
        private_original(c['evidenceRoot']+'/owned-'+connect_pin['sha256']+'-'+str(pid)+'-terminal.json',canonical(terminal_record))
    except BaseException as error: primary = error
    finally:
        if tree.pid is not None:
            try: cleanup.extend(tree.cleanup())
            except BaseException as error:
                cleanup.append(error); tree.terminal_proven = False; _UNREAPED[tree.pid] = tree
        for channel in (writer,reader):
            try: channel.close()
            except BaseException as error: cleanup.append(error)
    connect.deadline = deadline
    if primary is not None or cleanup:
        if tree.pid is not None: raise publish_unknown(connect,tree,primary,cleanup,frame,issued,observation_pin) from None
        raise GoViewFailure('GOVIEW_OWNED_SETUP_UNKNOWN_NO_RETRY',dict(state='UNKNOWN',retryAllowed=False,
            primary=safe_failure(primary) if primary else None,cleanup=[safe_failure(e) for e in cleanup])) from None
    # All result/source/driver callbacks and owned IPC cleanup have finished.
    # Nothing performs I/O on the accepted path after this final guard.
    try:
        scope.deadline = deadline
        connect.guard()
        require(scope.guard(physical=False) == context, 'GOVIEW_PARENT_FINAL_SCOPE_OR_FENCE_DRIFT')
    except BaseException as error:
        raise publish_unknown(connect,tree,error,[],frame,issued,observation_pin) from None
    return result
