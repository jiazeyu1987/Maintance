"""Published MAIN endpoints require exact identity and protection before writes."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from test_main_retained_authentication import contract
import recovery_main_target as main


def endpoint(case):
    bindings={'9000/tcp':[dict(HostIp='0.0.0.0',HostPort='9000')],
              '9001/tcp':[dict(HostIp='0.0.0.0',HostPort='9001')]}
    programs={family:dict(pin=dict(path='/usr/sbin/xtables-multi',bytes=100,sha256='1'*64),applet=applet)
              for family,applet in [('ipv4','iptables'),('ipv6','ip6tables')]}
    value=dict(role='minio',ip='127.0.0.1',port=9000,containerPort='9000/tcp',bindings=bindings,
        writeFence=dict(schemaVersion='PublishedHostWriteFence/v1',ports=[9000,9001],
            allowedWriterIPv4=[case.native.config_services['backend']['ip']],programs=programs))
    case.target['mainApplication']['publishedDataEndpoints']=[value]
    case.native.config_services['minio']['ip']='127.0.0.1'
    case.rows['minio']['HostConfig']['PortBindings']=deepcopy(bindings)
    case.rows['backend']['NetworkSettings']['Networks']['main']['IPAMConfig']={'IPv4Address':case.native.config_services['backend']['ip']}
    case.target['mainApplication']['serviceConfigurationDigests']['minio']=main.service_configuration_digest(case.rows['minio'])
    return value


def test_minio_host_endpoint_uses_exact_publication_and_full_port_protection(contract):
    value=endpoint(contract)
    main.validate(contract.target)
    main.verify_runtime(contract.native)
    main.object_endpoint(contract.native,'http://127.0.0.1:9000')


@pytest.mark.parametrize('change',['port','missing-console-fence','foreign-writer','foreign-service','ipv6-binding','wildcard-client','partial-binding'])
def test_published_contract_cannot_widen_the_original_scope(contract,change):
    value=endpoint(contract)
    if change=='port':value['port']=9002
    elif change=='missing-console-fence':value['writeFence']['ports']=[9000]
    elif change=='foreign-writer':value['writeFence']['allowedWriterIPv4'].append('10.0.0.99')
    elif change=='foreign-service':value['role']='mysql'
    elif change=='ipv6-binding':value['bindings']['9000/tcp'][0]['HostIp']='::'
    elif change=='wildcard-client':value['ip']=contract.native.config_services['minio']['ip']='0.0.0.0'
    elif change=='partial-binding':value['bindings'].pop('9001/tcp')
    with pytest.raises(Exception,match='MAIN_PUBLISHED_|PUBLISHED_FENCE_|MAIN_DATA_ENDPOINT_UNBOUND'):main.validate(contract.target)


def test_published_container_can_stop_and_must_rejoin_the_actual_registered_bridge(contract):
    endpoint(contract);row=contract.rows['minio']
    saved=contract.target['mainApplication']['networkAttachments']['minio']
    row['NetworkSettings']['Networks']['main']['IPAddress']=''
    main.verify_network_attachments(contract.native,'minio',row,saved)
    row['State']['Running']=True;row['NetworkSettings']['Networks']['main']['IPAddress']='172.29.1.33'
    contract.network['Containers'][row['Id']]={'IPv4Address':'172.29.1.33/24','IPv6Address':''}
    main.verify_network_attachments(contract.native,'minio',row,saved)
    contract.network['Containers'][row['Id']]['IPv4Address']='172.29.1.44/24'
    with pytest.raises(Exception,match='MAIN_SERVICE_NETWORK_CHANGED'):
        main.verify_network_attachments(contract.native,'minio',row,saved)


@pytest.mark.parametrize('failure',['fence','quiescence'])
def test_fence_or_writer_quiescence_failure_precedes_destructive_sql(tmp_path,failure):
    import recovery_replace
    calls=[]
    def mysql(statement,**kwargs):
        calls.append(('sql',statement))
        if statement.startswith('DROP DATABASE'):raise AssertionError('DESTRUCTIVE_SQL_REACHED')
        return '1' if statement=='SELECT @@GLOBAL.log_bin;' else ''
    def fence():
        calls.append(('fence','install'))
        if failure=='fence':raise RuntimeError('EXPECTED_FENCE_FAILURE')
    def quiescence():
        calls.append(('writers','verify'))
        if failure=='quiescence':raise RuntimeError('EXPECTED_QUIESCENCE_FAILURE')
    native=SimpleNamespace(root=tmp_path,original=dict(targetConfigRef='prod'),
        config=dict(database='ruoyi-vue-pro',application=dict(startOrder=['backend','frontend'])),
        config_services={role:dict(id=role) for role in ('backend','frontend','minio')},
        mysql=SimpleNamespace(query=mysql),docker=lambda args,**kwargs:calls.append(('docker',args)),
        replacement_write_fence=fence,replacement_quiescence=quiescence)
    with patch('recovery_replace.verify_services'),pytest.raises(RuntimeError,match='EXPECTED_'):
        recovery_replace.prepare(native,dict(databaseUuid='registered',services=native.config_services))
    assert not any(kind=='sql' and statement.startswith('DROP DATABASE') for kind,statement in calls)
    if failure=='fence':assert not any(kind=='docker' for kind,_ in calls)
    else:assert calls.index(('fence','install')) < calls.index(('writers','verify'))
