# Execution Log

## BDD

- BDD: DCC 受控浏览 viewer 权限 -> Given 测试服 `芋道源码/wangsiyu` 具备 `dcc:project-code:query` 和 `dcc:controlled-file:query` 但不具备 `form:instance:create` 与 `dcc:controlled-file:signature:manage`，When 用户从 DCC 项目代码关联文件进入受控文件 viewer，Then 仅加载受控预览所需接口，不触发管理态表单实例接口或电子签名管理接口，页面不出现“没有该操作权限”。

## Evidence

- GREEN: package-build -> PASS，`build-release.out.log` 记录 Maven reactor `BUILD SUCCESS`、`pnpm build:test` 成功、后端镜像 `intruoyi-backend:release-20260723-dcc-viewer-permission-r260723vp-r1` 与前端镜像 `intruoyi-frontend:release-20260723-dcc-viewer-permission-r260723vp-r1` 构建成功，并上传 NAS `Backup/ReleasePackage/release-20260723-dcc-viewer-permission-r260723vp-r1`。
- GREEN: manifest-contract -> PASS，本地发布包 `manifest.json` 校验 `releaseTag=release-20260723-dcc-viewer-permission-r260723vp-r1`、`publishScope=code-only`；`release-manifest.json` 校验 `component=intruoyi`；`sourceRepos` 为后端 `2d7fabf8263f3a5410f334bd177ea492e06b098b dirty=false`、前端 `4c6c01e824c0af5dca9df082141449ef1402ca03 dirty=false`。
- GREEN: publish-test-runtime -> PASS，测试服 `.env IMAGE_TAG=release-20260723-dcc-viewer-permission-r260723vp-r1`；`intruoyi-backend` 与 `intruoyi-frontend` 运行镜像均为该 tag；后端 health 返回 `{"status":"UP"}`；前端首页 HTTP `200`。
- GREEN: pdf-worker-runtime -> PASS，测试服 `/pdfjs/pdf.worker.mjs` 返回 `200 application/javascript`。
- GREEN: login-preflight -> PASS，官方 `login-preflight.mjs` 使用测试服 `芋道源码/wangsiyu` 进入 `/dcc/controlled-file/detail/2054545668044081212`，密码已脱敏记录。
- GREEN: controlled-viewer-probe -> PASS，`probe-preview-headers-result.json` 记录 `/preview-metadata` HTTP `200` / `code=0`，`/preview` HTTP `200` / `application/pdf`，`nonSuccessApiResponses=[]`，`pageMessages=[]`，`previewLayoutVisible=true`。
- GREEN: controlled-viewer-assertions -> PASS，`assert-controlled-viewer-result.json` 记录 `loginOk=true`、`permissionBaselineOk=true`、`previewMetadataOk=true`、`previewPdfOk=true`、`noActiveInstanceCall=true`、`noSignatureManagePageCall=true`、`noRoundedControlledFileId=true`、`noUnauthorizedMessage=true`、`noFailedAdminApi=true`、`previewLayoutVisible=true`。
- GREEN: cleanup-release-worktrees -> PASS，`git worktree list` 已不再包含 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260723vp\m`、`...\b`、`...\f`；物理目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260723vp` 已不存在。
- GREEN: cleanup-secret-config -> PASS，本次手工 NAS 配置 `runtime/runtime-control/nas-release-config/manual-20260723-dcc-viewer-permission-build.json` 已删除，未写入任务证据或提交范围。
- GREEN: experience-consolidation -> PASS，已按 `project-experience-consolidation` 检查；本轮发布超时不重复提交、worktree 物理残留清理、DCC viewer 只读权限隔离均已有 `docs/release-backup-restore.md`、`docs/worktree-memory.md`、`docs/powershell-memory.md` 和 `docs/agent-memory/project-error-prevention.md` 覆盖，不新增长期经验文档。

## Notes

- 本地前台发布命令超过等待窗口后，未重复提交；随后只读回查确认发布脚本进程退出且测试服运行态已切换到目标 releaseTag。
- 发布和 E2E 均未执行 `mark-tested`、备份服发布、正式服发布、备份或恢复。
