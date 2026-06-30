# 20260629 发布前经验前移整理执行日志

GREEN: experience-preflight-20260629-release-preflight-memory-promotion -> PASS，已读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md` 与 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`，确认本次目标是把“发布前必看”的规则前移到预检入口，而不是继续保留在事后 memory。

GREEN: release-preflight-memory-promotion-20260629 -> PASS，已将“已提交 git 版本发布前必须看到”的规则前移到：
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`

同时已从 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md` 移除这些前置规则，避免 Codex 只能在“出错后复盘”阶段才看到它们。
