# 控制代次 publication 与完整选择 v2 兼容

## Current Status

in_progress；已读父 control-generation-upgrade-plan.md / control-generation-upgrade-refactor-design.md，先私密保全当前三文件，再执行 BDD→RED→GREEN。旧未提交改动是基线的一部分，不重置或替换。

## 目标、范围与里程碑

1. 仅独占 main_program_spug_publication.py、main_program_installation_selection.py、observe_closeout_hosts.py 的显式 v2 分派，另新增专属测试和本记录。
2. 与 generation owner 冻结共享只读 loader，避免循环导入或重复弱化证明。
3. 新 publication 纯 prepare 显式绑定 sourceCommit/revisionId/controlGenerationPin/spugResourceBuildPin/publicationObservationPin/outputFile；build/plan/四控制由已核 generation 提供，不伪造前代 Spug 成功。
4. TaskMainProgramInstallations/v2 必须绑定同代真实 Spug 成功 core/rich 和已核控制代次；closeout 不能把 control-only 原件当完整安装。
5. BDD、真实本机临时文件与变动拒绝 RED/GREEN、旧 v1/899/r4 受影响回归、源 SHA 和完整差异检查后冻结。

## BDD

- Given 合法控制代次但没有真实 Spug 发布成功，When 读取完整安装 v2，Then 明确拒绝，不能伪造 full-installation。
- Given 精确同代控制原件和真实 Spug 成功 core/rich、资源与选择发布证据，When 显式 v2 读取，Then 返回原完整安装选择形状，并固定所有输入 pins。
- Given 输入缺件、revision/commit/plan/build/资源或发布证据跨代、未知schema/多余字段，When prepare 或完整选择读取，Then 本机 Fail Fast，无远程派发。
- Given 旧 v1/r4/899 成功或失败原件，When 原入口读取，Then 原合同保持，不扫描最新、不重写旧失败、不更改历史来源31执行路由、33应用/3任务及保护。
- Given 新版本远程前代门禁尚无受测实现，When 请求 apply，Then 明确拒绝，不借旧路径派发。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；显式 schema 分派，缺证明拒绝。
- 是否从根因和长期维护角度解决：是；控制代次与完整 Spug 发布独立建模，复用已核 loader 和原严格验证器。
- 是否存在临时补丁或绕过：否；不改 generation/custody/planner/activation/staging、共享文档或产品源码，不伪造旧成功。

## 经验门禁

- Trigger：控制已升级、Spug 尚未发布，需要严格 v2 兼容。
- Preflight check：父设计、原三脚本字节和未提交改动、精确generation公共API、旧失败及历史原件门禁。
- Blocker：未知代次或隐式latest；控制激活冒充完整发布；未实现远程前代门禁；跨代资源/观察证据。
- Verification：本机真实临时文件/pin及变动拒绝测试，RED→GREEN、旧合同回归；不把 fixture 结果当现场证明。
- Forbidden action：无服务器/Docker/浏览器/构建/提交/实际新选择或成功原件/wrapper执行；不得重写旧证据。
- Evidence：父两计划、本记录、专属测试及原文件私密快照。适用经验索引的包清单身份、自动增量链、多机器接管与AST载体门禁继续保持。

## 事前原字节与私密保全

2026-11-09T15:40:49.869781+00:00

```json
[
  {
    "file": "main_program_spug_publication.py",
    "bytes": 68318,
    "sha256": "8ca1260597155ab7f10346e193d26e99b0964d0c81e1702b3b29e44aee1eedc1",
    "privateBaseline": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\control-generation-ui-v2-baseline-20261109T154049869781Z\\main_program_spug_publication.py"
  },
  {
    "file": "main_program_installation_selection.py",
    "bytes": 12796,
    "sha256": "8b758212b09eec8c20e44c4604e47aac2ac873146125c52339f2b1940d26e176",
    "privateBaseline": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\control-generation-ui-v2-baseline-20261109T154049869781Z\\main_program_installation_selection.py"
  },
  {
    "file": "observe_closeout_hosts.py",
    "bytes": 16087,
    "sha256": "6395e6bdd209fb47f2d6a0f192321102cc3f1abbb3d4b33b0ff50fb5157fca70",
    "privateBaseline": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\control-generation-ui-v2-baseline-20261109T154049869781Z\\observe_closeout_hosts.py"
  }
]
```

三份副本均以独占新目录/文件写入并逐字节核对，不含任何 Git 写入。

## RED → GREEN → REGRESSION 实际证据

- RED：`python -X utf8 -B -m pytest -p no:cacheprovider TASK/test_main_program_publication_v2.py -q --tb=short`，42 项：36 failed / 6 passed，81.73s。失败是缺 v2/private 分派及无独立远程阻断，未修改旧断言。
- 第一轮 GREEN 探索中因完整 reader 对每个反例重复核资源 checkout，主动结束该本机测试；未把它记为通过，最终已确认无残留该 pytest 进程。随后明确分离 prepare 与已发布历史读取合同：prepare 仍核真实 HEAD/clean/测试输入/包资源；完整 reader 核固定 build/test/log 与实际 11 资源 pins 的同代阶段原件，不能要求将来必须删除的临时构建目录一直存在。
- GREEN 第二轮：41 passed / 1 failed，78.42s；缺观察文件抛底层 FileNotFoundError，修为明确 V2_PRIVATE_ORIGINAL_REQUIRED。该失败保留。
- GREEN 第三轮：43 passed，85.94s。新增真实历史配置材料纯 prepare，31 原执行 routes、33 apps、3 tasks、6/3/3 selectors，默认无远程。
- 内容负例 RED：9 项，8 failed / 1 passed / 43 deselected，14.40s。逐项篡改 native 三来源、target、错误、points 或九格 bridge 内容，揭示单看布尔不能覆盖实际结果。
- 最终 GREEN：专属 52 passed，105.23s，exit 0，0 skipped。
- REGRESSION：`python -X utf8 -B -m pytest -p no:cacheprovider TASK/test_main_program_spug_publication.py TASK/test_main_program_installation_selection.py TASK/test_closeout_host_snapshot.py TASK/test_main_program_control_generation.py -q --tb=short`，260 passed，48.17s，exit 0，0 skipped。
- 解释器均为 `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`；PYTHONPATH 为 PRIVATE/test-dependencies，PYTHONDONTWRITEBYTECODE=1。TASK 在实际命令中展开为本任务相对路径。
- 对三脚本和专属测试执行 Python compile(raw bytes)：PASS；不会写 pyc。
- 新测试使用真实临时文件和 pins；generation 的 coverage/pure-planner 材料 seam 明示继承独立 generation suite，并不是构建、安装或现场证明。真实 r4 规划器和获批历史模板只读使用，原件不改；资源证据引用已存在的实际 c7728ad 构建/96 项验证与原始日志，不生成假测试日志。不调用 server/browser/Docker/Git 写入。

## 差异审查

基于事前私密完整字节，原函数 AST 变化仅 publication 的 prepare/project_core/dispatch_prepared、完整选择 select_main_program_installation、主机选择 controller_selection；没有删除原函数。publication 的尾部配置图抽为共享 _prepare_publication_graph，v1 门禁和返回形状保留。原 HOST_BODY / SPUG_BODY 字符串逐字节相等；原 activation/r2 失败保全与历史 routes/settings/resource 验证函数 AST 未改。只显式 v2 分支使用 generation loader，不扫描 latest，不修改原 schema 或任何已有成功/失败回执。

## 冻结合同及后续真实 publisher 输入闭包

1. `MainProgramSpugPublicationInputs/v2` 精确字段：schemaVersion/sourceCommit/revisionId/controlGenerationPin/spugResourceBuildPin/publicationObservationPin/outputFile；输出名 `main-program-spug-installation-<commit7>-<revision>.json`。generation loader 提供已核 build/plan/四 core/rich、控制配置图、目标、历史链；仅显式新 v2 plan 与精确 revision，初始 r4 不隐式兼容成新代。
2. 私密 `MainProgramSpugPublicationObservation/v2` 精确字段：schemaVersion/sourceCommit/revisionId/controlGenerationPin/spugResourceBuildPin/selectorsByHost/hostPreservationByHost/spug。shared prepare 继续验证原 selector 观察、全部业务容器/fstab/mounts、Spug 精确容器/PID、原设置和所有 connection pins、11 资源字节；源31条 dispatch/query/fingerprint 保持。
3. 公开 full core 继续严格 `MainProgramSpugInstallation/v1`，buildPin/planPin 来自本代 generation。完整选择 `TaskMainProgramInstallations/v2` 只收 schemaVersion/sourceCommit/controlGenerationPin/spugInstallationPin。
4. 私密 `MainProgramSpugPublicationEvidence/v2` 固定绑定 sourceCommit/revisionId/controlGenerationPin/spugResourceBuildPin/publicationObservationPin/publicationInputsPin，另 status=PASS/stage=complete/resourceSourceCommit/stages/selectorCount12/applicationCount33/taskCount3/backupDispatched=false/restoreDispatched=false 和原 TRUE_CHECKS 全 true。
5. stages 精确有序 12 项：每 phase preflight→publish→verify，依次 host57/58/59/spug；每项只有 stage/resultPin。每个独立私密原件 `MainProgramSpugPublicationStage/v2` 只有 schemaVersion/stage/result 与上述六个 binding 字段。每个 raw result 必须真实 PASS/phase/sourceCommit/零备份恢复。host verify 还需真实 host、完整本代 controllers、selectorCount 6/3/3、原保护 flags 和每控制 nativeSelections 三来源准入；spug verify 还需九格 bridgeSelections、33/3、原保护 flags、11 个实际 productPins 精确等于 build 与 observation。
6. rich、inputs、generation、core、observation、build/test/raw log、12 stages 全部固定 pins 并在读取完成重核。prepare 仍检查真实资源构建 checkout 干净；历史读取仅核实际成功的同代证据，不把 checkout 存在当安装事实。
7. 本阶段 `remotePublicationSupported=False`；v2 apply 在 attempt 文件创建/transport 之前 `V2_REMOTE_PUBLICATION_NOT_IMPLEMENTED`。这是 reader/prepare 子阶段交付，**不是完整发布能力或最终任务完成**。下一阶段需新独立真实 v2 publisher，以现场输出生成 12 原件并复用完整保护流程，父任务负责实际运行。

## 冻结状态

本阶段实现及必要本机验证通过；尚未提交、部署或生成实际新成功安装选择。父任务继续整体流程，当前不宣称本任务 completed。以下源文件与原始日志是当前冻结证据。

```json
{
  "observedAt": "2026-11-09T16:24:21.327069+00:00",
  "sourcePins": [
    {
      "path": "C:\\Users\\D01021\\.codex\\worktrees\\spug-restore-targets\\Maintance\\doc\\tasks\\20261106-spug-prod-incremental-to-two-targets\\main_program_spug_publication.py",
      "bytes": 82950,
      "sha256": "ec4ca9f834332ef3b235c731f401b1c6435a49f08d2117be1acce1c35616aaae"
    },
    {
      "path": "C:\\Users\\D01021\\.codex\\worktrees\\spug-restore-targets\\Maintance\\doc\\tasks\\20261106-spug-prod-incremental-to-two-targets\\main_program_installation_selection.py",
      "bytes": 14007,
      "sha256": "f663ab53ae810b115fb418062e162d0a592349d7081fb59adcf191d5e4488966"
    },
    {
      "path": "C:\\Users\\D01021\\.codex\\worktrees\\spug-restore-targets\\Maintance\\doc\\tasks\\20261106-spug-prod-incremental-to-two-targets\\observe_closeout_hosts.py",
      "bytes": 16288,
      "sha256": "61d320d245c000c19c692d57a9e5cf15c257b38f411b36c72084d1889825f7a4"
    },
    {
      "path": "C:\\Users\\D01021\\.codex\\worktrees\\spug-restore-targets\\Maintance\\doc\\tasks\\20261106-spug-prod-incremental-to-two-targets\\test_main_program_publication_v2.py",
      "bytes": 17902,
      "sha256": "f90eb908bb0029538006ce45df7dd50c03da1b0c0b4b6c5ab8bba0c2bbe6525e"
    }
  ],
  "logPins": [
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\publication-v2-red-1.log",
      "bytes": 29046,
      "sha256": "8aadca8bbad6aa1e6bd26d138c2349caf0b62c53f6fb6be22f238607515e225c"
    },
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\publication-v2-green-2.log",
      "bytes": 1993,
      "sha256": "1af7fc3ef918dae6b330bd642ece8cccd5551b43b0d6ab9345bbd029b4ce4030"
    },
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\publication-v2-green-3.log",
      "bytes": 112,
      "sha256": "aa920028f3b034dfa94f37eccf45a542e99eff4480d6b4622137ed258992fa1e"
    },
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\publication-v2-content-red-1.log",
      "bytes": 4559,
      "sha256": "7e806a1eef3d84314a82c3df7cfdf063366d15bd72c480f89c961dc002ef76f3"
    },
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\publication-v2-green-final.log",
      "bytes": 113,
      "sha256": "fe1530714e114662714d758b0cf4303f08f126b56d9ee45d2f8f7fd4a755ff00"
    },
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\publication-v2-regression-1.log",
      "bytes": 346,
      "sha256": "aefcb90dc0afe86a6b10a691e72b9a871bd75d3ccc279eb8305bc2b7e431cd91"
    }
  ]
}
```
