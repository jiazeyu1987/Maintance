# 20260829 优化测试服发布 ops runtime 上传执行日志

- BDD: ops runtime 单包上传 -> Given publish-test 需要同步 runtime-control ops 脚本目录, When 发布脚本上传 ops runtime package, Then 应先在本地 staging 排除 secrets 后打成单个 tar 归档、一次 scp 上传、远端解包并校验关键文件存在，减少多次 scp 往返。
- BDD: 发布语义不变 -> Given ops runtime 上传方式改变, When publish-test 继续执行, Then releaseTag、manifest、required SQL、operation lock、运行态验收和失败判定语义不得降低或跳过。
- GREEN: experience-preflight -> PASS，本任务只修改本地维护仓脚本/测试/文档，不执行真实服务器发布、数据库写入、正式服、备份服、备份或恢复。
- RED-SETUP: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-test-release-ops-runtime-upload\pytest-parent\red` -> INVALID，`pytest-parent` 父目录缺失导致 13 个 setup error；目标新增测试也按预期失败。
- RED: 补齐本任务 `pytest-parent` 后重跑同命令 -> FAIL，`1 failed, 43 passed`；失败点为 `test_publish_script_uploads_ops_runtime_package_as_single_archive`，旧实现没有 `ops-runtime.tar` 且仍多次 `Copy-ToServer`。
- 修复动作：`Copy-ReleaseOpsRuntimePackage` 保留本地 staging 与 secret 排除检查，生成 `ops-runtime-<releaseTag>.tar`，单次上传为远端 `ops-runtime.tar`，远端解包后校验 `linux/backup-ops-linux.sh` 与 `script/deploy/manage-int-ruoyi-remote-root-disk.ps1`。
- 设计边界：远端不整目录删除 `$remoteOpsRuntimeDir`，仅清理 `linux/scripts/actions` 和受控 deploy 脚本，避免删除远端 `config` 下可能存在的 secrets。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-test-release-ops-runtime-upload\pytest-parent\green` -> PASS，`44 passed in 0.17s`。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> `PSSCRIPT_PARSE_OK`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-test-release-ops-runtime-upload\pytest-parent\regression` -> PASS，`55 passed in 0.17s`。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-test-release-ops-runtime-upload/task.md doc/tasks/20260829-optimize-test-release-ops-runtime-upload/execution-log.md doc/tasks/20260829-optimize-test-release-ops-runtime-upload/verification-report.md` -> PASS，仅 LF/CRLF warning。
- GREEN: tool-preflight -> PASS，本机 `tar.exe`、`ssh.exe`、`scp.exe` 存在。
- COMMIT: implementation -> `f33a8ec`（`任务: 优化发布ops运行包上传`），提交范围仅 `ops/deploy/publish-int-ruoyi.ps1` 与 `scripts/tests/test_release_sql_preflight_gate.py`。
- GREEN: task-closeout-cleanup preview -> PASS，状态 `ready`，仅计划清理本任务 `pytest-parent` 临时产物。
- GREEN: task-closeout-cleanup apply -> PASS，状态 `applied`，保留 `task.md`、`execution-log.md`、`verification-report.md`。
- GREEN: project-experience-consolidation -> PASS，经验合并到 `docs/release-build-preflight-lessons.md`，索引更新到 `docs/experience-index.md`。
- FINAL: task status -> completed；本任务未执行真实服务器发布、数据库写入、正式服、备份服、备份或恢复。
