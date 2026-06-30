# 20260628 Codex 发布执行检查清单日志

GREEN: checklist-task-bootstrap-20260628 -> PASS，已创建任务目录 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260628-release-agent-checklist\`。本轮目标限定为把发布经验压缩成 Codex 可直接执行的检查清单，不涉及新的构建、发布、登录后写入或服务器写入。

GREEN: release-agent-checklist-doc-20260628 -> PASS，已输出 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`，使用“触发条件 / 必做动作 / 放行条件 / 阻塞条件 / 完成判定”结构，覆盖 build、test、mark-tested、prod、backup、失败排查优先级和完整完成判定。

GREEN: release-agent-checklist-routing-20260628 -> PASS，已将新清单接入两个经验入口：
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md` 增加“让 Codex 直接照清单执行时同时读取 release-agent-checklist.md”。
- `D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md` 增加“Codex 构建发布执行检查清单”路由。
