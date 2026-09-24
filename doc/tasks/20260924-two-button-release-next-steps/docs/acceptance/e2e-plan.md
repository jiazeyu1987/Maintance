# 两入口真实页面验收

## Purpose and Scope
证明用户仅用页面和必要确认即可完成测试服发布及同包正式晋级。禁止API、手工脚本提交或mock成功代替真实按钮。

## Evidence Reviewed
现有index.vue、productionDialog、专用workflow API、同tag发布及页面隐式远端GET门禁。

## User Paths
路径A：真实登录→运行控制台→批准版本/原因→发布到测试服一次→自动构建/部署→测试服版本说明和业务页面验证。
路径B：选择路径A同一workflow→晋级正式服→真实验收/恢复候选→预览→确认→正式运行态与页面验证。

## Browser or Client Steps
- 固定Playwright1.60.0及规定浏览器；默认测试租户，明确例外授权记录范围。
- 独立GO前只做已授权本地/组件验证；页面mount也可能远端GET，配置必须阻断未授权环境。
- 新提交GO后用新专用发布输入及新tag；不能再用第二个部署按钮补齐自动编排缺口。
- 点击后刷新/关页/重新登录仍能查同一operation，重复请求不能新增部署。故障注入只在专属隔离环境进行，不盲杀正式写入。
- 正式确认前核对包身份、预检和授权；取消不派发。请求证据去掉认证头、口令和secret，页面必须暴露真实错误。

## API Verification
页面发起后接口仅作最终只读核验：workflow、operation、测试证据、源提交与双摘要一致。还须核远端IMAGE_TAG、实际镜像tag、health=UP、HTTP200和页面版本说明。

## Console and Log Checks
检查console/page错误、失败请求、UTF-8、脱敏和当前时间窗；不得用旧tag报告或单个HTTP200代替整条发布通过。

## Test Blockers
入口/权限缺失、包校验失败、锁归属不明、验收/恢复候选缺失、目标漂移或无独立GO时停止。不得为测试增加专用控件或绕过后端门禁。
