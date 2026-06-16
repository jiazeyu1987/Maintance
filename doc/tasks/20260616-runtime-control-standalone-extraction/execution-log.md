# 执行记录：拆分运行控制台独立应用

BDD: 独立应用本机启动 -> Given 新仓库包含后端、前端、配置示例和脚本 / When 执行构建与启动命令 / Then 应可访问 `http://127.0.0.1:48181/` 与 `/actuator/health`。

BDD: 无芋道权限依赖 -> Given 用户打开独立运行控制台 / When 页面加载和调用运行控制台接口 / Then 不要求登录、菜单、角色或 `infra:runtime-control:*` 权限。

BDD: 运维动作 fail fast -> Given 脚本、源码路径或 NAS 配置缺失 / When 用户预览或执行动作 / Then 后端返回明确缺失前置条件，不返回默认成功。

BDD: 高风险动作不在本次验证执行 -> Given 本任务只做独立化交付 / When 运行自动验证 / Then 不执行真实发布、备份、恢复、回滚、重启或远端清理。

- INFO: 本任务涉及运行控制台拆分，但验证阶段不执行真实发布、备份、恢复、回滚、重启、远端清理、数据库写入或服务器写入。

- RED: `python -X utf8 scripts\verify_contracts.py` -> FAIL, expected reason: 独立后端入口尚不存在，缺少 `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlController.java`。

- GREEN: `mvn -f backend/pom.xml test` -> PASS；后端契约测试覆盖无 Spring Security/PreAuthorize、缺失配置 fail-fast、`/admin-api/infra/runtime-control/*` 与 `/actuator/health`。

- GREEN: `python -X utf8 scripts\verify_contracts.py` -> PASS；独立运行控制台后端、前端、脚本、配置和 `.gitignore` 契约均存在。

- GREEN: `pnpm --dir frontend install --frozen-lockfile` -> PASS；使用 `pnpm-lock.yaml` 冻结依赖安装。

- GREEN: `pnpm --dir frontend typecheck` -> PASS；Vue 3 独立页面与 API 类型检查通过。

- GREEN: `pnpm --dir frontend build` -> PASS；Vite 生产构建通过，产物写入 `frontend/dist`。

- GREEN: `.\scripts\build.ps1` -> PASS；脚本检查 Java/Maven/Node/pnpm，执行前端安装、类型检查、构建，复制静态资源并打包 Spring Boot jar。

- GREEN: `.\scripts\start.ps1` + `curl.exe -s http://127.0.0.1:48181/actuator/health` -> PASS，返回 `{"status":"UP"}`。

- GREEN: Playwright `open http://127.0.0.1:48181/` + `snapshot` + `console error` + `requests` -> PASS；页面显示“运行控制台”，发布包接口错误以页面告警显示为 `NAS username is required`，浏览器 console error 为 0。

- GREEN: Playwright 点击“预览命令” -> PASS；弹窗显示 `build-release` 命令预览，未执行真实动作。

- INFO: 验证期间未执行真实发布、备份、恢复、回滚、重启、远端清理、数据库写入或服务器写入。

- GREEN: task-closeout-cleanup preview -> PASS；建议删除额外证据页，保留 `task.md` 与 `execution-log.md`，无 blocked/warnings。

- BLOCKER: task-closeout-cleanup apply -> Task status must be completed for apply mode, current status: unknown；已补充机器可读 `status: completed` 后重试。

- GREEN: task-closeout-cleanup apply -> PASS；删除额外证据页 `backend-api-evidence.md` 与 `frontend-feature-evidence.md`，保留 `task.md` 与 `execution-log.md`。

- INFO: 准备初始化 Git 仓库，默认分支 `int_main`，仅提交本任务新仓库文件。
