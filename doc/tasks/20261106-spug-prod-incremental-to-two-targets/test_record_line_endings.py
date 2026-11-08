"""Real Git checks for byte-preserving task evidence attributes."""
import subprocess
from pathlib import Path

import pytest


ATTRIBUTES = Path(__file__).with_name('.gitattributes')


@pytest.mark.parametrize('name,data,expected', [
    ('evidence.json', b'{\r\n  "status": "PASS"\r\n}\r\n', 0),
    ('automatic-closeout-helper-regression-r2.txt', b'1 passed\r\n\r\n', 0),
    ('catalogue-login-helper-r4-regression.txt', b'1 passed\n\n', 0),
    ('source.py', b'value = 1 \r\n', 2),
    ('ordinary.txt', b'record\n\n', 2),
])
def test_raw_records_preserve_bytes_and_real_whitespace_errors(tmp_path, name, data, expected):
    def git(*args):
        return subprocess.run(['git', '-c', 'core.autocrlf=false', *args],
                              cwd=tmp_path, capture_output=True, check=False)

    assert git('init', '-q').returncode == 0
    (tmp_path / '.gitattributes').write_bytes(ATTRIBUTES.read_bytes())
    (tmp_path / name).write_bytes(data)
    assert git('add', '--', '.gitattributes', name).returncode == 0
    assert git('show', ':' + name).stdout == data
    result = git('diff', '--cached', '--check')
    assert result.returncode == expected, result.stdout.decode('utf-8')
