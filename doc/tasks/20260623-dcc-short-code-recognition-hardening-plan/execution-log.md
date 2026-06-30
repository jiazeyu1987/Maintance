# 执行记录：DCC 短编码文件名直连识别硬化

- BDD: 短编码嵌入普通长 token 时不得直连 -> Given 启用项目编码中存在 IN/OC/EC 等短编码 / When 源文件名只是 INT、OCP、ECR 等普通长 token 子串 / Then 后端不得把该短编码当作唯一直连命中结果。
- BDD: 边界清晰且长度足够的长编码仍可直连 -> Given 源文件名包含边界明确且唯一的长项目编码 / When 文控执行基础信息识别 / Then 后端仍可在读取文件内容前直接锁定该编码并回写项目名称。
- BDD: 低置信度文件名证据必须转正式识别链路 -> Given 文件名只命中低置信度短编码 / When 后端评估直连规则 / Then 必须继续内容识别或返回明确失败，不能直接写回错误项目。
- GREEN: previous-task-check -> PASS，已核对 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-test-server-dcc-codex-recognition-audit\task.md` 为 `COMPLETED`，可在其结论基础上拆分新任务。
- GREEN: experience-gate-routing -> PASS，已读取 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md` 与命中文档 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`，本任务限定为本机规划与代码级方案，不执行服务器写入。
- GREEN: code-root-cause -> PASS，只读核对 `DccControlledFileProjectCodeRecognitionServiceImpl`，当前文件名直连使用“`containsIgnoreCase` 过滤 + 最长唯一编码优先”规则；该规则会把低置信度短编码当作直接命中入口。
- RED: `python -X utf8 C:\Users\BJB110\.codex\skills\roadmap-node-dev-plan\scripts\validate_node_dev_plan.py --task-dir D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-dcc-short-code-recognition-hardening-plan` -> FAIL，`Missing required file: task.md`，证明任务包在建档前确实不存在。
- GREEN: `python -X utf8 C:\Users\BJB110\.codex\skills\roadmap-node-dev-plan\scripts\validate_node_dev_plan.py --task-dir D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260623-dcc-short-code-recognition-hardening-plan` -> PASS，任务包结构已补齐，可进入后续实现阶段。
- BLOCKER: task-switch -> 用户当前线程改为“整理领导时间分配文档”，本任务暂停在规划完成状态；影响：backend 代码实现、TDD 验证和联调均顺延到用户恢复本任务后执行。
