# 正式发布按钮 BDD 场景

## Purpose and Scope

在实现前固定“已测试包一键晋级正式服”的可观察行为。场景覆盖资格、不可变包、权限、预检、确认、幂等、执行、成功证据和恢复隔离。

## Evidence Reviewed

- 产品需求 FR-PROD-001 至 FR-PROD-012。
- 后端工作流、一次性授权、环境 lease 和发布脚本现有合同。
- 项目真实 E2E、无 fallback、生产显式授权和部分写入恢复规则。

## Feature Scenarios

### BDD-PROD-001 仅 TESTED 工作流可进入预检

Given 一个工作流已用同一 releaseTag 完成测试服发布和 PASS 验收，且 package/manifest/test operation 证据完整  
When 有专用权限的操作者点击“发布到正式服务器”  
Then 服务端生成只读 production preview，页面展示正式目标、摘要、测试证据和检查项

### BDD-PROD-002 复用同一不可变包

Given preview、tested 证明和 NAS manifest 都绑定相同 releaseTag 和摘要  
When 操作者确认正式发布  
Then 系统执行 promote-prod，不运行 build-release、不生成新 releaseTag、不修改发布包

### BDD-PROD-003 服务端固定正式目标

Given 浏览器只提交 workflowId、reason、previewId、authorizationGrantId、stateVersion、idempotencyKey 和 `PROD`  
When 服务端创建低层发布动作  
Then targetEnvironment、host、目录、数据盘和脚本全部来自服务端受控配置

### BDD-PROD-004 生产确认与一次性授权

Given eligible preview 尚未过期且工作流未变化  
When 有权限操作者精确输入 `PROD` 并提交  
Then 服务端消费一次性授权并只创建一个 production operation

### BDD-PROD-005 成功由全量运行态证据决定

Given promote-prod 低层命令执行完成  
When operation、manifest、`.env`、实际镜像、容器、health、HTTP、release-info 和锁状态全部指向同一 releaseTag  
Then workflow 进入 `COMPLETED` 并产生一次成功通知

### BDD-PROD-006 页面重载恢复监控

Given production operation 正在运行  
When 操作者关闭并重新打开浏览器  
Then 页面从服务端恢复 operation、当前 stage、持续时间和最后进展，不创建新 operation

### BDD-PROD-007 正式与审查环境隔离

Given 正式发布完成  
When 系统关闭本次 workflow  
Then 没有创建 promote-backup operation，审查服运行版本不变

## Failure Scenarios

### BDD-PROD-F01 未测试工作流阻断

Given 工作流状态不是 `TESTED`  
When 页面加载或用户请求 preview  
Then 按钮不可执行，服务端返回 `RELEASE_WORKFLOW_NOT_TESTED`，生产零写入

### BDD-PROD-F02 摘要或测试证据漂移

Given workflow、tested.json 或 NAS manifest 的 releaseTag/digest/test operation 任一不一致  
When production preview 运行  
Then preview 返回 BLOCKED，工作流保持 `TESTED`，不签发授权

### BDD-PROD-F03 权限不足

Given 用户没有 `infra:runtime-control:promote-prod`  
When 调用 preview、authorization 或 promote API  
Then 服务端拒绝，且不创建 preview 授权或 operation

### BDD-PROD-F04 错误确认文本

Given preview eligible 且授权有效  
When 用户提交非精确 `PROD` 文本  
Then 服务端返回 `PROD_CONFIRM_REQUIRED`，授权不消费，生产零写入

### BDD-PROD-F05 preview 过期或目标改变

Given preview 创建后已过期或 target fingerprint 变化  
When 用户提交正式发布  
Then 服务端返回 `PRODUCTION_PREVIEW_STALE`，要求重新预检

### BDD-PROD-F06 重复提交

Given 同一 workflow/prod 已有活动 operation  
When 浏览器双击、重试或另一用户并发提交  
Then 只保留一个 production operation，返回现有 operation 或 lease conflict

### BDD-PROD-F07 派发后未知结果

Given 授权已消费或低层 operation 已被派发  
When 随后持久化、进程或网络失败导致结果未知  
Then workflow 进入 `RECOVERY_REQUIRED`，生产 lease/远端锁保持，不允许再次发布

### BDD-PROD-F08 最终证据不一致

Given 脚本返回成功但正式服 `.env`、实际镜像、health、HTTP 或 release-info 任一不一致  
When reconcile 判定终态  
Then workflow 不得进入 `COMPLETED`，而进入 `RECOVERY_REQUIRED`

### BDD-PROD-F09 服务重启恢复

Given 正式发布在 PROMOTING_PROD 阶段时运行控制台重启  
When后台恢复任务扫描 workflow、operation 和远端锁  
Then 它继续监控唯一 operation 或进入 `RECOVERY_REQUIRED`，不重复派发

## Boundary Scenarios

### BDD-PROD-B01 正式服已是目标版本

Given 正式服表面上已显示目标 releaseTag  
When preview 和最终验证运行  
Then 只有所有证据一致才返回幂等完成；任一漂移都阻断

### BDD-PROD-B02 客户端注入受控字段

Given 客户端额外提交 host、path、script、targetEnvironment、releaseTag 或 evidence path  
When 后端反序列化请求  
Then 请求因 `RELEASE_WORKFLOW_FIELD_NOT_ALLOWED` 失败

### BDD-PROD-B03 静默日志但结构化进度更新

Given 长步骤没有新增文本日志但 lastProgressAt 持续更新  
When 页面和恢复调度器检查任务  
Then operation 保持运行，不按日志 mtime 判失活

## Open Questions

- 双人审批不是当前首版要求；未来增加时需新增独立 BDD，不修改本场景含义。

## Test Blockers

- 真实 production E2E 需要单独正式服授权、生产窗口和恢复负责人。
- 专用权限和 production preview API 尚未实现，实施阶段必须先取得 RED。
