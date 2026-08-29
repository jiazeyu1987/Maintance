# 20260829 优化 required SQL 规划阶段 SSH 往返验证报告

## Verification Summary

- 状态：completed。
- 本轮不会执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。
- 已通过经验门禁预检；本轮优化不得破坏 required SQL tar 上传、远端数量校验、批量 SKIP 入账、APPLY 成功路径单 SSH 和 secret redaction 合同。

## Results

- RED: 新增 route snapshot hook 单 SSH 合同先失败，旧实现每个模式含 2 次 `Invoke-SshCommand`。
- GREEN: 新合同通过，`1 passed in 0.02s`。
- GREEN: `scripts\tests\test_release_sql_preflight_gate.py` 通过，`49 passed in 0.25s`。
- GREEN: PowerShell AST parse 通过，`PSSCRIPT_PARSE_OK`。
- REGRESSION: 发布合同回归集合通过，`60 passed in 0.17s`。
- GREEN: `git diff --check` 通过，仅 LF/CRLF warning。

## Boundary

- 未执行真实发布或远端写入。
- 未触碰、恢复或提交本任务外的既有脏改动。

## Closeout

- Implementation commit: `f035655`（`任务: 优化route snapshot发布hook校验`）。
- task-closeout-cleanup preview/apply: PASS。
- project-experience-consolidation: PASS，更新 `docs/release-build-preflight-lessons.md` 与 `docs/experience-index.md`。
- request-command-log: 已追加本轮条目。
