# FULL373原始派发审计合同诊断

## Current Status
ready_for_closeout — TASK helper精确派发合同已修复，23项RED→23项GREEN→63项回归PASS/零skip；UTF-8/语法通过。原失败日志完整保留，现场audit没有重跑；等待根任务审阅后独立验收FULL373，不能把本机合同测试当作实际备份验收。

## 目标与里程碑
- [x] 读取原生产派发格式和精确原始调用证据，找出不匹配条件。
- [x] BDD/RED复现真实合同，最小修复共享验收函数。
- [x] GREEN与相邻回归，交付新诊断报告，保留失败原件。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；依据真实协议调整错误假设，保留所有身份/原件/结果交叉绑定。
- 是否从根因和长期维护角度解决：是；把派发审计拆为明确可独测合同。
- 是否存在临时补丁或绕过：否；不以操作已成功为由跳过启动证据。

## 经验门禁
- Trigger：FULL373原生完成后独立helper错合同阻断验收。
- Preflight check：保存原失败日志pin，精确核实际执行入口生成的request/intent/process/exit及参数，不猜协议。
- Blocker：任何原记录/配置/程序/操作号/pid/真实终态不能一致绑定。
- Verification：先真实原始元数据只读诊断，再本机RED/GREEN；现场审计重跑须根任务评审。
- Forbidden action：不得改原回执、伪造启动结果、跳过原件或调用业务写入。
- Evidence：275B失败日志sha256 cb981ded009da56d9d3415786a9017e1d7a10c43d502cc6ddaea24e3ef40ce92；新诊断和任务测试。

## BDD
- Given真实原生executor产生完整启动/退出记录，When审计精确请求、程序、配置和调用，Then合法异步启动被准确验证。
- Given错操作/请求pin/程序pin/配置pin/intentpin/pid/退出状态/argv，When审计，Then明确拒绝，不能仅凭最终SUCCEEDED忽略。
- Given原launcher按已安装STANDARD协议退出2且响应为TERMINAL_UNKNOWN/REPOSITORY_QUERY_ORIGINAL_OPERATION，When其固定operationDirectory/resultRef和后来成功的唯一owner完全绑定，Then仅该明确异步合同通过；其他unknown/code/owner拒绝。
- Given同步launcher退出0，When返回内容与唯一owner终态逐字段相同，Then通过；任何不同响应或退出1/3均拒绝。

## 已证实根因与RED
两个只读诊断已固定所有原始元数据及原响应pin。实际FULL373的argv、操作号、request/config/program/intent pins、pid均一致，唯一旧断言失败是launcher实际exit2而helper错误只接受0/3。安装STANDARD和正式repository_minimal.execute都规定TERMINAL_UNKNOWN映射2；原owner后续SUCCEEDED/exit0。不能将此误判为备份重做依据。

`automatic-dispatch-audit-red.txt`：23项FAIL/exit1，缺少精确合同函数且audit仍有旧白名单；这是本机原始元数据重放测试，不是再次执行现场审计。

## GREEN / REGRESSION与交接
`automatic-dispatch-audit-green.txt`：23项PASS。扩展原件关联破坏用例并直接读取已安装0d STANDARD tgz的execute退出码及query协议；`automatic-dispatch-audit-regression.txt`：32项派发合同+15项链审计+16项源恢复=63项PASS/零skip，46.86秒。新增测试仅本机真实元数据重放及明确变造的拒绝输入，不使用mock冒充现场成功。

`automatic-dispatch-audit-contract-fix.json` 固定修复helper/test/原失败/诊断/测试日志pins，状态LOCAL_REGRESSION_PASS，实际audit尚未重跑。helper SHA256 `8c314deedebfc5ff9712899657dde8aaffdd6c73f5381383c2f68e18128b34e1`。`closeout_contracts.py` 同类0/3断言已通知其owner archive按nativeDispatch精确同步，本分工不修改共享文件。

根任务审阅后沿用 `verify_automatic_backup_chain.py --submission automatic-full-ui-submission.json --output automatic-full-audit.json`；本轮未执行此命令。FULL373保持原0d安装，source-restoration需该audit及真实UI terminal成功后另行执行。未来I1/I2的明确阶段代次绑定另按根任务后续分派实施，不改本次FULL原件。
