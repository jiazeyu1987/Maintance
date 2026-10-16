"""Focused R7 protocol/refusal checks; no lab/runtime acceptance is inferred."""
from copy import deepcopy
import ast
import base64
import hashlib
import json
from pathlib import Path
import socket
import struct
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))
from recovery_environment_contract import EnvironmentFailure
from recovery_native_observation import (MAX_FRAME, REQUEST_FIELDS, RESULT_FIELDS, ObservationOrder,
    receive_frame, send_frame, wire_canonical)
from recovery_native_launcher import LAUNCH_FIELDS, CALLER_FIELDS, native_call
from recovery_native_process import authenticate_payload


def intent(sequence=1, phase='BEFORE', collection='objects', binding=None):
    return {'schemaVersion': 'RepositoryLabNativeObserveRequest/v1',
        'rehearsalId': 'backup-server-rehearsal-20261012-r1', 'collectionId': collection,
        'sequence': sequence, 'phase': phase, 'operationRequestPin': {'p': 1},
        'serviceBindingPin': binding or {'p': 2}, 'issuedAt': '2026-10-13T00:00:00Z', 'deadlineMilliseconds': 1000}


def test_order_consumes_before_and_after_then_new_collection():
    order=ObservationOrder(4)
    for value in (intent(),intent(2,'AFTER'),intent(3,collection='services'),intent(4,'AFTER','services')):
        order.reserve(value)
    assert order.sequence==4


@pytest.mark.parametrize('damage', ['replay','skip','after-first','duplicate-before','binding','extra','phase','id','budget','bool'])
def test_replay_wrong_phase_binding_and_shape_fail(damage):
    order=ObservationOrder(2); first=intent(); order.reserve(first); second=intent(2,'AFTER')
    if damage=='replay':second['sequence']=1
    if damage=='skip':second['sequence']=3
    if damage=='after-first':second['collectionId']='new'
    if damage=='duplicate-before':second['phase']='BEFORE'
    if damage=='binding':second['serviceBindingPin']={'p':3}
    if damage=='extra':second['command']=['docker']
    if damage=='phase':second['phase']='NOW'
    if damage=='id':second['collectionId']='../escape'
    if damage=='budget':order.reserve(second);second=intent(3,collection='new')
    if damage=='bool':second['sequence']=True
    with pytest.raises(EnvironmentFailure):order.reserve(second)


def test_actual_socket_roundtrip_uses_utf8_canonical_frames():
    # Native socketpair is real I/O even on the local Windows validation host.
    value={'phase':'BEFORE','text':'测试租户'}
    a,b=socket.socketpair()
    try:
        send_frame(a,value,time.monotonic()+2)
        assert receive_frame(b,time.monotonic()+2)==value
        assert wire_canonical(value)==json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    finally:a.close();b.close()


@pytest.mark.parametrize('damage',['too-large','noncanonical','truncated','expired','duplicate-json'])
def test_frame_budget_and_canonicality_fail(damage):
    a,b=socket.socketpair()
    try:
        if damage=='too-large':a.sendall(struct.pack('!I',MAX_FRAME+1))
        if damage=='noncanonical':a.sendall(struct.pack('!I',8)+b'{"x": 1}')
        if damage=='truncated':a.sendall(struct.pack('!I',3)+b'{}');a.shutdown(socket.SHUT_WR)
        if damage=='duplicate-json':
            raw=b'{"x":1,"x":2}';a.sendall(struct.pack('!I',len(raw))+raw)
        with pytest.raises(EnvironmentFailure):receive_frame(b,time.monotonic()-.01 if damage=='expired' else time.monotonic()+2)
    finally:a.close();b.close()


def test_fixed_protocol_fields_match_actual_w06_client():
    path=Path(__file__).resolve().parents[1]/'recovery_verification/native_observe.py'
    tree=ast.parse(path.read_text(encoding='utf-8'));values={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('LAUNCH_FIELDS','REQUEST_FIELDS','RESULT_FIELDS','CALLER_FIELDS'):
            values[node.targets[0].id]=set(ast.literal_eval(node.value).split())
    assert values==dict(LAUNCH_FIELDS=LAUNCH_FIELDS,REQUEST_FIELDS=REQUEST_FIELDS,RESULT_FIELDS=RESULT_FIELDS,CALLER_FIELDS=CALLER_FIELDS)


@pytest.mark.skipif(sys.platform=='linux',reason='Local Windows native prerequisite refusal')
def test_missing_linux_cannot_launch_or_measure_success():
    with pytest.raises(EnvironmentFailure,match='NATIVE_LINUX_REQUIRED'):native_call('prctl',0)


@pytest.mark.parametrize('damage',[None,'payload','signature','authority','extra'])
def test_real_ed25519_exact_unicode_envelope_authentication(damage):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    key=Ed25519PrivateKey.generate()
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    digest=hashlib.sha256(public).hexdigest();payload={'schemaVersion':'RepositoryLabNativeObserveResult/v1','collectionId':'测试'}
    envelope={'schemaVersion':'RepositorySignedRecord/v1','keySha256':digest,'payload':payload,
              'signature':base64.b64encode(key.sign(wire_canonical(payload))).decode('ascii')}
    if damage=='payload':envelope['payload']['collectionId']='other'
    if damage=='signature':envelope['signature']=base64.b64encode(bytes(64)).decode('ascii')
    if damage=='authority':digest='0'*64
    if damage=='extra':envelope['callerSuccess']=True
    if damage:
        with pytest.raises(EnvironmentFailure):authenticate_payload(envelope,public,digest)
    else:assert authenticate_payload(envelope,public,digest)==payload
