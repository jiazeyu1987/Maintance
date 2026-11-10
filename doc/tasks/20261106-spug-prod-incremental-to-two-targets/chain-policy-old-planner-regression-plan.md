# 原规划器无写入回归的现存原件前提修正

## Current Status

verified。已独立重现旧单例FAIL；修正测试对原文件stat+SHA前后保持的断言，并加入已有/不存在输出两例，原路线/连接合同保持。单文件28PASS；父独立旧五组172PASS/0fail/error/skip/55.76s，新证据103PASS/0fail/error/skip/163.45s。真实45-r5原件及全部验证输入前后不变；产品规划器旧逻辑不变。原始stdout和JUnit保留PRIVATE，公开报告chain-policy-parent-{old,new}-20261110-r1.json记录完整pin。

## 目标、里程碑与验证

BDD：Given 规划输出路径已存在原历史材料，When 纯规划器生成内存计划，Then 原文件字节及完整pin保持，原路线/连接断言保持；给定尚不存在的路径时仍不得创建。先独立重现原1FAIL，最小修正测试的事前/事后检查，再重跑该文件及新证据合同/旧受影响组合。不得将环境前提过时记作产品功能RED。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；测试实际无写入行为，不依赖历史材料永远不存在。
- 是否存在临时补丁或绕过：否；原历史不动，路线/连接断言不放宽。

## 经验门禁

- Trigger：历史安装后重跑纯规划器回归。
- Preflight check：固定原计划pin/字节，独立验证失败来源，确认产品无差异。
- Blocker：原文件漂移、无法独立复现、为了通过删除/改历史材料或放宽业务断言。
- Verification：原单例FAIL原件、最小测试修正、全相关回归及原文件前后pin全等。
- Forbidden action：不删除真实45-r5，不改旧产品reader/allowlist，不把fixture当实际部署成功。
- Evidence：本计划、后续父原始日志、新helper79项与旧169/1原始输出。
