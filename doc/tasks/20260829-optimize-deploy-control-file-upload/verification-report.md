# 20260829 优化 deploy 控制文件上传验证报告

## Verification Summary

- 状态：completed。
- 本轮不会执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。

## Results

- RED: 新增 deploy-control tar 合同先失败，旧实现缺少 `Copy-DeployControlFilesToServer`。
- GREEN: 新合同通过，`1 passed in 0.07s`。
- GREEN: `scripts\tests\test_release_sql_preflight_gate.py` 通过，`50 passed in 0.19s`。
- GREEN: PowerShell AST parse 通过，`PSSCRIPT_PARSE_OK`。
- REGRESSION: 发布合同回归集合通过，`61 passed in 0.20s`。
- GREEN: `git diff --check` 通过，仅 LF/CRLF warning。
- GREEN: `tar.exe`、`ssh.exe`、`scp.exe` 可用。

## Boundary

- 未执行真实发布或远端写入。
- 未触碰、恢复或提交本任务外的既有脏改动。

## Closeout

- Implementation commit: `ff1368a`（`任务: 优化deploy控制文件上传`）。
- task-closeout-cleanup preview/apply: PASS。
- project-experience-consolidation: PASS，更新 `docs/release-build-preflight-lessons.md` 与 `docs/experience-index.md`。
- request-command-log: 已追加本轮条目。
