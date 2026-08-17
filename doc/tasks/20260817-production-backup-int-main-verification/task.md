# 正式自动备份契约 int_main 融合后验证

## Task Goal

独立验证 OPS-NODE-001 实现与收尾提交确已进入各自 `int_main`，并在当前主程序 `int_main` 上复验任务相关源码合同和自动化测试；不操作正式服务器。

## Milestones

- [completed] VER-M1：核对适用规则、经验门禁、当前分支和提交包含关系。
- [completed] VER-M2：审计当前 `int_main` 中需求、实现与测试文件的一致性。
- [completed] VER-M3：执行任务相关后端、脚本和前端验证命令。
- [completed] VER-M4：形成独立验证报告并记录最终结论。

## Expected Verification

- 主程序实现/融合提交是 `E:\IntRuoyi` 当前 `int_main` 的祖先。
- 维护仓收尾提交是当前维护仓 `int_main` 的祖先。
- 当前主程序 `int_main` 上 BackupPlan、Windows scheduler、runtime drill、backup-ops Pester/pytest 和前端静态/类型合同通过。
- 验证报告明确区分本地代码验证与正式服务器 rollout；未经授权不连接或修改正式服务器。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；验证当前融合结果而非复用旧分支结果。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- 唯一实现、测试和打包源为 `E:\IntRuoyi\IntRuoyiBackend\script\backup-ops`；维护仓 `ops/backup-ops` 历史副本不得作为本次验证输入。
- 验证必须覆盖主入口 `RepositoryEnvironment`、受保护生产确认、专用 principal、S4U/Limited、ACL identity 和 `completedAt` 新鲜度合同；不得用计划存在或历史备份文件替代合同证明。
- 当前工作区存在无法归属的并行 Maven/Java 或任务相关脏改动时必须停止，禁止覆盖、清理或把旧测试报告冒充本次结果。
- PowerShell 中每个关键测试命令单独执行并记录退出码；Maven `-D` 参数整体加引号，禁止用串联命令最后一个退出码掩盖前序失败。
- 本次仅做本地只读审计、构建与自动化测试；不执行发布、服务器写入、正式计划任务注册、备份或恢复。
- 中文任务记录必须使用 UTF-8，命令和证据不得包含凭据明文。

## Current Status

completed

独立验证结论为 PASS：当前 `int_main@210142332` 包含实现与融合提交，冻结 clean worktree 上的后端、脚本、权限封装、前端静态/语法/类型门禁全部通过。task-closeout preview/apply 无 blocker/warning，detached verification worktree 的 Git 注册和物理目录均已删除。

## Blockers

- 无。

## Cleanup Keep

- doc/tasks/20260817-production-backup-int-main-verification/task.md
- doc/tasks/20260817-production-backup-int-main-verification/execution-log.md
- doc/tasks/20260817-production-backup-int-main-verification/verification-report.md
