"""Real Git/filesystem proof for historical v1 coverage, never remote operations."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
import main_program_control_activation as subject


NAME = 'backend/src/main/resources/recovery_control_restore_catalogue.py'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def reference(raw):
    return {'bytes': len(raw), 'sha256': digest(raw)}


@pytest.fixture
def source_case(tmp_path):
    root = tmp_path / 'committed'; root.mkdir()
    live = tmp_path / 'development'; live.mkdir()
    raw = b'VALUE = "original"\nSECOND = 2\n'
    path = root / NAME; path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    (root / '.gitattributes').write_bytes(b'*.py text eol=crlf\n')
    def git(*args):
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                                timeout=15, check=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
        return result.stdout
    git('init', '--quiet')
    git('config', 'user.name', 'Coverage Contract')
    git('config', 'user.email', 'coverage-contract@example.invalid')
    git('config', 'core.autocrlf', 'false')
    git('add', '--', '.gitattributes', NAME)
    git('commit', '--quiet', '-m', 'coverage protocol fixture')
    commit = git('rev-parse', 'HEAD').decode().strip()
    path.unlink(); git('checkout-index', '-f', '--', NAME)
    assert path.read_bytes() == raw.replace(b'\n', b'\r\n')
    git('add', '--', NAME)
    assert git('diff', '--cached', '--exit-code') == b''
    assert git('status', '--porcelain', '--untracked-files=all') == b''
    assert git('cat-file', 'blob', commit + ':' + NAME) == raw
    live_path = live / NAME; live_path.parent.mkdir(parents=True)
    live_path.write_bytes(b'VALUE = "legitimate development change"\n')
    return SimpleNamespace(root=root, path=path, live=live, live_path=live_path, raw=raw,
        commit=commit, build={'worktree': str(root), 'targetCommit': commit},
        pins={NAME: digest(path.read_bytes())}, expected=reference(raw), git=git)


def read(case, name=NAME):
    return subject.generation_product_source(name, case.expected, case.build, case.pins)


def test_real_committed_raw_is_authority_while_checkout_and_development_differ(source_case):
    c = source_case
    before = {p: p.read_bytes() for p in (c.path, c.live_path)}
    result = read(c)
    assert result['raw'] == c.raw
    assert result['physicalPin'] == subject.file_pin(c.path)
    proof = result['provenance']
    assert proof['sourceCommit'] == c.commit and proof['relativePath'] == NAME
    assert proof['blobPin'] == c.expected and proof['checkoutPin'] == result['physicalPin']
    assert len(proof['commands']) == 2
    assert all(row['actualExitCode'] == 0 and row['timedOut'] is False for row in proof['commands'])
    assert proof['commands'][-1]['command'] == ['git', '-C', str(c.root), 'cat-file', 'blob', c.commit + ':' + NAME]
    assert all(path.read_bytes() == raw for path, raw in before.items())


@pytest.mark.parametrize('change', ['expected-raw', 'checkout-tamper', 'checkout-missing', 'linux-binding', 'blob-missing'])
def test_rejects_original_source_failure_without_live_workspace_fallback(source_case, change):
    c = source_case
    c.live_path.write_bytes(c.raw)
    if change == 'expected-raw':
        c.expected = reference(b'VALUE = "tampered original"\n')
    elif change == 'checkout-tamper':
        c.path.write_bytes(b'changed checkout\n')
    elif change == 'checkout-missing':
        c.path.unlink()
    elif change == 'linux-binding':
        c.pins.clear()
    else:
        c.git('rm', '--quiet', '--', NAME)
        c.git('commit', '--quiet', '-m', 'remove source from original commit')
        c.build['targetCommit'] = c.git('rev-parse', 'HEAD').decode().strip()
        c.path.parent.mkdir(parents=True, exist_ok=True)
        c.path.write_bytes(c.raw.replace(b'\n', b'\r\n'))
    if change == 'blob-missing':
        with pytest.raises(subprocess.CalledProcessError) as error:
            read(c)
        assert error.value.returncode != 0 and error.value.stderr
        assert error.value.cmd[-1] == c.build['targetCommit'] + ':' + NAME
    else:
        with pytest.raises((ValueError, FileNotFoundError)):
            read(c)
    assert c.live_path.read_bytes() == c.raw


@pytest.mark.parametrize('name', ['../outside.py', '/outside.py', 'backend/../outside.py',
                                  'backend\\outside.py', 'C:/outside.py', 'backend//outside.py'])
def test_unsafe_product_path_is_rejected_before_git_dispatch(source_case, name, monkeypatch):
    c = source_case
    c.pins[name] = c.pins[NAME]
    def forbidden(*args, **kwargs):
        raise AssertionError('Unsafe path dispatched Git')
    monkeypatch.setattr(subject.subprocess, 'run', forbidden)
    with pytest.raises(ValueError, match='GENERATION_SOURCE_EVIDENCE_SCOPE'):
        read(c, name)


def actual_materials():
    task = Path(__file__).resolve().parent
    records = subject.contract.Records(task)
    name = 'main-program-control-coverage-45dd7dc-r1.json'
    raw = (task / name).read_bytes()
    ref = {'file': name, **reference(raw)}
    report = records.pinned(ref)
    build = records.pinned(report['candidateBuildPin'])
    old_build = records.pinned(report['baselineBuildPin'])
    inputs = {'sourceCommit': build['targetCommit'], 'buildPin': report['candidateBuildPin'], 'coveragePin': ref}
    predecessor = {'build': old_build, 'generation': {'sourceCommit': old_build['targetCommit'],
                                                   'buildPin': report['baselineBuildPin']}}
    return task, records, inputs, predecessor, report, build


def test_actual_original_coverage_reader_uses_exact_committed_raw_and_real_packages():
    task, records, inputs, predecessor, report, build = actual_materials()
    path = task / inputs['coveragePin']['file']
    before = subject.file_pin(path)
    proof = subject.validate_generation_coverage(records, inputs, predecessor)
    assert len(proof['packageFiles']) == len(proof['previousPackageFiles']) == 147
    assert proof['coverage'] == report and proof['delta']['packages'][1]['variant'] == 'lightweight'
    assert proof['committedSourceEvidence'][0]['sourceCommit'] == build['targetCommit']
    assert proof['committedSourceEvidence'][0]['relativePath'] == NAME
    assert proof['committedSourceEvidence'][0]['blobPin'] == {
        'bytes': 20770, 'sha256': 'd6dfd4701a5a6343af71329167b1167952b3328b4a52568e9ff21ae060c84ab9'}
    assert any(p['path'] == str(Path(build['worktree']) / NAME) and
               p['sha256'] == '3de7bcca9e72ad7c94b670f470924ccb92ba123553791f430da6c28906ad7e9d'
               for p in proof['physicalPins'])
    assert subject.file_pin(path) == before


def test_task_original_drift_is_still_rejected_by_real_coverage_reader(tmp_path, monkeypatch):
    task, records, inputs, predecessor, report, build = actual_materials()
    proof = records.pinned(report['deltaTestEvidencePins'][0])
    copied_task = tmp_path / 'doc' / 'tasks' / task.name
    copied_task.mkdir(parents=True)
    copied = []
    for name in proof['files']:
        if name.startswith('doc/tasks/'):
            target = tmp_path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((task.parents[2] / name).read_bytes())
            copied.append(target)
    assert len(copied) == 11
    original = copied[0].read_bytes()
    copied[0].write_bytes(bytes([original[0] ^ 1]) + original[1:])
    monkeypatch.setattr(subject, 'TASK', copied_task)
    with pytest.raises(ValueError, match='MAIN_ACTIVATION_GENERATION_EVIDENCE_PIN_CHANGED'):
        subject.validate_generation_coverage(records, inputs, predecessor)
