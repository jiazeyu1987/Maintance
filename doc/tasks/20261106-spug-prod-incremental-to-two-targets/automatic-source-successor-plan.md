# 自动增量来源控制器后继代次

## Current Status
completed（仅来源控制安装子项）。根任务已按显式暂存续办计划完成source57升级，actual sourcePID20229，MAIN57/58/59、Spug和FULL373原证据保持；实际计划READY。I1任务374已由真实页面单次受理，总任务I1/I2终态和收尾仍在进行。

## Goal and milestones
1. 已确认最小部署边界：source57 控制服务；MAIN57、58、59 的恢复控制器及 Spug 11 个入口文件保留 0d44578。
2. 已完成真实本地文件 RED → GREEN 后继安装、按组件版本及按操作阶段证据合同。
3. 已完成默认 prepare only 的 source-only 安装器；新正式提交和构建回执存在后才能准备，只有显式 --apply 才允许远端变更。
4. 回归并交根任务审阅；安装、实际计划 READY、后续 I1/I2、最终清理由根任务协调。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。旧安装合同作为显式 v1 保留；新合同必须完整自描述，不缺字段猜版本，不延长产品查询超时。
- 是否从根因和长期维护角度解决：是。安装代次、执行时版本、当前运行版本分别固定，允许有证据的组件独立更新。
- 是否存在临时补丁或绕过：否。不改 FULL 原件，不初始化 epoch，不复跑旧双控制器 installer，不强制三服同提交。

## 经验门禁
- Trigger：来源控制程序后继版本安装。Preflight check：精确新提交及专属 worktree 的已验证构建包、前代安装回执和所有配置 pin、无活动来源/恢复任务、同一物理锁、epoch READY、完整原 FULL 373 元数据证据、保留目标和 Spug 逐文件身份。Blocker：任何 pin、服务归属、epoch 或当前任务漂移。Verification：只重载来源服务，真实新 PID/argv/dropin/所有包文件验证，计划仍引用 FULL 373，原目标和业务容器/挂载/失败原件不变。Forbidden action：重跑备份、初始化 epoch、目标控制器重载、变更业务服务、改写旧证据。Evidence：exclusive 后继安装 receipt、前后快照及阶段选择 pins。
- Trigger：跨代次自动备份验收与清理。Preflight check：FULL/I1/I2 各自明确安装/构建/Spug 证据，链与物理 epoch 一致，当前各组件单独 manifest 校验；所有构建来自 task-owned-builds.json 明示清单。Blocker：历史原件改变、阶段错绑、任一未归属工作区或产物。Verification：负向真实文件测试和根任务真实页面/元数据审计。Forbidden action：用当前 HEAD 伪写历史执行版本、广扫/清理其他任务、以同包文件数替代完整 SHA。Evidence：自动阶段选择、当前安装选择、不可变 audit/source-restoration 和清理报告。

## BDD
- Given FULL 373 在旧来源版本成功且物理 epoch 未改变，When 新来源控制修复安装，Then 仅来源 PID/包配置切换，原 FULL、目标和 Spug 原件不变，计划选中同一 FULL/最新父链。
- Given 当前 source 为新版本且 MAIN57/58/59、Spug 为旧版本，When 验收当前组件，Then 对各自构建 manifest 与实际进程逐项检查；不要求不相关组件提交相同。
- Given FULL/I1/I2 执行于不同已固定版本，When 验证链，Then 每个操作绑定其阶段安装 pin，链/epoch/起止位点仍连续；改动任何历史 pin 或误选代次必须失败。
- Given 缺少新提交构建、前代 receipt、运行身份或新安装输出已存在，When prepare/apply，Then 明确失败且不覆盖任何历史文件。

## Frozen receipt contract
新公共文件 automatic-source-control-installation-<commit7>.json，私密同名 .private.json，schemaVersion=AutomaticSourceControlUpgrade/v1。顶层 sourceCommit/packageSha256/fileManifestSha256/fileCount/policy/epoch；controllers 固定 [SOURCE, MAIN_TARGET]，只私密版本保留 control；controllerGenerations 每行 role/sourceCommit/fileManifestSha256/fileCount/packageSha256/buildPin，MAIN_TARGET 另 installationPin。predecessorInstallationPin 固定前代；Spug 使用独立旧回执且实文件验证。不回写旧 automatic-control-installation-57.json。

阶段选择由 UI 子项提供 AutomaticStageDeployment/v1：automatic-<full|i1|i2>-deployment-selection.json，显式 sourceInstallationPin/sourceBuildPin/spugInstallationPin/sourcePrivateInstallationPin、sourceCommit/spugCommit。FULL 旧 submission/terminal/audit/source-restoration 不回写；当前选择独立选择最后来源安装。

## Verification and ownership
本子项拥有 install_automatic_source_successor.py、closeout_contracts.py、verify_stable_controls.py 及自己的 test_automatic_mixed_generation.py。UI 子项拥有阶段选择/UI/preflight；epoch 子项拥有逐阶段 audit/source proof。task-owned-builds 仅在新构建真实 PASS 后根任务追加。不改变安装到 58/59 的历史流程或其 custody。

### 最终只读主机快照补充
根任务审阅后追加独占 `observe_closeout_hosts.py`、`test_closeout_host_snapshot.py`。BDD：Given 当前显式来源选择新代且 MAIN57/58/59 保留旧代，When 最终主机快照，Then 每个实际控制器按自身提交、manifest、PID、配置核验；I2 绑定执行时阶段安装，任何旧固定选择、不同 manifest、改动阶段 pin 都失败。不得调用控制 API、Ledger、SQL 或任何变更命令；历史 FULL/367 证明不改写。

RED：新 fixture 明确不同来源/目标 manifest 与新来源 PID，原固定 selector 导致 8 failures（缺每组件版本、忽略当前选择原件变化、I2 不支持阶段安装参数）。GREEN：collector 14 passed。与先前合同回归共 50 passed；只读 remote carrier compile/AST 检查保持无控制 API 和变更命令。实现已冻结待根审阅；新包尚未构建/prepare/安装。

## TDD evidence and handoff
- RED：`pytest test_automatic_mixed_generation.py -q` 首批 5 failed，缺 controller_generation/validate_source_successor/validate_native_dispatch；实现后 5 passed。
- RED：新增安装器默认不 apply、正式包差异范围、真实文件 rebind 测试，3 failed，缺 install_automatic_source_successor 模块；实现后 8 passed。
- REGRESSION：混合代次 10 项、原 closeout 12 项、UI stage 14 项，合计 36 passed。仅真实本地临时文件和原件，不执行服务/备份/远端；嵌入 Linux 脚本 compile 通过，不能代替实际安装验收。
- `python install_automatic_source_successor.py --commit <精确40位已提交SHA>`：默认仅本地 prepare，前置要求独立 FULL terminal/audit/source-restoration、同 epoch、已验证专属构建和 Spug 实文件。生成 exclusive `automatic-source-successor-plan-<7位>.json`。
- 根任务审阅后同命令加 `--apply`：先实核前代两服务与完整原包/配置，持物理锁只读 epoch，保留业务/挂载/历史元数据，安装并重载唯一 source unit。新 HTTP 计划必须 READY 且 base/parent 仍为 FULL 373；实际原始观察先存私密 exclusive 文件，本机证据与 Spug 复核后才输出正式公共 PASS。
- backend 子项最终确认包变更仅 `control/recovery_control_smallapp.py`、`control/recovery_control_smallapp_native.py`，成员集合保持 130 不变；安装器允许名单已收窄为这两个文件。后续真实构建超出该范围必须 fail fast 并交根任务审阅，不自动扩允许名单。

## 暂存 engine 精确续办
实际失败原件：PRIVATE/172.30.30.57-error-fc3fa06027c4.private.log，238 bytes，SHA256 fc3fa06027c4a101180a553e5fecfc33fc88100c783b7c8e0dbf319d24d417e3；原 prepare `automatic-source-successor-plan-0dc7429.json` 保留。目标提交 0dc7429d4758a208a5b0c098111fe9702ab63235。

BDD：Given 原 source PID/前代配置/物理 capture/epoch 未变，且此次 engine 的全部 130 正式文件及 package.json 已完整暂存、无新配置/dropin/阶段 receipt，When 显式 --resume-staged-engine，Then 只验证并复用这个精确目录，不删除或重写它，再执行原受控安装流程。目录缺文件、多文件、SHA 不符、已有后续配置/dropin、不同提交/前代、未知失败均拒绝。来源物理字段必须逐项保持，只有已证实的程序 pin 按新 engine 重绑定；未知 sources 字段漂移仍拒绝。

经验门禁沿用上文并补充：前置先保存失败阶段事实与当前实读状态，不用 existence 作为成功；resume 必须显式且只接受本次固定失败/提交/原 prepare pins。测试在本机真实临时目录复现 program pin 合法重绑定与全部反例，不 mock 服务器成功。不得 apply 或修改服务器。

只读实际诊断已完成：`automatic-source-successor-staged-engine-readonly.json`。唯一变化为 `captureCommand[2]` 的 `formal/minimal_capture_entry.py` 与 `toolPaths[2]` 的 `formal/formal_capture_recovery_inputs.py` 从旧 engine 移到新 engine；物理 `configurationPath/sourceIdentityPath/stagingRoot` 不变，两程序字节在新旧 130 清单相同。实际 source PID 25086、MAIN PID 20273、epoch 与物理 capture pin 同原；新目录 130 程序文件及 package.json 全部 SHA 验证，新 owner/control/staged/installation 配置和 dropin 均不存在。

修复采用逐字段比较：只有 captureCommand/toolPaths 数组内已经登记在两包且 SHA 相同的程序可换 engine 前缀；数组长度、其他 CLI 参数、所有物理/未知字段不变。显式 resume 仅接纳本次 0dc7429、前代固定文件、238-byte 错误原件、原 prepare 与只读观察的固定 SHA。续办复用目录而不改写；完整集合（含目录）、regular file/nlink、无符号链接、package.json 原字节、130 SHA、前代 PID/epoch/FULL pins、新配置/dropin 缺失均重新核验。

TDD：3 个新增合同用例 RED（缺函数/flag）→ GREEN；后续阶段文件门禁再 1 RED → GREEN。本机定向 14 passed。Windows 真实文件 symlink 创建报 WinError 1314，未当 PASS；已按根任务授权在本机既有 Python 镜像执行独立 Linux 测试，7 场景（正常、文件/目录/根 symlink、hardlink、额外目录/文件）全部通过，1 unittest/0.018s。镜像 sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735；network none、read-only workspace、32MiB tmpfs，容器 `spug-source-staged-alias-0dc7429` 已删除并精确 ps 空。未写服务器。

实际新包与完整 FULL proof 的 `prepare()` 内存构造通过，130 成员、payload SHA256 `28a2f6fde680dfde309080db0ec85b589e4acbb2944f23c5d4ed8eadfb4629f3`；未生成新的 prepare 文件、未连远端。根任务续办命令：

`python install_automatic_source_successor.py --commit 0dc7429d4758a208a5b0c098111fe9702ab63235 --resume-staged-engine`

该命令仍默认 prepare only，写新的 `automatic-source-successor-resume-plan-0dc7429.json`；根审阅后同命令加 `--apply` 才执行唯一实际续办。原 prepare、错误日志、暂存观察、FULL 373 原件保持。

### Root actual installation 2026-11-07T22:29:02.748915+00:00

根任务已审阅冻结计划及Linux别名测试，唯一 --resume-staged-engine --apply 实际PASS，见 automatic-source-control-installation-0dc7429.json。新sourcePID20229，MAIN20273及原业务/epoch/物理capture/历史FULL保持。前面的“未apply/不得修改服务器”为子Agent交接边界；实际安装由根任务在同一授权范围执行并记录experience-preflight。I1/I2阶段选择真实绑定已安装回执。此安装子项完成；总任务仍待I1/I2及最终收尾。
