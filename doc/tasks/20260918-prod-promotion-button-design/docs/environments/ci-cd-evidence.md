# CI/CD 与环境交付证据：已测试包晋级正式服按钮

## Environments and Deployment Targets

- local：开发、合同测试和隔离 preview；不访问远端服务器。
- test：测试服务器 `172.30.30.58`，用于真实 `build-release -> publish-test -> mark-tested` 和按钮资格验收。
- prod：正式服务器 `172.30.30.57`，仅在独立明确授权、生产窗口和恢复负责人就绪后执行 `promote-prod`。
- backup/audit：审查服务器 `172.30.30.59`，本按钮不操作，不自动 `promote-backup`。

正式目标 host、远端目录、数据盘、release root、MinIO 容器和健康 URL 只能来自服务端运行配置。前端不传这些字段。

## Build, Test, Lint, Package, Deploy, and Rollback Commands

实现阶段的标准验证意图：

```powershell
# 后端核心行为
mvn -pl yudao-module-infra -am '-Dtest=ReleaseWorkflowProductionPreviewTest,ReleaseWorkflowAuthorizationTest,ReleaseWorkflowOrchestratorTest,RuntimeControlProductionPermissionTest' '-Dsurefire.failIfNoSpecifiedTests=false' test

# 前端合同、类型和构建
node tests/e2e/runtime-control-prod-promotion-button-static.spec.cjs
corepack pnpm ts:check
corepack pnpm build:prod

# 维护发布治理
python -m pytest scripts/tests/test_release_package_governance.py scripts/tests/test_release_deployment_transaction.py scripts/tests/test_runtime_control_frontend_deploy_contract.py -q
```

真实发布不在本文执行。未来实施必须通过运行控制台工作流：同一 releaseTag 完成 `build-release -> publish-test -> mark-tested -> promote-prod`。禁止手工拼接服务器命令、跳过 preview 或重新构建已测试包。

回滚命令不预设为自动动作：

- 明确零写入失败：保持正式服原版本，无需回滚。
- 部分/未知写入失败：进入 `RECOVERY_REQUIRED`，先执行现场检查；只有数据库兼容性和恢复计划确认后才选择应用回滚、前滚或数据恢复。

## Pipeline Files Changed

本设计任务只新增 `doc/tasks/20260918-prod-promotion-button-design/` 下的文档，未修改 pipeline 或生产代码。

后续实现预计影响但尚未授权修改：

- 应用后端 runtime-control Controller、VO、workflow、authorization、preview/store 和测试。
- 应用前端 runtime-control 页面、API 类型和静态/真实 E2E。
- 维护仓发布脚本/治理测试，必要时增加最终证据和 target fingerprint 合同。
- 新的菜单权限 migration。

## Required Secrets and Owners

- SSH、MySQL、MinIO、NAS、通知等 secret references；owner 为运行环境/运维负责人。
- production write switch 与正式环境配置；owner 为发布平台主管或被授权运维负责人。
- 页面和任务日志只验证引用存在性或脱敏 fingerprint，不记录值。
- 缺任何必要 secret ref/owner 时 preview BLOCKED。

## Artifact and Release Output

- 发布制品：测试服已验证的同一 NAS 不可变 release package。
- 身份：releaseTag + package digest + manifest digest + source tuple + preset。
- 测试证明：publish-test operation evidence + PASS acceptance + tested proof。
- 正式证明：production preview + authorization + promote operation + final verification evidence。
- 不生成新的生产专用构建包，不修改原包。

## RED Evidence for New Config Checks

实施阶段预期先失败：

- 缺 `infra:runtime-control:promote-prod` 专用权限。
- 缺 production preview endpoint/check model。
- 授权未绑定 preview/stateVersion/target fingerprint。
- promote 请求缺 idempotency key。
- 最终 COMPLETED 可能只依赖低层 operation succeeded。

这些缺口必须用后端、前端和维护仓合同测试先得到 RED，不得通过手工操作验证替代。

## GREEN Verification Evidence

设计阶段验证：产品、系统、acceptance 和本 CI/CD 证据文档通过对应结构验证器和交叉一致性检查。

实现阶段必须保存：

- 精确 RED/GREEN/REGRESSION 命令与测试数。
- 本地不可变包和安装演练证据。
- 测试服 operation/manifest/env/image/health/HTTP/page/tested proof。
- 经授权正式发布的 preview、grant、operation、env/image/health/HTTP/page/lock。
- 审查服未被触发的只读证据。

## Manual Approvals and Blockers

- 文档编写不授权正式服访问或写入。
- 真实 prod preview 即使只读也需要当前任务正式服访问授权。
- 真实 promote-prod 需要单独明确授权、生产窗口、恢复负责人、有效 TESTED workflow 和全部 preview PASS。
- 前序 R93 候选实现尚未合入 `int_main`，实现基线是当前主要工程 blocker。
- 任何 blocker 不得以 mock、静默跳过、手工改台账或切换环境规避。

## Rollback Procedure and Validation

1. preview/授权/lease 前失败：证明零写入，工作流保持 TESTED。
2. 授权消费、operation 派发、生产锁取得或状态未知：进入 `RECOVERY_REQUIRED`，保留隔离。
3. 现场核对正式 `.env`、实际镜像、容器、迁移台账、release lock、health、HTTP 和业务兼容性。
4. 由恢复负责人选择继续前滚、应用回滚或独立数据恢复；不自动回滚业务数据。
5. 恢复后再次核验所有运行态和页面证据，审计通过后才能释放锁。
