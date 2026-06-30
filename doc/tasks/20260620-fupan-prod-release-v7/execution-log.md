# 执行日志：20260620-fupan-prod-release-v7

- BDD: 复盘只接纳项目级稳定规则 -> Given 本次正式发布任务存在多轮阻塞与修复证据 / When 提炼长期记忆 / Then 只保留跨任务稳定、能指导未来发布任务的规则，任务级细节留在执行日志。

- GREEN: evidence-source-check -> PASS，已确认本次复盘主证据源为 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-prod-release-current-latest\task.md`、`execution-log.md`、现有 `docs/agent-memory/project-error-prevention.md` 与 `AGENTS.md` 长期基线。
- DEFER: raw-prod-dry-run-field-rule -> `ProdDryRunEvidencePath`、`releaseTag`、`writeActions=[]` 等字段级约束已在本次正式发布中真实阻塞，但直接按字段名写入短记忆时被 `update_project_memory.py` 判定为不够泛化，说明它更适合作为任务证据而不是原样写入项目级记忆。
- GREEN: generalized-prod-preflight-rule -> PASS，将上述现场字段约束抽象为“正式环境发布前先补齐目标环境只读预检证据并校验版本一致；证据缺失、版本不一致或存在写动作直接阻塞”，该规则已被短记忆更新脚本接受。
- GREEN: memory-compaction -> PASS，复核更新后 `docs/agent-memory/project-error-prevention.md` 曾超出 800 字符；已按技能规则去重压缩，把重复的发布验证/预检表述合并为 5 条项目级规则，最终文件长度为 `783` 字符。
- REJECT: task-specific-release-details -> 本次正式发布中的 `900120` 菜单、排产角色缺失、`intruoyi-website` 运行 2 weeks、具体 `v4/v7` 包名、具体 SSH/HTTP 返回值都属于任务级现场证据，只保留在发布任务日志，不提升到长期记忆或 `AGENTS.md`。
