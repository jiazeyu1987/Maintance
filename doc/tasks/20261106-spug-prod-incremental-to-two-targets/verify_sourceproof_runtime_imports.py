"""One bounded read-only installed-runtime probe; no SQL, API or business checks."""
import json
from common import TASK, remote
from verify_automatic_source_restoration import SOURCE_RUNTIME, prepare, write_exclusive


SCRIPT = r'''
import datetime,pathlib,sys
reader=AuditReader(seconds=30)
item=SPEC['controller'];control=reader.document(item['controlConfigurationPin'])
argv=[arg.decode() for arg in (pathlib.Path('/proc')/str(item['pid'])/'cmdline').read_bytes().split(b'\0') if arg]
need(argv[:3]==[control['pythonPin']['path'],'-B',str(pathlib.Path(item['engine'])/'control_entry.py')],
 'SOURCE_RUNTIME_SERVICE_ARGV_CHANGED')
environment=dict(part.split(b'=',1) for part in (pathlib.Path('/proc')/str(item['pid'])/'environ').read_bytes().split(b'\0') if b'=' in part)
need(environment[b'PYTHONPATH'].decode()==control['environment']['PYTHONPATH'],'SOURCE_RUNTIME_SERVICE_PATH_CHANGED')
runtime=bind_source_runtime(reader,control,item['engine'],SPEC['files'])
reader.finish()
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 schemaVersion='AutomaticSourceProofRuntimeImports/v1',runtime=runtime,controlConfigurationPin=item['controlConfigurationPin'],
 controllerPid=item['pid'],installedServiceModulePathVerified=True,serverWrites=False,controlApiCalled=False,
 sqlCalled=False,sourceProofExecuted=False)))
'''


def main():
    destination=TASK/'automatic-sourceproof-runtime-imports-complete.json'
    if destination.exists():raise FileExistsError('RUNTIME_IMPORT_PROOF_ALREADY_EXISTS')
    _,spec=prepare('FULL')
    public=dict(controller=spec['installation']['controllers'][0],files=spec['files'])
    core=(TASK/'automatic_chain_audit.py').read_text(encoding='utf-8')
    script=core+'\n'+SOURCE_RUNTIME+'\nSPEC='+repr(public)+'\n'+SCRIPT
    compile(script,'readonly-source-runtime','exec')
    report=remote('172.30.30.57',script,timeout=45)
    if report['status']!='PASS':raise ValueError('RUNTIME_IMPORT_PROOF_FAILED')
    write_exclusive(destination,report)
    print(json.dumps(dict(status='PASS',controllerPid=report['controllerPid'],
        modules=len(report['runtime']['modulePins']),dependencies=len(report['runtime']['dependencyPins']),
        sourceProofExecuted=False,serverWrites=False)))


if __name__=='__main__':main()
