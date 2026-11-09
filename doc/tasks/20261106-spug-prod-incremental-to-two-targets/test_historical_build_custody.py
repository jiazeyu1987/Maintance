"""A-stage real local Git/file tests; no server, installation or business restore."""
from copy import deepcopy
import hashlib
import importlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

import pytest


def subject():
    return importlib.import_module('historical_build_custody')


def pin(path):
    raw = Path(path).read_bytes()
    return dict(path=str(Path(path).resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(',', ':')), encoding='utf-8')
    return pin(path)


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    return result.stdout.decode('utf-8').strip()


@pytest.fixture(scope='module')
def repository(tmp_path_factory):
    root = tmp_path_factory.mktemp('custody-real-git')
    git(root, 'init')
    git(root, 'config', 'user.name', 'Custody Test')
    git(root, 'config', 'user.email', 'custody-test@example.invalid')
    git(root, 'config', 'core.autocrlf', 'false')
    (root / '.gitattributes').write_bytes(b'*.crlf text eol=crlf\n*.txt text eol=lf\n*.bin -text\n')
    (root / 'code').mkdir()
    for name, raw in {'a.txt': b'one\ntwo\n', 'same.txt': b'one\ntwo\n',
                      'b.crlf': b'alpha\nbeta\n', 'c.bin': b'\x00\r\n\xff'}.items():
        (root / 'code' / name).write_bytes(raw)
    git(root, 'add', '.')
    git(root, 'commit', '-m', 'fixture committed inputs')
    before = git(root, 'rev-parse', 'HEAD')
    (root / 'revision.txt').write_bytes(b'next\n')
    git(root, 'add', 'revision.txt')
    git(root, 'commit', '-m', 'fixture selected revision')
    return root, before, git(root, 'rev-parse', 'HEAD')


@pytest.fixture
def case(tmp_path, repository):
    repo, previous, commit = repository
    worktree = tmp_path / 'release-fixture'
    git(repo, 'worktree', 'add', '--detach', str(worktree), commit)
    task = repo / 'doc' / 'tasks' / tmp_path.name
    task.mkdir(parents=True)
    private = tmp_path / 'private'
    private.mkdir()
    build = dict(status='PASS', targetCommit=commit, worktree=str(worktree.resolve()))
    build_pin = save(task / 'build.json', build)
    names = ['code/a.txt', 'code/b.crlf', 'code/c.bin', 'code/same.txt']
    originals = {name: pin(worktree / name) for name in names}
    raw = {name: (worktree / name).read_bytes() for name in names}
    assert raw['code/b.crlf'] == b'alpha\r\nbeta\r\n'
    source_pin = save(task / 'source.json', {'inputPins': {name: originals[name]['sha256'] for name in names}})
    log_name = 'doc/tasks/' + task.name + '/original.log'
    (task / 'original.log').write_bytes(b'original finite test output\r\n')
    log_pin = pin(task / 'original.log')
    local_pin = save(task / 'local.json', {'files': {log_name: {k: log_pin[k] for k in ('bytes', 'sha256')}}})
    inputs = dict(schemaVersion='HistoricalBuildCustodyInputs/v1', taskId=task.name,
        builds=[dict(id='engine', kind='ENGINE_PACKAGE', reportPin=build_pin)],
        sets=[dict(reportPin=source_pin, field='inputPins', bindings=[dict(name=name,
            purpose='COMMITTED_SOURCE', buildId='engine', originalPin=originals[name]) for name in names]),
            dict(reportPin=local_pin, field='files', bindings=[dict(name=log_name,
                purpose='TASK_ORIGINAL', buildId=None, originalPin=log_pin)])])
    value = dict(repo=repo, worktree=worktree, task=task, private=private, commit=commit, previous=previous,
        inputs=inputs, originals=originals, raw=raw, source_pin=source_pin, log_pin=log_pin,
        destination=private / 'historical-build-custody-fixture')
    yield value
    # Only this test's own checkout may be removed, including negative-test edits.
    assert worktree.resolve().parent == tmp_path.resolve()
    if worktree.exists():
        git(repo, 'worktree', 'remove', '--force', str(worktree))


def seal(case):
    return subject().seal_build_custody(case['task'], case['private'], inputs=case['inputs'],
        destination=case['destination'], repository=case['repo'])


def load(case, reference):
    return subject().load_build_custody(case['task'], case['private'], reference, repository=case['repo'])


def document(reference):
    return json.loads(Path(reference['path']).read_text(encoding='utf-8'))


def rewrite_manifest(reference, mutate):
    value = document(reference)
    mutate(value)
    return save(Path(reference['path']), value)


def test_roundtrip_keeps_raw_pins_and_git_identity_after_real_worktree_removal(case):
    before = deepcopy(case['inputs'])
    reference = seal(case)
    manifest = document(reference)
    assert case['inputs'] == before
    assert manifest['installationPerformed'] is manifest['testsExecuted'] is manifest['serverWrites'] is False
    assert manifest['builds'][0]['sourceCommit'] == case['commit']
    assert manifest['builds'][0]['treeId'] == git(case['repo'], 'rev-parse', case['commit'] + '^{tree}')
    by_name = {row['name']: row for row in manifest['entries']}
    assert by_name['code/b.crlf']['representation'] == 'CRLF_TO_LF'
    assert by_name['code/c.bin']['representation'] == 'IDENTICAL'
    git(case['repo'], 'worktree', 'remove', str(case['worktree']))
    assert not case['worktree'].exists()
    reader = load(case, reference)
    for name, original in case['originals'].items():
        assert reader.read_original(original, evidence_pin=case['source_pin'], purpose='COMMITTED_SOURCE') == case['raw'][name]
    reader.verify_original_inputs(list(case['originals'].values()))
    physical = reader.finish()
    assert reference in physical and manifest['archivePin'] in physical
    assert not any(str(case['worktree']) in row['path'] for row in physical)


def test_duplicate_content_keeps_all_original_bindings_with_one_member(case):
    reference = seal(case)
    value = document(reference)
    assert len(value['entries']) == 5
    with tarfile.open(value['archivePin']['path'], 'r:') as archive:
        assert len(archive.getmembers()) == 4
    load(case, reference).finish()


@pytest.mark.parametrize('change', ['missing', 'extra', 'duplicate', 'wrong_hash', 'wrong_bytes'])
def test_original_report_set_is_complete_and_exact(case, change):
    group = case['inputs']['sets'][0]
    if change == 'missing': group['bindings'].pop()
    elif change == 'extra': group['bindings'].append(dict(group['bindings'][0], name='code/extra.txt'))
    elif change == 'duplicate': group['bindings'].append(deepcopy(group['bindings'][0]))
    elif change == 'wrong_hash': group['bindings'][0]['originalPin']['sha256'] = 'a' * 64
    else: group['bindings'][0]['originalPin']['bytes'] += 1
    with pytest.raises(ValueError, match='BUILD_CUSTODY_(REPORT_SET|SOURCE_PIN|PIN)_'):
        seal(case)
    assert not (case['destination'] / 'manifest.json').exists()


@pytest.mark.parametrize('change', ['outside_build', 'task_outside_scope', 'path_traversal'])
def test_original_path_scope_cannot_be_supplied_as_arbitrary_fallback(case, change):
    if change == 'outside_build':
        case['inputs']['sets'][0]['bindings'][0]['originalPin'] = case['log_pin']
    elif change == 'task_outside_scope':
        case['inputs']['sets'][1]['bindings'][0]['originalPin'] = case['originals']['code/a.txt']
    else:
        group = case['inputs']['sets'][0]
        value = document(group['reportPin'])
        original = value['inputPins'].pop('code/a.txt')
        value['inputPins']['../escape.txt'] = original
        group['reportPin'] = save(Path(group['reportPin']['path']), value)
        group['bindings'][0]['name'] = '../escape.txt'
    with pytest.raises(ValueError, match='BUILD_CUSTODY_(SOURCE_PATH|MEMBER_NAME)_'):
        seal(case)


@pytest.mark.parametrize('change', ['tracked', 'untracked', 'head'])
def test_sealing_always_requires_the_actual_clean_selected_checkout(case, change):
    if change == 'tracked': (case['worktree'] / 'revision.txt').write_bytes(b'changed\n')
    elif change == 'untracked': (case['worktree'] / 'unexpected').write_bytes(b'new')
    else: git(case['worktree'], 'checkout', '--detach', case['previous'])
    with pytest.raises(ValueError, match='BUILD_CUSTODY_CHECKOUT_(NOT_CLEAN|COMMIT_CHANGED)'):
        seal(case)


def test_repeat_destination_is_rejected_without_rewriting_originals(case):
    reference = seal(case)
    old = Path(reference['path']).read_bytes()
    with pytest.raises(ValueError, match='BUILD_CUSTODY_DESTINATION_EXISTS'):
        seal(case)
    assert Path(reference['path']).read_bytes() == old


def test_missing_archive_has_no_live_original_file_fallback(case):
    reference = seal(case)
    Path(document(reference)['archivePin']['path']).unlink()
    assert (case['worktree'] / 'code/a.txt').is_file()
    with pytest.raises(ValueError, match='BUILD_CUSTODY_INPUT_UNAVAILABLE'):
        load(case, reference)


def test_unregistered_original_or_evidence_or_purpose_is_rejected(case):
    reference = seal(case)
    reader = load(case, reference)
    original = case['originals']['code/a.txt']
    for changed, evidence, purpose in [(dict(original, sha256='a' * 64), case['source_pin'], 'COMMITTED_SOURCE'),
            (original, case['inputs']['sets'][1]['reportPin'], 'COMMITTED_SOURCE'),
            (original, case['source_pin'], 'TASK_ORIGINAL')]:
        with pytest.raises(ValueError, match='BUILD_CUSTODY_ORIGINAL_NOT_REGISTERED'):
            reader.read_original(changed, evidence_pin=evidence, purpose=purpose)
    with pytest.raises(ValueError, match='BUILD_CUSTODY_ORIGINAL_NOT_REGISTERED'):
        reader.verify_original_inputs([dict(original, bytes=999)])


@pytest.mark.parametrize('change', ['archive', 'report', 'manifest'])
def test_finish_rejects_drift_after_the_actual_original_load(case, change):
    reference = seal(case)
    reader = load(case, reference)
    target = {'archive': document(reference)['archivePin']['path'],
              'report': case['source_pin']['path'], 'manifest': reference['path']}[change]
    with Path(target).open('ab') as stream: stream.write(b' ')
    with pytest.raises(ValueError, match='BUILD_CUSTODY_PIN_CHANGED'):
        reader.finish()


@pytest.mark.parametrize('change', ['missing', 'extra', 'duplicate', 'link', 'traversal', 'wrong_content'])
def test_bounded_archive_members_are_checked_even_with_recomputed_archive_pin(case, change):
    reference = seal(case)
    manifest = document(reference)
    path = Path(manifest['archivePin']['path'])
    with tarfile.open(path, 'r:') as archive:
        members = [(row.name, archive.extractfile(row).read()) for row in archive]
    if change == 'missing': members.pop()
    elif change == 'extra': members.append(('objects/' + 'a' * 64, b'extra'))
    elif change == 'duplicate': members.append(members[0])
    elif change == 'traversal': members.append(('../outside', b'bad'))
    elif change == 'wrong_content': members[0] = (members[0][0], b'changed')
    with tarfile.open(path, 'w:', format=tarfile.USTAR_FORMAT) as archive:
        for name, raw in members:
            row = tarfile.TarInfo(name)
            row.size = len(raw)
            archive.addfile(row, io.BytesIO(raw))
        if change == 'link':
            row = tarfile.TarInfo('objects/' + 'b' * 64)
            row.type = tarfile.SYMTYPE
            row.linkname = '../outside'
            archive.addfile(row)
    reference = rewrite_manifest(reference, lambda value: value.update(archivePin=pin(path)))
    with pytest.raises(ValueError, match='BUILD_CUSTODY_ARCHIVE_(MEMBER_INVALID|SET_CHANGED|CONTENT_CHANGED)'):
        load(case, reference)


@pytest.mark.parametrize('change', ['entry_missing', 'blob', 'representation', 'commit'])
def test_manifest_cannot_detach_original_report_or_commit_binding(case, change):
    reference = seal(case)
    def mutate(value):
        if change == 'entry_missing': value['entries'].pop()
        elif change == 'blob': value['entries'][0]['blobId'] = 'a' * 40
        elif change == 'representation': value['entries'][0]['representation'] = 'CRLF_TO_LF'
        else: value['builds'][0]['sourceCommit'] = case['previous']
    reference = rewrite_manifest(reference, mutate)
    with pytest.raises(ValueError, match='BUILD_CUSTODY_(MANIFEST_ENTRIES_CHANGED|BUILD_CHANGED|GIT_BINDING_CHANGED)'):
        load(case, reference)


def test_archive_is_parsed_once_for_all_registered_reads(case, monkeypatch):
    reference = seal(case)
    real = tarfile.open
    calls = []
    def counted(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)
    monkeypatch.setattr(tarfile, 'open', counted)
    reader = load(case, reference)
    for original in case['originals'].values():
        reader.read_original(original, evidence_pin=case['source_pin'], purpose='COMMITTED_SOURCE')
    reader.finish()
    assert len(calls) == 1


def test_declared_file_budget_is_enforced_on_real_file_bytes(case, monkeypatch):
    monkeypatch.setattr(subject(), 'MAX_FILE_BYTES', 4)
    with pytest.raises(ValueError, match='BUILD_CUSTODY_FILE_LIMIT'):
        seal(case)


def test_resource_build_identity_uses_its_original_source_commit(case):
    entry = case['inputs']['builds'][0]
    old = document(entry['reportPin'])
    old['sourceCommit'] = old.pop('targetCommit')
    entry['kind'] = 'SPUG_RESOURCE'
    entry['reportPin'] = save(Path(entry['reportPin']['path']), old)
    reference = seal(case)
    assert document(reference)['builds'][0]['kind'] == 'SPUG_RESOURCE'
    load(case, reference).finish()


def test_archive_end_blocks_cannot_hide_unvalidated_trailing_data(case):
    reference = seal(case)
    path = Path(document(reference)['archivePin']['path'])
    with path.open('ab') as stream:
        stream.write(b'unvalidated trailing archive bytes')
    reference = rewrite_manifest(reference, lambda value: value.update(archivePin=pin(path)))
    with pytest.raises(ValueError, match='BUILD_CUSTODY_ARCHIVE_MEMBER_INVALID'):
        load(case, reference)


def test_last_seal_guard_rejects_real_head_change_after_manifest_write(case, monkeypatch):
    module = subject()
    original = module._write_exclusive
    def write_then_change_head(path, raw):
        original(path, raw)
        if path.name == 'manifest.json':
            git(case['worktree'], 'checkout', '--detach', case['previous'])
    monkeypatch.setattr(module, '_write_exclusive', write_then_change_head)
    with pytest.raises(ValueError, match='BUILD_CUSTODY_CHECKOUT_COMMIT_CHANGED'):
        seal(case)


def test_worktree_must_be_the_actual_registered_checkout_top_level(case):
    nested = case['worktree'] / 'nested'
    (nested / 'code').mkdir(parents=True)
    for name, raw in case['raw'].items():
        (nested / name).write_bytes(raw)
    git(case['worktree'], 'add', 'nested')
    git(case['worktree'], 'commit', '-m', 'fixture nested identical bytes')
    build = case['inputs']['builds'][0]
    value = document(build['reportPin'])
    value.update(worktree=str(nested.resolve()), targetCommit=git(case['worktree'], 'rev-parse', 'HEAD'))
    build['reportPin'] = save(Path(build['reportPin']['path']), value)
    for row in case['inputs']['sets'][0]['bindings']:
        row['originalPin'] = pin(nested / row['name'])
    with pytest.raises(ValueError, match='BUILD_CUSTODY_CHECKOUT_ROOT_CHANGED'):
        seal(case)


@pytest.mark.parametrize('wrong_path', [False, True])
def test_repository_source_preserves_original_local_proof_path_and_exact_git_blob(case, wrong_path):
    source = case['repo'] / 'code/a.txt'
    original = pin(source)
    evidence = save(case['task'] / 'repository-source.json', {'files': {
        'code/a.txt': {key: original[key] for key in ('bytes', 'sha256')}}})
    binding = dict(name='code/a.txt', purpose='REPOSITORY_SOURCE', buildId='engine', originalPin=original)
    if wrong_path:
        binding['originalPin'] = pin(case['worktree'] / 'code/a.txt')
    case['inputs']['sets'].append(dict(reportPin=evidence, field='files', bindings=[binding]))
    if wrong_path:
        with pytest.raises(ValueError, match='BUILD_CUSTODY_SOURCE_PATH_INVALID'):
            seal(case)
    else:
        reference = seal(case)
        reader = load(case, reference)
        assert reader.read_original(original, evidence_pin=evidence, purpose='REPOSITORY_SOURCE') == source.read_bytes()
        row = next(row for row in document(reference)['entries'] if row['purpose'] == 'REPOSITORY_SOURCE')
        assert row['originalPin'] == original
        assert row['blobId'] == git(case['repo'], 'rev-parse', case['commit'] + ':code/a.txt')
