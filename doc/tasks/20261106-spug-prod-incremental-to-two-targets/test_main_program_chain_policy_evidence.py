"""Small real protocol archives, never installed product or business evidence."""
from copy import deepcopy
import hashlib
import importlib
import io
import json
from pathlib import Path
import tarfile
import sys
import subprocess

import pytest

import main_program_control_activation as activation
import main_program_control_upgrade_plan as planner

MODULES=('common/repository_records.py','common/repository_minimal.py','control/recovery_control_incremental_plan.py')
PROFILE='incremental-chain-policy-admission/v1'


def subject():return importlib.import_module('main_program_chain_policy_evidence')
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def local(name,value):
    raw=canonical(value);return dict(file=name,bytes=len(raw),sha256=digest(raw))


def package(path,files):
    hashes={name:digest(raw) for name,raw in files.items()}
    manifest=dict(files=hashes,packageSha256=digest(canonical(hashes)))
    with tarfile.open(path,'w:gz') as archive:
        for name,raw in {**files,'package.json':canonical(manifest)}.items():
            info=tarfile.TarInfo(name);info.size=len(raw);archive.addfile(info,io.BytesIO(raw))
    raw=path.read_bytes()
    return dict(packagePin=dict(path=str(path),bytes=len(raw),sha256=digest(raw)),
        fileCount=len(files),fileManifestSha256=manifest['packageSha256'])


@pytest.fixture
def materials(tmp_path):
    before={};after={};rows=[]
    for variant,count in [('standard',147),('lightweight',146)]:
        old={name:b'VALUE = 1\n' for name in MODULES}
        old.update({'other/module_%03d.py'%n:b'UNCHANGED = True\n' for n in range(count-3)})
        new=deepcopy(old)
        for name in MODULES:new[name]=b'VALUE = 2\n'
        old_package=package(tmp_path/(variant+'-old.tgz'),old)
        new_package=package(tmp_path/(variant+'-new.tgz'),new)
        evidence={name:dict(oldBytes=len(old[name]),newBytes=len(new[name]),oldSha256=digest(old[name]),
            newSha256=digest(new[name]),lineEndingOnly=False) for name in MODULES}
        rows.append(dict(variant=variant,**new_package,predecessor=dict(variant=variant,**old_package),
            changedFileEvidence=evidence,unchangedFileSha256={name:digest(raw) for name,raw in new.items() if name not in evidence}))
        before[variant]=old;after[variant]=new
    def build(row,commit):return dict(status='PASS',targetCommit=commit,worktree=str(tmp_path/'checkout'),
        fileCount=147,fileManifestSha256=row['fileManifestSha256'],packageSha256=row['packagePin']['sha256'],
        allFilesShaAndCompileVerified=True,newCommits=False,mergeRequired=False)
    new_build=build(rows[0],'b'*40);old_build=build(rows[0]['predecessor'],'a'*40)
    new_pin=local('release-build-bbbbbbb.json',new_build);old_pin=local('release-build-aaaaaaa.json',old_build)
    delta=dict(schemaVersion='MainProgramChainPolicyPackageDelta/v1',status='PASS',profile=PROFILE,
        sourceCommit='b'*40,predecessorCommit='a'*40,buildPin=new_pin,predecessorBuildPin=old_pin,
        predecessorGenerationPin=local('generation-a.json',{}),sourceSnapshotPin=local('snapshot.json',{}),packages=rows)
    return dict(delta=delta,before=before,after=after,build=new_build,old_build=old_build,build_pin=new_pin,old_pin=old_pin)


def validate(value):
    return subject().validate_chain_policy_delta(value['delta'],value['build'],value['build_pin'],
        value['old_build'],value['old_pin'],value['after']['standard'],value['before']['standard'],'b'*40,'a'*40)


def test_new_explicit_delta_reads_exact_three_module_changes(materials):
    assert validate(materials) is None


@pytest.mark.parametrize('change',['schema','profile','commit','baseline','variant','count','manifest',
    'missing-semantic','extra-semantic','claimed-sha','partition','syntax'])
def test_new_delta_rejects_unknown_or_unreviewed_material(materials,change):
    m=materials;d=m['delta'];row=d['packages'][0]
    if change=='schema':d['schemaVersion']='unknown/v1'
    elif change=='profile':d['profile']='anything/v1'
    elif change=='commit':d['sourceCommit']='c'*40
    elif change=='baseline':d['predecessorBuildPin']=d['buildPin']
    elif change=='variant':d['packages'][1]['variant']='standard'
    elif change=='count':row['fileCount']=146
    elif change=='manifest':row['fileManifestSha256']='0'*64
    elif change=='missing-semantic':m['after']['standard'][MODULES[0]]=m['before']['standard'][MODULES[0]]
    elif change=='extra-semantic':m['after']['standard']['other/module_000.py']=b'UNREVIEWED = True\n'
    elif change=='claimed-sha':row['changedFileEvidence'][MODULES[0]]['newSha256']='0'*64
    elif change=='partition':row['unchangedFileSha256'].pop('other/module_000.py')
    else:m['after']['standard'][MODULES[0]]=b'def invalid(\n'
    with pytest.raises((ValueError,SyntaxError)):validate(m)


@pytest.mark.parametrize('variant',['standard','lightweight'])
def test_real_archive_content_and_compile_are_verified(materials,variant):
    row=next(row for row in materials['delta']['packages'] if row['variant']==variant)
    reader=subject().EvidenceReader(Path(row['packagePin']['path']).parent,activation.file_pin)
    assert subject().read_package(reader,row,variant)==materials['after'][variant]


@pytest.mark.parametrize('change',['tamper','duplicate','traversal','symlink','invalid-python'])
def test_real_archive_unsafe_or_wrong_bytes_are_rejected(materials,change):
    row=materials['delta']['packages'][0];path=Path(row['packagePin']['path'])
    if change=='tamper':path.write_bytes(path.read_bytes()+b'changed')
    else:
        files=deepcopy(materials['after']['standard'])
        if change=='invalid-python':files[MODULES[0]]=b'def invalid(\n'
        values=package(path,files);row.update(values)
        if change!='invalid-python':
            with tarfile.open(path,'r:gz') as original:
                entries=[(info,original.extractfile(info).read()) for info in original.getmembers()]
            with tarfile.open(path,'w:gz') as changed:
                for info,raw in entries:changed.addfile(info,io.BytesIO(raw))
                info=tarfile.TarInfo(MODULES[0] if change=='duplicate' else '../outside' if change=='traversal' else 'alias')
                if change=='symlink':info.type=tarfile.SYMTYPE;info.linkname=MODULES[0]
                changed.addfile(info,io.BytesIO(b''))
            row['packagePin']=activation.file_pin(path)
    with pytest.raises((ValueError,SyntaxError)):
        subject().read_package(subject().EvidenceReader(path.parent,activation.file_pin),row,'standard')


def test_planner_public_dispatch_accepts_new_delta_without_changing_legacy_constants(materials):
    m=materials
    planner.validate_delta(m['delta'],m['build'],m['build_pin'],m['old_build'],m['old_pin'],
        m['after']['standard'],m['before']['standard'],'b'*40,'a'*40)
    assert planner.APPROVED_SEMANTIC_FILES==('control/recovery_control_restore_catalogue.py',)


@pytest.fixture
def executed_run(tmp_path):
    """A real pytest process; only the tiny protocol test contents are synthetic."""
    runner=importlib.import_module('run_main_program_chain_policy_verification')
    source=tmp_path/'source';test=source/'scripts/tests/test_incremental_chain_policy_admission.py'
    test.parent.mkdir(parents=True)
    for member,path in zip(MODULES,('ops/recovery/repository_records.py','ops/recovery/repository_minimal.py',
                                  'backend/src/main/resources/recovery_control_incremental_plan.py')):
        dest=source/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text('VALUE = 1\n',encoding='utf-8')
    test.write_text('import importlib.util\nfrom pathlib import Path\n'
        'ROOT=Path(__file__).resolve().parents[2]\n'
        'for name,path in '+repr(dict(zip(('repository_records','repository_minimal','recovery_control_incremental_plan'),
        ('ops/recovery/repository_records.py','ops/recovery/repository_minimal.py',
         'backend/src/main/resources/recovery_control_incremental_plan.py'))))+'.items():\n'
        ' spec=importlib.util.spec_from_file_location(name,ROOT/path)\n'
        ' module=importlib.util.module_from_spec(spec)\n'
        ' import sys\n sys.modules[name]=module\n spec.loader.exec_module(module)\n'
        'def test_actual_process():\n assert 2+2==4\n',encoding='utf-8')
    original=tmp_path/'source.tgz'
    with tarfile.open(original,'w:gz') as output:
        for path in sorted(source.rglob('*.py')):output.add(path,arcname=path.relative_to(source).as_posix())
    input_pin=activation.file_pin(original)
    run=runner.run_suite(source_root=source,output=tmp_path/'evidence',suite_id='source-policy',mode='source',
        source_commit='b'*40,input_pin=input_pin,runner_path=Path(runner.__file__),timeout=30)
    return dict(run=run,root=source,original=input_pin,base=tmp_path,
        modules={n:(source/p).read_bytes() for n,p in zip(MODULES,subject().SOURCE_MODULE_PATHS.values())})


def validate_run(value):
    reader=subject().EvidenceReader(value['base'],activation.file_pin,roots=[Path(__file__).parent])
    subject().validate_run(reader,value['run'],source_commit='b'*40,input_pin=value['original'],
        module_files=value['modules'],source_root=value['root'],runner_pin=activation.file_pin(
            Path(importlib.import_module('run_main_program_chain_policy_verification').__file__)))
    return reader.finish()


def rewrite(path, value):
    path.write_bytes(canonical(value));return activation.file_pin(path)


def test_actual_pytest_originals_are_accepted(executed_run):
    assert len(validate_run(executed_run))>=8


def test_source_policy_records_only_the_modules_it_actually_exercises(executed_run):
    executed_run['run']['loadedModulePins'].pop('common/repository_minimal.py')
    assert len(validate_run(executed_run)) >= 8


@pytest.mark.parametrize('suite,mode,expected',[
    ('source-regression','source',False),
    ('actual-package-policy','standard',True),
    ('actual-package-policy','lightweight',False),
])
def test_original_root_identity_contract_runs_on_the_standard_payload(suite,mode,expected):
    filename='scripts/tests/test_repository_root_identity.py'
    assert (filename in subject().suite_files(suite,mode)) is expected
    assert filename in subject().REQUIRED_SOURCE_FILES


@pytest.mark.parametrize('missing', ['common/repository_records.py', 'control/recovery_control_incremental_plan.py'])
def test_source_policy_still_requires_both_exercised_modules(executed_run, missing):
    executed_run['run']['loadedModulePins'].pop(missing)
    with pytest.raises(ValueError):
        validate_run(executed_run)


def test_source_snapshot_includes_the_real_spug_http_adapter(committed_source):
    root,revision,_ = committed_source
    path = root/'ops/spug/smallapp_adapter.py'
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b'# actual source-regression dependency\n')
        subprocess.check_call(['git','-C',str(root),'add',str(path)])
        subprocess.check_call(['git','-C',str(root),'-c','user.name=Protocol Fixture',
            '-c','user.email=protocol@example.invalid','commit','-qm','include runtime dependency'])
        revision=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD']).decode().strip()
    assert subject().committed_files(root,revision)['ops/spug/smallapp_adapter.py'] == path.read_bytes()


@pytest.mark.parametrize('change',['nonzero','timeout','skip','empty','missing-node','bad-junit','wrong-module',
    'foreign-module','wrong-input','filtered-command','input-drift','log-drift','wrong-suite'])
def test_actual_pytest_evidence_rejects_incomplete_or_unbound_claim(executed_run,change):
    value=executed_run;run=value['run']
    field='exitReceiptPin' if change in ('nonzero','timeout','input-drift') else 'resultPin'
    if change in ('wrong-module','foreign-module'):
        run['loadedModulePins'][MODULES[0]]['sha256' if change=='wrong-module' else 'path']='0'*64 if change=='wrong-module' else str(value['base']/'outside.py')
    elif change=='wrong-input':run['inputPin']['sha256']='0'*64
    elif change=='wrong-suite':run['suiteId']='any-tests'
    elif change=='log-drift':Path(run['stdoutPin']['path']).write_bytes(b'forged output')
    else:
        if change=='filtered-command':field='commandPin'
        path=Path(run[field]['path']);doc=json.loads(path.read_bytes())
        if change=='nonzero':doc['exitCode']=1
        elif change=='timeout':doc['timedOut']=True
        elif change=='input-drift':doc['inputPinsAfter'][0]['sha256']='0'*64
        elif change=='skip':doc['skipped']=1
        elif change=='empty':doc['tests']=0
        elif change=='missing-node':doc['nodeResults']=[]
        elif change=='bad-junit':doc['junitPin']['sha256']='0'*64
        elif change=='filtered-command':doc['argv']+=['-k','actual']
        run[field]=rewrite(path,doc)
    with pytest.raises(ValueError):validate_run(value)


def test_real_nonzero_pytest_is_preserved_as_failure(tmp_path):
    runner=importlib.import_module('run_main_program_chain_policy_verification')
    source=tmp_path/'source';path=source/'scripts/tests/test_incremental_chain_policy_admission.py'
    path.parent.mkdir(parents=True);path.write_text('def test_failure():\n assert False\n',encoding='utf-8')
    input_path=tmp_path/'source.tgz'
    with tarfile.open(input_path,'w:gz') as archive:archive.add(path,arcname=path.relative_to(source).as_posix())
    run=runner.run_suite(source_root=source,output=tmp_path/'evidence',suite_id='source-policy',mode='source',
        source_commit='b'*40,input_pin=activation.file_pin(input_path),runner_path=Path(runner.__file__),timeout=30)
    terminal=json.loads(Path(run['exitReceiptPin']['path']).read_bytes())
    result=json.loads(Path(run['resultPin']['path']).read_bytes())
    assert terminal['exitCode']==1 and terminal['timedOut'] is False
    assert result['failures']==1 and result['tests']==1


@pytest.fixture
def committed_source(tmp_path):
    """A real local Git commit with protocol contents, no product build."""
    root=tmp_path/'checkout';root.mkdir()
    runner=importlib.import_module('run_main_program_chain_policy_verification')
    for name in subject().REQUIRED_SOURCE_FILES:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b'# committed protocol input\n' if name.endswith('.py') else b'{}\n')
    def git(*args):
        return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE).decode().strip()
    git('init','-q');git('config','core.autocrlf','false');git('add','.')
    git('-c','user.name=Protocol Fixture','-c','user.email=protocol@example.invalid','commit','-qm','real protocol commit')
    return root,git('rev-parse','HEAD'),runner


def test_real_committed_snapshot_roundtrip_and_ignored_files_excluded(committed_source,tmp_path):
    root,revision,runner=committed_source
    (root/'.git/info/exclude').write_text('ignored.tmp\n',encoding='utf-8')
    (root/'ignored.tmp').write_bytes(b'not committed, must not enter the snapshot')
    build=local('build.json',{'targetCommit':revision})
    snapshot=runner.capture_snapshot(root,tmp_path/'snapshot',revision,build)
    reader=subject().EvidenceReader(tmp_path,activation.file_pin)
    files=subject().validate_source_snapshot(reader,snapshot,source_commit=revision,build_pin=build,root=root)
    assert set(files)==set(subject().REQUIRED_SOURCE_FILES)
    assert 'ignored.tmp' not in files


@pytest.mark.parametrize('change',['tracked-dirty','untracked','wrong-commit','missing-required','raw-checkout-drift'])
def test_snapshot_refuses_uncommitted_or_incomplete_source(committed_source,tmp_path,change):
    root,revision,runner=committed_source
    if change=='tracked-dirty':(root/subject().REQUIRED_SOURCE_FILES[0]).write_bytes(b'changed')
    elif change=='untracked':(root/'extra.tmp').write_bytes(b'unknown')
    elif change=='wrong-commit':revision='f'*40
    elif change=='missing-required':(root/subject().REQUIRED_SOURCE_FILES[0]).unlink()
    else:
        # Git may regard CRLF as clean, but source evidence still requires original committed bytes.
        subprocess.check_call(['git','-C',str(root),'config','core.autocrlf','true'])
        path=root/subject().REQUIRED_SOURCE_FILES[0];path.write_bytes(path.read_bytes().replace(b'\n',b'\r\n'))
    with pytest.raises(ValueError):runner.capture_snapshot(root,tmp_path/'snapshot',revision,local('build.json',{}))


def baseline_fixture(tmp_path,old_build=None,package_rows=None):
    def save(name,value):
        path=tmp_path/name;path.write_bytes(canonical(value));return local(name,value)
    old_build={'targetCommit':'a'*40} if old_build is None else old_build;build_pin=save('old-build.json',old_build)
    prior_delta=save('old-delta.json',dict(schemaVersion='ArchiveCataloguePackageDelta/v2',packages=[
        dict(variant=r['variant'],path=r['predecessor']['packagePin']['path'],packageSha256=r['predecessor']['packagePin']['sha256'],
        fileCount=r['predecessor']['fileCount'],fileManifestSha256=r['predecessor']['fileManifestSha256']) for r in package_rows or []]))
    old_coverage=save('old-coverage.json',dict(schemaVersion='MainProgramControlCoverage/v1',status='PASS',
        candidateBuildPin=build_pin,actualPackageEvidencePins=[prior_delta]))
    prior=local('prior-generation.json',{})
    evidence={};physical=[]
    for host,roles in {'57':['source','target'],'58':['target'],'59':['target']}.items():
        evidence[host]=[]
        for role in roles:
            inp=save('inputs-'+host+'-'+role+'.json',dict(sourceCommit='a'*40,buildPin=build_pin,
                previousControlGenerationPin=prior,coveragePin=old_coverage,revisionId='r5',suffix=host,role=role))
            rich=dict(sourceCommit='a'*40,previousControlGenerationPin=prior,coveragePin=old_coverage,
                activationInputsPin=inp,revisionId='r5')
            rich_pin=save('rich-'+host+'-'+role+'.json',rich)
            evidence[host].append(dict(path=str(tmp_path/rich_pin['file']),bytes=rich_pin['bytes'],sha256=rich_pin['sha256']))
            physical.extend([activation.file_pin(tmp_path/rich_pin['file']),activation.file_pin(tmp_path/inp['file'])])
    generation=dict(sourceCommit='a'*40,buildPin=build_pin,predecessor=dict(kind='CONTROL_GENERATION',generationPin=prior),
        activationEvidenceByHost=evidence)
    gen_pin=save('old-generation.json',generation)
    pred=dict(generationPin=gen_pin,generation=generation,build=old_build,inputPins=physical,
        plan=dict(revisionId='r5'))
    coverage=dict(baselineGenerationPin=gen_pin,baselineBuildPin=build_pin,
        baselineCoverageKind='CONTROL_GENERATION_COVERAGE',baselineCoveragePin=old_coverage)
    return coverage,pred


def test_predecessor_generation_binds_all_four_actual_rich_originals(tmp_path):
    coverage,pred=baseline_fixture(tmp_path)
    subject().validate_baseline(subject().EvidenceReader(tmp_path,activation.file_pin),coverage,pred,
        lambda *_:pytest.fail('must not fall back to initial coverage'))


@pytest.mark.parametrize('change',['kind','coverage','generation','missing-rich','not-owned','rich-coverage','input-build','revision'])
def test_baseline_never_substitutes_older_or_unowned_coverage(tmp_path,change):
    coverage,pred=baseline_fixture(tmp_path)
    if change=='kind':coverage['baselineCoverageKind']='INITIAL_FULL_COVERAGE'
    elif change=='coverage':coverage['baselineCoveragePin']=local('unrelated.json',{})
    elif change=='generation':coverage['baselineGenerationPin']=local('unrelated.json',{})
    elif change=='missing-rich':pred['generation']['activationEvidenceByHost']['57'].pop()
    elif change=='not-owned':pred['inputPins']=[]
    else:
        ref=pred['generation']['activationEvidenceByHost']['59'][0]
        path=Path(ref['path']);rich=json.loads(path.read_bytes())
        if change=='rich-coverage':rich['coveragePin']=local('different.json',{})
        elif change=='revision':rich['revisionId']='r99'
        else:
            inputs=tmp_path/rich['activationInputsPin']['file'];doc=json.loads(inputs.read_bytes())
            doc['buildPin']=local('wrong.json',{});inputs.write_bytes(canonical(doc))
            rich['activationInputsPin']=local(inputs.name,doc)
        path.write_bytes(canonical(rich));pred['generation']['activationEvidenceByHost']['59'][0]=activation.file_pin(path)
        pred['inputPins'].append(activation.file_pin(path))
    with pytest.raises(ValueError):subject().validate_baseline(subject().EvidenceReader(tmp_path,activation.file_pin),
        coverage,pred,lambda *_:pytest.fail('no baseline downgrade'))


def test_real_run_records_all_actual_inputs_with_explicit_execution_scope(executed_run):
    run=executed_run['run'];scope=run['executionInputRoot']
    assert scope==dict(schemaVersion='MainProgramExecutionInputRoot/v1',sourceRoot=str(executed_run['root']),
        moduleRoot=str(executed_run['root']),sourceInputPin=executed_run['original'],moduleInputPin=executed_run['original'])
    terminal=json.loads(Path(run['exitReceiptPin']['path']).read_bytes())
    with tarfile.open(executed_run['original']['path']) as archive:
        files={m.name:archive.extractfile(m).read() for m in archive.getmembers()}
    expected={n:dict(bytes=len(raw),sha256=digest(raw)) for n,raw in files.items()}
    assert terminal['runtimeInputPinsBefore']==terminal['runtimeInputPinsAfter']==dict(source=expected,program=expected)


@pytest.mark.parametrize('change',['unknown-schema','source-pin','module-pin','parent-escape','runtime-drift','missing-member'])
def test_execution_scope_cannot_escape_or_replace_originals(executed_run,change):
    run=executed_run['run'];scope=run['executionInputRoot']
    if change=='unknown-schema':scope['schemaVersion']='unknown/v1'
    elif change=='source-pin':scope['sourceInputPin']={**scope['sourceInputPin'],'sha256':'0'*64}
    elif change=='module-pin':scope['moduleInputPin']={**scope['moduleInputPin'],'sha256':'0'*64}
    elif change=='parent-escape':scope['moduleRoot']=scope['moduleRoot']+'/../alias'
    else:
        path=Path(run['exitReceiptPin']['path']);terminal=json.loads(path.read_bytes())
        table=terminal['runtimeInputPinsAfter']['source']
        if change=='runtime-drift':next(iter(table.values()))['sha256']='0'*64
        else:table.pop(next(iter(table)))
        run['exitReceiptPin']=rewrite(path,terminal)
    with pytest.raises(ValueError):validate_run(executed_run)


@pytest.mark.parametrize('path',['/runtime/source/../other','/runtime\\source','relative/path','/runtime//source'])
def test_linux_runtime_path_is_not_reinterpreted_by_windows(path):
    with pytest.raises(ValueError):subject().runtime_path(path)


def test_linux_runtime_path_is_lexical_and_needs_no_live_container():
    assert str(subject().runtime_path('/runtime/readonly-source'))=='/runtime/readonly-source'


@pytest.fixture
def complete_evidence(materials,tmp_path):
    """Four genuine subprocess suites over tiny committed protocol inputs.

    This exercises evidence closure, not product correctness or an installation.
    """
    from main_program_installation_selection import Records
    runner=importlib.import_module('run_main_program_chain_policy_verification');root=tmp_path/'release';root.mkdir()
    for name in subject().REQUIRED_SOURCE_FILES:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(b'# protocol\n' if name.endswith('.py') else b'{}\n')
    for filename in ('run_main_program_chain_policy_verification.py','main_program_chain_policy_evidence.py'):
        (root/subject().TASK_RELATIVE/filename).write_bytes((Path(__file__).parent/filename).read_bytes())
    for name in subject().SOURCE_MODULE_PATHS.values():(root/name).write_bytes(b'VALUE = 2\n')
    loader=('import importlib.util, os, sys\nfrom pathlib import Path\n'
        'ROOT=Path(os.environ["CHAIN_POLICY_RUN_COMMAND"]).parent/"package" if os.environ["CHAIN_POLICY_VARIANT"]!="source" else Path.cwd()\n'
        'MAP='+repr(subject().SOURCE_MODULE_PATHS)+'\n'
        'for member,source in MAP.items():\n'
        ' path=ROOT/(source if os.environ["CHAIN_POLICY_VARIANT"]=="source" else member)\n'
        ' name=Path(member).stem\n spec=importlib.util.spec_from_file_location(name,path)\n'
        ' module=importlib.util.module_from_spec(spec)\n sys.modules[name]=module\n spec.loader.exec_module(module)\n'
        'def test_protocol_inputs():\n assert module.VALUE==2\n')
    for name in {n for files in subject().SUITES.values() for n in files}:(root/name).write_text(loader,encoding='utf-8')
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE).decode().strip()
    git('init','-q');git('config','core.autocrlf','false');git('add','.')
    git('-c','user.name=Protocol Fixture','-c','user.email=protocol@example.invalid','commit','-qm','evidence protocol inputs')
    revision=git('rev-parse','HEAD');m=materials
    m['build'].update(targetCommit=revision,worktree=str(root));m['build_pin']=local('build.json',m['build'])
    (tmp_path/'build.json').write_bytes(canonical(m['build']))
    baseline,pred=baseline_fixture(tmp_path,m['old_build'],m['delta']['packages'])
    snapshot=runner.capture_snapshot(root,tmp_path/'snapshot',revision,m['build_pin'])
    (tmp_path/'snapshot.json').write_bytes(canonical(snapshot));snapshot_pin=local('snapshot.json',snapshot)
    m['delta'].update(sourceCommit=revision,buildPin=m['build_pin'],predecessorBuildPin=pred['generation']['buildPin'],
        predecessorGenerationPin=pred['generationPin'],sourceSnapshotPin=snapshot_pin)
    (tmp_path/'delta.json').write_bytes(canonical(m['delta']));delta_pin=local('delta.json',m['delta'])
    runs=[]
    for suite,mode in [('source-policy','source'),('source-regression','source'),('actual-package-policy','standard'),('actual-package-policy','lightweight')]:
        input_pin=snapshot['archivePin'] if mode=='source' else next(r['packagePin'] for r in m['delta']['packages'] if r['variant']==mode)
        runs.append(runner.run_suite(source_root=root,output=tmp_path/(suite+'-'+mode),suite_id=suite,mode=mode,
            source_commit=revision,input_pin=input_pin,source_input_pin=snapshot['archivePin'],
            runner_path=root/subject().TASK_RELATIVE/'run_main_program_chain_policy_verification.py',timeout=30))
    report=dict(schemaVersion='MainProgramChainPolicyVerification/v1',status='PASS',profile=PROFILE,sourceCommit=revision,
        buildPin=m['build_pin'],packageDeltaPin=delta_pin,sourceSnapshotPin=snapshot_pin,
        runnerPin=activation.file_pin(root/subject().TASK_RELATIVE/'run_main_program_chain_policy_verification.py'),runs=runs,failedAttemptPins=[],
        evidenceRootMapping=dict(runtimeRoot=str(tmp_path),persistentRoot=str(tmp_path)))
    (tmp_path/'verification.json').write_bytes(canonical(report));report_pin=local('verification.json',report)
    coverage=dict(schemaVersion='MainProgramControlCoverage/v2',status='PASS',profile=PROFILE,sourceCommit=revision,
        **baseline,candidateBuildPin=m['build_pin'],packagePartitions={r['variant']:{k:r[k] for k in ('changedFileEvidence','unchangedFileSha256')}
        for r in m['delta']['packages']},deltaTestEvidencePins=[report_pin],actualPackageEvidencePins=[delta_pin,report_pin],failedEvidencePins=[])
    (tmp_path/'coverage.json').write_bytes(canonical(coverage));coverage_pin=local('coverage.json',coverage)
    return dict(task=tmp_path,records=Records(tmp_path),inputs=dict(sourceCommit=revision,buildPin=m['build_pin'],coveragePin=coverage_pin),
        predecessor=pred,coverage=coverage,report=report,materials=m)


def test_full_coverage_dispatch_verifies_originals_and_preserves_return_shape(complete_evidence):
    v=complete_evidence
    proof=activation.validate_generation_coverage(v['records'],v['inputs'],v['predecessor'])
    assert set(proof)=={'coverage','build','delta','packageFiles','previousPackageFiles','physicalPins'}
    assert proof['packageFiles']==v['materials']['after']['standard']
    assert proof['coverage']['failedEvidencePins']==[]
    assert len(proof['physicalPins'])>40


@pytest.mark.parametrize('change',['profile','partition','wrong-report','failed-report','missing-suite','test-input-commit'])
def test_full_coverage_refuses_unreviewed_or_incomplete_proof(complete_evidence,change):
    v=complete_evidence;c=v['coverage'];report=v['report']
    if change=='profile':c['profile']='unreviewed/v1'
    elif change=='partition':c['packagePartitions']['lightweight']['unchangedFileSha256'].pop('other/module_000.py')
    elif change=='wrong-report':c['deltaTestEvidencePins']=[local('missing.json',{})]
    else:
        if change=='failed-report':report['status']='FAIL'
        elif change=='missing-suite':report['runs'].pop()
        else:report['sourceCommit']='d'*40
        (v['task']/'verification-new.json').write_bytes(canonical(report));ref=local('verification-new.json',report)
        c['deltaTestEvidencePins']=[ref];c['actualPackageEvidencePins'][1]=ref
    (v['task']/'coverage-new.json').write_bytes(canonical(c));v['inputs']['coveragePin']=local('coverage-new.json',c)
    with pytest.raises(ValueError):activation.validate_generation_coverage(v['records'],v['inputs'],v['predecessor'])


def test_required_source_names_match_real_repository_contract():
    root=Path(__file__).resolve().parents[3]
    assert all((root/name).is_file() for name in subject().REQUIRED_SOURCE_FILES)


def test_actual_package_carrier_never_builds_a_replacement_package():
    import ast
    path=Path(__file__).with_name('test_main_program_chain_policy_actual_packages.py')
    tree=ast.parse(path.read_bytes())
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='build' for n in ast.walk(tree))
    assert 'test_actual_packaged_constructor_and_publish_stop_before_capture' in path.read_text(encoding='utf-8')
    assert 'recovery_control_incremental_plan' in path.read_text(encoding='utf-8')


def test_explicit_evidence_mapping_keeps_original_pin_and_returns_host_pin(tmp_path):
    path=tmp_path/'original.log';path.write_bytes(b'original non-JSON output\n')
    host=activation.file_pin(path);original={**host,'path':'/evidence/original.log'}
    reader=subject().EvidenceReader(tmp_path,activation.file_pin)
    reader.bind_mapping(dict(runtimeRoot='/evidence',persistentRoot=str(tmp_path)))
    assert reader.raw(original)==path.read_bytes()
    assert reader.finish()==[host]
    assert original['path']=='/evidence/original.log'


@pytest.mark.parametrize('change',['outside-persistent','relative-runtime','parent-member','outside-member','rebind'])
def test_evidence_mapping_rejects_ambiguous_or_unowned_scope(tmp_path,change):
    reader=subject().EvidenceReader(tmp_path,activation.file_pin)
    mapping=dict(runtimeRoot='/evidence',persistentRoot=str(tmp_path))
    if change=='outside-persistent':mapping['persistentRoot']=str(tmp_path.parent)
    elif change=='relative-runtime':mapping['runtimeRoot']='evidence'
    with pytest.raises(ValueError):
        reader.bind_mapping(mapping)
        if change=='rebind':reader.bind_mapping(dict(runtimeRoot='/different',persistentRoot=str(tmp_path)))
        else:reader.raw(dict(path='/evidence/../bad' if change=='parent-member' else '/outside/file',bytes=1,sha256='0'*64))


def test_committed_runner_executes_the_complete_explicit_profile(complete_evidence):
    v=complete_evidence;m=v['materials'];root=Path(m['build']['worktree'])
    snapshot=json.loads((v['task']/'snapshot.json').read_bytes())
    request=dict(buildPin=m['build_pin'],packageDeltaPin=local('delta.json',m['delta']),packageDelta=m['delta'],
        sourceSnapshotPin=m['delta']['sourceSnapshotPin'],sourceSnapshot=snapshot,
        evidenceRootMapping=dict(runtimeRoot=str(v['task']),persistentRoot=str(v['task'])))
    path=v['task']/'verification-inputs.json';path.write_bytes(canonical(request))
    process=subprocess.run([sys.executable,'-B','-X','utf8',str(root/subject().TASK_RELATIVE/
        'run_main_program_chain_policy_verification.py'),'--source-root',str(root),'--output',str(v['task']/'full-runner'),
        '--source-commit',v['inputs']['sourceCommit'],'--inputs',str(path)],capture_output=True,timeout=90)
    assert process.returncode==0,process.stderr.decode()
    report=json.loads((v['task']/'full-runner/verification-report.json').read_bytes())
    assert report['status']=='PASS' and [(r['suiteId'],r['mode']) for r in report['runs']]==subject().REQUIRED_RUNS


@pytest.mark.parametrize('variant',['standard','lightweight'])
def test_real_prior_delta_forward_path_binds_same_native_package(variant):
    """Read original historical metadata and archive; never rewrite either."""
    task=Path(__file__).parent;path=task/'archive-catalogue-package-delta-r3.json'
    before=activation.file_pin(path);delta=json.loads(path.read_bytes())
    row=next(r for r in delta['packages'] if r['variant']==variant)
    assert row['path'].startswith('C:/') and '\\' not in row['path']
    archive=Path(row['path']);native=activation.file_pin(archive)
    assert native['sha256']==row['packageSha256']
    expected=dict(variant=variant,packagePin=native,fileCount=row['fileCount'],fileManifestSha256=row['fileManifestSha256'])
    reader=subject().EvidenceReader(task,activation.file_pin,roots=[archive.parent])
    subject().validate_predecessor_package(reader,row,expected,delta['schemaVersion'])
    assert activation.file_pin(path)==before
    assert reader.finish()==[native]


@pytest.mark.parametrize('name',['C:/evidence/original.log',r'C:\evidence\original.log'])
def test_windows_canonical_separator_forms_read_same_real_original(tmp_path,name):
    path=tmp_path/'original.log';path.write_bytes(b'original bytes')
    reader=subject().EvidenceReader(tmp_path,activation.file_pin)
    reader.bind_mapping(dict(runtimeRoot=r'C:\evidence',persistentRoot=str(tmp_path)))
    expected={**activation.file_pin(path),'path':name}
    assert reader.raw(expected)==b'original bytes'
    assert reader.finish()==[activation.file_pin(path)]


@pytest.mark.parametrize('name',[r'C:/evidence\original.log',r'C:\evidence/original.log',
    'C:/evidence/../original.log',r'C:\evidence\..\original.log','C:/evidence//original.log',
    r'C:\evidence\.\original.log',r'\\server\share\original.log','//server/share/original.log',
    r'\\?\C:\evidence\original.log','C:/evidence/original.log:stream','C:/evidence/CON',
    'C:/evidence/NUL.txt','C:/evidence/name.','C:/evidence/name ','C:relative/file',
    '/evidence\\original.log','/evidence/../original.log'])
def test_windows_physical_aliases_and_posix_escapes_remain_forbidden(name):
    with pytest.raises(ValueError):subject().runtime_path(name)


@pytest.mark.parametrize('change',['path','bytes','sha'])
def test_equivalent_path_never_replaces_actual_byte_and_digest_binding(tmp_path,change):
    path=tmp_path/'original.tgz';path.write_bytes(b'actual pinned archive bytes')
    current=activation.file_pin(path)
    old=dict(variant='standard',packagePin={**current,'path':'C:/evidence/original.tgz'},fileCount=147,
        fileManifestSha256='a'*64)
    expected={**old,'packagePin':{**current,'path':r'C:\evidence\original.tgz'}}
    if change=='path':expected['packagePin']['path']=r'C:\evidence\different.tgz'
    elif change=='bytes':expected['packagePin']['bytes']+=1
    else:expected['packagePin']['sha256']='0'*64
    reader=subject().EvidenceReader(tmp_path,activation.file_pin)
    reader.bind_mapping(dict(runtimeRoot=r'C:\evidence',persistentRoot=str(tmp_path)))
    with pytest.raises(ValueError):subject().validate_predecessor_package(reader,old,expected,subject().DELTA_SCHEMA)
