# 只读页面独立复核证据保全

## Current Status
completed

目标：保留371终态首轮真实包清单502原件，为同一操作显式新增只读观察编号；不得覆盖失败、重提恢复或放宽原HTTP200/身份/终态要求。通用观察脚本接受可选序号，原默认行为保持；收尾显式选择并核旧失败pin与新实际PASS时间，不以接口替代页面。

设计约束检查：不引入fallback/降级/吞异常；从长期证据保全解决；无临时绕过。

BDD：Given 原terminal观察文件为FAIL/502且不可覆盖；When 对同一371开启显式第二次只读观察；Then 第一份原字节及错误保留，新独立真实浏览器仍须catalogue/operation/progress全200、同一请求SUCCEEDED、零写入才PASS；重复序号拒绝。

里程碑：保留原件pin；原guard RED；最小辅助脚本输出编号支持；真实UI GREEN；收尾固定明确选择及原失败完整性。

GREEN/REGRESSION：r4真实页面三类HTTP均200、同一371 SUCCEEDED、日志无读取错误、零写入，显式产品刷新按钮通过；三次失败JSON/截图保留并核SHA，收尾选择固定新证据pin，success_submission真实文件独立检查PASS。
