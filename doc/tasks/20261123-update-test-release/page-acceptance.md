# 测试服真实页面验收

## 第一轮部署后的结论

状态：BLOCKED（打印必需路径）；部署运行态独立PASS。此结论仅对应2026-11-23-20-22-13 / d9022d50a / JOB-fd39bacc82，不可与后续新包拼接。

- 包SHA256：f9ab1873fac7b4493976fee9850784ba159ca5851745a864200fa8c1a71e5803。
- manifest SHA256：bf009b4bc5a31149b52d4ee9b77fd7a154b3034469571f00269a903973c69dd3。
- 入口：http://172.30.30.58:8081；Playwright实际登录只读平台账号，观察器在导航前注册；评估人：维护Agent。
- 私密原始证据：C:/SpugHandoff/release/private/update-test-release-20261123/release-2026-11-23-20-22-13-evidence/，保留两份页面JSON/截图、运行态、配置与脱敏前日志。含票据原文不提交。
- 菜单脚本SHA256：33a1bc34673773ebbf971e2d5bc5e417a881bd74f7301a6c03534e48dfa3fdb5；最终打印脚本SHA256：99fe1617c5b7bc24fce25217b3036bc3f174542c11857d0ea73b91ac94c61035。观察起止时间保留在各JSON的startedAt/endedAt。

## 必需检查

| 检查 | 预期及实际 | 结论 |
| --- | --- | --- |
| 真实登录 | 实际登录返回code0，登录用户身份匹配 | PASS |
| 排产工单 | 从智能排产菜单打开，列表及最近成功排产接口code0，真实空列表如实显示 | PASS |
| 页面版本和说明 | 页面tag/sourceCommit与包一致，版本说明可见 | PASS |
| 打印运行期配置 | status code0/running=true，公开地址为测试18733，内部host保留 | PASS |
| 认证票据 | 前端真实申请返回code0且有票据，不记录票据值 | PASS |
| 助手认证后页面 | 现有菜单搜索打开，callback403，正文系统异常，未到认证后页面 | BLOCKED |

## 全部异常归因

菜单脚本6项；最终打印脚本8项，其中前6项同类，另2项为必需路径错误。逐条原始事件顺序保持，不清空观察数组。

| 事件 | 来源/原因 | 影响与处置 |
| --- | --- | --- |
| 1 requestfailed | hm.baidu.com/hm.js，连接关闭 | 外部访问统计未加载；实际登录、排产数据及版本请求独立成功，不用于本轮业务结果。nonblocking，应用维护外部统计依赖 |
| 2 console | 对应事件1的资源加载失败 | 同事件1，nonblocking；保留原location关联 |
| 3 requestfailed | 外部头像图片，ERR_BLOCKED_BY_ORB | 用户头像未显示；截图可见账号身份及正常业务内容，不影响本轮必要路径。nonblocking，应用维护头像源 |
| 4 interception | /admin-api/workbench/context POST，事前只读保护主动拦截 | 个人工作台显示加载失败是验证器副作用；本轮必需路径为排产、版本、打印，工作台未验，不宣称工作台PASS。nonblocking，仅限明确范围 |
| 5 requestfailed | 对应事件4的blockedbyclient | 同事件4，nonblocking |
| 6 console | 对应事件4的网络失败 | 同事件4，nonblocking |
| 7 http（仅打印） | 助手/auth/callback HTTP403 | 必需认证路径失败，blocking。真实后端日志确认验票缺租户上下文，交IntRuoyi修复 |
| 8 console（仅打印） | 对应事件7 HTTP403资源错误 | 同事件7，blocking；不能按非关键观察放行 |

菜单基础冒烟单独可记PASS_WITH_OBSERVATIONS，整轮因打印仍BLOCKED。Excel导入、打印文件上传/生成、ERP完整业务、不同租户线上隔离与无财务权限场景未在本轮执行，不将单元测试冒充真实业务E2E。

## 新包复测

275c87011修复可信票据租户绑定，新包2026-11-23-22-02-22构建及发布均成功。独立复测结果：PASS_WITH_OBSERVATIONS，旧包结论不改。

- 发布JOB-2b57a4ae44；包SHA256 24568dfcc2d9f46c2876c8f2c19e46461f9ad75bf1abb1384ffab5ffc5788975；manifest SHA256 80bec78be45c2dc0066b70fd3d14215433886f40381d54ac710fca8e7ad2c6dd。
- 新一轮menu-page-check.cjs：真实登录、智能排产/排产工单及实际空列表、版本与变更说明均PASS；tag和commit与新包匹配。
- 新一轮print-page-check.cjs：2026-11-23T15:06:38.336Z至15:06:45.258Z；真实登录、status公开URL、新票据、认证后iframe根页面、版本绑定均PASS。截图实际显示打印助手和服务器已连接，无403或系统异常。
- 两脚本本轮各6项观察，逐项与上表事件1—6对应；均重新核对本轮原始请求、console及截图。不存在事件7—8；未出现pageerror、必需接口失败或未知异常。工作台因只读保护未验，不将其加载失败归为产品正常。
- 运行态独立PASS：operation SUCCESS、双镜像及IMAGE_TAG同tag、manifest摘要一致、backend UP、frontend 200、maintenance=false、runtimeOpeningPending=false、technicalStatus=passed。公开URL与内部assistant-host在实际新容器JAVA_OPTS中均保持。
- 原始新包证据为私密根目录menu-page.private.json/png、print-page.private.json/png、final-runtime-verification.json、print-network.json；公开运行态见本任务runtime-verification.json。
- 已关闭本次已复现的匿名验票缺租户上下文403。不同租户隔离、重复票据和无财务权限拒绝有应用回归证据，未在本轮线上执行，不宣称完整打印业务E2E。外部统计/头像观察及独立注册证提醒业务配置问题不由发布流程擅自修改。
