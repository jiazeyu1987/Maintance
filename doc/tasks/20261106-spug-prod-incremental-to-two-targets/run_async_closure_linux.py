"""Real Linux process/proc tests, isolated from host bytecode/module caches."""
import hashlib,json,subprocess,sys
from pathlib import Path
from common import TASK,write,now

root=TASK.parents[2];docker='C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
attempt=sys.argv[1];assert attempt.replace('-','').isalnum()
name='spug-async-closure-'+attempt
assert subprocess.run([docker,'inspect',name],capture_output=True).returncode!=0
paths=['backend/src/main/resources/recovery_control_smallapp.py','backend/src/main/resources/recovery_control_smallapp_native.py',
 'backend/src/main/resources/recovery_control_incremental_plan.py','scripts/tests/test_automatic_incremental_async_closure.py']
pins={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
write(TASK/('linux-async-closure-'+attempt+'-inputs.json'),dict(inputFiles=pins))
tests=sys.argv[2:] or ['test_automatic_incremental_async_closure.py']
baseline={}
if tests[0]=='--baseline':
 tests=tests[1:]
 for path in paths[:2]:
  baseline[Path(path).stem]=subprocess.check_output(['git','show','HEAD:'+path],cwd=root).decode('utf-8')
script='''import subprocess,sys
for name in TESTS:
 print('INDEPENDENT_TEST_FILE '+name,flush=True)
 p=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','--tb=short','scripts/tests/'+name])
 if p.returncode:raise SystemExit(p.returncode)
'''
if baseline:
 script='''import sys,importlib,pytest
sys.path[:0]=['/src/backend/src/main/resources','/src/scripts/tests']
for name,source in BASELINE.items():
 module=importlib.import_module(name);exec(compile(source,module.__file__,'exec'),module.__dict__)
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--tb=short',*['scripts/tests/'+name for name in TESTS]]))
'''
command=[docker,'run','-i','--name',name,'--mount','type=bind,source='+str(root)+',target=/src,readonly','-w','/src',
 'sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735','sh','-ec',
 'pip install --quiet --root-user-action=ignore pytest==8.3.5 jsonschema==4.23.0; exec python -B -']
p=subprocess.run(command,input=('TESTS='+repr(tests)+'\nBASELINE='+repr(baseline)+'\n'+script).encode(),capture_output=True,timeout=600)
log=p.stdout+p.stderr;output=TASK/('linux-async-closure-'+attempt);assert not output.with_suffix('.json').exists()
output.with_suffix('.log').write_bytes(log)
removed=subprocess.run([docker,'rm',name],capture_output=True).returncode==0
report=dict(status='PASS' if p.returncode==0 else 'FAIL',observedAt=now(),exitCode=p.returncode,containerRemoved=removed,
 inputFilesUnchanged=all(hashlib.sha256((root/path).read_bytes()).hexdigest()==sha for path,sha in pins.items()),inputFiles=pins,
 outputSha256=hashlib.sha256(log).hexdigest(),tests=tests,workspaceReadOnly=True)
write(output.with_suffix('.json'),report);print(log.decode());print(json.dumps({k:v for k,v in report.items() if k!='inputFiles'}));raise SystemExit(p.returncode)
