# 控制代次原件闭包：专属 TDD 记录

## Current Status

ready_for_closeout。本机15项GREEN和214项回归完成；父独立15 Windows通过，叶symlink另由真实Linux验证通过。不得宣称本机单次16全PASS。只拥有activation的原件范围局部接缝、新独立测试/计划/本记录；源policy、generation与原证据未修改。

## 经验与设计执行

已按 main-control-generation-scope-plan.md 摘取完整物理闭包与活动回执历史保全门禁。父审阅后批准，仅以本次已经完整验证并 `_finish` 重核的 bundle.inputPins 授权代次原件；不添加任意目录/递归白名单。非generation原TASK直接子文件合同保持。所有文本 UTF-8，记录只含路径/pin/摘要，不含凭据。

BDD：Given 已验证完整 generation 闭包包含主源/PRIVATE子目录/包原件，When prepare，Then完整pin精确成员及逐文件hash通过才准入。Given旧目录内但不属于闭包或path/bytes/SHA/额外字段漂移，Then拒绝；Given旧模式，Then仍只TASK直接子文件。

## RED

执行独立新文件 `test_main_program_control_generation_scope.py`，使用实际prepare AST中唯一原件循环和真正verify_local_pin；另一个用例完整执行真实固定59 r7输入默认prepare，没有mock外部验证。

- 原helper121722B，SHA `ba46ae81fa20861c6a4c9221f80bcd86cbbd0e7e9eec18548d117e7c0ba1ac3b` 保持。
- 16项结果：11 FAIL/5 PASS，exit1，34.32秒，零skip。
- 10项预期业务RED：3个完整闭包外部原件被旧目录限制误拒；5个TASK内非完整闭包成员误放；词法路径别名误放；真实r7 defaultprepare报MAIN_ACTIVATION_ORIGINAL_EVIDENCE_SCOPE。
- 另1项不是业务RED：Windows `Path.symlink_to` 创建叶symlink时报WinError1314（无特权），尚未进入被测逻辑。父明确要求保留此用例，由其无网络真实Linux载体执行；不删除、skip或mock创建成功。
- 原日志 `main-control-generation-scope-red-r1.log`：8653B，SHA `046c5b2b835e88bf33b4917a208948e2eb150acb6e6a21a67e00c9702215f770`。

## GREEN

最小局部实现只有分支范围判断；不改file_pin/verify_local_pin能力。原叶symlink拒绝保持；硬链接nlink/父目录symlink未由旧校验器全面检查，本轮不扩展也不宣称已验。

命令：`python -B -X utf8 -m pytest test_main_program_control_generation_scope.py -q -p no:cacheprovider --tb=short -k 'not leaf_symlink'`。

- 实际15 PASS/1明确deselected，exit0，33.23秒，无skip。
- 完整真实r7默认prepare成功，dispatch_prepared默认返回PREPARED_NOT_ACTIVATED/remoteDispatched=false；该用例核输入pin字节保持且没有实际attempt/rich/core。
- 日志 `main-control-generation-scope-green-r1.log`：116B，SHA `bf19c8923bdb4bec167b58e0b5f952f4cbab99bb9bb8ba7551ea04fa7e66c74b`。

## REGRESSION

- 父独立15 Windows PASS（34.97秒，1明确deselected叶symlink），输入前后SHA保持，真实r7默认prepare无attempt/远端写入；报告control-generation-scope-parent-20261110-r1.json。
- 父实际Linux叶symlink单项PASS（0.05秒），使用固定无网络/只读根/无cap载体，原实际源码SHA为ef070f77；与SAFE归档17项共同保存在capture-archive-scope-linux-20261110-r9.json，合计18 PASS/0failure/error/skip，输入不变、容器删除。Windows Win1314原件保持，不改记通过。

以独立依赖目录PYTHONPATH，执行以下六文件（名称均在当前TASK）：test_main_program_source_policy_activation.py、test_main_program_control_activation.py、test_main_program_control_generation_activation.py、test_main_program_control_generation.py、test_main_program_control_environment.py、test_main_program_activation_evidence_pins.py。

- 实际214 PASS，81.80秒，exit0，无skip。
- 日志 `main-control-generation-scope-regression-r1.log`：275B，SHA `ae09b9b831f51badfdf5a2121a9159df9473a5a4f0770efa5616c6405be1749d`。
- 原 `source-policy-activation-parent-20261110-r1.json` / 原214日志未修改；本次为独立新增回归记录。

## 冻结与范围证明

| 文件 | bytes | SHA256 |
| --- | ---: | --- |
| main_program_control_activation.py | 121760 | `ef070f77fd7c8f5753a5eead343d2e49e20e52e45cc4aabc5601f7e1d0726f69` |
| test_main_program_control_generation_scope.py | 6090 | `2cb1267f8f2f947838948bc9e100112edcf2d3073cbba353f0a625603660d321` |

只读逆应用唯一scope hunk后，原helper长度和SHA精确等于父给定原件，证明没有夹带source policy或其它实现变化。源码与测试已冻结交父，后续父真实Linux节点为 `test_main_program_control_generation_scope.py::test_generation_rejects_leaf_symlink_even_if_member`。本子任务没有访问服务器、Docker、构建、提交、修改原plan/原pins/实际输入或生成实际安装attempt。
