# 20260703 create-preflight-skill

## 任务目标

- 创建本地 Codex 技能 `preflight-experience-consolidation`，通过用户口令 `$前置技能` 触发。
- 技能用于沉淀和执行构建经验、发布经验、PowerShell 经验、worktree 经验等项目级前置经验门禁。

## 经验门禁

- 适用索引：`docs/experience-index.md`
- 命中经验：`docs/release-build-preflight-lessons.md`
- 本任务强制门禁：
  - 技能必须放在可自动发现的用户技能目录。
  - `SKILL.md` frontmatter description 必须明确包含 `$前置技能`。
  - 技能主体只放流程，详细经验按构建、发布、PowerShell、worktree 分区放入 references。
  - 创建后必须运行 skill validator。

## 里程碑

- [x] 创建任务目录。
- [x] 使用 skill-creator 初始化技能骨架。
- [x] 编写 `SKILL.md` 和 references 分区。
- [x] 验证 `$前置技能` 触发描述和引用文件存在。
- [x] 运行官方 quick_validate 校验。
- [x] 提交本任务直接产生的项目记录文件。

## 预期验证

- `C:\Users\BJB110\.codex\skills\preflight-experience-consolidation\SKILL.md` 存在。
- `SKILL.md` description 包含 `$前置技能`。
- references 包含 `build.md`、`release.md`、`powershell.md`、`worktree.md`。
- `quick_validate.py` 输出 `Skill is valid!`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，将重复错误沉淀为可触发、可执行、可验证的前置技能。
- 是否存在临时补丁或绕过：否。

## 当前状态

- 状态：已完成。
- 技能路径：`C:\Users\BJB110\.codex\skills\preflight-experience-consolidation`
- 验证结果：`quick_validate.py` PASS，输出 `Skill is valid!`。
- 待完成：无。
