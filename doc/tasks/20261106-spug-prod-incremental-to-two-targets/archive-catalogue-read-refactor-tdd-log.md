# Archive catalogue request read refactor evidence

## Current Status

completed (local implementation and required verification only). Parent-owned task plan: archive-catalogue-read-refactor-plan.md. Parent still owns independent review, commit, formal build, installation and actual latency verification. No server, runtime, deployment or commit actions by this subagent.

## Goal and design constraints

Reduce repeated scan/hash/JSON work within one catalogue request while preserving full content SHA, exact source/chain bindings, complete path/limit checks and final freshness. No cross-request stale cache, timeout changes, swallowed errors or fallback. Long-term formal request-scoped reader and stable discovery are preferred over temporary bypasses.

## Experience gates

- Trigger: real /selections exceeds the fixed 10-second client contract due to repeated archive metadata work.
- Preflight check: existing source and profile; actual file-based fixtures; isolated new tests; UTF-8; no parent shared-log edits.
- Blocker: inability to detect content, inode/path, directory membership or quarantine changes; no actual RED; unresolved safety regression.
- Verification: BDD -> RED -> GREEN -> affected REGRESSION; exact commands, exits, counts and raw logs retained.
- Forbidden action: no weaker integrity, increased timeout, remote access, runtime writes, commits or unowned file edits.
- Evidence: source-control-native-selections-profile-r3.json and this log.

## BDD before implementation

1. Given two admitted points sharing roots/parents, when archive_references completes, then each identical JSON is decoded once and discovery scans each root once while preserving complete admitted chains.
2. Given file content replacement, inode replacement, directory membership change or duplicate backupId addition during a request, when the request finishes, then it refuses explicitly.
3. Given a quarantine marker introduced during enumeration, wrong identity or wrong parent prefix, when the request finishes, then existing safety refuses remain.
4. Given a second request after archive changes, when it enumerates, then it reads current metadata and never returns a prior request's cached success.

## Verification timeline

2026-11-09T14:17:54.274413+00:00 Plan identified; tests not yet run.

RED: `python -X utf8 doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_archive_catalogue_request_reads.py -v` -> FAIL (18 tests, 11 expected failures). Original output preserved in `archive-catalogue-request-reads-red-r2.log` (earlier 16-test run remains r1). Root scanned twice; identical JSON decoded eight times. Late manifest mutation, same-bytes inode/directory replacement, new points in new/existing empty directories, changed immutable index and late quarantine after its previous check were not rejected. The for_request mutation test reached the Windows native-root gate rather than rejecting changed originals before any request-directory writes; its expected archive-integrity error failed accordingly. Seven existing refusal/fresh-request scenarios passed. No production changes had been made at RED.

Implementation decision: one private reader per public call; one complete native read/decode per path and a second SHA-only verification before return, with path/inode/size/mtime/ctime checks on cache reuse and after final SHA reads. Discover roots once and watch root, every candidate directory and existing `.repository` directory so additions/removals/replacements are detected without rescanning. Monitor immutable admission index and repeat all quarantine absence checks at completion. Private binding helper accepts the request reader; public callers retain their signatures. for_request completes the freshness barrier before producing any request-owned files.

GREEN r1: initial 18 scenarios passed. Added direct final-SHA mutation, root rename, same-bytes replacement between requests and for_request source-parent refusal verification; GREEN r2: 22/22 passed. Instrumentation was corrected to identify JSON by original path (different original-exit files can legitimately have equal bytes); original RED logs remain unchanged. Each original now requires exactly two native reads, not merely an upper limit.

REGRESSION r1: existing `scripts/tests/test_restore_archive_catalogue.py -v` -> 27/27 PASS; `scripts/tests/test_restore_target_registration.py -v` -> 9/9 PASS. Raw logs retained separately. No broad unrelated suite run.

BDD: Given an absent quarantine marker, When it is created and removed during a later chain read, Then even the transient custody-directory change must refuse. RED: `test_archive_catalogue_request_reads.py RequestReads.test_transient_quarantine_change_during_request_is_rejected -v` -> FAIL, expected marker-directory freshness refusal absent. Raw log `archive-catalogue-request-reads-red-quarantine-r3.log` retained. Add an observation of its existing parent/ancestor alongside final marker absence checks; no new cache lifespan or filesystem writes.

## Final verification and handoff

All commands used Python `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`, `-X utf8`, with PYTHONPATH `C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/test-dependencies`.

- GREEN: `doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_archive_catalogue_request_reads.py -v` -> 23/23 PASS, 7.023 s; raw `archive-catalogue-request-reads-green-r3.log`.
- REGRESSION: `scripts/tests/test_restore_archive_catalogue.py -v` -> 27/27 PASS, 4.097 s; raw `archive-catalogue-request-reads-regression-catalogue-r2.log`.
- REGRESSION: `scripts/tests/test_restore_target_registration.py -v` -> 9/9 PASS, 0.002 s; raw `archive-catalogue-request-reads-regression-registration-r2.log`.
- `git diff --check -- backend/src/main/resources/recovery_control_restore_catalogue.py` -> PASS (Git emitted its existing LF/CRLF checkout warning).
- Deterministic local native-file observation: 2 admitted points, 14 unique originals, 28 complete reads (exactly 2/original), 14 JSON decodes (exactly 1/original), 1 root enumeration. This verifies request work counts, not production latency.

Implementation SHA-256 (current file bytes): `d6dfd4701a5a6343af71329167b1167952b3328b4a52568e9ff21ae060c84ab9`.
New test SHA-256: `e4b8acd02e8bfb52f48ef4f5eccce8dbb09ec73a4d505b5042b704df8a4057f1`.
Per-file bytes and SHA for all raw logs, implementation and test are retained in `archive-catalogue-request-reads-result.json`.

Owned files: only `backend/src/main/resources/recovery_control_restore_catalogue.py`, this uniquely named log, `test_archive_catalogue_request_reads.py`, `archive-catalogue-request-reads-result.json`, and `archive-catalogue-request-reads-*.log` in this task. No edits to shared task.md/execution-log.md, other helpers or documentation.

Practical limits: parsed metadata lives until this call completes, so request memory includes its scanned metadata; existing point-count and per-file byte limits remain. Freshness intentionally refuses concurrent directory or quarantine custody changes. Final checks provide an observed completion barrier, not a filesystem-wide transaction or lock. Full successful for_request output persistence requires native Linux/root custody and was not claimed from Windows; its parent-admission and pre-write integrity refusals were verified here. Actual source /selections timing and filesystem behavior must be checked after the parent's formal deployment; no claim that the production 10-second contract has passed.
