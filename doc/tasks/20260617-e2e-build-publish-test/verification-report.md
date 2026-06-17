# 独立验收报告: 真实 E2E 构建发布测试服

## 结论

PASS。

目标“完成构建发布”已由当前状态证据证明：发布包 `release-20260617-1654-codeonly-e2e` 已构建成功，已通过真实前端 E2E 操作部署到测试服 `172.30.30.58`，远端前后端镜像 tag 与发布包一致，后端健康，管理前端真实浏览器入口可用，发布所需 DCC 迁移已在测试服落库为 `APPLIED`。

## 验收范围

- 构建范围：`code-only`，组件 `intruoyi`。
- 目标环境：测试服。
- 目标主机：`172.30.30.58`。
- 远端目录：`/opt/intruoyi/runtime`。
- 发布包：`release-20260617-1654-codeonly-e2e`。
- 禁止范围：不访问正式服 `172.30.30.57`，不访问备用服 `172.30.30.59`，不执行备份、恢复、回滚或正式发布。

## 要求到证据

| 要求 | 当前证据 | 结论 |
| --- | --- | --- |
| 通过真实前端 E2E 构建发布包 | `execution-log.md` 记录 Playwright 预览并执行 `build-release`；operation JSON `runtime/runtime-control/op-2026-06-17T085414727300800Z-8359c878-baa8-4ccd-abd4-65e3f2f03ca4.json` 当前 `status=SUCCESS` | PASS |
| 发布包为 code-only | operation 参数 `publishScope=code-only`、`includeOnlyOffice=false`、`includeShowroomBuildPackage=false`；远端 release manifest 返回 `component=intruoyi`、`publishScope=code-only` | PASS |
| 发布包 manifest 存在 | SSH 测试服读取 `/mnt/nas/Backup/ReleasePackage/release-20260617-1654-codeonly-e2e/release-manifest.json` 存在，`artifactCount=2847` | PASS |
| 通过真实前端 E2E 发布到测试服 | `execution-log.md` 记录 Playwright 预览并执行“部署测试服”；operation JSON `runtime/runtime-control/op-2026-06-17T090710635870700Z-11dabe12-ebbe-4311-98da-00b614aec4ec.json` 当前 `status=SUCCESS` | PASS |
| 远端版本与发布包一致 | SSH 测试服读取 `.env` 返回 `IMAGE_TAG=release-20260617-1654-codeonly-e2e`；`docker compose ps` 显示 `intruoyi-backend` 和 `intruoyi-frontend` 镜像均为该 tag | PASS |
| 后端健康 | `curl.exe -s -o NUL -w "%{http_code}" http://172.30.30.58:48081/actuator/health` 返回 `200`；正文验证返回 `{"status":"UP"}` | PASS |
| 管理前端可访问 | `curl.exe -s -o NUL -w "%{http_code}" http://172.30.30.58:8081/` 返回 `200` | PASS |
| 真实浏览器入口可用 | Playwright Chromium 打开 `http://172.30.30.58:8081/`，`responseStatus=200`，跳转到 `/login?redirect=/index`，标题 `瑛泰管理系统 - 登录`，包含“瑛泰数字化平台”和“登录”，console error 为 0 | PASS |
| 发布迁移已应用 | SSH 测试服查询 `infra_release_migration` 返回 `20260617_dcc_browser_performance_indexes APPLIED` | PASS |
| 发布前迁移依赖问题已闭环 | 原后端仓库提交 `c6b549c3e7 任务: 修复DCC浏览索引迁移依赖`；迁移策略门禁与 `script/tests/test_release_migration_policy_gate.py` 均通过 | PASS |
| 正式服/备用服/备份恢复回滚未越界 | 构建和部署预览日志记录未包含 `172.30.30.57`、`promote-prod`、`backup-now`、`rollback`、`restore-data`；本次现时验证仅访问测试服 `172.30.30.58` | PASS |

## 现时验证命令

- `curl.exe -s -o NUL -w "%{http_code}" http://172.30.30.58:48081/actuator/health` -> `200`
- `curl.exe -s http://172.30.30.58:48081/actuator/health` -> `{"status":"UP"}`
- `curl.exe -s -o NUL -w "%{http_code}" http://172.30.30.58:8081/` -> `200`
- `ssh -n root@172.30.30.58 "cd /opt/intruoyi/runtime; grep '^IMAGE_TAG=' .env; docker compose ps ..."` -> `IMAGE_TAG=release-20260617-1654-codeonly-e2e`，前后端容器 `running`
- 迁移状态查询 -> `20260617_dcc_browser_performance_indexes APPLIED`
- Playwright 浏览器验证 -> `responseStatus=200`，`finalUrl=http://172.30.30.58:8081/login?redirect=/index`，`consoleErrorCount=0`

## 边界与残余风险

- 未执行远端测试服登录。原因：`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md` 未提供远端测试服可用账号，且明确要求缺少凭据时不得静默切换账号或环境。本次以真实浏览器验证测试服管理前端入口可达并加载登录页。
- 后端仓库仍存在与本任务无关的既有未提交改动和 runtime 临时文件；本次提交只包含构建发布闭环所需的迁移依赖修复与证据。
- 维护仓库仍有未跟踪 `.codex/` 目录；该目录不是本任务产物，未纳入提交。

## 最终判定

构建发布目标已完成，可视为测试服 `release-20260617-1654-codeonly-e2e` 发布成功。
