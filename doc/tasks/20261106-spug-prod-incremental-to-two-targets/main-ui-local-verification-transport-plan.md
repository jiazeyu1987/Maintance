# MAIN UI 本机验真子进程：明确终态与原输出留存

## Current Status

ready_for_closeout。本机实现与限定50项JS验证已完成，三文件冻结交父精确提交及真实UI验收。上一双目录阶段已由父提交，真实 r7 preflight r6 PASS，父报告对应提交 `60d19f3`。本阶段仅处理本机正式验真 CLI 的结果分类、原输出证据和有限预算。不修改 dispatcher、历史 reader 或已存在原件，不运行真实 UI/远端。

## 目标、里程碑与预期验证

1. 保留这次原失败事实，区分已证实状态与超时推断。
2. 完整验真 CLI 无论成功/失败都保存原 stdout/stderr、返回码/信号/启动错误和实际耗时；只输出安全错误码。
3. 先新增有限 RED，再做 CJS 局部实现与有限 JS 回归。原 Windows Git 58 项不重跑，原 1630 原件闭包与提交前复核不变。
4. 实际预算等父只读 CLI 终态证据定值；本阶段不据估计扩大远端或产品期限。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。超时/非零/信号/启动错误/非法输出全部拒绝；原输出落私密不可变证据，不使用旧摘要替代。
- 是否从根因和长期维护角度解决：是。分离本机原生传输终态、正式摘要解析与完整闭包验真，保留可诊断原证据。
- 是否存在临时补丁或绕过：否。仅调整本机完整验证有限预算及录证；不改变业务接口、远端请求、产品超时或实际验真范围。

## 经验门禁

- Trigger：MAIN UI 在打开浏览器前完整本机验真失败，只给通用错误且没有内部 CLI stdout/stderr。
- Preflight check：固定 Python/脚本/参数、严格 selection pin、原 1630 closure，实际本机 CLI 时长证据、独占 observation 命名。
- Blocker：缺真实预算依据；原件留存失败；同 observation 已存在；子进程超时/未知/非零或输出不符合正式协议；任何原 pin 漂移。
- Verification：明确子进程协议边界 RED→GREEN，真实临时文件保存字节及 pin、成功缓存/失败无缓存、原 MAIN/v1/UI 合同回归；父独立实际 CLI 和 UI 验收。
- Forbidden action：不得把122秒推断直接改写成已证 ETIMEDOUT；不得伪造原 signal/status；不得忽略stderr或用旧摘要；不覆盖失败原件、不改 dispatcher/history/oldpins、不扩大到通用重试平台。
- Evidence：原失败及父单独 CLI 时长观察；下文列精确已读原件。

## 已证实事实与缺口

- `PRIVATE/main-r7-full-ui-submit-20261110-r1-native.private.json`：824B/SHA `3adc5c0b542bec4826150f4440e1526280d49979d1185cc0510da1fbf2eab6b9`，包含原 returnCode/seconds/stdoutPin/stderrPin/attemptPin。
- 原 stderr：72B/SHA `da7ee4daffcade993d356f3352fabb5a3c03558f2d0cec6a09a7de445be89f7e`，只有 `NOT_STARTED / MAIN_CURRENT_INSTALLATION_FAILED`。
- 父实际外层耗时122.547秒，与现 `spawnSync(timeout=120000)` 高度吻合，但当前通用判断把 `response.error`、非零exit和stderr全部合并，原内部 `response.error.code` 没有保存。因此**超时目前是有依据的推断，不能补造已丢失原字段**。
- `main()` 在初次 `validateGate` 后才建私密目录、打开浏览器并建立普通 UI report，所以此失败也没有本机 CLI 的独立 evidence。录证应属于 CLI 入口，不能依赖浏览器阶段启动。

## 最小正式接口与证据

在原 CJS 内抽出有限 `runMainInstallationCli(selectionPin, options)`；固定现有 Python 路径、当前 task dispatcher、selection文件名、`--public-summary`、`shell:false/windowsHide:true/maxBuffer:16MiB` 保持。`options` 仅为当前已校验 kind/phase/observation/cycle，用于唯一证据归属，不接受命令、回调、替代摘要或任意证据路径。

在既有 `PRIVATE/automatic-incremental-ui/<cycle>/` 下，创建固定 observation 对应的独占子目录，例如 `<kind>-<phase>-<observation>-current-installation/`。先校验字段、预留该目录（不允许已存在），再启动 CLI；第一次正式验证只有一份原生调用。相同 observation 再跑不得覆盖/默认重试；需要新 observation 才能形成新的独立执行证据。

`stdout.private.log`、`stderr.private.log` 用原 Buffer 字节写入 `wx` 并 fsync，包含零字节文件也记真实0/SHA；随后独占写 `native.private.json`：

```text
schemaVersion = MainUiCurrentInstallationNative/v1
selectionPin, cycle, kind, phase, observation
startedAt, finishedAt, durationMs, timeoutMs
executable, argv
pid (原返回值或null), exitCode (原status或null), signal (原signal或null)
errorCode (原error.code或null)
stdoutPin, stderrPin (绝对私密path/真实bytes/SHA)
```

若 spawnSync 抛错而没有原返回，则记录真实可得 error.code，status/signal/pid 保持null，不猜退出码；不存在输出记空字节并明确来自该抛错分支，不自造stdout。录证失败直接阻断，不能继续打开浏览器或建立成功缓存。安全输出只含稳定公共错误码与可选metadata pin，不打印原输出/连接/私密路径。

写完原 native evidence 后再分类：

- `error.code=ETIMEDOUT` → `MAIN_CURRENT_INSTALLATION_TIMEOUT`。
- `error.code=ENOBUFS` → `MAIN_CURRENT_INSTALLATION_OUTPUT_LIMIT`。
- 其它启动/传输 error → `MAIN_CURRENT_INSTALLATION_SPAWN_FAILED`。
- 明确 signal 或无可证退出码 → `MAIN_CURRENT_INSTALLATION_TERMINATED`。
- 明确非零 status → `MAIN_CURRENT_INSTALLATION_EXIT_FAILED`。
- status0但stderr非空 → `MAIN_CURRENT_INSTALLATION_STDERR_REJECTED`。
- status0且无stderr后才按原JSON/schema/selection/full inputPins/build/runtime合同验证；非法JSON仍 `MAIN_CURRENT_INSTALLATION_INVALID`。

原成功缓存仅在全部原件与runtime验证完成后建立；失败不缓存。后两次确认/写receipt前仍重验全部原 inputPins 和同selection原件，不重复慢CLI。新原生 evidence 不加入安装历史权威，不替代其原1630闭包，也不改变既有 receipt schema。

## 有限预算决策

当前120秒仅适用于原较快本机环境，父正在独立测量本轮真实全闭包验证。等待原结果后选择一个固定、明确、有限的本机 timeout 常量，并在本计划与测试中记录实际时长及裕量。不得无限等待、动态fallback重跑、接受超时后旧摘要或改变 HTTP/SSH/业务/产品期限。外层真实 UI 载体预算由父独立与此常量协调。

父已提供实际独立CLI session58196：exit0，完整原摘要PASS，276.188秒；`PRIVATE/main-r7-dispatcher-cli-observation-20261110-r1-native.private.json` 700B/SHA `1e913b153fe968801335ed3084fd2fd1a9a540dcbad6df561e66828effefab5d`，原stdoutPin保留。父明确批准固定本机 `timeout=600000ms`（约本次实际耗时2.17倍）；其它期限、16MiB、原1630闭包与dispatcher不变。原UI r1仍仅超时推断，不补造当时丢失的error.code。

## 本阶段 TDD 执行

先新增有限测试取RED，之后最小实现；测试是本机子进程协议与实际私密文件录证，不是完整CLI现场复验。实际结果随后追加，原件独占保存。

RED：`node --test TASK/main_ui_local_verification_transport.test.cjs` 实际 exit1，13 FAIL、0 PASS、0 skip，缺正式 `runMainInstallationCli`；测试载体与文件前置均可运行。原日志 `main-ui-local-verification-transport-red-r1.log` 27291B/SHA `3e105f6e0e0baab6cfce1ef10a930496b358834ba668565c361ffef56b318c93`；命令/退出码见同stem `.json`。生产尚未改，之后仅最小实现与合法相邻fixture修正。

GREEN + REGRESSION：唯一 session94254，固定 `node --test` 执行新 `main_ui_local_verification_transport.test.cjs` 13项、`main_ui_deployment_root.test.cjs`24项、`automatic_main_cycle_ui_contract.test.cjs`9项、`automatic_stage_ui_contract.test.cjs`4项；50 PASS、exit0、0skip、32.80秒。原日志 `main-ui-local-verification-transport-green-r1.log` 3777B/SHA `3872ba6450a82b6dd022f1f05f3f693b0b2c7486e0db60fdf5770f583a68b1e7`，命令/实际退出码/三输入前后SHA见同stem `.json`。未重跑Python/Git/实际CLI，未访问浏览器/服务器。

实现只修改原CJS、相邻双root测试的合法options/Buffer/临时PRIVATE/预算期望与新observation前置，并新增独立transport测试。原37合同断言保留，dispatcher/原1630闭包/两次确认前复核/其它期限未改。原native元数据新增 `responseReturned` 明确区分原返回与启动抛错，原0字节输出也保留实际SHA；错误公共码不包含原输出。相同observation原目录存在即拒绝，失败不缓存，不覆盖实际r1。

父另已完成真实 preflight r7 PASS并告知新gate；该现场结果不是本阶段50项协议测试的结论。冻结交付清单为 `main-ui-local-verification-transport-delivery-r1.json`，由父精确提交，本子任务不写本仓index或commit。

## BDD 与测试边界

1. Given 原 `ETIMEDOUT` 且有部分stdout/stderr，When MAIN v2验真，Then 两原输出逐字节保存、metadata记录真实status/signal/error/时长，报专用TIMEOUT，浏览器及receipt零创建。
2. Given 非零退出、signal、ENOENT、ENOBUFS或exit0+stderr，When验真，Then分别保留原字节并返回对应安全错误码；不得全部变成timeout，不泄露原输出。
3. Given exit0但JSON非法或后续closure漂移，When验真，Then已有原native证据保留，无成功缓存；不使用旧摘要补救。
4. Given 成功正式摘要及完整原文件闭包，When首次验真，Then原stdout保存且只跑一次固定CLI；确认前重复验证不重复CLI，但任一原文件变化继续拒绝。
5. Given 同observation证据已存在或写证据失败，When尝试验真，Then不覆盖且不得继续成功；相同observation不隐式重试，另显式observation的失败也不污染成功缓存。
6. Given 有限timeout常量及固定argv/maxBuffer，When协议边界检查，Then只有本机deadline变化，所有其他预算及v1不变。

测试新增独立 CJS 文件，真实临时私密目录/原字节/pin；仅固定 `spawnSync` 协议边界提供终态对象，不声称真实完整loader/现场已通过。在 VM 测试载体里把固定PRIVATE根重定位到临时目录，并给原新MAIN测试补真实合法 kind/phase/observation，避免测试写真实私密路径；不增加产品可注入参数。旧失败后立即同observation调用的测试应改为显式新observation，保留“失败无成功缓存”原断言，并新增同observation不可覆盖断言。

只触及原 CJS、新独立测试及必要受影响 `main_ui_deployment_root.test.cjs` 前置/预算期望、专属文档。原 Python、两Git函数、dispatcher/history、read-only audit均冻结。不重跑28分钟Git；JS新有限测试+原37合同作为回归。
