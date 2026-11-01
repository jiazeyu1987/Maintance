# 三服版本与结构一致性发布门禁

- Trigger：同一发布包依次升级测试服、正式服和审查服，或发现程序同版本但数据库缺表、缺字段、缺索引。
- Preflight check：先只读采集真实表、列、索引、约束及可编程对象；差异必须有明确原因。读取真实迁移台账，已 APPLIED 的历史迁移保持原字节。需要补齐结构时新增独立前向迁移，使用真实 MySQL 验证重复执行及现有行保留，发布输入必须来自已提交内容。
- Blocker：未知结构差异、历史摘要冲突、非预期待执行迁移、包摘要不符、有效启动配置与镜像不符、GxP 未关闭、恢复条件不满足、远端任务状态未知或三服升级后结构不一致，均不得记发布完成。
- Verification：同一 releaseTag 的测试升级、测试验收、正式升级和开放、审查升级和开放闭合。逐服核远端 operation=SUCCESS、manifest、实际生效配置、前后端镜像、backend health=UP、frontend HTTP 200、真实 Playwright 登录，以及 GxP 保存和运行均关闭。独立对照三服表名、字段、索引、约束，不能只比较表数。
- Forbidden action：不得修改旧 SQL 摘要或台账，不得删除测试服现有表凑齐数量，不得同步业务行来冒充结构一致，不得创建未被读取的旧 .env 凑齐格式，不得把只读页面核验称为完整业务回归。用户已取消的全量演练不重新加入门槛；正式独立恢复机制不重复采集。
- Evidence：本任务 schema-before.json、真实 MySQL 验证、源提交 fb88105a、维护提交 15b2f5c/43e4d3e、531 项回归、Spug 固定包及任务回执。最终结果以 release-result.json 为准，本文不预先宣称通过。

## 阶段必查项与推荐命令

1. 构建前：通过 Spug 真实页面选择固定提交并检查 GxP 配置来源；静态 migration-readiness 只证明计划检查。所有环境本轮 APPLY 应仅为新增修复迁移。
2. 封包后：校验 manifest、每个成员、release.tar 和 NAS 副本摘要。已封包后的上传或清理失败，保留原失败，用 Spug 原包重传入口校验续接，不重新编译。
3. 升级前：核实际起点、包身份、可用空间及本环境恢复条件。逐环境使用自身历史台账，不要求升级前结构或业务行相同。
4. 升级后：`verify-deployed-phase.py <env> [open]` 核运行态，`verify-target-gxp.cjs <env> <tag> [acceptance]` 走真实登录；正式和审查启动前、部署回执及开放验收均核同包上游已验收 schema。
5. 最终：`collect-schema.py schema-after.json` 与 `final-release-report.py` 核完整结构和同包闭环，随后清理本任务 checkout/槽位、保留独立分支并单独提交任务记录。

Fail Fast：任何未确认远端效果、原包冲突或真实验证失败必须保留证据并停止后续晋级，先查迁移、清单和脚本契约。不得手改服务器 SQL、改摘要或直接改任务状态绕过。

必须记录：目标、tag、提交、worktree、构建/验证命令、每阶段任务和操作号、恢复策略、失败及续接关联、实际镜像和 schema 摘要、GxP、验证范围及最终工作副本删除结果。
