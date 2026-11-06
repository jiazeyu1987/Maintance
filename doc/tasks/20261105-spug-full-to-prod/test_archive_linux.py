"""Real mount test on the already owned isolated Linux test container."""
from pathlib import Path
import subprocess
import sys

TASK=Path(__file__).resolve().parent
if __name__=='__main__':
    phase=sys.argv[1]
    code="import sys;sys.path.insert(0,'/work/deps');import pytest;sys.exit(pytest.main(['scripts/tests/test_archive_view_protection_linux.py','-q','-p','no:cacheprovider','--basetemp=/work/pytest-archive-"+phase+"']))"
    result=subprocess.run(['C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe','exec','-w','/source','spug-prod-published-network-env-20261105','python','-B','-c',code],capture_output=True)
    (TASK/('linux-archive-'+phase+'.log')).write_bytes(result.stdout+result.stderr)
    print(result.stdout.decode('utf-8')[-4500:]);print(result.stderr.decode('utf-8')[-1000:]);sys.exit(result.returncode)
