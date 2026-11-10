# MAIN UI 预检：分别绑定来源与 Spug 部署根目录

## Current Status

design_review。本修订替代尚未实施的单 root 设计；原设计及父实际单 root FAIL 原件保留。未改生产、未写测试、未运行 UI/服务器/构建。等待父审阅本修订后再执行 RED → GREEN → 有限回归。

## 目标、里程碑与预期验证

1. 区分真实已安装 source b5 与 Spug 565 各自的构建源码，完整绑定两份正式 build、两棵真实干净 worktree。
2. 显式成对选择，分别执行原完整 component 门禁；默认路径与旧 shared-head 合同保持。
3. MAIN gate v2 在浏览器前核正式 installation 公开 CLI、全部物理原件、两 build 与 runtime 同值证明；最终写入前继续原件屏障。
4. 先真实临时 Git RED，再最小实现及有限回归；本机协议测试不代替父真实 CLI/preflight/UI 验收。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。两参数必须同时给定；缺一拒绝，不推断目录，不自动改提交或排除文件。
- 是否从根因和长期维护角度解决：是。source 与 Spug 是两个真实已安装构建，必须分别验证对应原件和源码。
- 是否存在临时补丁或绕过：否。原 component scope 算法、默认 shared-head 门禁及完整 native 安装闭包保持。

## 经验门禁

- Trigger：已安装 source 与 Spug 使用不同提交，单一 clean worktree 在完整 Spug scope 出现真实差异。
- Preflight check：正式 dispatcher 已验两 build 原对象/pin/worktree/commit；每个 root 必须真实根目录、精确 HEAD、全 clean；原完整 component 门禁前后执行。
- Blocker：仅给一个 root；任何 pin、原完整对象、目录、HEAD、clean 或 component scope 不符；CJS 正式 CLI/完整原件/两 build/runtime 绑定失败。
- Verification：真实临时 Git 的两个提交与两个 worktree；保留 app.js 差异并让单 root 原门禁仍失败；两 root 各自完整通过。CJS 协议边界测试明确不代表实际 loader 或现场成功。
- Forbidden action：禁止忽略 app.js，禁止将 Spug commit 改成 source commit；不改历史 selector/reader/custody、dispatcher、旧 gate 或共享验证函数；不调用远端/UI/构建。
- Evidence：父 `main-ui-registered-component-roots-observation-20261110-r1.json` 已真实分别调用原 component 门禁 PASS，未生成 UI gate；父单 root r2 实际 exit 1 保留。

## 已证实事实及修订原因

父在登记的 b5 worktree 执行原 `verify_stage_deployment_inputs`：source 通过，Spug 报 `AUTOMATIC_DEPLOYMENT_INPUTS_CHANGED`。14 个真实 Spug 文件中唯一差异是 `ops/spug/smallapp-ui/app.js`。这不是工作区脏改动，不能忽略。

父随后独立只读观察证明两目录均真实根、全 clean，原完整 component 验证分别 PASS：

- source：`release-build-b5fa4c5.json`，1895B/SHA `cf8b70bf9d547c280dcdef33116707760100e4fdfff29b6d8dd1d73664c5164c`；`worktree=C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/release-chain-policy-b5fa4c5-20261110-r1`；`targetCommit=b5fa4c581f011f022cb9cde86a11b9b0ee0defd3`。
- Spug：`spug-resource-build-5651efc-r3.json`，7153B/SHA `a30b1d8f3472be5e740994ad71b4eb95f2be0743defe450d82427a7bb58008a5`；schema `MainProgramSpugResourceBuild/v2`；`worktree=C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/release-spug-5651efc`；`sourceCommit=5651efc5b9972b20bcacb50d0774e5862cbe8e6b`，`fileCount=14`。

Spug build 没有 `targetCommit` 或 `allFilesShaAndCompileVerified` 字段，不能套用 source build schema。现 dispatcher `spugRuntime` 已提供正式 `resourceBuildPin` 与原完整 `resourceBuild`；无需修改 dispatcher 或复制私密历史链。本子任务只读正式 loader 再核两原对象一致，不重复父 Git 观察。

## 最小 API 与执行次序

CLI 仅增加一对显式参数：

`--source-deployment-root ABSOLUTE_PATH --spug-deployment-root ABSOLUTE_PATH`

不接受之前未实施的 `--deployment-root`。不传两参数时，仍使用开发目录及原 `verify_stage_deployment_inputs`，仍要求其 shared HEAD；不引入自动 fallback。

同 preflight 文件内新增：

`verify_main_deployment_inputs(verified, default_root, *, source_deployment_root=None, spug_deployment_root=None) -> dict`

显式分支只在两参数均给定时进入：

1. 用 `BoundDocuments(TASK, verified.inputPins)` 分别读 `generation.generation.buildPin` 与 `spugRuntime.resourceBuildPin`；两读回对象必须分别完整等于 `generation.build`、`spugRuntime.resourceBuild`。source 必须原 `status=PASS/targetCommit=selection.sourceCommit/allFilesShaAndCompileVerified=true`；Spug 必须原正式 schema、`status=PASS/sourceCommit` 与正式 loader 投影一致，原 `files/fileCount` 闭合。不得从用户参数生成新 build 权威。
2. 两目录各自必须存在、绝对、无解析别名/symlink/junction，精确等于对应登记 `worktree`。Git `--show-toplevel` 必须为该实际目录，HEAD 精确等于该 component 的 build commit；`status --porcelain=v1 --untracked-files=all` 必须空。不得以另一 clean clone 同 commit 代替登记路径。
3. 分别调用原 `verify_deployment_inputs(source_root, source_commit, files, component='source')` 和 `verify_deployment_inputs(spug_root, spug_commit, files, component='spug')`。files 来自原 Spug build 的全部文件；source 仍从该 source commit 原 files.json 取得完整映射。**不修改两个共享验证函数，不复制或缩减 scope。**
4. 两 root 各自检查前后的根身份、HEAD、clean 一致；两 build 原 pin/完整对象和已验物理输入重新核对。只读 Git 参数数组、`GIT_OPTIONAL_LOCKS=0`、30 秒期限保持。
5. main 执行顺序：完整 installation loader → 两 root 本机门禁 → 原 Spug/来源只读运行态观察 → 两 root 再执行相同完整门禁且结果完全相等 → 原件屏障 → 写 runtime/baseline/gate。错误 root 在 Docker/远端观察前失败。

## 新证据结构

仅显式双 root 生成 `MainProgramAutomaticIncrementalUiPreflight/v2`。默认分支仍 v1；runtime 仍原 v1，已有 `gitDeploymentInputs` 放同一完整对象：

```json
{
  "source": "原 verify_deployment_inputs(component=source) 的完整对象",
  "spug": "原 verify_deployment_inputs(component=spug) 的完整对象",
  "deploymentRootBindings": {
    "source": {
      "schemaVersion": "MainProgramDeploymentRoot/v1",
      "mode": "PINNED_BUILD_WORKTREE",
      "path": "source 规范化绝对目录",
      "buildPin": "原 source build 本地 pin",
      "targetCommit": "source build.targetCommit",
      "headCommit": "同 targetCommit",
      "registeredWorktreeMatched": true,
      "clean": true
    },
    "spug": {
      "schemaVersion": "MainProgramDeploymentRoot/v1",
      "mode": "PINNED_BUILD_WORKTREE",
      "path": "Spug 规范化绝对目录",
      "buildPin": "原 resourceBuildPin",
      "targetCommit": "resourceBuild.sourceCommit",
      "headCommit": "同 targetCommit",
      "registeredWorktreeMatched": true,
      "clean": true
    }
  }
}
```

上述字符串是类型说明，不是可以用于现场的证据。实际字段全部来自原件及真实 Git。两个 HEAD 可以不同，但每个必须等于其自己 build commit、原 component gate.headCommit 和 installedCommit。不能据此放宽默认/旧 shared-head 合同。

## CJS 正式验真与写入前屏障

只修改 MAIN v2 分支，旧 MAIN v1/普通自动增量所有分支保持。新分支在浏览器创建前固定执行已经提交的 `main_program_current_installation.py --selection <固定本地文件名> --public-summary`，唯一 runtime 路径、参数数组、`shell:false/timeout:120000/maxBuffer:16MiB/windowsHide:true` 与已提交 `verify_goal_readonly` 的只读 CLI 合同一致。非零退出、超时、stderr、JSON/schema 不符全部拒绝，不接受外部 callback 或任意程序路径。

CLI 返回必须为原 `MainProgramCurrentInstallationSummary/v1` 精确字段；selection/source/spug/controlGeneration/spugInstallation 全匹配。先逐项重验 **全部 inputPins** 的绝对路径、无 alias/symlink、单链接、文件身份前后稳定、实际 bytes/SHA 及无重复，才读两 build。原 source buildPin 与 resourceBuildPin 必须在这一闭包中，不能以 gate 自述 PASS 代替验真。source generation 也按原 pin 读回并核其 buildPin/sourceCommit；两 build 的原字段/目录/commit 与 binding 精确一致。

`gate.gitDeploymentInputs` 精确三字段；bindings 精确 source/spug；每条 binding 字段固定、布尔值严格。原 component 证明的完整字段保留，scope 非空、规范、唯一，提交与自己 binding 一致。runtime 原 pin/JSON 必须为原 MAIN runtime v1/status PASS，同 selection，且 gitDeploymentInputs 与 gate 深度同值；两 build 的 component 原字段完整匹配。

当前 UI 主流程会在浏览器前、确认按钮前和最终 POST 路由的 durable receipt 写入前调用 `validateGate`。真实 CLI 每次约 84 秒，不能在已经开始的 UI 请求回调重复整套历史推导。因此仅在本次进程首次 v2 验证调用正式 CLI，成功后模块私有保留该**唯一精确 selection pin** 的已验证摘要/原件身份；后续同 selection 仍重新读取全部 inputPins、两 build、runtime、gate 和根证明。更换 selection、任一字节/身份变化或验证失败即拒绝；不重新挑代次、不保留失败缓存、不提供调用方注入证明接口。这样只复用已经完全核实且仍逐原件不变的推导结果，不省略最终写入前屏障；最终 parent 真正 CLI/preflight 验收独立执行。

## 影响文件与 BDD/TDD

仍为四文件：`prepare_main_program_ui_preflight.py`、`automatic_incremental_ui_acceptance.cjs`、新 `test_main_ui_deployment_root.py`、新 `main_ui_deployment_root.test.cjs`。独立 TDD 日志更新。其它消费者、dispatcher、旧五 reader/selector/history、共享 Git verifier 不改。

1. Given 临时真实 Git 的 source/Spug 两提交，app.js 确有不同、两个登记 worktree 各自 clean，When 默认或原单 root 门禁，Then 真实 scope 差异仍拒绝；When 显式两 root，Then 各自原完整 component PASS，保留不同 HEAD 和真实 build pin。
2. Given 仅一个参数、相对/缺失/别名/其它同 commit 目录、两目录互换，When 验证，Then 外部观察前拒绝；两参数都没有仍原默认逻辑。
3. Given 任一登记 root 的 staged/unstaged/untracked/错误 HEAD，或者在两次校验间发生变化，When 验证，Then 拒绝；source 与 Spug scope 均不可缩减。
4. Given 任一 build pin/完整对象/commit/worktree/文件闭合被改，When 验证，Then 拒绝，不能把 source 提交套给 Spug。
5. Given CJS 新 v2，When 正式固定 CLI 返回非零/错误 schema/未绑定 pin，或 inputPins 任一原文件变化，Then 浏览器前拒绝；单元测试只在明确 CLI 子进程协议边界提供数据，不称完整 loader/现场 PASS。
6. Given CLI 完整成功且其原件保持，When 首次读两 build/runtime，Then 两 component 各自闭合；When 第二次门禁，Then 不重复历史 CLI，但原件一字节变化仍拒绝，selection 切换拒绝，失败没有可用缓存。
7. Given 任一 binding 或 runtime/selection/build/head/布尔值缺失、错误或增加未知字段，When v2 消费，Then 拒绝；旧 v1 合同原测试保持。

RED 日志和真实 counts 先记录，再实现；有限回归包含原 Git 门禁、MAIN/普通 UI 合同和受影响 preflight。父另执行真实 dispatcher+真实双 root preflight，本子任务不运行远端或 UI。不得把临时 Git/CLI 协议测试写成真实用户验收。
