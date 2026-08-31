# 20260831 当前 HEAD 仅测试服发布验证报告

## Status

completed

## Verification Summary

- Frozen source: maintenance `ed282ac4d1bff57ba9320191bab948f21d5e5e6e`、app `58479242435efa1f7eafd6e0a17e36bd9c811e5f`；两个 release worktree tracked clean。
- Build: `release-20260831-frozen-head-test-r260831a-r1` 的 build operation SUCCESS，耗时 1872.633s。
- Package: 官方 validator `MANIFEST_VALIDATION_PASSED`，artifactCount=555、requiredSql=548；manifest 与 frontend image release-info 均绑定 app 冻结 commit、dirty=false、summary=`docs: 记录不合格评审主线融合结果`。
- Publish: operation `op-2026-08-30T181715327908800Z-09fe2159-482a-4211-beac-03d01dd4e554` FAILED。
- Root cause: code-only target preflight `BLOCKED_SCOPE_DEPENDENCY=1`；schema `20260830_mes_batch_record_report_project_code` 依赖尚未 APPLIED 的 data `20260829_mes_old_form_template_binding_switch`。
- Semantic audit: 目标 schema 仅添加 `mes_pro_batch_record_report.project_code`，与旧表单绑定 data 迁移无数据依赖；真实表创建迁移 `20260514_mes_batch_record_report` 已 APPLIED。当前 dependsOn 应作为代码/元数据缺陷正式修复，不应通过 with-data 扩大发布范围绕过。
- Failure state: `.env` 已指向失败 r1，实际 backend/frontend 仍运行上一版本 `release-20260830-invoice-assistant-test-r260830k-r1`，backend health=UP、frontend HTTP=200、release lock=FAILED、RUNNING=0、本轮 migration count=0。
- Boundary: 未执行 `mark-tested`、`promote-prod`、`promote-backup`，未操作正式服/备份服，未手工改 SQL/迁移台账/release lock/`.env`。

## Blocker Impact

验收标准中的“测试服务器发布成功”“测试服真实运行态为本轮版本”“运行控制台显示本轮版本和变更说明”“成功后经验沉淀与 closeout”尚未满足。本轮 r1 已判废，必须在正式解除 data 前置后使用新 releaseTag 重建。

## Authorized Resolution

用户已授权精确恢复测试服 `.env`、正式修正错误 dependsOn、提交新 HEAD，并用新 releaseTag 重建/发布。历史 blocked 证据保留，当前状态恢复为 `in_progress`。

## R260831B Build Evidence

- Frozen source: maintenance `ed282ac4`、app `c3a134a7`，两 worktree clean。
- Build operation: `op-2026-08-31T024323515301800Z-795a60df-e388-4a13-aeff-2caf1e26d2f6` SUCCESS。
- Manifest validator: passed，errors=0、warnings=0。
- Version/notes: releaseTag 与 summary=`任务: 修正批记录项目代码迁移依赖`，sourceRepos commit=`c3a134a7`、dirty=false。
- Prepublish code-only plan: status=passed、blockedCount=0、project_code action=APPLY。

## Final Verification Summary

- 成功 releaseTag：`release-20260831-cell-link-idempotency-test-r260831c-r1`。
- 冻结输入：maintenance `ed282ac4`、app `735f6978`，worktree clean，manifest sourceRepos dirty=false。
- Build operation：`op-2026-08-31T041314765504800Z-b1fc20d9-91a1-4658-8360-86dccead48d6` SUCCESS。
- Publish operation：`op-2026-08-31T053012842131200Z-9cafc46c-e123-4da6-88c1-f5ec4c85acb7` SUCCESS。
- Package：官方 validator passed，版本号、提交和变更说明一致。
- Runtime：`.env`、compose/actual images、containers、backend UP、frontend 200、release-info 全部匹配。
- Ledger：lock APPLIED、APPLIED=10、SKIPPED=485、FAILED/RUNNING=0；三个目标 migration APPLIED。
- Console：release-status API 与 Playwright 查看变更对话框显示正确 tag、summary、component、commit。
- Browser：Playwright 1.60.0，测试服登录页与运行控制台页面 PASS，console/page/request errors=0。
- Scope：仅测试服；没有 mark-tested/promote-prod/promote-backup。
- Final gate：28/28 true。

## Closeout Evidence

- task-closeout preview/apply 两轮均通过，最终只保留 task/execution/verification。
- 任务自有运行控制台已停止，48181 无监听。
- 8 个 worktree Git 注册和物理路径均不存在；fix branches 已融合。
- Slot 58/59 active=false，端口无监听。
- r260831a/b/c state 与 Playwright 临时输出已清理；正式 release package 保留。
- 清理后测试服运行态与 ledger 仍通过。
- App 两个修复任务已 completed，最终收尾 commit=`7ad8cde64`；共享 index.lock 自然消失，未删除锁或中断并发任务。
- 主任务 closeout 全部通过，最终状态 completed。
- Maintenance commit boundary: 混合 dirty 的 release-build/checklist/request-log 与依赖其未提交目标的 index 保持未暂存；核心任务记录、test-release 和 PowerShell preflight 可安全独立提交。

## Required Evidence

- 冻结提交与 clean worktree
- 构建 operation、package、manifest、版本号、变更说明
- publish-test operation
- 测试服镜像、容器、健康、HTTP、release lock/migration
- 运行控制台 API 与 Playwright 页面版本说明
- 正式服/备份服未触碰边界
- 问题清单、经验沉淀与 closeout 证据

## Evidence Collected

- `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260831a-state\evidence\migration-policy-gate.json`
- `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260831a-state\evidence\build-release-operation-final-r1.json`
- `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260831a-state\evidence\manifest-validation-r1.json`
- `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260831a-state\evidence\frontend-image-release-info-r1.json`
- `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260831a-state\evidence\publish-test-operation-final-r1.json`
- `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260831-frozen-head-test-r260831a-r1\preflight-plan.json`
- `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260831-frozen-head-test-r260831a-r1\preflight-target-state-test.json`
- `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260831a-state\evidence\publish-failure-ledger.tsv`
