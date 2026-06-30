# 任务：DCC 短编码文件名直连识别硬化

## Goal

把 DCC 文件名直连识别从“纯子串命中”收紧为“高置信度命中”，避免 `IN`、`OC`、`EC` 一类短编码在普通文件名中误命中后直接回写错误项目编码/项目名称。

## 上一任务检查

- 上一相关任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-test-server-dcc-codex-recognition-audit\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已完成只读核验并确认“短编码误命中风险”与“内容级 Codex 识别未跑通”两个独立问题；本任务只处理前者。

## Scope

- 业务后端识别逻辑：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-dcc\src\main\java\cn\iocoder\yudao\module\dcc\service\file\DccControlledFileProjectCodeRecognitionServiceImpl.java`
- 回归测试：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-dcc\src\test\java\cn\iocoder\yudao\module\dcc\service\file\DccControlledFileProjectCodeRecognitionServiceTest.java`
- 直连规则收紧策略：
  - 取消仅靠 `containsIgnoreCase` 的短编码直连
  - 引入边界感知匹配
  - 对低置信度短编码走“继续内容识别或显式失败”的正式路径，而不是错误回写

## Non-Scope

- 测试服内容级 Codex 识别运行时接通
- 维护仓发布链路修复
- 正式服/备份服部署
- `dcc_project_code` 基础数据清洗或人工改码

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- 命中文档：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 强制门禁摘录：
  - 先把上一轮核验结论写回任务文档、执行日志和命令记录，再进入下一轮修复规划，避免结论漂移。
  - 不把“短编码误命中硬化”和“测试服内容识别跑通”混成一个任务，避免多根因任务互相掩盖。
  - 缺少内容识别运行时前，短编码场景必须 fail fast 或继续正式识别路径，不能为了“看起来成功”继续误回写。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。低置信度文件名证据不允许“猜中就写回”，必须继续正式识别链路或显式失败。
- `是否从根因和长期维护角度解决`：是。直接替换“纯子串”命中规则，而不是继续靠样本运气放行。
- `是否存在临时补丁或绕过`：否。方案以规则收紧和测试补齐为主，不做环境特判绕过。

## BDD 场景

- `BDD: 短编码嵌入普通长 token 时不得直连 -> Given 启用项目编码中存在 IN/OC/EC 等短编码 / When 源文件名只是 INT、OCP、ECR 等普通长 token 子串 / Then 后端不得把该短编码当作唯一直连命中结果。`
- `BDD: 边界清晰且长度足够的长编码仍可直连 -> Given 源文件名包含边界明确且唯一的长项目编码 / When 文控执行基础信息识别 / Then 后端仍可在读取文件内容前直接锁定该编码并回写项目名称。`
- `BDD: 低置信度文件名证据必须转正式识别链路 -> Given 文件名只命中低置信度短编码 / When 后端评估直连规则 / Then 必须继续内容识别或返回明确失败，不能直接写回错误项目。`

## Milestones

1. 复盘当前 `containsIgnoreCase + 最长唯一编码` 行为，并补齐会失败的短编码回归测试。`PLANNED`
2. 实现边界感知命中与低置信度短编码拦截规则。`PLANNED`
3. 跑通 DCC 单测回归，确认长编码快捷路径未回归。`PLANNED`
4. 与测试服内容识别任务联动做最终联调验证。`PLANNED`

## Expected Verification

- `mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -Dtest=DccControlledFileProjectCodeRecognitionServiceTest -Dsurefire.failIfNoSpecifiedTests=false test`
- `mvn --% -f D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\pom.xml -pl yudao-module-dcc -Dtest=DccControlledFileProjectCodeRecognitionServiceTest,DccProjectCodeCodexCliClientImplTest -Dsurefire.failIfNoSpecifiedTests=false test`
- 如第二任务已完成：使用真实测试服样本验证“短编码误命中不再直连，长编码仍可直连”。

## Blockers

- 最终测试服联调依赖 `20260623-test-server-dcc-content-recognition-enable-plan` 先把内容级 Codex 识别运行时跑通。
- 若实现前无法确认当前启用项目编码长度分布，需要先只读核对 `dcc_project_code` 长度分布，再冻结低置信度阈值。
- 当前线程优先级已切换为“整理领导时间分配文档”，本任务暂缓进入实现；恢复前不得继续写 backend 代码或补测试。

## Current Status

BLOCKED：当前线程已切换到领导文档交付任务，本任务仅保留已完成的规划结论，待用户重新授权后再恢复 backend TDD 实现。
