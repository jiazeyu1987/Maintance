# 2026-08-16 仅测试服发布（HEAD 固化）

## Task Goal

从维护仓当前分支启动时的 `HEAD` 固化唯一目标提交，在本次专用干净临时发布 worktree 中构建维护控制台与测试发布包；核验 manifest、版本号和变更说明后，仅发布到测试服务器，并完成真实运行态、前端页面、运行控制台及问题记录验证。未提交改动不得进入构建产物，禁止执行正式服或备份服推广。

## Milestones

- [x] M1 发布前文档、经验、前序任务与 Git 状态预检；固化目标提交。
- [x] M2 从固化提交创建本次专用干净临时发布 worktree，并记录隔离证据。
- [x] M3 在临时 worktree 构建维护控制台和测试发布包。
- [x] M4 核验发布包、manifest、版本号、变更说明与目标提交一致。
- [ ] M5 仅执行测试服发布并核验 operation、镜像、容器、健康检查与前端 HTTP。
- [ ] M6 使用真实前端页面核验页面、运行控制台版本号和变更说明。
- [ ] M7 汇总问题与耗时点，沉淀前置经验，进入 `ready_for_closeout`。
- [ ] M8 执行 task-closeout-cleanup，删除本任务临时发布 worktree并恢复任务前稳定运行路径，完成最终记录。

## Expected Verification

- 源工作区记录当前分支、启动时 `HEAD`、`git status --short --branch`。
- 临时发布 worktree `HEAD` 等于固化目标提交，且 `git status --porcelain` 为空。
- 构建命令与输出目录可追溯；发布包、manifest、版本号、变更说明均指向同一目标提交。
- 只出现 `build-release -> publish-test`；不执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- 测试服 operation=SUCCESS、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag 一致、容器健康、backend health=UP、frontend HTTP 200。
- 通过 Playwright 真实打开测试服页面并登录验证；运行控制台显示本次版本号与变更说明。
- 问题记录包含现象、阶段、影响、原因判断、处理动作、结果、可前置检查、可自动化和避免方式。
- 临时发布 worktree 未产生提交则删除；若产生提交则先合回 `int_main` 并在合并结果验证后删除。

## 经验门禁

- Trigger: 构建、发布、服务器写入、真实 E2E 或 worktree 清理。
- Preflight check: 已读取 `docs/test-release-preflight.md`、`release-build-preflight-lessons.md`、`release-agent-checklist.md`、`powershell-preflight-lessons.md`，以及 `E:\IntRuoyi\docs\release-backup-restore.md`、`server-access.md`、`login-access.md`、`worktree-restrictions.md`、`worktree-memory.md`、`powershell-memory.md`、`powershell-encoding.md`、`task-closeout-rules.md`；固化启动时提交且后续不随主工作区更新漂移。正式 `worktree-restrictions.md` 要求新 worktree 只能位于 `D:\IntRuoyiWorktree\`，优先级高于维护仓旧经验中的历史推荐路径。
- Blocker: 无法确认目标提交、worktree 不干净、manifest/版本号/变更说明不一致、发布锁或测试环境冲突、凭据或依赖缺失、受保护配置漂移、任一运行态验证缺失。
- Verification: 高风险动作前在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`；发布后同时验证 operation、manifest、IMAGE_TAG、实际镜像 tag、backend health、frontend HTTP、真实页面及运行控制台显示。
- Forbidden action: 禁止从脏主工作区构建；禁止重新获取或切换到启动后更新的提交；禁止发布正式服/备份服；禁止跳过、mock、降级或拼接不同 releaseTag 的证据。
- Evidence: 本任务 `execution-log.md`、发布 manifest、构建/发布命令输出、Playwright 页面证据及服务器运行态检查记录。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；复用并核验现有单一 releaseTag 发布契约，发现偏差时先修正文档/脚本契约或阻塞。
- 是否存在临时补丁或绕过：否。

## Previous Task Check

- 只读引导检查发现按目录名排序的最新任务 `20260813-r260812b-experience-consolidation` 状态为 `in_progress`；当前线程无证据表明该任务属于本任务链，暂按无关并发任务处理，不修改其文件。若后续发现共享发布锁、worktree 或运行控制台冲突，则本任务立即阻塞。

## Frozen Release Baseline

- 冻结时间：`2026-08-16T00:41:42.4706042+08:00`。
- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`，分支 `int_main`，提交 `3cd1f3e7e99fa397497107708a9ba977d5879749`，主工作区 dirty 49 项（staged 0 / unstaged 20 / untracked 29）。
- 主程序仓：`E:\IntRuoyi`，分支 `int_main`，提交 `cb0464ce886973f16136ed31b4d5812d28927eb3`，主工作区 dirty 252 项（staged 0 / unstaged 34 / untracked 218）。`IntRuoyiBackend` 与 `IntRuoyiFronted` 的 Git 顶层目录均解析为 `E:\IntRuoyi`，因此只创建一个主程序 release worktree。
- 本轮 releaseTag：`release-20260816-intmain-head-test-r260816a-r1`。
- 临时发布根：`D:\IntRuoyiWorktree\r260816a`；维护 worktree `D:\IntRuoyiWorktree\r260816a\m`，主程序 worktree `D:\IntRuoyiWorktree\r260816a\a`，任务 state `D:\IntRuoyiWorktree\r260816a-state`。
- 构建目录：维护控制台在 `D:\IntRuoyiWorktree\r260816a\m` 构建；主程序后端/前端输入分别为 `D:\IntRuoyiWorktree\r260816a\a\IntRuoyiBackend` 和 `D:\IntRuoyiWorktree\r260816a\a\IntRuoyiFronted`。
- 冻结规则：后续不追逐源分支新提交，只比较临时 worktree HEAD、dirty 状态、Manifest v1 `sourceRepos` 和产物哈希。

## Current Status

blocked

当前阶段：M5 阻塞。M1-M4 已完成；`build-release` operation=`SUCCESS`，Manifest v1 validator 与 22 项来源/版本/变更/洁净度断言全部通过。唯一 `publish-test` operation=`op-2026-08-15T183354112639300Z-271fd4fe-4a9c-456d-93e4-bc3a14ae3c4f` 已失败，未重提。

- 阻塞条件：`20260813_form_template_menu_before_form_center.sql` 要求菜单 `605071200` 位于全局基础数据菜单 `990200` 下，但测试服真实值仍为 `parent_id=1186`。其前置迁移 `20260721_form_center_menu_under_basic_data` 被标记为 `type=data`，在 `publishScope=code-only` 中被跳过；后续 `type=menu` 迁移依赖闭包无法保证真实状态。
- 失败后远端状态：release lock=`FAILED`、RUNNING lock=0；目标迁移 `APPLIED=6`、`SKIPPED_ALREADY_APPLIED=428`、`FAILED=1`。`.env`/Compose 已指向目标 tag，但实际 backend 仍为 `hotfix-20260814-route-submit-order-r1`，frontend/release-info 仍为 `release-20260813-intmain-head-test-r260812b-r2`；backend health=UP、frontend HTTP=200 只能证明旧运行态可用，不能判定本次发布成功。
- 影响：测试服务器未发布本次版本；M5-M8 未完成，不执行真实页面/运行控制台成功验收、经验成功闭环、清理或提交。
- 解阻前置：必须在正式源码中修复 code-only 迁移分类/依赖闭包或提供等价的正式迁移方案并补合同测试，提交后从新冻结 HEAD 构建新 releaseTag；当前 Manifest 有 3 个待执行迁移传递依赖会被过滤的 pending data migration，不能只处理首个菜单错误。禁止手工改测试库、改 migration ledger、复用失败 tag 或重试同一包。
- 现场保留：两个临时 release worktree、任务 state、发布包与 48181 隔离控制台均保留。主维护目录 `config/runtime-control.local.yaml` 的 repo/frontend 路径与当前强制根不一致，未用该配置重启主控制台；修复配置并验证前不得删除 release worktree。
- 阻塞审计补充：`preflight-plan.json` 自身为 `passed`，但在计划生成后 PowerShell 才过滤 pending `type=data` APPLY 项，未重新验证剩余 APPLY 节点的传递依赖。结构化证据见 `code-only-dependency-closure-analysis.json`；冻结输入内不存在受支持的继续路径。
