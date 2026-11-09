"""Local v4 protocol contracts; temporary documents are not installation evidence."""
from copy import deepcopy
import hashlib
from pathlib import Path
import json
from pathlib import PurePosixPath
from types import SimpleNamespace

import pytest

import main_program_control_activation as subject
from test_main_program_control_activation import fixture as original_staging
import test_main_program_control_activation as original_tests
from test_main_program_control_environment import documents, environment
from test_installation_history_custody_layered import receipts
from test_main_program_control_upgrade_plan import originals


def local(name):
    return dict(file=name, bytes=1, sha256='a' * 64)


def inputs(suffix='59', role='target'):
    short, revision = 'a' * 7, 'r5'
    return dict(schemaVersion='MainProgramControlActivationInputs/v4', sourceCommit='a' * 40,
        suffix=suffix, role=role, revisionId=revision,
        buildPin=local('release-build-' + short + '.json'),
        planPin=local('main-program-configuration-plan-' + short + '-' + revision + '.json'),
        previousControlGenerationPin=local('control-generation-' + 'b' * 7 + '.json'),
        engineStagedPin=local('main-program-engine-staged-' + suffix + '-' + short + '-' + revision + '.json'),
        configurationStagedPin=local('main-program-configuration-staged-' + suffix + '-' + short + '-' + revision + '.json'),
        unitObservationPin=local('main-program-control-units-' + suffix + '-' + short + '-' + revision + '.json'),
        originalEnvironmentObservationPin=local('main-program-control-environment-baseline-' + suffix + '-' + short + '-' + revision + '.json'),
        precedingActivationPins=[local('prior-' + h + '-' + r + '.json') for h, r in subject.predecessors(suffix, role)],
        sourceBaselinePin=local('automatic-i2-audit.json'), coveragePin=local('main-program-control-coverage-' + short + '-' + revision + '.json'),
        outputFile='main-program-control-activation-' + suffix + '-' + role + '-' + short + '-' + revision + '.json')


@pytest.mark.parametrize('suffix,role', subject.ORDER)
def test_v4_explicit_inputs_accept_all_four_roles_without_automatic_selection(suffix, role):
    value = inputs(suffix, role)
    assert subject.validate_generation_inputs(value) == subject.predecessors(suffix, role)
    assert 'previousAutomaticSelectionPin' not in value


@pytest.mark.parametrize('change', ['coverage-missing', 'legacy-predecessor', 'continuation', 'revision',
    'old-plan', 'old-stage', 'old-unit', 'old-environment', 'old-output', 'wrong-host', 'wrong-order', 'bad-pin'])
def test_v4_rejects_missing_or_mixed_generations_before_dispatch(tmp_path, change):
    value = inputs()
    if change == 'coverage-missing': del value['coveragePin']
    elif change == 'legacy-predecessor': value['previousAutomaticSelectionPin'] = local('automatic-current-installations.json')
    elif change == 'continuation': value['preSwitchContinuationPin'] = local('old-failure.json')
    elif change == 'revision': value['revisionId'] = 'latest'
    elif change == 'old-plan': value['planPin'] = local('main-program-configuration-plan-r4.json')
    elif change == 'old-stage': value['engineStagedPin'] = local('main-program-engine-staged-59-r4.json')
    elif change == 'old-unit': value['unitObservationPin'] = local('main-program-control-units-59-r1.json')
    elif change == 'old-environment': value['originalEnvironmentObservationPin'] = local('main-program-control-environment-baseline-59-r2.json')
    elif change == 'old-output': value['outputFile'] = 'main-program-control-activation-59-target-aaaaaaa.json'
    elif change == 'wrong-host': value['suffix'] = '58'
    elif change == 'wrong-order': value['precedingActivationPins'] = [local('unrelated.json')]
    else: value['coveragePin']['sha256'] = 'wrong'
    name = 'inputs.json'; (tmp_path / name).write_bytes(subject.canonical(value))
    calls = []
    with pytest.raises(ValueError, match='MAIN_ACTIVATION_'):
        subject.validate_generation_inputs(value)
    with pytest.raises(ValueError, match='MAIN_ACTIVATION_'):
        subject.run_request(tmp_path, tmp_path, name, activate=True, transport=lambda *a, **k: calls.append(a))
    assert calls == []
    assert list(tmp_path.iterdir()) == [tmp_path / name]


def staging():
    value = inputs(); plan, build, engine, configuration = original_staging()
    refs = configuration['configurationStaging']['documents']
    binding = {k: value[k] for k in ('revisionId', 'previousControlGenerationPin', 'buildPin', 'planPin')}
    plan.update(schemaVersion='MainProgramConfigurationPlan/v2', revisionId=value['revisionId'],
        predecessorGenerationPin=value['previousControlGenerationPin'], buildPin=value['buildPin'],
        newDocumentsByHost={'59': refs[:2]}, retainedDocumentsByHost={'59': refs[2:]})
    for report in (engine, configuration): report.update(binding)
    configuration['configurationStaging'].update(newDocuments=refs[:2], retainedDocuments=refs[2:],
        retainedDocumentsVerifiedUnchanged=True, newDocumentsCreatedExclusively=True)
    return value, plan, build, engine, configuration


def test_v4_staging_requires_explicit_new_and_retained_document_sets():
    value, plan, build, engine, configuration = staging()
    assert subject.validate_generation_staging(value, plan, build, engine, configuration) is None


@pytest.mark.parametrize('change', ['revision', 'generation', 'build', 'plan', 'retained-rewritten',
    'not-exclusive', 'overlap', 'omitted', 'reordered', 'original-admission', 'original-preservation'])
def test_v4_staging_rejects_wrong_generation_or_unproven_retention(change):
    value, plan, build, engine, configuration = staging(); stage = configuration['configurationStaging']
    if change == 'revision': engine['revisionId'] = 'r4'
    elif change == 'generation': configuration['previousControlGenerationPin'] = local('different.json')
    elif change == 'build': engine['buildPin'] = local('different.json')
    elif change == 'plan': configuration['planPin'] = local('different.json')
    elif change == 'retained-rewritten': stage['retainedDocumentsVerifiedUnchanged'] = False
    elif change == 'not-exclusive': stage['newDocumentsCreatedExclusively'] = False
    elif change == 'overlap': stage['newDocuments'].append(stage['retainedDocuments'][0])
    elif change == 'omitted': stage['retainedDocuments'].pop()
    elif change == 'reordered': stage['retainedDocuments'].reverse()
    elif change == 'original-admission': stage['candidates'][0]['sourceArchiveProtections'][0]['actualFactoryPreflightPassed'] = False
    else: engine['businessContainersUnchanged'] = False
    with pytest.raises(ValueError, match='MAIN_ACTIVATION_'):
        subject.validate_generation_staging(value, plan, build, engine, configuration)


def revise_environment(h):
    value = inputs()
    name = value['unitObservationPin']['file']
    value['unitObservationPin'] = h.local(name, h.unit)
    extra = dict(revisionId=value['revisionId'], previousControlGenerationPin=value['previousControlGenerationPin'])
    h.baseline.update(extra, unitObservationPin=value['unitObservationPin'])
    h.private_baseline.update(extra, unitObservationPin=value['unitObservationPin'])
    stem = value['originalEnvironmentObservationPin']['file'][:-5]
    h.baseline['privateSnapshotPin'] = h.secret(stem + '.private.json', h.private_baseline)
    value['originalEnvironmentObservationPin'] = h.local(stem + '.json', h.baseline)
    return value


def test_v4_environment_reads_real_pinned_public_private_originals(documents):
    h = documents; value = revise_environment(h)
    before = {p: p.read_bytes() for root in (h.task, h.private) for p in root.iterdir()}
    proof = subject.validate_environment_baseline(subject.contract.Records(h.task), h.private, value,
        h.unit, h.original_controllers)
    assert proof['controllers'] == h.private_baseline['controllers']
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize('change', ['old-pid', 'wrong-generation', 'wrong-revision', 'private-drift', 'environment-drift'])
def test_v4_environment_rejects_unbound_or_changed_originals(documents, change):
    h = documents; value = revise_environment(h)
    if change == 'old-pid': h.original_controllers[0]['pid'] -= 1
    elif change == 'wrong-generation': h.baseline['previousControlGenerationPin'] = local('other.json')
    elif change == 'wrong-revision': h.baseline['revisionId'] = 'r4'
    elif change == 'private-drift': Path(h.baseline['privateSnapshotPin']['path']).write_bytes(b'{}')
    else: h.original_controllers[0]['argvSha256'] = 'e' * 64
    if change in ('wrong-generation', 'wrong-revision'):
        value['originalEnvironmentObservationPin'] = h.local(value['originalEnvironmentObservationPin']['file'], h.baseline)
    with pytest.raises(ValueError):
        subject.validate_environment_baseline(subject.contract.Records(h.task), h.private, value,
            h.unit, h.original_controllers)


def test_v4_missing_coverage_is_a_local_blocker_without_creating_attempt(tmp_path):
    value = inputs(); (tmp_path / 'inputs.json').write_bytes(subject.canonical(value)); calls = []
    with pytest.raises((ValueError, FileNotFoundError)):
        subject.run_request(tmp_path, tmp_path, 'inputs.json', activate=True, transport=lambda *a, **k: calls.append(a))
    assert calls == []
    assert [p.name for p in tmp_path.iterdir()] == ['inputs.json']


def test_v4_prepare_follows_only_the_explicit_missing_generation_without_dispatch(tmp_path):
    value = inputs(); (tmp_path / 'inputs.json').write_bytes(subject.canonical(value)); calls = []
    with pytest.raises(FileNotFoundError, match='control-generation-bbbbbbb'):
        subject.run_request(tmp_path, tmp_path, 'inputs.json', activate=True, transport=lambda *a, **k: calls.append(a))
    assert calls == []
    assert [p.name for p in tmp_path.iterdir()] == ['inputs.json']


@pytest.fixture
def coverage_documents(tmp_path):
    """Copy only explicitly referenced public originals, never rewrite originals."""
    task = Path(__file__).resolve().parent
    names = set()
    def copy_reference(ref):
        name = ref['file']
        if name in names: return
        names.add(name); raw = (task / name).read_bytes(); (tmp_path / name).write_bytes(raw)
        if not name.endswith('.json'): return
        def walk(value):
            if type(value) is dict:
                if set(value) == {'file', 'bytes', 'sha256'} and (task / value['file']).is_file(): copy_reference(value)
                else:
                    for item in value.values(): walk(item)
            elif type(value) is list:
                for item in value: walk(item)
        walk(json.loads(raw))
    name = 'main-program-control-coverage-45dd7dc-r1.json'; raw = (task / name).read_bytes()
    ref = dict(file=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()); copy_reference(ref)
    value = json.loads(raw)
    candidate = json.loads((tmp_path / value['candidateBuildPin']['file']).read_bytes())
    previous = json.loads((tmp_path / value['baselineBuildPin']['file']).read_bytes())
    envelope = dict(sourceCommit=candidate['targetCommit'], coveragePin=ref, buildPin=value['candidateBuildPin'])
    predecessor = dict(generation=dict(sourceCommit=previous['targetCommit'], buildPin=value['baselineBuildPin']), build=previous)
    return tmp_path, envelope, predecessor, value


def test_v4_real_coverage_reads_both_actual_packages_and_retains_failed_carrier(coverage_documents):
    task, value, predecessor, report = coverage_documents
    proof = subject.validate_generation_coverage(subject.contract.Records(task), value, predecessor)
    assert proof['coverage'] == report
    assert len(proof['packageFiles']) == len(proof['previousPackageFiles']) == 147
    assert proof['delta']['packages'][1]['variant'] == 'lightweight'
    assert report['failedEvidencePins']


@pytest.mark.parametrize('change', ['missing-linux', 'bad-coverage-pin', 'wrong-build', 'missing-difference',
    'wrong-unchanged', 'no-failure', 'unexpected-field', 'failed-linux', 'skipped-linux', 'wrong-package', 'raw-log-drift'])
def test_v4_coverage_rejects_incomplete_or_rebound_proof(coverage_documents, change):
    task, value, predecessor, report = coverage_documents
    def repin(name, document):
        raw = subject.canonical(document); (task / name).write_bytes(raw)
        return dict(file=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    if change == 'missing-linux': report['deltaTestEvidencePins'].pop()
    elif change == 'bad-coverage-pin': value['coveragePin']['sha256'] = 'a' * 64
    elif change == 'wrong-build': report['candidateBuildPin'] = report['baselineBuildPin']
    elif change == 'missing-difference': report['changedFiles'].pop(next(iter(report['changedFiles'])))
    elif change == 'wrong-unchanged': report['unchangedPackageFiles'][next(iter(report['unchangedPackageFiles']))] = 'a' * 64
    elif change == 'no-failure': report['failedEvidencePins'] = []
    elif change == 'unexpected-field': report['allOldTestsRerun'] = True
    else:
        ref = report['deltaTestEvidencePins'][1]; linux = json.loads((task / ref['file']).read_bytes())
        if change == 'failed-linux': linux['status'] = 'FAIL'
        elif change == 'skipped-linux': linux['results'][0]['skipped'] = 1
        elif change == 'wrong-package': linux['packagePins']['lightweight']['moduleSha256'] = 'a' * 64
        else: (task / linux['rawLogPin']['file']).write_bytes(b'changed')
        if change != 'raw-log-drift':
            newref = repin(ref['file'], linux)
            report['deltaTestEvidencePins'][1] = report['actualPackageEvidencePins'][1] = newref
    if change != 'bad-coverage-pin': value['coveragePin'] = repin(value['coveragePin']['file'], report)
    with pytest.raises((ValueError, FileNotFoundError)):
        subject.validate_generation_coverage(subject.contract.Records(task), value, predecessor)


def retained_remote(receipts):
    from test_main_program_control_environment import remote_functions
    import installation_history_custody
    scope = remote_functions(); custody = receipts['custody']
    class FilePath(PurePosixPath):
        def read_bytes(self): return receipts['files'][str(self)].read_bytes()
    def pin(path):
        raw = receipts['files'][str(path)].read_bytes()
        return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    scope.update(pathlib=SimpleNamespace(Path=FilePath, PurePosixPath=PurePosixPath), pin=pin,
        read=receipts['reader'], verify_layered_receipt_custody=lambda value:
            installation_history_custody.verify_layered_receipt_custody(value, read_pin=receipts['reader']),
        SPEC=dict(previousCustody=custody, targetConfigRef=custody['targetConfigRef'], oldReceiptPin=custody['selectedCurrentReceiptPin']),
        old=dict(service=custody['service'], ownerConfigurationPin=custody['selectedOwnerPin'], controlConfigurationPin=custody['selectedControlPin']),
        out={})
    return scope


def test_v4_remote_retention_uses_shared_complete_custody_and_all_original_packages(receipts):
    scope = retained_remote(receipts)
    scope['retained_custody']()
    actual = scope['out']['currentLayeredCustodyObservation']
    assert actual['status'] == 'PASS' and actual['activationCount'] == 3
    assert actual['selectedCurrentReceiptPin'] == receipts['custody']['selectedCurrentReceiptPin']
    assert len(scope['out']['custodyPackagePins']) == 3


def test_v4_remote_retention_rejects_a_changed_legacy_file(receipts):
    scope = retained_remote(receipts)
    ref = receipts['custody']['legacyCustody']['steps'][0]['ownerConfigurationPin']
    receipts['files'][ref['path']].write_bytes(b'changed')
    with pytest.raises(ValueError, match='RECEIPT_PIN_CHANGED'):
        scope['retained_custody']()


def test_v4_remote_final_custody_appends_only_the_actual_published_receipt(receipts):
    scope = retained_remote(receipts); custody = receipts['custody']; root = custody['root']
    previous = receipts['put'](root + '/configuration/target-installation-before-main-4444444.json', receipts['values'][-1])
    engine = root + '/engine-4'
    owner = receipts['reader'](custody['selectedOwnerPin']); owner['formalModuleDirectory'] = engine + '/formal'
    owner_pin = receipts['put'](root + '/configuration/owner-4.json', owner)
    control_pin = receipts['put'](root + '/configuration/control-4.json', dict(restoreConfigurations={custody['sourceConfigRef']: {
        custody['targetConfigRef']: owner_pin}}))
    dropin = receipts['put']('/etc/systemd/system/' + custody['service'] + '.d/4.conf', b'new fixture unit')
    package = receipts['put'](engine + '/package.json', dict(files={}, packageSha256=hashlib.sha256(b'{}').hexdigest()))
    receipt = dict(receipts['values'][-1], sourceCommit='4' * 40, engine=engine,
        ownerConfigurationPin=owner_pin, controlConfigurationPin=control_pin)
    current = receipts['put'](root + '/target-installation.json', receipt)
    scope.update(inputs=dict(sourceCommit='4' * 40), selected=dict(engine=engine, ownerPin=owner_pin, controlPin=control_pin))
    scope['out'].update(previousReceiptPin=previous, currentReceiptPin=current, dropinPin=dropin, packageJsonPin=package)
    scope['retained_custody']()
    proof = scope['out']['currentLayeredCustodyObservation']
    assert proof['activationCount'] == 4 and proof['selectedCurrentReceiptPin'] == current
    assert len(custody['mainSteps']) == 2
    assert custody['selectedCurrentReceiptPin'] != current


@pytest.mark.parametrize('field', ['activationInputsPin', 'coveragePin', 'previousControlGenerationPin', 'revisionId'])
def test_v4_core_requires_unchanged_explicit_input_and_coverage_echo(field):
    fixture = original_tests.CoreProjectionTests(); fixture.setUp()
    fixture.spec['inputs'].update(inputs()); fixture.spec['activationInputsPin'] = local('activation-inputs.json')
    fixture.observed.update(activationInputsPin=fixture.spec['activationInputsPin'],
        **{k: fixture.spec['inputs'][k] for k in ('coveragePin', 'previousControlGenerationPin', 'revisionId')})
    fixture.observed['currentLayeredCustodyObservation'] = dict(status='PASS',
        selectedCurrentReceiptPin=fixture.observed['currentReceiptPin'], originalInventoryVerified=True)
    assert subject.project_core(fixture.spec, fixture.observed)['schemaVersion'] == 'MainProgramControlActivation/v1'
    fixture.observed[field] = 'wrong' if field == 'revisionId' else local('wrong.json')
    with pytest.raises(ValueError, match='GENERATION_EVIDENCE_CHANGED'):
        subject.project_core(fixture.spec, fixture.observed)


@pytest.fixture
def prepared_protocol(coverage_documents, originals, monkeypatch):
    """Explicit generation/host observation protocol seam, never deployment proof.

    Actual two-generation tar bytes, coverage, planner and all prepared documents
    are read normally. The separately tested generation reader is the one seam.
    No service/backup/restore is executed or represented as having been executed.
    """
    import main_program_control_generation
    import main_program_control_upgrade_plan
    task, coverage_input, _, _ = coverage_documents; private = task / 'private'; private.mkdir()
    bundle = deepcopy(originals.kwargs['predecessor'])
    def save(root, name, value):
        raw = subject.canonical(value); (root / name).write_bytes(raw)
        return dict(file=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    def rpin(path, raw=b'fixture observation bytes'):
        return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    for host, selection in bundle['selections'].items():
        selection['localInstallationPins'] = []
        selection['baseAutomaticSelectionPin'] = local('automatic-current-installations.json')
        selection['controllers'] = [{k: row[k] for k in main_program_control_generation.SELECTION_CONTROLLER_KEYS}
            for row in bundle['controllersByHost'][host]]
    baseline_name = 'automatic-i2-audit.json'; baseline_raw = (subject.TASK / baseline_name).read_bytes()
    (task / baseline_name).write_bytes(baseline_raw)
    bundle['sourceBaseline'] = json.loads(baseline_raw)
    bundle['generation']['sourceBaselinePin'] = dict(file=baseline_name, bytes=len(baseline_raw), sha256=hashlib.sha256(baseline_raw).hexdigest())
    for host in ('58', '59'):
        inventory = json.loads((subject.TASK / ('protected-history-' + host + '.json')).read_bytes())
        save(task, 'protected-history-' + host + '.json', inventory)
        # The real layered recipe itself is covered through the original-files
        # reader tests above; this local prepare boundary only transfers it.
        bundle['custodyByHost'][host] = dict(schemaVersion='MainProgramReceiptCustody/v1', originalInventory=inventory,
            legacyCustody=dict(originalActiveReceiptPin=next(p for p in inventory['evidencePins']
                if p['path'] == bundle['selections'][host]['activeReceiptPin']['path'])),
            selectedCurrentReceiptPin=bundle['selections'][host]['activeReceiptPin'])
    def selected(actual_task, actual_private, ref):
        assert Path(actual_task) == task and Path(actual_private) == private and ref == bundle['generationPin']
        return deepcopy(bundle)
    monkeypatch.setattr(main_program_control_generation, 'load_control_generation', selected)
    kwargs = deepcopy(originals.kwargs)
    kwargs.update(predecessor=bundle, private_plan_path=str(private / 'main-program-configuration-plan-45dd7dc-r5.private.json'))
    planned = main_program_control_upgrade_plan.plan_control_upgrade(**kwargs)
    plan, secret = planned['plan'], planned['privatePlan']
    save(private, Path(kwargs['private_plan_path']).name, secret)
    plan_ref = save(task, 'main-program-configuration-plan-45dd7dc-r5.json', plan)
    for suffix, roles in subject.contract.ROLES.items():
        value = inputs(suffix, roles[-1]); value['sourceCommit'] = coverage_input['sourceCommit']
        value.update(buildPin=coverage_input['buildPin'], planPin=plan_ref, coveragePin=coverage_input['coveragePin'],
            previousControlGenerationPin=bundle['generationPin'], sourceBaselinePin=bundle['generation']['sourceBaselinePin'])
        short = value['sourceCommit'][:7]; revision = value['revisionId']
        for key, kind in [('engineStagedPin', 'engine-staged'), ('configurationStagedPin', 'configuration-staged'),
                          ('unitObservationPin', 'control-units'), ('originalEnvironmentObservationPin', 'control-environment-baseline')]:
            value[key] = local('main-program-' + kind + '-' + suffix + '-' + short + '-' + revision + '.json')
        binding = {k: value[k] for k in ('revisionId', 'previousControlGenerationPin', 'buildPin', 'planPin')}
        flags = dict(businessContainersUnchanged=True, configurationUnchanged=True,
            controlServicesReloaded=False, backupDispatched=False, restoreDispatched=False)
        old = bundle['selections'][suffix]['controllers']; observed = []
        for row in old:
            unitpin = rpin('/etc/systemd/system/' + row['service'])
            observed.append(dict(service=row['service'], pid=row['pid'], unitPin=unitpin,
                dropinPins=[row['dropinPin']], directory='/etc/systemd/system/' + row['service'] + '.d',
                existingNames=[PurePosixPath(row['dropinPin']['path']).name]))
        unit = dict(schemaVersion='MainControlUnitObservation/v1', status='PASS', host='172.30.30.' + suffix,
            sourceCommit=value['sourceCommit'], revisionId=revision, previousControlGenerationPin=bundle['generationPin'],
            historyGuardEnabledAndActive=True, originalWorkingDirectoriesHaveNoWorker=True, controllers=observed,
            requiredHistoryGuard='spug-history-prod57-readonly-' + suffix + '.service',
            **{k: False for k in subject.OBSERVATION_FALSE_FIELDS})
        unit_private = dict(unit, controllers=[dict(row, properties={}) for row in observed], historyGuardProperties={})
        private_unit_name = value['unitObservationPin']['file'].replace('.json', '.private.json')
        save(private, private_unit_name, unit_private); unit['privateSnapshotPin'] = subject.file_pin(private / private_unit_name)
        value['unitObservationPin'] = save(task, value['unitObservationPin']['file'], unit)
        environment_rows = []
        for row, observed_row in zip(old, observed):
            declaration = 'Environment=PYTHONPATH=/fixture/old PYTHONDONTWRITEBYTECODE=1\n'
            environment_rows.append(dict(**{k: row[k] for k in ('service', 'pid', 'engine', 'controlConfigurationPin', 'ownerConfigurationPin')},
                argvSha256='b' * 64, unitPin=observed_row['unitPin'], dropinPins=observed_row['dropinPins'],
                environmentSha256=hashlib.sha256(b'fixture inherited process environment').hexdigest(),
                systemdEnvironmentSha256=hashlib.sha256(declaration.encode()).hexdigest(),
                systemdEnvironmentRaw=declaration, declaredEnvironment=dict(PYTHONPATH='/fixture/old', PYTHONDONTWRITEBYTECODE='1')))
        env_private = dict(schemaVersion='MainControlEnvironmentBaseline/v1', status='PASS', host=unit['host'],
            observedAt='2026-11-09T15:00:00+00:00', unitObservationPin=value['unitObservationPin'],
            revisionId=revision, previousControlGenerationPin=bundle['generationPin'], controllers=environment_rows,
            **{k: False for k in subject.OBSERVATION_FALSE_FIELDS})
        env_name = value['originalEnvironmentObservationPin']['file']; save(private, env_name.replace('.json', '.private.json'), env_private)
        env_public = dict(env_private, controllers=[{k: v for k, v in row.items() if k not in subject.ENVIRONMENT_PRIVATE_FIELDS} for row in environment_rows],
            privateSnapshotPin=subject.file_pin(private / env_name.replace('.json', '.private.json')))
        value['originalEnvironmentObservationPin'] = save(task, env_name, env_public)
        engine = dict(status='STAGED_NOT_ACTIVATED', sourceCommit=value['sourceCommit'], host=unit['host'], **flags, **binding,
            engines=[dict(path=row['engine'], **{k: secret['build'][k] for k in ('fileCount', 'packageSha256', 'fileManifestSha256')},
                filesSha256Verified=True, pythonCompileVerified=True) for row in plan['controllers'][suffix]],
            controls=[dict(service=row['service'], pid=row['pid'], argvSha256='b' * 64) for row in old])
        value['engineStagedPin'] = save(task, value['engineStagedPin']['file'], engine)
        candidates = [dict(role=row['role'], controlPin=row['controlPin'], ownerPin=row['ownerPin'],
            actualConfigurationReadPassed=True, actualTargetOrCaptureBindingPassed=True,
            observedSourceRefs=[subject.SOURCES[0]] if row['role'] == 'source' else list(subject.SOURCES),
            sourceArchiveProtections=[dict(sourceConfigRef=source, actualFactoryPreflightPassed=True,
                mountCommandExecuted=False, journalWritten=False) for source in subject.SOURCES]) for row in plan['controllers'][suffix]]
        config = dict(status='STAGED_NOT_ACTIVATED', sourceCommit=value['sourceCommit'], host=unit['host'], **flags, **binding,
            existingPhysicalLockAcquiredAndReleased=True, configurationStaging=dict(status='STAGED_NOT_ACTIVATED',
            documents=[d['pin'] for d in secret['documentsByHost'][suffix]], candidates=candidates,
            registrySelectorsPublished=False, historyMaterialsChanged=False, newDocumentsCreatedExclusively=True,
            retainedDocumentsVerifiedUnchanged=True, newDocuments=plan['newDocumentsByHost'][suffix],
            retainedDocuments=plan['retainedDocumentsByHost'][suffix]))
        value['configurationStagedPin'] = save(task, value['configurationStagedPin']['file'], config)
        save(task, 'fixture-input-' + suffix + '.json', value)
    return task, private, bundle, plan_ref, save


@pytest.mark.parametrize('suffix,role', subject.ORDER)
def test_v4_complete_prepare_uses_actual_coverage_and_planner_with_local_protocol_observations(prepared_protocol, suffix, role):
    task, private, bundle, plan_ref, save = prepared_protocol
    value = json.loads((task / ('fixture-input-' + suffix + '.json')).read_bytes()); value['role'] = role
    value['outputFile'] = 'main-program-control-activation-' + suffix + '-' + role + '-45dd7dc-r5.json'
    plan = json.loads((task / plan_ref['file']).read_bytes()); value['precedingActivationPins'] = []
    for host, prior_role in subject.predecessors(suffix, role):
        core = deepcopy(next(row for row in bundle['controllersByHost'][host] if row['role'] == prior_role))
        planned = next(row for row in plan['controllers'][host] if row['role'] == prior_role)
        original_receipt = core.get('currentReceiptPin')
        core.update(sourceCommit=value['sourceCommit'], buildPin=value['buildPin'], planPin=plan_ref,
            pid=core['pid'] + 1000, engine=planned['engine'], controlConfigurationPin=planned['controlPin'],
            ownerConfigurationPin=planned['ownerPin'],
            **{key: json.loads((task / value['buildPin']['file']).read_bytes())[key]
                for key in ('fileCount', 'fileManifestSha256', 'packageSha256')},
            dropinPin=dict(path='/etc/systemd/system/' + core['service'] + '.d/new-45dd7dc.conf', bytes=1, sha256='f' * 64))
        if host != '57':
            core['previousReceiptPin'] = dict(original_receipt, path=str(PurePosixPath(original_receipt['path']).parent /
                'configuration' / 'target-installation-before-main-45dd7dc.json'))
            core['currentReceiptPin'] = dict(original_receipt, bytes=1, sha256='f' * 64)
        value['precedingActivationPins'].append(save(task,
            'main-program-control-activation-' + host + '-' + prior_role + '-45dd7dc-r5.json', core))
    name = 'fixture-input-' + suffix + '.json'; save(task, name, value)
    before = {p: p.read_bytes() for p in task.rglob('*') if p.is_file()}
    spec, payload = subject.prepare(task, private, name)
    assert spec['inputs'] == value and spec['previousCustody'] == (None if suffix == '57' else bundle['custodyByHost'][suffix])
    if suffix == '57': assert spec['oldReceiptPin'] is None
    if role == 'source': assert spec['current']['controllers'][-1]['sourceCommit'] == value['sourceCommit']
    assert spec['environmentBaseline']['publicPin'] == value['originalEnvironmentObservationPin']
    assert spec['activationInputsPin'] == subject.contract.Records(task).references.get(name, dict(
        file=name, bytes=len(before[task / name]), sha256=hashlib.sha256(before[task / name]).hexdigest()))
    assert spec['remoteAuditPath'].endswith('main-activation-' + role + '-45dd7dc-r5')
    compile(payload, '<v4-local-protocol-prepare>', 'exec')
    assert {p: p.read_bytes() for p in task.rglob('*') if p.is_file()} == before
    assert subject.dispatch_prepared(task, private, spec, payload)['remoteDispatched'] is False
