# “发布到正式服务器”后端与 API 设计

## Purpose and Scope

在现有 `ReleaseWorkflowOrchestrator` 上补齐结构化 production preview、专用权限、幂等提交、preview/授权绑定和最终证据判定。继续复用现有工作流、一次性授权、环境 lease、operation store 和 `promote-prod` 执行器。

## Evidence Reviewed

- `RuntimeControlController` 已有 workflow 创建、列表、测试发布、测试验收、production authorization、promote-prod 和详情端点。
- `ReleaseWorkflowAuthorizationService` 已绑定 workflow/releaseTag/package/manifest/preset/scope，默认授权有效 15 分钟并使用文件锁消费一次。
- `ReleaseWorkflowOrchestrator.startProductionPromotion` 已先验证 TESTED、授权和生产 lease，再派发 `promote-prod`；派发或授权消费后的异常会进入 `RECOVERY_REQUIRED`。
- `publish-int-ruoyi.ps1` 已校验 `PROD`、测试 operation evidence、tested 证明和 prod dry-run evidence。
- 当前所有写端点仍使用通用 `infra:runtime-control:operate`，且没有面向 workflow 的结构化 preview API。

## Modules

- `RuntimeControlController`：HTTP 权限与参数边界。
- `ReleaseWorkflowOrchestrator`：状态机、顺序、幂等、lease 和失败分类。
- `ReleaseWorkflowProductionPreviewService`（新增）：只读 eligibility 检查、preview 快照和 target fingerprint。
- `ReleaseWorkflowAuthorizationService`：一次性授权；扩展绑定 preview ID、target fingerprint 和预期 stateVersion。
- `RuntimeControlService`：低层 action preview/execute 和 operation 管理。
- `OperationEvidenceValidator` / 发布治理模块：验证测试 operation、tested.json、manifest 和最终证据。
- `publish-int-ruoyi.ps1`：正式部署执行，服务端传入受控参数，不接受浏览器参数。

## API Contracts

### 1. 获取工作流

`GET /admin-api/infra/runtime-control/release-workflows`

- 权限：`infra:runtime-control:query`。
- 响应应增加 `productionEligibility` 摘要：`eligible`、`primaryBlockerCode`、`primaryBlockerMessage`、`activeOperationId`。
- 摘要仅用于展示；不能代替点击时的实时 preview。

### 2. 创建正式发布只读预检

`POST /admin-api/infra/runtime-control/release-workflows/{workflowId}/production-preview`

- 权限：`infra:runtime-control:promote-prod`。
- 请求：

```json
{
  "reason": "本次正式发布原因",
  "expectedStateVersion": 12
}
```

- 禁止额外字段；尤其禁止 releaseTag、targetEnvironment、host、path、script 和 evidence path。
- 响应：

```json
{
  "previewId": "prod-preview-...",
  "workflowId": "rw-...",
  "expectedStateVersion": 12,
  "releaseTag": "release-...",
  "packageDigest": "...",
  "manifestDigest": "...",
  "targetEnvironment": "prod",
  "targetDisplayName": "正式服务器",
  "targetHost": "172.30.30.57",
  "currentProdReleaseTag": "release-old",
  "testOperationId": "op-...",
  "testedBy": "user-id",
  "testedAt": "...",
  "testConclusion": "...",
  "targetFingerprint": "sha256:...",
  "eligible": true,
  "checks": [
    {"code": "PACKAGE_DIGEST", "status": "PASS", "message": "...", "evidenceRef": "..."}
  ],
  "blockers": [],
  "createdAt": "...",
  "expiresAt": "..."
}
```

- preview 有效期建议 10 分钟；不得超过授权有效期。
- 该 API 必须零写入远端环境；可以持久化本机 preview 审计文件。

### 3. 签发一次性正式授权

`POST /admin-api/infra/runtime-control/release-workflows/{workflowId}/production-authorization`

- 权限：`infra:runtime-control:promote-prod`。
- 请求：`previewId`、`reason`、`expectedStateVersion`。
- 服务端从认证上下文取得 approver；不接受客户端 approver。
- 仅 preview eligible、未过期、target fingerprint 未变化且 workflow 仍为同一 `TESTED` stateVersion 时签发。
- 响应沿用授权对象并增加 `previewId`、`targetFingerprint`；不返回 nonce 或内部路径。

### 4. 提交正式发布

`POST /admin-api/infra/runtime-control/release-workflows/{workflowId}/promote-prod`

- 权限：`infra:runtime-control:promote-prod`。
- 请求：

```json
{
  "reason": "本次正式发布原因",
  "previewId": "prod-preview-...",
  "authorizationGrantId": "grant-...",
  "prodConfirmText": "PROD",
  "expectedStateVersion": 12,
  "idempotencyKey": "uuid"
}
```

- 服务端再次执行轻量关键校验：preview/授权/工作流绑定、preview 未过期、target fingerprint、生产写开关、权限、lease 和活动 operation。
- 返回 `202` 语义的 workflow/operation 信息；已有相同幂等操作时返回该 operation。
- 未知字段 fail fast；服务端内部注入 releaseTag、test operation evidence、固定 prod 目标和 preassigned operation ID。

### 5. 查询进度和日志

沿用 workflow detail、operation list/detail/log 接口。响应增加结构化 `currentStage`、`stageStartedAt`、`lastProgressAt`、`durationSeconds`、`zeroWriteEvidence`、`recoveryRequired` 和最终验证清单。

## Error Model

| 错误码 | HTTP/业务语义 | 处理 |
|---|---|---|
| `RELEASE_WORKFLOW_NOT_TESTED` | 409 | 保持 TESTED 前一状态，不预检 |
| `RELEASE_WORKFLOW_PROMOTION_EVIDENCE_MISSING` | 409 | 补齐测试/摘要证据 |
| `PRODUCTION_PREVIEW_BLOCKED` | 409 | 返回结构化 blockers，零远端写入 |
| `PRODUCTION_PREVIEW_STALE` | 409 | 重新预检 |
| `PRODUCTION_PREVIEW_BINDING_MISMATCH` | 409 | 拒绝，审计异常 |
| `PRODUCTION_WRITE_DISABLED` | 403/409 | 禁止创建 operation |
| `PROD_CONFIRM_REQUIRED` | 400 | 精确输入 PROD |
| `AUTHORIZATION_*` | 409 | 不自动重试，重新预检/授权 |
| `RELEASE_WORKFLOW_LEASE_CONFLICT` | 409 | 返回活动 operation ID |
| `RELEASE_WORKFLOW_IDEMPOTENCY_CONFLICT` | 409 | 同 key 不同请求拒绝 |
| `RELEASE_WORKFLOW_FIELD_NOT_ALLOWED` | 400 | 拒绝客户端拥有字段 |
| `RECOVERY_REQUIRED` | 409 | 阻止新发布，进入恢复流程 |

错误消息必须可诊断但不得包含秘密、完整命令行、连接串或凭据。

## Transactions and Idempotency

正式提交的顺序固定：

1. 校验权限、请求白名单、workflow TESTED 和 expectedStateVersion。
2. 校验 preview 与授权绑定、有效期及 target fingerprint。
3. 用 `workflowId + targetEnvironment + idempotencyKey` 查询已有 operation。
4. 获取本机/服务端 prod lease；失败时零写入并保持 TESTED。
5. 预分配 operation ID，原子写入 workflow 的 `PROD_PREVIEW` 和操作绑定。
6. 消费一次性授权；从此失败不能默认视为零写入。
7. 进入 `PROMOTING_PROD` 并派发低层 action。
8. 低层脚本在第一次远端写入前取得远端生产锁。
9. 后台 reconcile 读取 operation 与结构化阶段；最终证据全 PASS 才进入 `COMPLETED`。
10. 授权已消费、派发已发生、远端锁已取得或状态未知时，异常统一进入 `RECOVERY_REQUIRED` 并保留 lease/锁。

preview 失败、确认错误、授权签发前失败或 lease 获取失败且能证明零写入时，workflow 保持 `TESTED`。禁止把这些前置拒绝写成终态 `FAILED`。

## Open Questions

- preview 快照持久化沿用 JSON 文件还是进入发布治理数据库；首版建议沿用原子 JSON store，并增加 schemaVersion 与清理策略，以匹配现有工作流持久化。

## Design Blockers

- 当前候选 API/状态机未融合到 `int_main`。
- 缺 `production-preview` 服务和响应模型。
- 授权记录尚未绑定 preview/target fingerprint/stateVersion。
- promote-prod 请求尚无 idempotency key 与 expectedStateVersion。
- workflow 成功推进目前主要依赖低层 operation `succeeded`，需确认低层成功是否已包含所有最终运行态证据；未证明前不得直接 `COMPLETED`。
