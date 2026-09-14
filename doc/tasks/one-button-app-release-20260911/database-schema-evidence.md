# Database Schema Evidence - one-button-app-release-20260911

## Scope

- Data change goal: make `20260812_mes_qa_pressure_pump_idi_seed` compatible with a target database that has the IDI DCC project but no legacy route-process QA source regulations.
- Affected entities: `dcc_project_code`, `mes_qa_inspection_regulation`, `mes_qa_inspection_regulation_version`, `mes_qa_inspection_regulation_process`, `mes_qa_inspection_regulation_item`, and release target preflight SQL.
- Database engine and migration tool: MySQL 8 via release required SQL executed by `publish-int-ruoyi.ps1`.

## Safety

- Empty legacy source baseline is explicit no-op; no rows are created from guessed or synthetic QA data.
- Partial, duplicate, or malformed legacy source rows remain fail-fast blockers.
- Existing compatible DCC-owned QA regulation remains idempotent.
- Existing incompatible DCC-owned QA regulation remains fail-fast.
- Test server diagnostic and target preflight were read-only; no business data was modified during diagnosis.

## BDD

BDD: IDI QA legacy source empty baseline -> Given the target database has the IDI DCC project and zero matching legacy QA source regulations / When `20260812_mes_qa_pressure_pump_idi_seed` runs / Then the migration commits as no-op before creating DCC-owned QA rows and does not fail during publish.

BDD: IDI QA legacy source partial or duplicate baseline -> Given one or more but not exactly three unique legacy QA source regulations, or invalid item counts / When the migration runs or target preflight runs / Then the workflow fails fast before treating the release as successful.

BDD: IDI QA target preflight catches target-state mismatch -> Given a without-data app-release package / When build or deploy derives target-bound migration decisions / Then `20260812_mes_qa_pressure_pump_idi_seed.preflight.sql` accepts only empty legacy baseline, complete legacy source baseline, or an already-compatible direct DCC QA regulation.

## Evidence

- RED: `python -X utf8 -m pytest -q script\tests\test_mes_qa_pressure_pump_idi_seed_sql.py --basetemp .tmp-r49-idi-seed-red` -> FAIL, 3 failed; old SQL did not accept empty legacy source and old preflight only checked table existence.
- GREEN: `python -X utf8 -m pytest -q script\tests\test_mes_qa_pressure_pump_idi_seed_sql.py script\tests\test_release_target_preflight_files.py --basetemp .tmp-r49-idi-seed-green` -> PASS, 8 passed.
- REGRESSION: `python -X utf8 -m pytest -q script\tests\test_mes_qa_pressure_pump_idi_seed_sql.py script\tests\test_release_target_preflight_files.py script\tests\test_release_preflight_plan.py --basetemp .tmp-r49-idi-seed-regression` -> PASS, 27 passed.
- App commit: `dc8edfe5cf1e4daa84cc9523f0a5c8a1a7c5be34`.

## Verification

- Migration verification: test server read-only execution of `target-preflight/20260812_mes_qa_pressure_pump_idi_seed.preflight.sql` returned `TARGET_PREFLIGHT_PASS:20260812_mes_qa_pressure_pump_idi_seed`.
- Diff verification: only the IDI QA migration SQL, matching target preflight, and dedicated Python contract test were changed in the app worktree.

## Rollback

- The change is forward-only migration logic. If reverted before release, remove app commit `dc8edfe5cf1e4daa84cc9523f0a5c8a1a7c5be34` from the release source and generate a new release tag.
- R49 is retired and must not be reused because its deploy attempt wrote FAILED release ledger state before version switch.

## Blockers

- None for the IDI QA empty legacy source fix.
