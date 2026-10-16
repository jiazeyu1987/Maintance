"""R3: actual W03 custody/header/receipt contracts at W04 public admission only."""
from pathlib import Path

import pytest

from test_recovery_static_repair_r5_residual_w04 import signed_cli
from test_recovery_static_repair_r5_residual_r2_w04 import publication_cli
import recovery_cli as cli
import recovery_engine as engine
from recovery_engine import Budget, load, pinned_json
from recovery_plan import trusted_configuration


DOCUMENTS = ['archive_header', 'manifest', 'recovery_receipt', 'capture_point', 'original_recovery']


def outputs_absent(output):
    assert not output.exists()
    assert not output.with_name(output.name+'.recording-failure.json').exists()


def test_actual_required_custody_and_document_closure_uses_original_budget(publication_cli):
    fixture = publication_cli
    peer = pinned_json(fixture.document_pins['peer'])['payload']
    assert peer['custodyPaths'] == [fixture.byte_pins['custodyPaths']]
    assert Path(peer['custodyPaths'][0]['path']).read_bytes() == b'\x00native-custody\xff'
    capture = pinned_json(fixture.document_pins['native_capture_response'])['payload']['result']
    assert set(capture) == set(('schemaVersion repositoryId operationId requestPin sourceConfigPin binding '
        'originalProcessPin archiveHeaderPin payloadTree metadata nativeEvidencePins').split())
    header = pinned_json(capture['archiveHeaderPin'])
    assert set(header) == set(('schemaVersion binding manifestReference treeDigest fileCount totalBytes '
                             'recoveryReceiptReference archiveRemainingBudget').split())
    receipt = pinned_json(header['recoveryReceiptReference'])
    assert set(receipt) == set(('state sourceRestored disasterRecoveryVerified capturePointReference '
                              'originalRecoveryReference').split())
    trust, policy, config = trusted_configuration(load(fixture.request_pin['path']))
    publisher = cli.PublicOutput(fixture.root/'safe.json'); budget = Budget(30000)
    publisher.bind(fixture.request, fixture.request_pin, trust, policy, config, budget)
    assert publisher.complete and publisher.budget is budget
    for kind in DOCUMENTS:
        ref = fixture.document_pins[kind]
        assert publisher.documents[Path(ref['path'])] == ref
        assert Path(ref['path']) in publisher.protected
    custody = Path(fixture.byte_pins['custodyPaths']['path'])
    assert custody in publisher.protected and custody not in publisher.documents
    assert not fixture.invocations


@pytest.mark.parametrize('kind', ['custodyPaths']+DOCUMENTS)
@pytest.mark.parametrize('destination', ['primary', 'secondary'])
def test_required_actual_reference_primary_and_derived_collision_preserves_original(
        publication_cli, kind, destination, capsys):
    fixture = publication_cli
    ref = fixture.byte_pins[kind] if kind == 'custodyPaths' else fixture.document_pins[kind]
    original = Path(ref['path']); before = original.read_bytes()
    output = original if destination == 'primary' else original.with_name(
        original.name.removesuffix('.recording-failure.json'))
    assert cli.main(['--request', fixture.request_pin['path'], '--output', str(output)]) == 1
    assert original.read_bytes() == before
    other = output.with_name(output.name+'.recording-failure.json') if destination == 'primary' else output
    assert not other.exists()
    assert not fixture.invocations and not list(fixture.evidence.iterdir())
    assert 'PUBLIC_OUTPUT_PROTECTED_PATH' in capsys.readouterr().out


@pytest.mark.parametrize('kind', DOCUMENTS)
@pytest.mark.parametrize('fault', ['missing', 'changed'])
def test_required_actual_document_failure_stops_both_outputs(publication_cli, kind, fault, capsys):
    fixture = publication_cli
    path = Path(fixture.document_pins[kind]['path'])
    if fault == 'missing': path.unlink()
    else: path.write_bytes(path.read_bytes()+b' ')
    output = fixture.root/'safe.json'
    assert cli.main(['--request', fixture.request_pin['path'], '--output', str(output)]) == 1
    outputs_absent(output)
    assert not fixture.invocations and not list(fixture.evidence.iterdir())
    assert 'PUBLIC_OUTPUT_SCOPE_INCOMPLETE' in capsys.readouterr().out


@pytest.mark.parametrize('publication_cli', [dict(invalid_json=name) for name in
    ['archive-header', 'manifest', 'recovery-receipt', 'capture-point', 'original-recovery']], indirect=True)
def test_exact_pin_invalid_required_document_never_downgrades_to_bytes(publication_cli, capsys):
    fixture = publication_cli; output = fixture.root/'safe.json'
    assert cli.main(['--request', fixture.request_pin['path'], '--output', str(output)]) == 1
    outputs_absent(output)
    assert not fixture.invocations and not list(fixture.evidence.iterdir())
    assert 'PUBLIC_OUTPUT_SCOPE_INCOMPLETE' in capsys.readouterr().out


@pytest.mark.parametrize('publication_cli', [dict(unknown_reference=name) for name in ['header', 'receipt']], indirect=True)
def test_unknown_pin_inside_actual_required_document_stays_closed(publication_cli, monkeypatch, capsys):
    fixture = publication_cli; publishers = []; actual_collect = cli.PublicOutput.collect
    def collect(publisher, *args, **kwargs):
        if publisher not in publishers: publishers.append(publisher)
        return actual_collect(publisher, *args, **kwargs)
    monkeypatch.setattr(cli.PublicOutput, 'collect', collect)
    output = fixture.root/'safe.json'
    assert cli.main(['--request', fixture.request_pin['path'], '--output', str(output)]) == 1
    outputs_absent(output)
    assert len(publishers) == 1 and not publishers[0].complete
    assert not fixture.invocations and not list(fixture.evidence.iterdir())
    message = capsys.readouterr().out
    assert 'PUBLIC_OUTPUT_SCOPE_REFERENCE_TYPE_UNKNOWN' in message
    assert 'PUBLIC_OUTPUT_SCOPE_INCOMPLETE' in message


@pytest.mark.parametrize('fault', ['document-limit', 'byte-limit', 'node-limit', 'deadline'])
def test_actual_archive_expansion_keeps_limits_and_single_budget(publication_cli, monkeypatch, capsys, fault):
    fixture = publication_cli; publishers = []; budgets = []; reached = []
    actual_collect, actual_read, actual_init = cli.PublicOutput.collect, cli.pinned_json, engine.Budget.__init__
    def collect(publisher, *args, **kwargs):
        if publisher not in publishers: publishers.append(publisher)
        return actual_collect(publisher, *args, **kwargs)
    def budget_init(budget, milliseconds):
        budgets.append(budget); actual_init(budget, milliseconds)
    def read(ref, **kwargs):
        value = actual_read(ref, **kwargs)
        if ref == fixture.document_pins['archive_header'] and fault != 'deadline':
            publisher = publishers[0]
            reached.append(ref)
            if fault == 'document-limit': publisher.MAX_DOCUMENTS = len(publisher.documents)
            elif fault == 'byte-limit': publisher.MAX_JSON_BYTES = publisher.json_bytes
            else: publisher.MAX_NODES = publisher.nodes
        if ref == fixture.document_pins['manifest'] and fault == 'deadline':
            reached.append(ref); kwargs['budget'].deadline = 0
        return value
    monkeypatch.setattr(cli.PublicOutput, 'collect', collect)
    monkeypatch.setattr(engine.Budget, '__init__', budget_init)
    monkeypatch.setattr(cli, 'pinned_json', read)
    output = fixture.root/'safe.json'
    assert cli.main(['--request', fixture.request_pin['path'], '--output', str(output)]) == 1
    outputs_absent(output)
    assert len(reached) == 1 and len(publishers) == 1 and not publishers[0].complete
    assert len(budgets) == 1 and publishers[0].budget is budgets[0]
    assert not fixture.invocations and not list(fixture.evidence.iterdir())
    assert 'PUBLIC_OUTPUT_SCOPE_INCOMPLETE' in capsys.readouterr().out


@pytest.mark.parametrize('destination', ['same', 'new'])
def test_cache_hit_revalidates_actual_manifest_before_publication(publication_cli, destination, capsys):
    fixture = publication_cli; initial = fixture.root/'cached.json'
    assert cli.main(['--request', fixture.request_pin['path'], '--output', str(initial)]) == 0
    original = initial.read_bytes()
    journal = next(fixture.evidence.glob('request-*.json')); before_journal = journal.read_bytes()
    manifest = Path(fixture.document_pins['manifest']['path']); manifest.write_bytes(manifest.read_bytes()+b' ')
    output = initial if destination == 'same' else fixture.root/'new.json'
    assert cli.main(['--request', fixture.request_pin['path'], '--output', str(output)]) == 1
    assert initial.read_bytes() == original and journal.read_bytes() == before_journal
    if destination == 'new': outputs_absent(output)
    else: assert not initial.with_name(initial.name+'.recording-failure.json').exists()
    assert not fixture.invocations
    assert 'PUBLIC_OUTPUT_SCOPE_INCOMPLETE' in capsys.readouterr().out
