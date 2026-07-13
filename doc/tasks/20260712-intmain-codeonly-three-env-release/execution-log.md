# 20260712 IntRuoyi int_main code-only 三环境发布执行日志

## Initial Request

- REQUEST: 执行 IntRuoyi 不带数据的完整三环境发布闭环，使用维护仓、后端仓、前端仓当前 `int_main` 已提交 HEAD，在干净临时发布 worktree 中构建并发布到测试服、正式服和备份服。
- SCOPE: code-only；构建使用 `SkipDatabaseSync` 和 `SkipMinioSync`；不执行备份、恢复或回滚；正式/备份发布授权口径为 `PROD`。
- HARD RULE: 不得让未提交改动、未跟踪文件、脏工作区内容进入发布包；不得拼接不同 `releaseTag`；不得 mock、默认成功、静默跳过或手工标绿。
- STARTED: 2026-07-12T22:48:05+08:00。

## Milestone 1 - Task Records

- GREEN: task-directory -> PASS，创建 `doc/tasks/20260712-intmain-codeonly-three-env-release/`。
- GREEN: task-doc-bootstrap -> PASS，已写入 `task.md` 与 `execution-log.md` 初始目标、里程碑、验证标准和设计约束。

## BDD Scenarios

- BDD: clean committed release input -> Given 三仓 `int_main` 有已提交 HEAD 且主工作区可能存在脏改, When 本次发布开始, Then 必须创建本次专用临时 release worktree 并只从冻结 HEAD 构建。
- BDD: code-only manifest contract -> Given 本轮发布为 code-only 且使用 `SkipDatabaseSync`/`SkipMinioSync`, When build-release 完成, Then Manifest 必须为 `publishScope=code-only`、sourceRepos clean 且发布包不包含数据目录。
- BDD: full release chain -> Given 测试服验证通过且用户授权 `PROD`, When 执行完整发布闭环, Then 同一 releaseTag 必须依次完成 `publish-test`、`mark-tested`、`promote-prod`、`promote-backup` 且五个 operation 均为 SUCCESS。
- BDD: real runtime validation -> Given 发布动作成功, When 判定环境完成, Then 必须分别在测试服、正式服、备份服验证 `.env IMAGE_TAG`、镜像 tag、backend health、frontend HTTP、PDF worker HTTP，备份服还要验证 `/mnt/intruoyi-data`。

## Milestone 2 - Experience Preflight

- COMMAND: 读取并摘录 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`；按经验索引补充读取 `docs/test-release-preflight.md`、`docs/powershell-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`。
- GREEN: experience-preflight -> PASS，已命中完整三环境发布、code-only、Manifest v1、required SQL/migration、publish-test、mark-tested、promote-prod、promote-backup、备份服 `/mnt/intruoyi-data`、PowerShell/SSH、日志脱敏和 closeout worktree 门禁。
- ISSUE: P001 PowerShell Bash heredoc 误用，已改用 PowerShell single-quoted here-string 管道到 `python -X utf8 -`，未影响构建/发布/服务器状态。

## Milestone 3 - Release Worktree Freeze

- COMMAND: 从三仓当前 `int_main` 已提交 HEAD 创建本轮专用 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712c\m|b|f`。
- GREEN: worktree-freeze -> PASS，maintenance=`ad054b2bc218e1dea834c48a83e2b1fa2f8a4af1`，backend=`1cafac7a985e5cb6d0e2724fb9f0cc391a1b3b6c`，frontend=`1b359734068d845b690c8f0c45e72f9bc040ce0c`。
- GREEN: release-worktree-clean -> PASS，三个 release worktree 均为 detached HEAD，`git status --porcelain` 为空。
- NOTE: 三个主工作区均存在脏改或未跟踪内容；本轮构建只使用冻结 release worktree，主工作区脏内容不得进入发布包。
- EVIDENCE: `evidence/freeze-worktree-r260712c.json`。
- ISSUE: P002 读取运行控制台本地配置时原始输出包含 NAS 密码字段；该输出未写入任务证据、不会提交，后续只记录脱敏字段名和结构化检查结果。

## Milestone 4 - Prebuild Gates

- RED: backend migration policy gate command contract -> FAIL，命令携带当前脚本不支持的 `--json`，exit=2，构建未启动，未发布，未触碰服务器。
- EVIDENCE: `evidence/backend-migration-policy-gate.err.log`、`evidence/backend-migration-policy-gate.out.json`。
- ISSUE: P003 migration policy gate 参数契约漂移；已沉淀经验，下一步按当前冻结脚本 `--help` 显示的 `--output` 参数重跑。
- GREEN: backend migration policy gate rerun -> PASS，使用当前脚本支持的 `--output` 参数，输出 `evidence/backend-migration-policy-gate-rerun.json`。
- GREEN: maintenance code-only required SQL contract -> PASS，`pytest tests/test_code_only_required_sql_contract.py -q`。
- GREEN: maintenance runtime contract tests -> PASS，`mvn -f backend\pom.xml -Dtest=RuntimeControlContractTest,RuntimeControlOriginalParityTest test`。
- GREEN: maintenance console build from r260712c -> PASS，Jar SHA256=`33DBE3780DC9414F7AEDB12ACDD82ED0B33C4E772C80916349AEB415A7CC2712`。
- GREEN: runtime-control switch r260712c -> PASS，本地 48181 进程加载 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712c\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，health=`UP`。
- RED: build-release preview r1 target gate -> FAIL，缺 `-ProdServerHost`；构建未启动，未生成发布包，未触碰服务器。
- EVIDENCE: `evidence/build-release-preview-r1.json`、`evidence/build-release-preview-r1-gate.json`、`evidence/build-release-preview-r1-raw-summary.json`。
- ISSUE: P004 build-release 三环境预览缺 ProdServerHost；已按 TDD 修改维护仓代码并通过契约测试。
- GREEN: prodhost contract fix tests -> PASS，`mvn -f backend\pom.xml -Dtest=RuntimeControlContractTest,RuntimeControlOriginalParityTest test`。
- COMMIT: maintenance `367786f`，message=`任务: 修复三环境构建预览目标参数`。
- RESULT: 旧 release worktree `r260712c` 基于维护仓旧 HEAD `ad054b2`，不得继续出包；下一步停止旧 48181 运行控制台，删除本任务旧 release worktree，并从新维护仓 HEAD 重新冻结。

## Milestone 5 - r260713c Refreeze and Build r1

- GREEN: old release worktree cleanup -> PASS，停止引用 `r260712c` 的 Java 进程，删除 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712c`，见 `evidence/refreeze-worktree-r260713c.json`。
- GREEN: refreeze r260713c -> PASS，maintenance=`367786f125c3075aa2507854ee5d91b4479d3c69`，backend=`1cafac7a985e5cb6d0e2724fb9f0cc391a1b3b6c`，frontend=`1b359734068d845b690c8f0c45e72f9bc040ce0c`；三个 release worktree clean。
- GREEN: r260713c prebuild gates -> PASS，后端 migration policy gate、维护仓 code-only required SQL contract、维护仓 runtime contract tests 均通过。
- GREEN: r260713c maintenance console build -> PASS，Jar SHA256=`AC3E738917FCB413F426C6DDDB5586460DB8EEF2A7A82DFFC23C201DE9E8E712`。
- GREEN: runtime-control switch r260713c -> PASS，本地 48181 进程加载 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713c\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，health=`UP`。
- GREEN: build-release preview r260713c r1 -> PASS，`-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`、`-TestServerHost 172.30.30.58`、`-ProdServerHost 172.30.30.57`、`-BackupServerHost 172.30.30.59`、`BackendRepoRoot`、`FrontendRepoRoot` 均正确。
- RED: build-release r260713c r1 -> FAIL，operation=`op-2026-07-13T002006160172900Z-65295a64-bf64-4425-81cf-2e600bafbea0`，状态 `FAILED`；日志显示应用前端 `node_modules` 缺失导致 `cross-env` 不可用。后端 Maven 已完成，但没有可发布 Manifest，未执行服务器写入。
- EVIDENCE: `evidence/build-release-final-r260713c-r1.json`、`evidence/build-release-log-r260713c-r1.raw.json`、`evidence/build-release-preview-r260713c-r1-gate.json`。
- ISSUE: P005 release worktree 应用前端依赖未恢复；已沉淀经验，下一步恢复前端依赖并使用新的 releaseTag r2 重建。
- GREEN: frontend dependency restore r260713c -> PASS，在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713c\f` 执行 `pnpm install --frozen-lockfile`，生成 `node_modules/.bin/cross-env.cmd`，`git status --porcelain --ignored=no` 为空；见 `evidence/frontend-install-r260713c.out.log`、`evidence/frontend-install-r260713c.err.log`。
- ISSUE: P006 Python subprocess 直接调用 `pnpm` 无法解析 PowerShell wrapper；已改用 `pnpm.cmd` 绝对路径，未影响发布输入。
- GREEN: build-release preview r260713c r2 -> PASS，`releaseTag=release-20260713-intmain-codeonly-three-env-r260713c-r2`，preview gate 确认 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`、三环境 Host、BackendRepoRoot、FrontendRepoRoot 均正确。
- GREEN: build-release r260713c r2 -> PASS，operation=`op-2026-07-13T003414055290400Z-64d6fa63-206a-4d0d-927d-dfa49d0332b2`，status=`SUCCESS`；发布包路径 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260713-intmain-codeonly-three-env-r260713c-r2`。
- GREEN: manifest-validation r260713c r2 -> PASS，`manifest.json` 与 `release-manifest.json` 存在，`publishScope=code-only`，backend commit=`1cafac7a985e5cb6d0e2724fb9f0cc391a1b3b6c`，frontend commit=`1b359734068d845b690c8f0c45e72f9bc040ce0c`，sourceRepos dirty=false，变更说明存在，未发现数据目录，镜像包大小 815495680 bytes。
- EVIDENCE: `evidence/build-release-preview-r260713c-r2.json`、`evidence/build-release-preview-r260713c-r2-gate.json`、`evidence/build-release-submit-r260713c-r2.json`、`evidence/build-release-final-r260713c-r2.json`、`evidence/manifest-validation-r260713c-r2.json`。

## Milestone 6 - publish-test r260713c r2 Failure and Backend Fix

- GREEN: publish-test preview r260713c r2 -> PASS，preview gate 确认 `-Mode deploy-release`、`-Environment test`、`-ReleaseTag release-20260713-intmain-codeonly-three-env-r260713c-r2`、`-ServerHost 172.30.30.58`、`-RemoteAppDir /opt/intruoyi/runtime`。
- RED: publish-test r260713c r2 -> FAIL，operation=`op-2026-07-13T004825053690400Z-436f346e-5afd-4b88-b5de-be19cf186a6c`，status=`FAILED`；required SQL `20260708_mes_batch_record_version_phase_one.sql` line 291 报 `ERROR 1146`，缺 `mes_pro_route_use_process_batch_record`。
- EVIDENCE: `evidence/publish-test-preview-r260713c-r2.json`、`evidence/publish-test-preview-r260713c-r2-gate.json`、`evidence/publish-test-submit-r260713c-r2.json`、`evidence/publish-test-final-r260713c-r2.json`、`evidence/publish-test-log-r260713c-r2.redacted.json`。
- GREEN: publish-test failure db snapshot -> PASS，只读确认测试服存在 `mes_pro_route_use_process_batch_record_legacy_20260709`，不存在当前 `mes_pro_route_use_process_batch_record`；`20260708_mes_batch_record_version_phase_one` 状态 FAILED，`20260709_mes_route_flow_config_unification` 状态 SKIPPED_ALREADY_APPLIED；见 `evidence/publish-test-failure-db-snapshot-r260713c-r2.json`。
- ISSUE: P007 publish-test 原始日志含 `mysql -p...` 明文参数；已删除 raw evidence，保留 redacted evidence，并将增强 secret scan 写入 `evidence/evidence-secret-scan-r260713c-r2.json`。
- ISSUE: P008 required SQL 引用已重命名路线用途批记录表；已沉淀经验到 `docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md` 和 `docs/experience-index.md`。
- RED: backend regression route-flow legacy rename order -> FAIL，`python -X utf8 -m pytest script\tests\test_mes_batch_record_version_sql.py -q` 失败于 `test_batch_record_version_migration_handles_route_flow_legacy_rename_order`，证明 `20260708` SQL 没有当前表/legacy 表双路径 `table exists` 守卫。
- GREEN: backend regression route-flow legacy rename order -> PASS，`python -X utf8 -m pytest script\tests\test_mes_batch_record_version_sql.py -q`，7 passed。
- GREEN: backend related SQL regression -> PASS，`python -X utf8 -m pytest script\tests\test_release_migration_metadata_sql_20260708.py script\tests\test_mes_route_flow_config_migration_sql.py -q`，9 passed。
- GREEN: backend migration policy gate after fix -> PASS，`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql --output ...\backend-migration-policy-gate-after-route-legacy-fix.json`。
- COMMIT: backend `fdd93ec98c`，message=`任务: 修复批记录版本SQL兼容路线流迁移`。
- RESULT: `release-20260713-intmain-codeonly-three-env-r260713c-r2` 判废；下一步删除/弃用旧 release worktree，基于维护仓 `367786f`、后端 `fdd93ec98c`、前端 `1b359734` 重新冻结并用新的 releaseTag 重建。

## Milestone 7 - r260713d Stale Result Cleanup and r260713e Refreeze

- NOTE: 旧 release worktree `r260713d` 已生成并测试服发布 `release-20260713-intmain-codeonly-three-env-r260713d-r1`，build operation=`op-2026-07-13T012022161722800Z-7a5d8178-ceed-4c15-94ba-ce78e30993a5`，publish-test operation=`op-2026-07-13T013213335392600Z-7d8cd762-0582-4517-88ac-28f32059d1e6`，二者 status=`SUCCESS`。
- RESULT: `release-20260713-intmain-codeonly-three-env-r260713d-r1` 判废且不得继续 `mark-tested/promote-prod/promote-backup`，因为用户最新发布输入要求当前 `int_main` 已提交 HEAD，而 `r260713d` 使用 backend=`fdd93ec98cfe8e020982ec59e1e03da633cfeef7`、frontend=`1b359734068d845b690c8f0c45e72f9bc040ce0c`，不是当前 backend=`b382403450f12857e6c4d4de1455dbb0be00a033`、frontend=`14424c03ff16f5ee989d6b7585b881145a1691ff`。
- ISSUE: P009 旧 worktree 清理首次进程匹配命中当前 PowerShell 命令行，自身提前终止；随后按当前进程排除守卫重跑。
- ISSUE: P010 `git worktree remove --force` 对 `r260713d\m` 和 `r260713d\f` 返回 `Directory not empty`，Git 注册已注销但物理目录残留；已按 worktree-memory 先确认注册不存在、路径受限、无进程引用，再删除残留目录。
- GREEN: old stale worktree cleanup -> PASS，`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713d` 物理根目录不存在，三仓 `git worktree list --porcelain` 均不含 `r260713d`。
- GREEN: refreeze r260713e -> PASS，maintenance=`367786f125c3075aa2507854ee5d91b4479d3c69`，backend=`b382403450f12857e6c4d4de1455dbb0be00a033`，frontend=`14424c03ff16f5ee989d6b7585b881145a1691ff`；三个 release worktree 均为 detached HEAD 且 `git status --porcelain` 为空。
- GREEN: runtime-control local config r260713e -> PASS，已将本地私有配置写入 `r260713e\m\config\runtime-control.local.yaml`，只调整 `repo-root`、`frontend-root`、`ops-root` 和 `state-dir` 到本轮 release worktree；配置文件被 `.gitignore` 忽略，release worktree 仍 clean，未把 secret-bearing 配置写入 evidence。
- GREEN: r260713e prebuild gates -> PASS，后端 migration policy gate 通过，业务前端 `pnpm install --frozen-lockfile` 通过且 `cross-env.cmd` 存在，维护控制台 `scripts\build.ps1` 通过，Jar SHA256=`95B128361603E9321602AC6BDD63DAD7FB2335070131D37A9943C8579B89C0AC`，`pytest tests/test_code_only_required_sql_contract.py -q` 通过。
- GREEN: runtime-control switch r260713e -> PASS，本地 48181 进程加载 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713e\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，health=`UP`。
- GREEN: build-release preview r260713e r1 -> PASS，`releaseTag=release-20260713-intmain-codeonly-three-env-r260713e-r1`，preview gate 确认 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`、三环境 Host、BackendRepoRoot、FrontendRepoRoot 均正确。
- RED: build-release r260713e r1 -> FAIL，operation=`op-2026-07-13T020341321200Z-97c25063-2488-4604-aebf-2d62697b2496`，status=`FAILED`；日志显示本地 `docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' <container>` 在脚本 `publish-int-ruoyi.ps1:1132` 抛出 `Exception 0xc0000005`，退出码 1。发布包目录不存在，未生成 Manifest，未执行 publish-test/mark-tested/promote-prod/promote-backup。
- ISSUE: P011 build-release 本地 Docker inspect native crash；已冻结 operation、preview、日志和 packageDirMissing 证据，旧 releaseTag 判废。
- ISSUE: P012 排障时直接打印 Docker env 暴露容器环境变量；该输出未写入任务证据或仓库文件，后续仅使用白名单/脱敏检查，并已沉淀前置门禁。
- GREEN: docker inspect preflight after r1 failure -> PASS，`docker version` 可用，`int-ruoyi-mysql` 与 `docker-minio-1` 存在，本地 inspect 最小命令恢复可用；下一步使用新的 `r260713e-r2` releaseTag 重建。

## Milestone 8 - 2026-07-13 Continuation Refreeze to Current int_main HEAD

- COMMAND: 重新读取发布前置经验门禁：`docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`、`docs\powershell-preflight-lessons.md`、`docs\test-release-preflight.md`。
- GREEN: experience-preflight -> PASS，当前完整三环境 code-only 发布继续命中干净发布输入、Manifest v1、required SQL/migration、publish-test、mark-tested、promote-prod、promote-backup、备份服 `/mnt/intruoyi-data`、PowerShell/SSH/日志脱敏和 closeout 门禁。
- COMMAND: 重新核对三仓主工作区 HEAD 与 dirty 状态。maintenance=`367786f125c3075aa2507854ee5d91b4479d3c69`，backend=`4d7baa09fa7642dfd5017239622fecfe83c2796e`，frontend=`08c269172045526e2ed730b4c932d93dfab94e4a`；三仓主工作区均存在未提交或未跟踪内容，必须继续只从专用干净 release worktree 构建。
- RESULT: 旧 `r260713e` 判废，不得继续使用旧失败或旧构建结果，因为它冻结的 backend=`b382403450f12857e6c4d4de1455dbb0be00a033`、frontend=`14424c03ff16f5ee989d6b7585b881145a1691ff` 已不是本轮继续执行时的当前 `int_main` HEAD。
- GREEN: stale worktree cleanup r260713e -> PASS，已停止引用 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713e\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 的本任务旧 Java 进程；三仓 `git worktree list --porcelain` 均不含 `r260713e`；物理目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713e` 已删除。
- ISSUE: P013 `git worktree remove --force` 对 `r260713e\m` 和 `r260713e\f` 返回 `Directory not empty`，且首次物理删除因 `remapping` 权限拒绝失败；影响为清理未完成前不得复用或继续发布。原因判断为 Windows 深层依赖目录/属性残留。处理动作为先确认 Git 注册为 0、路径在本任务固定根、无外部 Java 占用，再 `attrib -R -S -H` 后受限删除。结果为物理根目录不存在；可前置检查=是；可自动化=是；下次避免=删除前先做属性归一化和进程守卫。
- GREEN: refreeze r260713f -> PASS，maintenance=`367786f125c3075aa2507854ee5d91b4479d3c69`，backend=`4d7baa09fa7642dfd5017239622fecfe83c2796e`，frontend=`08c269172045526e2ed730b4c932d93dfab94e4a`；三个 release worktree 均为 detached HEAD 且 `git status --porcelain --ignored=no` 为空。
- GREEN: r260713f prebuild gates -> PASS，backend migration policy gate、业务前端 `pnpm install --frozen-lockfile`、维护仓 code-only required SQL contract、维护仓 runtime contract tests、维护控制台 build 均通过；维护控制台 Jar SHA256=`EB632C0B84B8096C76DA81422F118EFFD56351B676401D0D111FEDB5A6885E41`。
- GREEN: runtime-control switch r260713f -> PASS，本地 48181 进程加载 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713f\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，health=`UP`。
- GREEN: build-release preview r260713f r1 -> PASS，`-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`、三环境 Host、BackendRepoRoot、FrontendRepoRoot 均正确。
- GREEN: build-release r260713f r1 -> PASS，operation=`op-2026-07-13T025622433587900Z-c4213c3a-32cb-42eb-a70b-afd1bba25fd9`，status=`SUCCESS`。
- GREEN: manifest-validation r260713f r1 -> PASS，packageDir=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260713-intmain-codeonly-three-env-r260713f-r1`，Manifest v1 与 legacy manifest 存在，`publishScope=code-only`，sourceRepos backend=`4d7baa09fa7642dfd5017239622fecfe83c2796e`、frontend=`08c269172045526e2ed730b4c932d93dfab94e4a`，dirty=false，未发现数据目录，变更说明存在。
- ISSUE: P014 测试服发布前只读锁表预检首次使用不存在字段 `updated_time`，MySQL 报 `Unknown column 'updated_time'`；未执行发布写入。已改为先 `SHOW COLUMNS FROM infra_release_operation_lock`，再按实际 `update_time` 查询。结果：测试服锁为 `APPLIED`，当前旧版本 r260713e-r2，可继续发布；可前置检查=是；可自动化=是；下次避免=锁表查询必须 DESCRIBE 或使用当前 schema 字段。
- GREEN: publish-test preview r260713f r1 -> PASS，preview gate 确认 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`、目标 releaseTag 和无 promote/mark-tested 动作。
- GREEN: publish-test r260713f r1 -> PASS，operation=`op-2026-07-13T031227142640400Z-daf36b95-a77c-43f5-864d-2e7e6baf5f1b`，status=`SUCCESS`。
- GREEN: test runtime verification r260713f r1 -> PASS，测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=`UP`、frontend HTTP 200、`/release-info.json`、PDF worker HTTP 200 均为 `release-20260713-intmain-codeonly-three-env-r260713f-r1`。
- ISSUE: P015 `mark-release-tested` 预览首次携带 `targetEnvironment=test` 返回 `targetEnvironment` 错误；未执行 mark-tested。原因判断：运行控制台契约要求 mark-tested 不传 targetEnvironment，并从当前测试服 releaseTag 自动解析；同时必须提供真实 `selectedRecoverySetCandidateId`。处理动作：读取 restore candidates，使用 `restore:20260621-063218`，去掉 targetEnvironment 后重试。结果：预览和执行通过；可前置检查=是；可自动化=是；下次避免=mark-tested payload 固定禁止 targetEnvironment，候选 ID 必须来自 `/restore-candidates`。
- GREEN: mark-tested r260713f r1 -> PASS，operation=`op-2026-07-13T033002346251200Z-4aa4245b-2b17-4979-9e96-f1480a17bfdc`，status=`SUCCESS`，selectedRecoverySetCandidateId=`restore:20260621-063218`。
- GREEN: promote-prod preview r260713f r1 -> PASS，preview gate 确认 `-Environment prod`、`-ConfirmText PROD`、`-RequireTested`、releaseTag 和 ProdDryRunEvidencePath。
- GREEN: promote-prod r260713f r1 -> PASS，operation=`op-2026-07-13T033204221394900Z-d0bebaca-2bab-4150-8da4-a9fb35efb329`，status=`SUCCESS`。
- GREEN: prod runtime verification r260713f r1 -> PASS，正式服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=`UP`、frontend HTTP 200、PDF worker HTTP 200、`/release-info.json` 均为 `release-20260713-intmain-codeonly-three-env-r260713f-r1`。
- GREEN: promote-backup preview r260713f r1 -> PASS，preview gate 确认 `-Environment backup`、`-ServerHost 172.30.30.59`、`-ConfirmText PROD`、`-RequireTested`、`RemoteReleaseRoot=/mnt/intruoyi-data/intruoyi-releases`、`RemoteDataRoot=/mnt/intruoyi-data/runtime-data`、`RemoteDataDiskMount=/mnt/intruoyi-data`、`RemoteDataDiskDevice=/dev/mapper/cl-home`、`RemoteMinioContainer=intruoyi-minio`。
- GREEN: promote-backup r260713f r1 -> PASS，operation=`op-2026-07-13T034834951764600Z-52a4de0f-ff9c-41aa-9a29-54f3c2baa020`，status=`SUCCESS`。
- GREEN: backup runtime verification r260713f r1 -> PASS，备份服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=`UP`、frontend HTTP 200、PDF worker HTTP 200、`/release-info.json` 均为目标 releaseTag；`findmnt` 证明 `/dev/mapper/cl-home /mnt/intruoyi-data ext4`，发布目录 `/mnt/intruoyi-data/intruoyi-releases/<releaseTag>` 与数据根 `/mnt/intruoyi-data/runtime-data` 存在。
- ISSUE: P016 Playwright 脚本经 PowerShell here-string 管道传入 Node 时，中文正则 `/查看变更/` 被污染为 `/????/` 并触发 `SyntaxError`；未执行页面动作。处理动作：改用 Unicode 转义 `\u67e5\u770b\u53d8\u66f4` 等 ASCII 源码重跑。结果：真实浏览器验证运行控制台三环境版本号和变更说明通过；可前置检查=是；可自动化=是；下次避免=PowerShell 管道传 Node/Playwright 源码时中文常量统一 Unicode 转义或写 UTF-8 脚本文件。
- GREEN: runtime-console release notes page -> PASS，Playwright 打开 `http://127.0.0.1:48181/`，测试服/正式服/备份服均显示 `release-20260713-intmain-codeonly-three-env-r260713f-r1`，三个“版本变更说明”对话框均包含 releaseTag 和变更项，console error=0。
- GREEN: runtime-control restore main path -> PASS，已停止 r260713f 临时 48181 Java 进程并启动主路径 `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，health=`UP`，进程命令行不再包含 `r260713f`。
- GREEN: closeout worktree cleanup r260713f -> PASS，三个 release worktree 清理前均 clean；`git worktree list --porcelain` 三仓均不含 `r260713f`；物理目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713f` 不存在；运行控制台仍为主路径且 health=`UP`。
- RESULT: 同一 releaseTag `release-20260713-intmain-codeonly-three-env-r260713f-r1` 完成 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`；五个 operation 均为 SUCCESS；三环境真实运行态、PDF worker、运行控制台版本变更说明和备份服数据盘挂载验证通过。

## Milestone 9 - Current HEAD Drift and r260713g Refreeze

- REQUEST: 用户再次明确目标为使用维护仓、后端仓、前端仓当前 `int_main` 已提交 HEAD 执行 code-only 完整三环境闭环，正式/备份发布授权口径为 `PROD`。
- COMMAND: 重新读取发布前置经验门禁：`docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`、`docs\powershell-preflight-lessons.md`、`docs\test-release-preflight.md`。
- GREEN: experience-preflight -> PASS，当前完整三环境 code-only 发布继续命中干净发布输入、Manifest v1、required SQL/migration、publish-test、mark-tested、promote-prod、promote-backup、备份服 `/mnt/intruoyi-data`、PowerShell/SSH/日志脱敏和 closeout 门禁。
- COMMAND: 重新核对三仓主工作区 HEAD 与 dirty 状态。maintenance=`367786f125c3075aa2507854ee5d91b4479d3c69`，backend=`738cfaeb04cc1b123de42283a01560b63fdac2b2`，frontend=`c1326e7b427ff1036bc49fcb401d6a365655099e`；三仓主工作区均存在未提交或未跟踪内容，必须继续只从专用干净 release worktree 构建。
- RESULT: 旧 `release-20260713-intmain-codeonly-three-env-r260713f-r1` 已完成但判为当前最终验收的过期成功证据，不得继续用它标记本次完成；下一步创建 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g\m|b|f` 并重新冻结当前 `int_main` HEAD。
- GREEN: refreeze r260713g -> PASS，maintenance=`367786f125c3075aa2507854ee5d91b4479d3c69`，backend=`738cfaeb04cc1b123de42283a01560b63fdac2b2`，frontend=`c1326e7b427ff1036bc49fcb401d6a365655099e`；三个 release worktree 均为 detached HEAD 且 `git status --porcelain --ignored=no` 为空。
- GREEN: r260713g prebuild gates -> PASS，backend migration policy gate 280 migrations passed，业务前端 `pnpm install --frozen-lockfile` 且 `cross-env.cmd` 存在，维护仓 code-only required SQL contract、runtime contract tests、维护控制台 build 均通过；维护控制台 Jar SHA256=`88B04A7EA2DB2963F528989C6727CE745F73282D51018305EC8421769CC5D94E`。
- ISSUE: P017 PowerShell stdin 脚本首字节 BOM 导致 Python `SyntaxError: invalid non-printable character U+FEFF`；未改文件，改用 `exec(sys.stdin.read().lstrip('\ufeff'))` 后继续。
- ISSUE: P018 运行控制台 `state-dir` 首次指向 release worktree 内 `runtime/`，造成维护 release worktree 出现未跟踪目录；未执行 build-release。处理动作为将 `state-dir` 移到 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g-state`，删除 `m\runtime`，重启 48181 后三仓 clean。
- GREEN: runtime-control switch r260713g -> PASS，本地 48181 进程加载 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，health=`UP`，三仓 release worktree clean。
- GREEN: build-release preview r260713g r1 -> PASS，`-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`、三环境 Host、BackendRepoRoot、FrontendRepoRoot 均正确。
- GREEN: build-release r260713g r1 -> PASS，operation=`op-2026-07-13T042641075294500Z-a45c6318-f096-4085-9715-38795a98fa74`，status=`SUCCESS`。
- GREEN: manifest-validation r260713g r1 -> PASS，packageDir=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260713-intmain-codeonly-three-env-r260713g-r1`，Manifest v1 与 legacy manifest 存在，`publishScope=code-only`，backend commit=`738cfaeb04cc1b123de42283a01560b63fdac2b2`、frontend commit=`c1326e7b427ff1036bc49fcb401d6a365655099e`，dirty=false，artifact 校验通过，未发现数据目录，变更说明存在。
- GREEN: publish-test preview r260713g r1 -> PASS，preview gate 确认 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`、目标 releaseTag 和无 promote/mark-tested 动作；测试服锁表 `update_time` schema-aware 预检通过。
- GREEN: publish-test r260713g r1 -> PASS，operation=`op-2026-07-13T043904247039400Z-58e11f61-27d7-4475-897f-726cf69c0367`，status=`SUCCESS`。
- ISSUE: P019 运行控制台 operation log 再次输出 `mysql -p...` 明文参数；本任务 evidence 内发布 tail 已脱敏，只保留 redacted-tail，经验门禁已补充为保存/提交日志前必须扫描并脱敏。
- GREEN: test runtime verification r260713g r1 -> PASS，测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=`UP`、frontend HTTP 200、`/release-info.json`、PDF worker HTTP 200、release lock APPLIED 均为目标 releaseTag。
- GREEN: mark-tested r260713g r1 -> PASS，operation=`op-2026-07-13T045527979959Z-8ae49468-8a07-46ca-a512-aab65f41f62d`，status=`SUCCESS`，selectedRecoverySetCandidateId=`restore:20260621-063218`，未携带 targetEnvironment。
- ISSUE: P020 promote-prod preview gate 首次用偶数参数配对解析，被 `-RequireTested` 单值 flag 打乱而误判 `ServerHost` 缺失；预览本身包含 `-ServerHost 172.30.30.57`，重写 flag-aware parser 后通过。
- GREEN: promote-prod preview r260713g r1 -> PASS，确认 `-Environment prod`、`-ConfirmText PROD`、`-RequireTested`、`ServerHost=172.30.30.57`、`RemoteAppDir=/opt/intruoyi/runtime`。
- GREEN: promote-prod r260713g r1 -> PASS，operation=`op-2026-07-13T045743664719Z-4c45114b-fa52-488d-b32a-3e39e4e00244`，status=`SUCCESS`。
- GREEN: prod runtime verification r260713g r1 -> PASS，正式服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=`UP`、frontend HTTP 200、PDF worker HTTP 200、`/release-info.json`、release lock APPLIED 均为目标 releaseTag。
- GREEN: promote-backup preview r260713g r1 -> PASS，确认 `-Environment backup`、`-ServerHost 172.30.30.59`、`-ConfirmText PROD`、`-RequireTested`、`RemoteReleaseRoot=/mnt/intruoyi-data/intruoyi-releases`、`RemoteDataRoot=/mnt/intruoyi-data/runtime-data`、`RemoteDataDiskMount=/mnt/intruoyi-data`、`RemoteDataDiskDevice=/dev/mapper/cl-home`、`RemoteMinioContainer=intruoyi-minio`。
- GREEN: promote-backup r260713g r1 -> PASS，operation=`op-2026-07-13T051411658807100Z-2bb859ba-86d9-492b-8b32-3e9980ebe07c`，status=`SUCCESS`。
- GREEN: backup runtime verification r260713g r1 -> PASS，备份服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=`UP`、frontend HTTP 200、PDF worker HTTP 200、`/release-info.json` 均为目标 releaseTag；`findmnt` 证明 `/dev/mapper/cl-home /mnt/intruoyi-data ext4`，发布目录 `/mnt/intruoyi-data/intruoyi-releases/<releaseTag>` 与数据根 `/mnt/intruoyi-data/runtime-data` 存在。
- GREEN: runtime-console release notes page r260713g -> PASS，Playwright 打开 `http://127.0.0.1:48181/`，测试服/正式服/备份服均显示 `release-20260713-intmain-codeonly-three-env-r260713g-r1`，三个“版本变更说明”对话框均包含 releaseTag 和变更项，console error=0。
- GREEN: runtime-control restore main path -> PASS，48181 已恢复主路径 `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，health=`UP`，进程命令行不再包含 `r260713g`。
- ISSUE: P021 closeout 首次脚本在删除 r260713g 时返回 255 且无 stdout；复核确认主路径已恢复、维护 worktree 已注销，后端/前端 worktree 仍注册或残留。随后逐仓清理，前端 `git worktree remove --force` 返回 Directory not empty；按 worktree-memory 确认 Git 注册不存在、路径受限、无外部进程引用后删除物理残留。
- GREEN: closeout worktree cleanup r260713g -> PASS，三仓 `git worktree list --porcelain` 均不含 `r260713g`，物理目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g` 和 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g-state` 均不存在；运行控制台仍为主路径且 health=`UP`。
- RESULT: 同一 releaseTag `release-20260713-intmain-codeonly-three-env-r260713g-r1` 完成 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`；五个 operation 均为 SUCCESS；三环境真实运行态、PDF worker、运行控制台版本变更说明和备份服数据盘挂载验证通过。

## Milestone 10 - Final Closeout and Commit Scope

- GREEN: task-closeout preview -> PASS，`task_closeout.py --task-id 20260712-intmain-codeonly-three-env-release --mode preview` 返回 keep=`task.md/execution-log.md/issues.md/verification-report.md`，delete=`<none>`，blocked=`<none>`，warnings=`<none>`。
- GREEN: task-closeout apply -> PASS，`task_closeout.py --task-id 20260712-intmain-codeonly-three-env-release --mode apply` 返回 status=`applied`，delete=`<none>`，blocked=`<none>`，warnings=`<none>`。
- GREEN: runtime-control final health -> PASS，`http://127.0.0.1:48181/actuator/health` 返回 `{"status":"UP"}`，运行控制台已恢复主路径。
- GREEN: final worktree deletion check -> PASS，维护仓、后端仓、前端仓 `git worktree list --porcelain` 均不含 `r260713g`；`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g` 与 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713g-state` 均不存在。
- GREEN: final task status -> PASS，`task.md` 已标记 `completed`；最终提交仅包含本任务任务记录、请求日志和必要经验沉淀文件，排除无关脏改、旧任务改动、备份配置、临时输出和未跟踪杂项。
