"""Static registered MAIN Redis contracts; no server or business acceptance."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
import recovery_target_capture as capture
from recovery_engine import RecoveryError


PASSWORD=dict(path='/private/redis-password',bytes=23,sha256='a'*64)


def configuration(version,mode='PASSWORD'):
    target=dict(mainApplication=dict(schemaVersion='RegisteredMainApplication/'+version),
        secrets=dict(redis=dict(REDIS_PASSWORD=deepcopy(PASSWORD))))
    redis=dict(containerId='b'*64,host='172.20.0.4',database=1,passwordPin=deepcopy(PASSWORD))
    if version=='v2':
        target['mainApplication']['redisAuthentication']=dict(mode=mode)
        if mode=='NONE':
            target['mainApplication']['redisAuthentication']['aclSha256']='c'*64
            target['secrets'].pop('redis');redis.pop('passwordPin')
    return target,redis


@pytest.mark.parametrize('version,mode',[('v1','PASSWORD'),('v2','PASSWORD'),('v2','NONE')])
def test_registered_authentication_is_admitted_without_mutating_inputs(version,mode):
    target,redis=configuration(version,mode);before=deepcopy((target,redis))
    assert capture._redis_authentication(target,redis) is None
    assert (target,redis)==before


@pytest.mark.parametrize('version',['v1','v2'])
@pytest.mark.parametrize('problem',['missing-capture-pin','wrong-path','wrong-size','wrong-hash',
    'missing-registered-secret','missing-registered-pin','null-registered-pin'])
def test_password_contract_requires_the_exact_registered_pin(version,problem):
    target,redis=configuration(version)
    if problem=='missing-capture-pin':redis.pop('passwordPin')
    elif problem=='wrong-path':redis['passwordPin']['path']='/private/another-password'
    elif problem=='wrong-size':redis['passwordPin']['bytes']+=1
    elif problem=='wrong-hash':redis['passwordPin']['sha256']='d'*64
    elif problem=='missing-registered-secret':target['secrets'].pop('redis')
    elif problem=='missing-registered-pin':target['secrets']['redis'].pop('REDIS_PASSWORD')
    else:target['secrets']['redis']['REDIS_PASSWORD']=None
    before=deepcopy((target,redis))
    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_REDIS_CREDENTIAL_CHANGED'):
        capture._redis_authentication(target,redis)
    assert (target,redis)==before


@pytest.mark.parametrize('problem',['missing-main','unknown-schema','v1-extra-declaration',
    'missing-v2-declaration','null-declaration','unknown-mode','empty-mode','password-extra-field',
    'none-missing-acl','none-invalid-acl','none-extra-field'])
def test_unknown_or_incomplete_declaration_is_rejected(problem):
    target,redis=configuration('v2')
    main=target['mainApplication']
    if problem=='missing-main':target.pop('mainApplication')
    elif problem=='unknown-schema':main['schemaVersion']='RegisteredMainApplication/v3'
    elif problem=='v1-extra-declaration':main['schemaVersion']='RegisteredMainApplication/v1'
    elif problem=='missing-v2-declaration':main.pop('redisAuthentication')
    elif problem=='null-declaration':main['redisAuthentication']=None
    elif problem=='unknown-mode':main['redisAuthentication']['mode']='AUTO'
    elif problem=='empty-mode':main['redisAuthentication']={}
    elif problem=='password-extra-field':main['redisAuthentication']['optional']=True
    else:
        target,redis=configuration('v2','NONE');main=target['mainApplication']
        if problem=='none-missing-acl':main['redisAuthentication'].pop('aclSha256')
        elif problem=='none-invalid-acl':main['redisAuthentication']['aclSha256']='not-an-acl-hash'
        else:main['redisAuthentication']['optional']=True
    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_REDIS_AUTHENTICATION_INVALID'):
        capture._redis_authentication(target,redis)


@pytest.mark.parametrize('problem',['registered-secret','capture-secret','null-capture-secret'])
def test_no_authentication_never_admits_a_secret(problem):
    target,redis=configuration('v2','NONE')
    if problem=='registered-secret':target['secrets']['redis']=dict(REDIS_PASSWORD=deepcopy(PASSWORD))
    elif problem=='capture-secret':redis['passwordPin']=deepcopy(PASSWORD)
    else:redis['passwordPin']=None
    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_REDIS_CREDENTIAL_CHANGED'):
        capture._redis_authentication(target,redis)
