# 20260829 优化 deploy 控制文件上传

## Task Goal

继续优化测试服发布链路耗时：检查 `deploy-release` 主流程中 compose/env/小 SQL/website runtime 等控制文件上传是否仍存在可安全合并的 `scp` 往返；优先将小型控制文件或目录打包后单次上传、远端解包校验，减少下次发布等待时间，同时保持镜像 tar、数据库 dump、大文件传输、manifest、releaseTag 和 fail-fast 语义不变。

## Milestones

1. 启动门禁与任务文档：记录范围、BDD、预期验证和经验门禁。
2. 代码合同盘点：定位 deploy 主段可合并的小文件上传路径。
3. RED 合同测试：新增测试证明目标控制文件仍分散上传。
4. GREEN 实现：最小化增加控制文件归档上传/解包校验，保留缺文件 fail-fast。
5. 回归验证与收尾：运行目标合同、发布合同回归、PowerShell AST、差异检查、经验沉淀和任务收尾。

## Expected Verification

- BDD: Given deploy 主段需要上传多个小控制文件，When publish-test 执行 deploy-release，Then 控制文件应通过单个归档上传并在远端校验关键文件，不应逐个 `scp` 放大启动开销。
- RED: 新合同在旧实现下失败，证明目标控制文件仍逐个 `Copy-ToServer`。
- GREEN: `scripts\tests\test_release_sql_preflight_gate.py` 通过。
- REGRESSION: 发布合同相关测试集合通过。
- PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` 通过。
- `git diff --check` 通过；只提交本任务脚本/测试和任务记录。

## 经验门禁

- deploy 控制文件合并只能减少上传往返，不得跳过 manifest/运行态验收、不得修改镜像 tar 或数据库 dump 大文件路径、不得绕过 SQL/服务启动失败。
- 远端解包后必须校验 compose/env/website runtime 关键文件存在；缺文件必须 fail fast。
- 日志、异常和任务证据不得输出 `mysql -p...`、`MYSQL_PWD=` 原值、password/token/secret 等敏感信息。
- 当前仓库存在与本任务无关的并行脏改动和 `frontend/` 删除状态，本任务不得恢复、覆盖或提交。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## Current Status

completed

## Milestone Status

1. 启动门禁与任务文档：completed。
2. 代码合同盘点：completed，确认 deploy 主段的 compose/env、website runtime、reset-db.sql、post-import.sql 仍分散上传；镜像 tar 与 db dump 保持原大文件路径。
3. RED 合同测试：completed，新增合同在旧实现下失败，命中缺少 `Copy-DeployControlFilesToServer`。
4. GREEN 实现：completed，新增 `Copy-DeployControlFilesToServer`，控制文件以 `deploy-control.tar` 单次上传并远端解包校验。
5. 回归验证与收尾：completed，目标合同、发布合同回归、PowerShell AST、差异检查、task-closeout-cleanup 和经验沉淀完成。

## Implementation Evidence

- Changed files:
  - `ops/deploy/publish-int-ruoyi.ps1`
  - `scripts/tests/test_release_sql_preflight_gate.py`
- 新增 `Copy-DeployControlFilesToServer`：
  - 本地 staging `app/docker-compose.yml` 与 `app/.env`
  - 条件包含 `website/` runtime 目录
  - 条件包含 `sql/reset-db.sql` 与 `sql/post-import.sql`
  - 打包为 `deploy-control.tar` 一次 `Copy-ToServer`
  - 远端解包后校验关键文件，再复制/移动到原远端路径
  - 远端脚本使用 `set -e` 和 `trap cleanup_deploy_control EXIT`
- 保持镜像 tar 继续走 `Copy-LargeFileToServerInChunks`，数据库 dump 继续单独上传；不改变 SQL 导入、required SQL、服务启动或运行态验收。

## Verification Evidence

- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py::test_publish_script_uploads_deploy_control_files_as_single_archive -q --basetemp doc\tasks\20260829-optimize-deploy-control-file-upload\pytest-parent\red` -> FAIL，`1 failed`；旧实现缺少 `Copy-DeployControlFilesToServer`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py::test_publish_script_uploads_deploy_control_files_as_single_archive -q --basetemp doc\tasks\20260829-optimize-deploy-control-file-upload\pytest-parent\green2` -> PASS，`1 passed in 0.07s`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-deploy-control-file-upload\pytest-parent\sql-gate2` -> PASS，`50 passed in 0.19s`。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> `PSSCRIPT_PARSE_OK`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-deploy-control-file-upload\pytest-parent\regression2` -> PASS，`61 passed in 0.20s`。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-deploy-control-file-upload/task.md doc/tasks/20260829-optimize-deploy-control-file-upload/execution-log.md doc/tasks/20260829-optimize-deploy-control-file-upload/verification-report.md` -> PASS，仅 LF/CRLF warning。
- GREEN: 本机 `tar.exe`、`ssh.exe`、`scp.exe` 可用。

## Verification Boundary

- 本次未执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。
- 仓库中已有与本任务无关的并行脏改动和 `frontend/` 删除状态，本任务未恢复、覆盖或提交。

## Closeout Evidence

- Implementation commit: `ff1368a`（`任务: 优化deploy控制文件上传`）。
- task-closeout-cleanup preview/apply 均通过，仅清理本任务 `pytest-parent` 临时产物；保留 `task.md`、`execution-log.md`、`verification-report.md`。
- project-experience-consolidation: 已合并到 `docs/release-build-preflight-lessons.md` 的 deploy 控制文件上传门禁，并更新 `docs/experience-index.md` 关键词路由。
- request-command-log: 已追加本轮优化条目并记录实现提交。
- 最终状态：completed。
