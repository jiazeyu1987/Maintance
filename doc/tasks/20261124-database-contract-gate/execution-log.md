# 执行记录

- 用户授权：维护负责长期机制修复和总协调；应用侧与发布侧按原分工协作。
- 前序发布 blocked，原因和影响已在原任务保留并告知用户。本任务不更改其成功判定。
- BDD: 已执行迁移发生结构漂移 -> Given 账本 APPLIED 但当前库不满足包内有效契约，When 发布核验，Then 阻断且不重放旧迁移、不开放服务。
- BDD: 正常兼容升级 -> Given 固定包及可迁移旧库，When 新迁移完成且当前契约全部满足，Then 允许继续技术与业务验收。
- BDD: 不可信契约 -> Given 文件缺失/摘要不符/只读限制违反，When 构建或目标执行，Then 明确失败，不默认成功。

- 工作区：C:/SpugHandoff/release/database-contract-gate-20261124，分支codex/database-contract-gate-20261124，起点2ecf33b。新建普通完整checkout；主区无关改动保留。
- RED: test_database_contract_gate 初始因缺少正式契约模块失败；核心模块实现后7项PASS。入口检查新增RED暴露缺verify_database_contract，随后接入并取得10项PASS；旧fixture缺backend/targets已纠正，未修改生产逻辑掩盖。
- GREEN: 10个相关测试模块134项PASS；新增真实deploy调用链反例后12项目标测试PASS。真实SQLite仅证明执行器判定，不冒充MySQL或业务E2E。
- GREEN: 实际Runtime.call生成的SSH源码在独立隔离Python进程加载模块PASS；不依赖远端仓库路径。
- GREEN: 应用工作区dbc-20261124实际migration_inputs通过，913迁移/8来源引用/1234产物，含契约两个文件。
- 应用侧已确认接口，真实MySQL升级测试进行中；审查补充同列额外CHECK反例。
- 本轮未操作服务器、未安装执行器、未修改旧发布包。

- GREEN: 135项相关回归PASS；最终执行前二次摘要复核新增后12项目标回归PASS。真实应用MySQL8.0.39联调14项及Java215项由IntRuoyi回报通过，待提交SHA绑定复核。
- 安装预核：稳定source的build_artifact_guard/intruoyi_build/intruoyi_runtime/intruoyi_runtime_agent四文件与2ecf33b基线按LF比较全部一致，未发现他人未融合安装修改。
