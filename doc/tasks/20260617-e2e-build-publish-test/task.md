# 任务: 真实 E2E 构建并发布到测试服务器

## 任务目标

通过运行控制台前端真实 E2E 操作构建 IntRuoyi code-only 发布包，并发布到测试服务器。

目标边界：

- 目标环境：测试服。
- 目标主机：`172.30.30.58`。
- 远端目录：`/opt/intruoyi/runtime`。
- 前端地址：`http://172.30.30.58:8081/`。
- 后端健康检查：`http://172.30.30.58:48081/actuator/health`。
- 发布范围：`code-only`，即 `-Component intruoyi -SkipDatabaseSync -SkipMinioSync`。
- 不访问正式服 `172.30.30.57`，不访问备用服 `172.30.30.59`，不执行备份、恢复、回滚或正式发布。

## 经验门禁

- `docs/experience-index.md`：涉及发布、服务器写入和真实 E2E，执行高风险动作前必须在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：构建发布包必须通过运行控制台前端按钮提交；提交前必须预览命令并确认 `code-only`、`-SkipDatabaseSync`、`-SkipMinioSync`、目标环境和禁止正式服动作；发布成功必须以 operation、manifest、远端 `.env`/镜像 tag 和健康检查共同证明。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：本次用户已明确授权测试服发布；服务器动作仅限 `172.30.30.58` 和 `/opt/intruoyi/runtime`，不得写入凭据，优先使用仓库封装脚本/运行控制台。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`：真实 E2E 前先验证登录或运行控制台入口；测试服验证使用真实前端路径，登录失败必须报告实际入口、租户、账号和影响。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。缺少运行控制台、发布包 manifest、测试服访问、登录凭据或验证证据时直接阻塞。
- `是否从根因和长期维护角度解决`：是。通过既有运行控制台前端路径提交构建和发布 operation，以 manifest、operation、远端状态和真实页面验证闭环。
- `是否存在临时补丁或绕过`：否。本任务不修改生产代码；命令行仅用于前置只读检查和最终验证，不代替前端发布操作。

## BDD 场景

- `BDD: 真实 E2E 构建发布到测试服 -> Given 本机运行控制台可访问且目标为测试服 172.30.30.58, When 操作者通过前端预览并执行 code-only 构建发布包后再执行发布到测试服, Then 构建和发布 operation 均成功，发布包 manifest 与远端 IMAGE_TAG 一致，测试服后端健康且管理前端真实路径可访问。`
- `BDD: 禁止越界环境 -> Given 本次任务只授权测试服, When 执行构建、发布和验证, Then 不得提交 targetEnvironment=prod，不得访问 172.30.30.57 或 172.30.30.59，不得执行备份、恢复、回滚或正式服动作。`

## 里程碑

- [x] 创建任务目录与任务文档。
- [x] 完成前置只读检查并记录 `experience-preflight`。
- [x] 启动或确认本机运行控制台，验证前端 E2E 入口。
- [x] 用 Playwright 真实操作预览并执行 code-only 构建发布包。
- [x] 校验发布包 manifest 与候选状态。
- [x] 用 Playwright 真实操作发布到测试服务器。
- [x] 校验测试服远端 `.env`/镜像 tag、后端健康和管理前端真实路径。
- [x] 更新执行日志、请求命令记录和最终状态。

## 预期验证

- `npx` 可用。
- 本机运行控制台健康检查通过。
- Playwright 真实页面可见运行控制台。
- 构建预览包含 `-SkipDatabaseSync`、`-SkipMinioSync`，不包含 `promote-prod`、正式服 IP、备份、恢复、回滚动作。
- 构建 operation `SUCCESS`，发布包 manifest 存在且 `publishScope=code-only`。
- 发布测试服 operation `SUCCESS`。
- 远端 `.env` 或等效配置 `IMAGE_TAG=<releaseTag>` 与发布 manifest 一致。
- `http://172.30.30.58:48081/actuator/health` 返回健康。
- `http://172.30.30.58:8081/` 可通过真实浏览器访问，必要时完成真实登录路径。

## 最终验证

- `GREEN: build-release-operation-sixth -> PASS`，发布包 `release-20260617-1654-codeonly-e2e` 构建成功并上传至 `Backup/ReleasePackage/release-20260617-1654-codeonly-e2e`。
- `GREEN: release-package-available -> PASS`，运行控制台发布包列表显示 `publishScope=code-only`、`component=intruoyi`、`checksumPresent=true`、`status=AVAILABLE`。
- `GREEN: deploy-operation -> PASS`，测试服部署 operation `op-2026-06-17T090710635870700Z-11dabe12-ebbe-4311-98da-00b614aec4ec` 成功。
- `GREEN: remote-image-tag -> PASS`，测试服 `/opt/intruoyi/runtime/.env` 为 `IMAGE_TAG=release-20260617-1654-codeonly-e2e`。
- `GREEN: remote-health -> PASS`，`http://172.30.30.58:48081/actuator/health` 返回 `{"status":"UP"}`，`http://172.30.30.58:8081/` 返回 HTTP 200。
- `GREEN: remote-migration-status -> PASS`，测试服迁移 `20260617_dcc_browser_performance_indexes` 状态为 `APPLIED`。
- `GREEN: remote-playwright-entry -> PASS`，Playwright 真实打开测试服前端并加载登录页；未执行远端登录，因为 `login-access.md` 未提供远端测试服账号。
- `GREEN: task-closeout-cleanup-apply -> PASS`，仅清理本任务两个临时日志。
- `GREEN: independent-verification-gate -> PASS`，`verification-report.md` 已按构建包、测试服发布、远端 tag、容器、健康检查、迁移状态和真实浏览器入口完成独立验收。

## Cleanup Candidates

- `doc/tasks/20260617-e2e-build-publish-test/runtime-control-start.out.log`
- `doc/tasks/20260617-e2e-build-publish-test/runtime-control-start.err.log`

清理结果：已删除。

## Cleanup Keep

- `doc/tasks/20260617-e2e-build-publish-test/verification-report.md`

## Current Status

completed

## 当前状态

completed

已完成。
