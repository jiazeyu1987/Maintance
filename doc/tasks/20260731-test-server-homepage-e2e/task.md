# 测试服首页只读 E2E 验证

## Task Goal

使用真实浏览器只读访问测试服务器首页 `http://172.30.30.58:8081/`，确认页面是否可达、是否正常渲染、是否存在控制台错误或资源加载失败。

## Milestones

- [x] 创建任务记录并确认测试服访问授权来自用户本轮明确要求。
- [x] 摘取真实 E2E 与测试服务器访问经验门禁。
- [x] 使用 Playwright + 本机 Chrome 访问测试服首页。
- [x] 记录页面 URL、标题、正文、控制台错误、网络失败、截图和结论。

## Expected Verification

- 测试服首页 HTTP 可达。
- 真实浏览器打开页面后应能渲染登录页或已登录首页。
- 控制台无 error，关键资源无加载失败。
- 截图和 JSON 证据保存在 `output/playwright/20260731-test-server-homepage-e2e/`。

## 经验门禁

- Trigger: 真实 E2E / Playwright / 测试服务器前端访问 / `172.30.30.58:8081`。
- Preflight check: 读取 `E:\IntRuoyi\docs\server-access.md` 确认测试服入口；读取 `E:\IntRuoyi\docs\e2e-rules.md` 确认真实浏览器、只读范围和浏览器可执行文件门禁。
- Blocker: 缺少用户授权、测试服入口不在文档中、无可用 Chrome/Edge、或页面无法渲染且无法取得错误证据时停止。
- Verification: 记录入口 URL、最终 URL、HTTP 状态、页面标题、正文片段、控制台错误、失败请求、截图路径。
- Forbidden action: 不登录、不写入业务数据、不访问正式服或备用服、不用 API-only 替代真实页面访问。
- Evidence: 本任务 `execution-log.md` 和 `verification-report.md`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，本次为只读定位访问问题，不修改产品。
- 是否存在临时补丁或绕过：否。

## Current Status

completed
