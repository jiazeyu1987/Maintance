"""Remove exact clean build worktrees and owned tests after verified restore."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess

from install_prod_control import PRIVATE, TASK, TARGET, POINT
from test_storage_linux import ROOT, DOCKER, NAME as VOLUME
from prepare_network_linux import NETWORK

LABEL='codex.task=spug-full-to-prod-20261105'
BUILDS={'release-build-db64656.json':123,'release-build-bdd8aab.json':124,'release-build-9b3a298.json':124,'release-build-1595d0f.json':125,'release-build-9dce318.json':126}

def read(name):
    return json.loads((TASK/name).read_text(encoding='utf-8'))

def command(args,cwd=None):
    return subprocess.check_output(args,cwd=cwd).decode('utf-8').strip()

def ready():
    native=read('restored-native-evidence.json')
    assert native['status']=='PASS' and native['state']=='SUCCEEDED' and native['actualExitCode']==0
    assert native['targetConfigRef']==TARGET and native['backupOperationId']==POINT
    assert native['archiveViewRestored'] and native['publishedWriteFenceReleased'] and native['hostResourceReservationReleased']
    assert native['mysqlSchedulerOriginalStateRestored']
    assert native['mainSemanticReadinessVerified'] and len(native['mainReadinessPins'])==3
    for name,count in [('failed-attempt-preservation.json',205),('health-failed-attempt-preservation.json',703)]:
        report=read(name);assert report['status']=='PASS' and report['remoteOriginalPinsUnchanged']==count
        assert report['localOriginalPinsUnchanged']==8 and report['successfulNewOperationId']==native['operationId']
    for name in ['restored-runtime.json','target-production-after-restore-business.json','protection-runtime-verification.json','other-business-after-restore.json']:
        report=read(name);assert report['status']=='PASS'
        if 'operationId' in report:assert report['operationId']==native['operationId']
    assert read('target-production-after-restore-business.json')['businessMutations']==0
    assert read('protection-runtime-verification.json')['stableRuntimePaths']
    assert read('preservation-full-point-verified.json')['state']=='SUCCEEDED'
    payload=read('preservation-full-payload-readback.json')
    assert payload['status']=='PASS' and payload['payloadContentVerified']
    assert payload['operationId']==read('preservation-full-point-verified.json')['operationId']
    assert payload['exactTreeVerifiedBeforeAndAfter'] and payload['metadataPinsVerifiedBeforeAndAfter']
    return native['operationId']

def check():
    operation=ready();builds=[]
    for name,count in BUILDS.items():
        report=read(name);path=Path(report['worktree']).resolve()
        assert path.parent==PRIVATE.resolve() and path.name=='release-'+report['targetCommit'][:7],'BUILD_PATH_OUT_OF_SCOPE'
        assert report['status']=='PASS' and report['allFilesShaAndCompileVerified'] and report['fileCount']==count
        assert not report['newCommits'] and not report['mergeRequired'] and not report['deleted']
        assert command(['git','rev-parse','HEAD'],path)==report['targetCommit'],'BUILD_HEAD_CHANGED'
        assert not command(['git','status','--porcelain'],path),'BUILD_DIRTY'
        assert not command(['git','rev-list',report['targetCommit']+'..HEAD'],path),'UNMERGED_BUILD_COMMITS'
        builds.append(dict(report=name,worktree=str(path),targetCommit=report['targetCommit'],newCommits=False,mergeRequired=False))
    ids=command([DOCKER,'ps','-aq','--filter','label='+LABEL]).splitlines()
    assert len(ids)==1,'OWNED_CONTAINER_SET_CHANGED'
    rows=json.loads(command([DOCKER,'inspect',*ids]));assert len(rows)==1
    row=rows[0]
    assert row['Name']=='/'+NETWORK and row['Config']['Labels']['codex.task']=='spug-full-to-prod-20261105'
    assert row['Id']==(TASK/'linux-network-environment.log').read_bytes().splitlines()[0].decode(),'OWNED_CONTAINER_ID_CHANGED'
    assert row['Config']['Image']=='python:3.12-bookworm' and row['Path']=='sleep' and row['Args']==['21600']
    assert row['HostConfig']['NetworkMode']!='host' and not row['HostConfig']['Privileged']
    mounts=row['Mounts'];assert len(mounts)==2
    assert any(m['Type']=='bind' and Path(m['Source']).as_posix().lower()==ROOT.as_posix().lower() and m['Destination']=='/source' and not m['RW'] for m in mounts),'TEST_SOURCE_MOUNT_CHANGED'
    assert any(m['Type']=='volume' and m['Name']==VOLUME and m['Destination']=='/work' for m in mounts)
    if row['State']['Running']:
        scan="import os,pathlib; own=os.getpid(); rows=[(int(p.name),(p/'cmdline').read_bytes().split(b'\\0')[0]) for p in pathlib.Path('/proc').iterdir() if p.name.isdecimal() and int(p.name)!=own]; assert rows==[(1,b'sleep')], 'ACTIVE_TEST_PROCESS'; print('PASS')"
        assert command([DOCKER,'exec',row['Id'],'python','-B','-c',scan])=='PASS'
    volumes=command([DOCKER,'volume','ls','-q','--filter','label='+LABEL]).splitlines();assert volumes==[VOLUME]
    volume=json.loads(command([DOCKER,'volume','inspect',VOLUME]))[0]
    assert volume['Name']==VOLUME and volume['Labels']['codex.task']=='spug-full-to-prod-20261105'
    references=command([DOCKER,'ps','-aq','--no-trunc','--filter','volume='+VOLUME]).splitlines()
    assert references==[row['Id']],'SHARED_TEST_VOLUME'
    return dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=operation,worktrees=builds,containerId=row['Id'],containerName=NETWORK,volume=VOLUME,ownershipVerified=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['check','cleanup']);args=parser.parse_args()
    result=check()
    if args.phase=='cleanup':
        for row in result['worktrees']:
            path=Path(row['worktree']).resolve()
            assert path.parent==PRIVATE.resolve() and path.name=='release-'+row['targetCommit'][:7]
            command(['git','worktree','remove',str(path)],ROOT)
            registrations=command(['git','worktree','list','--porcelain'],ROOT).replace('\\','/').lower()
            assert not path.exists() and path.as_posix().lower() not in registrations
            report=read(row['report']);report.update(deleted=True,physicalPathAbsent=True,gitRegistrationAbsent=True,cleanupCommand='git worktree remove '+str(path))
            (TASK/row['report']).write_text(json.dumps(report,indent=2),encoding='utf-8')
            row['deleted']=True
        command([DOCKER,'rm','-f',result['containerId']])
        assert not command([DOCKER,'ps','-aq','--filter','volume='+VOLUME]),'TEST_VOLUME_STILL_REFERENCED'
        command([DOCKER,'volume','rm',VOLUME])
        assert not command([DOCKER,'ps','-aq','--filter','label='+LABEL])
        assert not command([DOCKER,'volume','ls','-q','--filter','label='+LABEL])
        result.update(ownedTestContainerRemoved=True,ownedTestVolumeRemoved=True)
        latest=read('release-build-9dce318.json')
        (TASK/'release-build-verification.json').write_text(json.dumps(latest,indent=2),encoding='utf-8')
    (TASK/('owned-resource-'+args.phase+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
