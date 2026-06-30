# 20260630 发布默认走主分支规则固化

## Task Goal

把用户在当前线程确认的长期规则固化到维护仓事前文档与 `AGENTS.md`：后续执行“构建并发布到测试服务器”等发布命令时，默认只发布各仓库主分支当前版本，不再默认创建发布 `worktree`；如果主分支工作区存在脏改，必须先提示用户选择方案，再决定是否继续。

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

- 上一个维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260630-test-server-dcc-browser-cache-write-failure-rerelease\task.md`
- 状态：`COMPLETED`
- 处理说明：上一维护仓发布任务已完成，可开始本次长期规则固化任务。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 先读索引，只打开命中的发布经验文档。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 新规则必须写入事前发布文档入口，替换“默认 clean worktree 发布”口径为“默认主分支发布，脏改先询问用户方案”。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - Codex 执行清单必须与新规则保持一致，避免后续命令仍默认走 `worktree`。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；通过统一 `AGENTS.md` 与事前发布文档口径，避免后续发布命令继续沿用过期默认策略。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

BDD: 发布命令默认只走主分支 -> Given 用户后续再次下达“构建并发布到测试服务器” When Codex 读取事前经验与 `AGENTS.md` Then 必须先按各仓库主分支作为默认发布输入理解，不再默认切到发布 `worktree`。

BDD: 主分支脏改时先让用户选方案 -> Given 任一参与发布的主分支工作区存在未提交改动 When Codex 进入发布前检查 Then 必须先明确提示风险并让用户选择处理方案，而不是默认隔离到 `worktree` 或继续发布。

## Milestones

1. 新建任务台账并记录经验门禁。`COMPLETED`
2. 更新 `AGENTS.md` 的长期线程基线。`COMPLETED`
3. 更新事前发布经验文档和 Codex 执行清单。`COMPLETED`
4. 回填命令日志与任务结论。`COMPLETED`

## Expected Verification

- `AGENTS.md` 明确包含“发布默认只发布主分支；主分支脏时先提示用户选择方案”的线程基线
- `docs/release-build-preflight-lessons.md` 与 `docs/release-agent-checklist.md` 均改为同口径
- `docs/request-command-log.md` 已记录本次规则固化

## Current Status

COMPLETED：已将“发布默认只发布主分支；主分支工作区有脏改时先提示用户选择方案”写入 `AGENTS.md`，并同步更新 `docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md` 与 `docs/request-command-log.md`。后续收到“构建并发布到测试服务器”等发布命令时，将按该新基线执行。
