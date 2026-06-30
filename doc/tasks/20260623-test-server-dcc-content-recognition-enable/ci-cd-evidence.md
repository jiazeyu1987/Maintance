# Environment

- 目标环境：测试服 `172.30.30.58`
- 当前阶段：维护仓本地发布链路合同已修复，且已完成测试服真实部署与运行时核验

## Commands

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintanceWorktrees\int-maint-dcc-content-recognition-enable\scripts\tests\test_publish_dcc_codex_runtime_contract.py -q`
- `publish-int-ruoyi.ps1 -Mode build-release -Component backend -Environment test -ReleaseTag 20260623_dcc_content_recognition_runtime_fix_1 -SkipDatabaseSync -SkipMinioSync -DccProjectCodeCodexCliCommand /opt/intruoyi/runtime/tools/codex -DccProjectCodeCodexHome /opt/intruoyi/runtime/backend-codex-home`
- `publish-int-ruoyi.ps1 -Mode deploy-release -Component backend -Environment test -ReleaseTag 20260623_dcc_content_recognition_runtime_fix_1 -SkipDatabaseSync -SkipMinioSync -DccProjectCodeCodexCliCommand /opt/intruoyi/runtime/tools/codex -DccProjectCodeCodexHome /opt/intruoyi/runtime/backend-codex-home`
- `publish-int-ruoyi.ps1 -Mode build-release -Component intruoyi -Environment test -ReleaseTag 20260623_dcc_content_recognition_gateway_timeout_fix_1 -SkipDatabaseSync -SkipMinioSync -DccProjectCodeCodexCliCommand /opt/intruoyi/runtime/tools/codex -DccProjectCodeCodexHome /opt/intruoyi/runtime/backend-codex-home`
- `publish-int-ruoyi.ps1 -Mode deploy-release -Component intruoyi -Environment test -ReleaseTag 20260623_dcc_content_recognition_gateway_timeout_fix_1 -SkipDatabaseSync -SkipMinioSync -DccProjectCodeCodexCliCommand /opt/intruoyi/runtime/tools/codex -DccProjectCodeCodexHome /opt/intruoyi/runtime/backend-codex-home`

## Secrets

- 不新增任何仓库内密钥
- DCC Codex 运行时只引用既有远端 `auth.json/config.toml` 来源，owner 待测试服执行阶段记录

## Pipeline

- 修改文件限定为维护仓 `ops/deploy/publish-int-ruoyi.ps1`、`ops/deploy/int-ruoyi-test/docker-compose.yml` 与本地合同测试

## Verification

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintanceWorktrees\int-maint-dcc-content-recognition-enable\scripts\tests\test_publish_dcc_codex_runtime_contract.py -q` -> PASS, `2 passed`
- `python -X utf8 C:\Users\BJB110\.codex\skills\ci-cd-environment-delivery\scripts\validate_cicd_environment.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintanceWorktrees\int-maint-dcc-content-recognition-enable\doc\tasks\20260623-test-server-dcc-content-recognition-enable\ci-cd-evidence.md` -> PASS
- 测试服宿主机 `codex exec` 冒烟 -> PASS, `OK`
- 测试服 backend 容器 `/opt/intruoyi/runtime/tools/codex exec` 冒烟 -> PASS, `OK`
- 测试服 `8081/admin-api/dcc/controlled-files/2054545668044050094/recognize-project-code` -> PASS，约 `110s` 返回 backend 真实业务结果 `DCC project-code recognition returned no DCC basic-data match`，不再是 `504 Gateway Time-out`

## Rollback

- 若本地合同测试无法通过，回滚本次维护仓脚本与 compose 改动，不进入测试服重建

## Blockers

- 当前缺少一条“对象存在且内容足以命中 DCC 基础数据”的真实正样本；现有候选样本要么对象缺失，要么返回 `DCC project-code recognition returned no DCC basic-data match`
