# 实施计划：已测试发布包发布正式服按钮

## 目标

将文档方案实现为运行控制台中的独立“发布到正式服务器”按钮，并在获得明确授权后，用同一不可变发布包完成真实正式服验收。

## 实施前置

1. 明确 R93 应用/维护候选提交与当前 `int_main` 的融合方案；禁止在脏主工作区直接开发。
2. 创建新的应用前后端同名分支/worktree 和维护仓 worktree，记录目标提交。
3. 读取任务文档、经验索引、发布/服务器/登录/PowerShell/worktree 文档。
4. 正式服真实 preview/发布必须另行取得当前任务明确授权。

## Milestone 1：后端安全合同

- 新增专用 `infra:runtime-control:promote-prod` 权限和迁移。
- 先写 production preview、请求白名单、权限和错误码 RED。
- 实现 `ProductionEligibilitySnapshot` 与只读 checks/blockers。
- 验证 preview 不产生远端写入，非 TESTED/缺证据/写开关关闭正确阻断。

放行：目标 JUnit 全部 GREEN，真实 DB schema/菜单字段已按 `DESCRIBE` 核对。

## Milestone 2：授权、幂等和失败状态

- 先写 preview stale、grant binding、idempotency、lease conflict、重启恢复和派发未知 RED。
- 扩展授权绑定 preview/stateVersion/target fingerprint。
- 扩展 promote 请求，拒绝客户端拥有字段。
- 明确零写入保持 TESTED；消费/派发/写入未知进入 RECOVERY_REQUIRED。

放行：并发、双击、过期授权、错误 PROD、服务重启、持久化失败回归全部 GREEN。

## Milestone 3：最终证据与维护脚本

- 先写低层 operation succeeded 但运行态证据漂移的 RED。
- 补齐 operation/manifest/env/image/container/health/HTTP/release-info/page/lock 证据聚合。
- 同步维护仓 prod dry-run、target fingerprint、远端锁和脱敏合同。
- 确保不触发 build-release 或 promote-backup。

放行：应用和维护仓目标回归 GREEN；部分写入故障注入保持锁与 RECOVERY_REQUIRED。

## Milestone 4：前端按钮

- 读取统一前端样式文档。
- 先写按钮文案、专用权限、preview、字段白名单、错误态、可访问性和恢复态 RED。
- 应用前端标准面板实现按钮和 preview 对话框。
- 删除/禁用维护 standalone console 的旧 generic promote-prod 生产入口，或使其只跳转到唯一 workflow 页面；不得保留可手填 releaseTag 的第二入口。

放行：静态合同、类型检查、build:prod、query-only/operate/prod permission 真实权限投影检查 GREEN。

## Milestone 5：本地与测试服验证

- 在新的 clean release worktree 构建新 releaseTag。
- 完成本地真实安装包演练、manifest/integrity/schema/migration 门禁。
- 仅发布测试服，走真实页面完成 build/publish-test/PASS acceptance。
- Playwright 验证新正式按钮 eligibility/preview/错误确认，但在未获正式授权时不得触发生产写入。

放行：同一 releaseTag 的测试服 operation、manifest、env/image/health/HTTP/page/tested proof 全部 PASS。

## Milestone 6：经授权正式服验收

- 取得正式服授权、生产窗口、恢复负责人和 `GREEN: experience-preflight -> PASS`。
- Playwright 从真实页面点击新按钮，核对 preview，精确输入 PROD 并提交一次。
- 监控到终态，独立核对九项成功证据和审查服未触发。
- 任一失败按零写入/RECOVERY_REQUIRED 分支处置，不重试旧失败 operation。

放行：AC-PROD-001 至 AC-PROD-017 全部有证据，或明确记录未授权/环境 blocker。

## Milestone 7：融合与收尾

- 在实现 worktree 提交任务文件；只包含任务拥有的代码、测试和文档。
- 合入各自 `int_main` 并在合并结果复验。
- 标记 ready_for_closeout，运行 task-closeout-cleanup preview/apply。
- 删除任务 worktree、恢复稳定运行控制台路径后标 completed。

## 禁止事项

- 禁止从旧 generic action 直接提交任意 releaseTag 到正式服。
- 禁止用 mock、API-only、旧 operation 或测试服成功替代真实正式按钮验收。
- 禁止在失败后手工改 workflow、tested、migration ledger 或 release lock。
- 禁止自动回滚业务数据或自动发布审查服。
