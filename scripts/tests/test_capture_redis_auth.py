import json
from pathlib import Path
import sys
from unittest.mock import Mock, patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/backup_engine/formal'), str(ROOT/'ops/recovery')]
import minimal_redis_snapshot as snapshot
from minimal_capture_support import source_config_redis
from recovery_engine import pin


@pytest.mark.parametrize('authenticated', [True, False])
def test_source_redis_uses_explicit_password_only(authenticated, tmp_path):
    config = dict(containerId='a'*64, host='172.29.237.34', database=1)
    if authenticated:
        secret = tmp_path/'redis-password'; secret.write_bytes(b'test-secret\n')
        config['passwordPin'] = pin(secret)
    assert source_config_redis({'redisSnapshot': config}) == config
    observed = dict(Id=config['containerId'], State=dict(Running=True),
                    NetworkSettings=dict(Networks=dict(own=dict(IPAddress=config['host']))))
    client = Mock(); client.info.return_value = {'redis_version': '7.4.0'}
    with patch.object(snapshot.subprocess, 'check_output', return_value=json.dumps([observed]).encode()), \
            patch('redis.Redis', return_value=client) as factory:
        with snapshot.source_client(config, lambda: None): pass
        assert factory.call_args.kwargs.get('password') == ('test-secret' if authenticated else None)
        assert ('password' in factory.call_args.kwargs) is authenticated
        client.close.assert_called_once()


def test_source_redis_authentication_failure_is_not_swallowed():
    config = dict(containerId='a'*64, host='172.29.237.34', database=1)
    observed = dict(Id=config['containerId'], State=dict(Running=True),
                    NetworkSettings=dict(Networks=dict(own=dict(IPAddress=config['host']))))
    client = Mock(); client.info.side_effect = RuntimeError('authentication failed')
    with patch.object(snapshot.subprocess, 'check_output', return_value=json.dumps([observed]).encode()), \
            patch('redis.Redis', return_value=client):
        with pytest.raises(RuntimeError, match='authentication failed'):
            with snapshot.source_client(config, lambda: None): pass
        client.close.assert_called_once()
