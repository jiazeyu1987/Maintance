# Spug remote integration — 2026-10-23

## Scope and Git inputs

User requested committing and pushing the Spug changes, then retrying after integrating the remote.

- Remote base: `origin/int_main`, `0833831b10a555216fdfeb4b87d8f707af0464f9`.
- Local implementation: `5d6a68e7c8f4d262ca63c7c3469d2fb84e419d56`.
- Integration branch: `codex/spug-backup-restore-merged-20261023`.
- Isolated worktree: `C:/codex-build/spug-backup-restore-merged-20261023`.

The old local history diverged from the remote and contained large historical artifacts. This branch starts at the current remote base and transplants the Spug implementation, rather than bringing that unrelated history into the remote. No force push is intended.

The remote base did not contain the Spug, recovery, backup-engine and rehearsal-app directories or recovery resource modules. Their implementation dependencies were restored from the local implementation commit. The Spug release builder also required `ops/release/release_source_catalog.py`; its local implementation was included. The shared preflight planner now preserves a deep copy of `targetPreflight`, fixing the target-bound seed preflight contract without replacing other remote planner behavior.

Unrelated modifications in the original development workspace are excluded. This integration performs no deployment and starts no backup or restore operation.

## Verification on the integrated tree

- Spug UI safety and release-center Node checks: 26 passed.
- Restore-result Node checks: 6 passed.
- Smallapp Python checks: 36 passed.
- Release-center Python checks: 134 passed, after adding the missing source catalog and preserving `targetPreflight`.
- Shared preflight ordering, target binding and regression checks: 116 passed.
- Backup variants, timing, performance, Redis authentication, request binding, cancellation, binlog DDL and replacement checks: 102 passed, 12 skipped on Windows.
- Staged Python syntax and JSON parsing, package source-path completeness, CRLF-aware whitespace checks: passed.
- Staged files: none exceeds 2 MB; the credential-pattern scan found no private-key blocks or recognized GitHub/AWS token patterns. This limited scan is not a security audit.

## Known verification failures retained

The broader ten-module backup check returned **105 passed, 7 failed, 27 skipped on Windows**. Its failures remain visible and have not been skipped or rewritten to obtain a green run:

- `test_capture_archive_guard.py`: closed-reader exception type differs; excluded-control membership changes are no longer rejected by the lightweight reader.
- `test_repository_root_identity.py`: four root-directory replacement cases and one missing-directory case expect identity checks that the lightweight implementation intentionally omits.

These tests import the current lightweight source but assert earlier strict-reader behavior. The product explicitly defines fast mode as skipping content, consistency and environment checks; standard mode is built separately from the preserved baseline plus vetted patches. Re-enabling all strict checks in lightweight mode would change that approved behavior. These retained failures therefore prevent claiming that the complete test suite passes; standard-mode coverage must be evaluated against its generated package rather than inferred from these lightweight imports. Linux-only skipped cases were not rerun in this integration.

The existing `acceptance.json` and task notes describe prior real UI rehearsals. They were preserved as historical evidence; no new live business acceptance or production operation was performed by this Git integration.
