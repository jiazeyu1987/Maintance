# 正式发布按钮真实 E2E 计划

## Purpose and Scope

规定按钮必须通过 Playwright 从真实页面操作验证。API 只用于最终只读核验，不能代替点击路径。测试分为本地/测试服资格验证和经独立授权后的正式服发布验证。

## Evidence Reviewed

- 项目规定 E2E 必须真实登录、只用前端操作；接口仅最终验证。
- 正式服务器、登录方式和权限必须从 `E:\IntRuoyi\docs\server-access.md` 与 `login-access.md` 获取。
- 现有前端已有 runtime-control 页面和 real-flow 测试骨架，但旧测试可能走通用 action API，不能代替新 workflow 按钮路径。

## User Paths

### E2E-PROD-READINESS 本地/测试服只读资格路径

1. 使用已授权的测试租户账号登录本机或测试服运行控制台。
2. 打开运行控制台真实菜单，确认专用权限投影与按钮显示。
3. 选择非 TESTED 工作流，确认按钮禁用并显示原因。
4. 选择真实 TESTED 工作流，点击按钮进入 production preview。
5. 在没有正式服访问授权的阶段，preview 必须使用隔离 fixture/本地合同环境或明确阻断，不得探测正式服。
6. 验证确认框字段、`PROD` 校验、关闭/取消和错误展示；不提交生产写入。

### E2E-PROD-REAL 经授权的真实正式发布路径

1. 在任务日志先记录 `GREEN: experience-preflight -> PASS`、正式服授权范围、releaseTag、生产窗口和恢复负责人。
2. Playwright 登录运行控制台，使用具有专用生产权限的真实账号。
3. 选择同一 `TESTED` workflow，核对 releaseTag/digests/test evidence。
4. 点击“发布到正式服务器”，等待真实只读 preview 完成。
5. 核对所有 checks PASS 和目标为正式服务器；若任一 blocker，停止，不输入 PROD。
6. 填写任务标识原因并输入 `PROD`，点击最终确认一次。
7. 记录 workflowId/operationId，观察阶段直到终态；不重复点击。
8. 成功后 Playwright 打开正式前端，通过真实登录页只读登录，确认页面标题、版本标识和关键入口可加载。
9. 只读 API/SSH 最终核验 operation、manifest、`.env`、实际镜像、health、HTTP、release-info 和锁。
10. 只读核对审查服未创建本任务 promote operation、版本未被本任务改变。

## Browser or Client Steps

- 只使用项目固定 Playwright 版本和既有浏览器路径。
- 登录凭据从授权渠道提供，不写入脚本 snapshot、日志或任务文档。
- 通过可访问名称定位“发布到正式服务器”、工作流选择器、preview 检查项、原因和 `PROD` 输入。
- 监听页面错误、console error 和 failed request；非预期错误使 E2E 失败。
- 页面刷新一次以证明服务端可恢复 operation 状态。
- 不通过 `page.evaluate(fetch(...))` 创建发布；点击是唯一写入入口。

## API Verification

仅在页面操作完成后只读检查：

- workflow detail/stateVersion/evidenceRefs。
- production operation status/action/environment/releaseTag。
- release status 的 prodCurrentReleaseTag。
- backend health 与 frontend/release-info HTTP。
- 服务端固定目标和审查服未触发状态。

SSH/数据库只读验证必须按服务器和 PowerShell 文档执行、脱敏并核退出码；无授权则不执行。

## Console and Log Checks

- 浏览器 console 不得有新未处理异常。
- preview/authorize/promote 请求不得包含 host/path/script/credentials。
- operation 日志不得包含明文密码、token、私钥、连接串或完整 `.env`。
- 结构化阶段必须推进；静默日志期间 lastProgressAt 仍可判断活跃。
- 每种终态只出现一次通知。

## Test Blockers

- 未获得正式服明确授权、专用账号、生产窗口或恢复负责人时，`E2E-PROD-REAL` 必须保持 blocked。
- 没有真实 TESTED workflow 或包摘要/测试证据缺失时停止。
- 页面没有新按钮真实入口时 fail fast，不得用 API-only 替代。
- 正式服 preview 任一 blocker、活动环境锁或 `RECOVERY_REQUIRED` 时停止，不得为测试修改正式数据或台账。
