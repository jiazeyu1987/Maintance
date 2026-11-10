# MAIN UI 预检显式部署源码根目录设计

## Current Status

design_review。父任务要求只读评估，现有八个源码/测试继续冻结，等待父实现提交后再决定实施；不执行测试、UI、远端或构建。上一消费者接入子阶段本机验证完成，父复核 Python29与JS59通过并已取得真实六阶段 r7 acceptance PASS；本阶段处理当前开发 worktree 与实际已安装提交的证明归属。

## 目标、里程碑与预期验证

1. 只读核 `verify_stage_deployment_inputs` 的完整门禁及 source build 原 worktree/commit字段。
2. 设计显式部署根目录选择和证据绑定，保持原scope完整比较，不把未提交开发代码视为已安装代码。
3. 给父最小影响文件、BDD/后续RED验证建议；本阶段不实现。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。显式参数必须与正式build回执绑定；未知、缺失或漂移必须拒绝，不自动找clean目录。
- 是否从根因和长期维护角度解决：是。开发目录与已提交构建源码属于不同对象，选择目录后仍执行原完整源码/Spug校验。
- 是否存在临时补丁或绕过：否。不得monkeypatch、排除scope或宣称dirty内容已经安装。

## 经验门禁

- Trigger：MAIN真实UI预检、干净发布worktree、已安装提交与开发目录脏改动分离。
- Preflight check：读取正式build目标commit/worktree、现有源码范围算法和运行证据消费者；明确参数绑定及最终证据目录。
- Blocker：路径不是正式构建worktree、目标提交不符、目录别名/缺失、安装源码或Spug范围差异、原验真被跳过。
- Verification：后续实际独立临时Git仓库证明开发目录dirty不被误作安装输入，选中目录自身dirty/错误commit/错误pin仍失败；原完整验证函数不修改。
- Forbidden action：不改冻结源码，不隐式latest/fallback，不运行真实UI/远端，不构建新包。
- Evidence：父任务已证实实际安装仍为b5fa4c5且对应clean release worktree存在；下文记录只读源码事实与正式方案。

## 只读分析

1. `prepare_main_program_ui_preflight.main` 当前直接调用 `verify_stage_deployment_inputs(TASK.parents[2], selection.sourceCommit, resourceBuild.sourceCommit, resourceBuild.files)`。该目录是正在开发的维护仓工作区；错误不在scope算法，而是被观察源码对象选错。
2. 原 `verify_deployment_inputs` 严格核installed commit存在、是HEAD祖先，并分别比较 installed→HEAD、installed→index、installed→worktree及scope内未跟踪文件；source scopes包含已安装 `ops/backup_engine/files.json` 所有映射、整个 `ops/backup_engine` 和 `ops/recovery`，Spug scopes取真实已安装resource build的全部文件。两个component必须同HEAD。**该函数及scope完全保持。**
3. 当前正式源build字段叫 **`worktree`**，不是 `releaseWorktree`：`release-build-b5fa4c5.json` 中为 `C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/release-chain-policy-b5fa4c5-20261110-r1`；`targetCommit=b5fa4c581f011f022cb9cde86a11b9b0ee0defd3`。build通过已验证generation的 `generation.buildPin` 读取，不能通过短提交拼文件名或猜新worktree。
4. 新dispatcher的已验bundle已含 `generation.buildPin`、`build` 和全部1630物理pins，足够绑定这一选择，不需要更改dispatcher或控制包。父已报告当前新selector及独立CLI完整通过；本阶段没有重跑这些验收。
5. 实际 MAIN UI 消费器为 `automatic_incremental_ui_acceptance.cjs.validateMainDeploymentContract`。它目前核commit与installation pins，但没有使用 `gitDeploymentInputs`；普通自动增量v2分支另有source/spug检查。最终只读 `verify_goal_readonly.cjs` 不消费preflight或git目录，本次无需给它新参数。

## 最小正式方案

在 `prepare_main_program_ui_preflight.py` 增加显式可选参数 `--deployment-root ABSOLUTE_PATH`。**不传参数时保留原开发目录和原全部门禁**，不自动尝试build.worktree、其它clean目录或最新checkout。传参数时只允许本次已安装源build原 `worktree`，不接受其它恰好有相同commit的clone。

建议同文件纯本机函数：

`verify_main_deployment_inputs(verified, default_root, *, deployment_root=None) -> dict`

没有传参：原样调用当前 `verify_stage_deployment_inputs(default_root, ...)`，返回原source/spug对象；无额外fallback。

明确传参时：

1. 从 `verified.generation.generation.buildPin` 取原pin，通过 `BoundDocuments(..., verified.inputPins).read(buildPin)` 重新读原build，须完整对象等于bundle.build。核 `status=PASS`、`targetCommit=selection.sourceCommit`、`allFilesShaAndCompileVerified=true`、明确 `worktree`；不新增猜测字段。
2. 输入和登记目录都必须为存在的绝对目录；拒绝叶symlink/junction及路径解析后不同对象；规范化Windows分隔符后比较实际同一个原登记目录，不能用大小写/分隔符处理放宽到父目录。核 `git rev-parse --show-toplevel` 正是该目录、HEAD精确等于原 `targetCommit`；不因原函数允许无关后续提交而将另一代HEAD当原构建worktree。
3. 只读 `git status --porcelain=v1 --untracked-files=all` 必须空，证明这个显式**构建worktree**仍干净；不扩大默认开发目录的原合同。只使用参数数组、`GIT_OPTIONAL_LOCKS=0`、原30秒期限，不运行checkout/reset/clean或任何Git写操作。
4. 在这个同一目录执行**原封不动**的 `verify_stage_deployment_inputs`，两个component仍分别用实际source b5和Spug565 commit及完整真实文件scope。若Spug565内容在b5对应范围确有差异，同样阻断，不把source提交当Spug提交。
5. HEAD/根身份/clean状态在检查后再次读取并与检查前完全相同；build pin和原闭包重验。建议在真实source/Spug只读观察结束、写gate之前再运行同一个函数并要求整个返回证据相等，避免预检过程中修改所选源码而漏过。
6. 排序为完整installation loader→本机deployment-root/source+Spug校验→原Docker Spug观察→原远端source观察→同目录末次完整校验→写原件。显式错误路径在任何外部观察前失败。

返回保留 `source`、`spug` 原完整字段，并在**显式分支**加：

```json
{
  "deploymentRootBinding": {
    "schemaVersion": "MainProgramDeploymentRoot/v1",
    "mode": "PINNED_BUILD_WORKTREE",
    "path": "<规范化绝对路径>",
    "buildPin": {"file": "<原build>", "bytes": 1, "sha256": "<原SHA>"},
    "targetCommit": "<已安装source 40位commit>",
    "headCommit": "<同targetCommit>",
    "registeredWorktreeMatched": true,
    "clean": true
  },
  "source": "<原完整验证对象>",
  "spug": "<原完整验证对象>"
}
```

此结构放入runtime证据和gate已有 `gitDeploymentInputs`，两处必须完全相同；不写入私密配置或未提交源码。示例bytes/SHA仅说明类型，实际必须原pin，不能据此制造现场proof。

## UI消费合同与兼容策略

推荐仅显式root分支生成 **`MainProgramAutomaticIncrementalUiPreflight/v2`**，默认分支继续v1。原因是原v1消费者完全不核git证明；如果同schema默默增加可删字段，UI仍可能忽略新合同。v2代表明确新证明合同，不改既有v1原件或旧selector schema。

`automatic_incremental_ui_acceptance.cjs` 不需要增加第二个 `--deployment-root` 参数，目录以已pin的preflight为唯一输入。其MAIN validator保持原v1逻辑；新v2额外严格核：

- `gitDeploymentInputs` 精确包含source/spug/deploymentRootBinding，后者固定字段及上面schema/mode；全部真值必须真实布尔值。
- 两component的installedCommit分别等gate的source/Spug commit，ancestor和inputsUnchanged为true，同head且head等binding.targetCommit/selection.sourceCommit；scope仍由producer原函数计算，不在CJS重造或缩减。
- 从已pin selector.controlGenerationPin读原generation，再读其buildPin，binding.buildPin必须精确相同；build.status/targetCommit/worktree与规范化binding.path严格一致。CJS不执行Git，也不接受第二个目录来源。
- 从gate.runtimeEvidencePin读原runtime，runtime.gitDeploymentInputs和gate值完全相同，并保持原runtime/deploymentSelection绑定；未知v2字段缺失/错误应在浏览器启动前失败。

新schema字段仅限MAIN gate；UI submission仍原v3、baseline仍原v1、selection仍原v4。`verify_goal_readonly.cjs` 与chain audit不使用这个Git目录，保持冻结。source/Spug runtime以及实际package验真不因目录选择发生变化。

## 最小影响文件（实施需父批准）

1. `prepare_main_program_ui_preflight.py`：可选参数、同文件纯本机绑定函数、检查次序/末次复核、显式v2 gate。
2. `automatic_incremental_ui_acceptance.cjs`：仅MAIN v2的root/build/runtime证明读取；旧v1和其它自动增量分支保持。
3. 新 `test_main_ui_deployment_root.py`：临时真实Git仓/worktree测试，无Git或完整验证函数mock；外部观察边界拒绝测试可用明确抛错sentinel，不能模拟业务成功。
4. 原MAIN UI合同测试或新独立CJS测试：v2证据有限参数拒绝、旧v1保持；先核其未被原attempt pin。原 `prepare_automatic_ui_preflight.py`、dispatcher、其它两个刚提交消费者、所有历史readers不改。

不建议新增通用repository选择平台、修改全局默认目录、复制原scope算法，或重新构建/安装b5包。

## BDD 与 RED→GREEN 验证计划（尚未执行）

1. Given实际独立Git repository及两个worktree，开发worktree在source scope有dirty改动，而build登记worktree精确targetCommit且clean，When显式选择后者，Then原完整source+Spug函数通过，证据准确记录后者，前者原dirty字节保持。
2. Given同场景不传参数，When预检，Then原 `AUTOMATIC_DEPLOYMENT_INPUTS_CHANGED` 继续拒绝，不能静默改用clean目录。
3. Given存在另一个同commit clean clone/错误目录/相对路径/缺失目录/别名，When显式选择，Then在外部观察前拒绝；不能仅凭commit相同通过。
4. Given登记worktree自己有source staged、unstaged、untracked、Spug文件变动或错误HEAD，When显式检查，Then各自拒绝，不减少source或Spug scope；root在两次检查间漂移也拒绝。
5. Givenbuild pin、targetCommit、worktree或bundle.build被替换，When读取绑定，Then原pin或完整对象比较拒绝，不能凭CLI路径获得新授权。
6. Given新v2gate缺/改root binding、build pin、source/spug commit、head或runtime同值关系，WhenUI合同读取，Then在浏览器创建前拒绝；旧v1行为保持。
7. Given真实已安装b5和565的原件，When父完成实现提交后运行新预检，Then唯有真实Git与运行态检查全部通过才产出新gate；本机临时Git测试不替代该实际验证。

## 当前结论

可以使用已登记的clean build worktree，不需要改原漂移算法、排除任何开发文件或构建新包。实现前只需父确认上述显式分支gate v2及对应最小CJS合同范围。本阶段仅写此设计，八个已提交源码/测试保持不变。
