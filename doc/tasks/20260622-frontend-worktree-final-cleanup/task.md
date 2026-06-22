# 任务：删除已完成的前端 linked worktree

## 任务目标

删除 `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-release` 和 `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean`，让前后端最终都只保留各自 `int_main` 主工作区。

## 当前状态

COMPLETED：两个前端 linked worktree 已删除，前端与后端现在都只保留各自 `int_main` 主工作区。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- 命中门禁：
  - worktree 清理前必须先预览并确认只处理本任务 worktree。
  - 删除 linked worktree 前必须确认主工作区真实为 `int_main`，且不影响前端主目录里的现存本地改动。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否
- `是否从根因和长期维护角度解决`：是，删除已完成且不再承担运行态的前端 worktree，收敛成单一主工作区。
- `是否存在临时补丁或绕过`：否

## BDD 场景

- `BDD: 已完成的前端 linked worktree 可以删除 -> Given 两个前端发布/校验 worktree 都已经是干净的完成态 / When 删除 linked worktree / Then 前端只保留主工作区 int_main。`
- `BDD: 删除 worktree 不影响主目录现存改动 -> Given 前端主目录仍保留自己的本地修改和未跟踪文件 / When 删除其他 linked worktree / Then 主目录改动保持不变。`

## 里程碑

1. 建立删除前端 linked worktree 的任务台账。`DONE`
2. 预览并确认两个目标 worktree 都可安全删除。`DONE`
3. 删除两个前端 worktree 并复核剩余 worktree 数量。`DONE`
4. 回填验证结果并收尾。`DONE`

## 预期验证

- `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 worktree list`
- `git -C D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3 status --short --branch`

## Cleanup Candidates

- `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-dcc-preview-release`
- `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean`

## 当前状态

`COMPLETED`
