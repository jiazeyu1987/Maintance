# 激活通用证据 pin 与 JSON 文档职责分离

## Current Status

ready_for_closeout。实现与必要验证完成并冻结，待父统一回归/提交；父代理已识别同一任务目录并写入 `control-activation-evidence-contract-plan.md`。本子阶段按 Subagent-Driven Development 仅拥有 activation、独立新测试及本日志。真实59/r6默认准备失败原件由父保留；本阶段未操作服务器、改计划或原件、提交。

## 目标、里程碑与验证

1. 使用真实临时原始命令日志、源码、二进制和 JSON 重现错误；正式 prepare 与 dispatch 后通用闭包不能把所有 pin 当 JSON。
2. 最小提取通用完整 pin 核验函数，仅明确 JSON 消费者保留解析返回值。原 file_pin 身份/漂移/字节/SHA 校验原样复用。
3. 新场景 GREEN、activation v1-v4 与失败续办受影响回归；冻结准确 bytes/SHA 交父独立验证及真实默认 prepare。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。错误类型不触发补救解析或跳过原件。
- 是否从根因和长期维护角度解决：是。区分原件身份验证与 JSON 业务文档解析，通用闭包不假设文件格式。
- 是否存在临时补丁或绕过：否。不开原文件名白名单、不修改旧日志内容或引用。

## 经验门禁

- Trigger：真实旧代次选择含合法非 JSON 命令日志，纯 prepare 因 JSONDecodeError 阻断。
- Preflight check：已读经验索引及“多机器发布接管与缺失记录分析门禁”“AST 测试载体与生产入口前提一致性”；核两个通用循环及 checked_local/private_document/rotate_receipt 原返回值用途。
- Blocker：缺真实原件、原 pin 漂移、载体未到达目标行为或把私密文档语义核验删掉。
- Verification：真实临时文件和原 prepare/dispatch 正式路径，协议边界明确；不把本地 transport 回执当服务器成功；原回归零 skip。
- Forbidden action：不重写非 JSON 原件、不删引用、不按错误吞掉验证、不扩大到服务器/计划/其它模块。
- Evidence：父任务事前计划的119B原命令日志摘要、本日志 RED/GREEN/REGRESSION 和冻结 SHA。

## BDD

- Given 真实 JSON、命令日志、源码与任意二进制原件，When 通用 pin 核验，Then 格式无关且完整 bytes/SHA/文件身份检查保持。
- Given 原件同长度篡改、长度变化或预期摘要变化，When 核验，Then 明确拒绝；非普通文件仍拒绝。
- Given 完整已有 v4 本地协议 prepare 及新增真实非 JSON 历史原件，When 正式 prepare，Then 全部原件保持且不派发、不写 attempt。
- Given 已登记原始日志属于 dispatch 的完整输入闭包，When 明确本地 transport 协议回执返回，Then 正式二次核验通过；期间改变原件则不发布 core。
- Given 明确的 private JSON 文档或安装 receipt，When checked_local/private_document/rotate_receipt，Then 保留原 JSON 返回值与解析失败语义，不能将其降为只验摘要。

## TDD

- 初次 RED：10 failed / 8 passed / 0 skipped / exit 1 / 6.61s；其中5个 PASS 是导入旧 unittest 类被 pytest 再收集。仅改为模块导入以避免重复计数，原测试断言和产品未改。
- 精确 RED：`python -B -X utf8 -m pytest <TASK>/test_main_program_activation_evidence_pins.py -q --tb=short` → **10 failed / 3 passed / 0 skipped / exit 1 / 7.09s**。8处明确缺新通用 API；其余2处通过真实正式 prepare 与 dispatch_prepared 到达原763/979并抛 JSONDecodeError。明确 JSON 语义和原件漂移拒绝已通过，无 setup 错误。
- 最小实现：提取 `verify_local_pin(path, expected)` 原样调用 file_pin 和 bytes/SHA 判断，返回实际 pin；checked_local 先调用它再原样 read_document。只将两处通用闭包改为 verify_local_pin，private_document/rotate_receipt 的 JSON 语义不变。
- 联合候选：新文件加 `test_main_program_control_activation.py`、`test_main_program_control_environment.py`、`test_main_program_control_preswitch.py`、`test_main_program_control_generation_activation.py` → 166 passed / 1 failed / 0 skipped / exit 1 / 38.70s。唯一失败为新载体末尾误把 generation 历史 pins 期望归入 records 的 inputPins。正式 generation 合同将其归入 immutablePrivatePins；原 prepare 已完整通过。精确补载体 bundle.inputPins 与断言 immutablePrivatePins，未改产品或放宽任何 pin 检查。
- 最终 GREEN：同一新文件完整运行 → **13 passed / 0 skipped / exit 0 / 6.32s**。原联合运行的 **154 个既有回归全部通过**，其源码/测试保持不变；合计覆盖 167 个用例，不把先前聚合失败记成整体 PASS。父将另行统一回归。
- `git diff --check -- <TASK>/main_program_control_activation.py` → exit 0；生产 diff 仅 9 insertions / 3 deletions。
- 父独立真实验证（父消息确认，非本子代理执行）：59/r6 默认 prepare → PASS / exit 0 / PREPARED_NOT_ACTIVATED / remoteDispatched=false；私密日志 `activation-59-default-prepare-evidencefix-r1.log` 251 B，SHA256 `bfff00d2010e570c307efd088d51019e224891264b3c1429402a72b09ae56c1d`。尚未派发。
- Python 固定 `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`，PYTHONPATH 为任务既有 test-dependencies；所有测试用真实临时文件，generation/transport 按既有明确外部协议 seam，不视为真实部署或备份恢复成功。
