"""R6 consumer boundary checks using real local bytes and signatures.

These records are isolated test inputs, never runtime installation/authority.
Actual Linux trust/proof acceptance is a separate unexecuted prerequisite.
"""
import ast
import base64
from pathlib import Path
import sys

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))
from recovery_cli import PublicOutput
from recovery_engine import Budget, RecoveryError, canonical, pin, write
from recovery_plan_lab import LAB_ROOT, acyclic_inputs, native_installation


def originals(tmp_path):
    private = Ed25519PrivateKey.generate()
    public = tmp_path / 'unit-public.pem'
    public.write_bytes(private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
    key = pin(public)
    binary = tmp_path / 'unit-native-original.bin'
    binary.write_bytes(b'\x7fELF unit input only, not an executable Linux runtime')
    native = pin(binary)
    python = tmp_path / 'unit-python-original.bin'
    python.write_bytes(b'unit Python file original, not an interpreter')
    program = tmp_path / 'unit-program.py'
    program.write_bytes(b'"""Unit program bytes, never executed."""\n')
    metadata = tmp_path / 'unit-vendor-artifact.bin'
    metadata.write_bytes(b'unit vendor bytes')
    def seal(name, payload):
        return write(tmp_path / (name + '.json'), {
            'schemaVersion': 'RepositorySignedRecord/v1', 'keySha256': key['sha256'],
            'payload': payload, 'signature': base64.b64encode(private.sign(canonical(payload))).decode()})
    manifest = dict(schemaVersion='RepositoryNativeInstallation/v2', root=LAB_ROOT,
        sourceToolkitPin=pin(metadata), filePins=[pin(program)], dependencyPins=[native],
        pythonPin=pin(python), nativeRuntimeTrustPin=key, nativeRuntimeProofPin=key)
    return locals()


@pytest.mark.parametrize('version', ['RepositoryNativeInstallation/v0', 'RepositoryNativeInstallation/v3', None])
def test_unknown_installation_never_selects_an_alternate_reader(tmp_path, version):
    c = originals(tmp_path); c['manifest']['schemaVersion'] = version
    with pytest.raises(RecoveryError, match='LAB_INSTALLATION_VERSION_INVALID'):
        native_installation(c['seal']('unknown', c['manifest']), [c['key']])


@pytest.mark.parametrize('field', ['nativeRuntimeTrustPin', 'nativeRuntimeProofPin'])
def test_v2_requires_both_explicit_native_originals(tmp_path, field):
    c = originals(tmp_path); del c['manifest'][field]
    with pytest.raises(RecoveryError, match='LAB_RECORD_INVALID_REPOSITORYNATIVEINSTALLATION'):
        native_installation(c['seal']('missing', c['manifest']), [c['key']])


def test_v2_rejects_extra_wire_fields(tmp_path):
    c = originals(tmp_path); c['manifest']['outsideRoots'] = ['/usr']
    with pytest.raises(RecoveryError, match='LAB_RECORD_INVALID_REPOSITORYNATIVEINSTALLATION'):
        native_installation(c['seal']('extra', c['manifest']), [c['key']])


def test_native_fields_cannot_change_v1_meaning(tmp_path):
    c = originals(tmp_path); c['manifest']['schemaVersion'] = 'RepositoryNativeInstallation/v1'
    with pytest.raises(RecoveryError, match='LAB_RECORD_INVALID_REPOSITORYNATIVEINSTALLATION'):
        native_installation(c['seal']('legacy-native', c['manifest']), [c['key']])


def test_v1_still_rejects_a_real_original_outside_lab(tmp_path):
    c = originals(tmp_path); c['manifest']['schemaVersion'] = 'RepositoryNativeInstallation/v1'
    del c['manifest']['nativeRuntimeTrustPin']; del c['manifest']['nativeRuntimeProofPin']
    with pytest.raises(RecoveryError, match='LAB_PATH_OUT_OF_SCOPE'):
        native_installation(c['seal']('legacy', c['manifest']), [c['key']])


def test_v2_control_record_cannot_use_native_path_exception(tmp_path):
    c = originals(tmp_path)
    with pytest.raises(RecoveryError, match='LAB_PATH_OUT_OF_SCOPE'):
        native_installation(c['seal']('outside-control', c['manifest']), [c['key']])


def test_duplicate_native_dependency_path_is_rejected_before_import(tmp_path):
    c = originals(tmp_path); c['manifest']['dependencyPins'].append(c['native'])
    with pytest.raises(RecoveryError, match='LAB_INSTALLATION_DUPLICATE_PATH'):
        native_installation(c['seal']('duplicate', c['manifest']), [c['key']])


def test_signature_corruption_never_reaches_shared_loader(tmp_path):
    c = originals(tmp_path); reference = c['seal']('signed', c['manifest'])
    from recovery_engine import pinned_json
    value = pinned_json(reference); value['payload']['root'] += '/changed'
    with pytest.raises(InvalidSignature):
        native_installation(write(tmp_path / 'corrupted.json', value), [c['key']])


def graph(c):
    trust = c['seal']('trust', dict(schemaVersion='RepositoryLabNativeRuntimeTrust/v1',
        rehearsalId='unit-only', labRoot=LAB_ROOT, runtimeId='unit-only', runtimeRole='EXECUTOR',
        backingRootPath=str(c['tmp_path'] / 'private-backing'), literalRoots=['/usr', '/lib'],
        immutableRuntimeArtifactDigest='a' * 64, vendorArtifactPins=[pin(c['metadata'])],
        nativeFilePins=[dict(pin=c['native'], roles=['native-library'], vendorArtifactPins=[pin(c['metadata'])])]))
    evidence_path = c['tmp_path'] / 'unit-evidence.txt'
    evidence_path.write_bytes(b'unit raw mountinfo/status/maps original; no runtime acceptance\n')
    evidence = pin(evidence_path)
    proof = c['seal']('proof', {'schemaVersion': 'RepositoryLabNativeRuntimeProof/v1',
        'nativeRuntimeTrustPin': trust, 'readOnlyMountEvidencePin': evidence,
        'managerIdentityEvidencePin': evidence, 'nativeLinkageEvidencePin': evidence})
    c['manifest']['nativeRuntimeTrustPin'] = trust; c['manifest']['nativeRuntimeProofPin'] = proof
    installation = c['seal']('install-graph', c['manifest'])
    return installation, trust, proof, evidence


def test_public_output_tracks_v2_native_documents_and_protects_byte_originals(tmp_path):
    c = originals(tmp_path); installation, trust, proof, evidence = graph(c)
    publisher = PublicOutput(tmp_path / 'unused'); publisher.budget = Budget(30000)
    publisher.collect({'installedClosurePin': installation})
    for ref in (installation, trust, proof):
        assert Path(ref['path']) in publisher.documents
    for ref in (c['native'], pin(c['python']), pin(c['program']), pin(c['metadata']), evidence):
        assert Path(ref['path']) in publisher.protected
        assert Path(ref['path']) not in publisher.documents
    assert tmp_path / 'private-backing' in publisher.roots


def test_context_feedback_through_native_proof_is_rejected(tmp_path):
    c = originals(tmp_path); installation, _, _, evidence = graph(c)
    with pytest.raises(RecoveryError, match='LAB_CURRENT_CONTEXT_PIN_CYCLE'):
        acyclic_inputs([{'installedClosurePin': installation}], evidence)


def test_byte_original_and_document_pin_conflict_is_rejected(tmp_path):
    c = originals(tmp_path); changed = dict(c['native'], sha256='a' * 64)
    with pytest.raises(RecoveryError, match='LAB_STABLE_INPUT_PIN_CONFLICT'):
        acyclic_inputs([{'moduleSourcePins': [c['native']], 'nativeRuntimeProofPin': changed}], c['key'])


def test_combined_transitive_graph_counts_byte_leaves(tmp_path):
    key_file = tmp_path / 'selected-context.bin'; key_file.write_bytes(b'unit-selected-context')
    refs = []
    for number in range(4097):
        p = tmp_path / ('unit-member-%04d.bin' % number); p.write_bytes(b'unit member')
        refs.append(pin(p))
    with pytest.raises(RecoveryError, match='LAB_STABLE_INPUT_PIN_GRAPH_TOO_LARGE'):
        acyclic_inputs([{'moduleSourcePins': refs}], pin(key_file))


def test_native_source_never_imports_shared_reader_by_ambient_path():
    path = Path(__file__).resolve().parents[2] / 'ops/recovery/recovery_plan_lab.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    function, = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'native_installation']
    calls = [ast.unparse(n.func) for n in ast.walk(function) if isinstance(n, ast.Call)]
    assert 'module.verify_native_installation' in calls
    assert 'sys.path.insert' not in calls and 'sys.path.append' not in calls
