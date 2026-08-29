# Verification Report

## Result

passed

## Scope

本次最终有效轮次为 `r260829j-r1`，仅执行测试服发布链路 `build-release -> publish-test`。未执行 `mark-tested`、`promote-prod`、`promote-backup`，未发布正式服或备份服。

## Frozen Inputs

- 维护仓目标提交：`24106b18eec879e87d5cdf8d79fa0a739e9120a6`
- IntRuoyi 目标提交：`3892f88f00d30aa06a4be6c5bd48f9e55ed6203c`
- 维护仓发布 worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829j\m`
- IntRuoyi 发布 worktree：`D:\IntRuoyiWorktree\r260829j\a`
- 状态目录：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829j-state`
- Git 状态：两个发布 worktree 均为 detached HEAD 且 clean；主工作区既有脏改动未进入构建输入。

## Build Evidence

- 维护控制台构建：`scripts\build.ps1` 通过，维护前端 typecheck/build 通过，维护后端 Maven tests `26` 通过。
- 维护控制台 JAR：`runtime-control-maintenance-2026.06-SNAPSHOT.jar`
- JAR SHA256：`3A93FEE01504C96194B7BF0461C14E6CB0B4FC33BF1FA8F2B6331FD29D18E945`
- build operation：`op-2026-08-29T074248158573400Z-4ec035f6-02a6-49ee-a41c-c598d4cd2cee`，`SUCCESS`
- 发布包目录：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260829-frozen-head-test-r260829j-r1`
- 镜像包 SHA256：`c33654398b5464687625e018aeb7d310ffbd31814dc108a5b109eb2d60eab8dd`
- manifest 校验：`manifest.json`、`release-manifest.json`、镜像 tar 均存在；`sourceRepos[*].commit=3892f88f00d30aa06a4be6c5bd48f9e55ed6203c`，`dirty=false`；`changeSet.summary=任务: 修复注册证CHECK精确表达式合同`。
- 官方 manifest validator：`MANIFEST_VALIDATION_PASSED`。

## Publish Evidence

- publish operation：`op-2026-08-29T080003811407100Z-9e826bd7-61ca-44e3-bc28-f8a3794035bb`，`SUCCESS`
- releaseTag：`release-20260829-frozen-head-test-r260829j-r1`
- 测试服远端 `.env IMAGE_TAG`：`release-20260829-frozen-head-test-r260829j-r1`
- 后端实际镜像：`intruoyi-backend:release-20260829-frozen-head-test-r260829j-r1`，container running
- 前端实际镜像：`intruoyi-frontend:release-20260829-frozen-head-test-r260829j-r1`，container running
- 后端健康检查：`{"status":"UP"}`
- 前端 HTTP：`200`
- 前端 `/release-info.json`：releaseTag、packageId、source commit、dirty=false、变更说明均匹配本轮构建。

## Page And Console Evidence

- 测试服前端页面：Playwright 打开 `http://172.30.30.58:8081/`，实际跳转登录页，标题 `瑛泰管理系统 - 登录`，页面可见 `瑛泰数字化平台`、`登录`、`记住我`。
- 测试服前端截图：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829j-state\playwright\test-frontend-login-r260829j.png`
- 运行控制台 API：`testCurrentReleaseTag=release-20260829-frozen-head-test-r260829j-r1`，变更说明为 `任务: 修复注册证CHECK精确表达式合同`。
- 运行控制台页面：Playwright 打开 `http://127.0.0.1:48195/`，点击 `查看变更` 后显示 releaseTag、发布包、组件范围和提交摘要。
- 运行控制台截图：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829j-state\playwright\runtime-console-release-notes-r260829j.png`

## Final Gate

`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829j-state\test-release-final-gate-r260829j-r1.json` 为 `status=passed`，检查项全部为 true：

- maintenanceWorktreeClean
- appWorktreeClean
- buildOperationSuccess
- publishOperationSuccess
- packageManifest
- officialManifestValidation
- remoteEnvImageTag
- remoteBackendImage
- remoteFrontendImage
- backendHealthUp
- frontendHttp200
- frontendReleaseInfo
- runtimeConsoleVersion
- runtimeConsoleNotes
- playwrightFrontendPage
- playwrightRuntimeConsole
- forbiddenProdBackupUntouched

## Closeout Evidence

- `task_closeout.py --mode preview`：`status=ready`，blocked/warnings 均为 `<none>`。
- `task_closeout.py --mode apply`：`status=applied`，任务目录保留 `task.md`、`execution-log.md`、`verification-report.md`。
- Playwright：默认浏览器已关闭。
- 临时运行控制台：本任务各轮 release worktree 下的 `runtime-control-maintenance-2026.06-SNAPSHOT.jar` Java 进程已停止，后置扫描无残留。
- 临时 release worktree：维护仓和 app 仓共 44 个本任务 release worktree 已清理；最终 `registeredCount=0`、`existingCount=0`、`processRefCount=0`。
- 状态目录：最终发布证据保留在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829j-state`，用于验收追溯；未保留运行中的任务进程或 worktree 注册。

## Acceptance Status

- 构建产物只包含当前分支 HEAD 已提交代码：通过。
- 测试服务器发布成功：通过。
- 测试服真实运行态检查通过：通过。
- 运行控制台显示当前版本号和变更说明：通过。
- 所有问题已记录：通过，详见 `execution-log.md` 问题 1-41。
- 发布成功后已沉淀为前置经验：通过，更新 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md` 和 `docs/experience-index.md`。
