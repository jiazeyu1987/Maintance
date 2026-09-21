# R10 Security And Privacy Review

## Scope And Evidence

仅审查本地主程序正式预览/权限与本次 Playwright 只读验证。源码提交 `c8edc935c`、维护脚本 `1ce47ef`；证据在本任务 execution-log、verification-report 及任务输出目录。未连接正式服务器、未发布。

## Data Classification And Privacy

工作流标识、releaseTag、包 SHA、测试 operation 路径是运维敏感元数据；用户凭据、Cookie、token、数据库连接密码属于秘密。本轮页面截图和网络 JSON 只保留页面、方法/路径/HTTP 状态，未存登录请求体或授权头。既有本机运行进程命令行含连接参数，原始输出不进入仓库。

## Authentication And Authorization

生产路由要求独立 `infra:runtime-control:promote-prod`；通用 `/actions` 发布路径仍拒绝。正式预览读实际包/tested/操作证明与发布器 SHA，失败变 BLOCKED；`requireBinding` 在授权和派发前重检证据指纹。组件测试覆盖无 grant、TESTED 状态不变、无生产 operation。测试租户 122 的既有 query/operate/restart 角色菜单只读核对；新增 promote 权限未在本机执行迁移，不给其它角色自动赋权。admin 登录仅作用户已有授权的本机只读对照，未替代测试租户权限验收。

## Secrets And Configuration

本任务 JAR 运行时 `production-write-enabled=false`，批准维护/应用提交与维护脚本实际字节 SHA 已在进程参数核对。JAR/JVM 日志和截图置于不提交的任务输出目录；本机测试租户登录密码缺少安全来源，不猜测或复用 admin 密码。

## Dependencies And Supply Chain

前端使用工作树锁文件固定 Playwright 1.60.0 与指定 Chromium 1223；未临时安装新版本。真实 PowerShell 模块在本机直接验证标准 operation 证明，不使用复制的业务算法冒充发布执行器。

## Logging Audit Retention

代码层 operation 和 preview/grant 有状态版本与证据指纹约束；本轮没有新的生产 operation。页面网络证据仅含脱敏字段，截图/临时本地运行日志保留在任务输出目录，后续按任务收尾规则清理本任务资源，禁止提交秘密日志。

## Policy Gates And Findings

| Severity | Owner | Status | Evidence / impact |
|---|---|---|---|
| P0 | 发布任务/独立审阅 | BLOCKED | 第十轮审阅仍未“同意发布”，不得构建或部署 |
| P1 | 本任务 | PASS（组件） | 实际证明漂移在预览、授权、派发前阻断；未声称真实 NAS/服务器验收 |
| P1 | 本任务/用户输入 | BLOCKED | 测试租户凭据缺失，不能通过真实登录证明独立权限拒绝 |
| P1 | 本任务/环境 owner | BLOCKED | 本地 UI 自动远端状态只读探测触发脚本错误，尚未明确后续远端只读边界 |

未做法规合规或生产安全认证结论。所有 BLOCKED 项继续阻断发布与独立复检放行申请。

## Blockers

测试租户真实登录凭据、远端只读检查边界和独立审阅的“同意发布”结论均未具备；本机也没有可供真实页面验收的合格 TESTED 包。
