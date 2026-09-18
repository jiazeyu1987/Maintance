# 已测试发布包发布正式服验收标准

## Purpose and Scope

给实现、评审和测试提供可执行的产品验收门禁。任何“按钮已完成”结论都必须覆盖本文件，而不是只证明页面存在按钮。

## Evidence Reviewed

- PRD 的 FR-PROD-001 至 FR-PROD-012。
- 现有 R92/R93 测试服成功证据。
- 当前候选前端、工作流 API、一次性授权服务和发布脚本契约。

## Acceptance Criteria

| ID | Given | When | Then |
|---|---|---|---|
| AC-PROD-001 | 工作流不是 `TESTED` | 页面加载 | 按钮可见但禁用，并显示服务端资格原因 |
| AC-PROD-002 | 用户仅有 query 或通用非生产权限 | 尝试 preview/authorize/promote | 服务端 403；不创建授权、operation 或远端写入 |
| AC-PROD-003 | 工作流为 `TESTED` 且摘要/测试证据有效 | 点击按钮 | 只执行只读 preview，返回逐项 checks、blockers、preview ID 和过期时间 |
| AC-PROD-004 | preview 存在任一 blocker | 尝试最终确认 | 确认按钮不可用；工作流保持 `TESTED`；生产零写入 |
| AC-PROD-005 | preview 全部 PASS | 打开确认框 | 显示正式目标、当前/目标版本、摘要、测试验收、迁移/恢复摘要和风险提示 |
| AC-PROD-006 | 确认文本不是精确 `PROD` | 提交 | 服务端拒绝且不创建生产 operation |
| AC-PROD-007 | preview/授权与工作流摘要或状态版本不一致 | 提交 | 返回明确绑定或 stale 错误，要求重新预检 |
| AC-PROD-008 | 客户端额外提交 host/path/releaseTag/targetEnvironment/test evidence | 提交 | 服务端 fail fast 拒绝未知或客户端拥有字段 |
| AC-PROD-009 | 同一请求被双击或网络重发 | 并发提交 | 只有一个 production operation；后续请求返回同一 operation 或冲突 |
| AC-PROD-010 | 正式发布开始 | 查看命令/operation | 未触发 `build-release`，同一 releaseTag 和摘要贯穿测试与正式环境 |
| AC-PROD-011 | 派发前错误且有零写入证明 | 请求失败 | 保持 `TESTED`，释放未使用租约，授权未消费或明确撤销 |
| AC-PROD-012 | 已消费授权、已派发或写入未知 | 请求失败/中断 | `RECOVERY_REQUIRED`，生产锁保持，禁止再次发布 |
| AC-PROD-013 | 脚本返回成功 | 最终验收 | operation、manifest、`.env`、实际镜像、health、HTTP、release-info、页面和锁全部一致后才 `COMPLETED` |
| AC-PROD-014 | promote-prod 完成 | 核对审查服 | 无 promote-backup operation，审查服版本不变 |
| AC-PROD-015 | 操作者刷新或浏览器重启 | 重新进入页面 | 从服务端恢复 operation、阶段、最后进展和终态 |
| AC-PROD-016 | 日志长时间无变化但结构化心跳更新 | 页面监控 | 工作流保持运行，显示最新结构化进展，不误判失活 |
| AC-PROD-017 | 真实发布授权已另行取得 | 用 Playwright 走按钮路径 | 从登录、选择 TESTED 工作流、preview、输入 PROD、提交、监控到真实正式页面验收全程通过 |

## Rejection Criteria

- 仅增加按钮或调用旧通用 action API，没有 workflow/摘要/测试证据绑定。
- 按钮允许任意 `releaseTag`、主机、目录或脚本输入。
- 只校验前端 `PROD`，服务端不校验。
- preview 只是命令文本，没有 target-bound 只读检查和结构化 blockers。
- 成功只依据进程退出码、toast、旧容器健康或 HTTP 200。
- 写入不明时释放生产锁、退回 `TESTED` 或允许立即重试。
- 正式发布自动触发审查服或静默回滚业务数据。
- 用 API-only、mock 或测试服结果代替真实浏览器正式发布验收。

## Product Blockers

- 实现基线尚未确定：R93 候选分支未合入 `int_main`。
- 专用生产权限和 production preview 快照尚未实现。
- 真实 AC-PROD-017 需要独立的正式服发布授权、生产窗口和恢复负责人确认；本文本身不提供该授权。
