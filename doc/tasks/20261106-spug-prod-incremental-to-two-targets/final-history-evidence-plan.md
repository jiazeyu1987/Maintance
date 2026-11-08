# 最终历史保全审计的代次绑定修复

## Current Status
completed

## 目标及里程碑

最终审计实际因缺少旧 protected-history-verified-57.json 失败。旧流程还要求 58 的旧五代安装回执，而真实自动增量安装后已为六代；59 已为三代。当前 stable-controls-closeout.json 已在真实连接中完整核验原历史 SHA 与全部授权回执链。不能重造旧报告或要求当前 active receipt 回退。

BDD：Given 原始历史基线和自动增量后的当前完整保全证据，When 最终审计，Then 所有原路径/字节保全及授权历史回执归档和当前选择均需通过；篡改计数、基线 bytes、归档回执或当前回执须失败。

RED -> GREEN：先以当前真实 57/58/59 文件建立正例及篡改负例，再在 verify_closeout.py 增加精确代次验证，替换仅依赖缺失/过期报告的旧循环。最终只复用实际 stable 证据，新增报告明确来源 pin；不访问服务器、不修改原件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；删除过期证据路径要求，使用当前已验证证据并校验完整基线 bytes、计数与实际选中回执。
- 是否从根因和长期维护角度解决：是；最终审计跟随当前已授权代次，同时保留旧恢复当时的不可变证据。
- 是否存在临时补丁或绕过：否；不伪造旧结果，不修改服务器或放宽保全条件。

## 经验门禁

旧 closeout-verification-attempt1.private.txt 保留；当前三服稳定证据和保护基线只读。新审计必须在旧恢复与新增连续增量完成之后，必须仍核全部历史不可变 paths 与原始 active receipt 归档，而不是只核当前安装健康。验证失败立即停止，不宣称最终收尾完成。

## 实际验证

RED：8 项因缺少代次绑定函数实际失败。GREEN/REGRESSION：8 项当前真实文件正反例及相邻收尾、提交、行尾测试共 76 项 PASS，47.17 秒、退出0。新函数核原基线所有 evidencePins 的计数、总 bytes、无重复路径，当前不可变历史计数及原 active receipt 归档的完整 pin、当前选择回执和授权链计数。最终 verify_closeout.py 实际退出0，closeout-verification.json 于 2026-11-08 03:39:37Z 为 PASS。旧报告和原失败不覆盖，无额外服务器访问。
