# 正式发布按钮数据与状态模型

## Purpose and Scope

定义正式发布工作流、预检快照、一次性授权、operation 和证据之间的不可变绑定。模型只保存脱敏标识和证据引用，不保存凭据或秘密配置值。

## Evidence Reviewed

- 现有 `ReleaseWorkflowRecord` 使用原子 JSON 持久化，包含 stateVersion、operationId、摘要、测试 operation 和 source tuple。
- 现有 `ReleaseAuthorizationGrant` 使用原子 JSON 和文件锁，具备有效期、撤销和消费时间。
- 现有 operation store、环境 lease 和远端 release lock 分别承担执行记录与互斥。

## Entities

### ReleaseWorkflow

沿用现有字段，并确保以下字段可持久化和审计：

- `workflowId`
- `releaseTag`
- `publishScope=app-release`
- `presetId` / `presetVersion`
- `sourceSelectionId`
- maintenance/application/frontend commit
- `state` / `stateVersion` / `attempt`
- `packageDigest` / `manifestDigest`
- `testOperationId` / `testOperationEvidencePath`
- `operationId`
- `currentStage` / `stageStartedAt` / `lastProgressAt`
- `zeroWriteEvidence`
- `errorCode` / `failedStage` / `retryable`
- `evidenceRefs`
- `requestedBy` / `reason` / timestamps

### ProductionEligibilitySnapshot

新增短时只读快照：

- `schemaVersion`
- `previewId`
- `workflowId` / `expectedStateVersion`
- `releaseTag` / packageDigest / manifestDigest
- `testOperationId` / tested evidence digest
- `targetEnvironment=prod`
- `targetConfigVersion`
- `targetFingerprint`：正式服当前版本、锁、关键挂载/配置和迁移计划摘要的稳定哈希
- `checks[]`：code、status、message、evidenceRef、sampledAt
- `blockers[]`
- `eligible`
- `createdBy` / `createdAt` / `expiresAt`

### ReleaseAuthorizationGrant

在现有授权上增加：

- `previewId`
- `expectedStateVersion`
- `targetFingerprint`
- `reasonDigest`
- `consumedOperationId`

继续保留 workflow/releaseTag/package/manifest/target/preset/scope/approver/issuedAt/validUntil/revokedAt/consumedAt 绑定。nonce 仅存服务端，不返回前端。

### RuntimeControlOperation

- `operationId`
- `idempotencyKeyDigest`
- workflow/releaseTag/target/action 关联
- `requestedBy` / requestedAt
- `status`
- `currentStage` / `lastProgressAt`
- 脱敏 summary / resultLogPath
- `remoteLockId` 或证据引用
- 最终验证结果引用

### ProductionVerificationEvidence

- operation status
- manifest/package digest
- `.env IMAGE_TAG` 摘要
- backend/frontend 实际镜像 tag
- 容器状态
- backend health
- frontend HTTP
- release-info/page releaseTag
- environment lock/operation lock 状态
- checkedAt / checker version / evidence refs

## Relationships

- 一个 ReleaseWorkflow 对应一个不可变 source tuple 和发布包身份。
- 一个 workflow 可产生多个过期/阻断 preview，但同时最多一个未过期 eligible preview。
- 一个 eligible preview 可签发一个或多个未消费授权尝试，但成功消费后其余授权必须撤销；首版可简化为同时只允许一个有效授权。
- 一个 workflow/环境同时最多一个活动 production operation。
- 一个 production operation 必须引用一个已消费授权和同一 preview。
- `COMPLETED` 必须引用一份全部 PASS 的 ProductionVerificationEvidence。

## State Models

核心状态沿用：`TEST_DEPLOYED -> TESTED -> PROD_PREVIEW -> PROMOTING_PROD -> COMPLETED`，异常包含 `FAILED`、`CANCELED`、`RECOVERY_REQUIRED`。

约束：

- preview 是只读实体，创建 preview 不改变 workflow 状态。
- `TESTED -> PROD_PREVIEW` 仅在最终再校验、lease 获取、operation 预分配成功后发生。
- `PROD_PREVIEW -> PROMOTING_PROD` 发生在授权消费与派发边界。
- `PROMOTING_PROD -> COMPLETED` 需要低层 operation 成功且最终证据全 PASS。
- 派发/消费/写入后的失败不能转换回 `TESTED`。
- `RECOVERY_REQUIRED` 不允许通过普通按钮转换；只能由独立恢复审计流程处置。

## Migration Notes

- 增加 workflow/authorization JSON `schemaVersion`，使用显式迁移器升级旧记录；禁止对缺失安全字段静默填默认值。
- 老 `TESTED` 工作流若缺 test evidence digest、可信 acceptedBy/acceptedAt 或 source tuple，应标记不可晋级，不得通过兼容 fallback 放行。
- 新增专用菜单权限需要新 SQL migration；实施前必须以目标真实库 `DESCRIBE system_menu` 和现有 permission 唯一性查询为准，不修改已执行历史迁移。
- preview/audit 文件采用原子写入和受控保留策略；临时文件不得落在 release worktree 导致源码 dirty。

## Data Integrity Rules

1. packageDigest 与 manifestDigest 必须成对存在且为标准 SHA-256。
2. workflow、preview、grant、operation 的 releaseTag/digest/preset 必须完全一致。
3. 任何 grant 只能消费一次，并记录 consumedOperationId。
4. idempotency key 的同一摘要只能绑定同一请求身份；同 key 不同请求拒绝。
5. targetEnvironment 固定 `prod`，target config 版本与 fingerprint 必须匹配。
6. workflow stateVersion 采用 compare-and-set；陈旧页面不能覆盖新状态。
7. secrets、密码、token、私钥、连接串和完整 `.env` 禁止进入这些实体。
8. `COMPLETED` 必须具有完整最终证据引用；不能只靠 operation exit code。

## Open Questions

- preview/授权审计的保留期限应与 operation 历史一致；具体天数由运维保留策略确定，不在本文虚构。

## Design Blockers

- 旧候选记录是否都包含可信 TESTED 证据需要实现阶段扫描；不满足的记录必须阻断而不是自动升级。
- 专用 permission 的实际 menu ID/role binding 必须通过真实库前置查询确定。
