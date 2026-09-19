# Verification Report

## Result

PASS for the authorized test-server release scope as of r44.

Closeout is blocked only on source integration: the r44 application fix chain and maintenance release-script fix branch are preserved, but they have not been merged into their respective `int_main` branches because the branches diverge and both main workspaces currently have unrelated tracked dirty changes.

## 2026-09-11 r44 Final Result

- Release tag: `release-20260911-verified-branch-app-r260908c-r44`.
- Authorized scope: test server only, `build-release -> publish-test/deploy-release`; no `mark-tested`, `promote-prod`, `promote-backup`, production, backup, or review-server action.
- Package scope: `publishScope=app-release`; no MySQL dump, MinIO snapshot, or DCC object inventory data package was used for this release.
- Source commits: backend/admin-frontend `713c64112d7b626a2ba71788fd36cc32d686addc`, `dirty=false`; maintenance release worktree `8080c0d3c7076d2305d945dea26bf1a22ceaf026`.
- Runtime: remote `.env IMAGE_TAG`, backend image tag, frontend image tag, backend health, frontend HTTP, and frontend `/release-info.json` all match r44.
- Migration state: latest test release lock is r44 `APPLIED`; r44 migration ledger has `APPLIED=6`, `SKIPPED_ALREADY_APPLIED=555`, `FAILED/RUNNING=0`.
- T1 fix: `system_users.active_canonical_username` and unique key `uk_system_users_tenant_active_canonical_username(tenant_id, active_canonical_username)` are present.
- Page verification: Playwright logged into `测试租户/aoteman`, landed on `http://172.30.30.58:8081/index`, title `瑛泰管理系统 - 首页`, permissions loaded, and the post-login stable window had `consoleErrors=0` and `failedRequests=0`.
- Evidence: `output/playwright/r44-test-release/playwright-test-server-r44-post-login-stable-summary.json` and `output/playwright/r44-test-release/test-server-dashboard-r44-post-login-stable.png`.
- Cleanup: task-local pytest/log/intermediate artifacts were removed by `task-closeout-cleanup`; r260908c release worktrees were removed from Git registration and physical paths.
- Protected source branches: maintenance `codex/release-r44-maintenance-script-20260911` at `8080c0d3c7076d2305d945dea26bf1a22ceaf026`; application `codex/test-release-signature-t1-active-unique-20260911` at `713c64112d7b626a2ba71788fd36cc32d686addc`.

## Authorized Scope

Only `build-release -> publish-test` for test server `172.30.30.58` was authorized. `mark-tested`, `promote-prod`, `promote-backup`, prod, and backup/review server actions were not executed.

## Historical Evidence Before r44

This section records earlier failed attempts and is superseded by the r44 final result above.

- Experience preflight: PASS.
- User-approved app release source: `b88c242f0aa3030f387695b500b3fb6e85fa54d8`.
- Maintenance release worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c\m`, base HEAD `bd4a05fa82263814cbf2828e86183f9413aa28b1`, plus release-script fix commits `67ab5cf`, `467f750`, `8bd1481`.
- App release worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c\a`, HEAD `b88c242f0aa3030f387695b500b3fb6e85fa54d8`.
- Migration policy gate: PASS, `migrationCount=605`.
- Release-script regression evidence: `scripts\tests\test_release_build_preflight_cache.py` -> `45 passed`.
- Last attempted releaseTag: `release-20260908-verified-branch-r260908c-r8`.
- r8 build evidence before blocker: build preflight PASS, backend Maven build SUCCESS, frontend build SUCCESS, backend/frontend Docker image build SUCCESS, Docker build evidence finalize PASS, MinIO client image `quay.io/minio/mc:latest` pulled and used.
- Earlier blocker `dcc/original/20260611/empty.docx` was restored via MinIO API from historical snapshot and verified.
- Later blocker `dcc/original/20260614/QMS文件清单.xlsx` was restored via MinIO API from historical snapshot and verified.
- Batch DCC recovery restored/confirmed `17529` objects from `release-20260616-121500-e2e` and restored `215` additional objects from `release-20260701-1720-mes-scheduler-dcc-inventory-fast`.
- Historical blocker after full bucket preflight: `128` DCC references remained without available local MinIO object; `126` had nonblank object paths and `2` had blank object paths.
- Read-only DB content check: `infra_file_content` has `0` rows / `0` bytes for the remaining `126` nonblank paths.
- At that historical stage, test server write was not executed and `publish-test` was not executed.

## Historical r29 Next Fix

At r29, `20260717_mes_balloon_excel_device_workstation_binding` needed remediation before continuing. Later attempts superseded this blocker and r44 completed the authorized test-server release.

## 2026-09-10 Migration Rehearsal Gate Verification

- Maintenance release worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c\m`, clean HEAD `120df30c5a9d7705f2459fb383f79d31f8445df3`.
- Isolated app verification worktree: `D:\IntRuoyiWorktree\r260908c-gate-verify`, clean detached HEAD `dfc481c40b8d3dfc637322518bbd40359b6082f3`.
- Static/TDD verification: PowerShell AST PASS, `test_release_build_preflight_cache.py` `50 passed`, `git diff --check` PASS.
- Actual gate attempt: `release-20260910-verified-branch-app-r260908c-r29`.
- Snapshot: source server `172.30.30.58`, source container `intruoyi-mysql`, source image digest `sha256:f5da8fc4b539c8ff9005b316b41b09d99b6ef6cdf55b5abbfcfd40dd3547f845`, access `read-only-consistent-dump`.
- Isolation: disposable MySQL used `--network none`, no published ports, exact releaseTag container/volume/staging names.
- Plan: `APPLY=83`; snapshot completed; three migrations applied successfully in isolation; first failure was `20260717_mes_balloon_excel_device_workstation_binding` with `balloon Excel workstation machine count mismatch`.
- Fail-fast: no `Building backend jar` marker; no frontend/Docker/NAS/publish action; real backend/frontend remained on `release-20260903-main-invoice-assistant-test-r260903b-r1`.
- Cleanup: independent remote verification returned `REHEARSAL_RESOURCES_ABSENT`; backend health `UP`; frontend HTTP `200`.
- Evidence artifacts under failed local r29 package: `manifest/migration-rehearsal-evidence.json`, `build-preflight-plan-test.json`, `build-preflight-evidence-test.json`, `build-preflight-target-state-test.json`.
- Evidence correction: r29 historical evidence wrote `appliedCount=4` because it counted start markers; final code commit `120df30` parses authoritative `REHEARSAL_APPLIED_COUNT`, so future evidence records `3` for this failure shape.
