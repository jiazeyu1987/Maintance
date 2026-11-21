# 正式服发布验收

- 目标172.30.30.57，同包2026-11-20-23-36-11，源码3368249ef92ce90b7e401a2f916cf57db67c0c74；未重建或混入后续改动，未晋级审查服。
- 预检JOB-f997ae2836、正式部署JOB-02dc0e43d6、开放JOB-3c06d8e213全部succeeded。实际远端部署OP-efed0e9b744e2d6a4601。
- 包SHA256：0b8162da560270147159e805b8b4f620d612cb63526593d31142826ff3f39e2e；清单SHA256：b9b4e6173743f3135acf2f55f4a9535a9ad47cb67321047a137701990f27abbf。
- 独立final-runtime-verification.json PASS：实际双镜像ID/name与清单一致，.env IMAGE_TAG同tag，后端UP、前端200、maintenance=false、runtimeOpeningPending=false，无活动发布任务。
- 恢复沿用已确认external策略，独立恢复责任记录保留；本轮不宣称生成全量恢复快照或完成恢复演练。

## 页面验收
维护入口38084和开放入口8081均以Playwright真实登录；侧栏智能排产下排产工单可打开，page及latest-success业务code0，真实数据0行，同包版本浮层及10条变更说明通过。未用SQL/API写入替代页面，未修改租户或业务数据；不宣称完整业务E2E。

两轮均PASS_WITH_OBSERVATIONS，每轮6个事件完整保存在private/prod-promotion-20261121的prod-maintenance-page.private.json与prod-open-page.private.json（含时间窗口、checks、截图）。评估人为本维护任务：

| 事件 | 归因和影响 | 结论 |
| --- | --- | --- |
| 1/2 | hm.baidu统计脚本连接关闭及console；同包tongji插件仅统计路由访问。本轮登录、菜单、必需数据、版本均实际通过 | 非阻断，应用侧统计资源待处理 |
| 3 | 外部个人头像图片ORB拒绝，非认证或排产数据资源；本轮必要功能通过 | 非阻断，应用侧头像资源待处理 |
| 4/5/6 | 事前只读保护拦截workbench/context POST及派生请求/console；该路径为个人工作台查询上下文，本轮必需路径排产工单实际成功 | 非阻断，仅限所列范围，不宣称个人工作台功能通过 |

## 执行限制与记录缺口
第一次真实开始发布被误称预览，未在点击前追加经验门禁PASS；未倒填，详细证据留execution-log。正式用户授权、同包测试及正式专属预检均已具备。Spug状态页一次HTML解析错误及开放响应超时后，均以原任务实际状态续查，未重复派发。

本轮仅晋级既有不可变包，由稳定安装态执行器和远端独立attempts/JOB-02dc0e43d6执行，不在主开发区构建或运行发布源码；没有新建应用worktree。原构建worktree已在测试发布收尾删除。未重启或改动运行控制台，后续收尾核稳定路径。
