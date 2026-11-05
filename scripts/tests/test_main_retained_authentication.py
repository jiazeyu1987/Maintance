"""Versioned MAIN preservation and explicit existing Redis authentication."""
import hashlib
from unittest.mock import patch

import pytest
import test_main_restore_target as fixtures
import recovery_main_target as main


@pytest.fixture
def contract():
    case=fixtures.MainContractTests('test_registered_main_accepts_matching_archived_program');case.setUp()
    value=case.target['mainApplication'];value['schemaVersion']='RegisteredMainApplication/v2'
    value['publishedDataEndpoints']=[]
    value['redisAuthentication']=dict(mode='PASSWORD')
    case.target['replacement']['storage']=dict(schemaVersion='RegisteredReplacementStorage/v3')
    yield case
    case.doCleanups()


def test_v2_delegates_every_application_mount_to_the_explicit_storage_contract(contract):
    case=contract
    case.rows['backend']['Mounts']=[dict(Type='bind',Source='/runtime',Destination='/runtime',RW=True)]
    with patch('recovery_replacement_storage.verify_preserved_mounts',return_value=[]) as verify:
        main.application_inputs(case.native)
    verify.assert_called_once()
    assert verify.call_args.args[0] is case.target['replacement']['storage']
    assert verify.call_args.args[1]==case.rows


def test_v2_requires_the_versioned_preservation_contract(contract):
    contract.target['replacement']['storage']['schemaVersion']='RegisteredReplacementStorage/v2'
    with pytest.raises(Exception,match='MAIN_RETAINED_STORAGE_V3_REQUIRED'):main.validate(contract.target)


def noauth(case):
    acl=b'user default on nopass ~* &* +@all\n'
    case.target['mainApplication']['redisAuthentication']=dict(mode='NONE',aclSha256=hashlib.sha256(acl).hexdigest())
    case.target['secrets']={}
    calls=[]
    def docker(args,**kwargs):
        calls.append((args,kwargs))
        if args[-3:]==['CONFIG','GET','requirepass']:return b'requirepass\n\n'
        if args[-2:]==['ACL','LIST']:return acl
        return b'OK\n'
    case.native.docker=docker
    case.native.secret=lambda *a:(_ for _ in ()).throw(AssertionError('NO_FAKE_PASSWORD'))
    case.target['redisClientPath']='/usr/local/bin/redis-cli'
    return calls


def test_registered_passwordless_redis_uses_no_auth_and_rechecks_live_acl(contract):
    calls=noauth(contract)
    assert main.redis_password(contract.native) is None
    assert main.redis_command(contract.native,['-n','1','FLUSHDB'],mutation=True)==b'OK\n'
    args,options=calls[-1]
    assert args[-3:]==['-n','1','FLUSHDB']
    assert not any('REDISCLI_AUTH' in str(x) for x in args)
    assert 'input_bytes' not in options and options['mutation'] is True
    assert len([args for args,_ in calls if args[-2:]==['ACL','LIST']])==2


@pytest.mark.parametrize('change',['password','acl','published','fake-secret'])
def test_noauth_identity_or_acl_drift_fails_before_redis_mutation(contract,change):
    calls=noauth(contract);original=contract.native.docker
    if change in ('password','acl'):
        def docker(args,**kwargs):
            if change=='password' and args[-3:]==['CONFIG','GET','requirepass']:return b'requirepass\nnew-password\n'
            if change=='acl' and args[-2:]==['ACL','LIST']:return b'user default off\n'
            return original(args,**kwargs)
        contract.native.docker=docker
    elif change=='published':contract.rows['redis']['HostConfig']['PortBindings']={'6379/tcp':[{'HostIp':'0.0.0.0','HostPort':'6379'}]}
    else:contract.target['secrets']['redis']={'REDIS_PASSWORD':{'path':'/invented'}}
    with pytest.raises(Exception,match='MAIN_REDIS_'):main.redis_command(contract.native,['-n','1','FLUSHDB'],mutation=True)
    assert not any('FLUSHDB' in args for args,_ in calls)


def test_legacy_password_transport_stays_on_stdin(contract):
    contract.native.secret=lambda *args:'private-password-value'
    contract.target['redisClientPath']='/usr/local/bin/redis-cli'
    seen=[];contract.native.docker=lambda args,**kwargs:seen.append((args,kwargs)) or b'0\n'
    assert main.redis_command(contract.native,['-n','1','DBSIZE'])==b'0\n'
    args,options=seen[-1]
    assert 'private-password-value' not in repr(args)
    assert options['input_bytes']==b'private-password-value\n'
