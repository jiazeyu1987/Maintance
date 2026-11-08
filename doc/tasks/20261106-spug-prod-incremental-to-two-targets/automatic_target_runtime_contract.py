"""Separate the HTTP parent's import contract from the worker execution env."""
import hashlib
import json
import subprocess


def _runtime_digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def verify_control_runtime(parent_environment,worker_environment,argv,expected_argv):
    if argv!=expected_argv or len(argv)<3 or argv[1]!='-B':
        raise ValueError('CONTROL_ARGV_CHANGED')
    if parent_environment.get('PYTHONPATH')!=worker_environment['PYTHONPATH']:
        raise ValueError('CONTROL_PYTHONPATH_CHANGED')
    return dict(schemaVersion='TaskControlRuntimeEnvironment/v1',parentModulePathMatches=True,
        parentBytecodeDisabledByArgv=True,workerEnvironmentSha256=_runtime_digest(worker_environment),
        inheritedParentDifferences=sorted(key for key,value in worker_environment.items()
            if key!='PYTHONPATH' and parent_environment.get(key)!=value))


WORKER_PROBE=r'''
import hashlib,json,os,pathlib,sys
import recovery_control_smallapp_native as native
def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
path=pathlib.Path(native.__file__).resolve();raw=path.read_bytes()
print(json.dumps(dict(environmentSha256=digest(dict(os.environ)),bytecodeDisabled=sys.dont_write_bytecode,
 modulePin=dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))))
'''


def observe_worker_environment(python_path,environment,expected_module_pin):
    process=subprocess.run([python_path,'-B','-c',WORKER_PROBE],env=environment,
        capture_output=True,timeout=15)
    if process.returncode!=0 or process.stderr:
        raise ValueError('WORKER_ENVIRONMENT_PROBE_FAILED')
    value=json.loads(process.stdout)
    if value['environmentSha256']!=_runtime_digest(environment) or value['bytecodeDisabled'] is not True:
        raise ValueError('WORKER_ENVIRONMENT_CHANGED')
    if value['modulePin']!=expected_module_pin:
        raise ValueError('WORKER_MODULE_CHANGED')
    return value
