# 稳定控制验证的查询副作用报告

## Current Status
ready_for_closeout — TASK报告语义及下游合同已修正；7项新增测试与13项相邻收尾合同回归全部PASS，未调用服务器或浏览器，不改变健康/安装/历史校验。

## 目标与里程碑
- [x] 定位CURRENT_SCRIPT调用/selections及下游verify_closeout对serverWrites=false的依赖。
- [x] 先RED验证报告不再声称无服务器写入，随后最小修正并GREEN。
- [x] 明确仅业务无变更派发，控制API查询可能追加查询审计；交根任务收口。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；仅纠正事实报告和下游合同。
- 是否从根因和长期维护角度解决：是；区分业务变更与控制审计元数据写入。
- 是否存在临时补丁或绕过：否；原健康、配置SHA、当前代次、历史保全校验全部保留。

## 经验门禁
- Trigger：HTTP GET可经目标准入追加control-query审计，不等于服务器完全无写入。
- Preflight check：定位调用链和报告消费者，禁止继续使用serverWrites=false描述含控制API调用的验证。
- Blocker：下游仅认可旧字段或报告缺查询副作用字段。
- Verification：本机合同测试和载体语法；不做额外审计目录大扫描、不运行现场验证。
- Forbidden action：不得把可能发生的审计写入报告为无写入，不减弱已有运行态/历史校验。
- Evidence：本计划、任务测试及execution-log。

## BDD
- Given稳定控制验证执行控制API查询，When生成报告，Then businessMutationDispatched=false、controlApiQueriesPerformed=true、queryAuditWritesMayOccur=true，且不包含serverWrites。
- Given旧serverWrites=false报告或缺少上述字段，When最终收尾校验，Then拒绝把它当作新语义证明。
- Given仅本机record-selection，When写选择清单，Then原serverWrites=false事实仍成立，保持该独立分支。

## 验证
- RED：7项新合同测试均失败，分别暴露旧serverWrites=false、缺语义验证函数、最终收尾仍依赖旧字段。
- GREEN/REGRESSION：7项新测试+13项主机快照/收尾合同测试全部PASS（20 passed，0.41s，零skip）。CURRENT_SCRIPT、Python/UTF-8/diff检查PASS。
- CURRENT_SCRIPT和总报告改为三个明确字段；current_remote_controls和verify_closeout共用verify_control_query_effects拒绝旧模糊报告。原健康、安装SHA、当前来源计划、历史/安装代次证据校验未改。
- 仅本机record-selection分支仍保留serverWrites=false，因为该分支不调用服务器；没有对远端查询审计实际数量作未经验证的声明，也未扫描审计目录。
