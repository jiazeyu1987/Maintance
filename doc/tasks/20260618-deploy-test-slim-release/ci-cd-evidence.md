# CI/CD Evidence: 部署瘦身发布包到测试服并验证

## Environments And Deployment Targets

- Local runtime-control backend: `http://127.0.0.1:48181`
- Local runtime-control frontend: `http://127.0.0.1:48182`
- Test server frontend: `http://172.30.30.58:8081/`
- Test server backend health: `http://172.30.30.58:48081/actuator/health`
- Test server remote app dir: `/opt/intruoyi/runtime`

## Commands

- Deploy command source: runtime-control real frontend action `部署测试服`.
- Deploy mode: `-Mode deploy-release`
- Environment: `-Environment test`
- Release tag: `release-20260618-1006-slim-e2e`

## Pipeline

- Preflight: verify runtime-control health, release candidate availability, test-server target, and remote capacity/readiness.
- Preview gate: Playwright clicks `部署测试服` and checks the generated command before execution.
- Deploy stage: runtime-control submits a test deploy operation.
- Verification stage: operation status, remote `.env`, Docker image tags, health check, migration status, and browser entry are checked.

## Required Secrets And Owners

- Existing local runtime-control and SSH configuration are used.
- No secrets are committed or recorded.
- Release operation owner: `admin`.

## Artifacts And Release Output

- Release tag: `release-20260618-1006-slim-e2e`.
- Build operation: `op-2026-06-18T020729024794500Z-c7d40719-71d0-4ad4-a56d-0a521020632e`.
- Deploy operation: `op-2026-06-18T023529660636300Z-3ade4c9c-c424-4f58-a230-304a7990492e`, final status `SUCCESS`.
- NAS release package path: `Backup/ReleasePackage/release-20260618-1006-slim-e2e`.

## RED Evidence

- Not applicable; this task deploys an already built release package and does not change code.
- Extra non-acceptance probe: test-server `测试租户/aoteman` login returned business `code=500` with `登录失败，账号密码不正确`; no account switch or business write was performed.

## GREEN Verification Evidence

- Runtime-control Playwright preview passed for `部署测试服`: command contained `-Mode deploy-release`, `-Environment test`, `-ServerHost 172.30.30.58`, and `/opt/intruoyi/runtime`; command did not contain production, backup, restore, or rollback actions.
- Deploy operation `op-2026-06-18T023529660636300Z-3ade4c9c-c424-4f58-a230-304a7990492e` completed with status `SUCCESS`.
- Test server `.env`: `IMAGE_TAG=release-20260618-1006-slim-e2e`.
- Test server backend image: `intruoyi-backend:release-20260618-1006-slim-e2e`, state `running`.
- Test server frontend image: `intruoyi-frontend:release-20260618-1006-slim-e2e`, state `running`.
- Test server backend health: HTTP 200, body `{"status":"UP"}`.
- Test server frontend: HTTP 200.
- Test server PDF worker asset: HTTP 200, `application/javascript`.
- Required migration status records: `20260617_dcc_browser_performance_indexes`, `20260617_erp_kingdee_event_callback`, and `20260617_mes_scheduler_role_smart_scheduling_tab` are all `SKIPPED_ALREADY_APPLIED` for release `release-20260618-1006-slim-e2e` / environment `test`.
- Playwright browser entry smoke: `http://172.30.30.58:8081/` redirects to `/login?redirect=/index`, title `瑛泰管理系统 - 登录`, console error `0`, failed request `0`.

## Manual Approvals And Blockers

- User authorized deployment to the test server in this task.
- No approval is granted for backup or production servers.
- No CI/CD deployment blockers remain for the tested release.
- Deeper login-after-deploy E2E is blocked until a valid test-server `测试租户/aoteman` credential is confirmed; this was not part of the current deployment acceptance boundary.

## Rollback Procedure And Validation

- If test deployment fails, stop and record operation/log/remote state; do not deploy elsewhere.
- Application rollback, if needed, must be performed as a separate explicitly authorized rollback operation.
