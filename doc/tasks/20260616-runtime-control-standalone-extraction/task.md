# 任务：拆分运行控制台独立应用

## 任务目标

在 `D:\ProjectPackage\Int\IntRuoyiMaintance` 创建可独立运行的运行控制台本机应用，默认仅监听 `127.0.0.1`，不接入芋道登录、角色、菜单权限；新应用通过显式配置管理现有 IntRuoyi 后端、前端、Website 源码路径，保留运行控制台的命令预览、操作记录、发布/备份/恢复/重启脚本入口和 fail-fast 门禁。

## 经验门禁

- 已读取 `docs/experience-index.md`。
- 命中 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：构建发布、备份、恢复、回滚、运行控制台真实动作必须走受控入口；候选、日志、恢复集不得用 mock 成功；正式服未授权不得写入。
- 命中 `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：服务器访问、重启、远端联调前必须确认目标主机和授权范围；凭据不得写入仓库、脚本、任务文档或运行控制台配置。
- 命中 `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`：前端页面沿用运维控制台密集、可扫描、工作型风格，不做营销页或无关视觉重设计。
- 本任务验证阶段不执行真实发布、备份、恢复、回滚、重启、远端清理、数据库写入或服务器写入；若后续进入真实动作，必须先在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；缺少脚本、配置、源码路径、运行依赖时 fail fast。
- 是否从根因和长期维护角度解决：是；拆分为独立 Spring Boot + Vue 应用，由新 Git 仓库管控，配置显式指向被管理源码。
- 是否存在临时补丁或绕过：否；本次不通过 mock 成功或隐藏错误满足验证。

## BDD 场景

- BDD: 独立应用本机启动 -> Given 新仓库包含后端、前端、配置示例和脚本 / When 执行构建与启动命令 / Then 应可访问 `http://127.0.0.1:48181/` 与 `/actuator/health`。
- BDD: 无芋道权限依赖 -> Given 用户打开独立运行控制台 / When 页面加载和调用运行控制台接口 / Then 不要求登录、菜单、角色或 `infra:runtime-control:*` 权限。
- BDD: 运维动作 fail fast -> Given 脚本、源码路径或 NAS 配置缺失 / When 用户预览或执行动作 / Then 后端返回明确缺失前置条件，不返回默认成功。
- BDD: 高风险动作不在本次验证执行 -> Given 本任务只做独立化交付 / When 运行自动验证 / Then 不执行真实发布、备份、恢复、回滚、重启或远端清理。

## 里程碑

1. 创建新仓库骨架、复制 `AGENTS.md`、建立任务文档和经验门禁。
2. 先写 RED 检查：后端契约、前端无权限依赖、启动配置 fail-fast。
3. 实现独立后端、前端、脚本复制、配置示例和一键启动脚本。
4. 执行 GREEN 验证：后端测试、前端类型检查/构建、整体构建、启动健康检查、Playwright 只读页面验证。
5. 初始化 Git 并仅提交本任务在新仓库产生的文件。

## 预期验证

- `mvn -f backend/pom.xml test`
- `pnpm --dir frontend install --frozen-lockfile`
- `pnpm --dir frontend typecheck`
- `pnpm --dir frontend build`
- `.\scripts\build.ps1`
- `.\scripts\start.ps1` 后访问 `http://127.0.0.1:48181/actuator/health`
- Playwright 打开 `http://127.0.0.1:48181/`，确认页面显示运行控制台且无浏览器 console error。

## 当前状态

- status: completed
- 状态：已完成。
- 已完成：复制 `AGENTS.md`，建立任务目录、经验索引和请求记录；实现独立 Spring Boot 后端、Vue 3 前端、配置示例、脚本复制和一键构建/启动脚本。
- 已验证：后端测试、前端冻结安装、类型检查、前端构建、整体构建、健康端点、Playwright 页面与命令预览。
- 收尾：task-closeout-cleanup preview 建议删除额外证据页，保留 `task.md` 与 `execution-log.md`。
- Git：初始化 `int_main` 并提交本任务文件，提交信息 `任务: 拆分运行控制台独立应用`。
- 阻塞项：无。

## Current Status

completed
