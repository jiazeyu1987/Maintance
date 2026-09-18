# 正式发布按钮严格 TDD 计划

## Purpose and Scope

规定实现顺序必须为 RED → GREEN → REGRESSION。每一阶段只实现足以使当前行为转绿的最小正式方案，不允许 mock 成功、兼容 fallback 或跳过生产安全门禁。

## Evidence Reviewed

- BDD-PROD-001 至 BDD-PROD-B03。
- 现有 `ReleaseWorkflowOrchestratorTest`、`ReleaseWorkflowAuthorizationTest`、前端 one-button 静态合同和维护仓发布治理测试。

## TDD Sequence

1. 专用权限与请求白名单。
2. production eligibility/preview 数据模型和只读检查。
3. preview 快照持久化、过期和 target fingerprint。
4. 授权绑定 preview/stateVersion/fingerprint。
5. promote 请求幂等和活动 prod operation 冲突。
6. 派发前零写入失败与派发后 `RECOVERY_REQUIRED` 分类。
7. 最终证据全量判定，不能只凭 operation succeeded。
8. 前端按钮资格、preview 对话框、确认和监控。
9. 维护仓脚本参数/证据/锁合同。
10. 静态、组件、后端、脚本、测试服真实 E2E 和最终正式 E2E。

## RED Commands

以下是实现阶段建议命令，具体模块路径以最终基线为准；PowerShell 中每个 `-D...` 参数必须整体引用。

```powershell
# 后端 workflow/authorization/preview/permission 合同
mvn -pl yudao-module-infra -am '-Dtest=ReleaseWorkflowProductionPreviewTest,ReleaseWorkflowAuthorizationTest,ReleaseWorkflowOrchestratorTest,RuntimeControlProductionPermissionTest' '-Dsurefire.failIfNoSpecifiedTests=false' test

# 前端静态合同：新文件先断言按钮、preview API、专用权限、字段白名单和恢复态
node tests/e2e/runtime-control-prod-promotion-button-static.spec.cjs

# 维护仓发布治理与失败事务合同
python -m pytest scripts/tests/test_release_package_governance.py scripts/tests/test_release_deployment_transaction.py scripts/tests/test_runtime_control_frontend_deploy_contract.py -q
```

## Expected Failures

- RED-1：production endpoints 仍使用通用 `operate`，缺专用权限。
- RED-2：缺 `production-preview` API/响应和结构化 checks/blockers。
- RED-3：授权未绑定 previewId、stateVersion 和 targetFingerprint。
- RED-4：promote 请求缺 idempotencyKey、expectedStateVersion，重复提交可产生歧义。
- RED-5：低层 operation `succeeded` 可能直接推进 COMPLETED，缺独立最终证据合同。
- RED-6：当前前端直接 prompt → authorize → promote，未展示结构化 preview。
- RED-7：维护脚本/服务端需证明 prod dry-run evidence 与同一 workflow/digest 绑定。

## GREEN Commands

```powershell
# 复跑同一后端 RED 集，必须到达 Surefire 并全部 PASS
mvn -pl yudao-module-infra -am '-Dtest=ReleaseWorkflowProductionPreviewTest,ReleaseWorkflowAuthorizationTest,ReleaseWorkflowOrchestratorTest,RuntimeControlProductionPermissionTest' '-Dsurefire.failIfNoSpecifiedTests=false' test

# 前端合同、类型和生产构建
node tests/e2e/runtime-control-prod-promotion-button-static.spec.cjs
corepack pnpm ts:check
corepack pnpm build:prod

# 维护仓相同目标测试
python -m pytest scripts/tests/test_release_package_governance.py scripts/tests/test_release_deployment_transaction.py scripts/tests/test_runtime_control_frontend_deploy_contract.py -q
```

测试服真实验收和正式服真实验收必须分别取得明确授权后执行；命令不得预先硬编码在文档中携带凭据。

## Refactor Checks

- 旧通用 `promote-prod` 可见入口已移除或明确转为只读兼容合同，不能绕过 workflow。
- production target 只在服务端配置出现，前端无固定/可编辑 host。
- preview/authorization/operation 的绑定逻辑集中在明确服务，不散落于 Controller。
- 错误码稳定且无空 catch/默认成功。
- workflow store、preview store、authorization store 使用一致的原子写入和 schemaVersion 策略。
- 日志和响应不含 secret values。

## Evidence Log Template

```text
BDD: <scenario> -> Given/When/Then
RED: <exact command> -> FAIL, <expected missing behavior>
GREEN: <same command> -> PASS, <test count>
REGRESSION: <broader command> -> PASS, <test/build count>
GREEN: experience-preflight -> PASS, <authorized environment and boundaries>
E2E: <Playwright command> -> PASS/FAIL, workflowId=<redacted-safe-id>, operationId=<id>, releaseTag=<tag>
FINAL: operation=<status>, manifest=<digest>, env/image/health/http/page/lock=<results>
```

## Test Blockers

- 若最终实现基线仍未融合，不能在脏主工作区开始 RED；先建立独立实现 worktree 并记录目标提交。
- 无正式服明确授权时，所有真实 production 写入测试保持 blocked；不得用 mock 或 API-only 宣称通过。
- 缺正式测试包、tested 证明、恢复候选或生产配置时 fail fast。
