# AGENTS 与经验规则逻辑冲突审计报告

## 审计结论

结论：**存在需要优化的逻辑冲突和执行歧义**。未发现“全局规则与项目规则完全相反、导致所有任务都无法执行”的总冲突，但发现 2 个高风险生命周期冲突、4 个中风险执行歧义，以及 2 个低风险维护问题。

## 生效范围

当前维护仓任务会直接继承：

1. `C:\Users\BJB110\.codex\AGENTS.md`
2. `D:\ProjectPackage\AGENTS.md`
3. `D:\ProjectPackage\Int\AGENTS.md`
4. `D:\ProjectPackage\Int\IntRuoyiMaintance\AGENTS.md`

任务修改 `D:\ProjectPackage\Int\IntRuoyi\...` 下文件时，还需遵守：

5. `D:\ProjectPackage\Int\IntRuoyi\AGENTS.md`
6. `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md` 及其命中文档

## Findings

### [P1] 发布完成条件与 worktree 清理工具形成循环依赖

- 冲突 A：`D:\ProjectPackage\Int\IntRuoyiMaintance\AGENTS.md:23` 规定，所有临时发布 worktree 删除后，发布任务才算完成。
- 冲突 B：`C:\Users\BJB110\.codex\skills\task-closeout-cleanup\SKILL.md:10,67` 和 `references\closeout-rules.md:60` 规定，任务必须已经标记 `completed`，清理工具才允许 apply、合并和删除 worktree。
- 影响：保持 `in_progress` 会被清理工具阻塞；提前写 `completed` 又违反“worktree 删除后才算完成”，形成短暂或永久的假完成状态。
- 建议：新增 `ready_for_closeout` / `closeout_pending` 状态，并允许清理工具在该状态执行；只有清理、合并和 worktree 删除验证通过后，才写最终 `completed`。

### [P1] 独立验证报告可能被默认收尾规则删除

- 冲突 A：`C:\Users\BJB110\.codex\skills\independent-verification-gate\SKILL.md:12-14` 默认产出 `doc/tasks/<task-id>/verification-report.md`。
- 冲突 B：`C:\Users\BJB110\.codex\skills\task-closeout-cleanup\references\closeout-rules.md:13-15` 默认删除任务目录中除 `task.md`、`execution-log.md` 外的所有文件。
- 影响：独立验证证据可能在任务收尾时被删除，导致后续无法复核放行依据。
- 建议：把 `verification-report.md` 加入 closeout 的默认 keep 集；或要求独立验证技能自动在任务文档写入 `## Cleanup Keep`。

### [P2] E2E 测试数据规则同时允许写入又禁止自创数据

- 允许写入：`D:\ProjectPackage\Int\IntRuoyiMaintance\AGENTS.md:119-121` 要求只修改测试租户，并明确存在“真实 E2E 写入验证”。
- 禁止创建：同文件 `:127` 又要求“仅使用既有真实数据，禁止模拟、自创数据”。
- `D:\ProjectPackage\Int\IntRuoyi\AGENTS.md:116-118,124` 存在相同冲突。
- 影响：创建、导入、编辑后关联、删除等用户路径通常必须产生本用例数据；执行者无法判断通过真实 UI 创建的数据是否属于被禁止的“自创数据”。
- 建议：明确区分：
  - 只读 E2E：仅使用既有真实数据。
  - 写入 E2E：允许通过真实 UI 在测试租户创建可追踪的本用例数据，并按规则清理。
  - 始终禁止：mock、直接接口绕过、直接 SQL 伪造成功、修改芋道源码租户。

### [P2] 维护仓 worktree 经验路径指向不存在的文件

- `D:\ProjectPackage\Int\IntRuoyiMaintance\AGENTS.md:29` 要求读取相对路径 `docs/worktree-memory.md`。
- 实际不存在：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\worktree-memory.md`。
- 实际经验文件位于：`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`；维护仓 `docs/experience-index.md` 也路由到该绝对路径。
- 影响：严格按 AGENTS 执行会因前置经验缺失而阻塞，或误以为无需读取。
- 建议：把维护仓 AGENTS 的路径改为现有绝对路径。

### [P2] 两个项目的经验文档格式标准不一致

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md:5-26` 要求固定六字段门禁摘要：`Trigger`、`Preflight check`、`Blocker`、`Verification`、`Forbidden action`、`Evidence`。
- 业务仓：`D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md:30-37` 要求每个长期经验文档顶部固定四段：触发条件、强制门禁、常见失败模式、验证命令。
- 影响：跨维护仓和业务仓沉淀同一类发布、PowerShell、worktree 经验时，没有明确的格式优先级。
- 建议：统一为一个标准；推荐保留六字段门禁摘要，并允许在其后使用四段结构展开详细内容。

### [P2] “所有仓库建同名分支”与“不得自动扩展范围”存在张力

- `D:\ProjectPackage\Int\IntRuoyiMaintance\AGENTS.md:28` 和 `D:\ProjectPackage\Int\IntRuoyi\AGENTS.md:24` 要求新建或使用分支时，在每个 Git 仓库创建同名分支。
- `D:\ProjectPackage\Int\IntRuoyi\AGENTS.md:8` 要求不得因兄弟项目或跨项目痕迹自动扩展范围。
- 影响：单仓文档、单后端或单前端任务也可能被迫在无关仓库创建分支，产生额外状态和后续清理负担。
- 建议：改为“在本任务实际参与且需要修改的 Git 仓库创建同名分支”；发布任务再明确要求维护仓、后端仓、前端仓成组创建。

### [P3] 经验索引存在不可定位的残缺路由

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md:79-80` 两条规则以“见 ... 的”结束，没有章节名或锚点。
- 影响：关键词虽然命中，但无法快速定位具体门禁，容易导致全量阅读或漏读。
- 建议：补充目标章节标题和 Markdown 锚点。

### [P3] 同一规则在多层 AGENTS 中重复，存在未来漂移风险

- Playwright 版本和浏览器路径规则在 `D:\ProjectPackage\AGENTS.md`、`D:\ProjectPackage\Int\AGENTS.md`、维护仓和业务仓共重复 4 次。
- BDD/TDD、任务文档、E2E、编码规则也存在多处完全重复。
- 当前内容一致，因此不是即时冲突。
- 建议：共同规则只保留在最高有效父级；子项目仅保留差异和更严格的局部约束。

## 已确认不冲突

- 全局 no-fallback、fail-fast 与两个项目的禁止降级、禁止 mock、禁止吞异常方向一致。
- “完整发布必须走测试服到正式服/备份服单一 releaseTag 闭环”与“仅测试服发布任务禁止推进正式服/备份服”不冲突；二者适用于不同发布范围。
- 全局 E2E 真实用户路径与项目 Playwright 登录、接口仅最终校验规则一致。
- Git 只提交本任务文件、UTF-8 显式处理和 PowerShell 禁止 `&&` 的规则一致。
- 两套 PowerShell 经验文档目前方向一致，但作为两个入口存在未来漂移风险。

## 建议处理顺序

1. 先解决发布完成状态与 closeout 工具循环依赖。
2. 将 `verification-report.md` 加入默认保留集。
3. 明确写入型 E2E 的真实数据创建边界。
4. 修复维护仓 worktree 经验路径。
5. 统一两个仓库的经验写入格式。
6. 收窄同名分支规则，并逐步去重父子 AGENTS。

## Verification Result

**FAIL（规则一致性未完全通过）**：现有规则可继续使用，但 P1/P2 项会在发布收尾、独立验证、写入型 E2E 和跨仓经验沉淀中产生不同执行结论，建议修复后重新审计。
