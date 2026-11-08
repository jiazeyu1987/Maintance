"""Build private candidate metadata only; no SSH, deployment or activation API.

The returned pins describe proposed remote bytes. They are NOT installation
evidence until the installer creates, reads back and activates those files.
"""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

from common import TASK, PRIVATE, SOURCE, write
from installation_history_custody import inputs

COMMIT = '0d445782dc06995b3c84b1b45146ea4b75483f92'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def pin_bytes(path, raw):
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read_private(name):
    return json.loads((PRIVATE / name).read_text(encoding='utf-8'))


def verified_package():
    build = json.loads((TASK / 'release-build-0d44578.json').read_text(encoding='utf-8'))
    assert build['status'] == 'PASS' and build['targetCommit'] == COMMIT
    raw = (PRIVATE / 'package-0d44578/backup-restore-standard.tgz').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == build['packageSha256']
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        manifest = json.load(archive.extractfile('package.json'))
        names = archive.getnames()
        assert manifest['variant'] == 'standard' and manifest['fileVerification'] and manifest['payloadContentVerification']
        assert len(names) == len(set(names)) and set(names) == set(manifest['files']) | {'package.json'}
        assert len(manifest['files']) == build['fileCount'] == 130
        assert hashlib.sha256(canonical(manifest['files'])).hexdigest() == manifest['packageSha256'] == build['fileManifestSha256']
        files = {}
        for member in archive.getmembers():
            assert member.isfile() and not PurePosixPath(member.name).is_absolute() and '..' not in PurePosixPath(member.name).parts
            files[member.name] = archive.extractfile(member).read()
            if member.name != 'package.json':
                assert hashlib.sha256(files[member.name]).hexdigest() == manifest['files'][member.name]
                compile(files[member.name], member.name, 'exec')
    return build, files


def candidate(suffix, build, files):
    assert suffix in ('58', '59')
    installed = read_private('automatic-target-closure-' + suffix + '.private.json')
    custody_evidence = read_private('automatic-target-custody-' + suffix + '.private.json')
    retained_pins, custody = inputs(suffix)
    target_ref = 'intruoyi-main-' + suffix + '-safe-restore-20261104-v1'
    root = PurePosixPath(custody['root'])
    generation = 'automatic-' + COMMIT[:7]
    engine = root / ('engine-' + generation)
    old_engine = PurePosixPath(installed['engine'])
    old_owner, old_control = installed['owner'], installed['control']
    old_receipt = custody_evidence['receipt']
    assert custody_evidence['custody']['status'] == 'PASS'
    assert custody_evidence['receiptPin'] == custody['steps'][-1]['currentReceiptPin']
    assert old_receipt['ownerConfigurationPin'] == installed['ownerPin'] == custody['selectedOwnerPin']
    assert old_receipt['controlConfigurationPin'] == installed['controlPin'] == custody['selectedControlPin']
    assert old_receipt['engine'] == str(old_engine) and old_receipt['service'] == installed['unit']
    assert installed['allPackageFilesMatch'] and 'sourceEpochPolicies' not in old_control
    owner = deepcopy(old_owner)
    owner['formalModuleDirectory'] = str(engine / 'formal')
    assert 'targetBackupEpochPolicies' not in owner
    policy = None
    if suffix == '59':
        evidence = read_private('automatic-target-epoch-59-binding.private.json')
        captures = [row['capture'] for row in evidence['rows']]
        assert len(captures) == 2 and all(all(row['checks'].values()) for row in evidence['rows'])
        assert captures[0]['source']['sourceIdentity'] == captures[1]['source']['sourceIdentity']
        replacement = owner['targets'][target_ref]['replacement']
        for capture in captures:
            assert capture['source']['databaseUuid'] == replacement['databaseUuid']
            assert capture['sourceLockPath'] == replacement['lockPath']
            for field, role in (('mysqlContainerId', 'mysql'), ('minioContainerId', 'minio')):
                assert capture['source'][field] == replacement['services'][role]['id']
        policy = dict(schemaVersion='SourceBackupEpochPolicy/v1',
            root=evidence['proposedEpochRoot'], sourceIdentity=captures[0]['source']['sourceIdentity'],
            databaseUuid=replacement['databaseUuid'], sourceLockPath=replacement['lockPath'])
        owner['targetBackupEpochPolicies'] = {target_ref: policy}
    assert owner['sources'] == old_owner['sources'] and owner['targets'] == old_owner['targets']
    assert owner.get('frontendReadiness') == old_owner.get('frontendReadiness')
    owner_pin = pin_bytes(root / 'configuration' / ('main-recovery-' + generation + '.json'), canonical(owner))
    control = deepcopy(old_control)
    control['environment']['PYTHONPATH'] = old_control['environment']['PYTHONPATH'].replace(str(old_engine) + '/', str(engine) + '/')
    assert control['environment']['PYTHONPATH'] != old_control['environment']['PYTHONPATH']
    for role in control['programPins']:
        control['programPins'][role] = pin_bytes(engine / (role + '_entry.py'), files[role + '_entry.py'])
    assert control['restoreConfigurations'][SOURCE][target_ref] == installed['ownerPin']
    control['restoreConfigurations'][SOURCE][target_ref] = owner_pin
    assert control['sourceConfigurations'] == old_control['sourceConfigurations']
    assert 'sourceEpochPolicies' not in control
    control_pin = pin_bytes(root / 'configuration' / ('control-' + suffix + '-' + generation + '.json'), canonical(control))
    updated_receipt = dict(old_receipt, sourceCommit=COMMIT, engine=str(engine),
        ownerConfigurationPin=owner_pin, controlConfigurationPin=control_pin)
    previous_pin = dict(custody_evidence['receiptPin'], path=str(root / 'configuration' / (generation + '-previous-target-installation.json')))
    proposed_receipt_pin = pin_bytes(root / 'target-installation.json', canonical(updated_receipt))
    return dict(schemaVersion='TaskAutomaticTargetCandidate/v1', status='PLAN_ONLY_NOT_DEPLOYED',
        host='172.30.30.' + suffix, targetConfigRef=target_ref, service=installed['unit'],
        sourceCommit=COMMIT, engine=str(engine), oldControlPid=installed['pid'],
        packageSha256=build['packageSha256'], fileManifestSha256=build['fileManifestSha256'], fileCount=130,
        oldOwnerPin=installed['ownerPin'], oldControlPin=installed['controlPin'],
        oldActiveReceiptPin=custody_evidence['receiptPin'], previousReceiptPin=previous_pin,
        proposedCurrentReceiptPin=proposed_receipt_pin, proposedReceipt=updated_receipt,
        ownerConfigurationPin=owner_pin, controlConfigurationPin=control_pin,
        owner=owner, control=control, targetBackupEpochPolicy=policy,
        epochStatus='REGISTER_WITH_TARGET_ONLY' if policy else 'NOT_ENABLED_NO_REGISTERED_MAIN_SOURCE_IDENTITY',
        previousCustody=custody, retainedHistoryPins=retained_pins,
        historicalSourcesAndTargetsUnchanged=True, source57MetadataUnchanged=True,
        noRemoteActions=True, restoreDispatched=False, backupDispatched=False)


def extend_verified_custody(previous, activated, expected_candidate):
    """Prepare the next audit chain only from a real successful installer receipt.

    The caller must run installation_history_custody.SCRIPT against the returned
    chain remotely before changing the selected-installation pointers.
    """
    assert activated['status'] == 'PASS' and activated['sourceCommit'] == COMMIT
    assert activated['host'] == expected_candidate['host'] and activated['service'] == expected_candidate['service']
    assert activated['targetAndSourceConfigurationUnchanged'] and activated['previousGenerationsRetained']
    assert activated['actualSelectionVerifiedBeforeActivation'] and activated['actualHealthContractVerified']
    assert not activated['restoreDispatched'] and not activated['backupDispatched']
    for key in ('previousReceiptPin', 'ownerConfigurationPin', 'controlConfigurationPin', 'engine'):
        assert activated[key] == expected_candidate[key]
    assert activated['currentReceiptPin'] == expected_candidate['proposedCurrentReceiptPin']
    old_current = previous['steps'][-1]['currentReceiptPin']
    assert all(activated['previousReceiptPin'][key] == old_current[key] for key in ('bytes', 'sha256'))
    assert set(activated['dropinPin']) == {'path', 'bytes', 'sha256'}
    result = deepcopy(previous)
    result['steps'].append({key: activated[key] for key in ('sourceCommit', 'engine',
        'previousReceiptPin', 'currentReceiptPin', 'ownerConfigurationPin', 'controlConfigurationPin', 'dropinPin')})
    result['expectedGenerationCommits'].append(COMMIT)
    result['selectedOwnerPin'] = activated['ownerConfigurationPin']
    result['selectedControlPin'] = activated['controlConfigurationPin']
    return result


if __name__ == '__main__':
    build, files = verified_package()
    for suffix in ('58', '59'):
        value = candidate(suffix, build, files)
        private_path = PRIVATE / ('automatic-target-candidate-' + suffix + '-0d44578.private.json')
        assert not private_path.exists(), 'CANDIDATE_ALREADY_RECORDED'
        write(private_path, value)
        public = {key: value[key] for key in ('schemaVersion', 'status', 'host', 'targetConfigRef', 'service',
            'sourceCommit', 'engine', 'oldControlPid', 'packageSha256', 'fileManifestSha256', 'fileCount',
            'oldOwnerPin', 'oldControlPin', 'oldActiveReceiptPin', 'previousReceiptPin',
            'proposedCurrentReceiptPin', 'ownerConfigurationPin', 'controlConfigurationPin', 'epochStatus',
            'historicalSourcesAndTargetsUnchanged', 'source57MetadataUnchanged', 'noRemoteActions',
            'restoreDispatched', 'backupDispatched')}
        public['privateCandidatePin'] = pin_bytes(private_path, private_path.read_bytes())
        public_path = TASK / ('automatic-target-candidate-' + suffix + '-0d44578.json')
        assert not public_path.exists(), 'PUBLIC_CANDIDATE_ALREADY_RECORDED'
        write(public_path, public)
        print(json.dumps(public, ensure_ascii=False))
