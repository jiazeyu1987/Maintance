"""Verify stable local transports and exact installed Spug route, without writes."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

from install_prod_control import TASK, PRIVATE, APP, TARGET
from install_local_route import RUNTIME, READ, docker

POWERSHELL='C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
PORTS=r'''
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$ports=PORTS_LITERAL
$rows=@()
foreach($port in $ports) {
 $connections=@(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction Stop)
 if($connections.Count -ne 1){throw 'TRANSPORT_LISTENER_AMBIGUOUS'}
 $connection=$connections[0]
 $process=Get-CimInstance Win32_Process -Filter ('ProcessId='+$connection.OwningProcess)
 if(-not $process -or $process.ExecutablePath -ne 'C:\Windows\System32\OpenSSH\ssh.exe'){throw 'TRANSPORT_OWNER_INVALID'}
 $digest=[Security.Cryptography.SHA256]::Create()
 $commandDigest=([BitConverter]::ToString($digest.ComputeHash([Text.Encoding]::UTF8.GetBytes($process.CommandLine)))).Replace('-','').ToLower()
 $rows+=@{port=$port;address=$connection.LocalAddress;pid=$process.ProcessId;parentPid=$process.ParentProcessId;startedAt=$process.CreationDate.ToUniversalTime().ToString('o');commandSha256=$commandDigest}
}
$rows | ConvertTo-Json -Compress
'''

def ports(values):
    raw=subprocess.check_output([POWERSHELL,'-NoProfile','-Command',PORTS.replace('PORTS_LITERAL','@('+','.join(map(str,values))+')')])
    value=json.loads(raw.decode('utf-8-sig'))
    return value if isinstance(value,list) else [value]

def read(name):
    return json.loads((TASK/name).read_text(encoding='utf-8'))

def closeout():
    native=read('restored-native-evidence.json')
    assert native['status']=='PASS' and native['state']=='SUCCEEDED' and native['targetConfigRef']==TARGET
    original=read('local-transport-baseline.json')
    current=ports([42657,18557,43657])
    assert current[:2]==original['transports'],'ORIGINAL_SOURCE_OR_PROGRESS_TRANSPORT_CHANGED'
    receipt=read('transport-installation.json')
    assert receipt['taskName']=='SpugProdMainRestoreTransport57-20261105'
    stable=Path(receipt['stablePath'])
    assert stable.resolve().parent==PRIVATE.resolve() and stable.name=='production_control_transport.ps1'
    assert hashlib.sha256(stable.read_bytes()).hexdigest()==receipt['sha256']
    assert stable.read_bytes()==(TASK/'production_control_transport.ps1').read_bytes(),'STABLE_TRANSPORT_SCRIPT_CHANGED'
    live=json.loads((PRIVATE/'transport-production.json').read_text(encoding='utf-8'))
    assert live['target']=='172.30.30.57' and live['controlPort']==43657
    assert current[2]['pid']==live['sshPid'] and current[2]['parentPid']==live['supervisorPid']
    check=r'''
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$task=Get-ScheduledTask -TaskName 'SpugProdMainRestoreTransport57-20261105'
if($task.State -ne 'Running' -or $task.Actions.Count -ne 1){throw 'TRANSPORT_TASK_NOT_RUNNING'}
if($task.Actions[0].Execute -ne 'C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'){throw 'TRANSPORT_ACTION_CHANGED'}
if($task.Actions[0].Arguments -ne '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File C:/Spug/runtime/private/full-to-prod-20261105/production_control_transport.ps1'){throw 'TRANSPORT_STABLE_PATH_CHANGED'}
if($task.Principal.RunLevel -ne 'Limited'){throw 'TRANSPORT_RUN_LEVEL_CHANGED'}
$parent=Get-CimInstance Win32_Process -Filter 'ProcessId=SUPERVISOR_PID'
if(-not $parent -or -not $parent.CommandLine.Contains('C:/Spug/runtime/private/full-to-prod-20261105/production_control_transport.ps1')){throw 'TRANSPORT_SUPERVISOR_CHANGED'}
Write-Output 'PASS'
'''.replace('SUPERVISOR_PID',str(live['supervisorPid']))
    assert subprocess.check_output([POWERSHELL,'-NoProfile','-Command',check]).decode('utf-8-sig').strip()=='PASS'
    plan=json.loads((PRIVATE/'production-route-plan.private.json').read_text(encoding='utf-8'))
    current_settings=docker(READ)
    assert current_settings==plan['settings'],'SPUG_SETTINGS_CHANGED'
    assert json.loads((RUNTIME/'private/smallapp-bridge.private.json').read_bytes())==plan['bridge'],'SPUG_BRIDGE_CHANGED'
    for name,value in plan['files'].items():
        assert json.loads((RUNTIME/'private'/name).read_bytes())==value,'SPUG_TARGET_ROUTE_CHANGED'
    assert hashlib.sha256((RUNTIME/'ops/spug/smallapp_adapter.py').read_bytes()).hexdigest()==plan['adapterSha256']
    binding=next(b for b in current_settings['smallapp-simple-settings.json']['bindings'] if b['applicationId']==APP)
    assert set(binding['overwriteTargetServers'])=={'172.30.30.57','172.30.30.58','172.30.30.59'}
    assert binding['overwriteTargetServers']['172.30.30.57']==TARGET
    credentials=json.loads((PRIVATE/'target-control-headers.private.json').read_bytes())['headers']
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(urllib.request.Request('http://127.0.0.1:43657/selections?targetConfigRef='+TARGET,headers=credentials),timeout=100) as response:
        value=json.load(response);assert response.status==200
    selected=[a for a in value['applications'] if a['applicationId']==APP]
    assert len(selected)==1 and TARGET in selected[0]['freshTargetConfigRefs'],'LIVE_TARGET_ADMISSION_FAILED'
    return dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=native['operationId'],
                originalTransportsPreserved=True,stableTaskRunning=True,stableScriptVerified=True,liveTargetAdmission=True,
                exactSpugSettingsAndRoutesVerified=True,registeredTargetServers=sorted(binding['overwriteTargetServers']),
                transports=current,restoreSubmitted=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['baseline','closeout']);args=parser.parse_args()
    if args.phase=='baseline':
        destination=TASK/'local-transport-baseline.json'
        assert not destination.exists(),'TRANSPORT_BASELINE_ALREADY_RECORDED'
        result=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),transports=ports([42657,18557]))
    else:
        destination=TASK/'local-control-closeout.json';result=closeout()
    destination.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
