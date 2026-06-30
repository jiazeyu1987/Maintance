# 任务：复盘页面发布全链路并刷新项目记忆

## 任务目标

基于已完成的 `20260621-frontend-release-full-flow-main-merge-rerun` 真实页面发布全链路任务，提炼可长期复用的项目级错误预防规则，更新维护仓项目记忆文件，减少后续发布、E2E、文档回写和环境排障中的重复错误。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-commit-current-front-backend-code\task.md`
- 状态：`BLOCKED`
- 处理：
  - 该任务因用户切换到 `$fupan` 复盘而暂停，未进入正式提交阶段。
  - 本任务只做复盘与项目记忆刷新，不继续推进前后端代码提交。

## 用户要求与执行边界

- 用户要求：
  - 使用 `$fupan` 对当前项目经验进行复盘。
- 当前任务边界：
  - 允许读取维护仓任务文档、执行日志、现有项目记忆与 `AGENTS.md` 约束。
  - 允许更新 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`。
  - 允许在本任务目录记录候选证据与复盘结论。
- 禁止范围：
  - 不伪造历史经验，不把单次页面点击步骤写入项目长期记忆。
  - 不直接提升到 `AGENTS.md`，除非用户后续明确批准。
  - 不操作服务器、不改业务代码。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 项目记忆只保留跨任务稳定规则，不写具体页面、按钮、字段点击步骤。
  - 复盘结论必须来自任务文档、执行日志或既有项目记忆，不凭印象补写。
  - 若候选经验无法证明“错误动作 + 正确动作”，则不得写入长期记忆。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否
- `是否从根因和长期维护角度解决`：是。仅沉淀可稳定复用的项目级规则。
- `是否存在临时补丁或绕过`：否

## BDD 场景

- `BDD: 复盘只接受有证据的项目级经验 -> Given 已有任务文档、执行日志和项目记忆 / When 执行本次复盘 / Then 只有能从证据中证明且跨任务稳定的规则才允许进入项目记忆。`
- `BDD: 页面级细节不得进入长期记忆 -> Given 本次发布任务包含大量具体页面动作 / When 提炼项目记忆 / Then 必须只保留发布 workflow、证据回写、releaseTag、环境排障等项目级约束。`

## 里程碑

1. 建立复盘任务文档并确认可用证据源。`DONE`
2. 收集候选错误证据并筛选稳定规则。`DONE`
3. 更新项目记忆文件并记录接受/拒绝项。`DONE`
4. 汇总复盘结果并完成任务收尾。`DONE`

## 预期验证

- 生成候选证据文件 `candidate-error-evidence.md`
- 明确列出接受、拒绝或延后的候选经验
- `project-error-prevention.md` 更新后仍保持紧凑，且内容为项目级规则
- 本任务文档记录所用证据源与最终复盘结论

## 当前状态

`COMPLETED`：已完成候选证据采集、规则筛选与项目记忆刷新。本次采纳了 3 条新的项目级规则：`同一 releaseTag 必须一次性走通全链路`、`候选包 preflight 必须核 sourceRepos.dirty=false`、`部署构建失败要先区分本机依赖/占用与代码回归`；同时拒绝了“页面预览/点击顺序”“具体 operation UI 位置”等页面级细节，不写入长期记忆。`project-error-prevention.md` 当前长度为 `773` 字符，未超 800 字符上限，且未提升到 `AGENTS.md`。

## 采纳与拒绝

- 已采纳：
  - `部署完成必须同一 releaseTag 一次性走通 build/test/mark-tested/prod/backup；不要拼接多轮结果；证据: 20260621-main-merge-rerun`
  - `候选包 preflight 先核 manifest 的 sourceRepos.dirty=false；dirty worktree 不得作为部署输入；证据: 20260621-main-merge-rerun`
  - `部署构建失败先分清本机依赖/占用与代码回归；clean worktree 缺依赖时先恢复并跑本地测试；证据: 20260621-main-merge-rerun`
- 已合并压缩：
  - 现有 `repo-root/frontend-root` 规则保留，但去掉了证据后缀以满足 800 字符限制。
- 已拒绝或延后：
  - “页面上先点刷新再切动作”等具体 UI 步骤：属于页面级细节，不进入项目长期记忆。
  - “备份服 operation id、日志路径、showroom 具体计数值”：属于单次任务证据，保留在任务文档，不进入项目长期记忆。
  - 提升到 `AGENTS.md`：本次未申请，因为这些规则仍适合留在项目短记忆层。
