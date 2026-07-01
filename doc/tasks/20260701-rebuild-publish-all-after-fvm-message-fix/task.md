# 20260701 修复后重新构建并发布到测试/正式/备份服务器

## Task Goal

基于后端已提交的 DCC 文件视图矩阵 MESSAGE_TEXT 限长修复，重新构建新的发布包 ${releaseTag}，并按单一 releaseTag 完成 uild-release -> publish-test -> mark-tested -> promote-prod -> promote-backup 全链路，最终验证测试服、正式服、备份服运行态一致。

## Scope

- 维护仓：D:\ProjectPackage\Int\IntRuoyiMaintance
- 后端仓：D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro
- 前端仓：D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3
- ReleaseTag：${releaseTag}
- 目标环境：测试服、正式服、备份服

## 经验门禁

- elease-build-preflight-lessons.md：每次修复前置条件后使用新的 releaseTag 重跑构建；失败半成品只作为排障证据。
- elease-agent-checklist.md：完整发布必须严格按 uild-release -> publish-test -> 测试服验证 -> mark-tested -> promote-prod -> 正式服验证 -> promote-backup -> 备份服验证 执行。
- elease-backup-restore.md：发布不得 mock、静默跳过或自动降级；缺 manifest、operation、镜像、health 任一证据不得判定完成。
- server-access.md：本轮用户明确授权发布测试服、正式服、备份服；正式服/备份服只允许本 releaseTag 范围内发布验证。
- worktree-memory.md：发布必须使用临时发布 worktree 与目标提交，不把主工作区脏改混入发布包。
- powershell-preflight-lessons.md：PowerShell 5.1 不使用 &&；中文读写与输出必须显式 UTF-8。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；任一发布或验证门禁失败即阻塞。
- 是否从根因和长期维护角度解决：是；使用已提交 SQL 契约修复后重新构建发布包。
- 是否存在临时补丁或绕过：否；不手工改远端库或服务器绕过 required SQL。

## BDD 场景

BDD: 修复后必须重新构建新 releaseTag -> Given 旧 releaseTag 的正式服 required SQL 因 MESSAGE_TEXT 过长失败 When SQL 修复已提交 Then 必须构建新的 ${releaseTag}，不得继续使用失败旧包。

BDD: 单一 releaseTag 必须完成三环境发布闭环 -> Given ${releaseTag} 构建成功并发布测试服 When 测试服验证通过 Then 才能 mark-tested，并继续发布正式服和备份服。

BDD: 三环境运行态必须与 releaseTag 一致 -> Given 发布 operation 成功 When 验证远端环境 Then .env IMAGE_TAG、backend/frontend 镜像 tag、backend health 与 frontend HTTP 必须全部与 ${releaseTag} 一致。

## Milestones

1. 建立任务台账并记录经验门禁。COMPLETED
2. 复核修复提交、发布 worktree 与构建包状态。COMPLETED
3. 执行/确认 uild-release 并校验 manifest。IN_PROGRESS
4. 执行/确认 publish-test 并验证测试服。PENDING
5. 执行 mark-tested。PENDING
6. 执行 promote-prod 并验证正式服。PENDING
7. 执行 promote-backup 并验证备份服。PENDING
8. 回填证据、closeout 预览并提交维护仓记录。PENDING

## Current Status

IN_PROGRESS：已完成 MES 排产员角色修复的发布 worktree、运行控制台切换与后端/前端前置验证；已修复 DCC 发布对象清单污染、本机 DCC MinIO 历史对象缺失、NAS 中文共享名被 CLI 参数覆盖，以及 DCC 对象清单使用 PowerShell 数组 `+=` 导致大清单阶段无进度且疑似挂起的问题。当前旧失败/中止 releaseTag 均已废弃；下一步使用新的 releaseTag 重新执行 build-release，并继续单一 releaseTag 的测试服、正式服、备份服闭环。

## 追加门禁

- DCC 对象清单只覆盖正式业务引用表；临时上传表不得作为发布必需对象来源。
- 本机 MinIO 中 DCC `infra_file` 已引用对象必须真实存在；缺失时必须从可追溯历史快照恢复并记录 hash，不得静默跳过或改用 code-only。
- 本轮 blocker 修复后必须使用新 releaseTag 重跑 build-release，旧失败包仅保留排障证据。
- NAS 发布共享名必须以 UTF-8 配置文件为准；命令行 `NasShare` 参数若因进程调用发生乱码，不得覆盖配置文件中的中文共享名。
- DCC 对象清单生成必须使用线性追加集合并输出进度；不得在大清单场景使用 PowerShell 数组 `+=` 造成二次复杂度和无进度长时间静默。
