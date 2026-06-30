# 执行日志：复盘发布后三角色 E2E 门禁闭环

- `BDD: 只把稳定项目经验写入长期记忆 -> Given 已有发布后三角色门禁的完整任务证据 / When 执行复盘 / Then 只把能跨任务复用的执行门禁、发布校验和 smoke 约束写入项目记忆。`
- `BDD: 任务专属细节不得进入长期记忆 -> Given 候选经验包含页面、按钮、单模块排障细节 / When 评估是否写入 project-error-prevention / Then 必须拒绝该候选，避免把一次性细节污染项目级短记忆。`

- `GREEN: evidence-readiness -> PASS，已读取 C:\Users\BJB110\.codex\skills\fupan\SKILL.md、references/project-memory-template.md、D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md 与现有 docs/agent-memory/project-error-prevention.md；本次复盘有足够任务文档与最终证据支撑。`
- `GREEN: collect-error-evidence -> PASS，已生成 D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-fupan-post-release-role-e2e-gate\candidate-error-evidence.md；来源覆盖 AGENTS.md、doc/tasks/20260618-post-release-role-e2e-gate/task.md、execution-log.md 与 docs/request-command-log.md。`
- `GREEN: accepted-lessons -> PASS，采纳为长期项目经验的方向有两类：1) 发布后真实 E2E 必须先全量记录失败，再统一修复并整轮复测；2) required SQL、smoke 环境变量、发布 preflight 必须进入发布脚本和产物校验，不能依赖服务器残留默认值。`
- `GREEN: rejected-candidates -> PASS，拒绝写入长期记忆的候选包括 gaomin/zhaojie/wangsiyu 三账号页签细节、具体 smoke 账号昵称歧义、具体路线产品编码/工序/按钮问题；这些只适合留在任务证据，不适合成为项目级短记忆。`
- `GREEN: update-project-memory -> PASS，执行 update_project_memory.py 后现有 docs/agent-memory/project-error-prevention.md 保持 394 字符；新候选被判定与现有“发布验证三层确认”“发布相关配置必须代码化并补成门禁”规则等价，因此未新增重复条目。`
