# 20260701 排程日期产能覆盖根因修复发布到测试服务器执行日志

GREEN: experience-preflight -> PASS，已读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md` 与 `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`，确认本轮只允许执行 `build-release -> publish-test -> 测试服运行态验证`，不推进 `mark-tested`、正式服或备份服。

BDD: 只发布根因修复的已提交版本 -> Given 后端根因修复已提交且主工作区仍存在无关脏改 / When 执行测试服发布 / Then 发布输入必须锁定三仓 clean worktree，manifest 中后端 commit 应等于本次根因修复提交，且所有 sourceRepos 为 dirty=false。

BDD: 测试服运行态必须落到同一 releaseTag -> Given build-release 成功生成新的 releaseTag / When 执行 publish-test / Then 测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health 与 frontend HTTP 必须全部与该 releaseTag 一致。

GREEN: committed-head-clean-worktree-preflight -> PASS，已确认本轮 committed-only 发布输入：
- maintenance=`D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260701-dfb317e`，HEAD=`dfb317e8474ff1cc0b65b8063e00e85588649d46`
- backend=`D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260701-b0d401a`，HEAD=`b0d401af1eba3a71befc3c8b5d07552a3425ed85`
- frontend=`D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260701-c8f87af`，HEAD=`c8f87af720535115c233bf894e957471d68cc667`
- clean maintenance `config/runtime-control.local.yaml` 已切到上述 backend/frontend worktree，且 `ops-root/state-dir` 也已指向 clean maintenance 自身路径
- 后端迁移策略门禁 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=233`
- 前端依赖门禁 `pnpm install --frozen-lockfile` -> PASS
- clean maintenance `mvn -f backend\\pom.xml -DskipTests package` -> PASS

GREEN: runtime-control-clean-worktree-switch -> PASS，已停止旧 48181 主维护仓实例，并从 `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260701-dfb317e\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 以 `--spring.config.import=optional:file:D:/ProjectPackage/Int/release-worktrees/IntRuoyiMaintance-20260701-dfb317e/config/runtime-control.local.yaml` 重启本机运行控制台；`http://127.0.0.1:48181/actuator/health` 返回 `UP`，当前运行 PID=`65056`。

GREEN: build-release-preview -> PASS，`POST /admin-api/infra/runtime-control/actions/preview` 已确认：
- `scriptPath=D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260701-dfb317e\ops\deploy\publish-int-ruoyi.ps1`
- `-BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260701-b0d401a`
- `-FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260701-c8f87af`
- `releaseTag=release-20260701-capacity-horizon-v1`
- `publishScope=code-only`
- 包含 `-SkipDatabaseSync` 与 `-SkipMinioSync`

GREEN: build-release -> PASS，真实 `build-release` operation=`op-2026-06-30T171835232169700Z-d8d1ebbb-3274-4ddb-97e6-a50f13bdbb57` 最终 `SUCCESS`，`releaseTag=release-20260701-capacity-horizon-v1`；日志确认 backend Maven、frontend `pnpm build:test`、backend/frontend Docker 镜像构建、`docker save`、manifest 生成与 NAS 上传均已完成。

GREEN: build-release-manifest-check -> PASS，已只读核对 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260701-capacity-horizon-v1\manifest.json`：
- backend commit=`b0d401af1eba3a71befc3c8b5d07552a3425ed85`，`branch=HEAD`，`dirty=false`
- frontend commit=`c8f87af720535115c233bf894e957471d68cc667`，`branch=HEAD`，`dirty=false`
- `publishScope=code-only`
- 当前候选包满足继续真实 `publish-test` 的 committed-only 门禁。

GREEN: backend-release-contract-fix-20260701 -> PASS，后端已补上正式发布链路阻断修复：
- 业务根因修复提交=`b0d401af1eba3a71befc3c8b5d07552a3425ed85`，解决未来日期正式产能覆盖自动续期
- 发布契约修复提交=`1b364a2fe8d458deb14ba322bdeb1af5394d83f6`，解决 `20260630_mes_pro_work_order_erp_snapshot_fields.sql` 在测试服重复发布时的幂等性
- 定向验证 `python -X utf8 -m pytest script/tests/test_mes_work_order_erp_snapshot_fields_sql.py script/tests/test_release_migration_metadata_sql_20260630.py -q` -> PASS
- 发布迁移门禁 `python -X utf8 script/release/run-release-migration-policy-gate.py --sql-root sql/mysql` -> PASS

GREEN: build-release-preview-v2 -> PASS，`POST /admin-api/infra/runtime-control/actions/preview` 已确认：
- `scriptPath=D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260701-dfb317e\ops\deploy\publish-int-ruoyi.ps1`
- `-BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260701-1b364a2`
- `-FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260701-c8f87af`
- `releaseTag=release-20260701-capacity-horizon-v2`
- `publishScope=code-only`
- 包含 `-SkipDatabaseSync` 与 `-SkipMinioSync`

GREEN: build-release-v2 -> PASS，真实 `build-release` operation=`op-2026-06-30T180856412443100Z-e35aa0c2-d701-4bcb-99df-9e9540fe61ea` 最终 `SUCCESS`，`releaseTag=release-20260701-capacity-horizon-v2`；日志确认 backend Maven、frontend `pnpm build:test`、backend/frontend Docker 镜像构建、`docker save`、manifest 生成与 NAS 上传均已完成。

GREEN: build-release-manifest-check-v2 -> PASS，已只读核对 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260701-capacity-horizon-v2\manifest.json`：
- backend commit=`1b364a2fe8d458deb14ba322bdeb1af5394d83f6`，`branch=HEAD`，`dirty=false`
- frontend commit=`c8f87af720535115c233bf894e957471d68cc667`，`branch=HEAD`，`dirty=false`
- `publishScope=code-only`
- 当前候选包满足继续真实 `publish-test` 的 committed-only 门禁。

GREEN: publish-test-preview-v2 -> PASS，已通过运行控制台 action preview 确认测试服发布请求锁定：
- `action=publish-test`
- `targetEnvironment=test`
- `releaseTag=release-20260701-capacity-horizon-v2`
- 预览参数包含 `-Mode deploy-release -Environment test -ServerHost 172.30.30.58 -RemoteAppDir /opt/intruoyi/runtime`

GREEN: publish-test-submit-v2 -> PASS，真实 `publish-test` 已提交，operation=`op-2026-06-30T183226445474300Z-f8e7e47e-c07d-4d7b-98bf-8ca8b9ed4ea2`，当前状态=`RUNNING`；下一步只读轮询 required SQL、容器重建、HTTP readiness、runtime smoke 与 `LOCK_RELEASED`。

GREEN: publish-test-v2 -> PASS，真实 `publish-test` operation=`op-2026-06-30T183226445474300Z-f8e7e47e-c07d-4d7b-98bf-8ca8b9ed4ea2` 最终 `SUCCESS`；日志确认：
- required SQL 全量下发与执行完成，`20260630_mes_pro_work_order_erp_snapshot_fields.sql` 本轮未再出现重复加列阻断
- backend/frontend `docker compose up -d --no-deps` 容器重建成功
- `http://127.0.0.1:48081/actuator/health` 与 `http://127.0.0.1:8081/` remote readiness 通过
- scheduler smoke runtime 检查通过
- 发布锁成功 `LOCK_RELEASED`
- 远端临时文件清理完成，日志末尾输出 `Publish completed for test.`

GREEN: test-server-runtime-validation-v2 -> PASS，测试服 `172.30.30.58` 已完成只读运行态验收：
- `/opt/intruoyi/runtime/.env` -> `IMAGE_TAG=release-20260701-capacity-horizon-v2`
- `docker compose ps --format json` -> `intruoyi-backend:release-20260701-capacity-horizon-v2`、`intruoyi-frontend:release-20260701-capacity-horizon-v2`，且两者状态均为 `Up`
- `http://172.30.30.58:48081/actuator/health` -> `{"status":"UP"}`
- `http://172.30.30.58:8081/` -> `HTTP 200`

INFO: runtime-control-frontend-entry-gap -> 当前 clean maintenance worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260701-dfb317e` 的仓库受 `.gitignore` 规则 `/backend/src/main/resources/static/` 影响，运行中的 `runtime-control-maintenance-2026.06-SNAPSHOT.jar` 不包含静态前端资源，导致 `http://127.0.0.1:48181/` 根路径返回 404，仅 API 端点可用。本次测试服发布已通过受控 action 成功完成，但该问题会影响后续“必须从页面按钮触发”的正式路径，应作为独立维护仓契约问题收口。
