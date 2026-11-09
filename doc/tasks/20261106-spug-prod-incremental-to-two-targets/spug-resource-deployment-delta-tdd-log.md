# Spug 资源安装差异 v2

## Current Status

ready_for_closeout（本机子阶段）；延续父 spug-resource-deployment-delta-plan.md。只修改 main_program_spug_resource_activation.py，新增专属测试与本记录；原 build/test 报告、publication、产品源码、旧失败和已有未提交修改不变。

## 目标与里程碑

1. 显式区分 Git 提交 changedFiles 与实际安装 deployment delta，不改原资源报告的语义。
2. BDD → RED → 最小 v2 实现 → GREEN → 原 v1 资源安装器及资源 reader 回归。
3. 只准备代码、编译与本机临时文件合同；现场 observation、安装、进程重载由父任务执行。

## 合同设计

- MainProgramSpugResourceActivationInputs/v2：schemaVersion/resourceBuildPin/deploymentDeltaPin/observationPin。
- MainProgramSpugResourceDeploymentDelta/v1：schemaVersion/sourceCommit/resourceBuildPin/changes。
- changes 必须有序、唯一且只有 smallapp_adapter.py、smallapp-ui/app.js、smallapp-ui/simple.js；每项 relativePath/beforePin/afterPin。pins 是同一 /opt/intruoyi-spug/ 绝对文件路径，before 与真实观察完全一致，after 与原构建相同。三项必须实际有差异，其余八项保持。
- 新观察和 attempt/rich/core 名称加 delta SHA 前12位隔离，旧 v1 名称/合同保持。v2 core 明确新版，不冒充旧单 adapter 成功。
- 写入前全部三原字节 O_EXCL 保全，随后逐文件原子替换。每步核本机11资源应有状态和所有输入 pins；失败按实际当前文件逐项报告 UNCHANGED/REPLACED/UNKNOWN，不自动重试或回滚。

## BDD

- Given 明确三文件 before/after 与已核11文件构建，When 默认 prepare，Then 无 Docker/transport/运行文件写入。
- Given 三文件精确差异与现场新鲜完整观察，When apply，Then 先保存三个原件，再替换三项、仅重载已证 entry，完整观察验证其余8、配置/连接、业务历史、容器/18081均保持。
- Given 缺pin、未知schema/字段、重复或越界路径、after不符构建、before不符观察或额外第4项差异，When prepare，Then 写前明确拒绝。
- Given 第二项替换失败、替换后回读失败或entry重载失败，When结束，Then 每文件据实际bytes记状态、保存全部原件和已发生的变化，不写成功core、不重试、不回滚。
- Given 完整只读观察失败或内容被拒绝，When observe，Then 保存真实失败诊断/已有响应，没有有效观察PASS或安装成功。
- Given v1只有adapter差异，Then旧调用仍通过；v1有两UI变化仍拒绝。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。显式v2、未知差异Fail Fast。
- 是否从根因和长期维护角度解决：是。部署差异独立于提交diff，固定 before/after 与真实现场证明。
- 是否存在临时补丁或绕过：否。所有旧11文件、154输入验证和完整观察继续执行，未改旧报告。

## 经验门禁

- Trigger：已提交资源与实际现网的差异跨越多次产品提交。
- Preflight check：父计划、精确三文件范围、原构建/test/私密观察、原配置与实例身份、全部原件保存。
- Blocker：额外差异、任一pin漂移、未知attempt、非原entry、观察/构建不完整。
- Verification：真实本机文件状态与失败边界测试、旧合同回归；fixture仅证明本机逻辑，不证明安装。
- Forbidden action：本Agent不服务器/浏览器/Docker/构建/真实安装/提交；不扩写publication或旧测试，不扫描PRIVATE。
- Evidence：本记录、父计划、固定原始日志与事前安装器私密字节副本。

## 实际 TDD 与回归

- RED：`python -X utf8 -B -m pytest -p no:cacheprovider TASK/test_main_program_spug_resource_deployment_delta.py -q --tb=short`，28项，10 failed / 18 passed，60.41s，exit1。v2尚不支持，观察被拒绝时原响应未保留；原错误原件不改。
- 第一轮 GREEN：同命令，26 passed / 2 failed，122.74s；所有三文件替换/第二replace/首次回读/第二receipt/reload边界均已通过。两处失败是新增测试将“所有观察输出只有失败原件”的集合断言方向写反，已修正为相等，未改旧测试或放宽产品断言；原日志保留。
- 新增三项边界回归：第3份原件保存失败必须零运行文件写入；当前bytes既非before也非after必须UNKNOWN；observer异常保存失败且只读一次，不重复现场观察。
- 最终 REGRESSION：`python -X utf8 -B -m pytest -p no:cacheprovider TASK/test_main_program_spug_resource_deployment_delta.py TASK/test_main_program_spug_resource_activation.py TASK/test_main_program_spug_publication.py -q --tb=short`，209 passed，187.49s，exit0，0 skipped。新测试31项，原安装器与publication合同178项。
- Python为 `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`，PYTHONPATH=PRIVATE/test-dependencies，PYTHONDONTWRITEBYTECODE=1。TASK 在实际命令中展开为本任务相对路径。
- 两实现/测试源读取raw bytes compile通过，无pyc。原安装器测试未修改；既有resource fixture在自身临时目录创建独立Git并执行小型真实pytest证明，这是本机合同测试，不是工作区提交、正式构建或现场证明。没有Docker/服务器/浏览器/实际安装/观察调用。

## 差异与原件保全审查

事前安装器完整副本为 PRIVATE/spug-resource-deployment-delta-baseline-20261109T190643245972Z.private.py，23384B、SHA69daad3fdecc53a0a304d99be63f5a49ce253083210077369d152c430b5e88c3。原安装器/原测试未跟踪，因此明确使用该raw字节私密副本作no-index比较，不把git diff空当作未变。

原函数AST变化仅 validate_observation、prepare、expected_after、dispatch_prepared入口显式v2分派、run_request观察证据。新增 validate_deployment_delta、delta_suffix、delta_file_states、check_delta_runtime、replace_archived、observe_with_evidence、dispatch_delta；无删除原函数。原v1 dispatch主体和 ActualTransport、process_identity、reload_program、OBSERVE_PROGRAM、HELPERS保持；900秒完整observer预算、240秒其余调用、原entry精确重载、真实目录及历史路径验证保持。

publication.py仍82950B SHAec4ca9f834332ef3b235c731f401b1c6435a49f08d2117be1acce1c35616aaae；spug-resource-build-c7728ad.json仍2351B SHA659ae1f24bbb7f110a58c67b11618dfcda18e7104b65517b692f536388a47368；原spug-resource-validation-c7728ad.json仍19002B SHA21ea75038aee1bc22390ebdbf79c65df6f49c3ff6cfb8b4dd2a06197b767b298。

父任务实际公开delta及observe输入只读传入 validate_deployment_delta：PASS，不调用prepare/observe/apply。原11候选文件、154测试输入/构建proof仍由现有publication.validate_resource_build严格检查，changedFiles依旧只有单次提交的adapter，不被改成部署差异。

## 实际使用与证据合同

- 父构造的 MainProgramSpugResourceActivationInputs/v2 与 DeploymentDelta/v1 已按设计接受；缺任何pin或额外路径均写前拒绝。默认调用没有transport。显式 `--observe` 允许observationPin=null；完整观察只有通过所有原门禁与三文件before校验后才独占写有效原件。
- v2 stem：`main-program-spug-resource-activation-<commit7>-delta-<deltaSha12>`；observe stem同前缀`main-program-spug-resource-observation-...`。以父838ac378... delta为例，后缀为`-delta-838ac378a3e9`。新名字隔离旧失败，不覆盖任何原输出。
- 有效 observation 仍用原严格 MainProgramSpugResourceActivationObservation/v1 内容，不伪造现场新版本；v2输入通过其deploymentDeltaPin决定允许的精确before三项。其余8资源、三配置/连接、原模块/凭据、历史/台账、任务、容器及18081均继续核验。
- 观察失败：独立 `.failure-<UUID>.private.json`，MainProgramSpugResourceObservationFailure/v1、status FAILED、rawObservation真实返回值（transport抛错时null）、原errorType/errorCode、validObservation=false、installationAttempted=false。只调用observe一次、重抛原错误，不能用该文件替代有效观察。
- apply先新鲜完整观察相等，再attempt；先把全部三before原字节保存为audit内0-before.py/1-before.js/2-before.js并逐项核验，再写originals.json，随后才允许第一次运行文件os.replace。每步前核11资源预期状态与全部inputPins、所有原件。
- 每项replacement保存relativePath/previousPin/installedPin；rich的fileStates按实际磁盘独立读取，每项relativePath/state/currentPin，state仅UNCHANGED、REPLACED或UNKNOWN。原子替换成功但回读/receipt失败时，仍按当前字节报告REPLACED；未知字节/读取失败不可称未修改。
- 新成功core仅MainProgramSpugResourceActivation/v2，绑定resourceBuildPin/deploymentDeltaPin/observationPin、前后entryPid、三replacements、oldResourcesPreserved/otherEightResourcesUnchanged/settingsAndConnectionsUnchanged/originalBehaviorVerified/protectedSpugUnchanged，禁止sharedServiceRestarted/backupDispatched/restoreDispatched。只写真实通过的core；失败保留rich原件、运行字节和待处理staged，不自动重试/回滚。
- 三文件替换完成后仅按原精确entry身份重载，完整after观察须等于预期（新entry PID/startTicks和三资源，其余字段完全不变）。若失败，禁止新attempt重试，父另行审查现场状态。

## 冻结与尚待真实门禁

ready_for_closeout（本机部署差异实现子阶段）。父任务还需独立复核新增31项、限定提交、完整新鲜现场观察、经验preflight、正式三文件安装和entry重载、真实页面/历史矩阵验证。此处未安装、未调用现场，也未宣称用户总任务完成。

```json
{
  "observedAt": "2026-11-09T19:20:22.418915+00:00",
  "sourcePins": [
    {
      "path": "C:\\Users\\D01021\\.codex\\worktrees\\spug-restore-targets\\Maintance\\doc\\tasks\\20261106-spug-prod-incremental-to-two-targets\\main_program_spug_resource_activation.py",
      "bytes": 35407,
      "sha256": "979c3d6055b97e3552bce1cc5381f0f20a2bcd2cfedb027c4c634775b0672b20"
    },
    {
      "path": "C:\\Users\\D01021\\.codex\\worktrees\\spug-restore-targets\\Maintance\\doc\\tasks\\20261106-spug-prod-incremental-to-two-targets\\test_main_program_spug_resource_activation.py",
      "bytes": 27555,
      "sha256": "4338df67a8021b0952408bd7772d4864490ef4fa369c2c0241c2792f2041a3c3"
    },
    {
      "path": "C:\\Users\\D01021\\.codex\\worktrees\\spug-restore-targets\\Maintance\\doc\\tasks\\20261106-spug-prod-incremental-to-two-targets\\test_main_program_spug_resource_deployment_delta.py",
      "bytes": 15022,
      "sha256": "827845c343f8dde15a8b9370eef3f8c8f604ea42298c592995efdaf1a3da739e"
    }
  ],
  "logPins": [
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\spug-resource-delta-red-1.log",
      "bytes": 11552,
      "sha256": "735bab99f466ede9c37eb70d05b498c9b4e6c89f3cff393a729bc643c43cfad1"
    },
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\spug-resource-delta-green-1.log",
      "bytes": 1674,
      "sha256": "6dec31e5c9f2eff1b2a60f61ceef21556636987c10f41d69e60a58dc7d4642d2"
    },
    {
      "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\spug-resource-delta-final-regression.log",
      "bytes": 276,
      "sha256": "a1fe2ff722a52d0a6f75c8c71d5d65eeb56e3b795aa425dd8098402d8c4a2ac0"
    }
  ],
  "baseline": {
    "path": "C:\\Spug\\runtime\\private\\prod-incremental-to-two-targets-20261106\\spug-resource-deployment-delta-baseline-20261109T190643245972Z.private.py",
    "bytes": 23384,
    "sha256": "69daad3fdecc53a0a304d99be63f5a49ce253083210077369d152c430b5e88c3"
  }
}
```

## 父独立验证
GREEN: 缓存Python -X utf8 -B -m pytest -q -p no:cacheprovider test_main_program_spug_resource_deployment_delta.py -> 31 PASS，0 skip，exit0，121.109秒。四项源码/测试输入前后SHA一致。原始日志PRIVATE/spug-resource-delta-parent-green-r1.log 113 B，SHAac9ac995a86bb9a708abaedf73f3a901d851eebdf4e8fb71a8eb9fc361e8e415；报告spug-resource-delta-parent-validation-r1.json 2058 B，SHA2bc2dc5766173fba18edd458085ce2b3a680f4fa77668e6146863831a74aa1d9。与owner209项回归共同证明本机实现，未代表安装成功。
