# Execution Log

BDD: 日常测试服代码发布默认轻量 -> Given 操作员未显式要求数据快照, When 执行 build-release, Then 发布包不导出数据库/MinIO 快照且日志明确 publishScope=code-only。
BDD: 全量数据包需要明确确认 -> Given 操作员选择 with-data, When 未提供显式确认, Then 脚本 fail fast 并说明风险和所需参数。
BDD: 大包复制与校验可观察 -> Given 发布包包含大量文件或大文件, When 执行 manifest/integrity/NAS copy, Then 日志持续输出阶段、文件数、字节数或耗时心跳。

GREEN: experience-preflight -> PASS，已按索引命中 release-build-preflight、test-release-preflight、PowerShell 编排门禁；本任务只修改本机维护仓脚本/测试/文档，不操作服务器、不发布、不上传 NAS。

BDD: runtime-console with-data scope is preserved -> Given 运行控制台请求 `publishScope=with-data`, When 生成 `build-release` 命令预览, Then 必须下传 `-PublishScope with-data -ConfirmText WITH-DATA` 且不得带 `-SkipDatabaseSync` 或 `-SkipMinioSync`。

RED: `mvn -Dtest=RuntimeControlContractTest#buildReleaseWithDataPreviewContainsNasAndRuntimeBaseArguments test -q` -> FAIL，运行控制台预览没有把 `with-data` 范围和确认参数传给发布脚本，实际会落回脚本默认的 `code-only`。
GREEN: `mvn -Dtest=RuntimeControlContractTest#buildReleaseCodeOnlyPreviewSkipsDatabaseAndMinioData+buildReleaseWithDataPreviewContainsNasAndRuntimeBaseArguments test -q` -> PASS。

BDD: 发布阶段失败状态可观察 -> Given manifest、完整性校验或 NAS 复制阶段抛出异常, When `Invoke-ReleaseStage` 结束, Then 日志输出 `Failed release stage`，不输出误导性的 `Completed release stage`，并保留原始异常传播。
BDD: 包大小统计复用已有事实 -> Given manifest 已生成 artifact path/bytes/hash, When 输出包大小摘要, Then 只使用已生成的 artifact facts，不对整个包目录再做一次递归枚举。
RED: `python -X utf8 -m pytest scripts\tests\test_release_package_governance.py -q --basetemp .tmp-pytest-release-duration-static-review` -> FAIL，新增阶段失败状态和大小摘要复用断言各 1 项失败，证明旧实现会误报完成且重复扫描。
GREEN: `python -X utf8 -m pytest scripts\tests\test_release_package_governance.py -q --basetemp .tmp-pytest-release-duration-static-review` -> PASS，`64 passed`。
GREEN: `python -X utf8 -m pytest scripts\tests\test_release_package_slimming.py scripts\tests\test_deploy_precheck_report_contract.py -q --basetemp .tmp-pytest-release-duration-governance-review` -> PASS，`7 passed`。
GREEN: `python -X utf8 -m pytest scripts\tests\test_release_build_preflight_cache.py -q --basetemp .tmp-pytest-release-duration-preflight-review` -> PASS，`42 passed`；使用独立 basetemp 避免并发临时目录竞争。
GREEN: powershell-ast -> PASS，发布脚本与治理模块 `AST_OK`。
GREEN: cicd-validator -> PASS，CI/CD evidence 自检通过。
