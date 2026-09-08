# Execution Log

- Task ID: `release-preflight-cache-optimization-20260908`
- Created: `2026-09-08T11:13:31`

## BDD Scenarios

BDD: 构建前阻断不兼容迁移 -> Given staged required SQL 与测试服迁移台账不兼容 / When build-release / Then fresh target-state 与 planner 在 Maven/frontend/Docker 前返回 blocked 并停止。

BDD: 预检证据绑定本次输入 -> Given 预检通过 / When 源码、SQL、target-state、environment 或 scope 漂移 / Then 绑定摘要变化或验证失败，旧 evidence 不得放行。

BDD: Docker 原生缓存正确命中与失效 -> Given Dockerfile/context/base digest/build args / When 输入相同或任一变化 / Then Docker 原生内容缓存可命中，输入指纹确定性相同或变化。

BDD: 缓存不降低 P0 门禁 -> Given Docker cache 命中 / When 生成包 / Then image inspect/save、manifest、逐文件 SHA-256、packageDigest 和 NAS copy 后校验继续无条件执行。

## Planner Review

- Result: approved。
- Validation: `validate_artifacts.py` -> status ok。
- Scope: P1 early target-bound preflight；P2 verifiable native Docker cache；不修改 frontend，不执行真实远端/Docker build/发布。

## Phase Entries

### Phase P1 - Early Target-Bound Build Preflight

- Executor scope: 仅实现 P1（P1-AC1..P1-AC5），未进入 P2，未执行真实 SSH、NAS、Docker build、数据库写入或服务器发布。
- Changed paths:
  - `ops/deploy/publish-int-ruoyi.ps1`
  - `ops/release/release_build_preflight.py`
  - `scripts/tests/test_release_build_preflight_cache.py`
  - `doc/tasks/release-preflight-cache-optimization-20260908/execution-log.md`
- BDD: 构建前阻断不兼容迁移 -> Given required SQL 已暂存且测试服只读 migration ledger 与迁移计划不兼容 / When 执行 build-release / Then 本轮重新采集 target-state、调用既有 planner、写出 blocked evidence 并在 Maven/frontend/Docker build 前失败。
- BDD: 本轮证据绑定精确输入 -> Given planner 明确返回 passed / When source commit、staged SQL、prospective manifest、target-state、environment 或 scope 任一变化 / Then 对应摘要变化或 evidence 复验失败，旧 evidence 不参与放行。
- BDD: 采集或证据异常关闭构建资格 -> Given SSH/query 失败、空输出、非法 JSON、缺 migration ledger、非法 ledger item、blocked/未知 action、缺 binding 或摘要被篡改 / When 执行或复验 build preflight / Then 命令非零退出且昂贵构建不开始。
- RED: `python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\red"` -> FAIL，`14 failed, 4 passed`；预期原因为独立 runner 与发布脚本调用尚不存在。
- RED: `python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\red-ledger"` -> FAIL，`1 failed, 18 passed`；预期原因为非法 migration ledger item 尚未被拒绝。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_sql_preflight_gate.py -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\green-final"` -> PASS，`73 passed in 4.54s`。
- GREEN: 最终交付复跑同一聚焦范围（`--basetemp ...\green-delivery`）-> PASS，`73 passed in 4.66s`，包含固定 `preflightFingerprint` 向量。
- GREEN: PowerShell 5.1 AST parse `ops/deploy/publish-int-ruoyi.ps1` -> PASS，无解析错误。
- REGRESSION: `python -X utf8 -m pytest scripts/tests tests -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\full"` -> PASS，`165 passed in 42.70s`。
- REGRESSION: JDK 17 `mvn.cmd -f backend\pom.xml test` -> PASS，`26 tests`，`BUILD SUCCESS`。
- REGRESSION: `node --test scripts/tests/publish_frontend_deploy_sql_gate_contract.test.mjs scripts/tests/publish_image_tar_transfer_contract.test.mjs scripts/tests/publish_release_info_contract.test.mjs` -> PASS，`6 tests`。
- P1-AC1: PASS（executor evidence）— 发布脚本在 `Copy-RequiredDatabaseSqlScripts` 后构造 prospective manifest，固定读取 `TestServerHost` 的只读台账并调用复用 `release_preflight_plan.py` 决策的 runner，调用点早于 Maven、frontend build 和 Docker build。
- P1-AC2: PASS（executor evidence）— 每轮删除本 release tag 的旧外部 evidence 目录并生成新 UUID/UTC 采集信息；采集非零、空输出、非法 JSON、缺台账及 runner/planner 异常均非零失败。
- P1-AC3: PASS（executor evidence）— `release-build-preflight/v1` evidence 绑定 source commits/fingerprint、staged SQL、prospective manifest、normalized target-state、test/scope、collection ID/time、planner status/items 摘要；仅输出白名单字段，不复制 manifest 中密码、token、raw env 或连接信息。
- P1-AC4: PASS（executor evidence）— runner 写出 blocked 证据后返回非零；verify 仅接受 `APPLY`、`SKIP_ALREADY_APPLIED`、`SKIP_ENV_NOT_ALLOWED`、`SKIP_SCOPE_EXCLUDED`，并复算完整 evidence 拒绝缺字段、未知/blocked action 与摘要漂移。
- P1-AC5: PASS（executor evidence）— 相同规范内容产生相同 binding digests；source、SQL、target-state、scope 漂移均改变 `preflightFingerprint`，非 test environment 直接失败。
- Risk: 本阶段通过本地 fixture 和静态调用顺序合同验证，未连接真实测试服；真实服务器 SSH、容器名、`infra_release_migration` 表及只读查询可用性须由后续授权的真实 build-release 验证。外部 evidence 保留在 local cache 的 `build-preflight-<packageDirectoryName>` 目录，不进入不可变安装包。
- Executor result: P1 implementation ready for independent tester；未提交，未修改 `task-state.json`、`prd.md`、`test-plan.md`、`test-report.md` 或 `task.md`。

#### P1 Main Review Revision

- Review finding 1: planner 消费的 `database.schemaMigrations` 与 staged file 校验消费的 `requiredSql` 原先没有建立逐项等价门禁，两个数组可漂移。
- Review finding 2: source fingerprint 原先只绑定提交，未拒绝 dirty 或缺少显式 clean state 的源码仓库。
- RED: `python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\revision-red"` -> FAIL，`10 failed, 19 passed`；7 个 migration contract 字段漂移和 3 个 dirty/missing/non-boolean clean-state 场景未被阻断。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\revision-green"` -> PASS，`29 passed in 5.25s`。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_sql_preflight_gate.py -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\revision-focused"` -> PASS，`83 passed in 4.85s`。
- REGRESSION: `python -X utf8 -m pytest scripts/tests tests -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\revision-full"` -> PASS，`175 passed in 40.72s`。
- REGRESSION: PowerShell 5.1 AST parse -> PASS；`git diff --check` -> PASS（仅 CRLF working-copy 提示）。
- REGRESSION: JDK 17 `mvn.cmd -f backend\pom.xml test` -> PASS，`26 tests`，`BUILD SUCCESS`。
- REGRESSION: 既定 Node 发布合同命令 -> PASS，`6 tests`。
- Revision result: runner 现在规范化并精确比较 `migrationId/file/sha256/type/allowedEnvironments/dependsOn/riskLevel`，确认 `database.schemaMigrations` 与 `requiredSql` 一一相同后才调用 planner；每个 source repo 必须显式为 JSON boolean `dirty=false`，clean-state 同时进入 `sourceFingerprint`。PowerShell prospective manifest 继续复用 `New-ReleaseSourceRepoManifestEntries` 提供 `dirty` 字段。

### Phase P2 - Verifiable Native Docker Cache

- Executor scope: 仅实现 P2（P2-AC1..P2-AC5）；未实现自定义缓存、缓存服务、弱校验开关或 fallback，未连接 Docker daemon、SSH、NAS、数据库或服务器。
- Changed paths:
  - `ops/deploy/publish-int-ruoyi.ps1`
  - `ops/release/release_docker_build_evidence.py`
  - `scripts/tests/test_release_build_preflight_cache.py`
  - `doc/tasks/release-preflight-cache-optimization-20260908/execution-log.md`
- BDD: 相同应用镜像输入复用 Docker 原生缓存 -> Given Dockerfile、实际 COPY 文件、build args 和明确 base image digest 相同 / When build-release 构建 backend/frontend / Then 不传 `--no-cache`，输入 fingerprint 保持相同并由 Docker/BuildKit 原生缓存决定命中。
- BDD: 任一物化输入漂移阻断后续打包 -> Given 构建前已 capture input evidence / When Dockerfile、COPY context、build arg 或 base image digest 在构建中变化 / Then 构建后重建 spec 并复算失败，actual image inspect、docker save 和 NAS copy 不继续。
- BDD: 最终包保存可复算镜像证据 -> Given 构建输入前后相同且实际镜像 inspect 成功 / When 写入安装包 / Then `manifest/docker-build-evidence.json` 保存 input/dockerfile/context/base/buildArgs/actualImage/evidenceDigest，并由后续 manifest 与 P0 完整性校验覆盖。
- RED: `python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\p2-red"` -> FAIL，`8 failed, 34 passed`；预期原因为 Docker evidence runner 尚不存在、应用镜像仍含 `--no-cache`、调用顺序合同未实现。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\p2-unit-delivery"` -> PASS，`42 passed in 7.17s`，包含 backend 固定 fingerprint 向量。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\p2-focused-final"` -> PASS，`153 passed in 44.29s`。
- REGRESSION: `python -X utf8 -m pytest scripts/tests tests -q --basetemp "$env:TEMP\release-preflight-cache-optimization-20260908\p2-full"` -> PASS，`188 passed in 52.51s`。
- REGRESSION: PowerShell 5.1 AST parse -> PASS；Python `py_compile` -> PASS；`git diff --check` -> PASS（仅 CRLF working-copy 提示）。
- REGRESSION: 既定 Node 发布合同命令 -> PASS，`6 tests`。
- REGRESSION: JDK 17 `mvn.cmd -f backend\pom.xml test` 首轮出现既有 `RuntimeControlOriginalParityTest.releaseStatusExposesCurrentReleaseNotesForCurrentEnvironmentsOnly` 时间排序不稳定（expected `release-test-notes`，actual `release-old-history`）；未改测试或产品逻辑，原命令立即单独复跑 -> PASS，`26 tests`，`BUILD SUCCESS`。
- P2-AC1: PASS（executor evidence）— backend/frontend `docker build` 均移除 `--no-cache`，未新增跳过或弱校验参数。
- P2-AC2: PASS（executor evidence）— 独立 runner 解析每个 Dockerfile 的 `ARG`、单一 `FROM` 与实际 `COPY`，仅递归哈希该组件 COPY 的最小 context；fingerprint 同时覆盖 Dockerfile bytes、规范路径/内容/大小、全部 build args、base reference/digest 和目标 image reference。
- P2-AC3: PASS（executor evidence）— 缺文件、路径逃逸、glob、不支持 COPY、重复/大小写冲突、空目录、symlink、缺 build arg、FROM/base 不一致和非法 digest 均非零失败；构建后由新 spec 复算并与构建前 evidence 全量比较，漂移发生在 actual image inspect/docker save 前即阻断。
- P2-AC4: PASS（executor evidence）— 构建后先复算输入，再 inspect backend/frontend 实际 image ID/RepoDigests；最终 `release-docker-build-evidence/v1` 写入包内 `manifest/docker-build-evidence.json`，包含每组件 inputFingerprint、dockerfile/context/baseImage/buildArgs/actualImage 及顶层 evidenceDigest。
- P2-AC5: PASS（executor evidence）— 最终 evidence 在 `docker save` 前生成且进入包；原有 `docker save -> Write-ReleaseManifest -> Test-ReleasePackageIntegrity -> Copy-ReleasePackageToNas` 顺序保持，P0 governance 聚焦回归全部通过。
- Risk: 本轮按批准范围仅用本地文件 fixture 和发布脚本调用顺序合同验证，没有执行真实 Docker build/cache hit。真实 Docker 主机必须预先存在并可 inspect `nginx:1.27-alpine`；缺失时正式流程 fail fast，不自动 pull 或降级。Maven 首轮暴露一个与 P2 无关的既有时间排序不稳定用例，单独复跑已通过，未在本任务扩大修复范围。
- Executor result: P2 implementation ready for independent tester；未提交，未修改 `task-state.json`、`prd.md`、`test-plan.md`、`test-report.md` 或 `task.md`。

## Outstanding Blockers

- None yet.
