# Spug 运行依赖补齐与 c1 只验收设计

## Current Status

design_for_review。仅本机只读调查与本文档；未修改已冻结源码、旧构建/安装/c1 原件，未调用 Docker、服务器、浏览器或运行发布。父任务事前计划为 `spug-runtime-dependency-completion-plan.md`。本设计须父审后才进入 BDD → RED → GREEN → REGRESSION。

目标保持原控制代次 45dd7dc / r6、Spug 产品提交 `c7728adcecf94c199c0954330b29184f56b9c053`。旧 11 文件资源安装和 c1 七配置写入均为已发生的事实；补齐真实运行依赖后，用独立只验收原件完成发布结论，不追改两次失败。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。发现未知本地依赖、实际字节漂移、未闭合调用或缺少旧写入证明即拒绝。
- 是否从根因和长期维护角度解决：是。清单必须覆盖实际入口依赖，而非只列最近 Git 改动或只验证清单内部自洽；构建、安装与最终验收共用同一纯依赖合同。
- 是否存在临时补丁或绕过：否。仅以已提交 c772 字节正式补充安装一个文件；原运行校验、失败、原件与 claim 保留。没有手工覆盖或放宽配置解析。

## 经验门禁

- Trigger：实际入口延迟导入依赖未进入部署清单，配置已写入而最后解析失败。
- Preflight check：旧失败与原生 stdout/exit、七 APPLIED/三 HOST PASS 完整绑定；同提交实际入口图、旧 11 文件、额外三个文件、配置和 entry/实例真实身份；补充只认明确的原字节和候选字节。
- Blocker：依赖闭包不能解释、除 simple 外实际差异、源提交/工作树不闭合、配置或历史指纹变化、旧 native 未知或当前执行者仍活动、需要重复写配置。
- Verification：真实旧 simple + 已发布配置先复现解析失败；同 c772 补齐后真实函数通过；删依赖/改关系必拒绝；真实磁盘保全/替换失败、最终验证 dispatch 白名单及原生原件深绑定；父真实安装、原容器与 UI 独立验收。
- Forbidden action：不把 CRLF/LF 等价当部署授权，不扩大为整个 ops 目录复制；不更新三服控制、不改原 11 项报告，不重跑七配置/host-publish，不删 claim，不因 native exit0 就认业务成功。
- Evidence：本任务实际失败/依赖观察、下列源码行号与 SHA；`docs/release-agent-checklist.md` 的“实际封包构造配置传递门禁”36–43 行及“多机器发布接管与缺失记录分析门禁”104–118 行。实际交付构造/解析路径必验，当前核验不能伪造过去成功。

## 已核事实与遗漏位置

只读源码依据是旧构建记录指定的 `PRIVATE/release-spug-c7728ad/ops/spug`，不是当前开发 HEAD。未从 30 个顶层 Python 文件的字节差异推导安装集合。

1. `smallapp_entry.py:22` 导入 adapter；631/639/716/750 行在实际请求路径延迟导入 simple。adapter 568/582 行回引 entry。三者形成完整本地 import 闭包。
2. `smallapp_simple.py:101` 用 `Path(__file__).with_name('smallapp_progress_remote.py').read_bytes()` 读真实远端进度载体；这不是 Python import，但同样是运行依赖。该载体只有标准库依赖，不导入维护仓其它模块。
3. `smallapp-ui/index.html:2` 还引用 `preview/style.css`。原八项 UI 资源之外，该基础样式也是实际页面依赖；已读 CSS 未发现进一步 url/@import，现 JS 未发现新的本地 module import。
4. 因此本功能的本地发布资源闭包为 **14 文件 = 原 11 + simple.py + progress_remote.py + preview/style.css**。Django、Spug `apps`/`libs` 属现有平台依赖；控制服务器和 release-center 是外部服务接口，均应固定原身份与合同，不复制进本资源包。测试与安装工具不是产品运行依赖。
5. `main_program_spug_publication.py:29–31` 的 PRODUCT_FILES 少上述三项；296–305 行的 v1 reader 只验证 11 项及原 adapter 单提交差异，322 行的测试输入包含性因此也没有闭包证明。
6. `main_program_spug_resource_activation.py:71–73` 虽收集 entry/adapter/simple 的实际 modulePins，却仅对与 productPins 相交者核候选 SHA；simple 未进入 productPins，就只被当原模块保持。530 行重载保护继续保留该旧模块，观察 PASS 不能证明版本齐全。
7. 原 SPUG_BODY 1108 行实际导入 simple，1151 行执行 `simple.configuration()`。c1 在此真实抛出 SIMPLE_CONFIGURATION_INVALID：native exit0 只表示 Python 把 FAILED JSON 打印出来，不能认定最后验证成功；wrapper 的 UNKNOWN 不否定已有七个独立 APPLIED 原件。

三个漏项的实际原字节：

| 相对 ops/spug 路径 | c772 候选 bytes / SHA256 | 运行字节 | 处置 |
| --- | --- | --- | --- |
| `smallapp_simple.py` | 7137 / `c89fe4f805af53f784188ba98f061f34cad68d9f100d6cfef573d06bc3970bc0` | 6431 / `0c44e4d058dafab71bbd27c34eac4205b9a7e0ef93b80379be8b89226d05efab` | 已证语义不同；只对此文件计划替换 |
| `smallapp_progress_remote.py` | 2945 / `82873a4d3816d0d3713e4e0b38e86144e427472fa0868e807d40bc1d2e2e86fb` | 完全相同 | 纳入闭包证明，保持原件，不写 |
| `smallapp-ui/preview/style.css` | 4469 / `77d95f2e3642840a38bd1c40aa3dc493b37090f835438cfd718c5ee741130593` | 完全相同 | 纳入闭包证明，保持原件，不写 |

本机只读逐文件比较与父实际容器观察一致。父现场原件 `spug-runtime-dependency-observation-r1.json`：8423 B，SHA256 `88facbf0b650feefa215ee67d791fdafbfe58e5ca396152c09d2e57a7a963d1b`。其实际导入 entry/adapter/simple、simple 解析失败、七配置保持、entry 151768 和两个实例保持由父采集；本子任务没有重新执行该观察。

候选 simple 的真实 `configuration()` 14 行接受可选 catalogueRestoreBindings，25–32 行严格验证点引用、唯一绑定与 SAFE 模式；36–42 行 public_configuration 才把它投影给页面。修复是安装已提交的正式解析器，不能删掉已发布配置字段，不能把历史 binding 变成可备份。

## 最小实现边界（建议，待父批准）

只新增两个 TASK 模块及对应专属测试/日志：

- `spug_runtime_dependency_completion.py`：纯依赖闭包/补充构建 reader、明确单文件补充安装器；默认 prepare-only。
- `main_program_spug_publication_verify_only.py`：c1 已写入证明 reader、纯准备、仅最终验证的受限传输和新成功 reader；默认 prepare-only。
- 仅在接入最终选择时，`main_program_installation_selection.py`、`observe_closeout_hosts.py` 各增加显式新 schema 分派。旧 v1/v2/v3 分支保持。

不修改原 PRODUCT_FILES、resource_files(v1)、resource activation、publication.py、v2 publisher、c1 continuation、HOST/SPUG 正文、产品源码、原报告或 45/r6 控制代次。现有 c1 的纯深验证函数可复用；新 reader 验证成功前六阶段及最后失败，不调用要求全成功的 v3 reader，不伪造成功 stages 喂旧 reader。

若后续实际编码证明需要额外接缝，先报具体不可复用点；不能在本次顺手改全安装体系。

父建议的交付顺序采用两阶段：第一阶段只实现依赖合同、单文件正式安装器及专属测试，冻结回归后由父先恢复页面配置解析；第二阶段再实现只验收与 v4 选择接缝。第二阶段不是第一阶段已验证资源修复的前置条件。各阶段仍需父正式批准后才改源码。

## A. 补充闭包证明与单文件安装

### 纯合同 API

`inspect_runtime_dependencies(root) -> graph`：从固定 entry、index 和 nginx locations 入口出发，AST 包含函数内部 import；递归仓内模块，记录静态本地引用。smallapp_simple 的 with_name 载体关系和 HTML/CSS 引用是明确可验证边，不能只写人工 allowlist 后不检查源码。遇到新未知本地动态导入/代码载体/引用形式，失败并要求扩展合同和测试；不静默忽略。

依赖图的边记录 `{from, kind, to}`；kind 仅 LOCAL_IMPORT、EXECUTED_FILE、WEB_RESOURCE。外部标准库及既有 Spug/Django 平台根单列，不把任意未知模块归入“外部”免检。当前图输出 14 个文件，排除测试与部署脚本。源码 SHA 为实际提交 checkout 字节，不用 AST 或换行归一化摘要代替部署字节。

`validate_dependency_completion(records, pin, *, verify_checkout)`：原 v1 11 项报告照旧严格读取；新补充报告绑定原 buildPin 和同 sourceCommit，并核旧 11 项逐字节不变。准备安装时必须核该同提交工作树 HEAD/clean 与实际文件；历史 reader 只消费已保存且不可变的完整 pins/证据，不能在临时发布 worktree 清理后失效。

建议新增报告 `MainProgramSpugRuntimeDependencyCompletion/v1`：`schemaVersion,status,sourceCommit,baseResourceBuildPin,roots,edges,files,additionalFiles,externalPlatformRoots,coverageEvidencePin,sourceCheckoutEvidencePin`。files 为完整 14 项，additionalFiles 严格是上述三项，覆盖证据必须有真实解析/缺项拒绝测试结果。仅报告 status PASS 不足，reader 逐字段/pin/图重建核验。

这是同 c772 产品字节的补充证明，不改旧 fileCount=11 或 changedFiles=[adapter]；新报告不能宣称当时已安装 14 项。将来的资源准备必须调用此共享闭包检查，不再用“枚举了多少文件”替代真实依赖覆盖。父现有构建载体后续接这一纯入口，补充报告只从已提交输入生成。

### 单文件实际安装合同

输入 `MainProgramSpugRuntimeDependencyActivationInputs/v1` 绑定补充证明、旧 11 项安装、父实际 dependency observation、c1 failure/attempt/终态、operationId 与唯一输出文件。默认 prepare 检查全部本机 pins，不远程调用；只有显式 activate 执行。

准入必须证明 c1 已终态、7 APPLIED/原 native 写入与容器读回完整、3 HOST verify PASS、最后实际 FAILED/SIMPLE_CONFIGURATION_INVALID；同一固定容器和只读 bind、父观察中的 entry 身份；原 11 + 另外两个依赖已经等于 c772，七配置已等于 c1 后值，全部原历史/claim/audit 保持。除 simple 外任意漂移拒绝，不扩成“自动同步差异”。

安装只有一个宿主路径 `C:/Spug/runtime/ops/spug/smallapp_simple.py`：先原字节排他归档、fsync、读回与 beforePin 相同；原容器只读 guard 与宿主 pin 再核；同目录排他 staged、fsync、原子 replace，再由原容器精确路径读回 afterPin。任何替换后异常如实留下 DISPATCHED_OUTCOME_UNKNOWN 或 APPLIED 未验收，不自动回滚/重试。

entry 已可能缓存旧 simple，不能仅运行旁路 Python 得到新函数就认 live entry 已更新。仅重载已授权的本任务 entry：精确原 PID/startTicks/argv/监督身份核验后按现有安装器的受控重载机制；不重启容器、Docker、三服控制或其它服务。新进程必须核 exe/argv/cwd/env/实际 import 路径、完整 14 文件、真实配置解析与应用设置、原 7 配置/31 历史路由/33 apps/3 tasks、两个实例与受保护资源保持。

新实际报告 `MainProgramSpugRuntimeDependencyActivation/v1` 固定 before/after entryIdentity、before/after 完整14pins、replacement(唯一simple)、previousSourcePin、native receipts、配置/历史/实例保全、dependencyCompletionPin/baseResourceActivationPin/c1FailurePin。私密丰富原件和公开脱敏 core 分离；真正完成后才 PASS。不得只复用旧 11 文件 install PASS 作为新模块已安装证明。

## B. c1 只验收，不重写

建议输入 `MainProgramSpugPublicationVerificationInputs/v1`，精确字段：schemaVersion、sourceCommit、revisionId、controlGenerationPin、continuationInputsPin、continuationAttemptPin、continuationFailurePin、continuationCompletionPin、dependencyActivationPin、historicalSourceCustodyPin、verificationId、outputFile。仍为 45/r6/c1，verificationId 只标独立验收观察，不造 c2 配置发布或 r7 控制代次。

`prepare_verification(...)` 只核原 c1 的所有真实证据和新依赖安装，不生成原成功；要求末阶段 raw native exit0/FAILED/SIMPLE_CONFIGURATION_INVALID 与 wrapper 对应，并核 runner 已退出。前六阶段完整 reader 深核，包括七次独立 readback、两次 volume transition、五次 bind guard、所有 custody 与三 host verify 原件。不能仅信 failure.writeStates 布尔列表。

新 runner 仅具备 inspect / 原配置与14文件读回 / host-verify / spug-verify 命令。没有 publish、install、replace、custody 或恢复/备份入口；即使参数被篡改也不能转到旧 `execute_prepared`。原 c1 claim/gate 永久保持；新增独占 verify claim 绑定 c1FailurePin，未知查询只跟原编号，不重派。验证会调用控制 GET，可能追加原控制查询审计，因此报告应为 configurationWrites=false/businessMutationDispatched=false/controlApiQueriesPerformed=true/queryAuditWritesMayOccur=true，不能笼统声称服务器零写入。

最小当前验证顺序：核 entry 转移及14文件、七配置/audit原件 → 三服原 HOST verify（只读，不 host-publish）→ 原 SPUG_BODY verify → 再核完整当前身份/14文件/七配置。若父决定复用三服 c1 PASS，须仍有足够当前控制身份正证据；默认重新进行三项只读 verify 更直接，不重做任何已成功服务器写入。

HOST/SPUG 正文不改。生成新的 verify SPEC 只允许对 `spug.observation.entryPid` 作一次经 dependencyActivation 实际 old→new 证明的替换；c1 auditPath/七值/旧 expected/原历史指纹/旧11资源/任务快照均原样。补充3资源在外围严格核，旧深校验仍照旧验证11项，加起来完整14。新 SPEC 不回写到旧 attempt 或旧程序。不能放宽 entry 任意 PID 匹配。

独立新 rich `MainProgramSpugPublicationVerification/v1` 精确记录原 c1 failure、已成功前六阶段 pins、依赖安装、4个新 verify 原生阶段、当前 guards、只验收标志。原 c1 rich 仍 FAILED。只有新完整验证成功才复用原 `project_core` 生成新 `MainProgramSpugInstallation/v1` core，输出文件带 `-verification-v1`，不覆盖 c1 本应成功但未产生的文件。

最终 `TaskMainProgramInstallations/v4` 仅包含 schemaVersion/sourceCommit/controlGenerationPin/spugInstallationPin/verificationInputsPin。新 reader 同时深核历史 c1 写入、新补充依赖和最新只验收原件；原 v1/v2/v3 读取保持。收尾 collector 仅增加 v4 分派，不能把补充安装或控制-only记录视为 full publication。

### 历史源码 pin 边界

新增两个模块不改变 c1 的执行源码。若新增 v4 分派修改 selection/collector，而 c1 attempt.inputPins 实际引用其原字节，必须在修改前将且仅将被影响的原文件排他托管，映射 originalPin→preservedPin，完整回读。旧原输入其余逐 pin 核，不改旧源码pin；新执行依赖另固定。原正式旧 v2 source custody 仍保持，两代托管不能互相冒用。不得用“忽略当前 reader 文件”绕过原执行身份，也不要求历史合法读取永久依赖旧路径当前内容。

父已精确核 c1 attempt 的350项闭包：selection 当前 `d1191685c5792f3caf438d0b093285ded09800140677db4b71b7e089332cbe0b` 在其中，collector 不在；pub01077433、c1 2a4be50、v2 0915b324 及两份旧 v2 托管原件均在其中。因此第一阶段完全不动旧350项；第二阶段仅需为实际改动的 selection 追加一份 c1 历史原字节托管，其余349项保持逐原pin核验。不得为collector或未变化源码无故扩大托管集合。

## BDD / TDD 候选（批准后实施）

1. Given c772 实际 entry/index，When 清单只有原11，Then 真实闭包检查列出准确三缺项并拒绝；添加14后通过，移走 progress carrier/style 或增加未声明本地依赖仍拒绝。
2. Given 原旧 simple 与 c1实际配置字节，When 调用真实 configuration/public_configuration，Then RED 为 SIMPLE_CONFIGURATION_INVALID；同 c772解析器 GREEN，历史 nonselectable binding仍不变，未知字段/非法route继续拒绝。配置仅置于真实临时文件，替换 CONFIG路径，不mock解析成功、不调用网络。
3. Given 另外两个漏项与原11已经相同，When 补充安装计划，Then 唯一写入simple；任何其它差异拒绝，而非自动多写。
4. Given 原字节与预先全保全，When 实际临时文件替换后回执/读回出错，Then 实际新字节保留、失败明确、没有自动重试/回滚。
5. Given 正确候选文件但旧entry仍加载，When 旁路解析通过，Then 不足以生成PASS；必须实际授权entry重载及新身份/导入/真实入口合同证据。
6. Given c1实际七APPLIED与最后native FAILED，When 只验收prepare，Then 历史写入可读但整体仍未成功；删任一真实readback/native argv/program或修改最后错误拒绝。
7. Given 新依赖实际安装且七配置保持，When verify-only，Then 传输只能四项验证及guards，所有 publish/custody/配置write方法都应不可达；测试用真实子进程/磁盘原件验证，不能靠成功布尔fixture。
8. Given 原entry变化有严格安装转移证明，When 新verify SPEC，Then 只允许该PID字段变化；修改配置、audit、旧指纹、任务、原11字节、代次或其它PID均拒绝。
9. Given 最终验证全部真实证据，When v4reader，Then 新core闭合且两次原FAILED/claim保持；只有部分成功、native非零/损坏stdout或缺source custody不得投影成功。
10. 保留原所有旧测试，必要回归包括资源安装/delta、391项相关发布/reader，以及真实simple/entry/UI配置合同。本机fixture只证明合同；真实容器依赖/entry和用户矩阵由父执行，不能在本阶段声称完成。

## 风险与尚需父冻结的输入

- 父已提供实际 dependency observation；正式实现前还要固定 c1 outer completion/runner终态、原stage完整 pins 和唯一失败归因，不从 wrapper UNKNOWN猜测。
- 需要将当前实际读取的配置字节作为解析测试输入保存在 PRIVATE；公开报告仅pins，不输出凭据或历史业务内容。
- simple更新与entry重载之间可能仍服务旧模块；单文件成功不等于最终入口成功，必须保持失败状态直到新身份与真实入口确认。
- 本设计未验证完整14闭包在Linux实际运行/页面请求；静态图不会替代父的真实导入、配置解析和浏览器证据。
- 本轮只确认三项缺漏的本机关系/字节、现有合同缺口与最小补齐路径。未生成补充build/activation/verification成功原件，也未修改任何冻结工具。
