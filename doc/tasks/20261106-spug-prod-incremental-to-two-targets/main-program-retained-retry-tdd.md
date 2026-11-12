# MAIN 准备失败的目标专用重试上下文

## Current Status

ready_for_closeout：目标专用 v2 合同、backend/package 及 opaque 原件读取已完成；27 项独立 Linux GREEN，391 项有限相邻回归全部 PASS，无 skip。产品和测试冻结，由父审查、精确提交及正式包认证；本子任务没有服务器操作、业务恢复或提交。57 的 0119156 已激活、58 仅暂存、59 未暂存均为原事实，不重写。实际后继安装与58恢复仍由父任务独立验收，不能将此处协议 PASS 当成现场成功。

## 目标、里程碑与验证

1. 已完成只读根因：正式 no-mutation clearance 不等于 source epoch READY；旧程序恢复只支持 READY 相邻起点。
2. 已完成：独立失败测试 → 最小 v2 helper/调用链 → 原 v1 与有限相邻回归。
3. 验证真实文件、原 Linux flock、完整旧 v1 native/custody/proof、消费记录及 v2 snapshot/bind/STARTED/effective/stage/FINISHED/final evidence。外部 SQL/Docker 仍为现有明确协议边界，不冒称服务器或业务恢复。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。调用目的必须显式；源 capture 和公共 generation resolver 仍仅接受 READY。v2 不能递归续办 v2 失败，本轮明确拒绝。
- 是否从根因和长期维护角度解决：是。真实成功前缀 readyEpoch 与本次失败起点 startEpoch 分离，以原 clearance、完整无写入证明和唯一消费绑定目标专用执行。
- 是否存在临时补丁或绕过：否。不修改原三条 epoch、FAILED、原配置、receipt 或锁，不伪造成功，不改变源备份健康规则。

## 经验门禁

- Trigger：PROGRAM_EPOCH_NOT_READY 且原准备失败已正式签发 no-mutation v2 clearance。
- Preflight check：docs/experience-index.md 命中的 release-agent-checklist.md「MAIN 准备失败无写入续办门禁」；原进程退出、完整 MainProgramEvidenceValidation、PREPARATION、无 generation/mutation/unknown、所有保护未安装、原资源释放与同点同目标 clearance 完整。
- Blocker：未知状态、过期、target/source/point/operation 漂移、消费给他人、原件变更、v2 前代均拒绝。不以布尔摘要代替原证明。
- Verification：先 RED，再最小 GREEN，真实 Linux 独立固定快照及 v1 回归；记录输入 SHA、计数、原期限和容器移除。安装、真实页面由父另验。
- Forbidden action：不手删 journal/active/claim、不把 FAILED 写成 READY、不让 source capture 接受失败、不重发旧 operation、不输出秘密。
- Evidence：原 preparation-target-epoch-r1.private.json SHA5f58741dd1fb9535278dc5c296d585cd2c772c99b621eaf3782ecbe880c6563d；原 original-preparation-clearance-r1.private.json SHA cbb194d50a3202b415c7099f50ac04684d61ce9001edcf0aac5c805610585ceb；父批准本轮最小接线。

## 正式接口与循环边界

- recovery_program_retry.resolve_retry_target(..., purpose='SOURCE_CANDIDATE'|'RESTORE_REQUEST'|'CONSUMED_EXECUTION', source_ref, recovery_point_ref=None, operation_id=None)。缺少参数不默认切候选。
- observe_retry_admission(..., source_ref) 仅返回真实 FAILED_RETAINED_RETRY_ADMITTED 证据；UI source 候选不消费、不代表任意 point 已准许。
- snapshot_restore 对 v1 READY 原入口不变；失败分支必须显式给 owner/request，并已由原 bind_clearances 消费。MainProgramRestoreContext/v2 增加 startEpoch 与 retryAuthorization，readyEpoch 仍是真实旧成功前缀。
- 新 STARTED 仍用现有 FAILED→REPLACING 合同；其前一项必须等 startEpoch。完整 proof 以 startEpoch 序号定位本次 STARTED/FINISHED。
- 循环解法：先核旧 binding/context 为 v1，才调用原 validate_clearance → 原 owner/request → 原 validate_program_evidence；原 v1 历史只通过现有 journal 读回，不读取重试授权。v2 失败再次续办在进入这条调用链之前明确拒绝，不自递归。
- 必要产品范围：新增 retry helper，targets/main_target/activation/execution/evidence/restore 七文件；backend availability 一处明确 SOURCE_CANDIDATE；files.json/standard_fixes.py 正式登记第154个 payload。不改 backup_epoch/capture/resource/retained-release 原合同。

## BDD（实现前）

1. Given 完整真实 v1 PREPARATION 失败、保护未安装、正式 no-mutation release 与 clearance；When 同 source 只读候选；Then 目标可被观察且保留真实 FAILED epoch，全部原件不变、无消费。
2. Given 同一 clearance；When 不同 source/point/target、旧 operation、消费给另一 operation、过期或原件漂移；Then 首次写入前拒绝。
3. Given 已消费给唯一新 request；When snapshot→bind→begin_restore→effective→stage→成功 FINISHED→final program evidence；Then v2 指向旧真实 READY 和原 FAILED 起点，新操作有完整原件及新 READY，旧失败始终保留。
4. Given public resolve_target/resolve_capture 或未声明 purpose；When 当前 FAILED；Then 继续拒绝，不把候选当 source READY。
5. Given v2 新操作也失败且又取得准许；When 请求第三次重试；Then PROGRAM_RETRY_PREDECESSOR_V2_UNSUPPORTED，有限合同明确阻断、不递归或静默降级。
6. Given v1 正常 READY/恢复完成 READY（operationId 非空）；When 原调用链与历史 proof；Then 原合同保持，task native 检查不能要求成功 READY 必须 operationId=None。

## TDD 证据

证据目录均在本任务 PRIVATE，命令统一为固定 Python `-X utf8 run-program-retained-retry-linux.py <phase>`；外部 Docker 使用固定 Python 3.12 image SHA14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735、12 固定 wheel、network=none、read-only、cap-drop=ALL/仅 CHOWN、1GiB/2CPU/128PID 与有限 tmpfs。每轮仅操作本轮带任务标记的 --rm 容器，不接服务器。

| 阶段 | 实际结果 | pytest 秒 | 输入 source.tar SHA256 |
| --- | --- | --- | --- |
| red-r1 | 16 FAIL/0ERROR/SKIP，缺正式 helper | 4.352 | c68c2a91eb5ec51d19eb55a49c37a1198e776825fd15f1fecf46f74380be0d75 |
| green-r1 | 13 PASS/3 FAIL：消费错误码与变动 current tail 纳入固定 context | 3.981 | 原件保留 |
| green-r2 | 15 PASS/1 FAIL：新操作协议 switch 仍用旧 opId | 5.672 | 原件保留 |
| source-red-r1 | 16 PASS/2 FAIL：测试材料缺正式 capability 与外部 SQL 可变状态纳入原件比较 | 8.817 | 原件保留 |
| source-red-r2 | 17 PASS/1 FAIL：真实三 source selections 中未授权 source 抛通用错误 | 7.677 | cbf293202dfa698863f8a26a13755db863a80ec62bc1e790075928c2830bfb80 |
| green-r3 | 18 PASS，来源不符精确码，未知坏 proof 继续抛错 | 8.579 | 63a7ae0d6375e58decee75c6da7353178dfb6f6f5041c2ae770b7302c952476a |
| opaque-red-r1 | 18 PASS/2 FAIL：不透明原件被 JSON 解释 | 10.203 | 390b04d85280983bfe1faacbbbf9cc6499eb4096477edbb79cf9303aa1fad0ac |
| green-r4 | 21 PASS/3 FAIL：测试正则 ARCHIVE_ 未匹配正确的 ARCHIVED_PAYLOAD_CHANGED | 12.395 | 7c74fa6c2ee952eecb9e6cba23479135adc78ca66809e95d2c8d1e0dcc2880c7 |
| green-r5 | 25 PASS/2 FAIL：严格容器不能重新打开 0400 秘密写 FD；测试材料修为 chmod 前已持有 FD | 13.351 | 9e90aa19aab9b86d80ce4b4df917dde9425626e5bac07a3644e9f2ceb21c49a5 |
| green-r6 | 27 PASS/0FAIL/ERROR/SKIP；9 个 opaque 节点全部通过 | 12.783 | b8396fbb04fadee1be13ec670db4b63bf1c0cab4afd1477ef164f8993463b4c6 |
| regression-r1 | 388 PASS/3 FAIL：2处旧测试 adapter 接口仍旧；隔离载体缺实际 Git metadata | 153.946 | 70af1a67f8a79c305d55b74ba6f4e3f7127a4003d64a5a705f4db054052fe12e |
| regression-r2 | 391 PASS/0FAIL/ERROR/SKIP，外层179.422秒 | 155.501 | 5007507c9ebcfeb1d57fbdf85329ac7adc53e1a1a34aee321aec8478c452f2cc |

以上每轮 source snapshot 不变、localInputs 不变、容器移除均为 true；每轮 stdout/XML/result.json 原件独立保留，无覆盖或改写失败原件。green-r6 外层耗时23.610秒。完整 v2 成功 producer 节点：`scripts/tests/test_recovery_program_retained_retry.py::test_real_v2_context_binding_native_stage_terminal_and_history[True]`。

实际 source-target 注册、旧 v1 历史 proof、Linux flock、唯一 consumption、snapshot/bind/STARTED/effective/stage/FINISHED/final proof 都走正式代码。外部 SQL stdin 与 Docker 身份使用原有明确有限协议材料；不将此处 PASS 当真实服务器恢复成功。真实包认证模块路由动态读取 manifest，没有153硬编码；无需修改 TASK/preservation_candidate_imports.py，也不添加源码 fallback。

regression-r2 仅调整旧2处测试 adapter：mock resolver 改为正式新增 resolver 名，mock observer 接受显式 purpose。载体为 lightweight 真实构造补充本仓实际 HEAD、branch 与 `git cat-file commit` 原字节对象（先核 Git SHA1，再隔离封存），不 mock Git、不删节点或跳过。原 v1 target/generation/activation/execution/native/evidence、control history、准备失败 no-mutation、retained clearance 和 archive availability 合计391项通过，未重跑无关捕获大套。`git diff --check` 通过。

## 冻结范围与限制

- 产品：新增 recovery_program_retry.py；修改 recovery_program_targets/main_target/activation/execution/evidence/restore/native.py 与 backend recovery_control_target_availability.py。正式 files.json、standard_fixes.py 登记 helper。相对0119156标准包仅8个既有成员变化与1个新增，payload154；最终官方 clean 包与其完整 producer 由父验证。
- 测试：新增 test_recovery_program_retained_retry.py；上述2个旧测试 adapter 仅同步调用合同。未修改原 generation/capture/epoch/retained-clearance/resource 实现，也未改旧3条 journal。
- 原 proof 的不透明 pin 始终保留，以强 reader 完整 SHA/身份/权限读取并受连续 inotify/O_PATH 租约保护。0400和0755/50320B均验证，FD正常关闭及构造失败均无泄漏。
- 本轮仅一条正式 v1 PREPARATION no-mutation 失败接 v2 的目标专用续办。若 v2 再失败且再授权，明确 PROGRAM_RETRY_PREDECESSOR_V2_UNSUPPORTED，不声称所有失败都可自动恢复。
- 私密 runner/stdout/XML/result.json 原件均保留于本任务 PRIVATE/program-retained-retry-*，没有覆盖失败历史；最后冻结报告由父用于精确提交、clean build、包认证和现场验收。

### 不透明原件的附加 BDD

- Given 原证明含 owner 0400 的普通秘密或非 UTF-8 字节，以及 owner 0755、50320B 的工具二进制原件；When 新 native 上下文为完整旧证明建立租约；Then 以完整 SHA/身份/权限读取，秘密与二进制不被当 JSON 解释，租约关闭后 FD 恢复。工具测试字节仅是本机协议材料，不执行或声称真实 mount。
- Given 原件完整 SHA 不符，或建立租约后原件被改写/同名替换；When native 建立/检查连续保护；Then 明确拒绝，不丢弃原 pin，构造失败也释放所有自有 FD。
- opaque 原始 RED：18 PASS/2 FAIL，真实普通与非 UTF-8 原件被错误当 JSON，BACKUP_EPOCH_JSON_INVALID。最小修复仅将 additions 的 JSON 解析改为 epoch._read_file 全 SHA/身份/权限读取；完整 resolver 已分别解释所有 JSON，ArchivePathGuard 连续覆盖所有 pin。
