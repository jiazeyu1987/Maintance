# Verification Report

## Result

PASS

## Scope

- 默认 build-release 改为 `PublishScope=code-only`，自动启用数据库和 MinIO 跳过逻辑。
- with-data 需要 `-PublishScope with-data -ConfirmText WITH-DATA`，且不能同时传 `-SkipDatabaseSync` 或 `-SkipMinioSync`。
- manifest 用 `packageRole=release-code|release-data-snapshot` 标识代码包/数据快照包语义。
- manifest 生成缓存 artifact hash；本地 build integrity 复用缓存，NAS 目标包仍重新校验。
- NAS 上传改为 `Copy-ReleaseDirectoryTree` / robocopy 路径，并记录复制摘要。
- manifest、integrity、NAS upload 增加阶段开始/结束与耗时日志，包大小也会输出摘要。

## Verification

- `python -X utf8 -m pytest scripts\tests\test_release_package_governance.py scripts\tests\test_deploy_precheck_report_contract.py -q --basetemp .tmp-pytest-release-duration` -> `63 passed in 36.43s`
- PowerShell AST parse for `ops/deploy/publish-int-ruoyi.ps1` and `ops/release/lib/ReleasePackageGovernance.psm1` -> `AST_OK`
- `python -X utf8 C:\Users\BJB110\.codex\skills\ci-cd-environment-delivery\scripts\validate_cicd_environment.py --self-test` -> PASS
- `git diff --check` -> PASS

## Boundaries

- 未运行真实 build-release、publish-test、mark-tested、promote-prod 或 promote-backup。
- 未访问服务器、NAS、数据库、MinIO 或远程环境。
- 当前主线程正在运行的 r14 发布进程未停止、未修改、未接管。
