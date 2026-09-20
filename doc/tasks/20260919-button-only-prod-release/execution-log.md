# Execution Log

## 2026-09-20

- BDD: 测试服发布锁恢复按钮 -> Given 测试服存在旧 `RUNNING` 发布锁且无迁移写入证据，When 运维人员在 worktree 运行控制台真实页面点击“恢复测试服发布锁”，Then 后端必须只对匹配 `test-<releaseTag>` 与同一 `releaseTag` 的锁执行恢复，并在确认无远端发布执行器和无迁移证据后才将锁标记为 `FAILED`。
- BDD: 恢复脚本 Windows SSH 传输噪音 -> Given 远端 SQL 已返回 `LOCK_RECOVERED`，When Windows OpenSSH 在会话关闭时额外输出 `close - IO is still pending on closed socket`，Then 操作可判定成功；若存在 `RECOVER_BLOCKED_*`、SQL ERROR、权限或连接错误，则必须失败。
- GREEN: experience-preflight -> PASS；本轮只在 `D:\IntRuoyiWorktree\r260917-button-publish7\m` worktree 操作，恢复锁、后续构建、测试服和正式服写入均必须通过真实页面按钮触发。
- GREEN: recover-test-release-lock-ui-preview -> PASS；真实页面按钮预览脚本为 `ops\deploy\recover-release-operation-lock.ps1`，参数包含 `-ExpectedOperationId test-release-20260919-button-prod-r4 -ExpectedReleaseTag release-20260919-button-prod-r4 -ConfirmText RECOVER-TEST-LOCK`。
- BLOCKER: recover-test-release-lock-first-attempt -> FAIL；按钮操作 `op-2026-09-20T053707366529700Z-f416d7bb-6be3-4c7e-ac31-48ae6065018d` 因 PowerShell stdin 管道调用 ssh 出现 `close - IO is still pending on closed socket` 失败，远端锁仍为 `RUNNING`。
- RED: recover-script-stdin-ssh-transport -> FAIL；恢复脚本通过本机 stdin 管道喂给 ssh 的方式在 Windows OpenSSH 下不稳定。
- GREEN: recover-script-base64-transport -> PASS；改为 base64 远端载荷命令，不再依赖本机 stdin 管道；PowerShell AST PASS。
- BLOCKER: recover-test-release-lock-second-attempt -> FAIL；按钮操作 `op-2026-09-20T053857480531200Z-bf8661fc-0ad6-4e73-bcff-e472dd8d1155` 进入远端 SQL 后失败于 MySQL `ERROR 1267 Illegal mix of collations`。
- RED: recover-script-collation -> FAIL；恢复脚本字面量默认排序规则与锁表列排序规则不一致。
- GREEN: recover-script-collation -> PASS；恢复脚本 SQL 显式设置 `SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;`。
- PARTIAL: recover-test-release-lock-third-attempt -> REMOTE_RECOVERED；按钮操作 `op-2026-09-20T053959200981200Z-0f23216b-cee5-4405-8bfe-59b753d5433a` 在远端成功将旧 r4 锁从 `RUNNING` 改为 `FAILED`，只读核对 `finished_at=2026-09-20 13:40:00`、`error_message=RECOVERED_BY_EXPLICIT_BUTTON_AFTER_EXECUTOR_AND_MIGRATION_CHECK`、旧 r4/r14 迁移证据为 0；但本地 operation 因 Windows OpenSSH socket close 噪音仍标记 FAILED。
- GREEN: recover-script-ssh-close-noise-regression -> PASS；恢复脚本仅在 `LOCK_RECOVERED` 明确出现且无真实阻塞/SQL/权限/连接错误时接受 `close - IO is still pending on closed socket` 噪音；`python -m pytest .\scripts\tests\test_publish_release_lock_cleanup.py .\scripts\tests\test_release_sql_preflight_gate.py -q`，65 passed。
