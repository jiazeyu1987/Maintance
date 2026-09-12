# CI/CD Evidence

## one-button-app-release 恢复验证

- Environment: 本任务维护/app worktree；Windows PowerShell 5.1；测试服 172.30.30.58 仅执行已授权只读事务状态探针。本轮未重新打包或上传/部署。
- Commands: `python -X utf8 -m pytest ... --basetemp <task-cache>/resume-final-regression`，具体测试清单和RED/GREEN见任务 execution-log；生产门禁新增 `release_target_data_preflight.py`，在schema-only演练和正式构建前执行。
- Secrets: SSH使用已有受控凭据；MySQL密码仅在远端由容器环境解析，stdin传SQL、不返回密码；由现有运维配置所有者维护，不新增秘密值。
- Pipeline: `ops/deploy/publish-int-ruoyi.ps1` 的实际长路径清理、构建必跑回归集合和目标数据预检接线；`ops/release/release_target_data_preflight.py`、只读合同、缺结果阻断及元数据一致性验证。
- Verification: 真实PS5.1清理8项PASS；目标检查缺失/失败/篡改/非法SQL均阻断；测试服transaction_read_only=1。完整回归结果见任务记录。
- Artifact: 只产生任务本地诊断和回归证据；r15没有manifest/NAS READY资格，不发布旧失败包。
- Rollback: 若撤销此局部修复，发布保持禁用；不能恢复“排除迁移却不检查”的旧放行路径。无服务器写入，不需要服务器回滚。
- Blockers: 58个真实迁移检查缺失、已验证源选择性融合、部署时预检、自包含包、UI/全任务独立验收和融合收尾仍未完成；本文件不代表P3放行。

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

## 2026-09-13 one-button app-release immutable package gate

- Environments and deployment targets: 本次只修改维护仓发布脚本与合同测试；r23 本地包只读复核失败后判废，未继续测试服部署，未触碰正式服。
- Build/package commands: 标准 `build-release` 仍固定 `PublishScope=app-release` 并排除数据库全量 dump、MinIO 同步、DCC inventory、runtime data 和秘密配置；本次新增要求 `ops-runtime` 在构建期进入 `manifest.json` 和 `packageDigest`。
- Pipeline files changed: `ops/deploy/publish-int-ruoyi.ps1`、`scripts/tests/test_release_package_governance.py`。
- Required secrets and owners: 未新增 secret；`backup-ops.secrets.json` 明确禁止进入包，NAS/SSH/MySQL 凭据仍由既有运行控制台配置提供。
- Artifact and release output: r23 因部署阶段污染包目录而判废；下一轮必须使用新 releaseTag 重新构建，不复用 r23。
- RED verification evidence: `python -X utf8 -m pytest -q scripts/tests/test_release_package_governance.py -k "ops_runtime" --basetemp .tmp-r23-ops-runtime-red` -> 2 failed，旧脚本没有构建期 ops-runtime 包含和部署期只读合同。
- GREEN verification evidence: 定向 4 PASS；发布包治理、app-release governance、build preflight cache、schema rehearsal 宽回归 139 PASS；PowerShell AST PASS。
- Manual approvals and blockers: 用户已授权继续测试服/NAS app-release 链路；本次修复后仍需先提交，再用新 tag 重新构建与发布测试服。
- Rollback procedure and validation: 回滚本次维护提交会恢复部署阶段修改包目录的旧风险；若回滚，必须禁止继续 one-button app-release 发布并重跑上述回归。
