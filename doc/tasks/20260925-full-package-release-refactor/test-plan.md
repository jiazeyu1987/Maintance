# Test Plan — 完整包与逐目标受控升级

## Environment and evidence contract

测试工作目录固定 `D:/IntRuoyiWorktree/full-package-release-maintenance`。所有命令在该 worktree 执行；不在维护/应用主工作区构建，不连接三台服务器。PowerShell 5.1、Python UTF-8、Node、Docker 已确认可用；配置/引擎缺失必须失败，不能 skip。

已接受范围变更 `CR-20260926-PROCESS`：验收目标是可复用发布流程，保留既有 T 图、AC-01～AC-12、TC-01～TC-14、完整 C7 与 Node/PS/AST/diff、C6-J。应用合同固定使用 `D:/IntRuoyiWorktree/full-package-release-application` 的任务提交 `af5acd8266e4ca1eb71e1d0581ece77fa4743d48`，仅作为 T6J 接口兼容基线和待交接切片。不跟踪或合并主程序 main；当前主仓版本构建、三服实时计划、实际部署及应用 main 合入验证不再是本轮门禁，不能因这些范围外事项未执行而判流程功能失败。

主管已准备独占 MySQL `release-fullpkg-8bea35`，卷 `release-fullpkg-8bea35-data`，网络 none，无主机端口。配置仅从 `E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/mysql-runtime.json` 读取。测试辅助必须校验 task/container/volume，拒绝共享容器与空配置；原 P1 测试的 `int-ruoyi-mysql` 固定名字必须先去掉，才允许运行。

卷归属以配置中的精确卷名、容器的本任务标签、实际 `/var/lib/mysql` 挂载匹配该卷且独占为证据。卷由 Docker 隐式创建，没有卷标签；不要求补标签或因缺标签拒绝，但不得省略精确挂载/独占检查，禁止使用任何共享资源。

统一会话环境（本身不打印配置内容）：

```powershell
$testUtf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $testUtf8
[Console]::OutputEncoding = $testUtf8
$OutputEncoding = $testUtf8
$env:PYTHONUTF8 = '1'
$env:RELEASE_TEST_MYSQL_RUNTIME_CONFIG = 'E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/mysql-runtime.json'
$env:RELEASE_TEST_APPLICATION_BACKEND_ROOT = 'D:/IntRuoyiWorktree/full-package-release-application/IntRuoyiBackend'
```

每个用例在 execution-log 写 BDD、RED、GREEN、REGRESSION 与退出码。独立测试者写 test-report：实际命令、提交、用例数/失败数、相关证据路径和逐 AC 结论。证据使用任务缓存目录，必要的脱敏结论回写任务记录；凭据和原始 secret-bearing 输出不得入 Git。所有新增测试先在未修复代码上证明预期业务失败，而非 ImportError/缺测试依赖。

行为测试执行真实 PowerShell 模块或用 AST 载入生产函数；仅在命令运输边界注入故障/记录调用，不复制函数算法。针对生成 shell/SQL 的测试必须实际运行其生成结果或验证真实数据库结果。源码字符串检查只作既有合同回归补充。

不得搭建假 backend HTTP 服务、返回伪造业务成功或复制 JSON 事务模拟器来声称完成端到端升级。可控的健康检查故障用于证明失败分支顺序；真实数据保留和实际内容身份必须由独占 MySQL/Docker 验证。本次不执行真实产品在三服的全链路 rollout。

历史规划外部前提（当前状态以 task-state/test-report 为准）：既有 smoke 功能固定使用官方 `mcr.microsoft.com/playwright:v1.60.0-noble`、Playwright 1.60.0、xlsx 0.18.5。规划时本地缺该镜像，官方镜像直拉及直连/Windows 7890 代理 manifest 读取均遇 TLS EOF，曾请求同版本官方离线包或可用代理；此记录不重新将已完成的 T2P 标为阻塞。T2 可验证组件/模板/准备器的实际代码行为和负例；真实 Linux 载荷生成、模块/浏览器验证单列为 T2P/C2P/TC-14，运行时前提缺失仍必须报告阻塞，不能 skip、换镜像/依赖源或用假模块通过。T4 可在独立验收 T2 代码合同及 T3 后继续；T7 和 AC-02 的最终通过必须有 T2P 的完整证据。

## Executable validation commands

以下 C1～C7 是任务的必跑入口。新增文件由相应 T 任务先建立测试再实现；最终执行器可以运行 `scripts/tests/run-full-package-release-tests.ps1` 汇总相同清单，不能删除失败项、默认跳过真实 MySQL/Docker 或改成全部返回成功。

### C1 — P1 依赖 RED/GREEN 与回归

```powershell
python -X utf8 -m pytest -q scripts/tests/test_release_migration_supersession_contract.py scripts/tests/test_release_preflight_r20_regressions.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_preflight_plan_order.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_schema_rehearsal.py scripts/tests/test_release_package_governance.py scripts/tests/test_release_operation_lock_mysql_behavior.py
```

测试源路径统一只读指向上述固定任务应用 worktree 的真实源码和 `af5acd8266e4ca1eb71e1d0581ece77fa4743d48` 接口基线；禁止重建不存在的旧 backend 源码副本或追随当前主程序 main。P1 中已有的真实执行 PS 函数及生成 SQL 测试保留，不换成内存模型。

### C2 — 完整包、不可变和旧调用合同

```powershell
python -X utf8 -m pytest -q scripts/tests/test_release_full_package_contract.py scripts/tests/test_release_package_governance.py scripts/tests/test_app_release_package_governance.py scripts/tests/test_runtime_control_frontend_deploy_contract.py scripts/tests/test_release_digest_vectors.py
node --test scripts/tests/publish_frontend_deploy_sql_gate_contract.test.mjs
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/tests/verify-release-digest-vector.ps1
```

T2 保留完整包、组件、模板、包外渲染、准备器行为与全部负例测试；缺官方镜像/锁文件/载荷须报明确错误，目标安装不得在线 npm install。单元测试中的最小 tar/模块描述仅用于合同正反例，不能证明真实 Linux 依赖可加载；AC-02 还必须有 C2P/TC-14 真实证据。

### C2P — 真实 Linux smoke 载荷、模块和浏览器

只有同版本官方镜像已通过可用官方网络或用户提供的同版本官方离线文件取得后才可执行完整正例。镜像前提检查失败即记录 blocker，不将后续用例 skip 后汇总为 PASS。

```powershell
docker image inspect 'mcr.microsoft.com/playwright:v1.60.0-noble' --format '{{.Id}} {{json .RepoDigests}}'
$env:RELEASE_TEST_SMOKE_PAYLOAD_ROOT = 'E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/smoke-payload'
python -X utf8 -m pytest -q scripts/tests/test_scheduler_smoke_linux_payload_integration.py
```

集成测试实际调用 T2 的生产准备函数/生成 shell，在指定 Linux 镜像内由真实 package-lock 生成依赖 tar；将真实结果加入正式格式包后走实际治理函数。验证时用相同 imageId、network none 和任务临时容器解包，真实加载 playwright/xlsx、核对版本与锁文件、执行 xlsx 往返、启动并关闭浏览器；不连接产品或写业务数据。必须记录镜像引用、实际 `.Id` sha256、RepoDigests（如实际存在）、离线来源及归档 sha256、生成载荷的字节/sha256、锁文件摘要和包双摘要。不得替换镜像版本/来源，缺真实模块、浏览器或镜像字节不能用测试替身放行。

### C3 — 三基线计划及状态指纹

```powershell
python -X utf8 -m pytest -q scripts/tests/test_release_target_bound_plan.py scripts/tests/test_release_preflight_plan_order.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_migration_supersession_contract.py scripts/tests/test_release_preflight_r20_regressions.py scripts/tests/test_release_target_data_preflight.py
```

### C4 — 首次运行写入前门禁

```powershell
python -X utf8 -m pytest -q scripts/tests/test_release_readonly_deploy_gate.py scripts/tests/test_release_operation_lock_mysql_behavior.py scripts/tests/test_release_workflow_preflight.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_target_data_preflight.py
```

C4 必须包含可观察的生产 PowerShell 调用测试：覆盖 intruoyi/full 与 OnlyOffice 纳入/未纳入的全部组合，逐条检查实际生成并派发的应用和 Website `docker compose up` 都显式携带 `--no-deps --pull never`。OnlyOffice 纳入时不能省略参数；所需包内镜像未在目标已加载集合中确认时必须明确拒绝，观察到没有应用启动、registry pull 或平台依赖补齐调用。不得只断言源码包含参数，也不能构造另一套启动命令冒充生产路径。T2 的 runtimeImages/smoke 载荷合同、T5 的真实 imageId 核验与既有真实引擎验收全部保留。

T4 还必须运行完整 C2 回归，验证新增 targetPreflight 字段和检查载荷不破坏完整包合同。C4 调用真实 `Copy-RequiredDatabaseSqlScripts` / `New-ReleaseRequiredSqlManifestEntries`，验证从冻结源码复制对应检查到包内 `target-preflight/`，生成 `targetPreflight={reference,sha256,readOnly}` 且实际文件被 artifacts/packageDigest 覆盖。复用现有 `release_target_preflight_contract.py`；部署仅读取包内 checks，覆盖 test/prod/backup 目标参数和实际执行路径，以及缺文件、摘要漂移、无 PASS、非只读和锁内目标事实变化的失败行为。用任务隔离资源执行生产调用，不连接真实三服、不增加 SQL 安全框架，也不跳过 T2P 或既有真实引擎验收。

获批的治理/测试修改限 `ReleasePackageGovernance.psm1` 与 `test_release_full_package_contract.py` 中 targetPreflight 的缺件、sha256、readOnly 和引用一致性正反例。必须验证非 schema APPLY 依据现有 policy/实际 SQL 元数据要求检查，manifest 缺少 requiresTargetPreflight 或将它伪改为 false 仍不能绕过；引用不一致也明确拒绝。C2 全量执行，不只筛选新增用例。

C4 另用真实任务临时 Git 仓库调用生产同包工具链门禁（FR-02/FR-07、AC-05/AC-12）：manifest 维护 sourceRoots.approvedCommit/commit 与当前执行器维护 HEAD 一致且相关 tracked/untracked PS/Python/模块源码干净时通过；不同检出路径及缺少应用源码不构成拒绝条件。换 HEAD、仅改 Python、仅改 PS、增加相关 untracked 代码分别明确拒绝并证明无远端写入。保留 Java 既有 PS 配置 SHA 校验；即使重新配置该 pin，也不能用不同工具链为旧包重新生成目标计划。仅修改已批准 PS/readonly 测试，T7 通过 C7 全量复验，不新增 AC 或框架。

### C5 — 实际镜像和静态载荷身份

```powershell
python -X utf8 -m pytest -q scripts/tests/test_release_runtime_identity.py
node --test scripts/tests/publish_release_info_contract.test.mjs scripts/tests/publish_image_tar_transfer_contract.test.mjs
```

### C6 — 持久失败证据与恢复阻断

```powershell
python -X utf8 -m pytest -q scripts/tests/test_release_durable_deployment_evidence.py scripts/tests/test_release_operation_lock_mysql_behavior.py scripts/tests/test_publish_release_lock_cleanup.py scripts/tests/test_release_workflow_preflight.py scripts/tests/test_release_deployment_transaction.py
```

### C7 — 最终集成

```powershell
$env:RELEASE_TEST_APPLICATION_BACKEND_ROOT = 'D:/IntRuoyiWorktree/full-package-release-application/IntRuoyiBackend'
python -X utf8 -m pytest -q scripts/tests/test_release_full_package_mysql_integration.py scripts/tests/test_release_full_package_workflow_integration.py
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/tests/run-full-package-release-tests.ps1 -RuntimeConfigPath 'E:/Int/CacheData/IntRuoyi/tests/full-package-release-refactor/mysql-runtime.json' -ApplicationBackendRoot 'D:/IntRuoyiWorktree/full-package-release-application/IntRuoyiBackend'
git diff --check
```

C7 汇总 C1～C6、C2P 与两个集成测试，不重复执行已包含的同一个用例；同时校验生产 PowerShell 脚本 AST 无语法错误。T7 必须等待 T2P、T6、T6J 全部完成，汇总入口不得排除真实 Linux 载荷测试，AC-02 不能凭 T2 代码合同提前完成。T1 读取应用主线合同，最终集成读取本任务应用 worktree；不在应用主工作区产出 target/node_modules。未变化的参数合同，以真实 PowerShell 接受实际 intruoyi/full 参数、manifest/stage 协议为主，源码交叉核对为辅。T6J 的状态语义改动必须单独执行 C6-J 并纳入最终证据，不要求无关 Java 全量构建。维护仓持久部署门禁必须有实际运行的独立证据；源码搜索或 Java 单测不能替代它。

T7 配置与重建验收补充（AC-12/TC-12）：本段只约束 T7 实施，不改变 T6 当前冻结源码与独立验收。主管确认 T2P/T6/T6J 全部完成并移交后，使用原 `-RuntimeConfigPath` 明确提供 MySQL 及 classic 运行配置；由 `release_test_runtime.py` 集中解析。除既有 MySQL task/container/volume/password 外，classic 使用实例完整 ID、名称、独占卷、任务归属；任务缓存/前缀、MySQL 容器内真实 flock 工具目录及真实官方归档绝对路径/bytes/sha256/内容身份必须明确，runner 为现有 smoke payload 输入提供配置。不得打印/提交原始配置或 Docker Env。直接运行 C5/C6/两个集成测试也须使用同一显式配置，不依赖 C7 进程残留状态。

主管须在 T6 独立验收结束后，按任务归属与经验门禁安全准备/重建 classic 引擎，提供不同于旧 `1077b4a2af5f527ad2f57b99a72734d03578e256e0552f60fbaf48518d8a13fb` 的真实实例 ID，记录更新后的脱敏配置身份。执行者/测试者不得自行操作外层容器/卷生命周期。正式 C7 与独立复验必须在新 ID 上完整执行，不能保留旧容器或修改 ID 断言来规避重建；既有 MySQL 数据卷归属与隔离规则仍全部适用。

配置门禁在任何 fixture 写入之前核对配置完整 ID 与名称解析结果一致、任务标签、running、精确挂载与独占卷消费者、network none、零发布端口、无宿主 Docker socket、Docker 26.1.4/classic overlay2，以及所需工具可执行。固定官方 dind 引用保持 `docker.io/library/docker@sha256:dd43b430341a40d88f4f30edb03865daa9d6fa39c9b1da70f27e2a89cec3eae1`；Playwright 保持 1.60.0，内容 configDigest 保持 `sha256:ab853f51b03036cd52e74771c2dd07ee1471c408645048e928af67db6beae6d7`。实际归档 bytes/sha256 必须匹配显式配置，并继续由生产治理核对 descriptor/config/layers 与真实加载内容；不可将固定官方内容摘要误当一次性 ID 去除，不可重打包或改版本掩盖输入不符。

基础设施配置 RED 与产品业务 RED 分开记载：先在 T7 已有新增范围 `test_release_full_package_workflow_integration.py` 中增加可执行的配置行为测试，证明未修复辅助仍绑定旧实例/路径或缺少严格拒绝，再最小实现；缺少测试文件、ImportError、Docker/归档/工具前提不可用只能记录 blocker。配置负例使用临时脱敏配置副本，覆盖缺字段/空配置、旧 ID、名称与 ID 错配、错误任务/卷/挂载、无效路径/工具目录、归档 bytes/sha256 错配，逐例确认非零退出、明确原因及没有 fixture 写入；不创建共享/不安全资源制造负例，不使用 mock 成功。正确显式配置必须在真实新 ID 上完成 C7 全量及 C6-J；既有产品业务 BDD/RED 与故障矩阵不能被配置测试替代。正式脱敏验收报告和可追溯证据必须留存；临时配置副本/fixture 与外层任务引擎按归属和主管 closeout preview/apply 清理，记录删除结果与残留检查，不删除正式报告。

### C6-J — Java 状态语义回归

仅在主管冻结的 `D:/IntRuoyiWorktree/full-package-release-application/IntRuoyiBackend` 执行，固定任务提交 `af5acd8266e4ca1eb71e1d0581ece77fa4743d48`；不改用主程序 main 或另一个任务的 worktree，不以当前主仓版本或应用合入结果替代该接口切片。

T6J 没有维护仓任务依赖，可与 T1 并行；历史开发起点 `840b9ef`、批准差异和独立应用 worktree 的证据保留，当前 C6-J 以固定 `af5acd` 七文件切片回归。槽位 35 和执行 guard 的归属规则保留，不因范围变更启动共享服务。验证要求不变，最终 T7 须等待 T2P、T6 与 T6J 完成。

```powershell
mvn -f 'D:/IntRuoyiWorktree/full-package-release-application/IntRuoyiBackend/pom.xml' -pl yudao-module-infra -am '-Dtest=RuntimeControlServiceImplTest,ReleaseWorkflowOrchestratorTest,ReleaseWorkflowRecoveryTest' '-Dsurefire.failIfNoSpecifiedTests=false' test
```

按仓库既有 Maven/JDK 启动约定执行，不手工 javac、不拼 classpath、不复制 Java 源码为独立测试工程。必须核对 surefire 中三个指定目标测试实际发现且运行。T6J 及 TC-13 是主管已确认的必做项，不能省略。

## Test cases

### TC-01 — 已批准依赖在本任务冻结基线复现

- test_case_id: TC-01
- mapped_task_ids: T1
- mapped_acceptance_ids: AC-03、AC-04、AC-06、AC-11、AC-12
- environment or setup: 本任务干净维护 worktree，先迁入获批 P1 的相关测试增量；读取提交内容不导入其任务文档。MySQL 使用上述独占配置。
- steps: 先在维护任务起点 `3f3aabd` 跑能够复现缺陷的 supersession/拓扑和生产锁 SQL 测试，记录 RED；选择性迁入 15 路径生产增量后跑 C1；审核 diff 中没有 d316da9 input-preparation、别人的任务文档或应用变更。既有历史 RED/GREEN 保留，不因当前主程序 main 演进重开 T1。
- expected_result: RED 因既有功能缺陷失败；接入后通过；真实锁 SQL 保护所有权、租约和 fence，测试只触及任务数据库；无默认共享容器/默认密码路径。
- evidence: 15 路径差异清单、实际 failing test id、RED/GREEN 输出、真实 container/volume 非秘密身份和 SQL 结果。

### TC-02 — 完整组件固定且不可缩窄

- test_case_id: TC-02
- mapped_task_ids: T2
- mapped_acceptance_ids: AC-01、AC-12
- environment or setup: 真实治理模块 + 发布入口函数，生成合法 intruoyi/full 最小包，包含真实格式 manifest/摘要/来源；不调用远端。
- steps: 对 backend/frontend/website 单组件分别执行入口参数路径；合法 intruoyi/full 通过；OnlyOffice 纳入/不纳入分别核对；部署显式覆盖、缺失 component、覆盖 OnlyOffice 均拒绝；读取真实 Java Action 构建/晋级参数进行合同验证。
- expected_result: backend+frontend 始终成套；选择固定在 manifest，目标不能改；稳定错误指向非法参数；保留三模式/三环境/source selection/tested v2/正式授权参数。
- evidence: C2 行为结果、实际解析参数/组件集合脱敏输出；旧参数负例错误。

### TC-03 — 缺安装输入立即失败与包不可变

- test_case_id: TC-03
- mapped_task_ids: T2
- mapped_acceptance_ids: AC-02
- environment or setup: 合法包分别移除 Compose、Website 模板、受选镜像/静态文件、必需宿主工具或其平台声明；工作区保留同名模板作为反例诱因。
- steps: 逐项调用真实完整性/安装输入验证；记录运输调用次数；用两种目标配置实际生成控制文件，再比对包全部字节/清单双摘要；搜索控制输出秘密仅用于明确测试占位凭据，绝不取真实凭据。
- expected_result: 缺件或平台前提失败在目标运行写入前拒绝，不拿工作区补齐；`.env`/nginx/Website 渲染只在包外；两个目标部署准备均不改变包内容；包不含目标凭据或业务快照。
- evidence: 缺件矩阵、运行写入次数为零、前后摘要、目标控制文件路径。

### TC-04 — 同包三起点确定性计划

- test_case_id: TC-04
- mapped_task_ids: T3、T7
- mapped_acceptance_ids: AC-03、AC-07
- environment or setup: 一个不可变包固定 M1→M2→M3→M4，三个任务基线分别已合法完成 M1～M3、M1、M1～M2；必要 schema/data 前提齐备。分别绑定 test/prod/backup 逻辑环境，这些只是本地任务数据库标签。
- steps: 实际计划器 API 与 CLI 各运行两次；核对不同 APPLY 清单和相同包双摘要；在真实隔离 MySQL 中执行同一包并重新读结构/台账/历史行。
- expected_result: 分别执行 M4、M2～M4、M3～M4，顺序符合依赖，已成功相同摘要跳过；最终满足同一目标合同；业务行内容保留；不得据此声称真实三服基线受支持。
- evidence: 三份计划、执行 SQL 序列、同包摘要、每库升级前后真实记录及 ledger。

### TC-05 — 历史异常和依赖非法均阻断

- test_case_id: TC-05
- mapped_task_ids: T3、T4
- mapped_acceptance_ids: AC-04
- environment or setup: 完整相关台账含 APPLIED 摘要差异、FAILED、RUNNING、未知状态、重复 ID；迁移含缺依赖/环/被环境排除的必要依赖；同时保留合法 metadata-only 等价和获批 supersession 正例。
- steps: 用真实计划器逐例生成计划；运行实际台账采集生产 SQL，验证失败记录没有被成功过滤；尝试执行 blocked/未知 action 计划。
- expected_result: 具体阻断，不重跑成功摘要漂移、不擦写失败台账；合法等价/supersession 按合同通过；所有失败不触发迁移执行。
- evidence: C3/C4，真实 SQL 返回状态清单、稳定错误码、执行计数。

### TC-06 — 计划绑定与锁内漂移

- test_case_id: TC-06
- mapped_task_ids: T3、T4
- mapped_acceptance_ids: AC-05、AC-12
- environment or setup: 合法计划含全部身份/指纹，真实函数的运输边界指向任务资源；锁 acquire 使用真实任务 MySQL。
- steps: 分别修改包摘要、manifest 摘要、releaseTag、环境、host、数据库实例、执行器/计划器身份、schema、完整 ledger、持久挂载、非秘密配置；在预检生成后锁内复核前注入变化；缺字段和篡改动作也验证。
- expected_result: 任一身份/关键状态不一致拒绝旧计划；只允许已明确的控制锁记录，没有迁移、运行目录/配置修改或应用切换；不同采集时间不改变相同业务输入的动作排序。
- evidence: 每项变化的拒绝断言，调用顺序，控制写入与运行写入计数；包摘要未变。
- package-toolchain evidence: C4 真实临时 Git 仓库的 HEAD/干净状态和生产调用结果；同包跨目标计划均使用 manifest 固定的维护提交，HEAD/PS/Python/相关 untracked 漂移在远端写入前拒绝。不同检出路径及应用源码缺失正例通过，T7 再验证；映射现有 AC-05/AC-12，不替代原计划指纹测试。

### TC-07 — 只读预检不补齐目标平台

- test_case_id: TC-07
- mapped_task_ids: T4
- mapped_acceptance_ids: AC-06
- environment or setup: 任务目录/容器/数据库准备完整有效基线，逐例拿走挂载标记、数据目录、控制表/列、锁过程、配置项、平台工具前提或数据前提；记录运行文件/数据库前快照。
- steps: 实际生产预检/主链函数生成命令并执行合法只读部分；对全部运行写入命令做可观察运输边界记录；失败后重新读取文件、schema、业务行、容器身份；有效基线验证先预检后锁、锁内复核后运行写入。再覆盖 intruoyi/full × OnlyOffice 纳入/未纳入的实际应用及 Website 启动调用，核对 `--no-deps --pull never`，并逐项提供缺少应从包内加载镜像的负例。
- expected_result: 预检失败前不 mkdir/mount、不覆写 Compose/.env、不 CREATE/ALTER 控制 schema、不 docker load/recreate 或启动平台；资源缺失返回具体正式准备要求。通过前置门禁后的所有应用/Website compose up 均显式禁依赖启动与拉取，OnlyOffice 分支无例外；缺已加载镜像明确失败，绝不从 registry 补齐。不能只靠源码无某个单词证明只读或启动策略正确。
- evidence: C4、预检失败前后文件摘要/schema/行/容器身份相同，生产函数实际调用追踪、四种组件组合的 compose 实参、缺镜像错误及零启动/拉取/平台依赖补齐调用断言；T5 和 TC-08/TC-14 的真实身份/载荷证据仍为必要验收。
- package-check verification: 记录真实 builder 产出的 target-preflight 文件及 targetPreflight/artifacts 摘要、部署不读取包外源码的调用证据、三环境目标匹配、明确 PASS 和锁内目标事实复核；缺件/漂移/缺 PASS/非只读任一失败必须阻断运行写入，附 C2 全量回归结果。该项补充原 TC-07，不减少任何原 AC 或用例。

### TC-08 — 真实镜像身份与静态载荷

- test_case_id: TC-08
- mapped_task_ids: T5、T7
- mapped_acceptance_ids: AC-08、AC-09
- environment or setup: 任务 Docker 标签前缀 `release-fullpkg-8bea35-`；两个实际 imageId 不同的最小镜像，绑定同一 tag；任务静态文件集合。现有业务镜像/容器不得 retag/recreate。
- steps: 用生产函数读取实际容器 `.Image`，先同标签异内容拒绝，再正确内容通过；对每个选中组件参数化；Website 少文件、改内容、多旧文件拒绝，正确载荷通过；健康失败覆盖身份全部正确的情况。
- expected_result: 标签相等不能通过，完整所选组件缺任意一个不能成功；OnlyOffice 和 Website 按包选择验证；未选独立产品不假冒整包版本。
- evidence: 真实 image/container ID、期望/实际对比、静态文件摘要、C5；零生产容器变更证据。

### TC-09 — 持久阶段必须先于可能写入

- test_case_id: TC-09
- mapped_task_ids: T6
- mapped_acceptance_ids: AC-10、AC-11
- environment or setup: 生产证据模块与部署函数；包外持久状态根，实际任务 MySQL 和暂存文件；单元故障在 I/O/运输边界注入。
- steps: 拒绝阶段记录落盘，证明后续写入不执行；持久 STARTED/writeAttempted 后执行一条真实 DDL/迁移，再让下一条失败；迁移完成后注入 env/容器切换错误；原始异常后使观察也失败；运行新进程重读证据。
- expected_result: 已开始阶段和原/目标身份、已完成迁移可持久读取；无法观测的 actual 状态明确 unknown/error；主异常保留，不自动回滚/修台账/删除失败证据；零运行写入与可能写入可区分。
- evidence: C6、真实部分迁移台账、各阶段先后序列、第二进程读取结果、原始和观察错误独立字段。

### TC-10 — 中断后下一部署与锁恢复拒绝

- 同标签多次尝试补充：实际锁 operationId 保持不变、lease 不同，派生的 attemptId 和持久文件必须不同；前次文件字节保留。前次未解决 gate 阻断新尝试，旧 lease 恢复不能作用于新 lease；gate 指向其它 attempt、文件缺失/损坏/重复字段或身份不符时恢复 UPDATE 为零。可信零写入显式恢复后再次执行，也必须保留旧尝试证据。不改变现有外部恢复参数或 Java 四参数合同。

- test_case_id: TC-10
- mapped_task_ids: T6、T7
- mapped_acceptance_ids: AC-11、AC-12
- environment or setup: TC-09 产生持久门禁；任务持久锁 heartbeat 人为过期，仅在任务库；执行器作为独立子进程运行，不能杀共享进程。
- steps: 持久 STARTED 后中断任务执行器，再新启动生产部署入口的目标门禁；分别模拟原锁 RUNNING、FAILED 和 stale heartbeat；调用真实显式锁恢复函数；删除临时 deployControlLocalRoot 后重试读取。
- expected_result: 均识别未解决写入/未知状态并阻断；过期心跳和本地临时文件消失不会放行；新 operation 不覆盖失败事实；预检拒绝且有可信 zeroWriteEvidence 的记录按既有合同处理，不伪造写入。
- evidence: 子进程 PID/退出码（仅任务进程）、持久记录与真实锁结果、两入口的拒绝原因、调用方参数合同回归结果；Java 状态不一致由 TC-13 单独处理。

### TC-11 — 成功终态包含清理和完整最终化

- test_case_id: TC-11
- mapped_task_ids: T5、T6、T7
- mapped_acceptance_ids: AC-09、AC-10、AC-11
- environment or setup: 全部身份/迁移/配置/健康成功的任务资源；任务专有暂存文件，包外持久回执根。
- steps: 先正常完成；再分别在组件验证、清理、历史落盘、回执落盘、锁 APPLIED 落盘阶段失败；实际读取剩余 gate/receipt/lock/history，尝试下一部署。
- expected_result: 正常路径记录包双摘要、目标、期望/实际身份、迁移/配置/健康与完成时间，暂存清理后持久证据仍存在；任一最终化失败不输出整体成功，不提前释放可重试门禁；未知终态明确阻断，没有 APPLIED 后仍执行的失败清理伪成功窗口。
- evidence: 逐故障点终态矩阵、最终回执、锁/历史对账、后续部署拒绝；正常路径下一合法部署可取锁的正例。

### TC-12 — 数据边界和工作流合同回归

- test_case_id: TC-12
- mapped_task_ids: T7
- mapped_acceptance_ids: AC-07、AC-12
- environment or setup: 真实任务 schema 带历史订单/附件引用及任务 tenant 标记，挂载身份固定；当前应用源码只读输入，tested v2 和 source selection 使用既有合法测试向量。
- steps: 三起点升级前后按主键核对全部历史行/字段和数据库挂载身份；实际调用路径验证无源库 dump/MinIO 导入、受保护展厅和审核矩阵写入；运行 C7、digest vector 和真实生产 PowerShell 对现有 Java 所发参数的接受/拒绝测试；审阅两份运维文档。
- expected_result: 历史业务数据完整，只有包声明迁移发生；完整包/预置要求/旧基线拒绝/恢复门禁明确；现有 intruoyi/full 调用、SourceSelectionId、来源提交、tested v2、正式 dry-run/授权不退化；无 UI 或服务器范围膨胀。
- evidence: 前后记录摘要和差异为空、真实 mount 身份、C7 完整结果、调用合同测试计数、文档审阅记录。
- T7 infrastructure BDD: Given 主管重建的任务 classic 引擎具有新完整 ID 且官方内容身份不变，When 通过原 RuntimeConfigPath 载入严格匹配配置运行 C7，Then 全部既有业务用例实际执行并通过；Given 配置缺失或实例/归属/卷/工具/归档身份不符，When 进入测试基础设施门禁，Then 在首次 fixture 写入前明确失败，不默认连接共享引擎或回落旧硬编码值。
- T7 infrastructure steps: 先完成配置行为 RED/GREEN，再由主管交接新引擎与显式运行配置；依次执行配置拒绝负例和新引擎 C7 完整正例，保留 C2P 与 C6-J。审阅两份既有 runbook 是否写清本地任务资源和工具准备、官方归档身份、配置字段、重建/清理及同命令复跑，目标平台只支持可核验路径 classic overlay2、1 GiB 仅最低数据盘余量；不得新增长期文档或扩大远端操作范围。
- T7 infrastructure evidence: 旧/新容器 ID（必须不同）、新实例名/标签/精确卷和独占消费者、网络/端口/socket/版本/驱动结果、归档路径/bytes/sha256/官方内容摘要、工具检查、配置负例原因及零 fixture 写入证据；配置结构和摘要脱敏记录，密码不入日志。独立 C7 的实际命令、退出码、发现/运行用例计数、有效报告、源码 HEAD/diff/文件哈希及任务 fixture 残留检查均需记录。只替换硬编码后在旧实例运行或只通过配置负例，均不能关闭 AC-12/TC-12。

### TC-13 — 上下层对写入失败结论一致

- test_case_id: TC-13
- mapped_task_ids: T6J、T7
- mapped_acceptance_ids: AC-10、AC-11、AC-12
- environment or setup: 本任务应用切片固定为 `af5acd8266e4ca1eb71e1d0581ece77fa4743d48`；历史开发从 `840b9ef` 开始、仅选择性复用 `d30f7ee02` 引入状态修复的证据保留。四个生产文件/三个测试范围由 development-plan 冻结；使用真实 Maven/JUnit 的现有业务服务测试，不新建人工 Java 编译环境，不跟踪或合并当前应用 main。
- steps: 写 BDD 后 RED 重现 TEST_DEPLOYING/PROMOTING_PROD operation failed/blocked、dispatch 异常、无可信零写入时错误的 FAILED/retryable 行为；经选择性依赖接入或最小修复后 C6-J；同时验证预检明确零写入、正常成功、正式授权和重试路径。
- expected_result: 可能写入/未知结果进入 RECOVERY_REQUIRED、retryable=false，保持所需环境隔离；明确零写入的预检失败不被误认为写入后失败；workflow-bound dispatch/zeroWriteEvidence 不能被无关请求伪造；同一事实不能底层阻断而上层声称安全重试。保留四参数 acceptTest、正式授权和来源绑定，UI 不变。
- evidence: 七个路径的精确差异清单、RED/GREEN、surefire 实际测试数量与状态断言；禁止引入 recovery-set 第五参数和 P2～P5 的差异审阅。

### TC-14 — 随完整包交付的真实 Linux smoke 载荷

- test_case_id: TC-14
- mapped_task_ids: T2P、T7（T2 提供已独立验收的生产准备器与锁定合同）
- mapped_acceptance_ids: AC-02、AC-08、AC-12
- environment or setup: 精确官方 `mcr.microsoft.com/playwright:v1.60.0-noble` 实际镜像可用，`ops/release/smoke/package.json` 与真实 package-lock 固定 Playwright 1.60.0 / xlsx 0.18.5；任务专属缓存、容器和包。当前官方镜像不可用及 TLS EOF 是明确外部 blocker，不能用其它镜像、版本或依赖源替代。
- steps: 运行 C2P，调用生产准备器在 Linux 里实际按锁安装并生成 dependencies.tar；记录包/锁文件字节；检查随包镜像归档与准备器使用的真实 imageId 一致。在无网络的任务容器解包，真实 require playwright/xlsx，核对锁定版本和完整依赖，执行 xlsx 读写往返、真实浏览器启动/版本/关闭。调用实际包治理验证字节清单；移除/篡改载荷或镜像时必须拒绝。
- expected_result: 部署所需真实模块、浏览器和运行镜像完整随包交付，解包后无需在线 npm install 或临时下载；准备/验证使用相同镜像内容，实际载荷摘要与 manifest/packageDigest 一致。网络不可达或锁依赖无法获取明确阻断；最小 fixture tar、只有 package.json 的空壳模块和 mock 命令成功均不能完成此用例。
- evidence: 官方镜像引用、实际 imageId sha256、现有 RepoDigests/离线来源与镜像归档 sha256、package-lock 摘要、实际模块版本和库/浏览器退出码、dependencies.tar/随包镜像的字节长度与 sha256、包双摘要、无网络执行记录和独立验证结果。T2 的代码测试证据与 T2P 的真实制品证据分别记载。

## Acceptance coverage and release boundary

| Acceptance | Required cases |
|---|---|
| AC-01 | TC-02 |
| AC-02 | TC-03、TC-14（T2P 未完成不可通过） |
| AC-03 | TC-01、TC-04 |
| AC-04 | TC-01、TC-05 |
| AC-05 | TC-06 |
| AC-06 | TC-01、TC-07 |
| AC-07 | TC-04、TC-12 |
| AC-08 | TC-08、TC-14 |
| AC-09 | TC-08、TC-11 |
| AC-10 | TC-09、TC-11、TC-13 |
| AC-11 | TC-01、TC-09、TC-10、TC-11、TC-13 |
| AC-12 | TC-01、TC-02、TC-06、TC-10、TC-12、TC-13、TC-14 |

最终独立测试者在冻结的维护任务 worktree 上重跑完整 C7（保留全部 Node/PS/AST/diff），并对固定 `af5acd` 接口切片执行 C6-J，绑定任务 HEAD、diff 摘要与受验文件哈希，按上表核验；必要验证通过后才提交维护任务自有交付物，不把预先提交当作验证前提。相关用例缺真实引擎证据或只剩字符串断言时 FAIL，不以其余测试通过替代。若固定接口基线的测试暴露范围外合同问题，记录准确路径与失败行为，由主管决策；测试者不得自行修复或转而追踪当前主程序 main。

T2/T2P 拆分只改变独立代码工作的调度边界，不减少任何原有 AC 或 TC-01～TC-13；TC-14 的真实制品要求保留为必要验收。官方镜像等外部前提未解决时，允许独立验收稳定 T2 代码后继续 T4，禁止把 T2P、AC-02、T7 或整个目标标完成。

本轮不要求以当前主仓版本构建候选包、生成三服实时计划、访问 NAS、实际部署、登录真实前端或修正现场历史迁移/锁，也不要求应用 main 合入验证。后续每次现场发布仍须另行指定已提交来源，取得明确授权，并完成每台真实起点的只读预检和业务验收。测试通过仅证明本地受控范围内可复用发布流程符合合同，不宣称服务器实际就绪，也不证明任意旧版本都可以升级。

资源清理由主管执行 preview/apply，只处理已确认属于本任务且允许收尾的容器/卷/镜像/缓存/worktree；应用 `af5acd` 切片保留待交接，不扩大为主程序仓合并或清理。持久正式测试报告和任务记录必须保留；真实隔离测试、独立审查、维护任务自有交付物提交与复核、本任务清理门禁完成后才可标 completed。此前应用 main 合并结果验证要求由 `CR-20260926-PROCESS` 取代；维护仓无 origin 的推送限制单独保留，不声称已推送。
