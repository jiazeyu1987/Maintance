# 正式服页面验收

## 绑定与范围

环境prod57；releaseTag 2026-11-23-22-02-22；源码275c870118f8096328d94bd38700455de3e76fc0；包SHA256 24568dfcc2d9f46c2876c8f2c19e46461f9ad75bf1abb1384ffab5ffc5788975；晋级JOB-0ee3f179cb。评估人：维护Agent。

必要范围：Playwright真实登录、智能排产→排产工单实际列表、版本和变更说明、通过菜单搜索进入打印助手，status正式公开URL、真实票据及受认证iframe根页面。正式平台账号仅只读；预先阻断业务写入，允许登录/captcha/临时票据。不执行上传、打印包生成、ERP业务写入、Excel导入或完整个人工作台验收。

## 维护入口验收

入口http://172.30.30.57:38084，打印目标http://172.30.30.57:18733/。

- 菜单观察窗口2026-11-23T16:32:41.759Z—16:32:46.976Z：真实登录PASS；排产工单及最近成功排产请求code0，实际空列表rows=0；页面版本/sourceCommit及变更说明与候选一致。
- 打印观察窗口2026-11-23T16:32:55.338Z—16:33:00.941Z：真实登录PASS；status code0/running=true/正式18733 URL正确；新票据成功；iframe实际进入18733根页面，截图显示服务器已连接；版本绑定PASS。
- 两脚本均在导航前记录console/pageerror/requestfailed及必需API业务code。各6项观察，以下逐项评估；无pageerror、必需HTTP/业务错误或未知影响。
- 结论：PASS_WITH_OBSERVATIONS。此阶段仅证明维护入口，不冒充公开入口已开放。

## 全部观察逐项归因

| 事件（每脚本相同6项） | 证据与原因 | 影响、处置与归属 |
| --- | --- | --- |
| 1 requestfailed | hm.baidu.com/hm.js连接关闭 | 外部统计脚本未加载；本轮真实登录、排产请求、版本和打印认证独立通过。非必要路径，nonblocking；应用维护外部依赖 |
| 2 console | 对应事件1资源错误，location匹配 | 同事件1，nonblocking，保留原事件 |
| 3 requestfailed | 外部头像ERR_BLOCKED_BY_ORB | 截图头像未加载，账号身份及业务内容正常；不参与本轮必要业务结果。nonblocking；应用维护头像来源 |
| 4 interception | /admin-api/workbench/context POST被事前只读规则拦截 | 主动避免正式业务写入；不属于排产/版本/打印必要路径。个人工作台未验，其加载失败不认定产品正常。nonblocking，仅限已声明范围 |
| 5 requestfailed | 对应事件4 blockedbyclient | 同事件4，nonblocking，保持原计数 |
| 6 console | 对应事件4网络错误，location匹配 | 同事件4，nonblocking，保持原计数 |

私密证据：C:/SpugHandoff/release/private/promote-prod-print-20261123/maintenance-acceptance/，两份脚本、JSON、截图保留。公开记录不含票据和个人原始数据。

## 公开入口最终验收

开放JOB-b530c70f8e succeeded后，入口http://172.30.30.57:8081重新独立登录操作：

- 菜单观察窗口2026-11-23T16:42:23.361Z—16:42:30.704Z：3项必要检查全部PASS（登录、实际列表/接口、版本及说明）；脚本SHA256 a2131de5fcc4793bf7a3fca6d9d482614df4b546e9a0d1e96a09a89e6a101356。
- 打印观察窗口2026-11-23T16:42:32.463Z—16:42:37.613Z：4项必要检查全部PASS（登录、正式URL、新票据与真实iframe、版本绑定）；截图再次显示服务器已连接；脚本SHA256 62a0d7ee71a2add85fcb6b43253ca2825767283244977e610c5ff2b1c2dd6448。
- 两脚本各6项观察，逐条核本轮记录仍与上表1—6匹配，workbench来源为8081；无新增、未知或关键路径错误。最终PASS_WITH_OBSERVATIONS。
- 独立实际运行态PASS：双镜像ID/tag、manifest及.env IMAGE_TAG一致；backend UP、frontend HTTP200、maintenance=false、runtimeOpeningPending=false。内部助手DNS和正式公开URL均在重启后的JAVA_OPTS保持。
- 原始公开入口证据位于上述私密根目录，未覆盖维护入口证据；未执行上传发票/生成打印包/真实ERP查询等完整业务回归。
