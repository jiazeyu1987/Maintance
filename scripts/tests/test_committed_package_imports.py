"""Formal build identity for the same closed import boundary; no business IO."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

import pytest

ROOT=Path(__file__).resolve().parents[2]
HELPER=ROOT/'doc/tasks/20261106-spug-prod-incremental-to-two-targets/preservation_candidate_imports.py'

def pin(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

@pytest.fixture(scope='module')
def formal(tmp_path_factory):
    base=tmp_path_factory.mktemp('committed-package')
    spec=importlib.util.spec_from_file_location('formal_test_builder',ROOT/'ops/backup_engine/build_variants.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    baseline,origin=builder.standard_sources()
    payload=builder.safe_fixes(baseline)
    origin.update(source='frozen-20261021-with-reviewed-fixes')
    archive=base/'standard.tgz';builder.write_package(archive,'standard',payload,origin)
    engine=base/'engine';engine.mkdir()
    with tarfile.open(archive) as ar:ar.extractall(engine,filter='data')
    metadata=json.loads((engine/'package.json').read_bytes())
    report=base/'build.json'
    value=dict(status='PASS',targetCommit='1'*40,exactCommittedInput=True,allFilesShaAndCompileVerified=True,
        packages=[dict(pin(archive),variant='standard',fileManifestSha256=metadata['packageSha256'],fileCount=len(metadata['files']))])
    return base,engine,archive,report,value

@pytest.mark.parametrize('problem',['valid','report-pin','archive-pin','commit','status','manifest','payload'])
def test_formal_package_identity_rejects_unproven_inputs(formal,tmp_path,problem):
    import shutil
    base,original,archive,_,value=formal
    engine=tmp_path/'engine';shutil.copytree(original,engine)
    report=tmp_path/'build.json';value=json.loads(json.dumps(value))
    if problem=='commit':value['targetCommit']=''
    if problem=='status':value['status']='FAIL'
    if problem=='manifest':value['packages'][0]['fileManifestSha256']='0'*64
    report.write_text(json.dumps(value),encoding='utf-8')
    report_pin=pin(report);archive_pin=pin(archive)
    if problem=='report-pin':report_pin['sha256']='0'*64
    if problem=='archive-pin':archive_pin['sha256']='0'*64
    if problem=='payload':
        p=engine/'common/recovery_restore_inputs.py';p.write_bytes(p.read_bytes()+b'\n# drift\n')
    spec=importlib.util.spec_from_file_location('formal_imports_'+problem.replace('-','_'),HELPER)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    run=lambda:helper.committed_package_imports(engine,pin(engine/'package.json'),report_pin,archive_pin)
    if problem=='valid':
        with run() as route:
            assert route.manifest.get('candidateOnly') is not True
            assert 'recovery_restore_inputs' in route.modules
    else:
        with pytest.raises(RuntimeError,match='COMMITTED_|CANDIDATE_MEMBER_CHANGED'):
            run()
