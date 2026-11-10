# 来源链策略激活合同 TDD

## Current Status

IMPLEMENTED_VERIFIED / HISTORICAL_CUSTODY_BLOCKER。父已批准 `control-chain-policy-source-activation-plan.md` 的 A–D；专项50项全部通过，宽回归444项通过。旧发布 continuation 的原源码保留缺口造成2项失败与26项前置错误，已保留并交父处理。本阶段仅修改安装器配套与专项测试，不改变 e4e862b 的包输入、运行器或源码证明，不构建、不远端、不提交。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；只接受已验证新 profile、v4/57/source 下经共享策略证明的 AGE_EXPIRED，其他失败继续拒绝。
- 是否从根因和长期维护角度解决：是；原链保持与当前增量准入分别验证。
- 是否存在临时补丁或绕过：否；不改原链、owner 上限、epoch、历史或实际结果。

## 经验门禁

沿已批准设计中的 Trigger / Preflight check / Blocker / Verification / Forbidden action / Evidence 执行。新原件不得冒充实际服务器安装。保留原首次失败及测试完整终态，零 skip 才可交付本阶段。

## BDD

- Given 同一组真实临时 FULL/I1/I2 和 epoch，旧45 planner实际返回 READY，新 planner实际返回 AGE_EXPIRED；When 执行安装器实际切换后 source 分支；Then 精确验证候选与新 HTTP、原锁内 I2 和 policy 后通过。
- Given 未过期链；When 新 profile 准入；Then 保持 READY+原 I2；旧 schema/profile/target 不启用过期转换。
- Given 原 point/manifest/epoch/policy、旧锁内 I2、新 HTTP、摘要或真实候选结果变化；When 同一有限检查；Then 阻断，不产生成功 core。
- Given 固定实际证据的历史读取；When 当前时间已变化；Then 只核冻结证据，不用当前时钟重新判历史；缺实际嵌套证据、未知 reason 或仅 true 布尔值不得通过。

## 里程碑

1. 真实合同 RED：完成，实际旧安装分支拒绝新正确 AGE_EXPIRED；详见下方原始失败。
2. 最小 GREEN：完成，50 passed / 0 skipped / exit 0。
3. 原 activation/generation/stager/publication 受影响回归：已执行，444 passed；旧发布原源码 custody 缺口阻塞2项测试及26项前置，未放宽或改原件。
4. 源码冻结与 SHA：生产已冻结，精确清单见父交付；父负责提交与真实安装，未宣称已部署或全目标完成。

### 载体前提失败（不是产品 RED）

- 首次专项命令实际退出 1：1 passed / 34 setup errors / 0 skip，192.50 秒，exec session 4376。
- 原因：复用的 MetadataFixture.bind_epoch 以 FULL 请求发布增量点，真实 Native 严格拒绝 ORIGINAL_RESULT_BINDING_INVALID。仅修本专项夹具，按每点真实类型和父点调用原 publish_point_epoch；不修改既有 fixture 或产品校验。
- 临时元数据的初次构造改为模块级复用；每个负例仍读取真实文件并在测试结束恢复本测试临时文件的原字节，不触及任何任务原件。

### RED：真实门禁及两个消费边界

- 命令：固定 Python `-B -X utf8 -m pytest doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_main_program_source_policy_activation.py -q --tb=short`，PYTEST_DISABLE_PLUGIN_AUTOLOAD=1，依赖路径使用本任务已登记 test-dependencies。
- RED r1：33 failed / 2 passed / 0 skip，10.06 秒，exit 1；本机认证 HTTP 返回真实 Native AGE_EXPIRED，实际 REMOTE_SCRIPT 的切换后分支抛 SOURCE_BASELINE_CHANGED。保留输出：PRIVATE/source-policy-activation-red-r1.log。
- RED r2：补齐真实未过期链、独立 Python 候选入口及 core/generation 消费门禁后，37 failed / 8 passed / 0 skip，14.41 秒，exit 1。其8个通过中5个为导入旧 unittest 类导致的重复收集，专项实际40项；两个消费负例均 DID NOT RAISE，其他缺正式 helper。保留输出：PRIVATE/source-policy-activation-red-r2.log。
- 旧 planner 从已固定 SHA 的45 STANDARD tgz直接读取原模块；真实同一组私有临时元数据、owner 限制、epoch 分别由旧模块和当前 Native 解析，未 mock Native/策略/epoch 成功。
- 父正在运行独立107证据合同回归；收到暂停指令后至今 activation/generation 源码未改。其解冻后再进入最小实现。

### 最小实现首次验证

- 父107项检查通过并解除冻结后才修改 activation/generation。
- 首次候选：36 passed / 4 failed / 0 skip，13.60秒，exit1，PRIVATE/source-policy-activation-green-attempt-r1.log 保留。
- 三个漂移负例实际已被正式 Native 的 Failure/NATIVE_PIN_CHANGED 拒绝，测试原仅接受 ValueError/AssertionError，现精确按这三个场景要求 Failure 且该错误码；不放宽生产。
- 独立 Python AST 函数载体漏带原 candidate 顶层 sys/pathlib 导入，修复该本机载体全局前提，不伪造函数返回或替换正式执行逻辑。去除导入 unittest 类造成的5项重复收集后专项明确40项。

### GREEN r1 与原 FULL 审计关联补强

- 首轮完整 GREEN：40 passed / 0 skip，13.77秒，exit0，PRIVATE/source-policy-activation-green-r1.log。
- 静态复核确认已有 automatic-full-audit.json 将同一原根 pointPin 绑定真实根 manifestPin。仅记录一个结构合法的候选 manifest pin，历史消费缺独立原根关联。继续复用这个已存在的原件，不把每份6.26MB的root point/manifest原文复制两遍进rich，不增加v4输入字段或schema。
- BDD：Given 可重签的rich替换为I2的合法manifest pin；When 历史读取；Then 拒绝。RED：`-k 'unbound_valid_manifest or root_audit_must'` 实际8 failed / 42 deselected / 0 skip，5.99秒，exit1；原缺绑定的场景 DID NOT RAISE，其余7项缺新显式root_audit参数。
- 最小实现：prepare/generation只在新coverage分支读取固定原FULL审计；核同source、根op/generation、point/epoch、FULL成功exit0、原单点链及无父点；将其local pin与manifest pin加入内部transition。候选真实root point的manifest必须相同，历史proof也必须相同。仍不查询当前时钟或当前最新链。

### GREEN r2 与受影响回归

- 专项完整命令同前，实际50 passed / 0 skip，14.04秒，exit0；PRIVATE/source-policy-activation-green-r2.log 保留。
- 宽回归命令：固定 Python `-B -X utf8 -m pytest` 加以下10文件，统一 `-q --tb=short -k "not linux"`：`test_main_program_control_activation.py`、`test_main_program_control_generation_activation.py`、`test_main_program_control_generation.py`、`test_main_program_control_environment.py`、`test_main_program_activation_evidence_pins.py`、`test_main_program_spug_publication.py`、`test_main_program_spug_publication_continuation.py`、`test_main_program_spug_publication_verify_only.py`、`test_main_program_control_staging.py`、`test_main_program_control_staging_finalize.py`。文件均位于本 TASK。
- 实际 session61628：444 passed / 2 failed / 26 errors / 11 deselected，294.80秒，exit1。11项为明确未执行的 Linux 专项，不是 skip，也未记为通过；本阶段不获准 Docker 或远端。完整原始日志 PRIVATE/source-policy-activation-regression-r1.log，49745B / SHA256 `d469ad45c1dcd4e9a397ec4900700c5cdf7ac6044564fa79edcc111229867f7c`；同名 `.json` 保存完整命令、退出码、全部输入前后pins，输入保持为 true。
- 2个失败：continuation 的 `test_real_explicit_c1_preparation_is_local_and_consumes_original_failed_chain`、`test_all_generated_continuation_programs_compile_and_old_programs_are_unchanged`；26个错误均为 verify-only 共用 originals fixture 调用同一旧 continuation 前置时失败。全部错误均为 `validate_source_custody -> reader.verify_bytes -> MAIN_SPUG_ORIGINAL_BYTES_CHANGED`，不是新 source policy 逻辑。
- 本机只读逐项核对旧45/r6/c1 attempt 的所有未映射 inputPins，唯一漂移为 `main_program_control_activation.py`。旧 pin：107657B / SHA256 `963bbe907d1d2f7334ee9fa5d8598a5659361ca512d23514d92d9721b91146bb`；这正好等于 Git 提交 `3e5113225d6c09a8ade5a0b6321d55fbee8d6122` 的原始 blob。当前任务未提取或覆盖该原件。
- 本轮源策略修改前，e4e862b 的同文件已经是107997B / SHA256 `56c46eeedff9b8a7369c44f033d9a8822372ed1715a636c7500b48a31e34bb3a`，故该旧 custody 缺口早于本轮修改。旧映射的准许范围仅 publication、installation_selection、observe_closeout_hosts 三个源码文件，不包含 activation；正式门禁拒绝符合原合同。
- BLOCKER：旧发布 continuation 需由所属 owner 补齐精确旧 activation 源码保留及可追溯消费关系。不得删除、替换或重签原 attempt/失败证明；本分工不修改该模块、旧测试或原件。未把宽回归声明为全部通过。
- 源码保持冻结等待父独立审查；仅更新本专属 TDD 日志。真实服务器切换、新原件生成和安装后用户路径验证尚未在本阶段执行。

同一命令只追加 `--collect-only` 精确归属节点，不重跑测试。472/483 collected、11 deselected、exit0；将原实跑失败列表映射到各文件：

| 文件（均省略 test_main_program_ 前缀） | PASS | FAIL | setup ERROR |
| --- | ---: | ---: | ---: |
| control_activation.py | 24 | 0 | 0 |
| control_generation_activation.py | 56 | 0 | 0 |
| control_generation.py | 36 | 0 | 0 |
| control_environment.py | 32 | 0 | 0 |
| activation_evidence_pins.py | 13 | 0 | 0 |
| spug_publication.py | 148 | 0 | 0 |
| spug_publication_continuation.py | 55 | 2 | 0 |
| spug_publication_verify_only.py | 6 | 0 | 26 |
| control_staging.py | 51 | 0 | 0 |
| control_staging_finalize.py | 23 | 0 | 0 |

节点与归属记录：PRIVATE/source-policy-activation-regression-r1-collection.log、PRIVATE/source-policy-activation-regression-r1-by-file.json。以上统计不是新一轮运行结果，不替换原 exit1 报告。
