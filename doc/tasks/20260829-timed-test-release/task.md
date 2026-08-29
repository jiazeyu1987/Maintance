# 20260829 带分段耗时统计的仅测试服真实发布

## Task Goal

基于当前已提交 HEAD 执行一次仅测试服真实发布，采集 `build-release -> publish-test -> 测试服运行态/页面/版本说明验证` 的分段耗时，判断前几轮发布链路优化后的实际耗时分布；发布输入必须来自本轮专用 clean release worktree 的已提交内容。

## Milestones

1. 启动门禁与任务文档：记录目标、BDD、验收边界、经验门禁和计时采集方式。
2. 发布前置复核：读取发布/服务器/worktree/login 文档，确认目标提交、releaseTag、临时 worktree、脚本命令和远端目标。
3. build-release 计时执行：在本轮专用 release worktree 运行构建并采集分段耗时证据。
4. publish-test 计时执行：对同一 releaseTag 执行仅测试服发布并采集分段耗时证据。
5. 测试服真实运行态验证：核 operation=SUCCESS、manifest、远端 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200、页面版本说明。
6. 报告与收尾：汇总分段耗时、瓶颈判断、优化建议、清理任务自有 worktree/临时产物并记录证据。

## Expected Verification

- BDD: Given 当前已提交 HEAD 和本轮专用 release worktree，When 执行仅测试服真实发布，Then 同一 releaseTag 必须完成 `build-release -> publish-test` 并通过真实运行态/页面/版本说明验证。
- 分段耗时必须至少覆盖：准备/前置检查、release worktree 创建、build-release 总耗时、publish-test 总耗时、远端运行态验证、收尾清理。
- 若可从 operation/log 中安全解析阶段时间，再补充构建、上传、required SQL、服务启动、health wait 等更细分数据。
- 验收缺任一项必须 fail fast，不得口头判定成功。
- 不执行 `mark-tested`、`promote-prod`、`promote-backup`，不操作正式服/备份服。

## 经验门禁

- Trigger: 仅测试服真实发布、current HEAD release、build-release/publish-test、运行态验收与耗时统计。
- Preflight check: 发布输入必须来自本轮专用 clean release worktree 的已提交 HEAD；先读取发布、服务器、登录、worktree、PowerShell 和测试服发布经验文档；高风险动作前在执行日志记录 `GREEN: experience-preflight -> PASS`。
- Blocker: release worktree 不是目标提交、runtime-control 配置仍指向旧工作区、releaseTag 被占用、存在 RUNNING/FAILED 状态未解释、manifest/operation/远端 `.env`/实际镜像/health/frontend HTTP/页面版本说明任一缺失时停止。
- Verification: 同一 releaseTag 完成 `build-release -> publish-test`，并核 operation=SUCCESS、manifest、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200、页面版本说明和分段耗时证据。
- Forbidden action: 禁止使用未提交改动、复用旧 release worktree、拼接多轮 releaseTag 结果、修改 release worktree 临时绕过、执行 `mark-tested`/`promote-prod`/`promote-backup`、记录明文凭据或 raw secret log。
- Evidence: `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\powershell-memory.md`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## Current Status

completed

## Milestone Status

1. 启动门禁与任务文档：completed。已创建任务文档、记录 BDD 与经验门禁。
2. 发布前置复核：completed。固定维护仓 HEAD `eb1193f1e3dec75ed87cb01a10464a05e2e91d60`、IntRuoyi HEAD `3892f88f00d30aa06a4be6c5bd48f9e55ed6203c`，创建本轮 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829k\m` 与 `D:\IntRuoyiWorktree\r260829k\a`。
3. build-release 计时执行：completed。r1 因 clean app worktree 缺少 `node_modules\.bin\cross-env.cmd` 失败并作废；恢复前端依赖后，r2 `build-release` 成功。
4. publish-test 计时执行：completed。同一 r2 releaseTag `release-20260829-timed-head-test-r260829k-r2` 的 `publish-test` 成功。
5. 测试服真实运行态验证：completed。operation、manifest、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health、frontend HTTP、release-info、release-status 和 Playwright 页面版本说明均通过。
6. 报告与收尾：completed。耗时汇总已生成；本轮 runtime-control 进程与端口已停止，任务自有 maintenance/app release worktree 已从 Git 登记和物理目录中清理完成，并已沉淀可复用发布耗时经验。

## Cleanup Keep

- doc/tasks/20260829-timed-test-release/timing.ndjson
- doc/tasks/20260829-timed-test-release/timing-summary.json
- doc/tasks/20260829-timed-test-release/timing-summary.md
