# SQL 恢复后全库回读只读审查

## Current Status
ready_for_closeout

## 目标、里程碑与预期验证
当前 v11 全量恢复已完成 SQL 导入并进入 sql-readback。只读审查确认后，父任务批准实施最小 prepared 分支：真实 SQL 应用成功后只查询目标数据库一次，不再执行整库等价观察；增量前序接受同次操作、同一目标、同数据库 UUID、连续位置的真实应用成功回执。保留非 prepared 行为，不停止或部署运行中的恢复。

## 经验门禁
- 上次进度路径只读审查已 completed；本轮继续同一恢复验收任务。
- 从实际正式构建输出确定执行逻辑，不以 ops/recovery 轻量源码替代冻结 STANDARD 输出结论。
- 只读本地源码与既有证据，不扫描远端数据库，不重复校验 NAS；完整等价证明与关键样本验收必须明确区分。
- 用户已要求最小 MVP 与去重；现有经验中的整库证明不是本轮新增门禁，不将未执行证明标为成功。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；显式 prepared 合同不做整库证明，查询/导入失败照常失败，回执明确 NOT_PERFORMED。
- 是否从根因和长期维护角度解决：是，定位正式构建与真实执行成本，提出已有流程内最小调整。
- 是否存在临时补丁或绕过：否。

## 场景
Given SQL 已实际导入成功，When 最小空目标恢复继续运行，Then 不再为完整等价证明逐行重复读取整库；若仅关键数据验收，回执不得声称完成全库数据等价证明。

## BDD 与验证计划
- BDD: prepared 真实应用结束 -> Given SQL 导入正常返回，When 执行回读，Then 仅一次身份绑定 SELECT 1，回执 databaseApplyCompleted/databaseQueryable 为 true，完整等价和受影响数据证明仍为 false、verificationState 为 NOT_PERFORMED。
- BDD: 失败不能成功 -> Given 导入失败或数据库查询失败，When 执行恢复，Then 传播失败，不产生成功回读回执。
- BDD: 同一增量链 -> Given 前一步真实应用成功且同次操作/目标/UUID、位置连续，When 执行下一增量，Then 允许消费；异目标、异操作、错误 UUID 或位置、未成功回执拒绝。非 prepared 保留旧证明门槛。
- BDD: 最终组合 -> Given prepared 数据结果明确未做全库证明，When 实际 consistency 与 runtime 最终结果组合，Then 接受有效结果但不升格为全库等价，businessAcceptance 仍 NOT_PERFORMED。
- 预期验证：实际 standard_sources()+safe_fixes 生成模块的定向测试，必要相邻生成合同回归；不追加全仓测试或组件。
- 当前实际 Redis 通过 collect59 只读当前 worker configuration.json→所选点 material→derived.json，证实 RESTORE/REDIS_DUMP_ABSOLUTE_EXPIRY；不涉及旧 SMALLAPP_SESSIONS REBUILD 的数据证明消费者。证据 v12-derived-mode.private.json 位于父任务私密目录。

## 执行与结果
- 实际生成的旧 `common/recovery_data.py` SHA256 为 `0e7ff68fa1f97283cf48fee53a8d7b5a5f60fe1f3f0ccea0d5608b23ecc883a8`。FULL 调用 `formal_data_evidence.observe_data`：全表逐行/JSON token 哈希、外排序、每表独立 COUNT(*)、前后各一次 schema 观察，每次 schema 又读取所有 SHOW CREATE。此完整证明超出当前最小准备目标范围。
- RED: 已有本机 Docker `python:3.12-bookworm`、现成 `/deps`，`python -m pytest -q --tb=short -p no:cacheprovider scripts/tests/test_prepared_database_readback.py` -> 4 failed，均命中 `WHOLE_DATABASE_OBSERVATION_REACHED`，没有因依赖缺失冒充 RED。
- GREEN: 同命令 -> 4 passed。prepared 只执行一次现有身份绑定 `schema_query('SELECT 1;')`；成功结果只证明 SQL 应用完成与可查询，不宣称完整等价。
- REGRESSION: 同 Docker/挂载环境，`python -m pytest -q --tb=short -p no:cacheprovider scripts/tests/test_prepared_database_readback.py scripts/tests/test_backup_target_mounts.py` -> 10 passed。覆盖实际生成 `full_database` 的导入失败/成功顺序、查询失败、同目标连续增量、错误绑定拒绝、非 prepared 旧路径、实际 consistency 与 runtime 最终结果组合。
- 单元测试的 SQL 边界明确使用测试替身，仅验证生成代码合同，不声称执行了真实数据库验收；运行中的恢复未修改，父任务仍需终态后的 11 表/3 附件/真实登录验收。
- GREEN: 前一提交构建输出与本次 `standard_sources()+safe_fixes` 比较 -> 仅 `common/recovery_data.py` 改变；新 SHA256 `a8b9c763dcca4e7c6b73bf2071f8a54242015c02836c95d7b05eec8ff00a30b1`，编译通过；`git diff --check` PASS。
- 工作区：`C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/integration-worktree`；本次无部署/服务重启/远端写入，无新组件。父任务审核、融合及之后安装尚未完成，保持 ready_for_closeout。
