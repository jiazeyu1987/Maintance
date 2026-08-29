# 20260829 优化测试服发布 ops runtime 上传

## Task Goal

继续优化测试服发布链路耗时，将 runtime-control ops 脚本上传从多次目录 `scp` 收敛为单个 tar 归档上传和远端解包；不改变发布包、releaseTag、迁移、运行态验收或失败判定语义。

## Milestones

1. 启动门禁与任务文档：确认上一优化任务已完成，记录本轮范围、BDD 和预期验证。
2. RED 合同测试：新增测试证明当前 ops runtime 仍使用多次 `Copy-ToServer` 上传。
3. GREEN 实现：将 ops runtime 本地 staging 后归档为 tar，单次上传到远端并解包校验。
4. 回归验证：运行目标合同测试、PowerShell AST、差异检查，确认不触碰服务器。
5. 收尾记录：清理本任务临时产物，记录边界和提交。

## Expected Verification

- RED: 新增合同测试在旧实现下失败，原因是 `Copy-ReleaseOpsRuntimePackage` 仍对 `linux/scripts/actions/config/manage-int-ruoyi-remote-root-disk.ps1` 多次 `Copy-ToServer`。
- GREEN: `scripts\tests\test_release_sql_preflight_gate.py` 通过。
- REGRESSION: 发布相关合同测试集合通过；无法运行的相邻测试必须记录前置阻塞。
- PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` 通过。
- `git diff --check` 通过；只提交本任务脚本/测试和任务记录。

## 经验门禁

- 发布优化不得降低单一 releaseTag 的 `build-release -> publish-test` 验收标准，不得跳过 SQL、manifest、health、HTTP 或版本说明。
- 批量上传必须有本地归档非空、远端解包目标文件存在、敏感文件不进入包的断言。
- PowerShell 中文与日志记录显式 UTF-8；不提交 raw secret-bearing 日志。
- 当前仓库存在与本任务无关的并行脏改动和 `frontend/` 删除状态，本任务不得恢复、覆盖或提交。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## Current Status

completed

## Milestone Status

1. 启动门禁与任务文档：completed。
2. RED 合同测试：completed，新增测试命中 `Copy-ReleaseOpsRuntimePackage` 仍未单包上传。
3. GREEN 实现：completed，ops runtime staging 后打包为 `ops-runtime.tar`，一次上传、远端解包并校验关键文件。
4. 回归验证：completed，目标合同测试、发布合同回归、PowerShell AST 和差异检查通过。
5. 收尾记录：completed，task-closeout-cleanup 通过，长期经验与索引已更新，任务记录完成。

## Implementation Evidence

- Changed files:
  - `ops/deploy/publish-int-ruoyi.ps1`
  - `scripts/tests/test_release_sql_preflight_gate.py`
- `Copy-ReleaseOpsRuntimePackage` 保持本地 staging 和 `backup-ops.secrets.json` 排除检查，随后生成 `ops-runtime-<releaseTag>.tar`。
- 远端只清理 `linux`、`scripts`、`actions` 和受控 `script/deploy/manage-int-ruoyi-remote-root-disk.ps1`，保留远端 `config` 目录中可能存在的 secrets 文件。
- 上传从 5 次 `Copy-ToServer` 收敛为 1 次 `Copy-ToServer -LocalPath $opsRuntimeArchivePath -RemotePath $remoteOpsRuntimeArchive`。

## Verification Evidence

- RED-SETUP: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-test-release-ops-runtime-upload\pytest-parent\red` -> INVALID，`pytest-parent` 父目录缺失导致 13 个 fixture setup error；目标新增测试同时按预期失败。
- RED: 补齐本任务临时父目录后重跑同命令 -> FAIL，`1 failed, 43 passed`，失败测试为 `test_publish_script_uploads_ops_runtime_package_as_single_archive`，原因是旧实现没有 `ops-runtime.tar`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-test-release-ops-runtime-upload\pytest-parent\green` -> PASS，`44 passed in 0.17s`。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> `PSSCRIPT_PARSE_OK`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-test-release-ops-runtime-upload\pytest-parent\regression` -> PASS，`55 passed in 0.17s`。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-test-release-ops-runtime-upload/task.md doc/tasks/20260829-optimize-test-release-ops-runtime-upload/execution-log.md doc/tasks/20260829-optimize-test-release-ops-runtime-upload/verification-report.md` -> PASS，仅 LF/CRLF warning。
- GREEN: 本机 `tar.exe`、`ssh.exe`、`scp.exe` 可用。

## Verification Boundary

- 本次未执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。
- 仓库中已有与本任务无关的并行脏改动和 `frontend/` 删除状态，本任务未恢复、覆盖或提交。

## Closeout Evidence

- Implementation commit: `f33a8ec`（`任务: 优化发布ops运行包上传`）。
- task-closeout-cleanup preview/apply 均通过，仅清理本任务 `pytest-parent` 临时产物；保留 `task.md`、`execution-log.md`、`verification-report.md`。
- project-experience-consolidation: 已合并到 `docs/release-build-preflight-lessons.md` 的 2026-08-29 发布批量化门禁，并更新 `docs/experience-index.md` 关键词路由。
- 最终状态：completed。
