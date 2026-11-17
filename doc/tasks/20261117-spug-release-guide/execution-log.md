# 执行记录

- 用户需求：了解通过 Spug 发布到测试服和正式服的方法。
- Bootstrap：显式 UTF-8 只读读取 AGENTS.md、docs/experience-index.md、docs/powershell-memory.md；命令退出码 0。
- 范围：本地文档和脚本核对，无服务器操作、构建、发布或 E2E。
- BDD/TDD：本次为流程咨询与任务记录，不涉及功能或行为变更，不适用代码 RED/GREEN。

- 只读资料核对：经验索引命中发布检查清单、测试服前置门禁；读取 release-backup-restore、server-access、Spug 发布中心 README、portable README 及实际 UI 按钮映射。
- 来源：`ops/spug/release-center/README.md` 的直接三服策略与三项技术检查；`ui/app.js` 的构建、publish-test、mark-tested、promote-prod、accept-prod；`doc/tasks/20261030-spug-handoff-install/task.md` 的迁移入口 18081。
- GREEN: 文档一致性核对 -> PASS。固定已提交源码构建不可变包；同包测试后晋级；正式技术检查与业务验收开放分别记录；仅测试服任务依 AGENTS 停止在测试部署及验收，不自动 mark-tested 或晋级。
- GREEN: 本机监听只读检查 -> PASS。18080、18081、18112 有监听；此证据不代表页面登录、服务器版本、实例策略或健康已核验。
- 公开 Spug 官方文档检索返回上游 HTTP 502，未作为结论依据；内部流程依据本地正式文档及代码。
- 检索期间仓根 README.md 不存在导致一次 rg exit=2；随后直接定位 ops/spug/release-center/README.md，已解决资料定位问题，不涉及产品失败。
- 收尾范围：无服务端操作、发布执行、业务写入、临时 worktree 或本任务进程；仅记录文件需提交，保留既有并发改动。
