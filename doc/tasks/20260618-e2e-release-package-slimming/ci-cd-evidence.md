# CI/CD Evidence: 真实 E2E 验证发布包瘦身

## Environments And Deployment Targets

- Local runtime-control backend: `http://127.0.0.1:48181`
- Local runtime-control frontend: `http://127.0.0.1:48182`
- Build artifact target: local release package cache and NAS ReleasePackage upload performed by `build-release`.
- Remote deployment targets: not used in this task.

## Commands

- Build command source: runtime-control real frontend action `构建发布包`.
- Package mode: `-Mode build-release`
- Component: `-Component intruoyi`
- Data sync flags: `-SkipDatabaseSync -SkipMinioSync`

## Pipeline

- Trigger: Playwright operates the runtime-control frontend and clicks `构建发布包`.
- Preview gate: command arguments are checked before execution.
- Preflight gates: Docker base image availability, migration metadata policy, Maven target lock cleanup, slimming unit test, and PowerShell parse.
- Build stages: backend Maven package, frontend Vite build, Docker image build/save, required SQL and resource manifest collection, final package slimming, manifest generation, NAS ReleasePackage upload.
- Success gate: operation status must be `SUCCESS`, release-status must read the candidate as `AVAILABLE`, and package/manifest checks must prove `docker-build-context` is absent.

## Required Secrets And Owners

- Existing local runtime-control configuration is used.
- No secrets are committed or recorded.
- Release operation owner: `admin`.

## Artifacts And Release Output

- Release tag: `release-20260618-1006-slim-e2e`.
- Operation ID: `op-2026-06-18T020729024794500Z-c7d40719-71d0-4ad4-a56d-0a521020632e`.
- Local release package path: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260618-1006-slim-e2e`.
- NAS release package path: `Backup/ReleasePackage/release-20260618-1006-slim-e2e`.
- Package size: `813,672,335 bytes` / `775.98 MiB`.
- Old comparison package: `release-20260618-0056-codeonly-e2e`, `1,460,030,640 bytes` / `1,392.39 MiB`.
- Actual reduction: `646,358,305 bytes` / `616.42 MiB`.
- Required artifacts present: `docker-compose.yml`, `release-manifest.json`, `manifest.json`, `required-sql`, `resources`, `runtime-env`, `intruoyi-images_release-20260618-1006-slim-e2e.tar`.
- Removed artifact class: `docker-build-context`; recursive path and manifest checks found no hits.

## RED Evidence

- Not applicable for this task; the failing test for the slimming behavior was recorded in `doc/tasks/20260618-shrink-release-package/execution-log.md`.

## GREEN Verification Evidence

- `python -m pytest scripts\tests\test_release_package_slimming.py` -> PASS, 2 tests.
- PowerShell parser check for `ops\deploy\publish-int-ruoyi.ps1` -> PASS.
- `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS, 149 migrations.
- Maven clean lock preflight for `yudao-module-dcc` -> PASS.
- Maven clean lock preflight for `yudao-server` -> PASS.
- Playwright preview of `构建发布包` -> PASS; command contained `-Mode build-release`, `-Component intruoyi`, `-SkipDatabaseSync`, `-SkipMinioSync`.
- Playwright execute of `构建发布包` -> PASS; operation ended `SUCCESS`.
- `GET /admin-api/infra/runtime-control/release-status` -> PASS; release candidate `release-20260618-1006-slim-e2e` is `AVAILABLE` with `checksumPresent=true`.
- Playwright UI refresh after operation -> PASS; operation row visible as `SUCCESS`, console error 0, failed request 0.

## Manual Approvals And Blockers

- User requested real E2E testing.
- No deployment approval is used because this task does not deploy.
- No blockers remain.

## Rollback Procedure And Validation

- No server state is changed by this task.
- If build fails, the failed release tag is kept only as failure evidence and must not be deployed.
- This task did not deploy the package, so rollback is not applicable.
