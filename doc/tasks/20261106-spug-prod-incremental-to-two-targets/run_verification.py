"""Run affected regression and retain exact exit status and UTF-8 output."""
import hashlib,json,os,subprocess,sys
from common import TASK,write,now
root=TASK.parents[2]
tests=['scripts/tests/test_smallapp_binlog_ddl.py','scripts/tests/test_backup_variants.py',
       'scripts/tests/test_capture_request_binding.py','scripts/tests/test_capture_archive_guard.py',
       'scripts/tests/test_capture_redis_auth.py']
environment=dict(os.environ,PYTHONPATH='C:/Spug/runtime/private/prod-full-to-test-20261104/test-dependencies',PYTHONUTF8='1')
command=[sys.executable,'-X','utf8','-B','-m','pytest','-q','-p','no:cacheprovider','--tb=short',*tests]
result=subprocess.run(command,cwd=root,env=environment,capture_output=True)
raw=result.stdout+result.stderr
(TASK/'affected-regression.log').write_bytes(raw)
report=dict(observedAt=now(),command=command,exitCode=result.returncode,outputSha256=hashlib.sha256(raw).hexdigest(),status='PASS' if result.returncode==0 else 'FAIL')
write(TASK/'affected-regression.json',report)
print(raw.decode('utf-8'));print(json.dumps(report));raise SystemExit(result.returncode)
