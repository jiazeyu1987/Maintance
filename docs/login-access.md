# 登录访问与验证边界

> 路径约定：`docs/...` 相对本维护仓根目录；`IntRuoyiBackend/...`、`IntRuoyiFronted/...` 及其源码命令相对当次已验证配置确定的主程序根目录。不依赖盘符，不猜测源码目录。此文件沿用交接资料中的规则；当前用户授权和 AGENTS.md 优先。

登录验证先读取 `docs/server-access.md`，并核对当次已授权环境、实际入口和当前任务配置。

- 本机前端入口为 `http://localhost:8081`；本机后端健康检查为 `http://127.0.0.1:48081/actuator/health`。
- 按当前 AGENTS.md，真实写入 E2E 使用“测试租户 / aoteman”；“芋道源码 / admin”仅做最终只读验证。不得将旧交接文档中的默认管理员账号规则扩大为写入授权。
- 密码、token、Cookie、私钥由本机受保护配置读取，不写入本文档、任务记录或提交。未迁移的私密凭据保持原样；缺失时停止对应登录验证，不猜密码或重置账号。
- 通过真实页面登录后操作；接口只作最终核验。只读复用已有真实数据，写入仅通过测试租户真实页面创建可追踪、可清理的任务数据。
- 菜单异常先核 `system_menu`、`system_role_menu` 和 `get-permission-info`，不得去掉权限检查或隐藏真实请求错误。
- 默认只访问本机。测试服、正式服、审查服均须有当次任务授权，正式服/审查服按生产等级对待。

交接原文包含明文凭据和与当前写入租户边界冲突的旧默认身份，因此未整份复制；原文保留在私密交接资料，本文件只保留当前适用规则。

### 发布后页面登录基线门禁

- Trigger: 测试、正式或备用环境发布后，需要用 Playwright 验证真实登录、业务页面或版本浮层。
- Preflight check: 发布前只读确认测试租户账号可登录、密码未过期、租户选择接口有目标租户；凭据只能由当前进程安全注入，不写入任务文档或截图。
- Blocker: 登录返回密码过期/账号密码错误、租户选择无目标、入口不可达、必要页面/资源/接口失败或异常影响未知时，认证后页面门禁必须 BLOCKED；不能猜密码或改账号。所有浏览器异常按[发布页面验收规则](release-page-acceptance.md)逐项归因，不能仅按console错误数量放行或阻断。
- Verification: 统一采用[发布页面验收规则](release-page-acceptance.md)的PASS、PASS_WITH_OBSERVATIONS、BLOCKED判定和记录格式。保留全部console/pageerror/失败请求及业务code证据；非关键外部资源或验证器主动拦截仅在该规则全部条件满足时记观察通过。公共登录页、技术登录、认证后基础冒烟与完整业务回归分别注明范围。
- Forbidden action: 禁止冒用本机 admin 密码登录远端测试租户、切换正式/审查环境、API-only 冒充页面、为验收修改租户/用户密码或把过期凭据写进脚本。
- Evidence: 原账号/登录边界源自IntRuoyiMaintance task 20260823-fix-training-rules-sfc-test-release ISSUE-016；异常影响判定以统一规则为准，变更依据见`doc/tasks/20261119-update-and-release-prod/acceptance-policy-log.md`。历史验收结果不因规则更新自动改写。
