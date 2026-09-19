# Execution Log

## 2026-08-17

- 用户请求：授权实施上一任务记录的正式修复，提交新的 HEAD/releaseTag，并继续仅测试服发布。
- 上一任务状态：`20260816-test-only-release-head` 为 `blocked`；失败 releaseTag 禁止复用或重试。
- 技能路由：`bug-regression-fix-loop` 用于先复现并补回归测试；`database-schema-delivery` 用于 migration metadata 与数据安全合同；`ci-cd-environment-delivery` 用于构建、发布与测试服运行态门禁。
- BDD: code-only 待执行数据祖先阻塞 -> Given 一个 `data` migration 在目标库待执行且一个允许发布的 migration 传递依赖它，When 生成 `code-only` 发布计划，Then 计划必须在远端写入前失败并指出依赖链。
- BDD: code-only 已应用数据祖先放行 -> Given `data` 祖先已在目标库按相同 checksum 应用，When 生成 `code-only` 发布计划，Then 不得因该祖先被 scope 排除而误阻塞允许发布的后代。
- BDD: 发布计划不可二次静默过滤 -> Given 预检计划状态为 passed，When 发布脚本读取 APPLY 节点，Then 节点集合必须已与发布范围一致且调用方不得再删除依赖节点后继续发布。
- BDD: 错误迁移元数据被纠正 -> Given 菜单层级迁移属于代码发布必须执行的菜单配置且 MES foundation 不依赖 DCC 数据清理，When 执行迁移策略合同，Then 两者的 type/dependsOn 必须反映真实职责并保持依赖闭包。
- GREEN: experience-preflight -> PASS，已读取适用规则、`docs/experience-index.md`、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md` 的 code-only 依赖闭包门禁、`docs/release-agent-checklist.md`、`docs/powershell-preflight-lessons.md`，以及 `E:\IntRuoyi\docs\release-backup-restore.md`、`server-access.md`、`login-access.md`、`worktree-restrictions.md`、`worktree-memory.md`、`powershell-memory.md`。本次只放行任务专用开发 worktree 创建和本机 TDD；服务器写入前必须再次复核并发锁、目标版本和 live-state。

## Git Preflight Snapshot

- 维护仓只读快照：`int_main@3cd1f3e7e99fa397497107708a9ba977d5879749`，主工作区 dirtyCount=196；目标实现文件当前无重叠改动，本任务目录为 untracked，`docs/request-command-log.md` 已有并行改动。
- 主程序仓只读快照：一次检查先见 `969cf6d75033774dd957c12db787f96c49908a03`，后续精确检查已前进到 `2101423329a5b5af8534c44af7536eb69861504d`，主工作区 dirtyCount=11704；主工作区持续并发变化，禁止在其中开发、测试或构建。
- worktree 根限制：只允许 `D:\IntRuoyiWorktree\`；本任务计划使用短路径 `D:\IntRuoyiWorktree\r260817f-m` 与 `D:\IntRuoyiWorktree\r260817f-a`，从各自创建瞬间的本地 `int_main` 提交建立同名任务分支，并以实际 worktree HEAD 为开发冻结基线。

## Problems

### P-001 主程序主工作区并发且极脏

- 现象：只读预检期间 `int_main` HEAD 从 `969cf6d...` 前进到 `21014233...`，工作区约 11704 项脏状态并伴随历史损坏 target 目录枚举警告。
- 阶段：M1 Git 预检。
- 影响：主工作区不能作为开发、测试、合并验证或发布输入；单次较早 HEAD 快照不能代表任务基线。
- 原因判断：多个并发任务持续写入/提交主程序共享工作区，另有历史 target 残留。
- 处理动作：按 worktree 强制规则从创建瞬间的已提交 `int_main` 建立任务专用 worktree，后续只认 worktree 实际 HEAD；不清理、不停止、不提交并发任务内容。
- 结果：待 worktree 创建后记录实际冻结提交。
- 是否可前置检查：是。
- 是否可自动化：是，冻结 JSON 应同时记录 branch、HEAD、dirtyCount、目标路径重叠和创建后 worktree HEAD。
- 下次如何避免：发布/修复任务始终以 task-owned clean worktree 为输入，禁止在共享主工作区解析“最新”后延迟创建。

### P-002 宽路径状态枚举产生历史 target 警告

- 现象：主程序 `git status` 扫描历史 `target_corrupt_*` 路径时输出多条目录不存在警告。
- 阶段：M1 Git 预检。
- 影响：增加日志噪声和耗时，但不改变 Git 命令退出结论；也证明共享主工作区不适合本任务验证。
- 原因判断：历史构建残留目录内部已部分缺失。
- 处理动作：不清理非本任务目录；后续在 clean worktree 使用目标路径限定状态和测试。
- 结果：诊断范围已收敛。
- 是否可前置检查：是。
- 是否可自动化：是，可优先输出计数并仅列目标路径重叠。
- 下次如何避免：共享脏工作区预检使用路径限定和结构化计数，构建门禁在隔离 worktree 执行。

## Evidence Markers

- RED: pending
- GREEN: pending
- REGRESSION: pending
- GREEN: experience-preflight -> PASS（开发 worktree/TDD 阶段；远端写入前重验）
