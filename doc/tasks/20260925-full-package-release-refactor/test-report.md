# 独立测试报告

## 审查边界

- 独立测试者：`release_independent_tester`，未参与产品实现，不修改产品或测试、不提交代码、不操作服务器。
- 依据：中央 `dev-plan.md`、`test-plan.md`、`execution-log.md`，仅核验主管已派发的 T1、T2、T3 与 T6J；其它里程碑及最终 AC 不由本报告提前放行。
- 本轮没有三服发布或业务 E2E。隔离 MySQL 验证不能代替真实三服旧基线升级验收。

## T1 — PASS（C1 与 T1-COV01 独立补验均通过）

- 工作区：`D:/IntRuoyiWorktree/full-package-release-maintenance`；基线 `3f3aabdc82ab5e85e2f872173a665a361f022725`，当前任务增量尚未提交。
- 已审查 14 个批准产品/测试路径及 `scripts/tests/release_test_runtime.py`；`test_release_package_governance.py` 保持主线原样。未导入上游 mark-tested recovery-set、d316da9 input preparation、其它任务文档或三项未获准 DCC 业务 SQL 专属测试。
- MySQL 配置仅由测试辅助读取；独立身份校验通过：task=`20260925-full-package-release-refactor`，container=`release-fullpkg-8bea35`，container ID=`ded0e154197b72b214ffb92bbcc35373c22d3c8f6d20e2cb0f48a4737dc2e0e2`，volume=`release-fullpkg-8bea35-data`。容器任务标签、无网络/主机端口、唯一 `/var/lib/mysql` 挂载、独占消费者及凭据匹配均由实际 Docker inspect 校验；未打印或记录秘密。
- 首次独立 C1 命令准备失误：`--basetemp .../tester-t1/c1` 的父目录尚不存在，退出 1，139 passed / 134 setup errors / 0 skipped，128.88 秒；所有 setup 错误为该目录的 `FileNotFoundError`，不计产品 RED。原 JUnit XML 保留在 `E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t1-c1.xml`。
- 已仅创建任务自有 `tester-t1` 父目录，按相同 9 文件清单完整复跑，无产品/测试修改、不缩减用例。

### 独立 C1 实际执行

会话显式设置 UTF-8；`RELEASE_TEST_MYSQL_RUNTIME_CONFIG=E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/mysql-runtime.json`，`RELEASE_TEST_APPLICATION_BACKEND_ROOT=E:/IntRuoyi/IntRuoyiBackend`。

```powershell
python -X utf8 -m pytest -q scripts/tests/test_release_migration_supersession_contract.py scripts/tests/test_release_preflight_r20_regressions.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_preflight_plan_order.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py scripts/tests/test_release_package_governance.py scripts/tests/test_release_operation_lock_mysql_behavior.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t1/c1 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t1-c1-green.xml --tb=short
```

- 开始时间：2026-09-25 18:32:33 +08:00；结果：退出 0，**273 passed / 0 failures / 0 errors / 0 skipped**，577.64 秒。
- 已读取 JUnit XML 确认 273 个 testcase 和零 failure/error/skipped 节点。按文件计数：supersession 11、R20 20、migration preflight matrix 12、plan order 2、SQL preflight 62、build preflight cache 50、schema rehearsal 14、package governance 78、operation lock MySQL 24。
- `git diff --check`：PASS。六个变更 Python 模块规范化换行后逐一与获批 `772fc46` 对应内容相等；治理测试与当前 HEAD 相等。
- 本次执行产品身份：`ops/deploy/publish-int-ruoyi.ps1` 实际字节 SHA256=`5824d0f990e0756aeba091b785582565dec52baec50475e92cc330f7c2db3629`，复跑前后相同；`release_preflight_plan.py`=`ad520527034f680a8f0400dc43307099a941b1f510be10be33c5dbf331f72b5e`。

### 行为审查和覆盖缺口

- 真实生产 PowerShell AST 提取 acquire/ownership 函数，在任务 MySQL 执行生成 SQL。10 组独立空行并发获取全部恰好一个 LOCK_ACQUIRED 和一个 LOCK_HELD；APPLIED/FAILED 重新获取刷新 owner、lease 和 fence，RUNNING 行全部字段保持不变；同 releaseTag 的旧 lease 失权且当前 lease 可刷新心跳/fence。
- `INSERT VALUES ... ON DUPLICATE KEY UPDATE` 避免旧 `INSERT SELECT ... NOT EXISTS` 间隙锁竞争；status 在所有条件 owner/lease/fence 更新后赋值，RUNNING 的 updater/update_time/deleted 也条件保留。未新增 retry、自动解锁或吞异常。
- 真实生成 shell 载体保留 docker 退出码 17，即使前面已有成功文字；真实 acquire 函数拒绝非零运输结果，未因 LOCK_ACQUIRED 字样错误设置持锁。
- **T1-COV01：开发计划第 3 项要求真实生成的 acquire/release/fence SQL，而 `test_mysql_lock_release_requires_exact_executor_and_lease_owner` 目前使用手写 `_recover_sql`；它不能证明 `Invoke-ReleaseOperationLockRelease` 生产函数的行为。** 当前 C1 的 acquire/ownership/fence 已满足，production release 尚未满足。
- 主管确认需执行者补充实际生产 release AST 的正确 owner 终态更新、旧 lease 拒绝和整行不变用例；在产品不变的前提下，独立重跑新增用例及完整锁测试文件即可，不重复无关 C1 文件。补充前 T1 保持 pending，后续关闭证据如下。
- 本里程碑只是 AC-03、AC-04、AC-06、AC-11、AC-12 的依赖回归，不证明最终完整 AC 已完成。

### T1-COV01 独立补验 — PASS

- 执行方本轮只增加锁测试，没有生产变更。独立核对冻结 SHA256：生产 PowerShell=`5824d0f990e0756aeba091b785582565dec52baec50475e92cc330f7c2db3629`，锁测试=`f591975edf04cf4fdfcae84186d4e8d2f554c4aa55491f76cbabeaa91682b7d7`，测试运行辅助=`51743fbfb8cd6c06e4794b66915921ab0c99761b6d2d1e942b5836d7601e657e`；复验后生产和锁测试 hash 不变。
- 新增 helper 提取实际 `Invoke-ReleaseOperationLockRelease`、`Invoke-SshCommand`、SSH 参数/噪音处理及错误脱敏函数；仅在 `Invoke-ProcessCapture` 运输边界替换任务容器/随机库连接位置。生成 SQL 和原 shell 载体实际运行，不复制释放算法、不伪造成功结果。
- 5 个新增行为覆盖：合法当前 owner 分别释放到 APPLIED/FAILED 并清空执行器 held/releasing/lease 标志；同 tag 重新获取后旧 lease 释放被拒绝且当前锁整行不变；真实 MySQL ERROR 1054 保留错误与未确认持锁标志；SQL 已完成而运输退出 17 时仍抛错，保留未知确认状态。FAILED 的测试错误凭据为明确合成值，真实落库文本已脱敏。
- 独立命令（环境与前轮 C1 相同）：

```powershell
python -X utf8 -m pytest -q scripts/tests/test_release_operation_lock_mysql_behavior.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t1/lock-final --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t1-lock-green.xml --tb=short
```

- 实际结果：开始于 **2026-09-25 18:55:59 +08:00**，退出 0，**29 passed / 0 failures / 0 errors / 0 skipped**，237.01 秒；没有 deselect。JUnit XML 29 个 testcase 已读取核对。
- 独立后检：任务 MySQL 中 `release_lock_test_` 随机 schema 残留数为 0；所有连接继续由任务所有权辅助保护。`git diff --check` PASS。
- 后检首次 Python inline 命令因 PowerShell 引号包装错误未执行，不计产品或 SQL 结果；改为显式 UTF-8 here-string 后同一只读 XML/hash/schema 复核实际执行并通过，没有改变产品、测试或数据。
- 本轮补测关闭 T1-COV01；此前 C1 273 PASS 中未变化部分仍有效，不把重复锁用例累计成额外独立测试数量。

T1 无剩余本里程碑阻断，可以解锁 T2/T3。最终受控完整包发布、目标绑定和持久恢复门禁仍依赖后续任务，不作为 T1 已完成内容。

## T6J — PASS（T6J-F01 已修复并独立复验）

### 验证对象与范围

- 工作区：`D:/IntRuoyiWorktree/full-package-release-application/IntRuoyiBackend`；应用基线 `840b9ef0dca94e5ad2780f8182f1072209aa7b35`，当前任务增量尚未提交。
- 精确 7 文件差异：`RuntimeControlOperationRespVO.java`、`RuntimeControlServiceImpl.java`、`ReleaseWorkflowOrchestrator.java`、`ReleaseWorkflowService.java` 及 `RuntimeControlServiceImplTest.java`、`ReleaseWorkflowOrchestratorTest.java`、`ReleaseWorkflowRecoveryTest.java`。
- 生产 `acceptTest(String workflowId, String requestedBy, String result, String conclusion)` 保持四参数；未导入第五 recovery-set 参数、P2～P5、UI、业务 SQL 或远端操作。
- 已核对执行者的行为 RED：107 用例 11 失败，补充证据绑定负例后 112 用例 13 失败；属于实际状态/证据断言失败。独立测试不把该历史结果冒充自己运行的结果。

### 独立执行

```powershell
$env:MAVEN_OPTS = '-Xmx1536m -XX:MaxMetaspaceSize=512m -Dfile.encoding=UTF-8'
mvn.cmd -B -pl yudao-module-infra -am '-Dtest=RuntimeControlServiceImplTest,ReleaseWorkflowOrchestratorTest,ReleaseWorkflowRecoveryTest' '-Dsurefire.failIfNoSpecifiedTests=false' test
```

- 实际结果：2026-09-25 18:32:48 +08:00，退出 0，`BUILD SUCCESS`，13.978 秒。
- Surefire：RuntimeControlServiceImplTest 69、ReleaseWorkflowOrchestratorTest 37、ReleaseWorkflowRecoveryTest 6，总计 **112 passed / 0 failures / 0 errors / 0 skipped**。已读取本次三个 XML 计数，未用旧报告替代本次执行。
- 证据目录：上述应用 worktree 的 `yudao-module-infra/target/surefire-reports/`；文件名为 `TEST-cn.iocoder.yudao.module.infra.service.runtimecontrol.RuntimeControlServiceImplTest.xml` 及 `TEST-cn.iocoder.yudao.module.infra.service.runtimecontrol.releaseworkflow.ReleaseWorkflowOrchestratorTest.xml`、`TEST-cn.iocoder.yudao.module.infra.service.runtimecontrol.releaseworkflow.ReleaseWorkflowRecoveryTest.xml`。
- `git diff --check`：PASS。标准 Maven reactor 完成，没有手工 javac、复制源码工程或共享应用主工作区构建。

### 行为与实现核对

| 合同 | 独立结论与证据 |
| --- | --- |
| 未知提交/写入失败不可安全重试 | operation 已绑定而执行异常、failed/blocked 且无可信零写入证据时，协调器进入 RECOVERY_REQUIRED；对应测试覆盖测试部署和正式晋级的四组合。 |
| 零写入证据必须正确归属 | `hasExplicitZeroWriteEvidence` 同时核 operation ID、workflow ID、action、environment、releaseTag 和布尔证据；缺失或四种归属不符负例拒绝，正确绑定正例允许受控 FAILED/retry。 |
| 原环境保持隔离 | RECOVERY_REQUIRED 不是终态，不走释放租约；未知分派、心跳过期、坏 UTF-8 日志测试实际尝试获取下一个租约并验证被拒绝。 |
| 恢复事实保持稳定 | stale 扫描排除 RECOVERY_REQUIRED；重复扫描前后状态、版本和证据相同。 |
| 服务层不可错误标记可重试 | `verifyAdvance` 仅在非 RECOVERY_REQUIRED 且有 zeroWriteEvidence 时设 retryable；无证据的 FAILED 也拒绝 retry。 |
| 正常路径与原合同 | 三类全量定向测试保留正常构建、测试部署、四参数验收、正式授权和幂等回归。 |

### 阻断发现 T6J-F01：损坏操作证据会中断失败隔离并替换原始异常

- 发现方式：主管提出具体读取异常路径后，独立测试者复核真实 Store、协调器和 Scheduler 控制流。此项为已确认的静态缺陷，不冒充已运行的新增 RED。
- 位置：`ReleaseWorkflowOrchestrator.java:105`、`:144`、`:200` 的分派 catch 首先求值 `hasExplicitZeroWriteEvidence(workflow)`；`:633` 直接调用 `operationStore.findById`。
- 真实行为依据：`RuntimeControlOperationStore.java:84`～`:86` 对存在的 operation 文件调用 read；`:103`～`:107` 的 Jackson 读取发生 JSON 解析或文件 IOException 时抛 `RUNTIME_CONTROL_OPERATION_STORE_FAILED`。损坏 JSON 是明确可达的非秘密测试输入。
- 影响：该读取异常从 catch 条件求值直接抛出，既不会执行 `isolateAfterDispatchFailure`，也不会执行末尾 `throw ex`；已绑定操作的工作流仍保持活动状态，原始分派异常被读取异常替换。内存租约未主动释放，但“明确持久 RECOVERY_REQUIRED 与保留原始失败”合同未达成。
- 无后续自动补救路径：`reconcileActiveWorkflows` 的 operation 读取（`:350`）和 `recoverStaleWorkflows` 的读取（`:413`）同样未处理读取异常；Scheduler 先执行前者再执行后者，前者异常会阻止本轮恢复调用。不能用日后心跳扫描作为完成依据。
- 覆盖缺口：112 个定向用例没有真实损坏 operation JSON 或 operation store 读取异常的场景，因此全部 PASS 不能消除此发现。
- 要求：执行者增加真实任务 operation 文件损坏的 RED，并修复分派失败时的观察异常处理：在 workflow store 可用时持久隔离为 RECOVERY_REQUIRED、保持不可重试及租约隔离，原始分派异常与证据读取异常分别保留；相同证据异常不得让恢复扫描一直越过该事实。不得返回伪造 zeroWriteEvidence、默认成功或吞掉读取错误。

上述为首轮阻断记录；首轮 112 PASS 不能覆盖此缺口，后续修复证据如下。

### T6J-F01 独立复验 — PASS

- 冻结对象：应用基线仍为 `840b9ef0dca94e5ad2780f8182f1072209aa7b35`；实际 `git diff --binary` SHA256=`552e68f4dc449105a0c0c27ae542b06dae7233b6b4f59153c09beb32817c02d3`，与执行方冻结值一致。累计仍为批准 7 文件；四参数 acceptTest 不变。
- 执行者真实 RED 已核：真实临时 operation JSON 损坏后，第一组 119 用例 7 失败；补充绑定 operation 的 SOURCE_FREEZING、READY、TESTED、PROD_PREVIEW 状态后为 122 用例 10 失败。不是模拟 Store 返回异常或导入失败。
- 修复核对：三条分派路径调用 `handleDispatchFailure`，证据读取异常附加为原异常 suppressed，然后尝试持久 RECOVERY_REQUIRED，调用方继续抛同一个原异常。直接协调、活跃扫描、过期扫描等读取通过 `readOperationEvidence` 先隔离再抛原读取错误；没有 catch-return false 或伪造零写入证据。
- 持久证据保留原 evidenceRefs、operation 引用和错误类型；不持久化可能含凭据的异常消息。workflow store 仍可用时，新建 WorkflowService 能读回同一恢复记录；恢复写入本身失败也附加到原错误，不静默成功。
- 新增恢复转移只为 SOURCE_FREEZING、READY、TESTED、PROD_PREVIEW 到 RECOVERY_REQUIRED；不添加自动恢复或放行转移。实际坏文件测试覆盖这些状态、后续重复扫描不改事实和无关 prod 工作流/租约保持不变。
- 独立命令：在同一应用隔离 worktree 使用上文同一 C6-J 标准 Maven reactor 命令，`MAVEN_OPTS` 不变。
- 实际结果：**2026-09-25 18:52:54 +08:00，退出 0，BUILD SUCCESS，122 passed / 0 failures / 0 errors / 0 skipped，14.104 秒**。三个本次 Surefire XML 已核：RuntimeControl 69、Orchestrator 47、Recovery 6。
- `git diff --check`：PASS。没有手工 javac、复制源码测试工程、共享应用构建或远端操作。

T6J-F01 关闭，T6J 里程碑允许解锁依赖。AC-10、AC-11、AC-12 的维护仓持久门禁、失败恢复入口和最终集成仍待 T6/T7，不据此标记整体 AC 完成。

## T3 — PASS（T3-F01 已修复并独立复验）

### 冻结对象与独立执行

- 工作区：`D:/IntRuoyiWorktree/full-package-release-maintenance`，基线 `3f3aabdc82ab5e85e2f872173a665a361f022725`。只审 T3 Python 与测试增量，不把并行 T2 的包/PowerShell 修改计入 T3。
- 实际冻结 SHA256 已逐一匹配：planner=`5d65cf5ca535d76e38ce13cbc05682665d5bdef52a6086b77694074a3c740592`；collector=`15557ed3b6d6af039e846e6a6408d7d4df551246ffb25708a4e6970a0d28f55c`；Python executor=`f41fa57f50a67aa32a6bf9a0e1ad25000588f67927856631051acf62253b736c`；target-bound-plan 测试=`7164e618976cbc256947b0db59112cf7af0ee21b9c96e50aa65fe340a0a226ed`。
- 会话显式 UTF-8，`RELEASE_TEST_APPLICATION_BACKEND_ROOT=E:/IntRuoyi/IntRuoyiBackend`；未连接 MySQL 或远端。

```powershell
python -X utf8 -m pytest -q scripts/tests/test_release_target_bound_plan.py scripts/tests/test_release_preflight_plan_order.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_migration_supersession_contract.py scripts/tests/test_release_preflight_r20_regressions.py scripts/tests/test_release_target_data_preflight.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t3-c3 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t3-c3.xml --tb=short
```

- 实际结果：2026-09-25 19:34:22 +08:00 开始，退出 0，**156 passed / 0 failures / 0 errors / 0 skipped，14.79 秒**。本次 XML 已核：target-bound-plan 83、plan-order 2、migration-preflight-matrix 12、supersession 11、R20 20、target-data-preflight 28。
- T3 路径 `git diff --check`：PASS。未重复执行执行方已通过且本轮无变化的辅助 116 用例，也不把其历史结果算作独立运行。

### 已确认满足的行为

- API/CLI 使用同包三起点计算不同 APPLY 序列；完整包双摘要相同，生成/复验不改变包内容。prospective 必须显式选择，部署执行器在任何 SQL/台账回调前拒绝无绑定或 prospective 计划。
- 复验重新读取 artifact 实际内容与大小、manifest、执行器及四模块 planner 身份，再重新生成目标动作；改变目标身份、MySQL UUID、schema、完整 ledger、配置、挂载、平台前提或动作，即使重算 planDigest 也不能通过。仅采集时间变化不影响业务状态指纹。
- 失败/运行中/未知 ledger（含包外历史）阻断；已执行摘要漂移不能重放；迁移重复 ID、ledger 数组重复 ID、缺依赖/环被拒绝；supersession 不擦除失败历史。
- 任意 manifest equivalentSha256 不再作为白名单；metadata-only 等价来自已核全文摘要的实际 SQL 字节。平台证据要求 approvedSha256 与 actualSha256 相等且可执行；批准摘要的正式配置采集来源仍须在 T4 实际接入时验证。

### 阻断 T3-F01：collect_target_state 未执行严格 JSON 读取

- 位置：`ops/release/release_target_state_collector.py:157`，`collect_target_state` 直接调用 `json.loads`；Python 默认保留重复 key 的最后一个值。计划器 `_load_json` 的 object_pairs_hook 只覆盖自身文件读取，无法保护先经 collector 解析成 dict 的输入。
- 独立真实 API 负向探针：使用现有 T3 fixture 生成完整合法包和目标快照，把同一个 migrationLedger 项的状态改成 JSON 文本 `"status": "FAILED", "status": "APPLIED"`，写入任务自有 `target-state.json`，随后调用实际 `collect_target_state(root, target_environment='test')` 和实际 `build_target_bound_plan(...)`。
- 实际结果（退出 1）：`COLLECTED_STATUS: APPLIED`、`PLAN_STATUS: passed`、`FIRST_ACTION: SKIP_ALREADY_APPLIED`；断言失败为 `collector accepted contradictory duplicate status and hid FAILED ledger evidence`。这是行为复现，不是源码推测或缺依赖。
- 探针目录：`E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t3-duplicate-cda5b5oa`，仅含任务合成包/快照；没有业务数据、密码或服务器操作。
- 覆盖缺口：当前 `test_duplicate_json_keys_cannot_mask_ledger_or_target_identity` 只调用 planner 私有 `_load_json`，未调用 collector 的实际文件入口，因此 156 PASS 仍遗漏该路径。
- 修复要求：采集文件入口与部署 CLI 采用一致的严格 JSON 读取，重复字段明确失败；增加 collector 文件入口到实际 bound planner 的回归，覆盖重复 status、migrationLedger 或身份字段，验证在计划或 SQL/台账回调之前拒绝。不得让 FAILED 被后写 APPLIED 覆盖，不得以默认值、过滤或静默合并修复输入。

上述为首轮 T3 阻断记录，后续修复及关闭证据如下。

### T3-F01 独立复验 — PASS

- 新冻结 SHA256 已逐一匹配：collector=`01e7c0167b61e0e1afe8b1541bb72155fd8ada67885af96549f62bbc931c2330`；planner=`7a4a430208b90b245ada47ff57c0c0876dce8ace02baa71f1c9ed778414c36ea`；Python executor=`f41fa57f50a67aa32a6bf9a0e1ad25000588f67927856631051acf62253b736c`；target-bound-plan 测试=`12c9e40b90fc073044e3d4ac7422bff75c4892d90b479582cd15332afeb14aaf`。复验后 collector/planner hash 不变。
- 修复核对：重复字段检查集中在 collector 的 `read_json_evidence`，公开 `collect_target_state` 与 planner 的 `_load_json` 均调用它；`object_pairs_hook` 在任何嵌套对象发现同名字段即抛 `TargetStateCollectionError: JSON_DUPLICATE_KEY`，包括两值相同的重复字段。没有过滤、覆盖或默认值路径，错误不回显敏感字段值。
- 执行者新增 11 场景的原代码 RED 为 5 failed / 6 passed；5 个 collector 文件入口负例为 DID NOT RAISE，既有严格 CLI 和有效快照正例通过。独立核对新增场景确实写真实 UTF-8 快照文件并调用公开 collector，再串接 bound planner/executor；不是仅测私有读取函数。
- 独立重用首轮原始失败目录 `tester-t3-duplicate-cda5b5oa` 的同一个文件，未重写输入；真实公开 collector 现在以 JSON_DUPLICATE_KEY 拒绝，退出 0，原探针关闭。

```powershell
python -X utf8 -m pytest -q scripts/tests/test_release_target_bound_plan.py scripts/tests/test_release_preflight_plan_order.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_migration_supersession_contract.py scripts/tests/test_release_preflight_r20_regressions.py scripts/tests/test_release_target_data_preflight.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t3-f01 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t3-f01.xml --tb=short
```

- 独立结果：**2026-09-25 19:52:56 +08:00 开始，退出 0，167 passed / 0 failures / 0 errors / 0 skipped，14.65 秒**。本次 XML 167 个 testcase 已核，分文件为 94/2/12/11/20/28。
- 合法公开采集快照与直接规范化生成相同计划，包/执行器/目标绑定、实际 artifact 字节校验、metadata-only 等价限制、动作重算及 prospective 拒绝均在完整 C3 保持通过；未发现为修复而放宽合同。
- T3 路径 `git diff --check`：PASS。未访问远端或数据库；T2 并行变更未纳入此门禁。

T3-F01 关闭，T3 里程碑允许解锁依赖。T4 的实际采集/PowerShell 主链接入、T7 三个真实 MySQL 基线升级仍属于后续验收；T2/T2P 也由各自门禁判断，本报告不提前放行。

## T2 — PASS（固定组件与安装输入代码合同；AC-02 尚未整体完成）

### 冻结对象和独立命令

- 工作区：`D:/IntRuoyiWorktree/full-package-release-maintenance`，基线 `3f3aabdc82ab5e85e2f872173a665a361f022725`；按更新后的 T2/T2P 分工审查，未修改生产或测试文件。
- 冻结 SHA256 已在验证前后匹配：`ops/deploy/publish-int-ruoyi.ps1`=`ac6aeb96bc6aeafd1f8a0b8111a390073adfad56c1e59832f89ce0a719eacea5`；`ops/release/lib/ReleasePackageGovernance.psm1`=`f28035cd310b711f1ae53f2a74d22bc58e00b651baf827284065bbe433d30096`。
- 会话为显式 UTF-8，`RELEASE_TEST_APPLICATION_BACKEND_ROOT=E:/IntRuoyi/IntRuoyiBackend`；仅只读应用源码，没有访问公司服务器或业务数据库。

```powershell
python -X utf8 -m pytest -q scripts/tests/test_release_full_package_contract.py scripts/tests/test_release_package_governance.py scripts/tests/test_app_release_package_governance.py scripts/tests/test_runtime_control_frontend_deploy_contract.py scripts/tests/test_release_digest_vectors.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t2-c2 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/tester-t2-c2.xml --tb=short
node --test scripts/tests/publish_frontend_deploy_sql_gate_contract.test.mjs
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/tests/verify-release-digest-vector.ps1
```

- Python：2026-09-25 20:17:15 +08:00 开始，退出 0，**147 passed / 0 failures / 0 errors / 0 skipped，150.64 秒**。本次 JUnit XML 已核：完整包合同 45、包治理 78、应用合同 18、前端部署合同 2、摘要向量 4；无 deselect。
- Node：**1 passed / 0 failed / 0 skipped**，退出 0。
- PowerShell：`PowerShell release digest vector passed`，退出 0。
- T2 路径 `git diff --check`：PASS。测试中的最小 Docker tar/依赖条目是合同夹具，生产命令捕获停在运输边界；本报告不将它们算作真实 Linux/npm/Chromium 成功。

### 生产者、清单、校验和消费者核对

- 实际参数绑定只接受 `intruoyi` 与 `full`；两者均选 backend/frontend，full 再选 Website，OnlyOffice 在构建时固定。部署显式传 Component/IncludeOnlyOffice 被拒绝，实际选择来自已验包清单。
- `Get-ReleaseManagedImageReferences` 与生产 `docker save` 使用同一集合；`runtimeImages` 从真实 `docker inspect` 的 reference/id/sizeBytes 产生。治理模块核对每个受选镜像、tar 内 Config/Layers 成员、Config 原始字节 SHA256 与 imageId，以及 backend/frontend 构建证据。运行容器最终 imageId 核对属于 T5。
- `Write-AuthoritativeReleaseManifest` 保持既有 components，新增 installationContractVersion/runtimeImages/platformPrerequisites；`manifest-v1.schema.json` 顶层及 targetRequirements 的 additionalProperties=true。独立额外运行真实 `Get-ReleaseComponentManifestNames` 四种 profile×OnlyOffice 组合，全部与治理期望集合相同且属于 schema.components.enum（含 onlyoffice）；未向 components 引入 scheduler-smoke 新值。该步骤是实际组件生成与 schema 枚举核对，不冒充全量产品构建。
- 组件探针首次加载测试辅助时缺少 `scripts/tests` 的 import 路径，尚未执行生产函数；补充测试辅助 import 路径后四种组合通过。不计为产品 RED。
- 缺 Compose、Website 模板/入口、受管镜像、构建证据、运维脚本、smoke 清单/锁文件/依赖归档或平台声明时，实际治理函数拒绝；工作区同名模板不能补齐。清单和 artifact 摘要自洽也不能掩盖必要输入缺失、空文件或镜像 Config 内容改变。
- Website nginx、`.env` 和部署 report 写包外控制目录。两个目标渲染前后包每个文件字节与双摘要相同；部署不解析 BackendRepoRoot/FrontendRepoRoot/WebsiteRepo 源码根，intruoyi 构建也不要求 Website 源码。
- Linux smoke 准备器按已提交锁文件、固定 Playwright 1.60.0/xlsx 0.18.5，在明确 imageId 的任务容器生成归档；目标只复制解包，未调用 npm install。smoke wrapper 使用实际 imageId 且 `--pull=never`。真实归档可加载性仍由 T2P 证明。
- platformPrerequisites 使用正式配置键引用；批准摘要字段缺失或格式不合法会失败，不将观测文件的摘要自动当作批准身份。实际目标文件可执行性和批准/实际摘要比较属于 T4。

### 逐 AC 与明确未完成边界

| 验收项 | 本轮结论 | 剩余硬门禁 |
| --- | --- | --- |
| AC-01 | PASS：完整组件集合、合法四组合、单组件/部署覆盖拒绝均已实际验证。 | 后续整合改动须保持 C2。 |
| AC-02 | 本轮组件/模板/tar/准备器代码合同 PASS；整体仍未完成。 | T2P 真实官方 Linux 镜像与依赖/浏览器；T4 包内 target-preflight 检查闭包及首写入前真实门禁。 |
| AC-12 | 本轮来源选择、tested v2、三环境、正式授权参数和调用方合同回归 PASS。 | T4/T7 整合、运维文档与全部正式入口验收；本轮不运行业务 E2E或三服发布。 |

以下是主管已明确分配给后续阶段的真实缺口，不能因 T2 通过而视为完成：

1. **T2P 真实 Linux 载荷仍阻塞。** 指定官方镜像 `mcr.microsoft.com/playwright:v1.60.0-noble` 尚未取得，既有 pull/官方请求 TLS EOF。不能用夹具、捕获命令或单元用例替代真实镜像、npm 闭包、库往返和浏览器验收。
2. **T4 部署平台与拉取策略。** 当前部署主链仍读取本地 MySQL 凭据；`publish-int-ruoyi.ps1:7449`、`:7457` 的应用/Website Compose up 还没有明确禁止拉取，OnlyOffice 模板引用 latest。主管已将生产命令的 `--pull never`、`--no-deps` 及相应行为测试纳入 T4。Docker 官方说明默认 missing 策略仍会拉 latest；这一点支持后续门禁必要性，但本轮未在目标环境触发拉取。[Docker pull_policy](https://docs.docker.com/reference/compose-file/services/#pull_policy)
3. **T4 目标预检脚本随包闭包。** 当前 target-preflight 仍只在 build 从应用源码读取，未以包 artifact/manifest 引用及只读声明交付。主管已批准 T4 将固定检查复制入包，部署按包内 reference/SHA/readOnly 执行，并重跑 T2 缺件合同；禁止部署时访问目标外的应用源码。故当前不能宣称 AC-02 所有必要安装输入已经闭合。
4. **T5 真实运行内容身份。** 包内镜像身份已收紧，远端已加载镜像及实际容器 `.Image` 的比对尚待 T5，不由本轮 Config 字节检查代替。

### 附加只读审查：同包执行器来源合同

- 已有有效保护：应用 `RuntimeControlOperationAction.java:203`～`:209` 将 build/test/mark/prod/backup 五种包动作统一纳入工作流；`RuntimeControlServiceImpl.java:254`、`:415`～`:434` 每次派发调用 `ReleaseWorkflowExecutorContract.verify`，后者 `:18`～`:35` 核实际 PS 字节摘要与配置 `expectedPublishScriptSha256` 一致，并固定脚本根/路径。正式预览 `ReleaseWorkflowProductionPreviewService.java:157`～`:175` 将 executorDigest 绑定进授权指纹。因此批准配置不变时不能任意替换 PS。
- 当前强度边界：该 verify 不比较包的 maintenance sourceRoots.commit 与当前 Git HEAD，也不冻结 Python 模块；PowerShell `Assert-ReleaseSourceFreeze` 只在构建的 before-build/before-package 消费。T3 绑定当前实际 PS/planner 身份，能阻止一份旧计划被不同工具链复用，但生成三份新计划时不能单独证明工具链均等于测试时版本。
- 主管已确认 T4 补最小入口门禁：复用包现有 maintenance `sourceRoots.approvedCommit/commit`，核当前维护仓 HEAD 相同且相关工具链 tracked/untracked 源码干净；不要求历史绝对路径相同或应用源码存在，不另建框架。T4/T7 用真实任务 Git 仓的 HEAD/脏文件变化验证拒绝。

在上述边界明确保留的前提下，T2 当前分阶段代码合同无剩余独立阻断，可交接稳定接口给 T4。T2 PASS 不等于 AC-02 或整套完整包发布已经完成。

## T6 验收设计预审 — 尚未实施或验收，不构成 PASS

### 预审范围和现有风险

- 2026-09-25 20:43 +08:00 开始的有界只读预审；T4 正在开发，以下行号描述预审时的源码，正式 T6 验收必须重新定位最终函数。未改生产、测试、计划或状态；未访问公司服务器、数据库或 NAS。三个探针只解析生产 AST/参数或在本地命令边界注入故障，无外部业务写入。
- `publish-int-ruoyi.ps1:130` 的 `Fail` 直接 `exit 1`。它尝试释放 FAILED 锁，释放失败后仍在 finally 把 held/releasing 置 false。实际 AST 探针返回 exit 1，出现 `PROBE_RELEASE_CALLED` 和 `PROBE_FINALLY_HELD=False`，外层 catch 标记未出现。因此仅在总 catch 中新增持久失败记录不能覆盖全部退出路径，内存 held=false 也不能证明远端释放成功。
- 成功路径当前为 `:7495` NAS history → `:7499` 数据库锁 APPLIED → `:7516` 后远端/本地清理；清理失败时锁已终态。`Write-NasReleaseDeploymentHistory` 的历史文件和 latest 文件分两次写，Disconnect 在 finally，任一步都可能在部分写入之后失败。不能把“历史存在”“锁 APPLIED”或一个 SUCCESS JSON 单独作为最终完成。
- `Invoke-ReleaseOperationLockRelease:6075` 的生成命令仍以 `| grep '^LOCK_RELEASED$'` 结束。独立探针提取实际函数、生成实际 shell，仅让 docker 命令输出 LOCK_RELEASED 后返回 17，实际 shell 退出 **0**。这是内层退出码被管道掩盖；T1 已通过的外层 SSH exit17 拒绝不覆盖此分支。首个探针因本机 bash 启动 stderr 的编码产生读取线程解码错误，随后保持同一 shell、改用字节捕获确认相同 17→0 结果；没有切换执行环境或忽略产品失败。
- `recover-release-operation-lock.ps1` 当前只有执行器/lease/心跳/迁移台账检查，没有文件系统持久部署门禁；过期心跳和 FAILED/APPLIED 锁不能证明没有应用/配置写入。
- 该脚本 `DatabaseName` 在 `:6` 的 ValidatePattern 不允许 `-`，默认却为 `ruoyi-vue-pro`。使用真实 AST ParamBlock 的只读绑定探针确认：显式 `task_schema` 接受，显式 `ruoyi-vue-pro` 拒绝，`bad;schema` 拒绝。T6 必须修正合法带连字符库名的真实参数合同，并继续安全拒绝非法值；不能只改字符串测试。
- `release_deployment_transaction.py` 明确是本地测试模拟，却把 env/images 文件写入描述为原子并在异常中自动还原；其测试不能证明真实 PowerShell、文件系统、MySQL 与 NAS 的最终化或恢复语义。本轮不建议把该模拟升级成第二个发布框架。

### 最小实现必须保持的不变量

1. 持久权威门禁位于已批准的目标 `.release-state/<environment>/`，不在包内或本次临时控制目录。门禁/operation/回执至少绑定环境、目标主机与数据库实例、operation/lease、releaseTag、包双摘要和计划身份；同标签不同尝试不能覆盖旧失败事实。路径与标识校验必须在读写前完成。
2. 首次可能运行写入之前，先成功持久记录 STARTED/writeAttempted 和原/目标身份；写记录本身失败不得进入下一运行写入。所有 `throw`、直接 `Fail/exit`、进程被终止都必须留下可由下一进程识别的未完成事实，不能依赖 catch 必然执行。
3. 最终化前将门禁保持在 FINALIZING/等价阻断状态。清理、历史、回执、数据库终态及其必要回读必须全部成功，才执行最后一个持久完成提交点；该点之后不得再安排可能失败的必需清理/历史/释放工作。各文件在同一文件系统内临时写再原子替换，只保证单文件替换，**不宣称跨文件系统/MySQL/NAS 原子事务**。
4. 任何前置步骤失败或确认未知，现存未完成门禁仍阻断，即使数据库实际已经 APPLIED。不能通过重新读取一个成功文字、写 FAILED 锁、超时、删除临时目录或清理旧 gate 来放行。缺失/损坏/重复字段/未知 schema 的门禁也不能默认为空闲；首次正式准备与“丢失已有证据”必须有可验证的区别。
5. 下一部署在取锁前和取锁后都消费同一门禁。显式恢复入口必须在任何恢复 UPDATE 之前消费该门禁；无法读取门禁本身就是阻断，不能因 DB 心跳过期继续。恢复入口当前只允许 test，不能隐式扩大到 prod/backup 或自动修复事实。
6. 同时保留原始执行错误、观察错误和最终化错误的脱敏身份；未知实际镜像/配置/迁移状态标明 unknown，不以期望值代替实际值。SSHD/mysql/docker 的真实非零退出码优先于任何成功文本。
7. 对“最后持久提交已完成但客户端确认丢失”明确区别执行事实与响应事实：调用方结果可以 unknown，不能重放部署。后续只有读取到绑定一致且能与锁/历史/回执对账的已提交完整证据才可能认定已完成；缺任一项继续阻断。这是完成事实核对，不是自动恢复或自动回滚。

### 有限故障矩阵（供 T6 实现与独立验收）

| 编号 | 在真实路径注入的有限场景 | 必须观察到的结果 |
| --- | --- | --- |
| F00 | 正常迁移/安装/验证/清理/历史/回执/锁终态全部完成 | 最后提交点才产生成功；重启读取仍能对账；下一合法部署可进入。 |
| F01 | gate/operation/receipt 读取分别返回 SSH 非零、空/缺失、截断 JSON、同值/异值重复 key、未知 schema | 在任何部署或恢复写入前拒绝；不默认 READY、zeroWrite 或 SUCCESS。 |
| F02 | 门禁环境、主机/DB UUID、operation/lease、releaseTag/包摘要各换一项；门禁在首次读后、锁内复核前被换为另一个未完成 operation | 绑定不符或锁内漂移拒绝；不覆盖另一 operation 的持久事实、不修改无关环境租约。 |
| F03 | 首次 STARTED/writeAttempted 写入的临时文件创建或原子替换失败 | 运行写入计数为 0；没有无证据迁移/切换；错误原样可追踪。 |
| F04 | 任务真实 MySQL 第一步 DDL/业务行检查通过，第二步 SQL 失败；再分别让 FAILED ledger 写入或实际状态观察失败 | 已完成结构/历史行可读，未自动回滚/修台账；原 SQL 错误与后续错误分别保留；新进程阻断。 |
| F05 | 持久 STARTED 后 `.env` 切换、容器切换、内容身份或健康校验分别失败 | 记录实际混合/未知状态及所在阶段，writeAttempted=true；不得伪报恢复旧版或普通可重试。 |
| F06 | 同一阶段分别通过生产 `Fail` 和普通 throw 失败，锁释放再失败 | 两条路径均留下持久阻断；退出非零，未把 held=false 当作远端已释放证明；原错误不被 cleanup 错误覆盖。 |
| F07 | 实际生成 shell 中 docker/mysql 先输出成功标记再退出17；另测整个 SSH 返回17且含成功标记 | 两种均非成功；生产 SSH/SQL 载体不能由 grep 掩盖内部退出；未确认终态保持 unknown/阻断。 |
| F08 | FINALIZING 后逐项注入：本地清理、远端清理、history文件、latest文件、NAS断开、receipt临时写/替换失败 | 每个变体都无整体成功，gate 保持 FINALIZING/RECOVERY_REQUIRED；下一部署及显式恢复拒绝。每个变体独立起点，不串联污染。 |
| F09 | 锁 APPLIED UPDATE 真实失败；以及 UPDATE 实际成功但 SSH 确认丢失 | 两者在最后完成提交前仍被文件门禁阻断；不以数据库 APPLIED 单独放行，不自动删除记录。 |
| F10 | 只终止任务子进程：STARTED后、第一条真实DDL后、receipt/history写后、DB APPLIED后但最终门禁提交前；删除本轮临时control后重启 | 独立新进程的两个入口仍读到未完成事实；heartbeat过期不放行。另设已完成最后提交之后的正例，避免把完整完成事实误作必须重做。 |
| F11 | 显式 recovery：不确定写入门禁+RUNNING/FAILED/stale heartbeat；可信零运行写入正例；显式合法连字符库名与非法库名/路径 | 有未解决运行写入时恢复 UPDATE 为0；可信零写入沿原显式合同处理，不能仅因过期获准。真实参数绑定接受合法库名，SQL标识/参数安全，所有运行仅任务隔离 schema。 |

F08 的 7 个最终化故障点必须逐一参数化，不能只测其中一个；F01/F02/F10 为列明的有限变体，不要求无界随机测试。最后一次原子提交的“写前/写后”中断以是否存在完整、绑定且一致的提交证据判定，不能把跨存储确认窗口当作可保证原子性。

### 真实生产函数与测试切入点

- **状态读写**：最终新增 `ReleaseDeploymentEvidence.psm1` 的实际导出函数；在文件 I/O 或进程运输边界注入失败，真实写/读任务目录，并用独立 PowerShell 进程重读。不能另写内存状态机当被测实现。所有 JSON 入口执行重复字段/损坏证据负例。
- **退出与传输**：AST 提取现有 `Fail`、`Invoke-SshCommand`、`Invoke-SshCapture`、`Invoke-ReleaseOperationLockRelease`，保留其真实错误/退出逻辑。`Fail` 用独立任务进程，验证外层 catch 是否执行及持久 gate；SQL 载体只在 docker/SSH 运输边界换到任务资源或注入非零，不复制 SQL 算法。
- **迁移和部分写入**：实际 `Invoke-RequiredDatabaseSqlScriptWithState`、`Invoke-RequiredDatabaseSqlScripts` 与迁移台账函数，生成 SQL 后在既有任务独占 MySQL 执行；预先校验 task/container/volume，使用随机任务 schema。至少一组 schema 名包含 `-` 并正确引用，不让全为下划线的 fixture 掩盖真实默认名称合同。
- **切换与最终化**：实际 `Switch-RemoteRuntimeEnvNext`、最终 T5 身份验证函数、`Write-NasReleaseDeploymentHistory` 和主部署最终化调用段；在任务自有文件/真实 MySQL 上验证阶段先后与错误后读回。NAS 传输可映射到任务临时目录以测试多文件部分落盘，但必须标明未证明真实 NAS 可用性。
- **恢复入口**：实际运行 `recover-release-operation-lock.ps1` 参数与主链，SSH 运输边界限定任务容器。先对真实 ParamBlock 验证显式 `ruoyi-vue-pro`，再以任务专属连字符 schema 验证生成 SQL；保留原确认文本/本机执行器终止/所有权合同。未解决 gate 或 gate 读取失败时断言真实恢复 UPDATE 未执行。
- **成功与重入**：门禁最终提交之后真实读取 lock/history/receipt 和目标身份，再走下一部署取锁路径；在 lock 已 APPLIED、gate 尚 FINALIZING 的窗口启动另一个任务进程，证明双重门禁检查阻止继续写入。

本节是 T6 的事前风险与验收设计建议。所有 F00～F11 均尚未作为 T6 正式套件运行；不得因本预审结束将 T6、AC-09/10/11 或最终任务标为通过。

## 2026-09-26 T4 验收准备，非最终 PASS

- 独立测试者本轮仅只读核查 TC-05/06/07、T4 写范围、生产调用链和现存测试；执行者尚未冻结，未运行 C4/C2，不把中间工作树定为最终 FAIL。无生产/测试/计划/state 修改、无 Docker 或服务器操作。
- 已确认主部署段顺序为 Write-ReleasePreflightPlan → Enter-ReleaseOperationLock → Write-ReleasePreflightPlan -Verify → 首个运行写入。应用/Website 实际启动段均含 --no-deps --pull never；完整包源绑定在目标运行读取前调用。此为静态准备事实，不能代替正式执行结果。

### 有限确定性风险与漏测

1. **T4-PREP-01，目标数据库身份断裂（代码事实）**：Read-ReleaseTargetSnapshot 接受任意合法 MYSQL_DATABASE，Get-ReleaseTargetMySqlCommand 以该库采集 schema/ledger 和执行包内 checks；但 Get-ReleaseOperationLockSchemaState、Invoke-ReleaseOperationLockAcquire、Assert-ReleaseOperationLockOwnership 及 Invoke-RequiredDatabaseSqlScriptWithState 的原始生产载体仍固定 ruoyi-vue-pro。若配置库 A 与固定库 B 同时存在，计划绑定 A 而控制/迁移写 B。应明确拒绝非受支持库名，或令实际写入载体和计划身份统一；最终需生产原始载体一致性行为证据，运输边界直接替换库名不能证明此合同。
2. **T4-PREP-02，凭据参数主链缺口（代码事实）**：新 snapshot helper 在容器内展开 MYSQL_ROOT_PASSWORD；既有 acquire/ownership/heartbeat/release/迁移载体仍将 mySqlRootPassword 拼接入 shell（MYSQL_PWD=... 或 -p...）。只测新 helper 的特殊字符密码不足以证明主链可运行，最终需涵盖实际锁和迁移载体，不输出真实凭据。
3. **T4-PREP-03，固定工具链有限负例缺失（覆盖事实）**：test_executor_source_binding_checks_real_git_content_not_historical_absolute_root 目前覆盖干净异路径、HEAD 不符、Python tracked 改动；T4 明确要求的 PS tracked 与相关 untracked 负例尚未覆盖。最终应参数化这两个有限场景，并确认均在远端写入之前拒绝。
4. **T4-PREP-04，包内 checks 端到端合同缺口（覆盖事实）**：当前 sql_preflight_gate 用例手工复制检查文件、替换 digest helper 为 fixture；readonly-deploy-gate 仅对 test 环境的手工完整包执行真实 SQL。还需实际 Copy-RequiredDatabaseSqlScripts → New-ReleaseRequiredSqlManifestEntries → artifacts/packageDigest → 包内 checks 的行为链，并覆盖 test/prod/backup 目标选择、缺 PASS、环境排除、非 schema 且 requiresTargetPreflight=false/缺失不能绕过。已有 Python contract/治理负例是补充，不能代替部署实际消费。
5. **T4-PREP-05，启动失败观察不足（覆盖事实）**：四种组合的实际启动命令已有行为覆盖；缺镜像用例仅直接调用检查函数并让首个 image inspect 失败，未逐一覆盖所选 image 缺失及主启动段零启动断言。最终应参数化所选镜像和组合，在真实主启动段观察 fail-fast 后无 compose up/pull/平台初始化调用。
6. **回归调整提示**：C4 的 test_release_sql_preflight_gate.py 仍含要求 SKIPPED_* 批写及 reset/post-import 打包的旧静态断言，可能与 T4 正式合同冲突；由执行者按既定 RED/GREEN 验证并更新，不由独立测试者修改。

### 冻结后正式验收入口

- C4：python -X utf8 -m pytest -q scripts/tests/test_release_readonly_deploy_gate.py scripts/tests/test_release_operation_lock_mysql_behavior.py scripts/tests/test_release_workflow_preflight.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_target_data_preflight.py
- C2：python -X utf8 -m pytest -q scripts/tests/test_release_full_package_contract.py scripts/tests/test_release_package_governance.py scripts/tests/test_app_release_package_governance.py scripts/tests/test_runtime_control_frontend_deploy_contract.py scripts/tests/test_release_digest_vectors.py；node --test scripts/tests/publish_frontend_deploy_sql_gate_contract.test.mjs；powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/tests/verify-release-digest-vector.ps1。
- 所有命令使用维护任务 worktree，真实 MySQL 只由 RELEASE_TEST_MYSQL_RUNTIME_CONFIG 指定既有隔离资源；禁止打印 runtime JSON，独立 basetemp 避免与执行者争用。Docker 和跨目录产物继续经正式 require_escalated 审批。
- 等待主管明确冻结交接后记录 HEAD、受验 diff/文件 hash、完整命令/退出码/测试数，再按 TC-05/06/07 判定；当前没有 T4 最终 PASS 结论。容量实现仍在进行，本轮不将未冻结容量中间版本列为最终缺陷。
## 2026-09-26 T4 容量函数有界静态审查，非正式验收

范围仅 ConvertTo-ReleaseCapacityInteger、Get-ReleaseCapacityReservation、Assert-ReleaseTargetCapacity 与 Read-ReleaseTargetSnapshot/锁内重采调用关系。未执行 PS、Docker、C4/C2；未修改生产或测试文件。

- **CAP-PREP-01，归档展开预算不足**：dependencies.tar 按 2 × tar 字节预留 runtime 空间，Docker 按 image archive 字节 + logical image.Size 预留；两者没有按内部成员的目标文件系统块占用计费。具体反例：tar 含 100 个普通 1-byte 文件，在 4 KiB 文件系统解包需要至少 400 KiB 文件数据块，再加约 110 KiB 的 tar 自身，而当前对该 tar 只预留约 220 KiB。目录和元数据尚未计入，因此反例不依赖它们。需要基于实际归档常规成员长度/数量及目标 blockSize 的明确预算，或可证明覆盖此反例的上界。现有 exact-boundary 测试将被测函数自己算出的 requiredBytes 回喂，只证明比较符与聚合，不能证明生命周期预算正确。
- **CAP-PREP-02，独立数据盘仍只有一块空间门槛**：parts.data 固定为 1 byte，独立 data 文件系统在 blockSize=1024、availableBlocks=1 时可通过；这不证明迁移所需空间，且仍接受仅 1 KiB 的数据盘。若当前容量门禁范围仅限包制品写入，应明确数据迁移容量合同尚未覆盖，不能据此声称数据库容量已验证；若需覆盖原 data-free 门禁，必须定义真实、可审核的容量前提和相应负例。
- 其余静态观察：同 st_dev 的角色累加且取最小可用值；不同 st_dev 分别比较；artifact/image 大小限制整数与 Int64 范围，累加使用 decimal 并检查边界；Docker 只允许 classic overlay2 且明确拒绝 containerd 标记。探针 test/stat 使用 set -eu，SSH Ok 和完整三整数格式共同拒绝失败/截断。Read-ReleaseTargetSnapshot 在初始和锁内 verify 都重新执行容量检查。以上未见新增确定性缺陷，仍须冻结后动态验证。

本节只记录静态反例和观察，不撤销执行者既有 20 项定向 PASS，也不把它们提升为 T4 最终验收。
## 2026-09-26 T2 修复窄范围与 T2P 正式独立验收：PASS

本轮独立测试者未参与实现；主管冻结 PS/治理后验收。工作树 HEAD=3f3aabdc82ab5e85e2f872173a665a361f022725，包含未提交任务实现；结果绑定下列文件 hash，不以 HEAD 单独代表受验版本。

### 冻结身份与命令

- PS 前后 SHA256 一致：2ebdc688c72b494af9e13a8d3297d20131c999789c3dab0bd942ccbe87cf0448。
- 治理模块前后 SHA256 一致：a1501844a20ef2bd74eeb7fecc85e376535967f6fd7b4880697e7f8915d16c75。
- 集成测试 SHA256：7dd95a93f86fad43d1d9f5021c2180e6f24c998a99952d959592caa541c1714d；完整包测试 SHA256：7dba34570e8e89521b79137a0f7fba6e40f57318cd0bf139d22bdd5a012ad8b7。
- 运行目录：D:/IntRuoyiWorktree/full-package-release-maintenance。
- 环境：RELEASE_TEST_SMOKE_PAYLOAD_ROOT=E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/smoke-payload；RELEASE_TEST_APPLICATION_BACKEND_ROOT=E:/IntRuoyi/IntRuoyiBackend。
- C2P：python -X utf8 -m pytest -q scripts/tests/test_scheduler_smoke_linux_payload_integration.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/smoke-payload/pytest-t2p-independent-20260926 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/smoke-payload/t2p-independent-20260926.xml → exit 0，2 passed，78.63s。
- 归档修复：python -X utf8 -m pytest -q scripts/tests/test_release_full_package_contract.py -k 'containerd_archive or image_identity_is_derived_from_config' --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/smoke-payload/pytest-t2-archive-independent-20260926 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/smoke-payload/t2-archive-independent-20260926.xml → exit 0，10 passed / 51 deselected，18.07s。
- 权限申请通过后执行。归档测试首次审批超时未执行，按允许仅重试一次成功；不属于产品 FAIL，不关闭审批或改走旁路。未运行完整 C2；执行者报告的 T4 旧 Apply-ReleaseRuntimeEnvPackage 静态合同失败仍归 T4 完整 C4/C2 关口。

### 真实制品与离线运行证据

独立证据目录：E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/smoke-payload/integration-58dd656242f1476cb460d84561e66dc4。

- 官方镜像：mcr.microsoft.com/playwright:v1.60.0-noble；实际 imageId=sha256:aa88ecce96d1abff3797127aa1b22171134b4f217b99e81f0c01b2c1b1bd2992。准备器直接使用该 imageId，官方身份回执中的 config/所有层字节一致性经测试核对；没有替换镜像来源、版本或 node_modules。
- 离线容器 network=none、无端口、无非 loopback 网卡，实际容器镜像一致，exit 0。真实 playwright=1.60.0、xlsx=0.18.5，11 个锁文件依赖逐项版本通过；xlsx 含中文数据往返 16025 bytes；Chromium=148.0.7778.96，/ms-playwright/chromium-1223/chrome-linux64/chrome，实际页面操作与关闭通过。
- dependencies.tar：31774720 bytes，sha256=6a87a34658c644e7f46357ba13f65e79ecec00e33c6bdadae7a2decb29c019e8。
- package-lock.json：5143 bytes，sha256=e06792ca48ce60d50dc942e913e1bf699777f3341fe7ac25a198b96a0f644c68。
- 原始 docker save 归档：922632192 bytes，sha256=72d6d7c3cfee268c08c2f8f190f43644aa89d408698247c25165f79710d6f9be。
- 含原始 smoke 归档内容的完整格式治理包 image tar：922644480 bytes，sha256=77804c42b05ea69231b04dec1c46985d3b808c1bd05d0691429a9c798b787f8b。
- packageDigest=85bb0f50b3c590f43e1187095ca008da2b11021e79d271e46b4bd5be7607b345；manifestDigest=62c9b8fa6007f7ede3c0c59f2534902041cd815a65e296f2ae7f443957430d6a；真实治理 exit 0，镜像归档/依赖 tar 各自改字节或缺失均拒绝，恢复后重新通过。
- 完整格式治理包中的其它应用组件为格式 fixture，仅 smoke 镜像/载荷是真实制品；不据此证明 backend/frontend/Website 已构建或真实应用已发布。

### 严格拒绝与窄审查

归档专属 8 个拒绝场景全部通过：伪造 descriptor bytes、错误 config 链接、错误 layer 链接、config 内容漂移、layer 内容漂移、缺 layer blob、descriptor size 不符、tag 绑定不符。另有合法 descriptor 链正例与原 classic config 内容身份负例。审阅确认没有遇到 OCI 后直接接受/仅按 tag 接受：新分支要求固定 tag→descriptor digest/size→config digest/size→有序 layer digest/size 的实际归档字节链；classic config 内容校验保留。准备器改为真实 UTF-8 shell 文件载体，运行实际 npm ci、库版本与浏览器，再确认 container ExitCode 和 tar，finally 清除本次容器/脚本。窄审查未发现阻止此修复放行的新问题。

### AC 映射与边界

- TC-14/T2P：PASS。
- AC-02：真实 Linux 载荷、离线库/浏览器与包字节绑定子项 PASS；完整 AC-02 仍须其它门禁，不标整体通过。
- AC-08：smoke 实际镜像/归档身份子项 PASS；所有应用运行镜像仍由 T5 验收。
- AC-12：锁定版本、正式准备器/治理窄修复子项 PASS；完整工作流/三环境/Java 合同仍需后续 C4/C2/C7。
- 完整 C2、T4、T5、T6、T7 和发布就绪均未据此通过。未连接任何服务器、业务服务或真实产品页面；仅任务测试容器及缓存，未清理执行者产物。

独立验收已结束，可释放本轮 PS/治理冻结供主管按任务图安排后续执行；后续修改若影响本窄合同须重新执行相关验证。
## 2026-09-26 T4 最终冻结版本有界静态复核，动态门禁待交接

主管明确本轮只读，执行者完整 C4 尚在运行，完整 C2 审批两次超时；本测试者没有申请或执行 C4/C2，也没有改用其它入口绕开审批限制。仅追加本节，未修改产品/测试/计划/state。

受阅身份：publish-int-ruoyi.ps1 SHA256=8f398d1527e71f3ecea0233d1e4773aba9521618dec175170bed8e570fb7e56c；ReleasePackageGovernance.psm1=a1501844a20ef2bd74eeb7fecc85e376535967f6fd7b4880697e7f8915d16c75；release_target_state_collector.py=01e7c0167b61e0e1afe8b1541bb72155fd8ada67885af96549f62bbc931c2330；test_release_readonly_deploy_gate.py=8ca420c6e55db2863cdb6445d62360b2cf309d0044e424e848f581417ac92a20。

### 既有发现的静态关闭情况

- T4-PREP-01/02：实际部署锁 schema/acquire/ownership/heartbeat/release、迁移与台账载体已统一 Get-ReleaseTargetMySqlCommand；schema 查询使用 DATABASE()，密码由容器环境展开，不再把宿主密码拼入这些实际命令。新增测试捕获生产命令，并在两个真实任务库间验证只有绑定库发生变化；其运输适配只替换 Docker 调用，不修改 DB 参数或 SQL。代码与测试设计层面已关闭，运行结论待正式 C4。
- CAP-PREP-01：Read-ReleaseArchiveCapacity 实际读取 dependency tar 与 Docker 层 tar，汇总常规文件、目录、链接等成员尺寸/数量；按目标 blockSize 对成员取整累加，Docker 使用成员结果与声明 size 的较大值并计入导入归档。新增 2048 个 1-byte 文件用例以独立的 2048×4096 下界断言，未再用被测预算输出证明公式。代码与测试设计层面已关闭，运行结论待正式 C4。
- CAP-PREP-02：DatabaseCapacityReserveBytes 默认 1073741824，并拒绝低于 1 GiB 的显式值；数据库角色独立计入文件系统预算，增加 data-tiny/db-under/db-floor。1 GiB 是明确平台最低保留量；需要更大迁移增长时必须提高，不把它当任意数据量迁移的充分估算。上轮一字节/一块门槛已替换。
- collector 稳定合同：返回快照不再混入动态 capacityEvidence；当前可用字节留在 ReleaseTargetCapacityEvidence，文件系统身份单独保存并在 -Verify 时比较；Read-ReleaseTargetSnapshot 每次实际复查容量，Write-ReleasePreflightPlan 明确传递 -Verify。正常空间波动不会污染 schema/ledger/config 等稳定指纹；FS身份漂移或空间不足仍阻断。
- T4-PREP-03：真实 Git 用例已补 PS tracked 改动及相关 untracked Python 文件，两者恢复独立起点后检查 SOURCE_DIRTY；原干净异路径、HEAD、Python tracked 案例保留。
- T4-PREP-04：新增实际 Copy-RequiredDatabaseSqlScripts→New-ReleaseRequiredSqlManifestEntries、真实摘要、artifacts 包装及三环境包内消费；删除源码输入后消费 checks。有限负例包括缺件、hash、缺/重复PASS、非只读标记、危险SQL、引用/环境错误、false/缺失requiresTargetPreflight，随后核任务业务行未改。代码和测试设计层面已补齐。
- UTF-8：测试先应用与当前生产入口一致的四行 UTF-8 无 BOM 初始化，再调用真实 Invoke-ProcessCaptureWithInput，并将中文 stdin 原始字节 hash 与 Python 收到的字节 hash 比较。这里是相同初始化文本+真实函数测试，未宣称运行整个生产入口。

### 仍保留的既有覆盖缺口

T4-PREP-05 未变：缺镜像用例只直接运行 Assert-ReleaseSelectedImagesLoaded 且首个 inspect 失败；四组合主启动段用例将该检查函数替为空。现有测试尚未把逐所选镜像缺失与真实主启动段串联，从而观察零 compose up/pull/平台补齐。此为既有 TC-07 有限验收要求，不是新增产品范围；函数循环实现静态未发现确定性错误，但该覆盖项不能先标已完成。

本轮受审有限范围没有发现新的确定性代码缺陷；上述静态关闭不等于 T4 PASS。最终 C4/C2、完整调用合同与正式独立验收仍待主管明确交接和合法审批。
## 2026-09-26 T4 正式独立最终验收：PASS

### 独立性与执行通道

本测试者未参与产品实现，负责提出精确 C4/C2 命令及判定标准、静态复核、独立读取本轮新 JUnit、核对前后文件 hash 并最终判定。旧测试代理执行上下文没有继承宿主完全访问设置：不带 sandbox_permissions 的 docker inspect 返回 exit 1，permission denied while trying to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine。没有使用 escalated 或其它旁路。由于新代理名额已满，由同样未参与产品实现的主线程以操作员身份在用户已启用的宿主权限下实际运行本轮新测试。以下为主线程操作员真实重跑、独立测试者审核结果，不称为本测试者工具亲自执行，不复用执行者旧 XML。

### 冻结版本和完整命令

工作目录 D:/IntRuoyiWorktree/full-package-release-maintenance。环境 RELEASE_TEST_MYSQL_RUNTIME_CONFIG=E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/mysql-runtime.json；RELEASE_TEST_APPLICATION_BACKEND_ROOT=E:/IntRuoyi/IntRuoyiBackend。真实 MySQL 由任务 runtime 校验容器/卷归属，凭据未打印。

- publish-int-ruoyi.ps1 前后 SHA256：8f398d1527e71f3ecea0233d1e4773aba9521618dec175170bed8e570fb7e56c。
- ReleasePackageGovernance.psm1 前后 SHA256：a1501844a20ef2bd74eeb7fecc85e376535967f6fd7b4880697e7f8915d16c75。
- test_release_readonly_deploy_gate.py 前后 SHA256：a6bd59d2a5148d686f1623efff7b2491ee641c0582715e7b4921b5ce27a15e3e。
- 独立测试者在正式执行前及收到结果后均直接读取上述 hash，全部与冻结交接一致。代码冻结期间未修改产品。

C4：python -X utf8 -m pytest -q scripts/tests/test_release_readonly_deploy_gate.py scripts/tests/test_release_operation_lock_mysql_behavior.py scripts/tests/test_release_workflow_preflight.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_target_data_preflight.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t4-independent-final-c4 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t4-independent-final-c4.xml。

C2：python -X utf8 -m pytest -q scripts/tests/test_release_full_package_contract.py scripts/tests/test_release_package_governance.py scripts/tests/test_app_release_package_governance.py scripts/tests/test_runtime_control_frontend_deploy_contract.py scripts/tests/test_release_digest_vectors.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t4-independent-final-c2 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t4-independent-final-c2.xml。

补充：node --test scripts/tests/publish_frontend_deploy_sql_gate_contract.test.mjs；powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/tests/verify-release-digest-vector.ps1；git diff --check。

### 本轮真实结果

- C4 exit 0，226/226 PASS。独立读取新 XML：timestamp=2026-09-26T10:10:08.447515+08:00，suite time=495.422s（命令摘要495.47s），errors=0、failures=0、skipped=0；实际 testcase=226，五个指定测试文件均发现并执行。
- C2 exit 0，163/163 PASS。独立读取新 XML：timestamp=2026-09-26T10:10:53.835644+08:00，suite time=145.049s（命令摘要145.11s），errors=0、failures=0、skipped=0；实际 testcase=163，五个指定测试文件均发现并执行。此前 T4 的 Apply-ReleaseRuntimeEnvPackage 旧合同失败在本冻结版本与本轮新结果中已关闭。
- 操作员本轮回传 Node 1/1 PASS、PowerShell digest vector PASS、git diff --check exit 0；未把此前执行者报告当本轮证据。
- 操作员在 mysql_runtime 归属检查后运行 SHOW DATABASES，本轮结束仅 information_schema、mysql、performance_schema、sys；无任务测试 schema 残留。未删除或修改非任务容器/数据库。
- C4/C2 使用各自固定独立 basetemp/XML 并行运行，C2 不访问 MySQL；未访问服务器或真实业务服务。

### TC/AC 判定与已发现缺口关闭

- TC-05 / AC-04 的 T4 部分：PASS。完整历史台账采集、真实锁/schema 行为与非法/失败条件阻断具备本轮 C4 证据；预检不以成功状态过滤历史事实。
- TC-06 / AC-05、AC-12 的 T4 部分：PASS。计划先于锁、锁内重采后才允许运行写入；真实 schema/data 漂移拒绝且不重写旧计划；固定维护来源 HEAD、Python/PS tracked、untracked 工具链漂移拒绝；实际锁/迁移/台账载体绑定同一配置数据库且不拼宿主密码。T4-PREP-01/02/03 已闭环。
- TC-07 / AC-06 的 T4 部分：PASS。平台/控制根/挂载/工具/运行态缺失不自动补齐；归档逐成员块容量和明确 1 GiB 数据库最低保留量、整数边界、同/异文件系统、锁内容量及身份漂移负例通过；真实 UTF-8 stdin 字节无 BOM；CAP-PREP-01/02 已闭环。容量保留量是平台最低条件，不是所有迁移增长的充分保证，较大计划仍需显式更高保留量。
- TC-07 包内 checks / AC-06、AC-07、AC-12 的 T4 部分：PASS。实际 builder 复制 checks/生成摘要，三环境部署消费包内文件，删除源码输入仍可运行；缺件/hash/缺或重复PASS/非只读/危险SQL/错误引用和环境/false或缺requiresTargetPreflight 不能绕过；真实任务业务行保持。T4-PREP-04 已闭环。
- TC-07 启动策略：PASS。独立 XML 明确包含新增20项：intruoyi/full × OnlyOffice 四种组合4个正例，以及逐所选 backend/frontend/scheduler-smoke/website/onlyoffice 缺失16个负例。测试运行实际主启动片段与真实 Assert-ReleaseSelectedImagesLoaded，仅替换 SSH 运输；正常路径检查全部所选镜像和 --no-deps --pull never，缺任一项 commands 为空且拒绝对应镜像。T4-PREP-05 已闭环，不再仅用单函数失败替代主段观察。
- T4 修改要求的完整 C2 回归及 Node/PS 摘要验证：PASS。治理正式身份未放宽；T2P 真实离线载荷证据仍见前节，后续集成还须按计划验证。

### 最终结论

T4 在已批准本地隔离范围内正式独立 PASS，可解锁 T5。此结论不等于三服发布就绪，不把 T4 的部分 AC 证据提升为所有 AC 完成；T5 镜像/静态载荷真实身份、T6 持久阶段/恢复门禁、T7 最终集成与收尾仍是必要任务。测试者没有修改代码、计划或机器状态，任务推进由主管执行。
## 2026-09-26 T5 正式独立验收：PASS

### 执行通道与冻结身份

沿用已明确的独立操作员通道：本测试者未参与实现，提出命令/判定标准、只读审查代码和本轮新 XML，最终独立判定；同样未参与产品实现的主线程在完全访问宿主实际运行。旧测试代理未尝试 Docker、提权或绕过权限。没有将执行者 C5/C2 旧报告充当独立重跑。

本轮独立读取冻结前后生产文件及最终测试文件 hash，均与操作员交接一致：

- publish-int-ruoyi.ps1：c2358a404ac3d40af464d8124658cfe5763f1ff29a80eedec0ab8a70b2bba83b。
- ReleasePackageGovernance.psm1：8fb2cd2ea9c2117eb23229a8ca9cb179349f0eb01fce51bf28531a90fdd11deb。
- test_release_runtime_identity.py：595b480a1d1f87f48017268c00893b955d06fd310eb839db2c0b4d45f481ea60。
- test_release_readonly_deploy_gate.py：88898ae721b2c3d900281d38b3125a27a21c5cb50d50c0a2fd003cff11da5f1a。C4 包解析测试载体补齐 runtimeImages/verifiedImageContent 后才冻结和独立运行。

运行目录 D:/IntRuoyiWorktree/full-package-release-maintenance。C5 不读取额外环境变量，其 fixture 严格核固定任务 classic engine、ID、codex.task、network none、零端口、专用卷、overlay2 和干净命名空间。C2/C4 使用 RELEASE_TEST_APPLICATION_BACKEND_ROOT=E:/IntRuoyi/IntRuoyiBackend；C4 另使用 RELEASE_TEST_MYSQL_RUNTIME_CONFIG=E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/mysql-runtime.json，凭据不打印。

### 本轮命令与独立读取结果

1. python -X utf8 -m pytest -q scripts/tests/test_release_runtime_identity.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t5-independent-final-c5 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t5-independent-final-c5.xml。
2. python -X utf8 -m pytest -q scripts/tests/test_release_full_package_contract.py scripts/tests/test_release_package_governance.py scripts/tests/test_app_release_package_governance.py scripts/tests/test_runtime_control_frontend_deploy_contract.py scripts/tests/test_release_digest_vectors.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t5-independent-final-c2 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t5-independent-final-c2.xml。
3. python -X utf8 -m pytest -q scripts/tests/test_release_readonly_deploy_gate.py scripts/tests/test_release_operation_lock_mysql_behavior.py scripts/tests/test_release_workflow_preflight.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_target_data_preflight.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t5-independent-final-c4 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t5-independent-final-c4.xml。
4. node --test scripts/tests/publish_release_info_contract.test.mjs scripts/tests/publish_image_tar_transfer_contract.test.mjs scripts/tests/publish_frontend_deploy_sql_gate_contract.test.mjs。
5. powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/tests/verify-release-digest-vector.ps1；git diff --check。

独立解析新 XML 的 suite 属性和每条 testcase：

| 套件 | 实际 testcase | failures/errors/skipped | 本轮 timestamp | XML time |
| --- | ---: | --- | --- | ---: |
| C5 | 48 | 0/0/0 | 2026-09-26T11:18:01.453481+08:00 | 282.489s |
| C2 | 165 | 0/0/0 | 2026-09-26T11:18:01.686630+08:00 | 468.910s |
| C4 | 230 | 0/0/0 | 2026-09-26T11:19:15.238574+08:00 | 803.013s |

操作员命令摘要耗时分别 282.66/468.98/803.64s，三个进程均 exit 0；Node 7/7、PowerShell 摘要向量和 diff-check 均 exit 0。独立 XML 中 C2/C4 五个指定测试文件全部实际运行，不含 skip 或失败。所有报告为本轮新 t5-independent-final-* 文件。

### 行为与 AC 核验

- TC-08 / AC-08 的 T5 部分 PASS：四种 intruoyi/full × OnlyOffice 组合均核加载身份；五种所选镜像逐一缺失或同标签异内容均拒绝。实际容器对 backend/frontend/website/onlyoffice 的陈旧内容及缺失均拒绝；未选 Website/OnlyOffice 不产生同版声明。运行身份只接受实际 configDigest，不把构建 descriptor 当备选 ID。
- 实际原始官方归档 identity 链 PASS：固定 postload-save.tar 字节 hash 先后不变；归档 build descriptor=sha256:aa88ecce96d1abff3797127aa1b22171134b4f217b99e81f0c01b2c1b1bd2992，经真实治理产生 configDigest=sha256:ab853f51b03036cd52e74771c2dd07ee1471c408645048e928af67db6beae6d7，rootfsDiffIds 与 classic 实际镜像一致，再由生产加载核验消费；没有用修改归档或模糊接受两个 ID 放行。
- 内容来源绑定 PASS：verifiedImageContent 必须完整、无重复且匹配同一构建身份；空证据、重复组件、外来 buildImageId 拒绝；目标 daemon OS/architecture 不符拒绝。target smoke 的 MES_SMOKE_NODE_IMAGE 来自已校验 configDigest。
- TC-08 / AC-09 的 T5 部分 PASS：真实隔离文件系统读取 Website 完整文件集合、逐文件长度/hash 和目标渲染 nginx；少文件、变内容、多旧文件、文件/目录链接和配置错误均拒绝。find/stat/sha256sum/base64 每项外部失败均返回 unknown 并拒绝，未引入未声明的远端 Python。full 目标平台前提由 Read-ReleaseTargetSnapshot 首写前路径消费。
- 健康与结构化结果 PASS：后端健康生产函数对 HTTP 请求成功但 DOWN、缺 status、非法 JSON 均拒绝，UP 正例通过；loadedImages/images/website/checks 分别保留期望、实际或未知/失败结果供 T6。此处健康响应在运输边界注入，只证明解析/状态合同，未宣称实际业务 backend 已达到 UP。
- 主链检查位置：源码与回归共同确认所有应用和 Website 启动之后才核所有选中容器与 Website 内容。实际 Docker/文件行为由 C5 另行证明，不把该顺序的源码断言误报为三服主链部署。
- AC-12 相关回归 PASS：完整 C2、受影响 C4 三逻辑环境 checks/只读门禁/固定工具链/启动策略和 Node/PS合同本轮通过。T5 内容函数本身不分环境；本轮没有访问 test/prod/backup 真实服务器。

### 资源和结论

操作员在 mysql_runtime 归属校验后末尾 SHOW DATABASES 仅 information_schema/mysql/performance_schema/sys；classic 内层 docker ps -a 为空，images 仅保留原 mcr.microsoft.com/playwright:i-was-a-digest（ab853...），测试容器/临时 tag 已由其 fixture 清理。测试者未自行操作容器或服务器，未修改产品、测试、计划或状态。

**T5 正式独立 PASS，可解锁 T6。** 此结论覆盖本地受控内容身份与验证合同，不代表实际 backend 健康、三台服务器已升级或整体可发布。T6 持久阶段/失败事实/恢复门禁、T7 最终集成与收尾仍必须完成。

## T6 续接独立预审 — 2026-09-26（未冻结，非最终验收）

范围：独立读取中央 T6 计划、TC-09～TC-11、F00～F11、状态和执行证据，以及维护 worktree 当前主链、持久模块、实际恢复入口和测试。执行者仍在修改；本轮未运行测试、未操作 Docker/服务器、未修改产品或计划/state。以下行号仅对应本次读到的中间版本，不将尚未实施的矩阵判作最终 FAIL。

1. **F04 测试注入误判，已定位。** `test_release_durable_deployment_evidence.py:385` 以命令包含 `infra_release_migration` 和 `'FAILED'` 拦截，但生产 `New-ReleaseMigrationStateUpsertSql` 的固定 CASE IN 列表始终包含 `'FAILED'`（当时发布脚本 :6531），RUNNING/APPLIED 更新也会提前失败。`t6-ledger-red.xml` 的原错确为 `FAILED ledger write rejected`，尚不能证明第二条 SQL 失败后原错误被覆盖。必须只在真实 FAILED 台账更新边界注入，并核首条 DDL/业务行已提交、第二 SQL 原错及失败台账错误分别保留。续跑 `t6-resume-ledger.xml`、`t6-resume-ledger-2.xml` 分别为旧容器、旧镜像引发 fixture setup ERROR（各 1 error、0 failure），不是业务 RED。
2. **operation 的锁内 CAS 缺口，确定性静态风险，待动态复现。** `Save-ReleaseDeploymentState` 在 flock 外读取旧 operation 并验证单调性，锁内仅比较 gate 摘要。A 读取旧 false 后，B 同 lease 保存 true，并在替换 operation 后、替换 gate 前中断；A 随后取得锁仍可匹配旧 gate 摘要，可能覆盖已持久 true。锁内须再次核对旧 operation 摘要，且需通过故障窗口回归证明不可覆盖；现有 caller-context 单调性测试不覆盖该时序。
3. **同包 COMMITTED 只读完成路径尚未落地。** 当时 `Assert-ReleaseDeploymentCompletionEvidence` 只核同 lease 的 DB 终态和历史；主链在 gate 放行后仍 Enter/Initialize/执行。尚未见同 releaseTag/双摘要的只读实际镜像、配置、迁移、健康复核及不重放短路。F00 目前仅调用门禁复读，不能证明重新调用完整入口不会重放。不同新包还须有删除旧本地/NAS 程序包后仍可凭旧持久完成事实进入的正例，避免增加旧包依赖。
4. **F10 真实进程中断矩阵待补。** 当前测试文件未见实际终止独立任务子进程的载体；普通 throw 和新 PowerShell 读取不能替代 STARTED 后、第一真实 DDL 后、receipt/history 后、DB APPLIED 后但 COMMITTED 前的四个中断点。最后提交后须另有只读成功正例；删除任务临时 control 后两个入口仍应消费远端事实。
5. **F01/F02/F11 恢复入口已有实现但完整证据待验。** 恢复脚本实际导入并读取持久模块，锁内重核 gate/operation 摘要，DB FAILED 回读 fence 后才保存 ZERO_WRITE_FAILED；STARTED/FINALIZING/RECOVERY_REQUIRED 的 3×3 锁状态用例及部分损坏/身份/heartbeat 用例已存在，尚无本轮独立运行证据。同标签恢复后新 lease 保留旧文件字节、旧 lease 不能恢复新 attempt、锁内 gate 漂移拒绝仍需有限正负例。READY、PREPARED 的恢复边界不能仅凭 stale heartbeat 放行。
6. **阶段观察与最终化覆盖尚不能从片段报告外推。** 当前 before/失败观察确实读取镜像、DB ledger、白名单配置并对失败记 unknown；原错误与台账/观察错误分字段保存，类型检查已严格要求整数 revision/Boolean 标志。F08 七变体、F05 env/健康等测试已写出，但未取得独立 GREEN；实际内容身份失败、观察失败、锁释放失败和最终化错误应逐项核对持久阶段、原错和未知事实，不能把健康运输桩当作真实业务后端健康证明。

结论：T6 保持 in_progress；本节仅为可执行的预审反馈。正式独立 C6/受影响回归需等执行者冻结后运行新命令，核新 JUnit、测试前后源码摘要及任务资源残留，再逐 AC 给出结论。

## T7 独立验收准备检查 — 2026-09-26（未启动、未运行测试）

已只读核对 TC-04、TC-12、C7 和当前生产/测试；两个新增集成模块及 runner 尚不存在，这属于计划内未开始交付，不是最终 FAIL。

- `test_release_full_package_mysql_integration.py`：必须用同一不可变 M1→M4 包，在三个真实任务 schema 建立 M1～M3/M1/M1～M2 的结构与合法台账，绑定 test/prod/backup 逻辑环境；以生产 `Get-ReleaseTargetDatabaseSnapshot` 采集真实 schema/完整 ledger，再对实际 `build_target_bound_plan` API 和 CLI 各跑两次，获得 M4/M2～M4/M3～M4；锁内重新采集/验证后，由生产 `Invoke-RequiredDatabaseSqlScripts` / `Invoke-RequiredDatabaseSqlScriptWithState` 执行原样 SQL/台账载体。须核实际执行序列、未重写 SKIP 历史、终态四迁移结构/摘要一致、包双摘要和全部文件字节不变。历史订单/附件引用/任务 tenant 的全部原有主键字段逐行及摘要前后相同，挂载由任务容器真实 inspect 前后对账。不得调用 T3 的 `snapshot()` 手造三个 ledger 冒充真实旧库，也不得复制排序/跳过/台账算法到测试 helper。
- `test_release_full_package_workflow_integration.py`：贯通真实生产入口/门禁与任务资源，证明 app-release 路径没有源库 dump、数据库/MinIO 导入、protected showroom 或审核矩阵写入；以实际参数绑定及生产验证函数覆盖 intruoyi/full、OnlyOffice、三环境、SourceSelectionId/来源提交、tested v2、正式 dry-run/授权的接受和拒绝。绑定 T6 的持久回执、失败/重启消费和 T5 实际内容身份；已有 F00～F11/C5 用例直接由 runner 执行，不复制一套算法或重复相同用例。运输适配、健康响应故障注入、sleep 容器只证明对应边界/顺序，不能写为真实产品 E2E、三服 rollout 或真实 backend UP。两份运维文档需列出授权后平台/READY gate 初始化、classic overlay2 支持边界、目录/恢复入口、旧包拒绝及本次未操作三服。
- 可复用：`release_test_runtime.mysql_runtime/run_mysql/application_backend_root`（归属和秘密保护）；readonly-deploy-gate 的 `_functions`、`_real_database_snapshot`、实际 SQL carrier/docker transport 模式和 real planner 重采集用例；生产 `Write-ReleasePreflightPlan`/`Assert-ReleaseTargetDataPreconditions`、锁 acquire/fence/release；完整包 fixture/正式治理 `write_complete_package/rebind_package`；governance 的 tested v2 正反例及真实 ParamBlock 载体。`_mysql_snapshot_for_plan` 的 DB 部分是真实采集，但其中 host/platform/部分 mount 字段是测试边界，不能原样当作真实平台证明；最终应单独记录来源和真实挂载事实。Python `execute_preflight_apply_migrations` 的 callback 用例只能覆盖该 API，不能替代正式 PowerShell 部署链。

最终 runner 去重清单：以下 **24 个 pytest 模块**各执行一次（共同前缀 `scripts/tests/`）；C7 前面的两模块定向命令是开发入口，独立完整 runner 验收时不要先跑它们再重复计数。

```text
test_release_migration_supersession_contract.py
test_release_preflight_r20_regressions.py
test_release_migration_preflight_matrix.py
test_release_preflight_plan_order.py
test_release_sql_preflight_gate.py
test_release_build_preflight_cache.py
test_release_schema_rehearsal.py
test_release_package_governance.py
test_release_operation_lock_mysql_behavior.py
test_release_full_package_contract.py
test_app_release_package_governance.py
test_runtime_control_frontend_deploy_contract.py
test_release_digest_vectors.py
test_scheduler_smoke_linux_payload_integration.py
test_release_target_bound_plan.py
test_release_target_data_preflight.py
test_release_readonly_deploy_gate.py
test_release_workflow_preflight.py
test_release_runtime_identity.py
test_release_durable_deployment_evidence.py
test_publish_release_lock_cleanup.py
test_release_deployment_transaction.py
test_release_full_package_mysql_integration.py
test_release_full_package_workflow_integration.py
```

其余必跑项各一次：Node 的 `publish_frontend_deploy_sql_gate_contract.test.mjs`、`publish_release_info_contract.test.mjs`、`publish_image_tar_transfer_contract.test.mjs`；PowerShell `verify-release-digest-vector.ps1`；生产 publish/recover 脚本与证据模块 AST 检查；`git diff --check`。C6-J 必须以独立应用 worktree 标准 Maven 运行 `RuntimeControlServiceImplTest,ReleaseWorkflowOrchestratorTest,ReleaseWorkflowRecoveryTest` 并保存新 Surefire 证据，不混入 pytest 计数。runner 应显式载入任务 MySQL/应用 worktree/真实 smoke 载荷配置，缺引擎或载荷即失败，不能 skip；保留官方镜像身份、JUnit、源文件哈希和前后资源清单。T6 仍在执行，本节不解锁 T7、不更改任何状态。

## T6 完成事实有限复审 — 2026-09-26（未冻结、非最终验收）

本轮仅只读核最新同包完成路径、观察/健康和历史回执绑定，未跑测试。主链已在生成新计划和取租约前调用 `Test-ReleaseDeploymentAlreadyCommitted`；相同 tag/双摘要通过当前实际配置、数据库 schema/完整 ledger、组件镜像/运行态、健康及 Website 内容后直接 return，避免旧 APPLY 计划被新 SKIP 计划替代或重放。观察结束后已重新读取 gate 摘要，并再次核同 lease 的数据库 APPLIED；静态路径满足最终复核要求，正式验收仍需覆盖健康/Website 观察期间 gate 或 lease 漂移。

确定缺口已立即交主管和执行者：当时 `Assert-ReleaseCommittedRuntime` 用当前新包的 `ReleaseVerifiedImageContent/publishWebsite/IncludeOnlyOffice` 调用通用观察器。旧包不含 Website/OnlyOffice、合法新包首次纳入组件时，会因新组件尚不存在或新配置尚缺失而阻断旧完成复核。旧完成事实应按已绑定旧 receipt 的选中组件观察；新增有限正例须证明新包可以到达新计划，同时旧已选组件漂移仍拒绝。此项等待执行者 RED/GREEN 和独立验收，不提前关闭。

NAS 合同经主管澄清：允许读取旧 tag 目录下既有正式 history/latest；禁止新增对旧 payload/archive/manifest 的读取/下载依赖。目录名称包含旧 tag 不构成缺陷，不要求删审计历史后成功，也不扩展历史迁移。当前完成历史核对只读历史文件摘要；正例应删除旧程序载荷/manifest 并保留正式 history，验证不同新包继续。配置观察限定白名单，endpoint 拒绝 userinfo/query/fragment，数据库持久证据只含身份/schema 摘要及不含 error_message 的 ledger；不保存整份 env、凭据或业务数据。原异常/观察异常仍经既有脱敏器处理，当前 credential sentinel 和 endpoint 负例待正式运行确认，不能仅凭静态检查宣称所有敏感数据验证通过。

## T6 暂冻结最后只读预审 — PASS（独立动态门禁待验）

2026-09-26 本轮只读产品和实际 JUnit，不运行测试、不操作测试引擎、不修改产品/计划/state。已亲自核对四文件 SHA256 与主管暂冻结一致：publish=`0619a27cc293b0414b0a74a90dcc8cec4c908b93e26fabb6a41d847f0a9a53df`；recover=`50ad271c744175627e91bdac5e7063eff8e3be9440bd46c415a976a06960d0b6`；evidence 模块=`a1f5a8cf3c1fa778ebaba2af12d4d6e6eea40dd80975fed0c261703a32f1a6bf`；durable 测试=`b017cd75cbb113befd38b8e04c0346ce8259a518b5af523ee055458b12545a7d`。以下 PASS 仅指本轮有限静态预审，不是 T6 独立动态放行。

| 原预审项 | 本轮核对结果 |
| --- | --- |
| F04 误注入/无效 RED | 注入已只匹配 INSERT 实际 FAILED 值槽位；测试先核第二 SQL 的真实 missing-table 原错、首条业务行保留，再核 FAILED-ledger 次错或未知数据库观察；AST 初始化与正式入口一致。原 setup ERROR/宽匹配 RED 不计有效产品证据。 |
| operation CAS/锁缺失/三文件绑定 | Update、Create-after-zero、Create-after-committed、Receipt 共用锁内旧 operation/receipt 摘要守卫；锁改只读打开，缺失不再创建；operation.receiptDigest 与 gate/实际 receipt 摘要一致。实际 I/O 交错负例保留，不靠改内存对象模拟竞态。 |
| 同包完成及不同新包 | 主链规划前按 tag/双摘要识别；同包只读复核真实配置/schema/完整 ledger/组件/健康/Website 后返回，测试禁止 planner、新 lease 和 gate 变化；同 tag 异摘要拒绝。旧组件已由 receipt 显式传给观察器，新增 Website/OnlyOffice 新包可以进入新计划。健康期间真实 gate 文件或 DB lease 被替换时拒绝；末尾重读 gate 并核同 lease APPLIED。历史核对只读取已有 history/latest，不读取旧 payload/archive/manifest。 |
| F10 真实中断 | 用 `Popen(powershell.exe -File)` 启动独立任务执行器，生产阶段完成后写 marker，父进程确认 marker 再 kill 并 wait。STARTED 后无业务表、第一 SQL 后仅首行和一条 APPLIED、receipt/DB APPLIED/COMMITTED 后两行均通过真实 SQL 核查；删除本轮 control、过期 heartbeat 后新进程实际部署入口读取，前四点阻断且实际恢复脚本也拒绝，COMMITTED 点只读成功。 |
| 恢复/同标签尝试 | 实际 recovery 脚本入口保留确认文本、本机身份/终止 PID、过期 heartbeat、原 lease 和迁移证据检查；锁内文件摘要复核在 SQL UPDATE 前，FAILED 同 lease 回读后才 ZERO_WRITE_FAILED。3×3 未决状态/DB 终态矩阵、损坏/身份/新 heartbeat/失 lease、合法连字符库名及同标签新 lease 历史保留负例均有载体。 |
| 观察/最终化/历史 | before/after 真实 DB/镜像/env 观察保留 unknown；F05 实际部分容器切换与同 tag 错镜像负例，F08 七个明确阶段、F09 UPDATE 失败/确认丢失、F07 内层/运输非零载体均在。历史返回值在阶段替换 operation 后再赋值；history environment/tag/attempt 与 operation 对账；读取失败+断开失败保留主错和脱敏次错。 |

F00 正例已参数化 test/prod/backup 本地逻辑环境；下一合法包真实执行且旧 attempt 文件字节保留。F01 三类文件损坏/重复键/schema/远端非零，F02 绑定变化及取锁后真实 gate 变化，F03 首次 STARTED 临时写/原子替换失败均在当前套件。测试中 planner/upload/HTTP 边界仍明确注入；真实 MySQL/文件/内层 Docker 身份证据仅覆盖相应合同，不称真实后端健康或三服产品 E2E。

亲自读取执行侧新报告：`t6-f10-restored.xml` 为 6 tests / 0 failures / 0 errors / 0 skipped，suite time 467.487 秒；`t6-history-binding-green.xml` 为 5 / 0 / 0 / 0，5.297 秒。它们可确认有效报告及实际载体，不能代替测试者自行运行。结论：原六项预审缺口已有实现/对应有限载体，未发现新增确定性产品缺陷；等待执行侧完整 C6/C4/C5/C2 串行完成及正式冻结，再由本独立测试角色亲自运行必要验收、核新 JUnit/源码哈希/资源残留后决定 T6 放行。

### T6-LOG-01 补充日志检查 — 确定缺陷，待修复/独立复验

主管要求追加最小租约日志检查后发现原有限预审范围外的实际泄露路径；因此上一节静态 PASS 不能作为当前日志合同放行。未中断正在运行的 C6，未运行重套件、未访问引擎/网络、未打印任何真实租约或 EncodedCommand。

已用 AST 加载当前真实 `Invoke-ReleaseOperationLockRelease`、`Invoke-SshCommand`、`Protect-ReleaseSensitiveText`、`Info` 及依赖，只在 `Invoke-ProcessCapture` 截断运输边界，所有输出留内存并仅输出布尔结论。释放成功路径经 publish 脚本 :1547 的命令展示 → :2198 脱敏 → :145 Info 实际 Write-Host，结果 `releaseLogContainsSyntheticLease=true`；运输收到完整原租约 `releaseTransportRetainsLease=true`。SQL 的 `lease_token='…'` 不匹配当前脱敏 pattern，因而成功释放日志暴露租约明文。

正常 Acquire 使用 `Invoke-SshCapture -IgnoreExitCode`，没有 Run 日志，不能称常态 Acquire 必然泄露；但模拟生产采集返回 LOCK_ACQUIRED 所有权文本且退出码 17 时，真实 Acquire 抛出的 capture.Output 再经真实 Protect 后，`acquireFailureAfterProtectContainsGeneratedProbeLease=true`。该错误可进入失败日志/持久原错，须同时修复。探针 `interceptedTransportCalls=2`、`realNetworkCalls=0`，未保存或输出敏感原文。

最小行为 RED 建议已交执行者：以真实 Release→InvokeSsh→Protect→Info 捕获主机/输出/错误流，只 mock 运输，断言合成租约不在任何显示或失败证据中，同时运输 SQL 仍保留原 lease 以免破坏 fencing；另覆盖 Acquire 所有权成功文本后运输失败的异常脱敏。保持现有外部参数、DB/attempt 身份和错误传播合同，不新增日志框架。修复后须独立复验该窄行为，再结合当前完整套件结果判断 T6。

### T6-LOG-01 修复只读复核 — 关闭（最终独立动态门禁仍待验）

已核新冻结 publish SHA256=`f14b16df78f8e2132a1fab9f1703e90fa2d6e5f3cc61705aeb72e9c1e7460911`、durable 测试=`079f45ca8d53f4763a40cf68df8ec2807e896fcac4e8856620f4a911422915e9`；recover/module 哈希与上一轮一致。复用原 Protect，对当前租约及显式敏感值作原文/SQL 引号转义值精确替换，并遮蔽 LOCK_ACQUIRED/LOCK_UPGRADED 协议令牌。Release 的 normalizedCommand 仍原样传输，只有 displayCommand/错误文本脱敏；Acquire/Upgrade/Ownership/Heartbeat 保留原失败条件、throw、held 状态处理和 SQL，只在构造异常时保护文本，未改变锁算法或吞掉异常。

亲自读取两条测试：Release 显式重新加载真实 Info（非空桩），经真实 Release/InvokeSsh/Protect，以 `*>&1` 捕获全部流，断言有真实 `[INFO]`、无合成租约、运输 SQL 有原租约且正常释放；Acquire 在运输边界返回所有权确认文本和 exit17，检查原始异常及主机/输出/错误流均无租约，运输保持原值且 held=false。亲自解析 JUnit：`t6-lease-logs-red.xml` 2 tests / 2 failures / 0 errors / 0 skipped（2.139 秒）；`t6-lease-logs-green.xml` 2 / 0 / 0 / 0（3.866 秒）。测试确实针对原泄露链路，未以伪日志替代实际输出。

本轮未运行任何测试或并发重套件，仅独立代码/报告复核；T6-LOG-01 的实现与执行侧行为证据已满足该项关闭条件，最终独立 C6 仍须包含这两条用例后才能整体放行。

## T6 正式独立动态验收 — 执行中

首轮预检已自行核对执行侧 evidence JSON 所列 11 个源文件 SHA、4 份 JUnit SHA/实际 testcase 数/结果（C6=194、C4=230、C5=48、C2=165，全部 0 failure/error/skip）。两任务容器精确 ID/label/独占卷/network none/无端口匹配；classic 为 overlay2 26.1.4，内层 0 容器、仅预置镜像；MySQL 仅 4 系统库。

BLOCKER: independent-preflight -> 两容器均残留 `/var/lib/docker/task-inputs/release-fullpkg-8bea35-t6-161d0bfb462b4f97b0f3fd6f25a6828e`。尚未启动独立 C6；测试者未读内部内容、未删除执行者现场，已请主管确认归属并处理。此为运行前资源差异，不是产品测试 FAIL；此前报告不替代本轮动态结果。

预检阻塞已解除：主管确认该根属于旧中断 T6 fixture 后精确清理，独立测试者重新核两容器 fixture 根均为空、11 源/4报告摘要未变、资源身份/4系统库/零内层容器/唯一base镜像一致，platform.node 子进程正常返回。GREEN: independent-preflight -> PASS。前置快照保存于任务缓存 `t6-independent-final-preflight.json`；HEAD=`3f3aabdc82ab5e85e2f872173a665a361f022725`。随后执行独立完整 C6，结果待退出和新 JUnit 完整落盘。

### T6 正式独立动态验收结果 — PASS

独立测试者于 2026-09-26 17:02:18 +08:00 从冻结维护 worktree 亲自串行执行以下完整 C6；仅本套重测试，无并发 C2/C4/C5。设置 `PYTHONUTF8=1`、任务 MySQL 配置路径和本任务应用 worktree backend 根；未改生产/测试文件。

```powershell
python -X utf8 -m pytest -q -x --tb=short scripts/tests/test_release_durable_deployment_evidence.py scripts/tests/test_release_operation_lock_mysql_behavior.py scripts/tests/test_publish_release_lock_cleanup.py scripts/tests/test_release_workflow_preflight.py scripts/tests/test_release_deployment_transaction.py --basetemp E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t6-independent-final-c6 --junitxml E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/t6-independent-final-c6.xml
```

实际退出 0，pytest `194 passed in 3142.08s (0:52:22)`。亲自解析新 JUnit：194 个唯一 testcase，0 failures / 0 errors / 0 skipped，suite time 3141.677 秒；模块计数 durable=136、operation-lock=29、lock-cleanup=14、workflow-preflight=14、旧 transaction=1。最后一项仅既有模拟回归，未当作真实恢复证据。JUnit SHA256=`bbe782610add9ba59ac5ff98aa0836b7496c15b8f033eb341fdc93b9949171d0`，不存在未退出或零字节报告冒充 PASS。

随后亲自运行三个 Node 合同文件，共 7/7、0失败/跳过；`verify-release-digest-vector.ps1` PASS；生产 publish/recover/evidence-module 三文件 AST 无错误；`git diff --check` 退出0（仅既有 LF/CRLF 提示，无diff错误）。11个冻结源文件前后 SHA 完全一致，HEAD未变；当前工作树 diff SHA256=`04c156c18f8c31d1b6d25b309627a84d49f7d98fa4c6309a680c6f902f9cf467`。明细保存在任务缓存 `t6-independent-final-evidence.json`。C4=230/C5=48/C2=165 的既有新报告已核 report SHA、实际计数及本次未漂移源码，此轮未重复这些依赖套件；最终 T7/C7 仍需全量运行。

| 验收范围 | 独立结论与实际证据 |
| --- | --- |
| AC-09（T6） | PASS。F00 三逻辑环境完成真实 SQL、env/容器身份、最终化、历史/回执和 DB APPLIED→COMMITTED；F05/F08/F09 的组件/最终化/确认失败不产生整体完成。健康响应属于已声明运输边界，本结论不证明真实业务 backend UP。 |
| AC-10（T6） | PASS。F03 证据落盘失败无运行写入；F04 第一真实 DDL/业务行保留、第二 SQL 原错与 FAILED-ledger/观察次错分别保留；F05 实际部分容器切换与错镜像保留混合状态；F06/F07 错误与非零不被清理/成功文本覆盖；unknown、secret sentinel 和租约日志两项均通过。 |
| AC-11（T6） | PASS。F01/F02/F11 实际持久/恢复入口拒绝损坏、漂移、未决状态与旧lease；CAS与true单调负例通过；F10五个真实子进程kill边界后新进程部署/恢复均按未完成或COMMITTED只读事实处理；删除临时control、过期heartbeat不能放行未决写入。 |
| AC-12（T6及受影响合同） | PASS。新包按旧receipt组件复核、同包不重放/不换lease、最后gate+DB复查、原数据库operationId与attempt派生/显式恢复参数保留；Node/PS及既有C2/C4/C5证据完整。整体AC-12的T7三起点集成、交付文档、最终融合/发布就绪不在本次提前放行。 |

运行后实际资源回读：MySQL仍仅4系统库，classic内层容器0、仅原预置官方base镜像，两容器 `/var/lib/docker/task-inputs` 下T6根均为空；CIM仅输出计数确认本独立测试相关Python/kill-executor进程0。任务引擎、卷和flock工具按主管要求保留供后续阶段。

额外资源发现：最终扩大只读扫描 `/tmp` 时见旧 recovery 根 `/tmp/release-fullpkg-8bea35-t6-recover-fe106c8ccae44b5f8dab70733333ee7c`，其8项最新mtime=2026-09-26 04:38:05 UTC（本轮开始前约4.5小时），gate=PREPARED/database=`release-t6-recover-5de9c940`，该schema已不存在。该根不属于本轮新增残留，已交主管精确清理；测试者未删除。预检只扫描了task-inputs而未包含该旧/tmp根，此范围差异明确记录，不宣称此前全部临时目录为零。

**T6 在已批准本机隔离范围内正式独立 PASS，可由主管解锁 T7。** HTTP/SSH/NAS为明示运输/故障边界；真实证据是任务独占MySQL、内层classic Docker、真实文件/SQL/进程中断与生产函数。不宣称已部署三服、真实产品E2E或最终发布就绪。T6-LOG-01两项已在本轮完整194项内亲自复验通过。没有修改源/测试/计划/state、提交、合并或远程操作。

## T7 有限独立只读预审 — 待补 TC-12 动态调用证据

本轮读取已批准 T7 配置化补充、8个当前交付路径与重建记录；未运行任何测试、未读取原始私密 runtime JSON、未修改产品/测试/计划/state，未并发干扰执行者 C7。重建记录明确旧 classic `1077b4…` 和旧卷已删除，新 classic=`1243a95b18bfe7819c396d22f5502676680bd84cb1469360d38c16fe81835ddf`，同官方 dind/归档重新装载并验证；这只是主管生命周期证据，独立 C7 仍须实际复跑。

有限检查无确定产品缺陷的部分：MySQL 集成建立三个真实任务 schema（M1～M3/M1/M1～M2），用生产数据库采集函数读实际结构/完整台账，API与CLI各跑两次；实际取锁后生产 `Write-ReleasePreflightPlan -Verify` 重采并核对，原样生产 SQL carrier 执行不同 APPLY 清单。历史 tenant/order/attachment 全字段与 SKIP 台账全行逐字对照，四迁移最终数据、真实 Docker mount 和同包全部文件字节前后核验。平台/应用载荷边界已明示，未把 T3 内存 snapshot 冒充三起点。唯一 helper 保留严格任务、精确 ID/名称/挂载/独占消费者、network none/无端口/socket、26.1.4 overlay2、官方内容/归档和工具哈希检查；消费文件没有回落旧实例路径。runner完整24模块去重，缺模块或 JUnit 含 failure/error/skipped 拒绝，维护源码集合/哈希/HEAD/diff和外部应用 clean HEAD 前后取证。两文档写明后续授权 bootstrap、旧合同/未知基线拒绝、1 GiB仅floor、classic边界、人工恢复和未执行真实现场发布。

**T7-EVIDENCE-01（验收覆盖差距，非已证实产品bug）**：`test_release_full_package_workflow_integration.py:190` 最后一条仅遍历 `Invoke-ReleaseDeploymentExecution` 的 CommandAst 字符串，未实际运行并观察禁用动作。既有 C6 虽真实执行主链，但运输载体把上传/控制文件/运行包等 helper 置空、未对真实调用记录断言无 dump/import/protected-write；因此两者组合不足以将 TC-12 的“实际调用路径无源库dump/MinIO导入/受保护展厅和审核矩阵写入”记录为行为 PASS。

最小补证建议已交主管：只在现有 T7 workflow 模块新增/替换一条真实主链调用证据测试，复用 C6 的 flow/flow_script，在运输和已声明辅助边界记录并拒绝 source dump、DB/MinIO导入、protected写入和平台重建，核只有通过计划的 SQL 进入真实任务库；使用正式 app-release 范围设置函数/语句，不能仅靠 fixture 手设 SkipMinioSync=true 宣称产品合同通过。不复制 F00～F11、不新增产品框架、不要求真实产品 E2E；仍被 stub 的 helper 只能声明主链调用边界，不能宣称其内部实现已动态验证。当前冻结 workflow SHA=`2e6c1d7e4a0f63bf70af11250f9b4623444f22abfb0d35204a6a4c118ddb2bc4`，待主管协调修改/重冻后复核，正式 T7 放行仍待独立 C7/C6-J。

### T7-EVIDENCE-01 补证只读复核 — 关闭，可重跑完整 C7

本轮未运行测试。已核 workflow SHA256=`66c3bcd104d1eedf68b8f3b5bbc7b0df563a66940a7354a61b886db5f0e6a101`，新增 `test_actual_app_release_dispatch_excludes_data_replacement_and_platform_rebuild` 补足原 AST-only 项；原 AST 测试仍可作辅助，不能单独代替此动态证据。

测试复用既有真实 flow，先把 flags 显式设 false，再调用真实 `Resolve-EffectiveBuildReleasePublishScope`、实际 deploy app-release 范围语句和两个实际顶层 export guard，断言 build/deploy 均得到 true,true。之后实际执行 `Invoke-ReleaseDeploymentExecution`，运输/辅助边界记录分类；禁止分类区分 dump、实际 DB/对象导入、protected写入及平台重建，没有再把 cleanup 对 db.sql 的普通文件引用误判为导入。实际计划 SQL 仅001/002，并从真实任务库确认两条业务行；原 SQL、命令、lease 均未序列化到安全 trace。

亲自读取 `t7-dispatch-verified.xml`：1 testcase / 0 failures / 0 errors / 0 skipped，suite time 96.634秒；这只是定向结果，44 deselected 不计全量通过。安全 `t7-dispatch-boundary-evidence.json` 实际记录 buildFlags/deployFlags=[true,true]、sql=[001.sql,002.sql]、denied=[]、categories=[application-compose]，并列出真实主链触达的辅助边界名。没有把上传/平台前置/HTTP/NAS的既有空helper内部冒称真实执行；仅 SQL/租约/持久文件/env/内层Docker为实际行为。该范围与原 TC-12 最小动态证据一致，T7-EVIDENCE-01关闭；允许执行者在当前冻结上从头运行完整 C7，正式独立 T7 门禁尚未放行。

## T7 最终独立动态验收 — 执行中

独立预检 PASS：已自行核 executor-handoff SHA=`c18e409e29c3bed8f86bbe7d18579126faf1717ffe905090d7a104fdcd676ae0`、114文件路径集/全部SHA、任务diff=`cf9105505e7897fc373c385cdea2556c65e5c8495a04d35e5015ad63f32fa49a`、执行侧845唯一有效testcase与JUnit摘要。实际调用共享helper严格检查新classic/原MySQL、官方归档/工具；classic内层容器0、fixture根0、MySQL仅4系统schema且仅批准flock目录。外部应用HEAD=`af5acd8266e4ca1eb71e1d0581ece77fa4743d48`、clean，匹配测试进程0、platform.node正常。前置证据=`t7-independent-preflight.json`；不使用执行侧结果替代本轮结果。随后按计划唯一串行完整runner，再标准C6-J，不重复先跑定向模块。

### T7 独立轮次1 — 超时阻塞，未放行

实际原 runner 命令已执行，唯一证据目录为 `E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/c7-20260926T131100-add275c5`。2026-09-26 21:11:04 +08:00 启动 pytest，80.35秒后按 `-x` 首错停止；runner及外层命令退出1。有效新 JUnit=227 tests、226 passed / 1 failure / 0 error / 0 skipped，SHA256=`f161d2a25d259cfa61e895758d9b356a26882bfe50b53b27a0e631b26373aee6`。未自动重跑、未继续Node/PS/AST后段或C6-J，不把已通过的前226项当全量结果。

失败入口为 `test_release_package_governance.py::test_mark_tested_rejects_missing_or_malformed_operation_without_creating_attestation`，`_run_powershell(timeout=15)` 等待真实模块导入/`Write-ReleaseTestedAttestation` 子进程触发 `subprocess.TimeoutExpired`。现场 operation.json 存在且为1字节，表明已进入第二个 malformed 子例（第一个 missing 子例已返回）；未生成 tested.json 或 tested.json.*.tmp。生产路径先核包完整性，再调用 `Assert-PublishTestOperationEvidence`；现有证据不能确定卡在启动/模块导入/验包/JSON错误返回的哪一步，也不能据此认定业务缺陷、有效业务RED或环境原因已确认。

失败后仅只读核查：114源SHA和任务diff不变，应用HEAD及clean不变；共享helper重新核资源与前置快照一致（新classic/原MySQL、4系统库、零内层容器/fixture、唯一base与批准flock工具）。CIM按本轮目录/runner归属只输出计数，残留测试进程0。脱敏汇总保存 `independent-failure-readback.json`，有效失败JUnit及现场未删除；没有输出原始配置、Env、租约或EncodedCommand。测试资源所有权已释放给执行者做有界诊断；测试者不修源码、不放宽timeout、不自行重跑。T7最终独立门禁继续待验。

### T7 独立轮次2 — 原冻结原参数完整复验中

主管批准一次完整重跑前，独立读取单次原用例诊断 `t7-timeout-diagnostic-once.xml`（1/0/0/0，7.531秒）及脱敏 summary：原15秒阈值未改、三份fixture字节相同，历史卡点仍不可观察；不以单例通过替代完整C7，不归因WMI/OOM。重新实际核114源码/任务diff、应用clean HEAD、共享helper全部资源清单与原预检一致，匹配测试进程0。此轮继续使用原runner、不增加retry或skip、不改阈值，失败仍首错停止；原227项失败报告完整保留。

### T7 独立轮次2与C6-J最终验收 — PASS（2026-09-26）

本节为最终独立验收结论，仅追加本轮原始证据与判定。验收目标按 `CR-20260926-PROCESS` 收敛为可复用发布流程合同：完整包、逐目标预检、同包不同起点、数据保留、身份绑定、失败恢复和调用边界。当前主程序 main、当次候选包、三服实时计划和实际服务器部署不属于本轮门禁。

#### 独立运行证据

- C7 round2 使用冻结维护 worktree `D:/IntRuoyiWorktree/full-package-release-maintenance`，HEAD=`3f3aabdc82ab5e85e2f872173a665a361f022725`，task diff SHA=`cf9105505e7897fc373c385cdea2556c65e5c8495a04d35e5015ad63f32fa49a`，原 runner 命令和15秒阈值未改。新证据目录：`E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/c7-20260926T132901-27955b0f`。
- C7 pytest JUnit 实际 `845` 个 testcase，`0` failures / `0` errors / `0` skipped；JUnit SHA=`0424d8f54545728277c66dd6a374b8b58d32a094da825b9b6a8b0b90f626a703`，summary=`PASS`，24个模块均被 runner 校验并执行。Node 合同 `7/7`、PowerShell digest、3个生产脚本 AST、`git diff --check` 均 PASS。
- C7 维护源码受验集合为 `114` 个文件；以 runner 同一 source scope 重新计算，路径集合 `114/114` 一致、当前 SHA 与 `source-before.json` 的 `114/114` 一致、hash diff=`0`。运行前后 MySQL/classic 容器身份、任务卷、4个系统 schema、classic 内层容器数和 fixture 根均保持不变；只保留批准的 flock 工具目录。应用 worktree `D:/IntRuoyiWorktree/full-package-release-application/IntRuoyiBackend` 前后均 clean，HEAD=`af5acd8266e4ca1eb71e1d0581ece77fa4743d48`。
- TC-12 动态边界证据已从 pytest 临时目录复制至 `E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/c7-20260926T132901-27955b0f/c7-tc12-t7-dispatch-boundary-evidence.json`。实际 trace 为 `buildFlags=[true,true]`、`deployFlags=[true,true]`、SQL=`[001.sql,002.sql]`、`denied=[]`、类别仅 `application-compose`，并确认两条业务行保留；运输 HTTP/SSH/NAS 和应用载荷 helper 仍按既定 fixture/stub 边界，不冒称真实三服部署或真实 backend 健康。
- C6-J 在固定应用 worktree按原 Maven 命令新跑，证据目录：`E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/c6-j-20260926T224300-luna`。Maven exit code=`0`；三个新 Surefire 分别 `69/47/6`，合计 `122` tests，`0` failures / `0` errors / `0` skipped；新 XML、Maven exit 及应用前快照均已保存，Maven 日志未命中 password/token/secret/EncodedCommand 等敏感模式。应用 HEAD/clean 状态在 C6-J 后保持不变。

#### Acceptance coverage

| Acceptance | 独立结论 | 直接覆盖与限制 |
| --- | --- | --- |
| AC-01 | PASS | TC-02；C7完整包组件固定、backend/frontend成套、OnlyOffice选择固定和旧调用合同回归通过。 |
| AC-02 | PASS（本轮范围内） | TC-03、TC-14；真实Linux smoke载荷、锁定依赖、镜像/静态载荷完整性和缺件拒绝均包含在845项C7中，不能外推为三服已部署。 |
| AC-03 | PASS | TC-01、TC-04；同包不同目标起点生成不同APPLY清单，包双摘要保持一致，历史已完成项跳过。 |
| AC-04 | PASS | TC-01、TC-05；FAILED/RUNNING/UNKNOWN/重复或依赖非法状态阻断，未触发迁移执行。 |
| AC-05 | PASS | TC-06；包、manifest、releaseTag、目标、数据库、执行器/计划器、schema、ledger、挂载和非秘密配置漂移在锁内复核前拒绝。 |
| AC-06 | PASS | TC-01、TC-07；只读预检和目标平台前提缺失在运行写入前失败，未以工作区或registry补齐。 |
| AC-07 | PASS | TC-04、TC-12；同包三逻辑起点计划顺序与历史数据保留通过，包外目标状态和受保护资源边界保持明确。 |
| AC-08 | PASS | TC-08、TC-14；实际镜像内容身份、归档摘要、Website/Smoke静态载荷和缺件/篡改拒绝通过。 |
| AC-09 | PASS | TC-08、TC-11；身份正确、组件完整、最终化和清理失败不会输出整体成功；健康/运输仅按声明边界验证。 |
| AC-10 | PASS | TC-09、TC-11、TC-13；持久证据、部分真实DDL、原始错误、最终化失败和Java状态语义均通过C7+C6-J。 |
| AC-11 | PASS | TC-01、TC-09、TC-10、TC-11、TC-13；真实kill、旧lease、过期heartbeat、损坏/漂移gate及RECOVERY_REQUIRED阻断通过，zero-write与可能写入分层保持。 |
| AC-12 | PASS（流程合同范围） | TC-01、TC-02、TC-06、TC-10、TC-12、TC-13、TC-14；来源/应用接口绑定、同包身份、恢复合同、T7新classic ID、C6-J和TC-12实际边界均有本轮证据。未宣称当前main合入、三服发布就绪或现场部署成功。 |

#### Test-case coverage

| Test case | 结论 | 证据摘要 |
| --- | --- | --- |
| TC-01 | PASS | C7中迁移supersession、拓扑、锁SQL和历史合同回归通过。 |
| TC-02 | PASS | C7中完整组件与旧调用参数合同通过。 |
| TC-03 | PASS | C7中缺件、不可变包、包外渲染和零写入负例通过。 |
| TC-04 | PASS | C7中同包三起点API/CLI确定性计划与实际隔离MySQL保留历史通过。 |
| TC-05 | PASS | C7中历史异常、依赖非法和blocked plan均 fail closed。 |
| TC-06 | PASS | C7中锁内身份/指纹/目标漂移拒绝及无远端写入证据通过。 |
| TC-07 | PASS | C7中只读目标预检、组件组合、`--no-deps --pull never`和缺镜像拒绝通过。 |
| TC-08 | PASS | C7中实际镜像身份、归档内容和静态载荷完整性通过。 |
| TC-09 | PASS | C7中阶段持久化、真实DDL后失败、原始/观察错误分离通过。 |
| TC-10 | PASS | C7中同标签不同lease/attempt、真实中断、恢复拒绝和零写入恢复边界通过。 |
| TC-11 | PASS | C7中成功最终化与各最终化失败点的写保护通过。 |
| TC-12 | PASS（边界范围） | C7真实三逻辑起点、历史数据保留、受保护资源禁止写入和动态T7 dispatch trace通过；HTTP/SSH/NAS/载荷内部实现仍为明示fixture/stub边界。 |
| TC-13 | PASS | C7与C6-J共同覆盖下层/上层对 TEST_DEPLOYING、PROMOTING_PROD、dispatch、zeroWriteEvidence 和 `RECOVERY_REQUIRED` 的一致结论；Surefire 122/0/0/0。 |
| TC-14 | PASS（本轮范围内） | C7真实Linux smoke载荷、Playwright/xlsx锁定版本、离线加载和身份校验通过；不等同于真实产品E2E或三服运行态。 |

#### Final independent verdict

**PASS — 可复用完整程序包发布流程合同在本轮批准的本地隔离范围内完成独立验收。** C7与C6-J均为本轮新鲜结果，未使用执行侧旧报告替代；C7历史轮次1的15秒超时仍保留，根因未被证实、未被归因、未通过放宽阈值或重试掩盖，轮次2按原参数从头完整通过。

剩余限制仅为范围边界：本轮未追踪或合并主程序main，未构建当次候选包，未生成三服当前实时计划，未访问NAS/三服，未执行真实服务器部署、真实backend健康或产品前端E2E。因此本结论是“发布流程合同 PASS”，不是“当前版本已部署”或“任意旧版本均可升级”。
