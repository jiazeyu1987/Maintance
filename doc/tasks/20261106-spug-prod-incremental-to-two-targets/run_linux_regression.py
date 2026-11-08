"""Independent Linux test processes avoid module-cache contamination."""
import hashlib,json,subprocess,sys
from common import TASK,PRIVATE,write,now
docker='C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
name='spug-incremental-ddl-tests-20261106'
parent_final = '--parent-final' in sys.argv
if parent_final:
 name = 'spug-parent-final-regression-20261107'
assert subprocess.run([docker,'inspect',name],capture_output=True).returncode!=0,'TEST_CONTAINER_ALREADY_EXISTS'
script='''import hashlib,importlib.util,json,os,pathlib,subprocess,sys,tarfile,tempfile
# Linux Git cannot resolve the native Windows worktree refs through this bind.
# Create only ephemeral ref metadata pointing to the verified real commit;
# all commit objects remain the actual repository objects mounted read-only.
subprocess.run(['git','init','--bare','-q','/tmp/test-git'],check=True)
os.environ.update(GIT_DIR='/tmp/test-git',GIT_COMMON_DIR='/tmp/test-git',GIT_WORK_TREE='/src',GIT_ALTERNATE_OBJECT_DIRECTORIES='/git-common/objects')
subprocess.run(['git','cat-file','-e',os.environ['EXPECTED_HEAD']+'^{commit}'],check=True)
subprocess.run(['git','update-ref','--no-deref','HEAD',os.environ['EXPECTED_HEAD']],check=True)
assert subprocess.check_output(['git','-C','/src','rev-parse','HEAD']).decode().strip()==os.environ['EXPECTED_HEAD']
# The archive lease suite specifies SAFE behavior. ops/recovery is intentionally
# LIGHTWEIGHT; test the actual built STANDARD package, the deployment input.
spec=importlib.util.spec_from_file_location('variants','/src/ops/backup_engine/build_variants.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
package_root=pathlib.Path(tempfile.mkdtemp())
builder.build(package_root/'variants')
with tarfile.open(package_root/'variants/backup-restore-standard.tgz') as archive:
 manifest=json.load(archive.extractfile('package.json'))
 for member,sha in manifest['files'].items():assert hashlib.sha256(archive.extractfile(member).read()).hexdigest()==sha
 archive.extractall(package_root/'standard',filter='data')
files=['test_smallapp_binlog_ddl.py','test_backup_variants.py','test_capture_request_binding.py','test_capture_archive_guard.py','test_capture_redis_auth.py']
if os.environ['PARENT_FINAL']=='1':
 files=['test_backup_variants.py','test_capture_request_binding.py','test_capture_redis_auth.py']
for name in files:
 print('INDEPENDENT_TEST_FILE '+name,flush=True)
 args=['-q','-p','no:cacheprovider','--tb=short','scripts/tests/'+name]
 if name=='test_capture_archive_guard.py':
  print('TEST_ACTUAL_STANDARD_PACKAGE '+manifest['packageSha256'],flush=True)
  code='import sys;sys.path[:0]='+repr([str(package_root/'standard'/p) for p in ('common','control','formal')])+';import repository_minimal;import pytest;raise SystemExit(pytest.main('+repr(args)+'))'
  p=subprocess.run([sys.executable,'-B','-c',code])
 else:p=subprocess.run([sys.executable,'-B','-m','pytest',*args])
 if p.returncode:raise SystemExit(p.returncode)
'''
command=[docker,'run','-i','--rm','--name',name,'--label','codex.task=20261106-spug-prod-incremental-to-two-targets',
         '--mount','type=bind,source='+str(TASK.parents[2])+',target=/src,readonly',
         '--mount','type=bind,source='+subprocess.check_output(['git','rev-parse','--path-format=absolute','--git-common-dir']).decode().strip()+',target=/git-common,readonly',
         '--env','EXPECTED_HEAD='+subprocess.check_output(['git','rev-parse','HEAD']).decode().strip(),'--workdir','/src',
         '--env','PARENT_FINAL='+('1' if parent_final else '0'),
         'sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735',
         'sh','-ec','pip install --quiet --root-user-action=ignore pytest==8.3.5 jsonschema==4.23.0 redis==5.2.1; exec python -B -']
report_stem = 'linux-parent-final-regression' if parent_final else 'linux-affected-regression'
previous=TASK/(report_stem+'.json')
if previous.exists():
 suffix=hashlib.sha256(previous.read_bytes()).hexdigest()[:12]
 (TASK/(report_stem+'-prior-'+suffix+'.json')).write_bytes(previous.read_bytes())
 (TASK/(report_stem+'-prior-'+suffix+'.log')).write_bytes((TASK/(report_stem+'.log')).read_bytes())
result=subprocess.run(command,input=script.encode(),capture_output=True)
raw=result.stdout+result.stderr
(TASK/(report_stem+'.log')).write_bytes(raw)
absent=subprocess.run([docker,'inspect',name],capture_output=True).returncode!=0
expected_files = 3 if parent_final else 5
executed=result.stdout.count(b'INDEPENDENT_TEST_FILE ')==expected_files and result.stdout.count(b' passed')==expected_files and b' skipped' not in result.stdout
report=dict(status='PASS' if result.returncode==0 and absent and executed else 'FAIL',observedAt=now(),command=command,exitCode=result.returncode,containerRemoved=absent,outputSha256=hashlib.sha256(raw).hexdigest(),isolatedProcesses=True,allTestsActuallyExecuted=executed,testFiles=expected_files)
if not parent_final: report['allFiveTestsActuallyExecuted']=executed
write(TASK/(report_stem+'.json'),report);print(raw.decode());print(json.dumps(report));raise SystemExit(0 if report['status']=='PASS' else 1)
