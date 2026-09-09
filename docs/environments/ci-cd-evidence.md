# CI/CD Evidence

## 2026-09-09 发布打包耗时优化

- Environments and deployment targets: 本次只修改本机维护仓发布脚本、manifest schema、validator 和合同测试；未连接测试服、正式服、备份服或 NAS。
- Build/package commands: 未执行真实 `build-release`；实现目标是让日常 build-release 默认 `code-only`，with-data 需要显式 `-PublishScope with-data -ConfirmText WITH-DATA`。
- Pipeline files changed: `ops/deploy/publish-int-ruoyi.ps1`、`ops/release/lib/ReleasePackageGovernance.psm1`、`ops/release/lib/ReleaseManifestValidator.psm1`、`ops/release/manifest-v1.schema.json`、`scripts/tests/test_release_package_governance.py`。
- Required secrets and owners: 未新增 secret；NAS/MySQL/MinIO/SSH 既有 secret 仍由运行控制台配置和目标环境提供。
- Artifact and release output: manifest 新增 `packageRole=release-code|release-data-snapshot` 与 `relatedReleaseTag`；本地完整性校验复用刚生成的 artifact hash，NAS 目标包仍重新校验。
- GREEN verification evidence: `python -X utf8 -m pytest scripts\tests\test_release_package_governance.py scripts\tests\test_deploy_precheck_report_contract.py -q --basetemp .tmp-pytest-release-duration` -> `63 passed in 36.43s`。
- GREEN validation evidence: PowerShell AST parse -> `AST_OK`；`git diff --check` -> PASS；CI/CD skill validator self-test -> PASS。
- Manual approvals and blockers: 用户明确要求按 6 步开始修改；无阻塞。
- Rollback procedure and validation: 回滚实现提交 `6639128` 即可恢复旧发布行为；回滚后需重跑发布包治理 pytest 与 PowerShell AST。
