# OPS-NODE-001 最终验证报告

## 结论

PASS。正式自动备份计划任务契约已完成本地/测试环境实现、独立验证、`int_main` 融合和任务收尾；未操作正式服务器、正式计划任务、备份、恢复、发布、数据库或 NAS。

## 错误原因与解决结果

| 问题 | 根因 | 解决结果 |
|---|---|---|
| query-only 写接口测试失败 | 项目权限异常封装为 HTTP 200 + JSON `code=403`，原测试错误期待 transport 403 | 保持现有 API 合同，修正 E2E 和静态断言；同一 query-only 身份的四个写接口均验证为业务码 403 |
| 8086 页面可开但登录链路异常 | Vite 启动 mode 错误导致 API 前缀为 `/undefined`，单独 HTTP 200 不能证明成对运行态可用 | 使用 `vite --mode dev` 和 48086 proxy，独立 tester 完成真实登录、只读页面和权限路径 |
| 隔离 worktree 全量 Maven 编译缺类 | 当时 `int_main` 引用了尚未提交、只存在于主工作区的 MES 前置源文件 | 未复制脏文件绕过；等待正式提交 `254bb6181` 补齐后，在当前融合 HEAD 重新执行 30 模块构建并通过 |
| query-only 凭据/权限前置缺失 | 无预批准最小查询身份，不能用全权限账号冒充 | 管理员仅通过测试租户真实前端创建临时最小角色、绑定现有用户；验收后恢复原角色并删除临时角色 |

## 融合证据

- 实现提交：`1ee24591a`、`27db9a062`、`7a658f581`。
- 融合提交：`050b19a7c3390475fa5f015925a2b223971410bc`。
- 收尾验证 HEAD：`9f7055e2989291564a215d20725cb4186afc02f7`。
- `git merge-base --is-ancestor 050b19a7c... int_main`：PASS。
- 融合后续提交对本任务路径的差异：无。

## 验证矩阵

| 验证项 | 结果 |
|---|---|
| `mvn.cmd -pl yudao-server -am -DskipTests package` | PASS；30/30 模块 SUCCESS |
| BackupPlan/Windows scheduler/runtime drill Maven | PASS；31 tests |
| 权限异常封装 Maven | PASS；1 test |
| backup-ops Pester | PASS；9 tests |
| task-relevant pytest | PASS；15+1 tests |
| 前端静态合同、E2E 语法、`pnpm ts:check` | PASS |
| 独立 query-only 真实 UI 生命周期 | PASS；只读可见、写控件隐藏、四写接口业务码 403、角色恢复和清理完成 |
| `git diff --check` | PASS |

## 清理证据

- `task-closeout-cleanup` preview/apply：PASS；blocked=0、warnings=0。
- lifecycle helper：已删除。
- `D:\IntRuoyiWorktree\production-backup-scheduled-task-contract`：物理路径不存在。
- Git worktree 注册：不存在。
- 任务端口 8086/48086：无监听。
- 任务所属进程：无残留。

## 剩余范围

正式环境 principal、受保护凭据安装、`backup.maxFreshnessHours` 对应 RPO、计划任务注册/启用和连续运行证明仍需单独授权任务；这些 rollout blocker 不影响本节点本地/测试环境完成结论。
