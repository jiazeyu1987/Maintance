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

- 首次安装0046d16后真实只读远端调用发现Python3.6拒绝future annotations。应用服务器零写入，失败未掩盖。按重构规则委派子Agent提取共享解析器，原CLI/动态加载入口保留。
- GREEN: 兼容候选真实test/prod远端bootstrap通过；测试当前契约PASS，正式旧CHECK被BLOCKED。4项共享解析器测试及原预检28项PASS，现有135项相关测试均通过。
- GREEN: experience-preflight -> PASS，适用兼容修复安装3d3e607：沿相同保全/ACL探针/空闲/稳定路径安装流程，替换3文件、新增共享解析器；不改配置/历史/应用数据。

- GREEN: 安装3d3e607成功，稳定source PID21804；474个非本次文件、配置和SQLite payload保持，443条job未变。真实test/prod读取及新模块远端加载PASS；当前测试契约PASS，正式旧约束明确BLOCKED，服务器零写入。
- GREEN: 固定3d3e607最终139项相关回归PASS，原预检28项PASS，安装态12项PASS。应用21f7528a固定Git blob契约SQL SHA6856f92502c82a30a2b1eeb8ce8ed4f84316be8630eee16c6efc0626d1556eb8；工作区CRLF SHA仅另作参考，不混入包。
- 实现0046d16及兼容3d3e607均fast-forward合入int_main；合并结果与隔离HEAD相同，并完成上述验证。
- GREEN: experience-preflight -> PASS，适用本任务维护worktree清理：HEAD3d3e607、工作区/索引干净、主线已包含且验证通过，运行执行器位于稳定source不引用临时checkout。仅清理database-contract-gate-20261124，外置回执保留；原PQC发布两个worktree及应用方被拒绝目录不触碰。

- 收尾：首次cleanup被启动器命令行含目标路径误判consumer；核无实际consumer后以外置入口运行同一守卫，随后发现7个测试生成pyc。逐个核MAGIC及对应Git跟踪源码，外置保留后原守卫通过；5290文件、Git退出0、registeredAfter=false、physicalPathExists=false。没有放宽守卫或删除未知文件。
- 当前协调状态blocked：应用工作区残留清理被自动审批拒绝（blocked by policy，无更具体原因），slot9保留且未换方式重试。维护实现和安装已完成，但整体不标completed；最终状态记录暂未提交。原业务发布仍因路线基线缺失阻塞，后续须新契约包新tag。

- 用户询问是否需要手动删除残留目录。本轮只读复核精确路径、Git登记、合并关系、文件内容范围和进程占用，不重试被拒绝的删除；确认后提供人工处理范围。

## 人工清理前只读复核
- 目标：C:/SpugHandoff/release/dbc-20261124；Git 已取消登记，功能提交已融合，无进程占用，无重解析点。
- 完整长路径读取无错误；16670 个版本文件与功能分支相同（允许 CRLF/LF 差异），无改动文件；12194 个构建/依赖缓存文件，另 9 个 Maven flatten 插件产物。
- 证据：C:/SpugHandoff/release/private/database-contract-gate-20261124/residue-content-comparison.json。
- 未重试自动审核拒绝的删除。用户可手工仅删除该残留目录，待核验目录消失和端口槽位收尾后再关闭任务；正式发布业务验收阻塞独立保留。

## 最新主线同步复验
用户已手动删除应用残留，要求同步 IntRuoyi int_main 并验证改动有效。沿用本任务；先核删除、主线与远端差异，固定提交隔离验证安装态与真实数据库契约；不将契约验证等同订单业务验收。

GREEN: experience-preflight -> PASS; user deletion verified; fetch via required proxy succeeded, app HEAD=origin/int_main=21f7528. Reverification reads fixed Git blobs in isolated evidence directory and installed modules; SSH queries are read-only transactions, no application deployment/database writes. No new release worktree or build required because source unchanged.

GREEN: latest-main installed verification -> 12 tests PASS; seven installed implementation files match committed 3d3e607. Real test58 current contract PASS; prod57 current contract BLOCKED as intended. Both remote bootstrap imports PASS. Evidence: latest-main-verification.json; serverMutations=false.

GREEN: closeout -> PASS. Application owner confirmed slot9 inactive under mutex and all other entries unchanged. Both task worktree paths absent; stable executor PID21804 cwd remains C:/SpugHandoff/release/source/ops/spug/release-center. This contract-gate task completed; original business-release acceptance remains blocked separately.
