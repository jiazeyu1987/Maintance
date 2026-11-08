"""Delete only this task's clean committed build after real acceptance."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from common import TASK,PRIVATE,now,write
from closeout_contracts import build_entry,owned_builds,automatic_chain,file_pin,moment,current_installations

ROOT=TASK.parents[2]
DOCKER='C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
POWERSHELL='C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe'
def command(args,cwd=None):return subprocess.check_output(args,cwd=cwd,timeout=40).decode('utf-8-sig').strip()
def read(name):return json.loads((TASK/name).read_text(encoding='utf-8'))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['register','check','cleanup']);parser.add_argument('--generation');parser.add_argument('--report');args=parser.parse_args()
 entries=owned_builds(TASK)
 if args.phase=='register':
  assert args.report and not args.generation,'EXPLICIT_BUILD_REPORT_REQUIRED'
  added=build_entry(TASK,PRIVATE,args.report)
  assert added['generation'] not in [entry['generation'] for entry in entries],'BUILD_ALREADY_REGISTERED'
  manifest=read('task-owned-builds.json');manifest['builds'].append(added)
  write(TASK/'task-owned-builds.json',manifest)
  print(json.dumps(dict(status='REGISTERED',generation=added['generation'],serverWrites=False,deleted=False)))
  raise SystemExit(0)
 assert not args.report and args.generation,'EXPLICIT_GENERATION_REQUIRED'
 selected=[entry for entry in entries if entry['generation']==args.generation]
 assert len(selected)==1,'BUILD_NOT_EXPLICITLY_OWNED'
 selected=selected[0];generations=[entry['generation'] for entry in entries]
 assert '## Current Status\nready_for_closeout\n' in (TASK/'task.md').read_text(encoding='utf-8'),'TASK_NOT_READY_FOR_CLOSEOUT'
 point=read('new-incremental-point-verified.json');readback=read('new-incremental-payload-readback.json')
 assert point['status']=='PASS' and point['actualExitCode']==0 and readback['status']=='PASS' and readback['operationId']==point['operationId']
 assert readback['payloadContentVerified'] and readback['exactTreeVerifiedBeforeAndAfter']
 for suffix in ('58','59'):
  native=read('restore-'+suffix+'-native-evidence.json')
  assert native['status']=='PASS' and native['actualExitCode']==0 and native['backupOperationId']==point['operationId']
  for name in ('restored-runtime-'+suffix+'.json','target-'+suffix+'-after-business.json','target-'+suffix+'-preservation.json'):
   assert read(name)['status']=='PASS'
 assert read('source-after-backup-preservation.json')['status']=='PASS' and read('source-global-state-restored.json')['status']=='PASS'
 automatic=automatic_chain(TASK)
 stable=read('stable-controls-closeout.json')
 assert stable['status']=='PASS' and stable['automaticOperationIds']==automatic['operationIds'],'CURRENT_CONTROLS_AND_AUTOMATIC_CHAIN_REQUIRED'
 assert stable['currentInstallationEvidenceVerified'] and stable['catalogueCurrentRuntimeVerified']
 assert moment(stable['observedAt'])>=moment(automatic['finalFinishedAt']),'STABLE_CONTROL_PROOF_PRECEDES_AUTOMATIC_CHAIN'
 assert stable['currentInstallationSelectionPin']==file_pin(TASK,'automatic-current-installations.json'),'CURRENT_INSTALLATION_SELECTION_CHANGED'
 current_installations(TASK)
 report=read('release-build-'+args.generation+'.json');path=Path(report['worktree']).resolve()
 assert path.parent==PRIVATE.resolve() and path.name=='release-'+report['targetCommit'][:7] and path.is_dir() and not path.is_symlink(),'BUILD_PATH_OUT_OF_SCOPE'
 assert report['targetCommit']==selected['targetCommit']
 assert report['status']=='PASS' and report['allFilesShaAndCompileVerified'] and report['fileCount']==selected['fileCount'] and not report['newCommits'] and not report['mergeRequired'] and not report['deleted']
 assert command(['git','rev-parse','HEAD'],path)==report['targetCommit'],'BUILD_HEAD_CHANGED'
 assert not command(['git','status','--porcelain=v1','--untracked-files=all','--ignored'],path),'BUILD_HAS_LOCAL_OR_IGNORED_FILES'
 assert not command(['git','rev-list',report['targetCommit']+'..HEAD'],path),'UNMERGED_BUILD_COMMITS'
 package=Path(selected['package'])
 assert hashlib.sha256(package.read_bytes()).hexdigest()==report['packageSha256'],'RETAINED_PACKAGE_CHANGED'
 scan=r'''$ErrorActionPreference='Stop'
$target='TARGET_LITERAL'
$matches=@(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -ne $PID -and $_.CommandLine -and $_.CommandLine.Replace('\','/').ToLowerInvariant().Contains($target)})
if($matches.Count -ne 0){throw 'BUILD_PROCESS_STILL_REFERENCED'}
Write-Output 'PASS'
'''.replace('TARGET_LITERAL',path.as_posix().lower())
 assert command([POWERSHELL,'-NoProfile','-Command',scan])=='PASS'
 label='codex.task=20261106-spug-prod-incremental-to-two-targets'
 assert not command([DOCKER,'ps','-aq','--filter','label='+label]),'OWNED_TEST_CONTAINER_REMAINS'
 assert not command([DOCKER,'volume','ls','-q','--filter','label='+label]),'OWNED_TEST_VOLUME_REMAINS'
 result=dict(status='PASS',observedAt=now(),backupOperationId=point['operationId'],automaticOperationIds=automatic['operationIds'],generation=args.generation,buildReportPin=selected['reportPin'],ownedBuildManifestPin=file_pin(TASK,'task-owned-builds.json'),worktree=str(path),targetCommit=report['targetCommit'],cleanIncludingIgnored=True,noActiveProcessReferences=True,newCommits=False,mergeRequired=False,retainedPackageSha256=report['packageSha256'],ownedTestContainersAndVolumesAbsent=True,deleted=False)
 if args.phase=='cleanup':
  command(['git','worktree','remove',str(path)],ROOT)
  registrations=command(['git','worktree','list','--porcelain'],ROOT).replace('\\','/').lower()
  assert not path.exists() and path.as_posix().lower() not in registrations,'BUILD_NOT_REMOVED'
  result.update(deleted=True,physicalPathAbsent=True,gitRegistrationAbsent=True)
  result.update(cleanupCommand=['git','worktree','remove',str(path)])
 write(TASK/('owned-build-'+args.phase+'-'+args.generation+'.json'),result)
 if args.phase=='cleanup' and all((TASK/('owned-build-cleanup-'+g+'.json')).exists() for g in generations):
  completed=[read('owned-build-cleanup-'+g+'.json') for g in generations]
  assert all(v['status']=='PASS' and v['deleted'] and v['gitRegistrationAbsent'] and not Path(v['worktree']).exists() for v in completed)
  assert {entry['generation'] for entry in completed}==set(generations)
  write(TASK/'owned-build-cleanup.json',dict(status='PASS',observedAt=now(),deleted=True,ownedBuildManifestPin=file_pin(TASK,'task-owned-builds.json'),builds=completed))
 print(json.dumps(result))
