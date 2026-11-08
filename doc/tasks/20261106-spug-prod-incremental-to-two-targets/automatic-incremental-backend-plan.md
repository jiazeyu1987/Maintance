# 自动增量源端计划与同源互斥

## Current Status
ready_for_closeout — 源端实现及本机契约验证完成，交由父任务统一封包、Linux 回归及真实用户路径验收。本分工未访问服务器、未提交；不宣称线上功能已交付。

## 目标
提供认证后的自动增量计划查询，以真实成功点的不可变元数据确定 FULL 根及最新增量端点，提交时复核父点，并以持久化 Ledger 拒绝同源未闭合任务的第二个编号。保持既有 SmallAppBackupUiRequest/v1 与历史原件可读。

## 修改范围
- backend/src/main/resources/recovery_control_incremental_plan.py
- backend/src/main/resources/recovery_control_smallapp_native.py
- backend/src/main/resources/recovery_control_smallapp_http.py
- backend/src/main/resources/recovery_control_smallapp.py
- scripts/tests/test_automatic_incremental_plan.py

## 里程碑与预期验证
- [x] 明确计划响应与 epoch 对接合同；持久化原件验证规则形成测试。
- [x] 真实临时元数据及子进程 RED；Linux flock 由 epoch 分工验证。
- [x] 最小实现 GREEN：选链、认证查询、提交最新父点及同源互斥。
- [x] 本机可执行回归与证据交回父任务；Linux 进程证据和真实 MySQL 预检剩余验证明确列出。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。无法证明链或恢复周期时给出 BASELINE_REQUIRED/BLOCKED，不从本机 History、目录时间或操作编号猜。
- 是否从根因和长期维护角度解决：是。选链逻辑归属源端正式控制组件；使用已发布原件与持久化 Ledger。
- 是否存在临时补丁或绕过：否。旧请求格式不变；不跳过内容摘要、源身份、失败历史或未知终态。

## 经验门禁
- 只以同来源、成功退出、完整父链及原始内容摘要为选点依据；恢复保持 UUID，不能据此推断恢复周期未改变。
- 标准/轻量封包需由父任务统一登记新增模块并验证实际入口；本分工不改封包映射。
- 同源互斥必须检查持久记录而非仅内存 active；服务重启后未知状态继续阻塞，已有编号只查询。
- Windows 文本读写显式 UTF-8；BDD -> RED -> GREEN -> REGRESSION；真实元数据文件与进程锁测试不替代真实备份 E2E。

## BDD
- Given 完整成功 F1 -> I1 -> I2 且本地 Spug 历史不存在；When 查询计划；Then READY，父点 I2、全量根 F1、完整链深度 3。
- Given 更新的 FULL 周期或失败/其它来源记录；When 查询计划；Then 只使用当前来源最新已验证链；失败尝试不能成为父点。
- Given 父点字节变化、链前缀缺失、周期/UUID不一致、未知失败或分叉歧义；When 查询计划；Then 明确 BLOCKED，不自动回退旧点。
- Given 计划后发布了新点；When 提交旧父点；Then 在派发前拒绝过期父点。
- Given 同来源原任务未闭合或服务重启后仍未知；When 提交新编号；Then 不派发第二个 worker；原编号请求仍查询原状态。
- Given 不同来源或前任务已真实完成；When 提交；Then 不被无关来源或历史成功阻塞。
- Given HTTP 未认证或不合法 sourceConfigRef；When 请求 /incremental-plan；Then 不调用计划器。

## RED / GREEN / REGRESSION
- RED: Python `-B -m unittest discover -s scripts/tests -p test_automatic_incremental_plan.py -v` -> FAIL，14 项中 3 fail / 10 error：未实现计划接口，原实现接受陈旧父点，并且同源及重启孤儿记录会再次派发。
- GREEN: 同命令 -> PASS，14 项，28.975 秒；真实临时文件、HTTP、真实子进程退出和持久化任务覆盖。
- RED/GREEN: epoch 来源配置绑定、未初始化错误码、sidecar 的事件与 epochId 交叉校验和公共 evidenceDigest/planDigest 合同均先失败再修复。
- GREEN: EpochAdmission -> PASS，8 项，29.078 秒。使用真实不可变事件链文件，不伪造线上恢复或 Linux flock 验证。
- RED: 在线日志保留协议 3 项 -> FAIL，purge/缺段/UUID变化仍返回 READY。
- GREEN: 在线日志保留协议及正常推进稳定摘要 4 项 -> PASS，13.052 秒。
- RED/GREEN: 周期目录与捕获归档存储重叠必须阻止；1 项由未抛异常变为 PASS。
- REGRESSION: Python `-B -m unittest discover -s scripts/tests -p test_automatic_incremental_plan.py -v` -> PASS，29 项，69.897 秒，无跳过。
- REGRESSION: pytest `test_capture_request_binding.py test_restore_archive_catalogue.py test_restore_target_http.py -q -p no:cacheprovider` -> PASS，19 项，1.42 秒。
- BLOCKER（平台边界，已报告父任务）: 同批加入 Linux 原生进程测试时，`test_native_import_process_evidence.py` 13 项按原有标记跳过；`test_native_oom_target.py` 27 fail / 18 error，因 Windows 不存在 `/proc/sys/kernel/random/boot_id` 及测试固定 POSIX argv 路径比较。未改用 mock 成功、未把此批记为通过。父任务需在 Linux 原生环境运行这两文件。
- REGRESSION: `git diff --check` -> PASS；新模块、现有控制文件及测试均显式 UTF-8。
- RED/GREEN: 单次 document 真实 hash 次数从 2 次变 1 次；退休增量内部元数据不再阻止新 FULL 代，但退休 selector/native result/point 摘要损坏仍 BLOCKED。两项先失败后 PASS。
- 独立真实 HTTP 性能回归：24 个已闭合 FULL，24 个真实 no-op 子进程退出原件；pinned_read 829 -> 249，读取 50,788,703 -> 1,214,938 bytes，readback 48 -> 1；请求约 0.891 / 1.125 秒，桥接专用预算 40 秒。`test_automatic_incremental_resilience.py -k 'planning_does_not or http_budget'` -> 2 PASS，52.45 秒（包含 fixture 构建）。
- RED/GREEN: 日常计划接入 `try_reconcile_current`，仅 REPLACING 尝试持锁收口已证明的固定恢复回执；未恢复或重放任何数据。无 Linux 锁/固定回执时仍明确 BLOCKED。
- REGRESSION: 缓存读后原件被修改 -> `INCREMENTAL_PLAN_INPUT_CHANGED`；总预算耗尽 -> `INCREMENTAL_PLAN_TIMEOUT`，均 BLOCKED，2 PASS。
- 最终本机 REGRESSION: `test_automatic_incremental_plan.py` 34/34 PASS，63.148 秒，无跳过；capture binding / restore archive catalogue / restore target HTTP 19/19 PASS，2.22 秒。源码已冻结供父任务最终 Linux 验证。

## 最终接口与集成边界
- 认证 `GET /incremental-plan?sourceConfigRef=...` 返回 `AutomaticIncrementalPlan/v1`；核心字段为 state/reasonCode/parentChainRef/baseFullRef/generationId/chainDepth/pointType/finishedAt/baseFinishedAt/basePointType/parentPointType。
- `evidenceDigest` 是私密原件集合规范 JSON 的 SHA256；`planDigest` 是全部公共响应字段（排除 planDigest 自身）的规范 JSON SHA256。实时向前推进的位置和日志大小不进入摘要。
- 服务配置可选 `sourceEpochPolicies[sourceConfigRef]`，完整 `SourceBackupEpochPolicy/v1`。未登记旧源保持旧合同；启用后缺 sidecar 的历史点明确要求新 FULL。
- sidecar 位于 registry 的 `point-epochs/<reference>.json`，绑定原 pointPin、成功 resultPin、policySha256、epochId、epochEventPin；不改归档内容。
- Native 的运行前复核排除当前 operationId；其他同源未闭合 durable intent 阻止第二编号，已有编号只查询。
- 调度扫描的成功快判必须同时绑定 request/intent/selection/completion、native-intent/native-process/native-original-exit，同 pid、实际 exit=0、timedOut=false、SUCCEEDED。缺少完整闭合证明继续既有完整 reconcile；原编号详细 GET 不改变，不信任孤立 UI 状态。
- 单次计划缓存完整 Pin 的已验证元数据，结束复核文件身份；全计划 30 秒预算，在线只读探测最多 10 秒且受剩余预算约束。超时明确 BLOCKED。旧代 FULL 根与 selector/result/point 身份仍验证；完整 readback/父链仅展开当前代，避免历史数量导致不断重复读取。
- 正常计划只读；REPLACING 的恢复已具备固定终态回执时，正式 `try_reconcile_current` 可在同源物理锁下补记该终态，不重放恢复、不启动服务。这个收口是有原件依据的状态提交，不能解释成恢复成功兜底。
- 本机观察协议用真实临时 JSON 原件与实际 hash 读回验证。Live Docker/MySQL 方法未在本分工访问服务器运行，不能据此宣称真实 MySQL 连接或生产备份通过；由父任务原授权范围内验收。

## 本机来源登记盘点扩展（只读）
- 目标：核对当前 18080 容器 `f615a60c76f4` 的 public simple settings，以及 `C:/Spug/runtime/private/smallapp-bridge.private.json` 引用的来源连接/版本登记，避免升级 57SAFE 后其它公开增量入口仍访问旧 API。
- 范围：本机配置元数据和精确容器的只读公开配置；不输出 headers、password、token、完整环境变量，不访问远端，不修改 runtime、产品或测试；18081 的另一容器不属于本任务。
- 验证：形成公开来源 -> 控制服务 -> 配置引用 -> 物理来源分组；只以登记证据判断共享或弃用，不把旧目录名当作弃用证明；列出 epoch 与覆盖目标成对登记的已知事实和缺口。
- 状态：completed（仅此只读清单）；结论见 `automatic-incremental-source-inventory.md`。当前 10 可选源中仅 57SAFE 控制活动；另 9 项为升级前已无监听的历史登记，且 SMALL58 物理容器已退出、MAIN59 旧 MinIO 路径与实际挂载漂移。本轮最小闭包为 57SAFE 源 + 三 MAIN 覆盖，同源模式未来共用 epoch；未启停旧源。源码和测试保持父任务最终 Linux 验证所需冻结状态。
- 扩展授权：父任务确认用户既有三服只读授权继续适用，允许通过当前任务 `common.remote` 核 10 个可选来源的实际服务、配置 pin、物理来源身份及锁；仍不安装、不重载、不执行备份恢复，不触碰审查服原任务 372。
- 经验门禁：已读迁移入口 `C:/SpugHandoff/release/repository/docs/server-access.md`、`powershell-memory.md`、`release-backup-restore.md`；只用三台明确主机与当前可信 SSH/known-hosts 引用；Python UTF-8 stdin、有界子进程、退出码失败即停止；仅输出配置路径与身份摘要，不输出凭据或 Env；数据与挂载无写入；未能唯一核实的源不得按 IP 或模式名合并 epoch。

## 在线日志保留预检补充 BDD
- Given 已验证父点但 MySQL 已清理父 binlog、缺少中间日志或位置/GTID 倒退；When 重新规划；Then BASELINE_REQUIRED，按钮明确新 FULL。
- Given 固定容器身份不符、权限/连接/格式异常；When 规划；Then BLOCKED，不能转换为全量成功路径。
- Given 正常业务推进当前位置或新增 binlog，父链/epoch/配置仍相同；When 再规划；Then READY 且 planDigest 稳定。
- 使用既有在线只读 observe_position 和正式 binlog_ranges；仅固定完整 MySQL 容器 ID、本机 Docker socket 和配置 Docker 路径，凭据仅通过既有 stdin 路径。未执行真实服务器预检。
- 物理源锁由 minimal_capture_worker.capture 持有至 capture_locked 返回；归档发布间隙若发生恢复，sourceEpoch 前后严格对比拒绝 sidecar 与 point selector 发布。

## 候选包真实历史绑定修复（2026-11-08）
- 目标：诊断候选 3019c2e 在当前正式源历史返回 `INCREMENTAL_CAPTURE_BINDING_INVALID` 的原因；按正式捕获/仓库双层合同校验，合法无 epoch 旧点应进入 `BASELINE_REQUIRED`。
- 范围：只改本机 planner 与对应测试；仅以可信 `common.remote` 读取正式源精确 metadata pins，不修改远端候选包、不切服务，不访问审查服任务。
- 设计约束检查：不引入 fallback/吞异常；从真实生产者合同修正错误等式；不加临时绕过；非法捕获/仓库/请求关联仍必须 BLOCKED。
- 根因证据：7 个真实点的 backupId、generationId、pointType、UUID、recoveryPoint 均一致，全部仅 sourceRestored 检查失败。正式捕获器在源服务恢复前封存不可变 capture-content-point（false），随后以 captureResultPin → sourceRestorationPin 记录恢复成功；并非原生 ID 不同。
- BDD: Given 冻结内容点 sourceRestored=false 且独立捕获成功结果/恢复回执严格绑定同一 operation、内容 bytes/SHA、sourceIdentity、recoveryPoint、固定根路径与时间顺序，When 规划旧无 epoch 点，Then BASELINE_REQUIRED；有合法当前 epoch 的完整链可正常 READY。
- BDD: Given 冻结内容点 false 但捕获结果缺失、跨操作、失败、exit非0、内容摘要不符、回执跨根/跨源、restored=false、errors非空或原回执被修改，When 规划，Then BLOCKED，不仅删除原等式放行。
- RED: pytest `test_automatic_incremental_plan.py -k frozen_content` -> 4 FAIL，正常真实布局误报 CAPTURE_BINDING；负向尚不能进入正式恢复回执验证。
- GREEN: 同一 `-k frozen_content` 命令 -> 4 PASS，21.17 秒；随后补充缺少捕获结果、缺少恢复 pin 与恢复时间晚于成功结果的负向覆盖。
- REGRESSION: planner 与 capture-request-binding / restore-archive-catalogue / restore-target-http 共 58 项，57 项首轮 PASS；1 项新增负向 fixture 错用不可变 persist 重写现有 selector 触发 FileExistsError，改为该临时测试原件的显式字节重绑定后独立重跑 PASS（1.48 秒）。产品实现未因此修改。合计 planner 39 项、邻近合同 19 项均已执行通过。
- REGRESSION: 24 个真实已闭合子进程的两项 HTTP 性能测试 -> 2 PASS，91.92 秒；249 次 pinned_read、1,215,322 bytes、readback 1 次，实际 HTTP 0.734 / 0.844 秒，bridge 预算 40 秒。`git diff --check` PASS。
- 真实只读验证：同一 .57 控制配置与旧 7 点元数据下，原 staged planner 返回 BLOCKED/INCREMENTAL_CAPTURE_BINDING_INVALID（9.579 秒）；单独 Python 进程仅在内存加载当前修复后返回 BASELINE_REQUIRED/BACKUP_POINT_EPOCH_REQUIRED（12.764 秒）。候选配置/原 planner SHA、活动源/目标 PID、epoch 前后完全保持。修复 SHA 为 `f25ba6f0ae97ff34580013a688e784500bf398522d512ed65f3d56bb0a0944db`。不据此宣称 staged 引擎已修改或部署完成。
- 私密证据：`automatic-capture-binding-diagnosis.private.json`、`automatic-capture-restoration-diagnosis.private.json`、`automatic-capture-restoration-plan-validation.private.json`，均位于本任务 PRIVATE；不提交原 metadata、环境或凭据。
- 里程碑：真实字段对照、RED、最小修复、GREEN、邻近性能回归及实际原件只读验证均完成；本分工状态 ready_for_closeout，源码冻结，后续独立提交/新 worktree 封包/正式部署由父任务完成。新增明确失败码 `INCREMENTAL_SOURCE_RESTORATION_INVALID`；没有给旧点补写 epoch 或绕过内容身份绑定。


## FULL373之后计划超时：只读诊断与正式修复
- 当前状态：in_progress。新FULL373实际SUCCEEDED，但21:06:51原预检计划30秒后BLOCKED/INCREMENTAL_PLAN_TIMEOUT，原文件完整保留。只读定位当前0d44578真实完成原件、计划各阶段与pin/path开销，不写服务器、不安装/备份/恢复。
- 设计约束检查：不延长总预算、不跳过必要完整性、不吞异常；以实际生产者合同和真实耗时解决根因。仅在确定根因后写最小产品改动，BDD→RED→GREEN→邻近回归。
- BDD诊断：Given真实成功FULL和当前epoch，When读取原闭合合同及每阶段开销，Then明确是调度闭合证明、文件SHA、路径身份或在线源探测耗时，不能把sourceIdle/health通过当计划READY。
- 经验门禁：原超时及诊断原件不可覆盖；读取配置/原件完整内容只存PRIVATE、公开仅pins/字段类型/时间；可信SSH限定57、Python UTF-8与有界timeout。任何可能追加query的Ledger.reconcile不调用，先只读判闭合证明；不得改正式引擎或扩大预算。

- 根因已证实：15个真实来源任务immutable completion全为RUNNING/REPOSITORY_QUERY_ORIGINAL_OPERATION、CLI退出2；真实owner独立工作进程最终7成功/8失败。现成功快判只接受同步completion SUCCEEDED，因此真实部署从未使用；每次准入重新走完整reconcile并追加query，旧FULL每点originalResultPins约6.25MB，且递归重核data/logRefs。
- BDD: Given真实异步launcher退出2、固定等待回执和独立worker原生终态，When日常计划判断同源空闲，Then严格核原request/intent/selection/completion/launcher进程与精确owner request/start/result、worker停止；只返回终态闭合，不重hash历史大readback/logs，不修改immutable completion或旧query。
- BDD: Given等待回执跨operation/root/result、pid/config/program/request不一致、owner还运行/终态缺失/unknown，When准入，Then不能快判空闲。异步边界仅来源FULL/INCREMENTAL，RESTORE及原编号详细GET不改变，当前代链/旧根摘要照常完整验证。
- TDD计划：真实临时原件+真实launcher退出2+实际独立worker/子进程，用协议夹具测试，不声称执行线上备份；有界大readback文件计数证明计划不重复读取，负向逐项绑定失败；Linux实际/proc验证，不以Windows mock通过冒充。
- BDD补充：Given后续归档失败但最后捕获child实际退出0，或捕获前失败/明确取消时owner退出码未观察，When核调度闭合，Then遵循生产者的原实际退出语义；必须存在非空规范failureCode，存在child终态时核固定路径、原pin、operation、pid、processTerminated与实际退出一致，取消须绑定原SIGTERM intent/observation。缺失败原因、错退出、错child/缺pin或仍运行一律拒绝，不能把FAILED字符串当闭合证明，也不能强制exit1误拒合法历史。
- RED：真实Linux、只在测试进程内加载b5c8817旧Ledger/Native，同一15项真实launcher/worker协议测试精确失败为readback=15/reconcile=15；`linux-async-closure-history-red.json`。FAILED证明新增9负向先7FAIL/2PASS，失败为缺failureCode、退出码与真实child不符、缺pin/错operation/未终止/错pid未被拒绝；`linux-async-closure-failed-proof-red.json`。
- GREEN：最终Linux28PASS/0SKIP，254.26秒，前后输入SHA一致、只读仓库挂载、容器已移除；`linux-async-closure-green-3.json`。真实进程覆盖同源重建、RESTORE排除、当前worker仍运行、最后child退出0而owner失败、捕获前未观察退出及真实SIGTERM取消None合同。此前14项GREEN保留，不冒称旧14项是最终28项。
- REGRESSION：相邻planner39/resilience9/capture-binding5/catalogue13/target-http1，共67PASS/0SKIP；原容器自然退出0。外层本机driver240秒先超时，容器372秒后完成，收取原日志后仅移除该容器，没有重跑或伪造起始SHA；`linux-async-closure-regression-plan-recovered.json`明确inputFilesUnchanged=null，产品30秒预算未变。其后新增失败证明只在新异步分支，最终28项及实际15历史覆盖该分支。
- 实际只读验证：新代码仅加载到独立Python进程内，audit hook禁止文件/目录写入并禁止Native.reconcile。`automatic-async-plan-fourth.json`：7.924秒READY，parent/base均为原FULL373，15项原任务全闭合，仅当前代readback一次；实时MySQL元数据预检1.333秒。没有安装/重载/备份/恢复，没有修改原FULL/epoch/历史。旧超时和所有失败诊断保留。
- 正式实现只改既有Ledger、Native两模块；planner、公共API、30秒预算、STANDARD130成员及归档合同不变。新增异步协议测试与既有release-agent-checklist/experience-index前置门禁；原编号详细GET仍验证全部original pins。安装仅需source57新控制代次，三MAIN目标可保留原代次。
- 当前里程碑状态：ready_for_closeout（本分工实现/验证完成、5个正式交付文件冻结）；由父任务单独提交、新worktree封包、source-only实际安装及UI连续增量验收后收口，当前不宣称线上修复已经启用。
