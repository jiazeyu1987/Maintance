# 20260701 发布当前版本到正式服和备份服

## Task Goal

基于已在测试服验证成功的 `release-20260701-1720-current`，按完整发布链路继续执行 `mark-tested -> promote-prod -> promote-backup`，并完成正式服、备份服运行态验证。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 后端仓：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
- 前端仓：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
- ReleaseTag：`release-20260701-1720-current`
- 目标环境：正式服、备份服

## Non-Scope

- 不重新构建新 releaseTag
- 不拼接其他 releaseTag 的构建或测试服发布结果
- 不绕过 `mark-tested`

## 经验门禁

- `release-build-preflight-lessons.md`：完整发布只认单一 releaseTag，正式服/备份服发布前必须核预览参数与测试服成功证据。
- `release-agent-checklist.md`：执行顺序必须是 `build-release -> publish-test -> 测试服验证 -> mark-tested -> promote-prod -> 正式服验证 -> promote-backup -> 备份服验证`。
- `release-backup-restore.md`：正式服/备份服发布不得 mock、静默跳过或自动降级；缺 operation、manifest、镜像、health 任一证据不得判定完成。
- `server-access.md`：正式服默认禁止操作；本任务用户已明确要求发布正式服和备份服，因此授权范围仅限本 releaseTag 的正式服与备份服发布验证。
- `powershell-preflight-lessons.md`：PowerShell 5.1 不使用 `&&`，中文读写与输出必须显式 UTF-8。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；严格沿运行控制台发布链路推进。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

BDD: 只有测试服成功的 releaseTag 才能继续上线 -> Given `release-20260701-1720-current` 已完成测试服发布并通过运行态验证 When 用户要求发布正式服和备份服 Then 必须先执行 `mark-tested`，再按同一 releaseTag 发布正式服和备份服。

BDD: 正式服和备份服运行态必须与 releaseTag 一致 -> Given 发布 operation 成功 When 验证远端环境 Then `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health 与 frontend HTTP 必须全部与 `release-20260701-1720-current` 一致。

## Milestones

1. 建立任务台账并记录经验门禁。`COMPLETED`
2. 复核测试服成功证据与当前三仓状态。`PENDING`
3. 通过运行控制台真实执行 `mark-tested`。`PENDING`
4. 通过运行控制台真实执行 `promote-prod` 并验证正式服。`BLOCKED`
5. 通过运行控制台真实执行 `promote-backup` 并验证备份服。`BLOCKED`
6. 回填证据、closeout 预览并提交维护仓记录。`PENDING`

## Current Status

BLOCKED：promote-prod 已真实执行但失败，失败点为正式服 required SQL 20260613_dcc_file_view_matrix_seed.sql 执行 CALL apply_dcc_file_view_matrix_seed() 时触发 ERROR 1648 (HY000): Data too long for condition item 'MESSAGE_TEXT'。正式服发布未完成，按发布门禁禁止继续执行备份服发布；需先修复该 required SQL 的 MESSAGE_TEXT 过长契约，并重新走同一 releaseTag 发布链路。
