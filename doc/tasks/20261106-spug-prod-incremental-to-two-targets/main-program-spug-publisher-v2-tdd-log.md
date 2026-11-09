# 真实 v2 Spug 发布器独立阶段

## Current Status

in_progress；父任务已批准下一阶段，reader/prepare 五文件保持冻结。本阶段只新增 main_program_spug_publication_v2.py、test_main_program_spug_publisher_v2.py 和本记录；不运行服务器、浏览器、Docker、构建、Git 写入或真实发布 wrapper。

## 目标与里程碑

1. 复用已测严格 v2 prepare、原 HOST_PROGRAM/SPUG_PROGRAM 全部实际门禁和十二步发布顺序。
2. 独立脚本默认 prepare-only；仅明确 --apply 允许 transport。实际运行由父任务完成。
3. 每阶段先独占写请求回执，再真实派发一次，立即独占保存原始阶段结果；异常不重试、不覆盖历史失败。
4. 只有十二阶段全部真实通过、全部输入 pins 保持、完整 proof 可读验证后，才生成公开 core。完整选择仍由父任务另行创建。
5. BDD → RED → GREEN → 受影响回归、compile、差异与冻结 SHA。

## BDD

- Given v2 已核准备图，When 默认调用，Then 无 transport、无成功或尝试文件。
- Given 明确 apply 与真实 transport，When 十二步依次成功，Then 所有 preflight 先于任何 publish，stage 原件固定 source/代次/输入/资源/观察 pins；host verify 返回实际控制身份和三来源、Spug verify 返回实际十一资源与九格组合。
- Given 任一阶段失败、超时、结果错代、输入漂移或原件已存在，When 执行，Then 立即停止，无后续派发，无公开成功 core，保留已受理阶段回执；绝不自动重试。
- Given 伪造 prepared 或跳过真实 prepare，When CLI/apply，Then 严格准备与 pins 门禁不能绕过；测试注入 transport 仅验证本机编排，不声称实际安装。
- Given 原 HOST_PROGRAM/SPUG_PROGRAM，When 新载体生成，Then 不删除或改写旧保护代码；包字节、锁、真实 Native、原配置与历史 paths、业务容器/fstab/mounts、33 apps/3 tasks/31 routes 均仍由原程序执行。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；遇未知状态保留原件停止，不重试或推断成功。
- 是否从根因和长期维护角度解决：是；将发布编排与已完成历史 reader 分离，复用严格准备和真实保护程序；每阶段显式不可变证据。
- 是否存在临时补丁或绕过：否；不改冻结 reader、旧 v1、生产或其他 Agent 文件。

## 经验门禁

- Trigger：新控制代次已经激活，需要发布 selectors/Spug 设置。
- Preflight check：同代 generation/build/plan/四控制/rich、独立资源11文件、精确现场观察与原路径、历史失败保全；真实执行前父任务另记 experience-preflight。
- Blocker：缺任何实际前置、并行任务或锁、旧失败未处理、输入漂移、阶段未知结果、实际 API/Native 不可用。
- Verification：本机编排和载体合同与实际 fixture 临时文件只能证明代码；父任务另做真实十二阶段、页面目标矩阵与只读验证。
- Forbidden action：本 Agent 不调用服务器/容器/页面/真实 wrapper，不写实际成功或选择，不重试、不改冻结文件或旧证据。
- Evidence：父设计、冻结 reader TDD、专属测试及原始 RED/GREEN/回归日志。

## RED → GREEN → REGRESSION

- RED：`python -X utf8 -B -m pytest -p no:cacheprovider TASK/test_main_program_spug_publisher_v2.py -q --tb=short`，20 failed，43.16s，exit 1；独立 publisher 模块尚未存在。
- GREEN：同命令，20 passed，155.06s，exit 0，0 skipped。
- 补充本机 final reader 拒绝保全、默认 CLI 无 apply 两项，真实验证现有门禁，不修改旧断言。
- 最终 REGRESSION：`python -X utf8 -B -m pytest -p no:cacheprovider TASK/test_main_program_spug_publisher_v2.py TASK/test_main_program_spug_publication.py TASK/test_main_program_installation_selection.py TASK/test_closeout_host_snapshot.py TASK/test_main_program_control_generation.py -q --tb=short`，282 passed，324.66s，exit 0，0 skipped。其中新独立 publisher 22 项，旧合同 260 项。
- 使用 `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`，PYTHONPATH=PRIVATE/test-dependencies，PYTHONDONTWRITEBYTECODE=1。TASK 在实际命令中为本任务相对路径。
- 两个新增 Python 源文件 compile(raw bytes) PASS，无 pyc。此前 reader 阶段 3 实现+测试+TDD 五个文件 raw SHA 均保持父已提交 e21db8f 时的原值。
- 测试真实创建本机临时文件/请求回执/原始结果 pins；Recorder 是明确的本机 transport 编排适配器，不证明服务器安装。默认请求使用已核真实历史模板/资源的纯 prepare；生成程序 AST 中包含完整同字节原 HOST_PROGRAM/SPUG_PROGRAM。没有服务器、Docker、浏览器、构建、Git 写入或实际发布。

## 正式接口与父任务调用

`main_program_spug_publication_v2.py --inputs <TASK 内明确 v2 输入文件名>` 默认只执行严格本机 prepare。只有父现场复核经验门禁、同代四控制真实成功与独立资源/现场观察之后，才可加 `--apply`。支持 `--task` / `--private` 显式根目录；禁止传测试 fixture 或依赖默认 latest。

新脚本没有生成 inputs 或现场观察。输入仍严格 MainProgramSpugPublicationInputs/v2，由冻结 prepare 解析；sourceCommit/revisionId/controlGenerationPin/spugResourceBuildPin/publicationObservationPin/outputFile 全显式。缺实际新 generation、coverage、资源或现场观察则准备拒绝，不执行 transport。

正式顺序保持：host57/58/59 + Spug 全部 preflight → host57/58/59 + Spug publish → host57/58/59 + Spug verify。每个阶段的请求和完整私密程序先 O_EXCL+fsync 落盘，之后仅派发一次。auditPath 在 commit 隔离上再加明确 revision，避免与旧失败目录同名；不改原私密文件、selector 或旧历史 guard 程序字节。

真实生成载体在独立 namespace 执行原 HOST_PROGRAM/SPUG_PROGRAM，捕获原唯一 JSON 输出，仍运行全部原保护。仅当原 verify 真实 PASS 时，host 再运行实际 verify_controls 并返回控制身份；Spug 再读取 11 个文件的真实 pins。原 nativeSelections 和九格 bridgeSelections 不由本地推造。父 transport 继续复用 ActualTransport 的精确主机/18080 容器/18081 保全和实际前后观察。

## 不可变回执与收口

- 公共 core：inputs.outputFile，仅十二阶段通过、全部输入 pins 未漂移、严格完整 reader 验证后 O_EXCL 写入。
- 私密 attempt：`<output-stem>.attempt.private.json`，真实 inputPins、十二阶段顺序、retryPermitted=false。
- 每阶段三个原件：`<stem>.<stage>.program.private.py`、`.request.private.json`、`.private.json`；request 绑定程序 pin，result 绑定 source/代次/输入/资源/观察的六个原件字段。程序包含私密配置，必须留 PRIVATE，不纳入 Git。
- 聚合 rich：`<stem>.private.json`。原阶段失败/未知时状态 FAILED，保留已派发阶段 refs。超时阶段 raw status=UNKNOWN，不将未知包装成 accepted:false 或成功，不自动重试。
- 若十二阶段真实返回 PASS，但本机最终 reader 拒绝，则保留这些实际阶段原件和聚合阶段证据，并新增 `<stem>.finalization-failure.private.json`；公开 core 不生成。聚合阶段 PASS 不能替代公开完整 core；完整选择 reader 仍拒绝。
- 最终 core 先在内存中做投影，由 PendingCoreRecords 仅为这一个尚未发布的投影提供读取；其余 generation/build/input/观察/12阶段必须读取真实 pins。未写任何虚构公共安装或选择，也没有临时伪造前代成功。
- 所有后续 --apply 遇 attempt、结果、程序、request 任一原件即拒绝 V2_ATTEMPT_EXISTS，不能重试覆盖。若现场需要 finalization 续办，必须另立显式只消费原成功12阶段原件+重复全部必要当前只读验证的计划/合同；当前无盲 resume 或重发 publish 入口。

## 尚需父任务完成的实际门禁

本机代码阶段验证通过，实际发布未执行、未生成现场成功或新完整选择。父任务还需实际新代四控制成功、同代资源与观察、经验 preflight、十二阶段正式发布、真实页面全矩阵与稳定控制/收尾。共享 generation successor 的覆盖/纯规划验证是否依赖待删除控制构建 checkout，已提醒 generation owner 和父任务独立处理；本脚本不放宽其门禁。资源完整 reader 已区分准备 checkout 与已发布原件，不能以构建目录现存代替实际安装事实。

## 冻结

ready_for_closeout（仅本机独立 publisher 实现子阶段，父整体任务仍待真实发布/融合/清理）；没有提交或操作运行环境。

```json
{
  "observedAt": "2026-11-09T16:47:10.972345+00:00",
  "sourcePins": [
    {
      "path": "C:\\Users\\D01021\\.codex\\worktrees\\spug-restore-targets\\Maintance\\doc\\tasks\\20261106-spug-prod-incremental-to-two-targets\\main_program_spug_publication_v2.py",
      "bytes": 12313,
      "sha256": "0915b324db982f1213289a35a8148833f69c141fa080d91671fee00696eb37fa"
    },
    {
      "path": "C:\\Users\\D01021\\.codex\\worktrees\\spug-restore-targets\\Maintance\\doc\\tasks\\20261106-spug-prod-incremental-to-two-targets\\test_main_program_spug_publisher_v2.py",
      "bytes": 9427,
      "sha256": "972bf9853d66bf800acfb67c44c8f0d6f40939c526a780699298a3458ad829fb"
    }
  ],
  "logPins": [
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\spug-publisher-v2-red-1.log",
      "bytes": 23690,
      "sha256": "f66bdf9e221b5aaaab6fa94b5b35be14fc49573b86f566b10549a48f95ebc2d9"
    },
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\spug-publisher-v2-green-1.log",
      "bytes": 113,
      "sha256": "e09229e5cc5357dae3d3bc621696e421b6b2e306c58448168f275ac91c9f013e"
    },
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\spug-publisher-v2-final-regression.log",
      "bytes": 357,
      "sha256": "2191082d07362db03d5eb9628b7142ad1dec6aaf68131b58375d2005ab27a22c"
    }
  ]
}
```
