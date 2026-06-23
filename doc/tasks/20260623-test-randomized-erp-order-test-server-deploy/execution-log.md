# Execution Log: 测试服发布随机 ERP 建单改动

## BDD 场景

BDD: 只发布本次测试改动到测试服 -> Given 干净 release worktree 已重放本次前后端提交 / When 运行控制台页面执行构建发布包并部署测试服 / Then 测试服只切到包含本次随机 ERP 建单改动的新 releaseTag。

BDD: 发布输入必须与干净 worktree 一致 -> Given 页面预览发布命令 / When 运行控制台生成 build-release 和 deploy-test 命令 / Then 命令必须指向本次干净 worktree，而不是主仓其他未提交现场。

BDD: 测试服验证必须暴露真实运行态 -> Given 测试服部署完成 / When 核对运行态 / Then `.env`、镜像和页面都必须显示新 releaseTag，且后端健康与前端入口可用。

## 执行证据

- 2026-06-23：已读取 `experience-index.md`、`release-build-preflight-lessons.md`、`project-error-prevention.md`、`release-backup-restore.md` 与 `server-access.md`。
- 2026-06-23：只读确认测试服当前 `IMAGE_TAG=20260623_dcc_content_recognition_gateway_timeout_fix_1`；本地缓存 manifest 显示当前测试服基线为 backend `23c596d1e2ba97ef06b4854b53e80b0e88ec25ed`、frontend `4ed836cf016975fa6cca74d99b152b9b5ee3891c`。
- 2026-06-23：创建发布专用 clean worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean` 与 `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean`，分支同为 `codex/20260623-test-randomized-erp-order-release`。
- GREEN: backend-release-worktree -> PASS，后端 release worktree 已仅重放本次代码改动，提交 `aa13420c67513224bebe114d090f0cfffb8388ab`，`mvn -pl yudao-module-mes clean -Dtest=MesKingdeeProductionOrderCreateServiceImplTest test` 通过。
- GREEN: frontend-release-code -> PASS，前端 release worktree 已仅重放本次代码改动，提交 `e301a67af7acca887c60d1625d34b87d17409e9f`，`node tests/e2e/workorder-create-erp-order-static.spec.js` 与 `pnpm ts:check` 通过。
- GREEN: experience-preflight -> PASS，用户已明确批准把 frontend release worktree 的 `pnpm-lock.yaml` 修复一起带入本次测试服 `code-only` 发布；发布范围仍限制为页面真实 `build-release -> deploy-test`，不进入 `mark-tested/prod/backup`。
- GREEN: page-build-release-preview -> PASS，页面预览命令确认 `-Mode build-release -ReleaseTag release-20260623-random-erp-test-v1 -Component intruoyi -SkipDatabaseSync -SkipMinioSync`，且 `-BackendRepoRoot/-FrontendRepoRoot` 指向本次 clean release worktree。
- GREEN: page-build-release-submit -> PASS，页面真实提交 `build-release`，operation=`op-2026-06-23T072156013940200Z-4e4291e1-3c74-4f26-8cda-8c116760c505` 初始状态 `RUNNING`。
- GREEN: build-release-operation -> PASS，`op-2026-06-23T072156013940200Z-4e4291e1-3c74-4f26-8cda-8c116760c505` 最终 `SUCCESS`；发布包目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260623-random-erp-test-v1\` 已生成 `manifest.json`、`release-manifest.json`、`docker-compose.yml`、`runtime-env/`、`resources/`、`required-sql/`、镜像 tar。
- GREEN: build-release-manifest -> PASS，manifest 记录 backend `aa13420c67513224bebe114d090f0cfffb8388ab`、frontend `e301a67af7acca887c60d1625d34b87d17409e9f`，`publishScope=code-only`；frontend `dirty=true` 对应用户明确批准带入的 `pnpm-lock.yaml` 修复。
- GREEN: page-deploy-test-preview -> PASS，页面预览命令确认 `-Mode deploy-release -Environment test -ReleaseTag release-20260623-random-erp-test-v1 -ServerHost 172.30.30.58 -RemoteAppDir /opt/intruoyi/runtime`，且仍指向本次 clean release worktree。
- GREEN: page-deploy-test-submit -> PASS，页面真实提交 `deploy-test`，operation=`op-2026-06-23T074133159825800Z-f54c26d2-d986-42bb-8c53-485f509c8c06` 初始状态 `RUNNING`。
- GREEN: deploy-test-operation -> PASS，`op-2026-06-23T074133159825800Z-f54c26d2-d986-42bb-8c53-485f509c8c06` 最终 `SUCCESS`；日志确认 required SQL 传输、远端发布目录同步、`backend/frontend` 容器重建和 HTTP readiness 全部通过。
- GREEN: deploy-test-runtime-verify -> PASS，测试服 `/opt/intruoyi/runtime/.env` 已切到 `IMAGE_TAG=release-20260623-random-erp-test-v1`；`docker compose ps` 显示 `intruoyi-backend` 和 `intruoyi-frontend` 均为新 tag 且 `Up`；`http://172.30.30.58:48081/actuator/health` 返回 `{"status":"UP"}`，`http://172.30.30.58:8081/` 返回 HTTP `200`。
