"""Read only exact immutable dispatch metadata; never rerun the archive audit."""
import hashlib
import json
from common import TASK, PRIVATE, remote
from verify_automatic_source_restoration import read_pinned, write_exclusive

SCRIPT = r'''
import datetime,hashlib,json,pathlib
def pinned(reference):
 path=pathlib.Path(reference['path']);need(path.resolve(strict=True)==path and not path.is_symlink(),'DIAGNOSTIC_PATH_ALIAS')
 raw=path.read_bytes();need(len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'DIAGNOSTIC_PIN_CHANGED')
 return json.loads(raw)
def need(value,message):
 if not value:raise ValueError(message)
def read(path):
 path=pathlib.Path(path);need(path.resolve(strict=True)==path and not path.is_symlink(),'DIAGNOSTIC_PATH_ALIAS')
 raw=path.read_bytes();need(len(raw)<4*1024*1024,'DIAGNOSTIC_SIZE_LIMIT')
 pin=dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
 return dict(pin=pin,value=json.loads(raw))
config=pinned(CONTROL_PIN);operation=REQUEST['operationId'];ledger=pathlib.Path(config['ledgerRoot'])/operation
records={name:read(ledger/name) for name in ('request.json','selection.json','execute/native-intent.json','execute/native-process.json','execute/native-original-exit.json')}
selected=records['selection.json']['value'];owner=pinned(selected['ownerConfigurationPin'])
owner_root=pathlib.Path(owner['operationRoot'])/hashlib.sha256(operation.encode()).hexdigest()
for name in ('start.json','worker-process.json'):
 records['owner/'+name]=read(owner_root/name)
launched=records['execute/native-intent.json']['value'];process=records['execute/native-process.json']['value'];exited=records['execute/native-original-exit.json']['value']
checks=dict(identities=all(row['operationId']==row['requestId']==operation for row in (launched,process,exited)),
 requestPins=launched['requestPin']==exited['requestPin']==records['request.json']['pin'],
 intentPins=process['intentPin']==exited['intentPin']==records['execute/native-intent.json']['pin'],
 pid=process['pid']==exited['pid'],allowedLauncherExit=exited['actualExitCode'] in (0,3),notTimedOut=exited['timedOut'] is False,
 programPin=launched['programPin']==selected['ownerProgramPin'],configurationPin=launched['configurationPin']==selected['ownerConfigurationPin'])
expected_argv=[config['pythonPin']['path'],selected['ownerProgramPin']['path'],'--configuration',selected['ownerConfigurationPin']['path'],
 '--request',records['request.json']['pin']['path'],'--output',str(ledger/'execute/result.json')]
checks['actualArgvMatchesExecutor']=launched['argv']==expected_argv
result=read(owner_root/'result.json');result_value=result['value']
print(json.dumps(dict(status='OBSERVED',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=operation,
 checks=checks,records=records,expectedArgv=expected_argv,configPythonPin=config['pythonPin'],
 originalOwnerResultPin=result['pin'],originalOwnerResult={k:result_value[k] for k in ('operationId','requestId','state','actualExitCode','failureCode','finishedAt')},
 noServerMutation=True,actualAuditRerun=False)))
'''


if __name__ == '__main__':
    failure=PRIVATE/'172.30.30.57-error-cb981ded009d.private.log'
    raw=failure.read_bytes()
    assert len(raw)==275 and hashlib.sha256(raw).hexdigest()=='cb981ded009da56d9d3415786a9017e1d7a10c43d502cc6ddaea24e3ef40ce92'
    private=PRIVATE/'automatic-full373-dispatch-contract-diagnostic.private.json'
    public=TASK/'automatic-full373-dispatch-contract-diagnostic.json'
    assert not private.exists() and not public.exists()
    installation,installed_pin=read_pinned(TASK/'automatic-control-installation-57.json')
    submission,submission_pin=read_pinned(TASK/'automatic-full-ui-submission.json')
    variables=dict(CONTROL_PIN=installation['controllers'][0]['controlConfigurationPin'],REQUEST=submission['request'])
    code='\n'.join(key+'='+repr(value) for key,value in variables.items())+'\n'+SCRIPT
    compile(code,'dispatch-contract-diagnostic','exec')
    report=remote('172.30.30.57',code,60)
    assert report['operationId']==submission['request']['operationId']
    write_exclusive(private,report)
    summary={key:report[key] for key in ('status','observedAt','operationId','checks','originalOwnerResultPin','originalOwnerResult','noServerMutation','actualAuditRerun')}
    summary['inputPins']=dict(installation=installed_pin,submission=submission_pin,
        originalFailure=dict(path=failure.as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    summary['diagnosticPin']=read_pinned(private)[1]
    summary['launcherActualExitCode']=report['records']['execute/native-original-exit.json']['value']['actualExitCode']
    summary['launcherTimedOut']=report['records']['execute/native-original-exit.json']['value']['timedOut']
    write_exclusive(public,summary)
    print(json.dumps(summary))
