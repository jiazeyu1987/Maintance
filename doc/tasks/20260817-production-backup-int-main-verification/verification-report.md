# OPS-NODE-001 int_main 融合后独立验证报告

## 结论

PASS。主程序实现和融合提交已进入 `int_main`，维护仓收尾提交已进入维护仓 `int_main`；冻结的当前主程序 `int_main@2101423329a5b5af8534c44af7536eb69861504d` 通过 OPS-NODE-001 相关源码审计及自动化回归。

本结论仅证明本地代码、测试和融合状态，不表示正式服计划任务已注册、启用或正常运行。本次未连接或修改正式服务器，未执行发布、数据库、NAS、备份或恢复操作。

## 融合证据

- `050b19a7c3390475fa5f015925a2b223971410bc`（融合提交）是当前主程序 `int_main` 的祖先。
- `7a658f581`（实现提交）是当前主程序 `int_main` 的祖先。
- `3cd1f3e7e99fa397497107708a9ba977d5879749`（维护仓收尾提交）是维护仓 `int_main` 的祖先。
- 主程序预检期间分支前进，因此在 clean detached worktree 冻结 `2101423329a5b5af8534c44af7536eb69861504d`；验证结束时 `int_main` 仍为该提交。

## 合同审计

- 唯一测试与实施源为 `IntRuoyiBackend/script/backup-ops`，未使用维护仓历史副本。
- 专用 `taskPrincipal.principalId`、S4U/Limited、batch-logon、ACL identity、普通用户不可写和敏感信息不入命令合同存在。
- `backup.repositoryEnvironment` 显式传播，缺失/非法 fail fast；主入口与注册命令使用同一值。
- `completedAt` 与正整数 `backup.maxFreshnessHours` 健康判定、缺失/过期阻塞合同存在。
- query-only 权限仍为 HTTP 200 + JSON `code=403`，前端只读展示合同存在。

## 自动化验证

| 验证项 | 结果 |
|---|---|
| BackupPlan/Windows scheduler/runtime drill Maven | PASS，31 tests |
| 权限封装 Maven | PASS，1 test |
| backup-ops Pester | PASS，9 tests |
| source/runtime/menu pytest | PASS，15 tests |
| 发布打包同步 pytest | PASS，1 test |
| 前端备份计划静态合同 | PASS |
| readonly/query-only E2E 语法 | PASS |
| `pnpm install --frozen-lockfile` | PASS，lockfile 未修改 |
| `pnpm ts:check` | PASS |
| verification worktree `git diff --check` | PASS |

## 收尾验证

- `task-closeout-cleanup` preview/apply：PASS，blocked=0、warnings=0、无一次性任务文件需要删除。
- detached verification worktree：Git 注册不存在，物理路径不存在。
- 任务进程和监听：0；本任务未登记端口，也未停止其它任务进程。

## 剩余范围

正式环境 principal、受保护凭据安装、RPO 对应的 `backup.maxFreshnessHours`、计划任务注册/启用和连续运行证明仍需后续明确授权。本次验证不解除这些 rollout blocker。
