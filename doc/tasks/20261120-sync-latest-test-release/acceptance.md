# 测试服发布验收

## 绑定与结论
- 环境：test / 172.30.30.58。仅测试服，无正式或审查晋级。
- releaseTag：2026-11-20-23-36-11；源码3368249ef92ce90b7e401a2f916cf57db67c0c74。
- build JOB-884ecc8d34、预检JOB-badf14ebba、publish JOB-8440398672均succeeded。
- package SHA256：0b8162da560270147159e805b8b4f620d612cb63526593d31142826ff3f39e2e。
- manifest SHA256：b9b4e6173743f3135acf2f55f4a9535a9ad47cb67321047a137701990f27abbf。
- final-runtime-verification.json：PASS。前后端实际镜像ID与清单一致，.env IMAGE_TAG同tag，backend UP、frontend HTTP200，maintenance=false、runtimeOpeningPending=false，technicalStatus=passed。
- 页面判定：PASS_WITH_OBSERVATIONS，评估人：本维护任务。仅证明以下已列明基础冒烟和菜单边界；不代表完整业务E2E。

## 真实页面检查
- 平台账号真实登录成功；通过侧栏进入/mes/pro/schedule-order，页面与latest-success请求均code=0，真实列表返回0条；未造数据。页面版本与sourceCommit同包，版本变更说明10项可见。
- 测试A真实登录用户910251，SRM、CRM系统、AI大模型及已确认的218个排除菜单ID均未返回，侧栏无三个模块。智能排产原有排产员工作台、报工、排程日历、生产排产、璞慧排产入口可见。版本及变更说明同包。
- 测试A首轮误复用了平台“排产工单”菜单预期，等待超时；保留test-a-menu-page.private.json原失败。平台菜单授权不能套用于测试A，修正验证器为目标租户既有五入口，未更改产品或扩大权限。最终test-a-menu-acceptance.private.json记录全部必查PASS，增加networkidle等待后复跑通过。
- 本机IntRuoyi HEAD与origin/int_main均5a67a98d1；与构建目标差异仅三个测试类和两份验证文档，无生产代码差异。应用113项回归证据见应用仓permission-risk-closure.md。

## 全部观察项归因
原始证据位于C:/SpugHandoff/release/private/sync-latest-test-release-20261120，保留脚本、起止时间、截图、checks、observations。凭据未写入记录。

| 证据与事件 | 原因、用途和实际影响 | 处理 |
| --- | --- | --- |
| menu-page.private.json事件1、2；test-a-menu-acceptance.private.json事件1、2 | hm.baidu.com/hm.js连接关闭及对应console；源码src/plugins/tongji/index.ts确认仅生产统计及路由访问统计。两轮登录、菜单、版本和平台排产请求均实际通过，不承担必需页面资源 | nonblocking，外部统计资源问题保留，应用侧后续处理 |
| 平台事件3 | 外部user/avatar图片ORB拒绝；登录后个人头像资源，非认证、菜单、排产或版本数据。平台已验必需动作全部通过 | nonblocking，头像资源配置问题保留，应用侧后续处理 |
| 平台事件4、5、6 | 验证器事前只读保护拦截POST /workbench/context及派生请求/console。src/api/system/profileWorkbenchTodo/index.ts initializeWorkbenchContext用于个人工作台查询上下文；本轮必需业务路径为排产工单，实际请求及页面通过 | nonblocking，仅对本轮基础冒烟。个人工作台待办未验收，不将拦截结果当工作台功能通过 |

最终测试A观察2项，平台6项；不删除原事件、不按域名自动忽略。测试A直接接口越权阻断以应用回归为证据，未执行越权业务写入。未运行Excel导入或完整业务回归。

## 收尾
临时worktree C:/SpugHandoff/release/build/2026-11-20-23-36-11：构建任务自动删除成功，无新提交；最终Test-Path=False、git worktree list无本tag。执行器PID43352仍在原source稳定路径运行，本任务没有新增服务/控制台需恢复。已经过ready_for_closeout，收尾验证通过。

补充实时远端ls-remote先TLS失败、再20秒低速超时；该附加查询未通过，不宣称远端此刻无新提交。发布前fetch/ff-only成功及固定提交来源可验证，此网络问题不推翻已完成的同包发布和验收，也不把附加查询记PASS。
