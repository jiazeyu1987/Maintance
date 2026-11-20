# 测试服发布验证

## 固定范围
- 目标：test / 172.30.30.58，仅测试服发布。
- 应用提交：152a084c3ebc8eefcddf300f66384e1117b297b9。
- releaseTag：2026-11-20-14-42-40。
- 构建任务：JOB-8e4a355562。
- 菜单范围：5580迁至900120下，名称“排产工单”，路径/permission/sort与当前已提交定义一致；保留900120根级及原角色套餐关联。不据此声称全部菜单与不存在的本机运行态全量对齐。

## 构建前证据
- 真实测试服schema/菜单/账本只读核验；两个新增迁移target-preflight均PASS。
- 真正隔离MySQL验证：4项PASS，含修复、幂等、冲突拒绝、SQL失败不改数据及通知新装迁移链；Node通知迁移2项PASS。合回int_main后同HEAD再次通过。
- 迁移目录903项、1218个artifact通过；本轮测试服预期APPLY两项新增迁移。
- 登录基线：真实Playwright登录和身份PASS_WITH_OBSERVATIONS。3个事件关联两种非关键资源：百度访问统计连接关闭（1个请求失败+1个console），个人头像ORB拒绝（1个请求失败）；来源代码与本轮成功登录证据已关联。正式菜单页面尚待部署后验证。
- 综合构建预检中的审查服旧配置检查失败，保持原失败记录；本轮只测服，目标测试项及本机构建项通过，审查服未执行发布。

## 部署与最终验收
- 测试专用预检JOB-0a38fee0d2 succeeded；publish-test JOB-363a294001 succeeded，技术检查passed；远端OP-6bbaad713cb6c3323708 succeeded。
- 同包manifest摘要07bfdfe4e896701d990f3c26bbd5b9202742cc2060acd55df0f98ddcdf546a23；包摘要ea6e6ec501193143eb391200fc7a7458541d066e144a7f5afd9dc4b64c8d874a。
- IMAGE_TAG、页面和双镜像tag均2026-11-20-14-42-40；后端UP、前端200、maintenance=false、openingPending=false。
- 菜单迁移APPLIED/test，SHA256=48b977ec238a8c8c215ff65b52d664da36d64e0a1af09d83bcdc43daf0e4082b；1941菜单只5580改变，900120保持根级，已查角色关联及套餐不变。
- 真实Playwright登录后点击智能排产→排产工单；权限树5580/900120关系正确；列表与最近成功排产接口code0，当前真实列表0条；版本浮层和10条变更说明与提交一致。
- 页面PASS_WITH_OBSERVATIONS：6原始事件分3组。统计脚本连接关闭（requestfailed+console）与头像ORB（requestfailed）不影响本轮必要路径；个人工作台POST/context被事前只读规则拦截（interception+requestfailed+console），源码确认该请求初始化工作台上下文，工作台不在验收范围。菜单、列表、最近排产及版本请求均实际通过；无其他未知/业务异常。评估人Codex，完整逐项归因、时间窗和脚本摘要见私密page-assessment.json。
- 只证明本次发布基础冒烟及菜单修复；未进行Excel导入/导出或业务写入回归。正式服菜单仍待下次授权发布应用同一修复。

## 私密证据位置
C:/SpugHandoff/release/private/test-menu-release-20261120/。原始运行状态、只读菜单/账本/关联、登录截图及页面事件均在此保存，不提交凭据或业务明细。
