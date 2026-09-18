# “发布到正式服务器”前端设计

## Purpose and Scope

在现有运行控制台“标准程序发布”区域提供独立的“发布到正式服务器”按钮，并以服务端工作流为唯一事实来源完成资格展示、只读预检、生产确认、进度监控和恢复阻断展示。

## Evidence Reviewed

- 候选页面 `src/views/infra/runtime-control/index.vue` 已有工作流选择器、“发布测试服”“晋级正式服”和 TESTED 判断。
- 候选 API 已有 workflow、test acceptance、production authorization 和 promote-prod 调用。
- 当前 `requestProdReleaseWorkflow` 在一个函数中直接 prompt、签发授权、执行晋级；缺少结构化 preview 页面和 stale snapshot 绑定。
- `FRONTEND_STYLE.md` 是后续实际 UI 修改的统一样式基线；本文不实施 UI。

## Pages and Routes

- 保持现有运行控制台路由和页面：`src/views/infra/runtime-control/index.vue`。
- 不新增独立正式发布路由，避免从工作流上下文中跳出。
- 标准程序发布区域的动作顺序固定为：生成程序安装包 → 发布测试服 → 测试验收 → 发布到正式服务器。
- 旧通用运维 action 区不得再暴露另一套可绕过工作流的 `promote-prod` 入口。

## Components

### ProductionPromotionButton

- 文案固定“发布到正式服务器”。
- 危险级样式，按钮始终可见。
- enabled 条件来自服务端 eligibility 摘要，不由前端仅凭 `state === TESTED` 自行推断。
- disabled 时提供可聚焦说明和首要 blocker。

### ProductionPreviewDialog

分为四个区块：

1. 身份：workflowId、releaseTag、package/manifest digest、源码提交。
2. 测试证明：测试 operation、验收人/时间/结论、测试服当前版本。
3. 正式目标：正式服务器、当前正式版本、变更/迁移摘要、恢复准备。
4. 检查结果：逐项 PASS/BLOCKED、证据时间、下一步建议。

所有检查 PASS 后才显示原因输入、`PROD` 输入和“确认发布到正式服务器”按钮。

### ProductionProgressPanel

- 展示 operation ID、workflow 状态、当前结构化 stage、持续时间、最后进展时间。
- 提供刷新和查看脱敏日志入口。
- 页面重载后按 workflow/operation 恢复，不依赖浏览器状态。
- `RECOVERY_REQUIRED` 时显示醒目的隔离提示和独立恢复入口，不显示“重试发布”。

## State and Data Flow

1. 页面加载 `GET /release-workflows`，选择工作流。
2. 页面读取服务端可操作能力与 blocker 摘要。
3. 点击按钮调用 `POST /release-workflows/{id}/production-preview`。
4. preview PASS 后打开确认框；用户填写原因和 `PROD`。
5. 页面调用 production authorization，随后调用 promote-prod；两个请求都携带 preview ID，promote 请求另带 authorization ID、stateVersion 和 idempotency key。
6. 页面取得 operation 后清空 `PROD` 输入，不在 localStorage/sessionStorage/日志保留。
7. 页面轮询或使用既有状态刷新机制读取 workflow/operation，直到 `COMPLETED`、`FAILED` 或 `RECOVERY_REQUIRED`。

前端不得发送 `releaseTag`、package digest、manifest digest、targetEnvironment、host、path、script、testOperationId 或 evidence path；这些全部由服务端从 workflow 和配置解析。

## Error States

- `WORKFLOW_NOT_TESTED`：提示先完成测试验收。
- `PRODUCTION_PREVIEW_BLOCKED`：展示逐项 blockers，不允许确认。
- `PRODUCTION_PREVIEW_STALE`：关闭可提交状态并要求重新预检。
- `PROD_CONFIRM_REQUIRED`：保留对话框，提示精确输入 `PROD`。
- `AUTHORIZATION_*`：清除授权 ID，要求重新预检/授权，不自动重试。
- `RELEASE_WORKFLOW_LEASE_CONFLICT`：展示现有活动 operation 链接。
- `RECOVERY_REQUIRED`：切换为恢复提示，禁用所有新发布动作。
- 网络断开：只提示连接失败；不得假定 operation 未创建。恢复连接后先查询 workflow/operation，再决定页面状态。

## Accessibility and Responsive Behavior

- 按钮、阻断提示、检查项和最终确认输入必须有明确 label/aria-label。
- disabled 原因不能只靠 tooltip；必须在按钮附近以文本显示。
- 状态不能只用颜色表达，必须带 PASS/BLOCKED/RECOVERY_REQUIRED 文本和图标。
- 对话框支持键盘浏览，但危险确认不能通过 Enter 在输入不完整时误提交。
- 小屏幕改为纵向区块；digest 允许换行和复制，不横向撑破页面。

## Open Questions

- 是否在首版显示正式服务器完整 IP；本文默认显示固定目标名和 IP，因其已是内部受控运维信息，但绝不显示凭据。

## Design Blockers

- 候选前端位于未融合分支，实际修改前必须确定基线。
- 后端尚未提供结构化 production preview/eligibility 响应，前端不能先行用本地判断模拟 PASS。
- 专用 `infra:runtime-control:promote-prod` 权限尚未进入权限响应，按钮权限 E2E 暂不可验收。
