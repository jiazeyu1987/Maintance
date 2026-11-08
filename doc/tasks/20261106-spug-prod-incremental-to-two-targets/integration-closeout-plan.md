# 自动增量最终融合与收口方案

## Current Status
ready_for_review — 只读范围核验和PRIVATE三方候选已形成；实际融合尚未执行。当前仍需父任务审阅、最终真实验收及按现行门禁处理共享日志敏感历史和并行修改。本文件不宣告主任务completed，不操作主线、索引、分支或worktree，不执行stash/restore/clean/reset、提交或合并。

## 目标与里程碑
- M1：读取实际task/main HEAD、分支、index与tracked/untracked状态，固定共同base与精确incoming路径。
- M2：分别核已提交产品、本任务Nov6待提交记录、共享request-command-log的主线同路径覆盖风险；只对真实重叠给出处置。
- M3：如有3方冲突，仅在PRIVATE保留base/main/task原文和可审阅候选，元数据记录SHA；保持两边历史，不触碰实际工作区。

## 预期验证
读前读后HEAD/index身份一致；所有候选仅写PRIVATE；TASK仅新增方案及非敏感元数据。不能以全量dirty数量替代路径交集核验，不把候选当实际融合成功。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否；未确认归属、重叠或必要输入缺失明确记录阻塞。
- 是否从根因和长期维护角度解决：是；以精确路径、Git三方与已提交内容保护长期历史。
- 是否存在临时补丁或绕过：否；候选只用于审阅，未经父任务批准不融合。

## 经验门禁
- Trigger：共享主线有未提交文件且任务将最终融合。Preflight check：先读worktree-memory，固定HEAD/index、merge-base和incoming各路径的实际状态与SHA。Blocker：同路径改动归属不明、工作区与index无法保留、候选冲突未审。Verification：逐路径三方文本及候选结果与原字节pins，读前读后实际主线/index不变。Forbidden action：禁止全量复制、stash/clean/reset、隐含覆盖、直接以dirty总数推断重叠；本轮不建worktree、不提交合并。Evidence：本方案、只读快照和PRIVATE候选pins。

## BDD
- Given 主线存在大量无关dirty；When 精确计算incoming与主线tracked/untracked/index交集；Then 仅具体交集阻塞对应文件，无关路径不被改动或作为冲突假设。
- Given request-command-log及历史任务文档两边都有历史；When 在PRIVATE做三方预演；Then 保留双方原文和SHA，明确候选冲突及人工审阅策略，不回写任一真实工作区。

## 结论与精确范围

2026-11-07 18:56:21 UTC只读快照显示：主线dirty共有9949个路径，但本任务未来incoming与之精确重叠的只有`docs/request-command-log.md`，路径前缀冲突为0。77个已提交产品路径没有主线dirty覆盖风险；不能把9949个路径全部判成冲突，也不能因此清理或提交它们。

| 核验项 | 实际结果 |
| --- | --- |
| 主工作区 | `C:/Users/D01021/Documents/ChatGPT/Maintance`，分支`int_main` |
| 主线HEAD | `e2e89420851a57885f9c1ddf22ff1862916add83` |
| 本任务工作区 | `C:/Users/D01021/.codex/worktrees/spug-restore-targets/Maintance` |
| 任务分支与HEAD | `codex/spug-selectable-restore-targets-20261104`，`b5c8817de2b4cc5efdad566f0fb65fdabefcb8d8` |
| 共同base | `e1389aa621bc92bc2f2e02ebdbc249d3c3086808` |
| 分叉 | 主线独有2个提交，任务独有29个提交；目前不能直接fast-forward |
| 两边index | 暂存路径均0、均无index.lock；快照读前后HEAD/index SHA不变 |
| 主线dirty | 63个tracked、9886个untracked；原始路径清单仅存PRIVATE |
| 已提交incoming | 720路径，含77产品路径、643文档记录路径 |
| 本轮Nov6待提交 | 快照650路径；父任务仍产生真实记录，最终提交前必须重算 |
| 未来incoming并集 | 快照1370路径，包含共享日志；不能直接作为最终git add清单 |
| incoming与主线dirty交集 | 仅`docs/request-command-log.md`，主线状态` M` |
| 两边已提交内容的重叠 | 旧Nov4任务`execution-log.md`、`task.md`和共享日志，共3个文件 |

完整77产品路径、643已提交记录路径、主线独有提交和交集见`integration-readonly-scope.json`。本轮方案未检查全部主线dirty文件内容，亦未将无关文件复制到任务目录。

## 三方候选与保留策略

原始base/main HEAD/task HEAD/main工作区/task工作区字节均保存在PRIVATE：`C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/integration-review-20261108-r1`。`integration-three-way-review.json`记录每份原文的bytes/SHA；只在比较输入中严格UTF-8解码并统一CRLF/LF。旧Nov4两文件在共同base中不存在，已明确记录为add/add，没有构造不存在的历史。

| 路径 | PRIVATE候选 | 可审阅的语义依据 |
| --- | --- | --- |
| `doc/tasks/20261104-spug-selectable-restore-targets/execution-log.md` | `overlap-1-resolved-candidate.md` | 主线已提交全文是任务全文的精确前缀；保留任务全文可保全两边历史。不是未经比较的整文件theirs。 |
| `doc/tasks/20261104-spug-selectable-restore-targets/task.md` | `overlap-2-resolved-candidate.md` | 保留任务当前正文；追加明确标注日期、主线提交和原文SHA的完整主线历史引用。历史引用逐行去掉引用前缀后可还原主线全文；不把历史阻塞改写为成功。 |
| `docs/request-command-log.md` | `overlap-3-future-task-resolution-candidate.md` | 主线已提交的17行追加内容已全部存在于任务版本；保留任务待提交内容及既有历史脱敏修正，排除主线9行并行未提交记录。 |
| 融合后主线共享日志的预期工作区 | `overlap-3-future-main-worktree-candidate.md` | 将主线9行并行记录单独回放为未提交修改。真实`git merge-file --stdout`仅在PRIVATE运行，退出码0；从候选移除这9行后精确等于任务候选。 |

旧Nov4两文件工作区与各自HEAD的原始SHA不同仅因CRLF，规范换行后完全相同，不应误报为新增本地修改。共享日志9行确为内容插入，不能加入本任务提交。候选SHA和上述逐项断言见`integration-candidates.json`。

所有候选只是审阅材料，未回写真实文件。`overlap-3-committed-resolution-candidate.md`及原文副本可能保有既有敏感历史，只存PRIVATE，不得提交、公开全文或误当可发布版本。任务待提交候选和融合后工作区候选均保留已识别历史凭据的`[REDACTED]`处理；这只证明已识别这一处，不能替代最终敏感信息审查。

## 本任务待提交记录及排除项

Nov6快照650路径合计10,424,290字节，包含421 JSON、144 Python、34 PNG、32 Markdown、13 CJS及其它6项。这里包含尚在生成中的操作证明、测试、截图及helper，须按实际归属、最终真实状态、敏感信息和二进制必要性逐项审查后明确暂存，禁止直接`git add -A`或整目录无审查暂存。PRIVATE目录及其中原始响应、登录信息、三方原文不在提交范围。

任务工作区另有42个旧Nov4未跟踪文件，均不属于当前Nov6新增记录：39个规范换行后与主线已提交内容相同；`configure_main_controls.py`与主线不同；`resume-57-readonly.json`和`resume-59-readonly.json`不在主线HEAD。它们保持原样，暂不提交、不删除；后3项归属未确认，不得视作自动清理对象。逐项元数据见`integration-pending-scope.json`。

## 现行规则、审批边界与真实阻塞

本轮使用迁移后的现行`C:/SpugHandoff/release/repository/docs/worktree-memory.md`，SHA256为`2e14fe0af02258b46dc791f3107c2af08baebddfe7f6986ca91631b556703a60`；不是旧任务中保存的历史副本。PowerShell编码规则使用同目录`powershell-memory.md`，SHA256为`9aec95a50d513ec4d3c1be816df048ea2f71539db0aa690a6f3734995f6efd63`。

- worktree-memory第152行：同路径未提交或同路径未跟踪覆盖等情况“必须停止受保护融合；不得用 `git add -A`、stash、reset、checkout、clean 或删除未跟踪目录绕过保护。”本轮具体触发的是共享日志，不是其余无重叠的dirty路径。
- 第203行明确手工三方流程的条件：“用户明确授权手工三方融合并要求保留并行改动。”第204行要求只处理精确交集，非交集dirty不得进入stash、暂存区或任务提交。
- 第205行原文：“Blocker: 未取得用户明确授权、交集包含无法归属的未跟踪文件或敏感文件、任务分支未通过验证、路径级 stash 无法完整保存、stash apply 冲突无法语义保留双方修改、或恢复后无法证明并行改动仍在工作区时必须停止。”共享日志主线原文仍含已识别历史凭据，任务待提交版本已脱敏，因此不能把普通路径级stash当作当前已满足的执行方案。
- 第207行原文：“Forbidden action: 禁止全工作区 stash、整文件 `ours/theirs`、提交并行改动、直接 `update-ref` 移动已检出的脏 `int_main`、先删除重叠文件再 merge、或在未验证恢复结果前 drop stash。”
- 第484行要求最终合入前复核来源摘要，漂移则停止重建验证；第487—488行仍要求尊重最终closeout dirty guard，不能以此方案自行绕过。

因此，父任务最终审批须明确：三处候选的语义保留方式；共享日志9行并行记录继续留为未提交改动；已识别历史凭据的私密保全、脱敏和不新增敏感Git对象的处理范围。当前已获实现/服务器范围授权不自动等于手工处理dirty主线及敏感历史的授权。本轮没有发出许可请求，由父任务将完整结果交用户审阅后决定。

## 建议执行顺序（尚未执行）

1. 先完成自动FULL→I1→I2真实终态、三点原件审计与独立源恢复证明、最终READY计划，核58/59当前安装PASS、原历史原件不变、目录142包实际页面证明及当前稳定控制。失败原件和早期诊断保持不变；不能用候选或准备报告替代真实PASS。
2. 对本任务实现与Nov6记录分批做明确文件审查和所需验证。实现已提交内容与未来记录提交分开；不能在真实验收或融合仍未完成时写completed。共享日志保留脱敏而不包含主线9行并行记录；42项旧未跟踪资产仍排除。
3. 执行前重新只读记录两边HEAD、index、status NUL清单、incoming交集、每个候选输入SHA；当前快照是固定观察，不是持续锁。若父任务推进HEAD/新记录或其它主线变更，重新生成候选并复核，不强行沿用旧摘要。
4. 在父任务另行批准的隔离融合环境中将实际主线已提交基线语义合入实际任务提交，按三处候选解决文档冲突，并运行受影响测试与`git diff --check`；不把主线参考副本或其并行dirty作为输入提交。当前分叉下不能省略这一步直接移动主线。
5. 对敏感共享日志先完成上节明确审批的保全/脱敏处置，再采用符合现行门禁的精确交集保留流程。只允许处理`docs/request-command-log.md`，不触碰另外9948个当前无重叠dirty路径；若敏感文件阻塞仍未解除则保持融合阻塞，不执行普通stash或绕过guard。
6. 仅在实际授权与前置门禁全部通过后由父任务融合到int_main，验证旧主线与任务提交祖先关系、两边历史、9行并行记录仍为未提交、非交集dirty/index未被纳入，再跑融合后回归。没有验证前不得删除保存或任务工作区。
7. 10个构建worktree严格按`task-owned-builds.json`逐项证明归属和最终提交、生成新提交情况、依赖和稳定控制后收尾；本方案不添加任意扫描清理。当前开发worktree还有未融合提交、未确认旧文件和最终验证，不能删除。最终记录提交与completed状态必须在允许的融合/收尾完成后形成；若主线门禁未解除，如实维持ready_for_closeout并列明具体阻塞。

## 本轮验证与边界

- PASS：三处原文pins、显式不存在的base、规范换行身份、主线已提交历史完整保留、task正文完整保留及主线9行独立回放断言；回放使用真实本机git merge-file退出0。
- PASS：PRIVATE候选内已识别凭据脱敏保留；不输出秘密。未进行全仓凭据扫描，不能把此项扩展为所有记录可提交的证明。
- 本轮所有Git调用均只读，设置`GIT_OPTIONAL_LOCKS=0`；未创建worktree、未改真实Git索引、分支或主线文件，未stash/restore/clean/reset/提交/合并，未访问服务器或浏览器。
- M1/M2/M3准备完成；真实融合、目标验证、最终清理尚未执行。末次只读保护复核见`integration-final-readonly-verification.json`。
