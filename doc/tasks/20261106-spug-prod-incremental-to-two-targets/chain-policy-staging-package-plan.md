# 链策略真实包暂存读取接线

## Current Status

implementation_verified。父在实际暂存入口事前核对发现：新delta以packagePin记录包，原暂存入口仅读取旧delta的path。Linux运行路径/evidence只在原验证容器存在，不能直接作为Windows暂存包路径。正式读取接线与必要回归已通过；实际暂存尚未执行。

## 目标、里程碑与验证

1. BDD / RED：Given 完整验证的新delta与同提交build中的实际本机归档pin，When 暂存准备读取包，Then 取得精确原字节并再次核长度/SHA；改变归档、错variant或错pin拒绝。Given 旧delta，When 同入口读取，Then 保持旧path合同。
2. 最小正式接线：新schema显式选择build.variants.standard.packagePin，要求bytes/SHA与已验证delta包一致并实读前后检查。旧schema继续原路径，无自动猜测、路径回写或fallback。
3. 必要回归通过后精确提交；纯准备通过才允许按既有授权暂存，不改包内产品代码。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；schema显式分支，不支持未知schema。
- 是否从根因和长期维护角度解决：是；区分原验证运行路径与构建产物路径，以完整原字节绑定。
- 是否存在临时补丁或绕过：否；不修改旧delta或Linux原命令，不制造宿主/evidence目录。

## 经验门禁

- Trigger：控制暂存读取新profile实际归档。
- Preflight check：已审coverage、同提交build与完整包pin，路径实际存在；默认仅本地读取。
- Blocker：变更字节、未知schema、错variant/pin、缺实际产物。
- Verification：真实归档正反例、旧路径保持及暂存相关原回归。
- Forbidden action：不改原证据、不将fixture作为实际暂存成功、不联系服务器。
- Evidence：本计划、后续RED/GREEN原始输出及父验证报告。

## BDD / TDD 证据

RED：新7例实际运行，7 FAIL / 0 error/skip，0.39秒；缺read_covered_package正式入口，原工具chunk cd77ff。GREEN：相同7例全部PASS，0.88秒，chunk1669f7。正例实际读取a4c279f的147成员STANDARD归档并由正式verify_package全成员核验；其余真实pin/归档字节替换负例均拒绝，旧delta path保持。

REGRESSION：原暂存测试 -k 'record_prepare or prepare_materials or actual_standard or candidate_protocol or runtime_materials'，14 PASS / 45 deselected / 0 skip，31.25秒，session9490终态chunk7ae7a2；只读record准备、纯计划复建、旧真实包与候选协议均通过。未执行Linux专属文件写入，也未将deselected计作通过。
