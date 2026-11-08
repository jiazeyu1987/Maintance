"""Local file/CLI contracts; Git writes use owned temporary fixtures only."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location('record_commit_under_test', Path(__file__).with_name('commit_records.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
HEAD = 'b5c8817de2b4cc5efdad566f0fb65fdabefcb8d8'
PREFIX = 'doc/tasks/20261106-spug-prod-incremental-to-two-targets/'


class RecordCommitContract(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.task = self.root / PREFIX
        self.task.mkdir(parents=True)
        self.document = self.task / 'task.md'
        self.document.write_text('# Task\n\n## Current Status\nready_for_closeout\n\nPast: completed\n', encoding='utf-8')

    def pin(self, path):
        import hashlib
        data = path.read_bytes()
        return dict(path=path.relative_to(self.root).as_posix(), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

    def selection(self, entries=None, **extra):
        value = dict(schemaVersion='TaskRecordSelection/v1', mode='acceptance', expectedHead=HEAD,
                     files=entries if entries is not None else [self.pin(self.document)])
        value.update(extra)
        path = self.task / 'test-selection.json'
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def load(self, path):
        return MODULE.load_selection(self.root, self.task, path, 'acceptance', HEAD)

    def test_explicit_full_head_and_default_prepare(self):
        args = MODULE.argument_parser().parse_args(['--mode', 'acceptance', '--expected-head', HEAD,
            '--selection', str(self.task/'selection.json'), '--receipt', str(self.task/'new-receipt.json')])
        self.assertFalse(args.execute)
        self.assertEqual(HEAD, args.expected_head)
        self.assertNotIn('EXPECTED_HEAD', vars(MODULE))

    def test_ready_records_do_not_require_completed(self):
        self.assertEqual('ready_for_closeout', MODULE.validate_phase('acceptance', self.document.read_text(encoding='utf-8')))

    def test_first_status_is_authoritative(self):
        with self.assertRaisesRegex(ValueError, 'TASK_STATUS_NOT_READY_FOR_CLOSEOUT'):
            MODULE.validate_phase('acceptance', '## Current Status\nin_progress\n\n## Current Status\nready_for_closeout\n')

    def test_acceptance_cannot_accept_completed(self):
        with self.assertRaisesRegex(ValueError, 'TASK_STATUS_NOT_READY_FOR_CLOSEOUT'):
            MODULE.validate_phase('acceptance', '## Current Status\ncompleted\n')

    def test_final_cannot_accept_ready(self):
        with self.assertRaisesRegex(ValueError, 'TASK_STATUS_NOT_COMPLETED'):
            MODULE.validate_phase('final', self.document.read_text(encoding='utf-8'))

    def test_exact_pinned_selection(self):
        selection = self.selection()
        entries = self.load(selection)
        self.assertEqual([self.pin(self.document)], entries)

    def test_file_drift_fails(self):
        selection = self.selection()
        self.document.write_text('Changed after review', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'SELECTED_FILE_PIN_CHANGED'):
            self.load(selection)

    def test_selection_head_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, 'SELECTION_HEAD_OR_MODE_CHANGED'):
            self.load(self.selection(expectedHead='0'*40))

    def test_old_nov4_asset_cannot_enter(self):
        other = self.root/'doc/tasks/20261104-spug-selectable-restore-targets/resume-57-readonly.json'
        other.parent.mkdir(parents=True)
        other.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'UNOWNED_RECORD_PATH'):
            self.load(self.selection([self.pin(self.document), self.pin(other)]))

    def test_traversal_cannot_enter(self):
        row = dict(self.pin(self.document), path=PREFIX+'../outside.md')
        with self.assertRaisesRegex(ValueError, 'INVALID_RECORD_PATH'):
            self.load(self.selection([row]))

    def test_private_original_cannot_enter(self):
        original = self.task/'private'/'original.json'
        original.parent.mkdir()
        original.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'PRIVATE_OR_GENERATED_RECORD_PATH'):
            self.load(self.selection([self.pin(self.document), self.pin(original)]))

    def test_duplicate_paths_rejected(self):
        row = self.pin(self.document)
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_RECORD_PATH'):
            self.load(self.selection([row, row]))

    def test_task_status_document_must_be_pinned(self):
        with self.assertRaisesRegex(ValueError, 'TASK_STATUS_DOCUMENT_NOT_SELECTED'):
            self.load(self.selection([]))

    def test_only_explicit_shared_doc_is_selected(self):
        document = self.root/'docs/request-command-log.md'
        document.parent.mkdir()
        document.write_text('Shared reviewed record\n', encoding='utf-8')
        other = self.root/'docs/experience-index.md'
        other.write_text('Unrelated parallel change\n', encoding='utf-8')
        rows = self.load(self.selection([self.pin(self.document), self.pin(document)]))
        self.assertEqual(2, len(rows))
        self.assertNotIn(other.relative_to(self.root).as_posix(), [r['path'] for r in rows])

    def test_unreviewed_binary_fails(self):
        screenshot = self.task/'page.png'
        screenshot.write_bytes(b'not-a-real-screenshot')
        with self.assertRaisesRegex(ValueError, 'BINARY_CREDENTIAL_REVIEW_REQUIRED'):
            self.load(self.selection([self.pin(self.document), self.pin(screenshot)]))

    def test_syntax_and_known_private_value_fail_without_value_output(self):
        row = self.pin(self.document)
        secret = 'synthetic-local-secret-for-unit-check'
        self.document.write_text(secret, encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '^PRIVATE_VALUE_IN_SELECTED_RECORD$') as caught:
            MODULE.scan_selected_text(self.document, {secret})
        self.assertNotIn(secret, str(caught.exception))

    def test_prepare_receipt_is_exclusive(self):
        path = self.task/'prepare-receipt.json'
        MODULE.write_exclusive(path, dict(status='PREPARED'))
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            MODULE.write_exclusive(path, dict(status='PASS'))
        self.assertEqual(before, path.read_bytes())

    def test_completed_without_final_proof_fails(self):
        with self.assertRaisesRegex(ValueError, 'FINALIZATION_EVIDENCE_REQUIRED'):
            MODULE.validate_finalization(self.root, self.task, None, HEAD, '')

    def test_cli_missing_explicit_head_is_rejected(self):
        with self.assertRaises(SystemExit):
            MODULE.argument_parser().parse_args(['--mode', 'acceptance', '--selection', 'x', '--receipt', 'y'])

    def final_fixture(self, **changes):
        def save(name, value):
            path = self.task/name
            path.write_text(json.dumps(value), encoding='utf-8')
            return dict(file=name, **MODULE.pin(path))
        build_path = self.root/'absent-build'
        development = self.root/'retained-development'
        development.mkdir()
        assets = []
        for number in range(42):
            name = 'doc/tasks/20261104-spug-selectable-restore-targets/asset-' + str(number) + '.json'
            asset = development/name
            asset.parent.mkdir(parents=True, exist_ok=True)
            asset.write_text(json.dumps({'localFixtureAsset': number}), encoding='utf-8')
            asset_pin = MODULE.pin(asset)
            assets.append(dict(path=name, taskBytes=asset_pin['bytes'], taskSha256=asset_pin['sha256']))
        assets_pin = save('integration-pending-scope.json', dict(schemaVersion='IntegrationPendingScope/v1', otherTaskPending=assets))
        build = dict(generation='b5c8817', worktree=str(build_path), targetCommit=HEAD,
                     reportPin={'file': 'build.json', 'bytes': 2, 'sha256': 'b'*64}, packageSha256='c'*64)
        manifest_pin = save('task-owned-builds.json', dict(schemaVersion='TaskOwnedBuilds/v1', taskId=self.task.name, builds=[build]))
        save('integration-readonly-scope.json', dict(task=dict(path=str(development))))
        merge_pin = save('merge.json', dict(status='PASS', mainHead=HEAD, taskHead='a'*40,
                         mergeVerified=True, targetedRegressionPassed=True, parallelChangesPreserved=True))
        closeout_pin = save('closeout-verification.json', dict(status='PASS', ownedBuildCount=1, ownedBuildPhysicalAndGitRegistrationAbsent=True,
                            stableControlsVerified=True, currentControlGenerationsIndependentlyVerified=True))
        cleanup_pin = save('owned-build-cleanup.json', dict(status='PASS', deleted=True, ownedBuildManifestPin=manifest_pin,
                           builds=[dict(build, status='PASS', deleted=True, newCommits=False, mergeRequired=False,
                                        physicalPathAbsent=True, gitRegistrationAbsent=True,
                                        buildReportPin=build['reportPin'], retainedPackageSha256=build['packageSha256'])]))
        stable_pin = save('stable-controls-closeout.json', dict(status='PASS', currentInstallationEvidenceVerified=True,
                          catalogueCurrentRuntimeVerified=True))
        proof = dict(schemaVersion='TaskRecordsFinalization/v2', status='PASS', mainHead=HEAD, taskHead='a'*40,
                     taskWorktree=str(development), mergeVerificationPin=merge_pin, closeoutPin=closeout_pin,
                     cleanupPin=cleanup_pin, stableControlsPin=stable_pin,
                     taskWorktreeDisposition='retained_with_preexisting_assets', taskWorktreeHead='a'*40,
                     retainedAssetsPin=assets_pin)
        proof.update(changes)
        save('finalization.json', proof)
        return self.task/'finalization.json', build_path, development

    def validate_final(self, proof, registrations='', state=None):
        development = self.root/'retained-development'
        state = state if state is not None else dict(head='a'*40, mergedIntoMain=True, pendingOwnedPaths=[])
        # Git observations are an explicit local contract fixture; these tests
        # never assert a real merge or create commits. Asset checks use real files.
        return MODULE.validate_finalization(self.root, self.task, proof, HEAD,
            registrations + '\nworktree ' + development.as_posix() + '\n',
            state_reader=lambda *args: state)

    def test_final_file_contract_accepts_complete_local_fixture(self):
        proof, _, _ = self.final_fixture()
        result = self.validate_final(proof)
        self.assertEqual(HEAD, result['mainHead'])
        self.assertEqual('retained_with_preexisting_assets', result['taskWorktreeDisposition'])
        self.assertEqual(42, len(list((self.root/'retained-development').rglob('asset-*.json'))))

    def test_final_rejects_drifted_merge_proof(self):
        proof, _, _ = self.final_fixture()
        (self.task/'merge.json').write_text('{"status":"PASS"}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'PROOF_PIN_CHANGED'):
            self.validate_final(proof)

    def test_final_rejects_existing_build_despite_deleted_flag(self):
        proof, build, _ = self.final_fixture()
        build.mkdir()
        with self.assertRaisesRegex(ValueError, 'BUILD_WORKTREE_STILL_PRESENT'):
            self.validate_final(proof)

    def test_final_rejects_registered_build_despite_absent_path(self):
        proof, build, _ = self.final_fixture()
        with self.assertRaisesRegex(ValueError, 'BUILD_WORKTREE_STILL_PRESENT'):
            self.validate_final(proof, 'worktree '+build.as_posix()+'\n')

    def test_final_rejects_changed_preexisting_asset(self):
        proof, _, development = self.final_fixture()
        asset = development/'doc/tasks/20261104-spug-selectable-restore-targets/asset-0.json'
        asset.write_text('{"changed":true}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'RETAINED_ASSET_PIN_CHANGED'):
            self.validate_final(proof)
        self.assertEqual('{"changed":true}', asset.read_text(encoding='utf-8'))

    def test_final_rejects_wrong_head(self):
        proof, _, _ = self.final_fixture(mainHead='d'*40)
        with self.assertRaisesRegex(ValueError, 'FINALIZATION_HEAD_CHANGED'):
            self.validate_final(proof)

    def test_final_rejects_missing_retained_asset(self):
        proof, _, development = self.final_fixture()
        next(development.rglob('asset-*.json')).unlink()
        with self.assertRaisesRegex(ValueError, 'RETAINED_ASSET_MISSING'):
            self.validate_final(proof)

    def test_final_rejects_implicit_checkout_deletion(self):
        proof, _, _ = self.final_fixture(taskWorktreeDisposition='deleted')
        with self.assertRaisesRegex(ValueError, 'EXPLICIT_CHECKOUT_RETENTION_REQUIRED'):
            self.validate_final(proof)

    def test_final_rejects_unmerged_retained_head(self):
        proof, _, _ = self.final_fixture()
        with self.assertRaisesRegex(ValueError, 'RETAINED_CHECKOUT_HEAD_NOT_MERGED'):
            self.validate_final(proof, state=dict(head='a'*40, mergedIntoMain=False, pendingOwnedPaths=[]))

    def test_final_rejects_unaccounted_owned_changes(self):
        proof, _, _ = self.final_fixture()
        with self.assertRaisesRegex(ValueError, 'RETAINED_CHECKOUT_PENDING_TASK_CHANGES'):
            self.validate_final(proof, state=dict(head='a'*40, mergedIntoMain=True, pendingOwnedPaths=[PREFIX+'new.json']))

    def test_final_rejects_unregistered_retained_checkout(self):
        proof, _, _ = self.final_fixture()
        with self.assertRaisesRegex(ValueError, 'RETAINED_CHECKOUT_NOT_REGISTERED'):
            MODULE.validate_finalization(self.root, self.task, proof, HEAD, '',
                state_reader=lambda *args: dict(head='a'*40, mergedIntoMain=True, pendingOwnedPaths=[]))

    def test_copy_resolves_its_own_checkout(self):
        copied = self.task/'commit_records.py'
        copied.write_bytes(Path(MODULE.__file__).read_bytes())
        spec = importlib.util.spec_from_file_location('copied_record_helper', copied)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(self.task.resolve(), module.TASK)
        self.assertEqual(self.root.resolve(), module.ROOT)

    def test_diff_check_batches_windows_argument_budget(self):
        calls = []
        names = [PREFIX + 'record-' + str(i) + '.json' for i in range(650)]
        def runner(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, b'', b'')
        MODULE.check_selected_diff(self.root, names, runner=runner)
        self.assertEqual(names, [name for command in calls for name in command[4:]])
        self.assertTrue(all(len(command[4:]) <= 30 for command in calls))

    def test_real_wrong_head_fails_before_any_git_write(self):
        # A real fixture keeps this guard test valid on int_main and integration
        # branches while still exercising the exact production CLI and Git.
        shared_index = Path(MODULE.git_text(MODULE.ROOT, 'rev-parse', '--git-path', 'index'))
        if not shared_index.is_absolute():
            shared_index = MODULE.ROOT/shared_index
        shared_before = MODULE.pin(shared_index)
        shared_head = MODULE.git_text(MODULE.ROOT, 'rev-parse', 'HEAD')
        for name in ('commit_records.py', 'common.py', 'verify_task_records.py'):
            (self.task/name).write_bytes(Path(MODULE.__file__).with_name(name).read_bytes())
        def fixture_git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args])
        fixture_git('init', '--quiet', '--initial-branch=' + MODULE.TASK_BRANCH)
        (self.root/'baseline.txt').write_text('owned test fixture\n', encoding='utf-8')
        fixture_git('add', '--', 'baseline.txt')
        fixture_git('-c', 'user.name=Record contract test', '-c', 'user.email=record-contract@example.invalid',
                    'commit', '--quiet', '-m', 'Owned fixture baseline')
        fixture_head = fixture_git('rev-parse', 'HEAD')
        receipt = self.task/'records-contract-rejected-not-created.json'
        self.assertFalse(receipt.exists())
        index = self.root/'.git/index'
        before = MODULE.pin(index)
        result = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(self.task/'commit_records.py'), '--mode', 'acceptance',
             '--expected-head', '0'*40, '--selection', str(self.task/'absent-selection.json'),
             '--receipt', str(receipt)], capture_output=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn(b'HEAD_CHANGED_REVIEW_OWNED_SCOPE', result.stderr)
        self.assertEqual(before, MODULE.pin(index))
        self.assertEqual(fixture_head, fixture_git('rev-parse', 'HEAD'))
        self.assertEqual(shared_before, MODULE.pin(shared_index))
        self.assertEqual(shared_head, MODULE.git_text(MODULE.ROOT, 'rev-parse', 'HEAD'))
        self.assertFalse(receipt.exists())

    def test_unselected_scope_does_not_read_file_contents(self):
        other = self.root/'unrelated.bin'
        other.write_bytes(b'unrelated local fixture')
        with patch.object(MODULE, 'changed_paths', return_value={'unrelated.bin'}):
            with patch.object(Path, 'read_bytes', side_effect=RuntimeError('UNRELATED_CONTENT_READ')):
                observed = MODULE.unrelated_files(self.root, set(), set())
        self.assertEqual(other.stat().st_size, observed['unrelated.bin']['size'])

    def test_unselected_identity_detects_real_edit(self):
        other = self.root/'unrelated.txt'
        other.write_text('before', encoding='utf-8')
        with patch.object(MODULE, 'changed_paths', return_value={'unrelated.txt'}):
            before = MODULE.unrelated_files(self.root, set(), set())
            other.write_text('after with changed size', encoding='utf-8')
            after = MODULE.unrelated_files(self.root, set(), set())
        self.assertNotEqual(before, after)

    def test_retained_dirty_record_is_carried_by_exact_final_selection(self):
        development = self.root/'retained-work-copy'
        retained = development/PREFIX/'task.md'
        retained.parent.mkdir(parents=True)
        retained.write_bytes(self.document.read_bytes())
        row = self.pin(self.document)
        seen = []
        def reader(root, *args):
            self.assertEqual('status', args[0])
            return (' M '+row['path']+'\0').encode('utf-8')
        def text_reader(root, *args):
            self.assertEqual(('rev-parse', 'HEAD'), args)
            return 'a'*40
        def runner(command, **kwargs):
            seen.append(command)
            self.assertEqual(['git', 'merge-base', '--is-ancestor', 'a'*40, HEAD], command)
            return subprocess.CompletedProcess(command, 0, b'', b'')
        with patch.object(MODULE, 'git_bytes', side_effect=reader), patch.object(MODULE, 'git_text', side_effect=text_reader), patch.object(MODULE.subprocess, 'run', side_effect=runner):
            observed = MODULE.read_retained_checkout_state(development, self.root, self.task, HEAD, [row])
        self.assertEqual([], observed['pendingOwnedPaths'])
        self.assertEqual(1, len(seen))

    def test_retained_unselected_new_record_stays_pending(self):
        development = self.root/'retained-work-copy'
        relative = PREFIX+'uncommitted-proof.json'
        retained = development/relative
        retained.parent.mkdir(parents=True)
        retained.write_text('{"actualLocalFile":true}', encoding='utf-8')
        commands = []
        def runner(command, **kwargs):
            commands.append(command)
            if command[1] == 'merge-base':
                return subprocess.CompletedProcess(command, 0, b'', b'')
            self.assertEqual(['git', 'rev-parse', '--verify', HEAD+':'+relative], command)
            return subprocess.CompletedProcess(command, 128, b'', b'not present')
        with patch.object(MODULE, 'git_bytes', return_value=('?? '+relative+'\0').encode('utf-8')), patch.object(MODULE, 'git_text', return_value='a'*40), patch.object(MODULE.subprocess, 'run', side_effect=runner):
            observed = MODULE.read_retained_checkout_state(development, self.root, self.task, HEAD, [])
        self.assertEqual([relative], observed['pendingOwnedPaths'])
        self.assertTrue(all(command[1] not in ('add', 'commit', 'reset', 'stash', 'clean') for command in commands))


if __name__ == '__main__':
    unittest.main()
