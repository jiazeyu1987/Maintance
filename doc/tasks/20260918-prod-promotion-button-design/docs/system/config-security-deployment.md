# 正式发布按钮配置、安全与部署设计

## Purpose and Scope

定义正式发布按钮所需的受控配置、秘密边界、权限、生产安全控制、部署门禁、监控和恢复边界。

## Evidence Reviewed

- 正式服务器固定为 `172.30.30.57`，运行目录 `/opt/intruoyi/runtime`。
- 测试与正式环境默认数据根、release 根和数据盘参数由服务器文档定义。
- `productionWriteEnabled` 当前默认关闭；一次性授权已经检查该开关。
- 发布脚本已要求 `ConfirmText=PROD`、测试证据和 production dry-run evidence。
- 项目规则禁止在日志、任务文档或提交中保存凭据和完整 secret-bearing 输出。

## Configuration

服务端配置至少包含：

- `release-workflow.production-write-enabled=false`（默认）。
- `release-workflow.preset-id` / `preset-version`。
- approved source tuple 配置或正式的服务端 source selection 解析。
- preview TTL、authorization TTL、heartbeat timeout、lease TTL。
- prod 环境固定 host、server user、remote app dir、release root、data root、data disk mount/device、MinIO 容器和健康检查 URL。
- NAS release root。
- secret references，而不是 secret values。
- 最终验证探针和通知配置。

配置启动时 fail fast 校验；缺 host、路径、secret ref、preset 或生产写配置时服务不可提供 eligible preview。

## Secrets

- SSH、数据库、MinIO、NAS、TLS、通知等秘密只从受控 secret store/本机受保护配置引用。
- API、preview、workflow、grant、operation、日志和页面不返回秘密值。
- 只记录 secret reference 的存在性、版本或脱敏 fingerprint。
- 浏览器不得传密码、私钥、连接串或任意环境变量。
- 原始 operation 日志若含秘密必须保留在受限运行目录，提交证据前先脱敏；含明文凭据的文件不得提交。

## Permissions

- `infra:runtime-control:query`：查看工作流、preview 结果、operation 和脱敏日志。
- `infra:runtime-control:operate`：非生产通用运维动作；不足以执行正式晋级。
- `infra:runtime-control:promote-prod`（新增）：production preview、production authorization、promote-prod。
- 后端每个 production endpoint 必须单独校验专用权限，前端权限仅用于体验，不作为安全边界。
- 操作者身份只取服务端认证上下文。
- 首版不强制双人审批；授权和执行仍分别审计。

## Security Controls

1. 服务端字段白名单和未知字段拒绝。
2. 固定正式目标，客户端不可覆盖环境、host、path 或脚本。
3. TESTED、摘要、test operation、preset 和 source tuple 强绑定。
4. 短时 preview 和一次性授权；提交前重新验证 target fingerprint。
5. 精确 `PROD` 服务端确认。
6. expectedStateVersion、幂等键、prod lease 和远端发布锁共同防并发。
7. 首次远端写入前获取统一远端锁；重启后先恢复未完成 workflow。
8. 零写入与部分写入分类；部分/未知写入保持隔离。
9. 不自动回滚业务数据；应用回滚前必须证明数据库兼容性。
10. CSRF、认证、审计日志和现有安全框架继续生效。

## Deployment

实现和放行顺序：

1. 在独立开发 worktree 中先实现后端 RED/GREEN：preview、permission、binding、idempotency、failure classification。
2. 实现前端静态合同和交互，不连接真实正式服。
3. 同步维护仓脚本/合同测试，验证低层参数和最终证据。
4. 在合并结果上运行后端、前端和维护仓回归。
5. 用新的 releaseTag 构建不可变包并完成本地真实安装包演练。
6. 只发布测试服，通过真实页面完成 workflow、测试验收和按钮资格验证。
7. 在未授权正式写入时只允许离线/隔离的 production preview 合同测试；不得探测正式服。
8. 取得单独正式发布授权、生产窗口和恢复负责人确认后，才运行真实正式服 E2E。
9. 成功后不自动发布审查服。

回滚策略：

- 实现发布前：代码回滚使用 Git 任务提交；不处理业务数据。
- 正式发布零写入失败：保持旧正式版本并修复前置条件。
- 已写入失败：进入 `RECOVERY_REQUIRED`；根据现场检查决定应用回滚、继续前滚或独立数据恢复，禁止按钮自动猜测。

## Observability

- 指标：preview PASS/BLOCKED 数、promote 请求数、幂等命中、阶段耗时、最后进展年龄、成功/失败/恢复态数。
- 日志：workflowId、operationId、releaseTag、stage、errorCode、evidence ref；全部脱敏。
- 告警：生产 operation 失败、心跳超时、远端锁遗留、`RECOVERY_REQUIRED`、最终证据不一致。
- 页面：当前步骤、持续时间、最后进展、阻断原因和负责角色。
- 通知：SUCCESS、FAILED、RECOVERY_REQUIRED 各终态一次；轮询或重启不得重复通知。

## Open Questions

- 企业微信/邮件是否纳入首版通知渠道尚未确定；不影响站内/现有通知与审计要求。

## Design Blockers

- 真实 prod secret/config 只能在获得正式任务授权后做 presence/fingerprint 检查，本设计任务未检查。
- 前序候选实现未融合，不能直接以其本地配置作为生产 source of truth。
- 专用权限 SQL、角色绑定和运行配置升级尚未实施。
