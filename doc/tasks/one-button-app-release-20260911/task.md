# one-button-app-release-20260911

## Task Goal

设计“按钮化、程序化、不可变安装包”的发布 workflow：标准安装包固定为 `PublishScope=app-release`，只包含程序升级所需制品和版本化迁移，不包含 MySQL 全量 dump、MinIO 快照/同步、DCC object inventory、runtime data 或秘密配置。

## Milestones

1. [completed] 梳理现有运行控制台、发布脚本、R31-R44 失败证据和已验证 release line。
2. [completed] 产出 PRD，定义三按钮 workflow、状态机、授权边界、包边界和错误码。
3. [completed] 产出测试计划，覆盖构建前门禁、不可变包、测试服发布、正式服晋级守卫、R31-R44 防复发用例。
4. [completed] 完成文档结构校验和独立规划评审，明确实施前置条件。
5. [completed] P1 基线与唯一 app-release/manifest/摘要/来源合同已在两个独立 worktree 中收敛并完成复审修正。
6. [completed] P2 ReleaseWorkflow 状态机、原子持久化、CAS、租约、心跳/恢复与 verifier-only 推进已实现并回归通过。
7. [in_progress] P3 继续整改与真实验证：r15 已终止于本机上下文清理；清理根因及真实 target readonly preflight 接线尚待核实。暂停新一轮完整构建，先完成故障单独复现及门禁闭环。
8. [in_progress] P4/P5 静态三按钮工作台已实现；任务 worktree 锁定依赖和 Playwright 1.60.0 已恢复，类型检查通过，真实页面验收待发布后执行。

## Expected Verification

- PRD 和测试计划结构完整，acceptance id 全覆盖。
- workflow 明确排除 with-data、全量数据库和 MinIO 同步。
- 每个阶段有 fail-fast、证据、恢复和授权边界。
- P1 前置条件未满足时不得开始实现。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；用正式 workflow、状态机和门禁替代人工反复打包。
- `是否存在临时补丁或绕过`：否。

## 经验门禁

- 标准程序包只能使用 `app-release`，with-data 仅属于显式数据发布/备份恢复流程。
- UI/API 不允许操作者自由填写服务器、NAS、MinIO、repo root、LocalCacheRoot 或 releaseTag。
- 构建前必须完成 source freeze、schema-only 迁移演练、target readonly preflight、依赖/前端模块解析、manifest 和 package digest 门禁。
- 同一个 releaseTag/package digest 只能构建一次，测试服和正式服必须消费同一不可变包。
- R31-R44 失败必须转换为可执行回归，不得靠人工记忆避免复发。
- 正式服真实写入必须另行显式授权并要求 PROD 确认。

## Current Status

in_progress

P1、P2 已完成；P3 继续执行真实 `app-release` 构建与测试服发布闭环。r23-r35 均已判废且不得复用；r32 包构建和 NAS READY 成功，但测试服 required SQL 在版本切换前失败于 `20260807_test_tenant1_all_role_permission_sync.sql` 的源角色权限计数 1676/1678 漂移。应用仓已提交 `c4ba9d3f` 修正计数，维护仓已提交 `b189ef1` 将该应用 SQL 静态测试纳入 build-release 前门禁。r33/r34 本地缓存虽验包完整，但 manifest 均绑定旧应用提交 `ccd0d9a3`，不含 `c4ba9d3f` 修复，已判废；r35 在构建前 fail-fast 于错误的 `NasConfigPath` YAML 参数，未生成本地包。下一步使用新 releaseTag `release-20260914-one-button-app-r36` 从维护仓本段证据提交后的 clean HEAD 和应用仓 `c4ba9d3f` 重新生成 without-data/app-release 程序包并验证测试服发布。正式服仍保持零写入。

## Verification Evidence

- 本轮恢复验证：实际 PowerShell 5.1 长路径清理 8 个行为用例通过；发布清理、目标数据门禁、构建计划、schema-only 与相邻发布回归合计 154 PASS。该数字只证明这些局部检查，不代表 P3/P4/P5 完成。
- `r15-target-preflight-audit.json`：按既有 r15 来源/SQL/账本重算绑定后，检查覆盖失败，requiredCount=58、passedCount=0、sshStarted=false；未进行新一轮构建。测试服真实只读连接查询 `@@session.transaction_read_only` 返回 1。
- 长路径修复移除了无根据重试、原子移出和“目录消失即成功”的补丁，采用实际 PS5.1 可验证的 Windows 长路径调用；此前“竞态已修复”的结论以本轮记录为准。

- `validate_artifacts.py`: `status=ok`, 0 errors, 0 warnings。
- CI/CD evidence validator: PASS。
- PRD: 5 phases、32 acceptance IDs；test plan: 15 cases、32/32 acceptance coverage。
- Independent planning review: final PASS after three review rounds。
- UTF-8、trailing whitespace 与 diff checks: PASS；未运行产品构建、发布或服务器写入。
- P1：maintenance 聚焦回归与三语言摘要均 PASS；app manifest/source/digest/consumer 定向回归 91 PASS；frontend P1 static PASS。
- P2：ReleaseWorkflowStore/Lease/Recovery/Security 11 PASS；相关 infra 回归共 102 PASS。
- P3：维护仓全量 Python 234 PASS、Node 6 PASS、PowerShell digest/AST PASS；app P1-P3 targeted Maven 111 PASS；覆盖 target preflight、schema-only 两轮迁移演练、显式 TCP、幂等/ledger/delimiter、NAS 原子 READY、同摘要晋级授权和 `.env`/actual image 失败恢复。
- `pnpm ts:check` 在补充 `ElMessageBox` 显式导入后通过；任务 worktree Playwright 为规定的 1.60.0。
- r23 immutable package gate：本地 `Test-ReleasePackageIntegrity` 发现 `ops-runtime/actions/01-立即备份.bat: undeclared file`；新增回归先 RED 后 GREEN，发布包治理宽回归 139 PASS，PowerShell AST PASS。
- r24 deploy-control pollution gate：本地 `Test-ReleasePackageIntegrity` 发现 `preflight-plan.json: undeclared file`；新增回归先 RED 后 GREEN，发布包治理宽回归 139 PASS，PowerShell AST PASS。
- route-menu target preflight gate：应用仓 `20260629_mes_smart_scheduling_role_scope` 改为选择当前活跃的 `5726/5727` 或未统一前的 `900121/900122`；相邻脚本回归 54 PASS，提交 `6079138ea`。
- r26 deploy-release：版本未切换；失败点为旧包内 `20260709_mes_rt000006_batch_record_mapping.sql`，错误 `Missing RT000006 pressure pump route`。当前应用 HEAD 已有等价修复，旧 r26 判废不复用。
- app-release Object Lock probe gate：新增 RED/GREEN 测试，`deploy-release` 仅校验 `EDHR_S3_*` 配置，不调用写对象探针；聚焦测试 3 PASS，PowerShell AST PASS。
- r28 deploy-release：build-release 与 NAS READY 成功，但测试服 required SQL 在版本切换前失败于 `20260716_mes_balloon_xlsx_route_00002_invalid_process_cleanup` 的 `target mismatch`；根因是测试库已是 `23+26=49` 的规范化路线，sort=26 为合法 `Z2620` 而非旧无效 `B320`。应用仓提交 `8e6c033c6` 已补 already-normalized no-op 和严格 target preflight，回归 11+40 PASS。
- r29 deploy-release：build-release 与 NAS READY 成功，但测试服 required SQL 在版本切换前失败于 `20260717_mes_balloon_excel_device_workstation_binding` 的设备绑定数量硬编码 83；真实目标库只有 44 条可绑定设备种子。应用仓提交 `9d886766a` 已改为目标数据派生计数并增强 target preflight，定向 11 PASS、相邻回归 37 PASS、测试服只读 preflight PASS。
- r32 deploy-release：build-release 与 NAS READY 成功，但测试服 required SQL 在版本切换前失败于 `20260807_test_tenant1_all_role_permission_sync.sql` 的源角色权限计数硬编码 1676；实际源数据为 1678。应用仓提交 `c4ba9d3f` 修正 SQL 与静态测试，维护仓提交 `b189ef1` 将该应用 SQL 静态测试纳入 build-release 前门禁。
- r33 local cache：本地包完整性通过，但 manifest 绑定维护仓 `cecdc120` 与应用仓 `ccd0d9a3`，不是当前已修复的维护仓 `67ee44f` / 应用仓 `c4ba9d3f`，因此判废不发布。
- r34 local cache：本地包完整性未作为可发布依据；manifest 同样绑定维护仓 `cecdc120` 与应用仓 `ccd0d9a3`，不是当前已修复来源，因此判废不发布。
- r35 build command：构建前参数门禁失败，原因是把 `config/runtime-control.local.yaml` 误传给 `-NasConfigPath`；脚本要求 UTF-8 JSON，未进入 Maven、Docker、NAS 上传或测试服写入，r35 判废。

## Current Phase

- P3 正在执行：r23-r35 已判废；R32 已证明包构建链路可到 NAS READY，但部署在 required SQL 前置执行阶段失败于测试租户角色权限同步静态计数漂移。应用仓当前可发布提交为 `c4ba9d3f`，维护仓提交本轮 R35 判废记录后作为新 source freeze。下一轮使用新 releaseTag `release-20260914-one-button-app-r36` 重新生成不可变 `app-release` 包，再执行 NAS 原子 READY、测试服 publish、operation/manifest/.env/实际镜像/容器/health/frontend/release-info/lock/migration 组合验证。
- P4/P5 运行时前置已恢复；真实页面验证必须在测试服发布成功后执行。
- 两个实现 worktree 和已提交代码保留；正式服、审查服及 MinIO 数据同步不在本轮范围。

## Deferred Gates

- 本轮恢复核验：r14/r15 隔离清理目录实际位于 `LocalCacheRoot/publish-int-ruoyi/`，仍各残留 763 个文件，最长路径 306 字符；此前从上一级目录查询后宣称“全部不存在/并发竞态”不成立。必须用 PowerShell 5.1 真实行为回归验证，不能靠代码字符串断言或 PowerShell 7 的手工结果放行。
- `requiresTargetPreflight=true` 不能仅表示排除空库演练；所有排除的待应用迁移必须有实际目标只读检查及成功证据。覆盖缺口解决前不得发布。

- 最终融合前必须重新确认两个主工作区同路径 dirty 改动归属；不得覆盖并发任务。
- 测试服真实写入已获本轮授权；正式服真实写入不在当前授权范围。
- Playwright 固定使用任务 app worktree 锁文件安装的 1.60.0，不切换版本。

## Artifacts

- PRD: `doc/tasks/one-button-app-release-20260911/prd.md`
- Test plan: `doc/tasks/one-button-app-release-20260911/test-plan.md`
- Execution log: `doc/tasks/one-button-app-release-20260911/execution-log.md`
- State: `doc/tasks/one-button-app-release-20260911/task-state.json`
- Test report: `doc/tasks/one-button-app-release-20260911/test-report.md`
