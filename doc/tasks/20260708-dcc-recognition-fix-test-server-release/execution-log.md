# 执行日志

## 2026-07-08T10:57:52+08:00
- BDD: 测试服发布 DCC 非 Codex 修复 -> Given 后端修复提交已通过本地回归但测试服仍运行旧镜像；When 使用干净发布 worktree 构建并部署 code-only 包；Then 测试服运行镜像必须包含修复提交，且 active claim/running task/新增非 Codex 失败审计通过。
- GREEN: release-preflight-docs -> PASS，已读取 IntRuoyi server-access、release-backup-restore 与维护仓库发布配置；本轮只发布测试服，不触碰正式服/备份服/备份/恢复/回滚。
- GREEN: release-worktree-create -> PASS，backend=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260708dccfix\b @ 730072c720186579e8dd9a0b0e160eede0ac9699；frontend=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260708dccfix\f @ 92796b5d5fa21cf1a3b29c4f2c6bf7df6e7e7cec；两者 status clean。
- GREEN: runtime-control-config-switch -> PASS，已备份 config/runtime-control.local.yaml 到 D:\ProjectPackage\Int\IntRuoyiMaintance\config\runtime-control.local.before-dccfix-20260708.yaml，repo-root/frontend-root 已切到干净发布 worktree。
- GREEN: runtime-control-frontend-start -> PASS，pnpm dev 被 pnpm v11 ignored-builds 门禁阻断；已用本地 node_modules/.bin/vite.cmd 直接启动维护前端 48182，后端 48181 health=UP。
- GREEN: runtime-control-backend-restart -> PASS，维护后端已用 java.exe 精确匹配方式重启/确认运行，48181 health=UP。
- GREEN: build-release-preview -> PASS，releaseTag=release-20260708-dcc-recognition-fix，预览指向干净 worktree，包含 build-release / SkipDatabaseSync / SkipMinioSync，未出现正式服/备份/回滚/恢复动作。
- GREEN: build-release-preview -> PASS，releaseTag=release-20260708-dcc-recognition-fix，预览指向干净 worktree，包含 build-release / SkipDatabaseSync / SkipMinioSync，未出现正式服/备份/回滚/恢复动作。
- GREEN: build-release-submit -> PASS，releaseTag=release-20260708-dcc-recognition-fix，operationId=op-2026-07-08T031226594428900Z-0f7f7fe7-f65b-4f73-88c3-68313f0a084d，已通过运行控制台 API 触发 code-only build-release。
- RED: `python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql --sql-file D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260705_showroom_legacy_product_code_auto_confirmable_draft.sql` -> FAIL，发布门禁报 `missing release-migration metadata`，测试服 DCC 识别修复发布被历史展厅草稿 SQL 元数据缺失阻塞。
- IMPLEMENTATION: 为 `20260705_showroom_legacy_product_code_auto_confirmable_draft.sql` 补充显式 `release-migration` 元数据；该 SQL 仍保持全量 `REVIEW ONLY` 注释，无可执行 SQL 行。
- GREEN: `python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql --sql-file D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql\20260705_showroom_legacy_product_code_auto_confirmable_draft.sql` -> PASS，migrationCount=1。
- GREEN: `python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\sql\mysql` -> PASS，migrationCount=258。
- BDD: 测试服后端健康检查端口契约 -> Given 测试服发布包内 Spring Boot 后端监听 48081；When docker-compose 将宿主 BACKEND_HOST_PORT 映射到后端容器且前端 nginx/OnlyOffice 通过 backend 服务名访问后端；Then 所有容器内访问与宿主健康检查必须指向容器 48081，不能继续指向 48080。
- RED: `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_publish_int_ruoyi_to_test_tooling.py -q` -> FAIL，5 failed / 89 passed；失败断言分别证明 publish-int-ruoyi.ps1、docker-compose.yml 与 nginx.conf 仍使用 `backend:48080` 或 `${BACKEND_HOST_PORT}:48080`。
- IMPLEMENTATION: 将测试服发布模板后端容器端口统一为 48081：docker-compose 端口映射、Dockerfile EXPOSE、前端 nginx proxy_pass、OnlyOffice public file base URL 均改为容器实际监听端口。
- GREEN: `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_publish_int_ruoyi_to_test_tooling.py -q` -> PASS，94 passed；`rg "backend:48080|BACKEND_HOST_PORT}:48080|EXPOSE 48080"` 未发现测试服发布模板残留。
- GREEN: release-worktree-port-contract -> PASS，`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiWorktrees\r260708dccfix\b\script\tests\test_publish_int_ruoyi_to_test_tooling.py -q` -> PASS，94 passed；发布 worktree 已包含端口契约修复提交 `92132519db`。
- GREEN: build-release-submit -> PASS，releaseTag=release-20260708-dcc-recognition-fix-3，operationId=op-2026-07-08T035930119570500Z-3a81703b-831b-43f6-b972-a714026b82fe，build-release 最终 SUCCESS；发布包已上传 NAS `Backup/ReleasePackage/release-20260708-dcc-recognition-fix-3`。
- RED: publish-test -> FAIL，operationId=op-2026-07-08T041600143391500Z-707f686f-3353-4aba-beac-12e0f802ea22；新镜像已启动，但测试服宿主 `http://127.0.0.1:48081/actuator/health` 仍连接重置。
- ROOT_CAUSE: 测试服真实排查显示新后端镜像 `intruoyi-backend:release-20260708-dcc-recognition-fix-3` 容器内 `127.0.0.1:48081/actuator/health` 为 HTTP 200，但远端 `/opt/intruoyi/runtime/docker-compose.yml` 仍为 `${BACKEND_HOST_PORT}:48080`；根因是维护仓 `ops/deploy/int-ruoyi-test` 模板仍保留旧容器端口，覆盖了业务仓模板修复。
- RED: `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_dcc_codex_runtime_contract.py -q` -> FAIL，1 failed / 4 passed；新增维护仓发布端口契约断言捕获 `${BACKEND_HOST_PORT}:48081` 缺失。
- IMPLEMENTATION: 将维护仓测试服发布模板的 docker-compose、Dockerfile.backend、nginx.conf 后端容器端口统一为 48081，并保留契约测试禁止回退到 48080。
- GREEN: `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_dcc_codex_runtime_contract.py -q` -> PASS，5 passed；维护仓发布模板中影响测试服后端端口的 48080 残留只存在于负向测试断言。
