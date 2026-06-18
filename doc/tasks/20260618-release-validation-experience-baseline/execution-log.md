# 沉淀发布验证通用经验执行日志

- 2026-06-18 任务开始。
- 用户需求：将通用 1-6 条发布验证经验补充到经验或者基线里。
- BDD: 发布验证经验可复用 -> Given 后续任务涉及功能修改、构建发布包或部署 When Agent 读取经验索引和发布经验文档 Then 能看到唯一发布源头、配置代码化、发布产物验证、环境差异检查、目标运行态验证、故障补门禁六条通用规则。
- GREEN: experience-preflight -> PASS，已读取 `project-experience-consolidation` 技能、`docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`docs/agent-memory/project-error-prevention.md`；本任务只更新已有经验文档，不执行远端写入或发布。
- RED: rg -n "唯一发布源头|配置必须代码化|验证发布产物|环境差异显式检查|目标环境真实运行态|故障补成门禁" docs\release-build-preflight-lessons.md docs\agent-memory\project-error-prevention.md -> FAIL, 经验文档尚未包含这六条通用规则。
- GREEN: apply_patch -> PASS，已在 `docs/release-build-preflight-lessons.md` 补充通用发布验证基线，并在 `docs/agent-memory/project-error-prevention.md` 补充高频短记忆。
- GREEN: rg -n "唯一发布源头|配置必须代码化|验证发布产物|环境差异显式检查|目标环境真实运行态|故障补成门禁" docs\release-build-preflight-lessons.md docs\agent-memory\project-error-prevention.md -> PASS，六条通用规则可被长期经验文档命中。
- GREEN: git diff --check -- docs/release-build-preflight-lessons.md docs/agent-memory/project-error-prevention.md doc/tasks/20260618-release-validation-experience-baseline docs/request-command-log.md -> PASS，无空白错误。
- GREEN: task-closeout-cleanup --mode preview -> PASS，无删除项、阻塞项或警告。
- GREEN: task-closeout-cleanup --mode apply -> PASS，无删除项、阻塞项、警告或删除路径。
