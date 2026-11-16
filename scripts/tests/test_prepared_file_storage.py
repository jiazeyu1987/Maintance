"""Prepared-target storage adaptation never changes archived business data."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/recovery'))
sys.path.insert(0, str(ROOT / 'ops/backup_engine'))


def test_connection_update_is_explicit_and_secret_free_in_receipt():
    from recovery_prepared_storage import connection_update
    policy = dict(id=28, bucket='yudao', sourceEndpoints=['http://host.docker.internal:9000'])
    observed = dict(id=28, bucket='yudao', endpoint='http://host.docker.internal:9000', sha256='a'*64)
    sql, receipt = connection_update('ruoyi-vue-pro', policy, observed, 'http://172.29.238.33:9000', 'target-user', 'target-password')
    assert 'JSON_SET(config' in sql
    assert all(field in sql for field in ('$.endpoint', '$.accessKey', '$.accessSecret'))
    assert '$.domain' not in sql and '$.bucket' not in sql
    assert 'WHERE id=28' in sql and 'a'*64 in sql
    assert 'target-password' not in repr(receipt) and 'target-user' not in repr(receipt)


@pytest.mark.parametrize('change', [dict(id=29), dict(bucket='external'), dict(endpoint='https://outside.example')])
def test_wrong_configuration_is_rejected(change):
    from recovery_prepared_storage import connection_update
    policy = dict(id=28, bucket='yudao', sourceEndpoints=['http://host.docker.internal:9000'])
    observed = dict(id=28, bucket='yudao', endpoint='http://host.docker.internal:9000', sha256='a'*64)
    observed.update(change)
    with pytest.raises(ValueError):
        connection_update('ruoyi-vue-pro', policy, observed, 'http://172.29.238.33:9000', 'user', 'password')


def test_actual_safe_package_adapts_before_application_start():
    import build_variants
    payload = build_variants.safe_fixes(build_variants.standard_sources()[0])
    source = payload['common/recovery_minimal_runtime.py'].decode()
    start = source[source.index('    def start_application(self):'):]
    assert start.index('adapt_file_storage(self)') < start.index("self.docker(['start'")
    assert b'def adapt_file_storage(' in payload['common/recovery_prepared_storage.py']
