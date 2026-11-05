"""Verify and remove only this fix's clean, unused build worktrees/test volume."""
import json
from pathlib import Path
import subprocess
import sys
from preflight import COMMON, PRIVATE, TASK, remote
from test_recovery_linux import DOCKER

ROOT=TASK.parents[2]
VOLUME='spug-review-network-unit-20261105'
REPORTS=('network-release-build-verification.json','network-release-build-76bb60b-verification.json')

def git(*args,cwd=ROOT):
    return subprocess.check_output(['git',*args],cwd=cwd).decode('utf-8').strip()

def check():
    reports=[]
    for name in REPORTS:
        report=json.loads((TASK/name).read_text(encoding='utf-8'))
        path=Path(report['worktree']).resolve()
        assert path.parent==PRIVATE.resolve() and path.name=='release-'+report['targetCommit'][:7]
        assert path.is_dir() and not report['newCommits'] and not report['mergeRequired']
        assert git('rev-parse','HEAD',cwd=path)==report['targetCommit']
        assert not git('status','--porcelain',cwd=path)
        assert not git('rev-list',report['targetCommit']+'..HEAD',cwd=path)
        reports.append(dict(report=name,worktree=str(path),targetCommit=report['targetCommit'],clean=True,newCommits=False,mergeRequired=False))
    install=json.loads((TASK/'retry-control-installation.json').read_text(encoding='utf-8'))
    baseline=json.loads((TASK/'restore-preflight.json').read_text(encoding='utf-8'))
    pins={key:baseline[key] for key in ('ownerConfigurationPin','controlConfigurationPin')}
    script=COMMON.split('receiptpath=root/')[0]+'\nINSTALL='+repr(install)+'\nBASELINE='+repr(pins)+r'''
receipt=json.loads((root/'target-installation.json').read_bytes())
need(receipt['ownerConfigurationPin']==INSTALL['ownerConfigurationPin'] and receipt['controlConfigurationPin']==INSTALL['controlConfigurationPin'],'CONTROL_CHANGED')
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
engine=pathlib.Path(owner['formalModuleDirectory']).parent
need(str(engine)==INSTALL['engine'],'ENGINE_CHANGED')
version=json.loads((engine/'package.json').read_bytes())
need(all(pin(engine/n)['sha256']==h for n,h in version['files'].items()),'PACKAGE_CHANGED')
need(run(['systemctl','is-active',receipt['service']]).strip()==b'active','CONTROL_INACTIVE')
paths=control['environment']['PYTHONPATH'].split(':')+[control['pythonPin']['path']]+[v['path'] for v in control['programPins'].values()]
need(all(pathlib.Path(p).is_absolute() and pathlib.Path(p).exists() for p in paths),'RUNTIME_PATH_INVALID')
oldowner=read(BASELINE['ownerConfigurationPin']);oldcontrol=read(BASELINE['controlConfigurationPin'])
oldengine=pathlib.Path(oldowner['formalModuleDirectory']).parent
expected=oldcontrol['environment']['PYTHONPATH'].replace(str(oldengine)+'/',str(engine)+'/')
need(control['environment']['PYTHONPATH']==expected,'MODULE_PATH_CHANGED_OUTSIDE_GENERATION')
need(control['pythonPin']==oldcontrol['pythonPin'],'PYTHON_RUNTIME_CHANGED')
need(all(v['path'].startswith(str(engine)+'/') for v in control['programPins'].values()),'UNSTABLE_ENTRY_PATH')
print(json.dumps(dict(status='PASS',controlActive=True,runtimeDependsOnReleaseWorktree=False,engine=str(engine),packageFileCount=len(version['files']))))
'''
    stable=remote('172.30.30.59',script,35)
    volume=json.loads(subprocess.check_output([DOCKER,'volume','inspect',VOLUME]))
    assert len(volume)==1 and volume[0]['Name']==VOLUME
    assert volume[0]['Labels']['codex.task']=='spug-prod-full-to-review-20261105'
    assert not subprocess.check_output([DOCKER,'ps','-aq','--filter','volume='+VOLUME]).strip()
    return dict(status='PASS',worktrees=reports,stableRuntime=stable,volume=VOLUME,volumeTaskLabelVerified=True,volumeReferences=0)

if __name__=='__main__':
    phase=sys.argv[1]
    assert phase in ('check','cleanup')
    result=check()
    if phase=='cleanup':
        for row in result['worktrees']:
            path=Path(row['worktree']).resolve()
            assert path.parent==PRIVATE.resolve() and path.name=='release-'+row['targetCommit'][:7]
            git('worktree','remove',str(path))
            registrations=git('worktree','list','--porcelain').replace('\\','/').lower()
            assert not path.exists() and path.as_posix().lower() not in registrations
            report=json.loads((TASK/row['report']).read_text(encoding='utf-8'))
            report.update(deleted=True,physicalPathAbsent=True,gitRegistrationAbsent=True,cleanupCommand='git worktree remove '+str(path))
            (TASK/row['report']).write_text(json.dumps(report,indent=2),encoding='utf-8')
            row.update(deleted=True,physicalPathAbsent=True,gitRegistrationAbsent=True)
        subprocess.run([DOCKER,'volume','rm',VOLUME],check=True,capture_output=True)
        volumes=subprocess.check_output([DOCKER,'volume','ls','--format','{{.Name}}']).decode().splitlines()
        assert VOLUME not in volumes
        result['volumeDeleted']=True
    (TASK/('network-cleanup-'+phase+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
