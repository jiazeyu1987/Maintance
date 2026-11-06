"""Install the verified semantic-health generation, retaining both actual failures."""
import argparse
import base64
import hashlib
import json
from install_prod_control import COMMON,PRIVATE,TASK,ROOT,HOST,PYTHON,DEPENDENCIES,APP,TARGET,POINT,UNIT,LOCK,remote
from install_retained_control import CHECK as PREVIOUS_INSTALLATION

def script_template():
    replacements=[
        ("receipt['sourceCommit']=='9b3a298ce378b3ac565792a3bc3b92f1e5208898'", "receipt['sourceCommit']=='1595d0f414756362734b51193233b5606ca544ec'"),
        ("len(version['files'])==124", "len(version['files'])==125"),
        ('observe(original,request,oldroot,0)', 'observe(original,request,oldroot,885)'),
        ("len(package['files'])==125 and len(archive.getnames())==126", "len(package['files'])==126 and len(archive.getnames())==127"),
        ('from recovery_mysql_scheduler import MainMysqlScheduler;Native', 'from recovery_mysql_scheduler import MainMysqlScheduler;from recovery_main_health import wait_healthy;Native')]
    text=PREVIOUS_INSTALLATION
    for old,new in replacements:
        assert text.count(old)==1,'INSTALLATION_CONTEXT_CHANGED'
        text=text.replace(old,new)
    return text

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);args=parser.parse_args()
    commit=args.commit;assert len(commit)==40 and all(c in '0123456789abcdef' for c in commit)
    assert not (TASK/'health-control-installation.json').exists(),'INSTALLATION_ALREADY_RECORDED'
    build=json.loads((TASK/'release-build-verification.json').read_text(encoding='utf-8'))
    assert build['status']=='PASS' and build['targetCommit']==commit and build['fileCount']==126
    failure=json.loads((TASK/'healthcheck-failure-diagnosis.json').read_text(encoding='utf-8'))
    old=json.loads((TASK/'database-state-failure-diagnosis.json').read_text(encoding='utf-8'))
    installed=json.loads((TASK/'retained-control-installation.json').read_text(encoding='utf-8'))
    quiesced=json.loads((TASK/'health-storage-quiescence.json').read_text(encoding='utf-8'))
    assert quiesced['status']=='PASS' and quiesced['operationId']==failure['operationId'] and quiesced['originalMinioStopped'] and quiesced['originalFailurePinsUnchanged']==908
    raw=(PRIVATE/('package-'+commit[:7])/'backup-restore-standard.tgz').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==build['packageSha256']
    assert len(failure['evidencePins'])==703 and len(old['evidencePins'])==205
    values=dict(ROOT=ROOT,ENGINE=ROOT+'/engine-mainv2-'+commit[:7],HOST=HOST,COMMIT=commit,PYTHON=PYTHON,
        DEPENDENCIES=DEPENDENCIES,APP=APP,TARGET=TARGET,POINT=POINT,UNIT=UNIT,LOCK=LOCK,
        EXPECTED_OWNER=installed['ownerConfigurationPin'],EXPECTED_CONTROL=installed['controlConfigurationPin'],
        FAILED_OPERATION=failure['operationId'],FAILURE_PINS=failure['evidencePins']+old['evidencePins'],ACTIVE_POINTER=failure['activePointerPin'],
        PACKAGE=base64.b64encode(raw).decode(),PACKAGE_SHA=build['packageSha256'])
    script='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+COMMON.split('need(root.resolve()==root')[0]+'\n'+script_template()
    report=remote(script,180)
    (TASK/'health-control-installation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
