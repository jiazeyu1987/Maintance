# 20260701 发布统一走临时 worktree 规则固化

## Task Goal

把用户在当前线程确认的长期规则固化到维护仓事前文档与 `AGENTS.md`：后续每次构建发布一律通过临时发布 `worktree` 执行，构建发布输入固定为目标提交对应的 Git 已提交内容；发布完成后必须删除所有临时发布 `worktree`，现场只保留各仓库 `int_main` 主工作区。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 持久化位置：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\AGENTS.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\request-command-log.md`

## Non-Scope

- 不执行真实 `build-release`
- 不发布测试服、正式服或备份服
- 不修改业务仓源码、数据库或服务器配置

## Previous Task Check

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260701-build-publish-test-server-current\task.md`
- 状态：`BLOCKED`
- 处理说明：上一任务基于“先提交主工作区再发布”的旧规则推进，已不再符合当前线程确认的统一发布工作流；已先显式阻塞，再开始本次长期规则固化任务。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 先读索引，只打开命中的发布经验文档。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 新规则必须写入事前发布文档入口，替换“默认主分支直发 / dirty 时再询问方案”的旧口径为“每次发布统一走临时发布 worktree”。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - Codex 执行清单必须与新规则保持一致，避免后续命令继续在主工作区直发或按旧条件分叉。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；通过统一 `AGENTS.md` 与事前发布文档口径，消除“主工作区直发 / dirty 再建 worktree / 只发已提交版本时才建 worktree”等多种执行分叉。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

BDD: 每次发布统一走临时 worktree -> Given 用户后续再次下达“构建并发布到测试服务器”或其他发布命令 When Codex 读取事前经验与 `AGENTS.md` Then 必须先新建本次专用临时发布 `worktree`，并在该 `worktree` 中完成构建、验证和发布。

BDD: 发布输入固定为 Git 已提交内容 -> Given 主工作区存在脏改或无脏改 When Codex 准备发布输入 Then 必须只使用目标提交对应的 Git 已提交内容，未提交改动、未跟踪文件和脏工作区内容一律不得进入发布包。

BDD: 发布结束后只保留主工作区 -> Given 本次发布所需临时发布 `worktree` 已完成构建、验证与发布 When 本次发布收尾 Then 未产生新提交的临时发布 `worktree` 必须直接删除；产生新提交的临时发布 `worktree` 必须先合回对应仓库 `int_main` 并验证通过后删除；最终现场只剩各仓库 `int_main` 主工作区。

## Milestones

1. 新建任务台账并记录经验门禁。`COMPLETED`
2. 显式阻塞旧发布基线任务，避免与新规则冲突。`COMPLETED`
3. 更新 `AGENTS.md` 的长期线程基线。`COMPLETED`
4. 更新事前发布经验文档和 Codex 执行清单。`COMPLETED`
5. 回填命令日志与任务结论。`COMPLETED`

## Expected Verification

- `AGENTS.md` 明确包含“每次构建发布一律在临时发布 worktree 中执行；发布完成后只保留各仓库 int_main 主工作区”的线程基线
- `docs/release-build-preflight-lessons.md` 与 `docs/release-agent-checklist.md` 均改为同口径
- `docs/request-command-log.md` 已记录本次规则固化

## Current Status

COMPLETED：已完成旧任务阻塞、规则建档、`AGENTS.md` 与两份发布前置文档的统一基线替换，并补齐 `docs/request-command-log.md` 与执行日志。后续收到构建发布命令时，必须按“每次发布一律先创建临时发布 worktree，发布完成后删除所有临时发布 worktree，只保留各仓库 int_main 主工作区”的统一工作流执行。
