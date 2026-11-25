# 测试与正式发布结果

- 版本：2026-11-25-10-22-04。
- 产品源码：462d6647fc484ef4d3433a5a640015c9559c37db；通过7890代理同步int_main。随后主线01c362bff仅增加文档，不改变本包产品内容。
- 构建：JOB-dd0cd66f8b；测试发布：JOB-58851b5e0e；测试验收：JOB-9f07f0d8dc；正式晋级：JOB-6eec691c6c；正式开放：JOB-eb73176ba8，均succeeded。
- 两环境包、manifest、IMAGE_TAG及实际前后端镜像一致，后端UP、前端200、维护关闭。正式backupSourceBindingPending=false。
- 数据库契约在迁移后、后端开放前、公开入口开放前均PASS；包含PQC巡检规则检查。
- 真实页面：测试公开入口、正式维护入口与正式公开入口的登录、排产菜单读取、版本和变更说明、打印助手票据及认证iframe均通过。
- 限定验收PASS_WITH_OBSERVATIONS：每组页面有统计服务连接失败2条、外部头像ORB1条、预声明工作台写入拦截及其网络/控制台反馈3条，逐项核实，不把它们写成无错误。未验证完整入单流程、工作台写入或实际打印；未补业务数据。
- 用户明确排除59，未执行promote-backup，不宣称三服务器完整闭环。

## 原阻塞与处理

1. 7890代理Git TLS握手失败，按原代理重试成功，未关闭TLS验证。
2. ERP两项SQL未登记，IntRuoyi正式提交a330c9004修复，并登记PQC聚合明细字段可空迁移。
3. 注册证导入权限迁移缺目标预检，通知IntRuoyi后提交462d6647f修复。重新固定提交构建，未跳过门禁。
4. 测试schema摘要漂移：只读完整schema对比及内存反向修改摘要证明，仅production_submit_event_id可空状态改变，恰为本次迁移目标。保留历史执行者未知结论，使用正式只读基线登记后重跑预检。
5. 单独构建诊断硬编码检查59曾失败；代码复核确认其不是实际build-release的必需前置。保留失败，实际构建未实时访问59，58/57分别完成目标预检。

## 命令与证据

构建与发布经稳定executor的actions.py action build-release / publish-test / mark-tested / promote-prod / accept-prod执行。页面使用menu-page-check.cjs与print-page-check.cjs，显式传入tag、full及完整提交；运行态使用final-runtime.py，源镜像按manifest ID与tag双重核对。私密原始证据保存在C:/SpugHandoff/release/private/test-prod-20261125，公开脱敏结果见release-result.json。

本任务无维护工具实现变更，不伪造功能RED/GREEN；实际发布失败及修复后的成功记录保留于execution-log.md。应用实现验证由IntRuoyi提供迁移输入、目标预检反向测试及相关合同测试证据。
