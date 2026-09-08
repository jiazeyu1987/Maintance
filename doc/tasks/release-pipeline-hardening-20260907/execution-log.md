# Execution Log

- Task ID: `release-pipeline-hardening-20260907`
- Created: `2026-09-07T21:07:40`

## BDD Scenarios

BDD: 禁止绕过安装包直发 -> Given 操作者调用发布脚本 / When 缺少显式 Mode 或选择 direct / Then 在构建、NAS 和远端写入前失败。

BDD: 数据包禁止晋级生产级环境 -> Given 完整 with-data 包 / When 目标为 prod 或 backup / Then 在 SSH、环境、数据库和容器写入前失败；test 保持允许。

BDD: 篡改包不能使用 -> Given 不可变包任一文件或 manifest 声明变化 / When build 入库、deploy 或 mark-tested / Then 逐文件校验失败且后续写入不执行。

BDD: 测试证明来自真实成功操作 -> Given 不存在同 tag 的 test/publish-test/SUCCESS operation / When mark-release-tested / Then 不创建或覆盖 tested.json。

BDD: 同一已验证包晋级 -> Given code-only 包与 tested 证明绑定 package/manifest digest 和成功 operation / When promote-prod 或 promote-backup / Then 两环境执行同一门禁后进入既有流程。

## Planner Review

- Result: approved after revision 1。
- Validation: `validate_artifacts.py` -> `status: ok`。
- Scope: P1-P3；缓存、同构环境、真实 target-state preflight、单一归档和签名为明确 non-goals。

## Phase Entries

## Phase P1

- Status: completed
- Workspace: `D:\ProjectPackage\Int\IntRuoyiWorktrees\release-pipeline-hardening-20260907\m`
- External access: 禁止且未执行 NAS、SSH、Docker、数据库或服务器访问。
- Changed paths: `ops/deploy/publish-int-ruoyi.ps1`、`ops/release/lib/ReleasePackageGovernance.psm1`、`scripts/tests/test_release_package_governance.py`、`scripts/tests/publish_frontend_deploy_sql_gate_contract.test.mjs`、`doc/tasks/release-pipeline-hardening-20260907/execution-log.md`。

BDD: P1 安装包入口强制化 -> Given 操作者准备调用发布脚本 / When 未提供 `Mode` 或尝试 `direct` / Then PowerShell 参数绑定在脚本主体及任何文件、构建、NAS、远端动作前失败。

BDD: P1 生产级 scope 门禁 -> Given 已读取发布包且 `publishScope=with-data` / When 目标环境为 `prod` 或 `backup` / Then scope 门禁明确失败且后续动作探针保持为 0；目标为 `test` 时允许继续。

BDD: P1 控制台合法命令兼容 -> Given 控制台生成 build、test、mark、prod、backup 命令 / When 使用合法 code-only 流程 / Then 命令只显式传入 `build-release`、`deploy-release`、`mark-tested`，并保留既有 test/prod/backup 参数。

RED: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp output/pytest-release-governance-red` -> FAIL, `8 failed, 2 passed`；预期原因是 Mode 仍默认 `direct`、治理模块与生产级 scope 门禁尚不存在。外部动作探针未生成。

GREEN: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp output/pytest-release-governance-green` -> PASS, `10 passed in 2.39s`。

REGRESSION: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py scripts/tests/test_release_package_slimming.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_publish_release_lock_cleanup.py -q --basetemp output/pytest-release-governance-regression` -> PASS, `72 passed in 3.36s`。

REGRESSION: `python -X utf8 -m pytest scripts/tests tests -q --basetemp output/pytest-release-governance-full` -> PASS, `99 passed in 3.22s`。

REGRESSION: `mvn -f backend/pom.xml test` -> PASS, `Tests run: 26, Failures: 0, Errors: 0, Skipped: 0`；控制台 build/publish/mark 与 code-only test/prod/backup 既有命令合同通过。

RED: `node --test scripts/tests/*.test.mjs` -> FAIL, `5 passed, 1 failed`；既有 frontend-only 合同测试在 Windows CRLF 下硬编码 LF，无法定位后端门禁。该失败不涉及产品行为。

GREEN: `node --test scripts/tests/*.test.mjs` -> PASS, `6 passed, 0 failed`；测试读取 PowerShell 后统一 CRLF 为 LF。

GREEN: PowerShell AST -> PASS；`publish-int-ruoyi.ps1` 由治理 pytest 的 AST 用例验证，`ReleasePackageGovernance.psm1` 由本地 Parser 验证。

GREEN: `python -X utf8 scripts/verify_contracts.py` -> PASS, `PASS: standalone runtime-control contracts are present`。

GREEN: `git diff --check` -> PASS；仅报告 Windows 工作区预期的 LF/CRLF 提示，无 whitespace error。

### P1 Acceptance

- P1-AC1: PASS。`Mode` 已声明为 mandatory、无默认值，ValidateSet 仅包含 `build-release`、`deploy-release`、`mark-tested`；缺失 Mode 与 `-Mode direct` 均非零退出，测试 sentinel 未产生。
- P1-AC2: PASS。治理模块矩阵证明 `with-data` 对 `prod`、`backup` 抛出明确错误，对 `test` 保持允许；`code-only` 对三环境均允许。
- P1-AC3: PASS。发布脚本在解析本地包 scope 后立即执行统一门禁，静态顺序合同锁定其早于 artifact 后续处理、运行环境应用、SSH 命令检查/读取和智能发布部署预检；拒绝用例的后续动作探针为 0。
- P1-AC4: PASS。控制台源码和 Maven 回归证明只显式生成三种合法 Mode，code-only build 仍携带 `-SkipDatabaseSync -SkipMinioSync`，test/prod/backup 仍生成对应显式环境参数。

### Remaining Risks

- P2 的逐文件完整性、稳定 package digest 与四生命周期统一校验尚未实现；本阶段未提前进入 P2。
- P3 的真实 publish-test operation 绑定、tested 原子写入及 prod/backup 统一证明门禁尚未实现；现有 `RequireTested`/backup 临时逻辑由 P3 按计划处理，本阶段未提前修改。
- 本阶段仅使用本地 fixture、AST、Python/Node/Java 合同测试；按任务约束未连接或操作任何真实 NAS、服务器、Docker 或数据库。

## Phase P2

- Status: completed
- External access: 禁止且未执行 NAS、SSH、Docker、数据库或服务器访问。
- Changed paths: `ops/deploy/publish-int-ruoyi.ps1`、`ops/release/lib/ReleasePackageGovernance.psm1`、`scripts/tests/test_release_package_governance.py`、`doc/tasks/release-pipeline-hardening-20260907/execution-log.md`。

BDD: P2 精确不可变 payload -> Given 包含 `manifest.json` 的完整发布包 / When 校验 `release-manifest.json.artifacts` / Then 声明集合与除受控可变 metadata 外的普通文件集合完全相等，并逐项实算 path、bytes、SHA-256。

BDD: P2 稳定摘要 -> Given 内容和 manifest 原始字节相同但绝对根及本机路径分隔表示不同 / When 校验包 / Then `manifestDigest` 与 `packageDigest` 等于固定向量且保持一致；payload 或 manifest 改变时摘要变化或校验失败。

BDD: P2 篡改与非法声明阻断 -> Given 文件篡改、缺失、额外、bytes/hash 错误、绝对/父级路径、重复或大小写冲突 / When 校验包 / Then 返回具体相对路径和 mismatch/missing/undeclared/invalid/duplicate 原因并非零退出。

BDD: P2 生命周期强制校验 -> Given build、NAS 复制、deploy 下载和 mark-tested 四个包使用位置 / When 进入后续动作 / Then 全部先调用同一完整性校验器，失败不继续。

BDD: P2 受控可变 metadata 精确排除 -> Given 包含 tested、rollback compatibility、prod/backup latest 与 deployment history / When 校验不可变 payload / Then 仅 revision 2 白名单路径被排除，其他附加文件仍失败；排除不代表 metadata 有效。

RED: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp output/pytest-release-governance-p2-red` -> FAIL, `15 failed, 10 passed`；预期原因是逐文件校验器、固定摘要、最终 manifest 收集顺序和四生命周期调用尚未实现。

GREEN: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp output/pytest-release-governance-p2-green3` -> PASS, `25 passed in 10.72s`；完成精确 artifact、固定摘要、负例矩阵、白名单和生命周期合同。

RED: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp output/pytest-release-governance-p2-edge-red` -> FAIL, `1 failed, 30 passed`；null bytes 声明触发 PowerShell 空对象方法错误，未返回合同要求的路径化 `invalid bytes`。

GREEN: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp output/pytest-release-governance-p2-final-green` -> PASS, `31 passed in 12.95s`；null/负 bytes、大小写 hash、manifest.json 声明缺失、缺失声明文件等边界均明确失败。

GREEN: fixed digest vector -> `manifestDigest=sha256:2d03b3a34a07105aec291600962fcfbf1494534055466a0d559ca7736db75c62`，`packageDigest=sha256:bca84ee56d15a8cf4b662442ba30d7f96000835ccaa63d6c6d402251cdde3276`；两个绝对根及 `/`、`\` 根路径表示得到相同结果。

REGRESSION: `python -X utf8 -m pytest scripts/tests/test_release_package_slimming.py scripts/tests/test_deploy_precheck_report_contract.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_publish_release_lock_cleanup.py scripts/tests/test_runtime_control_frontend_deploy_contract.py -q --basetemp output/pytest-release-governance-p2-focused` -> PASS, `65 passed in 0.25s`。

REGRESSION: `python -X utf8 -m pytest scripts/tests tests -q --basetemp output/pytest-release-governance-p2-full` -> PASS, `120 passed in 14.35s`。

REGRESSION: `mvn -f backend/pom.xml "-Dtest=RuntimeControlContractTest,RuntimeControlOriginalGovernanceParityTest,RuntimeControlOriginalParityTest" test` -> PASS, `Tests run: 26, Failures: 0, Errors: 0, Skipped: 0`。

REGRESSION: `node --test scripts/tests/*.test.mjs` -> PASS, `6 passed, 0 failed`。

GREEN: `python -X utf8 scripts/verify_contracts.py` -> PASS, `PASS: standalone runtime-control contracts are present`。

GREEN: PowerShell AST -> PASS；`publish-int-ruoyi.ps1` 与 `ReleasePackageGovernance.psm1` 均无解析错误。

### P2 Acceptance

- P2-AC1: PASS。`release-manifest.json.artifacts` 由最终不可变文件集合生成并逐项实算 path、bytes、小写 SHA-256；`manifest.json` 先生成再被最终清单声明，避免自引用。
- P2-AC2: PASS。`manifestDigest` 对 release manifest 原始字节计算；`packageDigest` 使用固定 UTF-8/LF 记录、ordinal 路径排序和实际文件值，固定向量及跨根/根路径分隔表示一致性通过；manifest 变化导致双摘要变化，payload 漂移失败。
- P2-AC3: PASS。覆盖内容篡改、缺失、额外文件、bytes/hash 错误、绝对路径、父级路径、反斜杠非规范路径、重复与大小写冲突、null/负 bytes、非小写 hash、manifest.json 声明缺失；全部非零并包含具体路径与原因。
- P2-AC4: PASS。同一 `Test-ReleasePackageIntegrity` 在 build 本地完成、NAS 复制完成、deploy 下载完成、mark-tested 写证明前强制调用；deploy 的 scope 来自校验结果，静态顺序合同保证失败不进入后续动作。
- P2-AC5: PASS。仅精确排除 `tested.json`、`rollback-compatibility.json`、`prod-latest.json`、`backup-latest.json`、`prod-deployments/**`、`backup-deployments/**`；任意内容可被排除但不被视为有效，其他相似或额外路径失败。

### P2 Remaining Risks

- P3 尚未实现受控 metadata 内容有效性、真实 publish-test operation 绑定、tested 原子写入及 prod/backup 无条件晋级门禁；P2 仅保证这些白名单文件不改变不可变 payload 摘要。
- 仍为目录包而非单一归档，NAS staging/READY、外部签名与 SBOM 属于明确后续工作。
- 按任务约束未执行真实构建、NAS 复制或服务器发布；生命周期由共享校验器的本地 fixture 与静态执行顺序合同验证。

## Phase P3

- Status: completed
- External access: 禁止且未执行 NAS、SSH、Docker、数据库或服务器访问。
- Changed paths: `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlOperationAction.java`、`RuntimeControlService.java`、`backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlOriginalParityTest.java`、`ops/deploy/publish-int-ruoyi.ps1`、`ops/release/lib/ReleasePackageGovernance.psm1`、`scripts/tests/test_release_package_governance.py`、`doc/tasks/release-pipeline-hardening-20260907/execution-log.md`。`RuntimeControlOperationStore.java` 最终与任务 baseline 一致，不属于本任务交付。

BDD: P3 服务端选择真实测试操作 -> Given operation store 包含不同环境、动作、状态和 releaseTag 的记录 / When mark-tested 或晋级 / Then 仅精确 `test/publish-test/SUCCESS` 且同 tag 的记录由服务端选中并传递受控 operation ID 与 evidence path。

BDD: P3 原子测试证明 -> Given 完整 code-only 包和匹配成功 operation / When mark-tested / Then 原子生成 tested v2 并绑定 package/manifest digest、test 环境、operation ID/status/requestedAt、testedAt/testedBy/conclusion；前置失败不创建或覆盖文件。

BDD: P3 双生产级环境统一门禁 -> Given prod 或 backup 使用发布包 / When tested 任一字段伪造、过期、payload 漂移或 operation evidence 不匹配 / Then 在任何远端动作前失败；合法同包证据允许两个环境继续。

BDD: P3 删除临时绕过 -> Given 任一 prod/backup deploy / When 执行门禁 / Then 不存在 `RequireTested` 可选语义或 backup 临时禁用分支，按 Environment 无条件校验 tested 与 operation evidence。

RED: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp output/pytest-release-governance-p3-red` -> FAIL, `24 failed, 31 passed`；预期原因是 operation 二次验证、tested v2 原子写入、晋级绑定门禁尚未实现且 RequireTested/backup 绕过仍存在。

RED: `mvn -f backend/pom.xml "-Dtest=RuntimeControlOperationStoreTest" test` -> FAIL, test compilation；预期原因是 `findLatestSuccessfulTestPublish` 严格选择方法尚未实现。

GREEN: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp output/pytest-release-governance-p3-final-green` -> PASS, `55 passed in 39.41s`；operation 交叉验证、tested v2 原子写入、全部字段负例、payload 漂移、prod/backup 合法闭环及无后续动作探针通过。

GREEN: `mvn -f backend/pom.xml "-Dtest=RuntimeControlOperationStoreTest" test` -> PASS, `Tests run: 1, Failures: 0, Errors: 0, Skipped: 0`；严格 selector 仅选择同 tag 的 `test/publish-test/SUCCESS`。

REGRESSION: `mvn -f backend/pom.xml "-Dtest=RuntimeControlContractTest,RuntimeControlOperationStoreTest,RuntimeControlOriginalGovernanceParityTest,RuntimeControlOriginalParityTest" test` -> PASS, `Tests run: 27, Failures: 0, Errors: 0, Skipped: 0`；mark/prod/backup 命令由服务端注入 operation ID 与受控 evidence path，客户端伪造字段未进入命令。

REGRESSION: `python -X utf8 -m pytest scripts/tests tests -q --basetemp output/pytest-release-governance-p3-full` -> PASS, `144 passed in 42.37s`。

REGRESSION: `node --test scripts/tests/*.test.mjs` -> PASS, `6 passed, 0 failed`。

GREEN: `python -X utf8 scripts/verify_contracts.py` -> PASS, `PASS: standalone runtime-control contracts are present`。

GREEN: PowerShell AST -> PASS；`publish-int-ruoyi.ps1` 与 `ReleasePackageGovernance.psm1` 均无解析错误。

GREEN: `git diff --check` -> PASS；仅有 Windows LF/CRLF 提示，无 whitespace error。

### P3 Acceptance

- P3-AC1: PASS。`RuntimeControlOperationStore.findLatestSuccessfulTestPublish` 对 environment=`test`、action=`publish-test`、status=`SUCCESS`、`parameters.releaseTag` 精确匹配，错误环境/动作/状态/tag 均不能被选中。
- P3-AC2: PASS。客户端 DTO 未增加证据字段；`RuntimeControlService` 在写 NAS 临时配置前选择真实 operation，并向 mark/prod/backup 命令追加服务端 `-TestOperationId` 与 operation store 受控绝对路径。PowerShell 再读取 JSON 交叉验证 ID、环境、动作、状态、tag、UTC requestedAt；客户端伪造值未进入命令。
- P3-AC3: PASS。`Write-ReleaseTestedAttestation` 在完整性与 operation 验证后写入 schema v2，绑定 releaseTag、目录、package/manifest digest、test 环境、operation ID/status/requestedAt、testedAt、testedBy、结论；同目录临时文件通过原子 move/replace 提交，任一前置失败保持旧字节且无残留临时文件。
- P3-AC4: PASS。prod、backup 共用 `Test-ReleasePromotionAttestation`，重新计算完整性和双 digest，并逐字段绑定 tested 与同一 operation evidence；12 项 tested 字段变异和 payload 漂移均在后续动作探针前失败，两环境正向用例均通过。
- P3-AC5: PASS。PowerShell 与 Java 命令生成均移除 `RequireTested`，删除 `TEMPORARY_BACKUP_RECOVERY_GATE_DISABLED` 和旧 backup 放行函数；prod/backup 由 Environment 无条件执行同一 attestation 门禁。
- P3-AC6: PASS。本地完整 code-only fixture 完成 mark-tested v2 后分别通过 prod、backup gate；全量 Python、Java、Node、AST 与合同验证全部通过，外部调用为 0。

### P3 Remaining Risks

- 本任务按 non-goal 未增加包签名、SBOM、单一归档、NAS staging/READY 或目标服务器真实只读 preflight。
- 验证使用真实本机 PowerShell/Python/JVM 与隔离文件系统 fixture，未执行真实 NAS、SSH、Docker、数据库、MinIO 或服务器发布；上线前仍需按发布流程进行独立测试与受控真实环境验收。

### P3 Review Revision

RED: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q -k "blocked_rollback or mark_checks_rollback" --basetemp output/pytest-release-governance-p3-revision-red` -> FAIL, `2 failed, 55 deselected`；`New-RollbackCompatibilityEvidence` 返回 BLOCKED 时缺少 tested 写入前强制门禁。

GREEN: `python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q -k "blocked_rollback or mark_checks_rollback" --basetemp output/pytest-release-governance-p3-revision-green` -> PASS, `2 passed, 55 deselected`；BLOCKED 明确失败，既有 tested 字节保持不变，Mark 顺序锁定为 compatibility 计算、强制门禁、原子 tested 写入。

GREEN: selector 测试已迁入受版本控制的 `RuntimeControlOriginalParityTest.operationStoreSelectsOnlyExactSuccessfulTestPublishForReleaseTag`；共享 exclude 命中的本任务临时 `RuntimeControlOperationStoreTest.java` 已精确删除，未触碰主工作区同名并发 staged 文件。

REGRESSION: `mvn -f backend/pom.xml "-Dtest=RuntimeControlOriginalParityTest" test` -> PASS, `Tests run: 20, Failures: 0, Errors: 0, Skipped: 0`。

REGRESSION: `mvn -f backend/pom.xml "-Dtest=RuntimeControlContractTest,RuntimeControlOriginalGovernanceParityTest,RuntimeControlOriginalParityTest" test` -> PASS, `Tests run: 27, Failures: 0, Errors: 0, Skipped: 0`。

REGRESSION: `python -X utf8 -m pytest scripts/tests tests -q --basetemp output/pytest-release-governance-p3-revision-full` -> PASS, `146 passed in 41.07s`。

REGRESSION: `node --test scripts/tests/*.test.mjs` -> PASS, `6 passed, 0 failed`；`python -X utf8 scripts/verify_contracts.py` -> PASS；PowerShell AST -> PASS；`git diff --check` -> PASS。

### P3 Integration Revision

RED: `mvn -f backend/pom.xml "-Dtest=RuntimeControlOriginalParityTest" test` -> FAIL, main compilation；从 `RuntimeControlOperationStore` 删除本任务 selector 后，`RuntimeControlService` 仍引用已移除 API，证明 selector 所有权尚未迁移。

GREEN: `mvn -f backend/pom.xml "-Dtest=RuntimeControlOriginalParityTest" test` -> PASS, `Tests run: 19, Failures: 0, Errors: 0, Skipped: 0`；selector 已迁入 `RuntimeControlService` 私有方法。

GREEN: `git diff --exit-code b085f32e4953138467223a17a1afbe03e6b1ad7d -- backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlOperationStore.java` -> PASS；该共享文件精确恢复为本任务 baseline，未携带 selector 变更。

GREEN: tracked `RuntimeControlOriginalParityTest` 的 mark/prod/backup preview 分别注入错误 environment、action、status、releaseTag 与唯一 exact success；命令只包含 exact operation ID 和服务端 evidence path。Store 新 API 的直接测试已移除。

REGRESSION: `mvn -f backend/pom.xml "-Dtest=RuntimeControlContractTest,RuntimeControlOriginalGovernanceParityTest,RuntimeControlOriginalParityTest" test` -> PASS, `Tests run: 26, Failures: 0, Errors: 0, Skipped: 0`。

REGRESSION: `python -X utf8 -m pytest scripts/tests tests -q --basetemp output/pytest-release-governance-p3-integration-full` -> PASS, `146 passed in 38.85s`。

REGRESSION: `node --test scripts/tests/*.test.mjs` -> PASS, `6 passed, 0 failed`；`python -X utf8 scripts/verify_contracts.py` -> PASS；PowerShell AST -> PASS；`git diff --check` -> PASS。

### P3 Deterministic Ordering Revision

RED: independent post-integration Maven recheck -> FAIL，`RuntimeControlOriginalParityTest` expected `release-current` but received `release-current-other`；多个 operation JSON 具有相同文件 mtime 时，`resolveCurrentReleaseTag` 依赖文件枚举顺序，当前测试版本选择不确定。

GREEN: `RuntimeControlService` 对发布 operation 统一按 `requestedAt` 降序、`operationId` 降序确定性排序；精确 selector 先按 environment/action/status/releaseTag 过滤再排序。测试将 operation 文件 mtime 固定为相同，并覆盖旧 operation、同时间 operation、错误环境/动作/状态/tag。

GREEN: `mvn.cmd -f backend/pom.xml "-Dtest=RuntimeControlContractTest,RuntimeControlOriginalGovernanceParityTest,RuntimeControlOriginalParityTest" test`（JDK 17.0.20）-> PASS，`Tests run: 26, Failures: 0, Errors: 0, Skipped: 0`。

REGRESSION: `python -X utf8 -m pytest scripts/tests tests -q --basetemp "$env:TEMP/release-pipeline-hardening-20260907/ordering-full-final"` -> PASS，`146 passed in 41.22s`。

REGRESSION: `node --test scripts/tests/*.test.mjs` -> PASS，`6 passed`；`python -X utf8 scripts/verify_contracts.py` -> PASS；PowerShell AST -> `AST_PASS_2_FILES`；主审未连接任何外部环境。

## Outstanding Blockers

- None yet.

## Integration And Closeout

GREEN: implementation commits -> PASS，`ad9bf60`、`82c4d44`、`4303126` 仅包含本任务发布代码与测试；任务证据提交 `ee93103` 包含 PRD/test plan/state/execution/test report。

GREEN: int_main fast-forward -> PASS，主线与任务分支均为 `ee93103`；并发 `RuntimeControlOperationStore.java` 未提交改动保留且主工作区 Maven 27/27 PASS。

GREEN: merged-main verification -> PASS_WITH_BOUNDARY，JDK17 Maven 27、Node 6、PowerShell AST 2 files PASS；治理相邻 pytest 123 PASS，唯一失败为任务前已有 `frontend/src/App.vue` 删除。隔离 worktree完整全量 pytest 146 PASS。

GREEN: task worktree cleanup -> PASS，任务 pytest 临时目录已删除，worktree clean、提交已合入主线，Git worktree 注册与物理目录均已移除。

GREEN: task-closeout-cleanup -> PASS，主工作区 preview=ready、apply=applied，无 blocker；warning 仅为 cleanup candidate 已先行删除。

GREEN: experience-consolidation -> PASS，经验合并到 `docs/release-build-preflight-lessons.md` 并更新 `docs/experience-index.md`，未新建长期经验文档。
