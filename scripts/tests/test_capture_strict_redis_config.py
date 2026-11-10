"""Strict MAIN capture must retain the existing explicit Redis credential."""
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
import minimal_capture_support as support
from formal_snapshot_linux import FormalSnapshotError
from recovery_engine import pin


@pytest.mark.parametrize('valid',[True,False])
def test_strict_redis_retains_and_validates_explicit_password_pin(tmp_path,valid):
    assert Path(support.__file__).resolve()==ROOT/'ops/recovery/minimal_capture_support.py'
    secret=tmp_path/'redis.private';secret.write_bytes(b'finite-private-protocol');secret.chmod(0o600)
    config=dict(containerId='a'*64,host='172.20.0.4',database=0,passwordPin=pin(secret))
    if valid:
        assert support.source_config_redis(dict(redisSnapshot=config))==config
    else:
        config['passwordPin']={'path':str(secret),'bytes':secret.stat().st_size,'sha256':'bad'}
        with pytest.raises(FormalSnapshotError):support.source_config_redis(dict(redisSnapshot=config))
