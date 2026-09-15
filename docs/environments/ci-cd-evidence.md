# CI/CD Evidence

## 2026-09-16 one-button app-release Maven/Surefire guard

- Environments and deployment targets: 本次只修改维护仓发布脚本和合同测试；R72 在本机构建前 Maven 门禁中断，未生成发布包、未上传 NAS、未写测试服；正式服、审查服、`mark-tested`、`promote-prod`、`promote-backup`、MinIO 数据同步和全量数据库同步均未执行。
- Build/package commands: R72 判废；下一轮必须使用新 releaseTag `release-20260916-one-button-app-r73` 从当前维护/app clean HEAD 重新 `build-release`，继续固定 `PublishScope=app-release`、`SkipDatabaseSync`、`SkipMinioSync`。
- Pipeline files changed: `ops/deploy/publish-int-ruoyi.ps1`、`scripts/tests/test_release_workflow_preflight.py`、任务执行记录和本 CI/CD evidence。
- Required secrets and owners: 未新增 secret；NAS/SSH/MySQL/EDHR 配置仍由既有运行控制台/目标环境提供，修复不输出或提交 secret。
- Artifact and release output: R72 无 `manifest.json`、镜像 tar、NAS READY 或测试服 operation；卡点为 Maven/Surefire forked JVM 启动期。
- RED verification evidence: `python -X utf8 -m pytest -q scripts\tests\test_release_workflow_preflight.py::test_backend_contract_maven_uses_windows_surefire_classpath_guard --basetemp .tmp-r72-surefire-guard-red` -> FAIL。
- GREEN verification evidence: 同目标测试 -> PASS；相邻回归 `test_release_workflow_preflight.py test_release_target_data_preflight.py test_release_sql_preflight_gate.py test_release_package_governance.py` -> 166 passed；`publish-int-ruoyi.ps1` PowerShell AST -> PASS；直接复跑发布脚本同款 Maven 合同命令 10 tests PASS，总耗时 6.468s。
- Manual approvals and blockers: 用户已授权测试服/NAS app-release 续跑；R72 已中断并判废，必须提交脚本门禁后用 R73 重建，不得继续 R72。
- Rollback procedure and validation: 回滚本次维护提交会恢复 Windows 跨盘 Surefire 启动卡死风险；若回滚，必须禁止一键发布构建并重跑上述 RED/GREEN 用例。

## 2026-09-14 one-button app-release required SQL empty-candidate gate

- Environments and deployment targets: 测试服 `172.30.30.58` 仅在用户授权范围内执行 `app-release deploy-release`；正式服、审查服、`mark-tested`、`promote-prod`、`promote-backup`、MinIO 数据同步和全量数据库同步均未执行。
- Build/package commands: r38 本地包和 manifest validation 通过，但测试服 required SQL 在版本切换前失败；r38 已判废，下一轮必须使用新 releaseTag `release-20260914-one-button-app-r39`，继续固定 `PublishScope=app-release`、`SkipDatabaseSync`、`SkipMinioSync`。
- Pipeline files changed: 应用仓 `20260811_mes_process_pool_cleaning_process_parameter_data.sql`、对应 `target-preflight`、新增 SQL 静态测试；维护仓 `docs/release-build-preflight-lessons.md`、`docs/experience-index.md`、任务执行记录。
- Required secrets and owners: 未新增 secret；测试服 MySQL 密码仅在远端容器环境解析，任务证据只记录脱敏命令和聚合计数。
- Artifact and release output: r38 `packageDigest=9387c858b542f3899a7162003e0b396fc2816f762c832e93def5271d7060a106`、`manifestDigest=f93bc66c3225c90563e8634ccba2e87cb775b91fb9aa95378ae86a18fdf04475`；部署失败发生在 `.env` 切换前，operation lock 已释放为 FAILED。
- RED verification evidence: `python -X utf8 -m pytest -q D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiBackend\script\tests\test_mes_process_pool_cleaning_process_parameter_data_sql.py --basetemp D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiBackend\.tmp-r38-cleaning-process-red` -> FAIL，2 failed。
- GREEN verification evidence: 修复后同目标用例 2 PASS；相邻 `test_release_target_preflight_files.py` / `test_release_preflight_plan.py` 回归 26 PASS；测试服只读 preflight 返回 `TARGET_PREFLIGHT_PASS:20260811_mes_process_pool_cleaning_process_parameter_data`。
- Manual approvals and blockers: 用户已授权测试服/NAS app-release 续跑；r38 已失败，必须提交应用修复和维护证据后用 r39 重建，不得继续 r38。
- Rollback procedure and validation: 若回滚应用提交 `b286fd47d`，空规则目标库会再次在 publish-test required SQL 阶段失败；回滚后必须禁止 without-data 一键发布并重跑新增 SQL 静态测试与目标只读 preflight。

## 2026-09-14 one-button app-release target-bound package gate

- Environments and deployment targets: 本次只在维护仓隔离 worktree 修复发布脚本和合同测试；r37 本地包只做本地 manifest validation，未执行测试服 `deploy-release`，正式服、审查服、`mark-tested`、`promote-prod`、`promote-backup` 均未执行。
- Build/package commands: r37 已判废；下一轮必须使用新 releaseTag `release-20260914-one-button-app-r38` 从当前维护/app clean HEAD 重新 `build-release`，继续固定 `PublishScope=app-release`、`SkipDatabaseSync`、`SkipMinioSync`。
- Pipeline files changed: `ops/deploy/publish-int-ruoyi.ps1`、`scripts/tests/test_release_package_governance.py`、`docs/release-build-preflight-lessons.md`、`docs/experience-index.md`、任务执行记录。
- Required secrets and owners: 未新增 secret；NAS/SSH/MySQL/EDHR 配置仍由既有运行控制台/目标环境提供，包内不再携带 target-bound config、secret 示例或目标服务器证据。
- Artifact and release output: r37 本地包被 `validate-release-manifest.ps1` 阻断，原因是 `evidence/target-data-preflight.json`、`ops-runtime/config` 和远程磁盘脚本携带目标 IP/secret-like 内容；测试服版本未切换，失败 tag 不复用。
- RED verification evidence: `python -X utf8 -m pytest -q scripts/tests/test_release_package_governance.py -k "target_data_preflight_evidence or ops_runtime_package_excludes" --basetemp .tmp-r37-forbidden-package-red` -> FAIL，2 failed。
- GREEN verification evidence: 修复后同目标用例 PASS；相邻回归 `test_release_package_governance.py`、`test_app_release_package_governance.py`、`test_release_sql_preflight_gate.py`、`test_release_workflow_preflight.py` -> 151 passed；`publish-int-ruoyi.ps1` PowerShell AST PASS。
- Manual approvals and blockers: 用户已授权测试服/NAS app-release 续跑；r37 已失败，必须提交脚本门禁后用 r38 重建，不得继续 r37。
- Rollback procedure and validation: 若回滚本次脚本门禁，app-release 包会重新携带 target-bound evidence/config 并在 manifest validation 阶段失败；回滚后必须禁止 without-data 一键发布并重跑上述 RED/GREEN 用例。

## 2026-09-14 one-button app-release deploy no-data gate

- Environments and deployment targets: 测试服 `172.30.30.58` 仅在用户授权范围内执行 `app-release deploy-release`；正式服、审查服、`mark-tested`、`promote-prod`、`promote-backup` 均未执行。
- Build/package commands: r26 已判废；下一轮必须使用新 releaseTag `release-20260914-one-button-app-r27` 从当前维护/app 提交重新 `build-release`，继续固定 `PublishScope=app-release`、`SkipDatabaseSync`、`SkipMinioSync`。
- Pipeline files changed: `ops/deploy/publish-int-ruoyi.ps1`、`scripts/tests/test_release_workflow_preflight.py`、`docs/release-build-preflight-lessons.md`、`docs/experience-index.md`、任务执行记录。
- Required secrets and owners: 未新增 secret；NAS/SSH/MySQL/EDHR 配置仍由既有运行控制台/目标环境提供，证据只记录配置存在性和脱敏路径，不提交 secret 值。
- Artifact and release output: r26 包完整性和 NAS READY 通过，但 manifest 绑定旧应用提交 `6079138ea`，缺少后续 RT000006 不适用修复；测试服版本未切换，失败 tag 不复用。
- RED verification evidence: `python -X utf8 -m pytest -q scripts/tests/test_release_workflow_preflight.py -k "edhr_storage_probe" --basetemp .tmp-r27-edhr-probe-red` -> FAIL，旧脚本在 app-release deploy 路径调用写对象 verifier。
- GREEN verification evidence: `python -X utf8 -m pytest -q scripts/tests/test_release_workflow_preflight.py -k "edhr_storage_probe or nas_config or tests_and_source_freeze" --basetemp .tmp-r27-edhr-probe-green` -> PASS，3 passed；`publish-int-ruoyi.ps1` PowerShell AST PASS。
- Manual approvals and blockers: 用户已授权测试服/NAS app-release 续跑；r26 已失败，必须提交脚本门禁后用 r27 重建，不得继续 r26。
- Rollback procedure and validation: 若回滚本次脚本门禁，`app-release deploy-release` 会恢复 Object Lock 探针写入风险；回滚后必须禁止 without-data 一键发布并重跑 `test_release_workflow_preflight.py -k edhr_storage_probe`。

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
