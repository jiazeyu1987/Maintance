# 自动备份链独立验收

`verify_automatic_backup_chain.py` 只读取已完成操作的原生证据。它不会发起备份、查询 HTTP、执行 SQL、调解控制台账、恢复数据或重载服务。新报告使用独占创建；已存在的报告不会覆盖。旧367验证脚本与原回执保持不变。

## 前提

- FULL373保留原 `automatic-control-installation-57.json`、0d44578构建/包及全部成功原件，不重跑或覆盖。I1/I2必须先有 `automatic-{i1,i2}-deployment-selection.json`，由统一 `automatic_stage_deployment` 验证对应公开/私密source安装、构建、Spug与逐controller代次。所有选定提交的STANDARD tgz保留于本机私密目录。
- 对应真实 UI `automatic-{full,i1,i2}-ui-submission.json` 已保存原始 request。UI 回执本身不能证明原生成功。
- 控制 registry 已发布该操作的成功 point，原 owner 已退出。缺点、缺终态、还在运行、epoch 变化时脚本失败，不等待或重试派发。父任务在正常 UI 终态后再执行即可。

## 调用

在当前维护仓根目录用任务 Python 执行；以下文件名是收尾验证的固定合同：

```powershell
$auditPython = 'C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$auditHelper = 'doc/tasks/20261106-spug-prod-incremental-to-two-targets/verify_automatic_backup_chain.py'
& $auditPython -B -X utf8 $auditHelper --submission automatic-full-ui-submission.json --output automatic-full-audit.json
& $auditPython -B -X utf8 $auditHelper --submission automatic-i1-ui-submission.json --parent automatic-full-audit.json --output automatic-i1-audit.json
& $auditPython -B -X utf8 $auditHelper --submission automatic-i2-ui-submission.json --parent automatic-i1-audit.json --output automatic-i2-audit.json
```

附加 `--prepare-only` 仅核本机提交、安装、包与请求输入，不连接服务器、不写报告，也不证明备份成功。

I1/I2必须使用v2 UI submission，精确绑定stage selection pin、source commit和Spug commit。wrapper读取所选source实际控制pin，不默认复用旧0d控制。`--installation`可省略；显式传入时必须与stage选择的source安装文件相同。后续源码提交不能替代操作当时真正使用的安装。sourceproof同时核新source和保留MAIN各自130成员manifest；服务配置摘要由MAIN自身Python、PYTHONPATH及程序文件计算，两个runtime分别记录实际模块/依赖pins。新审计/源证明包含 `deploymentSelectionPin/sourceCommit/spugCommit/sourceInstallationPin/controllerGenerations`；历史FULL报告不追补字段或改写。

## 验证范围

1. 已安装130文件 STANDARD 逐SHA与本机实际包相等；源 owner 程序来自该引擎。核完整 reader 的实际调用合同与全量内容读取实现。
2. 原始 UI request、dispatch intent、执行入口、进程与请求/配置 pins，以及唯一 operation hash 下的 owner result 精确绑定。原生 result 与归档 capture exit 均成功/exit0。同步启动器 exit0 必须返回完全相同的原 owner result；异步启动器 exit2 必须是 `TERMINAL_UNKNOWN/REPOSITORY_QUERY_ORIGINAL_OPERATION`，原响应中的 operationDirectory/resultRef 必须精确指向同一 owner，且该 owner 随后实际成功。其他退出码及不明 unknown 均拒绝，不能仅凭 exit2 判断备份成功。
3. 直接调用该实际程序的 `read_declared/read_point/validate_chain/validate_epoch`；FULL 无父且自身开启 generation，I1/I2 父前缀精确等于前序报告的完整 pointPins，捕获父点与日志开始位置精确连续。
4. 直接 `read_current` 核 epoch，不调用可能追加调解事件的 `source_epoch`。各点 sidecar 与 result/point/source/policy/epoch 均绑定，审计前后 epoch 不变。
5. 使用纯 `bind_documents` 重算每请求的 capture/repository/object配置，核父点与原 source 保持；不调用会创建目录的 `for_request`。
6. 原生独立 SMB readback 的完整 `archivedFilePins` 与 manifest、payload tree 完全一致；逐SHA核保留的原始元数据副本。不会再次打开 SQL 压缩包、原始 binlog SQL 或附件 payload。每个元数据文件上限64MiB、总上限256MiB，审计超时120秒，输入身份最后再次核对。
7. 捕获成功与独立 sourceRestoration 的 restored=True/errors=[]；增量使用正式 `incremental_observation_tables` 验证实际事件范围与受影响表的冻结观察，不再假定每次增量都有数据库级 DDL 或全表范围。

## 报告合同与界限

`schemaVersion=AutomaticBackupChainAudit/v1`，`status=PASS`。顶层保留 operationId、sourceConfigRef、pointType、state、actualExitCode、resultPin、pointPin、manifestPin、generationId、parentPointPins、sourceEpoch、epochBindingPin、sourceRestorationPin、sourceRestored。`chain` 是从 FULL 到当前点的完整列表；`package` 记真实程序摘要；`readback` 记完整读取证据与总量；`database` 记实际日志位置、SQL pins 与增量事件范围。

脚本不执行当前源健康探测或下一次增量计划的实时 MySQL 观察。因此保留 `sourceIndependentHealthCheckRequired=true`，实际 UI 终态、来源独立健康与最终 READY 计划由父任务单独验证；`serverDurabilityVerified=false` 沿用原生证明，不扩大结论为断电耐久或恢复已完成。

### 独立源健康与收尾证据

每点 `sourceIndependentHealthCheckRequired=true` 必须由 `verify_automatic_source_restoration.py --kind FULL|I1|I2` 生成的 `automatic-{full,i1,i2}-source-restoration.json` 满足。该工具先要求真实审计 PASS 与 UI terminal SUCCEEDED，报告的 `operationId`、`sourceConfigRef`、安装提交及 `inputPins.submission/audit/terminal` 精确绑定对应证据；`observedAt` 不早于审计点 `finishedAt`，`sourceEpoch` 与审计源周期相等。它从实际安装 owner 读取该请求原 capture pin，在同一物理来源锁下只读检查数据库 UUID/version、event_scheduler=ON、read_only=0、super_read_only=0，Redis 真实 PING、原五服务固定配置/运行态与 MinIO/后端/前端语义健康，同周期 READY、无 worker、无恢复资源预留。不会执行任何恢复/SQL写入/重载。

```powershell
& $auditPython -B -X utf8 'doc/tasks/20261106-spug-prod-incremental-to-two-targets/verify_automatic_source_restoration.py' --kind FULL
& $auditPython -B -X utf8 'doc/tasks/20261106-spug-prod-incremental-to-two-targets/verify_automatic_source_restoration.py' --kind I1
& $auditPython -B -X utf8 'doc/tasks/20261106-spug-prod-incremental-to-two-targets/verify_automatic_source_restoration.py' --kind I2
```

每种报告使用独占创建；已存在直接拒绝，不重跑远程检查或覆盖。`--prepare-only` 只核本机前置证据。FULL 与 I2 `failedOriginals.fullShaVerified=true/verifiedFiles=10044/mode=FULL_SHA256`；I1 明确 `fullShaVerified=false/verifiedFiles=0/mode=NOT_RECHECKED_THIS_OBSERVATION`，仅实时状态检查，不能被称为第三次完整原件检查。旧367脚本和原证明不改。

原 `prepare_automatic_ui_preflight.py --kind FULL|I1|I2 --phase verify --observation <唯一观察名>` 生成的 `automatic-{full,i1,i2}-verify-<观察名>-preflight-evidence.json` 及配对门禁报告继续用于 UI 验证前置和实时下一次计划。该证据也绑定原始 UI request 的操作号与 source，但它本身没有 SQL 全局状态和10044原件检查，不能独立代替上述来源恢复报告。

收尾清单 `TaskAutomaticAcceptanceSelection/v2` 每种 kind 的 `deploymentSelectionPin` 选择明确阶段，`sourceRestorationReportPin` 指向独立来源恢复报告，submit/terminal observation pins指向各次实际浏览器观察（按精确文件 pin 选择，不猜最新文件）。`finalSourcePreflightPin` 另选 I2 之后的最终预检，核 `sourceIdle=true/workerCount=0`、实际下一次增量 `plan.state=READY` 且 `parentChainRef` 为 I2。审计内的原生 `sourceRestorationPin` 证明捕获后的恢复动作完成，不能代替上述独立报告。若任一报告缺失或源忙、健康/计划不符合，收尾必须失败。

任务内测试命令：

```powershell
$env:PYTHONPATH = 'C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/test-dependencies'
& $auditPython -B -X utf8 -m pytest doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_automatic_chain_audit.py -q -p no:cacheprovider --tb=short
```

这些测试使用真实临时文件、已有生产合同与实际已构建包，覆盖 FULL/I1/I2、完整读回、篡改、大小上限、错误父链/周期和请求配置；测试样例不代替现场备份证据。
