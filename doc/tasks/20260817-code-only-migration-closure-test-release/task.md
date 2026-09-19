# 2026-08-17 code-only 迁移闭包修复与仅测试服发布

## Task Goal

在用户授权扩大范围后，以正式、可维护方案修复 `code-only` 发布预检未保持迁移传递依赖闭包的问题，同时纠正已确认的菜单迁移分类、MES 跨域错误依赖和本机运行控制台仓库路径。全部修复采用 BDD + 严格 TDD，验证通过后仅提交本任务文件，从新的 `int_main` 已提交 HEAD 创建本次专用干净发布 worktree，构建新的唯一 `releaseTag` 并只发布测试服务器，完成真实运行态、页面、版本号和变更说明验收。

## Authorization And Scope

- 用户于 2026-08-17 回复“授权”，明确授权解除上一任务固定 HEAD 的限制，实施正式修复、产生新提交和新 `releaseTag`，并继续仅测试服发布。
- 允许修改：主程序/维护仓发布预检代码与测试、相关 SQL migration metadata 与测试、本机 `runtime-control.local.yaml` 的固定仓库路径（仅当确认该文件不含需提交的秘密且仅做本机配置修复）、本任务文档与既有经验文档。
- 禁止：手工修改测试库、修改 migration ledger、复用或重试失败 `releaseTag`、发布正式服/备份服、执行 `mark-tested`/`promote-prod`/`promote-backup`、提交秘密或无关改动。

## Milestones

- [x] M0 确认上一任务已明确 `blocked`，记录用户授权并创建本任务文档。
- [x] M1 读取命中的发布/worktree/PowerShell/迁移经验与正式发布文档，完成 Git、环境和设计预检。
- [ ] M2 在任务专用开发 worktree 中以 BDD + TDD 复现并修复 scope-aware 迁移依赖闭包。
- [ ] M3 以 BDD + TDD 修复菜单迁移分类、MES 跨域错误依赖及维护仓同步合同。
- [ ] M4 修复并验证本机运行控制台固定路径；完成相关回归和技能证据校验。
- [ ] M5 仅提交本任务实现，合回对应仓库 `int_main` 并在合并结果验证。
- [ ] M6 从新的已提交 HEAD 创建本次专用干净发布 worktree，构建维护控制台与新发布包。
- [ ] M7 核验 manifest、版本号、变更说明、sourceRepos、发布范围和迁移闭包后，仅执行 `publish-test`。
- [ ] M8 验证测试服 operation、镜像 tag、容器、健康检查、HTTP、真实前端页面、运行控制台版本号与变更说明。
- [ ] M9 汇总问题与耗时点，沉淀前置经验，设置 `ready_for_closeout` 并执行任务级清理。
- [ ] M10 合并/清理/恢复验证通过后标记 `completed`，提交最终任务记录。

## Expected Verification

- 新增回归测试先证明：`code-only` 计划若过滤一个待执行 `data` 祖先而仍执行其后代，预检必须在任何远端写入前失败。
- 新增回归测试证明：已在目标库正确应用且 checksum 匹配的 `data` 祖先不会被误阻塞。
- 发布脚本不得在已通过的计划之后静默删除依赖节点；主程序与维护仓的 preflight 实现和合同保持一致。
- 菜单迁移和 MES 迁移 metadata 的正式归类/依赖关系通过迁移策略与专项测试。
- 相关技能证据文档通过各自 validator；UTF-8 无 BOM、`git diff --check`、秘密扫描通过。
- 各仓 `int_main` 合并结果包含且只包含已验证任务提交；发布 worktree HEAD 与 manifest `sourceRepos` 一致且 dirty=0。
- 唯一新 `releaseTag` 的 `build-release` 与 `publish-test` operation 均为 SUCCESS；不出现正式服/备份服推广操作。
- 测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP=200、真实页面及运行控制台版本/变更说明全部一致。

## 经验门禁

- Trigger: 发布预检脚本、SQL migration metadata、`code-only`、worktree、服务器写入、真实 E2E、运行控制台配置。
- Preflight check: 先读取索引命中的 `test-release-preflight.md`、`release-build-preflight-lessons.md`、`release-agent-checklist.md`、`powershell-preflight-lessons.md`，以及 `E:\IntRuoyi\docs\release-backup-restore.md`、`server-access.md`、`login-access.md`、`worktree-memory.md`；在高风险动作前记录 `GREEN: experience-preflight -> PASS`。
- Blocker: 迁移计划对当前发布范围不闭包、计划通过后仍由调用方过滤 APPLY 节点、SQL metadata 与真实依赖不符、worktree 不干净、manifest/sourceRepos/版本/变更说明不一致、发布锁或测试环境冲突、运行态任一项不一致。
- Verification: RED/GREEN/REGRESSION、迁移策略测试、技能 validator、manifest validator、Git 洁净度、operation 和真实运行态/页面联合证据。
- Forbidden action: 禁止手工修库或 ledger、失败包重试、静默过滤/降级、从脏工作区构建、拼接不同 releaseTag 证据、发布正式服或备份服。
- Evidence: 本目录 `execution-log.md`、三份专项 evidence、测试报告、manifest、operation 响应和运行态/Playwright 证据。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；预检发现 scope 破坏依赖闭包时直接阻塞。
- `是否从根因和长期维护角度解决`：是；让迁移计划原生感知发布范围并在生成计划时验证闭包，移除“计划通过后再过滤”的双阶段语义分裂，同时修正错误 metadata。
- `是否存在临时补丁或绕过`：否；不手工改数据库、不改 ledger、不复用失败包。

## Previous Task Check

- 当前线程上一任务 `doc/tasks/20260816-test-only-release-head` 已标记 `blocked`，原因、影响、保留现场和正式解阻条件均已记录。
- 本任务是用户授权后的正式解阻任务；上一任务的两个冻结 release worktree、失败 operation 和隔离控制台仅作为证据保留，在本任务完成新发布且达到清理门禁前不删除。

## Current Status

in_progress

当前阶段：M2。任务范围、授权和经验门禁已固化；维护仓主工作区 `int_main@3cd1f3e...` dirtyCount=196，主程序共享主工作区在预检期间发生并发前进且 dirtyCount=11704，因此后续只在任务专用 clean worktree 中实施和验证。尚未修改生产代码、SQL、配置或远端环境。
