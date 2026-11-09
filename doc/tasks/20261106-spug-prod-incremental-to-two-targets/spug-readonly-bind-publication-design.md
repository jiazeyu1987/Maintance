# Spug 只读 bind 配置发布与 r6 明确续办设计

## Goal and current status

design_review。只读审查和本设计已完成，尚未修改实现、编写或运行新测试、调用 Docker/服务器、发布配置或生成新的成功原件。本设计从父任务 `spug-readonly-bind-publication-refactor-plan.md` 派生，等待父任务明确批准下列实现及共享 reader 解冻范围后才进入 RED。

目标是正式完成同一个 `45dd7dc/r6` 的配置发布：保留原 v2 失败和已成功的三服写入，通过宿主更新只读 bind 中的精确配置，通过原容器更新 writable volume 中的精确配置，保持原挂载只读和完整验证合同。配置发布不是备份、恢复或 UI 验收成功。

## 已核事实与根因

本轮仅读取明确文件，并只投影私密报告的 schema、阶段、数量和 pins，未输出配置正文或凭据。

| 原件 | bytes | SHA256 |
| --- | ---: | --- |
| `main-program-spug-installation-45dd7dc-r6.private.json` | 3308 | `cca54c2dec46b26c187df5e7c463d75f7b3cc08e1a9f24ba14fda4929a7c7b77` |
| `main-program-spug-installation-45dd7dc-r6.attempt.private.json` | 73005 | `50a42921f08ef427c6983391fd90e55bb714267dcc5c12b5a222415b2cfb9360` |
| `spug-publication-failure-state-r2.json` | 4155 | `e3367e3a5fc302e9c729ac50e21abeb406572faa87cbface439f5e64e48427f4` |
| r2 的 `spug-publication-failure-inspection-r2.private.json` | 8908 | `0bbc22b46574b1d818bb983f1c964dba630023b747285da8e302178f45ee5d16` |
| `main-program-spug-resource-activation-c7728ad-delta-838ac378a3e9.json` | 2751 | `b0ea2939ef9c479b5fc9a246054552cf6b520b1a95cb43fef51b4260e18fb026` |

原 rich 为 `MainProgramSpugPublicationFailure/v2`，阶段严格为原 schedule 的前八项：四个 preflight PASS、三个 host-publish PASS、spug-publish FAILED。三服 completedWrites 分别为 6/3/3；失败阶段 completedWrites 为 0。这一计数本身不足以证明未写入，所以还必须核父任务已完成的 r2 真实状态原件：七个目标按原 expected pin 均未改变，原 Spug audit 目录存在且为空，实际查询 exit0，受保护实例保持。不能只凭错误文字或 completedWrites=0 放行。

父任务实际 inspect 已明确 `/run/intruoyi-spug` 是 `C:/Spug/runtime/private` 的只读 bind，`/opt/intruoyi-spug` 是只读产品 bind，`/var/lib/intruoyi-spug` 是 writable named volume。r2 的顶层私密报告没有完整 mount inspect 字段；正式输入必须补上已存在的实际 inspect 原件 pin 或父任务后续生成的精确 mount 原件，不得把本段文字当作机器可验证 mount 证据。

原 `SPUG_BODY` 在容器内统一调用 `replace_once`，错误地假定全部配置路径可写。`SETTINGS` 的 simple 和 entry 均在 `/var/lib`；bridge 和四个新增连接在 `/run`。`_prepare_publication_graph` 的实际 writes 顺序为四个新增连接、simple、entry、最后 bridge。新实现必须保存这一顺序；不能把五个 bind 文件先整组写完而提前切换 bridge。

## Milestones and expected verification

1. **DONE — 本机只读设计**：确认七个写入的两类存储、原失败状态和最小 reader 接口。
2. **PENDING — BDD/RED**：新增专属真实文件/进程合同测试，先证明当前工具不能执行 ro-bind 发布，也不能正确消费部分完成的原失败。
3. **PENDING — GREEN**：独立 continuation 模块完成精确映射、全量 custody、原顺序逐文件安装、严格一次续办和原程序验证；共享 reader 只作下述有限提取/分派。
4. **PENDING — REGRESSION**：原 v1/v2 publisher、reader、selection 和 closeout 合同全部保持；冻结源码和真实日志 pins，由父独立审查。
5. **PENDING — 真实发布**：父任务提供最终明确输入、先记录经验门禁，再执行唯一 continuation；本机 fixture PASS 不替代此阶段。
6. **PENDING — 独立 UI/恢复/收尾**：仍由父任务原验收计划处理。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。两种存储方式是由精确 mount 和原计划目标决定的显式分派；未知方式、pin 漂移或未知写入状态均停止，不回退到可写目录，不自动重试。
- 是否从根因和长期维护角度解决：是。保留容器只读保护，将配置部署位置与运行时读取位置明确区分；续办是可审计的版本化合同，不复用一个已经失败的发布尝试。
- 是否存在临时补丁或绕过：否。不修改产品资源、不更换控制代次、不改旧原件、不手工复制、不扩大容器权限，不把七个历史 PASS 拼成新的完整成功。

## 最小实现边界与需解冻位置

建议新增 `main_program_spug_publication_continuation.py`，包含 v3 输入/失败继承校验、只读准备、精确传输、逐文件发布、v3 证据校验和 CLI。新增 `test_main_program_spug_publication_continuation.py` 与专属 TDD 日志。单模块保持任务专用，不建立通用安装框架。

必须先由父明确批准的现有文件改动只有：

1. `main_program_spug_publication.py`：将 `validate_publication_v2` 内已有 verify 阶段深校验提取为一个共享纯函数；原 v2 调用该函数，所有原 exact-fields/schema、12 阶段、顺序、绑定、矩阵、输入复核均保持。新 v3 reader 调用同一函数，避免复制后漂移或只校验布尔值。`HOST_BODY`、`SPUG_BODY`、`ActualTransport` 和旧发布流程字节不改。
2. `main_program_installation_selection.py`：显式识别 `TaskMainProgramInstallations/v3`，局部 import 新模块的严格 reader，输出原公共 selection 结构。v1/v2 分支不接受 v3 证据，也不改变旧合同。
3. `observe_closeout_hosts.py`：只增加显式 v3 schema 分派到上述 selection；不修改实际远端采集程序、旧 I2 绑定或历史判断。

以下冻结输入不改：`main_program_spug_publication_v2.py`、资源 activation/lifecycle、控制 generation/planner/activation/staging、产品 `ops/`、构建/测试原件、原失败/attempt/八阶段及既有选择。若提取后原测试需要修改断言，必须停止报告，不能自行放宽原测试。

初始源码 SHA：publication `ec4ca9f834332ef3b235c731f401b1c6435a49f08d2117be1acce1c35616aaae`；v2 publisher `0915b324db982f1213289a35a8148833f69c141fa080d91671fee00696eb37fa`；selection `f663ab53ae810b115fb418062e162d0a592349d7081fb59adcf191d5e4488966`；closeout collector `61d320d245c000c19c692d57a9e5cf15c257b38f411b36c72084d1889825f7a4`。

## v3 输入、输出和 reader 合同

输入建议 exact fields：

```text
MainProgramSpugPublicationInputs/v3
  sourceCommit, revisionId, controlGenerationPin, spugResourceBuildPin
  originalPublicationInputsPin, originalAttemptPin, originalFailurePin
  originalSourceCustodyPin
  failureStatePin, mountObservationPin, resourceActivationPin
  continuationId, outputFile
```

- sourceCommit 和 revisionId 必须逐字等于原 v2 输入、原失败和实际 control generation；本次仍为原 45 完整 SHA 与 `r6`。不得输入 r7。资源 build 与已安装资源 PASS 的 11 个实际文件 pins 绑定。
- `failureStatePin` 明确引用上述 r2 公共原件，并验证它所 pin 的私密证据、原查询程序/stdout/stderr、七项目标和原空 audit 状态。它是历史状态观察，正式 apply 仍重新读取当前状态。
- `mountObservationPin` 是明确容器、两个固定 loopback 端口、受保护实例和三项 mount 身份的真实原件。prepare 不调用 Docker；缺该原件就拒绝。其具体封装由父实际 inspect 原件形状确定，不凭推测填 `PASS`。
- `originalAttemptPin` 必须是同一个原 v2 attempt。原阶段引用由 FAILED 原件取得，严格验证只有原八项、顺序相同、全部原 bindings 相同、前七项 PASS、最后 FAILED 且 actual state 未写入。原 request/program/result 全部逐 pin 继承；不依赖目录扫描或“最新”。
- `continuationId` 是与控制 revision 不同的明确发布尝试编号，例如 `c1`；输出名为 `main-program-spug-installation-45dd7dc-r6-continuation-c1.json`。原 r6 名字绝不复用。
- 以 `originalFailurePin.sha256` 建立固定排他 claim，防止换 continuationId 绕过已有或结果未知尝试。原运行器已退出及本次互斥需有实际证明；相同原失败不能并发或自动第二次写入。
- attempt、每次派发请求、程序、stdout/stderr、逐文件状态、终态 rich/core 全部独占新路径。新 attempt schema 为 `MainProgramSpugPublicationAttempt/v3`；rich 为 `MainProgramSpugPublicationEvidence/v3` 或 `MainProgramSpugPublicationFailure/v3`，均显式包含原失败/attempt pins、continuation 输入 pin、原八阶段 pins 和新阶段 pins。
- 公共核心继续由原纯 `project_core` 产生 `MainProgramSpugInstallation/v1` 的相同最终状态字段；新文件名及 typed v3 selection 明确区分来源。新 selection 为 `TaskMainProgramInstallations/v3`，exact fields 是 `schemaVersion, sourceCommit, controlGenerationPin, spugInstallationPin, continuationInputsPin`。v3 reader 必须验证整个新 rich 和原失败继承链；仅公共核心或控制索引不能通过。
- 新 reader 不制造十二个全 PASS 的虚构旧 schedule。它分别核原七项已成功行为、原第八项失败事实，以及新配置发布和四项真实最终 verify，确保原十二个业务职责均被真实证据覆盖。

建议 API：`prepare_continuation(task, private, inputs_file)` 默认纯本机；`run_request(..., apply=False, transport=None)` 只有显式 apply 可派发；`validate_publication_v3(records, private, selected)` 纯读取原件。reader 内局部 import 避免循环，历史读取不依赖发布 worktree 仍存在；准备/执行时仍核实际安装、源文件和执行输入闭包。

## 精确路径与安装顺序

1. **当前只读 preflight**：核容器 ID/名字/18080、受保护 18081、entry PID、产品 11 pins、任务快照、历史连接、原 FAILED/audit、全部七个 expected 状态。实际 inspect 的 mount Source/Destination/Type/RW/volume Name、container snapshot 必须与明确原件一致。仅 `/run/intruoyi-spug` 的五个精确原计划目标可映射到唯一宿主根 `C:/Spug/runtime/private`；仅 simple 和 entry 的两个原 `/var/lib/intruoyi-spug` 目标可走 named-volume 容器路径。禁止 `/opt` 写入、未知子 mount、路径逃逸、Windows 大小写/路径别名冲突、symlink/reparse/hardlink、未知文件和新增 broad allowlist。
2. **全部 custody**：在独立 continuation audit 中先保存三个已存在配置的原始 bytes、七项实际状态/缺失证明和对应索引，并逐字节读回；旧 `/run` bridge 必须同时匹配容器和宿主的原 pin，volume 两设置从原容器保存。容器可写 audit 中保留 `before-<原 index>.private.json`，使原 SPUG verify 无需修改；宿主 PRIVATE 保留对应原件镜像/pins，凭据不进入公共输出或 Git。全部七项 custody 验证完成前，不能改变任何运行目标。原失败的空 audit 独立保留，不补写或移用。
3. **原顺序逐项发布**：沿用原 spec.writes 顺序和 canonical bytes，不重新生成业务配置。每项根据精确已核存储类型分派：先四个宿主新连接，然后容器 simple、entry，最后宿主 bridge。每个目标写前复核全部输入与本项 old pin/缺失状态、custody、路径身份和实例/mount；临时文件同目录、独占、flush/fsync；已有文件用明确原子替换，新文件用平台明确支持的原子 no-clobber 移入，不能覆盖突然出现的目标。unsupported 平台拒绝，不退回非原子写法。
4. **逐项状态**：写前持久化 `DISPATCHED_OUTCOME_UNKNOWN`；只有实际安装及原容器读回成功才能记 `APPLIED`。未触发写入为 `NOT_STARTED`。发生 replace 后 receipt/readback 错误必须如实保留原始异常、已写文件状态和未知项，不能因 completedWrites 列表未追加而判定零写入。只允许原请求身份下只读诊断；无自动重试、回滚、下一文件写入或换 ID 重派。
5. **最终验证**：按旧 v2 顺序执行三个原 `HOST_PROGRAM` verify（原 r6 host audit 不变），然后原 `SPUG_PROGRAM` verify（本次新 audit）。程序原正文和 guards 保持，wrapper 继续增加实际 controllers/productPins。原容器必须实际读取全部七项新配置，原 native 三来源 × 三目标准入、33 apps、3 tasks、历史指纹/路径、旧 tasks、产品、容器/业务/fstab/mount 保全全部证明。查询可能产生既有审计写入，不能把它表述为无服务器写入；不派发备份或恢复。

Windows 宿主写入必须在真实本机临时目录验证：同目录独占 staged 文件，`flush` 后 `os.fsync` 成功，再用 Windows 明确的原子替换/不覆盖移入语义完成最后一步。已有目标必须在替换前最后核原 pin；新目标必须由最终操作本身拒绝覆盖，不能仅依赖提前 `exists()`。检查父目录和每层目录的 reparse/身份，核新旧文件 nlink=1、原目标和 staged 的同一卷；任一别名或身份变化拒绝。原 helpers 的 `sync_parent` 在 Windows 是空操作，不能因此声称目录元数据已经 fsync 或抗断电已经验证；回执分别记录真实 `fileFsyncCompleted`、`atomicMoveCompleted`、容器 readback 与 `powerLossDurabilityVerified=false`。文件 fsync/原子调用失败必须原样失败，不吞异常或降级。

每项容器命令保存原生 returncode、stdout/stderr pins、进程/请求身份和其结果，不仅相信返回 JSON 的 PASS。宿主写入也保存原生调用成功/异常及文件前后身份；如以独立子进程执行，必须记录它的真实退出码，不能为进程内调用捏造 exit0。容器读回必须另有实际命令退出与目标 pin。dispatch 后超时或进程身份/终态不可知时保留 UNKNOWN/claim，不以 Docker CLI 退出代替 worker 已退出；不得自动再次执行本项、后续项或下一 continuation。

新顶层阶段可保持最小固定序列：`spug-continuation-preflight`、`spug-custody`、`spug-configuration-publish`（包含原顺序七个独立 receipt）、`host-verify-57/58/59`、`spug-verify`。每个阶段有独立 request/program/result pin；本机 file transition 也写明真实 executor 类型，不能伪装成 container 的 publish PASS。

任一输入漂移、旧 PID 未知、实际原配置不再等于原 expected、旧 audit 非空、已有 continuation claim、局部替换失败或整体终态丢失均 fail fast。以后如需失败续办或仅本地 finalization，必须根据保存状态另行明确设计和审批；当前不交付通用 resume，也不盲重跑任何 publish。

## BDD 与严格 TDD

本机 fixture 只证明合同和真实文件/子进程行为，不证明真实容器挂载或三服已安装；真实容器事实来自父任务固定原件，之后真实 apply 独立执行。

| 场景 | Given / When / Then |
| --- | --- |
| 两类存储 | Given 原七项计划及真实 ro-bind/writable-volume 证据，When prepare/分派，Then 五个精确 bind 目标走宿主、两个 volume 目标只走容器，原顺序严格保留；prepare 不调用传输。 |
| 原根因 RED | Given 原容器只读写失败及完整实际七项未改原件，When 旧发布合同重跑，Then 拒绝复用旧 attempt；新合同实现前仍失败，不能把 fixture 改为 writable 就称修复。 |
| mount 拒绝 | Given RW 被改 true、Source/Name/Type 漂移、子 mount 遮盖或路径逃逸/别名，When 分派，Then 首次运行目标写入前拒绝。 |
| 保全屏障 | Given 多个旧文件和新文件缺失，When 任一 custody 原件/镜像/读回失败，Then 全部实际运行文件 bytes 和缺失状态保持。 |
| 新文件抢占 | Given 已通过 preflight 的新连接名随后出现，When 原子发布，Then 拒绝覆盖并保留两个原件，后续文件不写。 |
| 部分替换 | Given 第一或中间项真实 os.replace/rename 成功，When receipt 写失败或原容器读回失败，Then 实际磁盘新 bytes 可见、失败状态准确保存、没有第二次写入或自动回滚。 |
| 原失败继承 | Given 真实八阶段包含七 PASS、一 FAILED，When 准备续办，Then 原 bytes/pins 不变，三次旧 host-publish 不被派发；少一阶段、顺序变化、UNKNOWN/非零写入/原件漂移均拒绝。 |
| 一次尝试 | Given 同一个 originalFailurePin 已有 claim 或未知派发，When 换 continuationId 或再次 apply，Then 拒绝；不能用新随机编号绕过。 |
| 同代绑定 | Given 控制代次 45/r6，When 输入 r7、其它 generation/build/resource/entry PID，Then 拒绝；不从 latest 补齐。 |
| 真实读回 | Given 7 个目标已写，When 宿主 bytes 正确但原容器仍读旧值，Then 失败；不能用宿主 readback 冒充产品 readback。 |
| 完整深校验 | Given bool flags 全 true 但 native/source/target 矩阵、33 apps/3 tasks、历史指纹或旧 audit 任一缺口，When v3 reader，Then 拒绝，不生成/消费成功 core。 |
| 旧版本回归 | Given 旧 v1/v2 成功和失败 fixture，When 原 reader/CLI，Then 所有原结果、错误码和严格字段不变；旧 v2 不接受新 v3 partial evidence。 |

测试实施顺序：先添加测试并保存 RED 原始退出/日志/源码 pins；再最小实现；最后运行新增测试及原 v1/v2 publisher、publication reader、selection、closeout 的实际受影响模块。原测试断言不弱化，无 skip、mock success 或假现场 PASS。真实磁盘测试覆盖写前保全、实际局部替换和进程结果未知；传输记录 fixture 仅检查禁止/允许的调用顺序，不代替真实字节行为。

## 经验门禁

- Trigger：同一发布已有三服配置写入成功，但 Spug 的只读 bind 写入失败，需要明确失败续办。
- Preflight check：原 inputs/attempt/八阶段/FAILED 与实际 r2 原件 pins、精确 mount 原件、同代控制/资源、七项目标与旧空 audit、固定容器/端口/entry/受保护实例、原运行器终态、全部 custody 与当前输入闭包。
- Blocker：缺 mount 原件或原运行器退出证明；原 expected/current 不同；路径/存储歧义；已存在 claim；已知或未知局部写入；缺最终三服/Spug 深校验。
- Verification：真实本机 RED→GREEN→REGRESSION、源码前后 SHA、原失败保持 SHA、父独立验证与正式唯一 continuation 原件、之后单独 UI/恢复验收。
- Forbidden action：不改 ro、容器权限、产品或控制代次；不重跑三服 publish；不覆盖旧证据；不自动重试/回滚；不凭 completedWrites=0 认定没写；不把本机测试或目录空状态当完整发布成功。
- Evidence：父计划、本设计、本文固定原件、后续专属 TDD 日志/实际命令/原始 stdout stderr/退出码/pins。真实写入前必须由父在 execution-log 记录本轮经验门禁 GREEN。

## 本阶段交付限制

当前只能交付设计。真实 mount 原件的路径/pin 和旧运行器终态的机器可验证封装仍由父补齐；本设计没有捏造这些字段，也没有重新查询现场。上述三个 reader 的最小解冻未获明确实施批准前，继续保持源文件不变。

## 父批准后的明确补充

父任务随后明确批准本方案实现和三个 reader 最小解冻，仍禁止本代理真实发布。实际 mount/runner 原件已由父生成 `spug-continuation-mount-observation-r2.json`（7961 bytes，`65a68d645016cc27088c4befbf08150fef943aa10ec080248bac3a66ecc16bbc`）；正式 c1 输入 `main-program-spug-publication-inputs-45dd7dc-r6-continuation-c1.json` 为 1941 bytes、`5db6e9c043b3f7c043fa6b5cdb7d70a43ca7f7feea7c13c334d4f8fbbf36d2ec`。它们只解除本机准备缺件，不表示已发布。

父同时批准唯一 `originalSourceCustodyPin` 扩展，严格指向 `MainProgramSpugPublicationSourceCustody/v1`：exact fields 为 schemaVersion/originalAttemptPin/entries；每行 exact originalPin/preservedPin。仅允许旧 attempt 实际引用且本轮改变的 publication/selection/collector reader 源文件映射，原字节必须等于旧 pin，不修改旧 attempt；其余旧输入仍按原路径全文复核，旧 v2 publisher 不允许映射。本轮实际旧 attempt 共 286 pins，只有 publication 和 selection 需要映射，未包含本轮待替换的运行配置。父已独占保存两份旧源码并实际复核其余 284 项，正式 custody 为 `main-program-spug-original-source-custody-45r6-r1.json`（1441 bytes，`4a783fb0448cd8324e4e6a5b51bd07345e505d1c65ded744efbac80f2c3d80b6`）。新执行源码独立固定。

写前 guard 使用 `container_program(prepared, 'guard-before-custody')`：只有只读检查，要求 entry 三元身份、原空 audit、七项旧状态、新 audit 不存在。每个宿主 bind 写入前另外执行 `guard`，并重新核当时已经完成/尚未开始的七项状态。每个 native request 的精确容器/SSH目标、实际退出、stdin 程序和 stdout 都由 v3 reader 逐项绑定；七个 readback 和两个 volume write 不能用 inspect 或布尔状态代替。
