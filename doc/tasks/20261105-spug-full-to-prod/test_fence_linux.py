"""Run network behavior in the current goal's independent Linux namespace."""
import subprocess
import sys
from test_storage_linux import TASK,DOCKER
from prepare_network_linux import NETWORK

if __name__=='__main__':
    phase=sys.argv[1]
    code='import pytest;raise SystemExit(pytest.main(["scripts/tests/test_published_write_fence_linux.py","-q","-p","no:cacheprovider","--basetemp=/work/fence-'+phase+'"]))'
    result=subprocess.run([DOCKER,'exec',NETWORK,'python','-B','-c',code],capture_output=True)
    (TASK/('linux-published-fence-'+phase+'.log')).write_bytes(result.stdout+result.stderr)
    print(result.stdout.decode('utf-8',errors='replace')[-6500:]);print(result.stderr.decode('utf-8',errors='replace')[-1500:])
    print('EXIT',result.returncode);raise SystemExit(result.returncode)
