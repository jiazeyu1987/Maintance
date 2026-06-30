# 20260628 发布链路复盘与研发规范总结

## Task Goal

基于 `20260625-head-full-release` 从最早失败版本到最终 `release-20260628-0015-head-full-v17` 成功的全过程，沉淀一份可长期复用的复盘总结，覆盖：

- 构建发布链路的稳定执行规范
- 测试服、正式服、备份服的环境与验证规范
- 发布过程中暴露出的后续研发规范
- 后续任务可直接复用的执行清单与预防规则

## Scope

- 读取并总结本仓任务与日志证据：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260625-head-full-release\`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\request-command-log.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
- 输出复盘文档到本任务目录。
- 视情况补充项目级短记忆，但不直接修改 `AGENTS.md`。

## Non-Scope

- 不重新执行发布。
- 不修改测试服、正式服、备份服状态。
- 不改动业务代码、SQL 或发布脚本，仅沉淀规范与经验。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 任务开始先读索引，只打开命中文档。
  - 高风险动作前必须先有 `experience-preflight`；本任务仅做文档沉淀，不执行高风险动作。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - 发布经验必须区分“构建成功”“发布成功”“环境可用”三层证据。
  - 候选发布包必须以 manifest、releaseTag、sha256 和远端运行态闭环证明。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 正式服、备份服经验必须保留明确边界：环境参数、数据盘、容器、健康检查、授权。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
  - 仅沉淀项目级、可复用、长期稳定的规则；任务专属细节保留在任务文档。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；总结必须把问题收敛为长期规则，而不是只记录表面现象。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

BDD: 发布链路复盘可直接指导后续任务 -> Given 本次发布从多个失败版本收敛到 v17 成功 When 归纳版本演进中的真实问题、修复方式和验证证据 Then 后续任务可以按文档直接完成构建发布，并在研发阶段提前规避同类问题。

## Expected Deliverables

- `release-flow-fupan.md`：正式复盘总结。
- `execution-log.md`：本轮总结过程与证据记录。
- 如有必要，更新项目级短记忆文件。

## Current Status

COMPLETED：已完成从早期失败版本到 `release-20260628-0015-head-full-v17` 成功版本的全链路复盘，文档已沉淀构建发布规范、三环境验证规范、研发规范与后续执行清单，并补充了项目级短记忆。
