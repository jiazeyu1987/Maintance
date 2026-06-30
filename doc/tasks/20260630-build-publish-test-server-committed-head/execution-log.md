# 20260630 将 IntRuoyi 已提交 git 版本发布到测试服务器执行日志

GREEN: experience-preflight-20260630-build-publish-test-committed-head -> PASS，已读取并命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md` 与 `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`。已确认本轮只允许执行 `build-release -> publish-test -> 测试服运行态验证`，不推进 `mark-tested`、正式服或备份服。

GREEN: committed-head-initial-state-check-20260630 -> PASS，已核对当前主工作区状态：
- 维护仓 HEAD=`fd139bca838a43e76ea7a9b344ca7d82dfe9a4f1`，存在大量已跟踪修改与未跟踪文件
- 后端仓 HEAD=`ec6514ef24ccddd1c05eb751fb6a7ea2962fab5f`，存在大量已跟踪修改与未跟踪文件
- 前端仓 HEAD=`eb577ab5edb0009a0702e669f3c6fae0834ec2cb`，存在大量已跟踪修改与未跟踪文件
- 本机 runtime-control 健康检查 `http://127.0.0.1:48181/actuator/health` -> HTTP `200`
结论：主工作区当前不满足“只发布 git 已提交版本”的发布输入要求，必须继续核对并使用干净 worktree 隔离本次发布输入。

BLOCKER: runtime-control-switch-20260630 -> 新 maintenance clean worktree 初始不含 backend\\target\\runtime-control-maintenance-2026.06-SNAPSHOT.jar，直接切换 48181 失败；先在该 worktree 构建 runtime-control jar，再继续发布。

GREEN: runtime-control-clean-worktree-switch-20260630 -> PASS，已执行 `mvn -f D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260630-fd139bc\backend\pom.xml -DskipTests package` 生成 runtime-control jar，并将本机 `http://127.0.0.1:48181` 切换到 `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260630-fd139bc`；当前健康检查返回 HTTP `200`。

GREEN: committed-head-clean-worktree-preflight-20260630 -> PASS，已确认本轮发布输入仅来自干净 worktree：
- maintenance=`D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260630-fd139bc`
- backend=`D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260630-ec6514e`
- frontend=`D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260630-eb577ab`
- `runtime-control.local.yaml` 中 `repo-root` 与 `frontend-root` 已指向上述 backend/frontend clean worktree
- 后端迁移策略门禁 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=228`
- 前端依赖门禁 `pnpm install --frozen-lockfile` -> PASS

GREEN: experience-preflight-build-publish-test-committed-head-20260630 -> PASS，本轮高风险动作前已再次确认：只允许执行真实 `build-release -> publish-test`；发布范围固定测试服 `172.30.30.58`；禁止混入主工作区未提交改动、未跟踪文件、正式服或备份服动作。

BLOCKER: build-release-v1-noncompliant-maintenance-script-20260630 -> 首次 `build-release` 预览与执行虽然已切到 clean backend/frontend worktree，但 `scriptPath` 仍落在主维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\publish-int-ruoyi.ps1`；实进程 PID `76544` 已确认从主维护仓脚本启动，违反“只发布 Git 已提交版本”要求，因此主动中止本轮不合规构建。

GREEN: runtime-control-config-root-fix-20260630 -> PASS，已将 clean maintenance worktree 本机配置补齐 `website-root`、`ops-root`、`state-dir`，并重启本机 runtime-control；重新预览 `build-release` 后 `scriptPath` 已切换为 `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260630-fd139bc\ops\deploy\publish-int-ruoyi.ps1`，当前发布入口已满足 clean maintenance / backend / frontend 三仓均只取已提交 worktree 的要求。

GREEN: build-release-v2-preview-20260630 -> PASS，重新预览 `build-release` 后已确认：
- `scriptPath=D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260630-fd139bc\ops\deploy\publish-int-ruoyi.ps1`
- `-BackendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260630-ec6514e`
- `-FrontendRepoRoot D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260630-eb577ab`
- `publishScope=code-only`
- 包含 `-SkipDatabaseSync`、`-SkipMinioSync`
- 未混入主维护仓脚本路径

BLOCKER: build-release-v2-committed-head-testcompile-failure-20260630 -> 真实 `build-release` operation=`op-2026-06-30T010356130672500Z-b5e8545b-72bb-49b0-8cc2-ad0f93b4e9cd` 最终 `FAILED`；当前 clean backend 已提交 HEAD=`ec6514ef24ccddd1c05eb751fb6a7ea2962fab5f` 在 `yudao-module-dcc` 的 `testCompile` 阶段失败，具体为 `DccNasPermissionSnapshotCaptureServiceImplTest` 仍按旧签名构造 `NasConnectionConfig`，但当前已提交源码要求 6 个参数（含端口等），测试仅传了 4 个参数，导致 Maven 构建停止，发布包未生成，禁止进入 `publish-test`。关键信息：
- 文件：`D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260630-ec6514e\yudao-module-dcc\src\test\java\cn\iocoder\yudao\module\dcc\service\permission\DccNasPermissionSnapshotCaptureServiceImplTest.java`
- 失败位置：`[90,29]`、`[479,16]`
- 期望构造签名：`NasConnectionConfig(String, Integer, String, String, String, String)`
- 实际调用参数：`(String, String, String, String)`
- 影响：本轮无法生成合规 releaseTag，测试服发布未开始，正式服/备份服仍未触达。

GREEN: backend-committed-head-release-blocker-fix-20260630 -> PASS，已在 clean backend worktree `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260630-ec6514e` 完成最小修复并提交新版本 `bdf13bc3de04d5dcda9e76d6765c5bf3573696cc`，提交信息 `任务: 修复NAS配置发布构建阻塞`。定向验证：
- `mvn -pl yudao-module-dcc -Dtest=DccNasPermissionSnapshotCaptureServiceImplTest test` -> PASS
- `mvn -pl yudao-module-srm "-Dtest=SrmNasLocatorServiceTest,SrmSupplierPortalApprovalTaskAdapterTest" test` -> PASS
当前发布输入 backend 仍保持 clean worktree 路径不变，但其已提交 HEAD 已从 `ec6514ef24ccddd1c05eb751fb6a7ea2962fab5f` 前进到 `bdf13bc3de04d5dcda9e76d6765c5bf3573696cc`，下一步继续重发真实 `build-release`。

GREEN: build-release-v3-20260630 -> PASS，真实 `build-release` operation=`op-2026-06-30T012508646561400Z-465583a5-36f1-4fdb-abe2-8fd0c222aeaa` 最终 `SUCCESS`，releaseTag=`release-20260630-0940-committed-head-v3`；日志确认 backend Maven、frontend `pnpm build:test`、backend/frontend Docker 镜像构建、`docker save`、manifest 生成与 NAS 上传均完成。下一步进入真实 `publish-test` 与测试服六项运行态验收。

GREEN: publish-test-v3-20260630 -> PASS，真实 `publish-test` operation=`op-2026-06-30T014234251292100Z-47f360d4-e1e9-4bbd-89f4-8a8d9db21d22` 最终 `SUCCESS`；日志确认 required SQL 执行/登记完成、backend/frontend 容器重建成功、远端 HTTP readiness 通过、scheduler smoke runtime 检查通过、发布锁释放与远端临时文件清理完成。

GREEN: test-server-release-v3-runtime-verification-20260630 -> PASS，测试服六项验收通过：
- manifest=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260630-0940-committed-head-v3\manifest.json`
- manifest backend commit=`bdf13bc3de04d5dcda9e76d6765c5bf3573696cc`，frontend commit=`eb577ab5edb0009a0702e669f3c6fae0834ec2cb`，两者 `dirty=false`
- 测试服 `.env IMAGE_TAG=release-20260630-0940-committed-head-v3`
- 测试服运行镜像：
  - `intruoyi-backend|intruoyi-backend:release-20260630-0940-committed-head-v3`
  - `intruoyi-frontend|intruoyi-frontend:release-20260630-0940-committed-head-v3`
- `http://172.30.30.58:48081/actuator/health` -> HTTP `200` / `UP`
- `http://172.30.30.58:8081/` -> HTTP `200`
