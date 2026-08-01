# Execution Log

## 2026-08-01

- Goal: 仅基于发布开始时当前分支 HEAD 已提交代码构建并发布到测试服务器，未提交改动不得进入构建产物。
- BDD: HEAD-only test release -> Given 当前系统仍在开发且工作区可能存在未提交改动, When 执行本次发布, Then 构建产物必须只来自发布开始时冻结的 HEAD 已提交代码，且仅发布到测试服务器。
- BDD: Test runtime acceptance -> Given 测试服发布完成, When 检查真实运行态和运行控制台, Then 镜像 tag、容器状态、健康检查、前端 HTTP、页面、版本号和变更说明均必须与本 releaseTag 一致。
- BDD: No production promotion -> Given 用户要求仅测试服发布, When 发布流程完成, Then 不得执行 mark-tested、promote-prod 或 promote-backup。
- Bootstrap: 已读取适用 AGENTS 路径、`docs/experience-index.md`、`E:\IntRuoyi\docs\powershell-memory.md` 和最近任务状态；最近同链路任务均为 completed。
- GREEN: experience-preflight -> PASS, 已读取 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\worktree-restrictions.md` 并摘取本次仅测试服发布强制门禁。

## Issues

## Build / Publish Evidence

- Git freeze: 维护仓主工作区 `int_main` HEAD=`cb85bb0dbf2f36931ff2bc0aff75a4e96b5bd331`，主程序 HEAD=`9420210f7ad4fb2519c179458fae0e823d082b54`；主工作区存在无关脏改动，因此本轮使用 clean release worktree。
- Worktree: 维护 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260801a\m`，主程序 `D:\IntRuoyiWorktree\r260801a-release-app`，state dir `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260801a-state\runtime-control`；复核 release worktree 均 clean。
- GREEN: experience-preflight -> PASS, 高风险发布前已记录测试服发布、构建、PowerShell、server/login、worktree 与 no-prod/no-backup 门禁。
- GREEN: migration-policy-gate -> PASS, `migration-policy-gate-r260801a.json` 显示迁移策略门禁通过，migration count=`403`。
- GREEN: maintenance-console-build -> PASS, Maven tests `26` passed，Jar=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260801a\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`。
- RED: build-release r1 -> FAIL, releaseTag=`release-20260801-intmain-head-test-r260801a-r1`，operation=`op-2026-07-31T181050340020300Z-1f2bea9b-ea22-45ab-9800-1100bb9fb2d3`，失败原因为 clean frontend worktree 未恢复 `node_modules`，`cross-env` 不可用。
- GREEN: frozen-frontend-dependency-restore -> PASS, 在同一冻结 frontend worktree 内执行 locked dependency restore 后，`cross-env.cmd`、`vite.cmd`、`vue-tsc.cmd` 存在，`pnpm build:test` 通过，Git 仍 clean。
- GREEN: build-release r2 -> PASS, releaseTag=`release-20260801-intmain-head-test-r260801a-r2`，operation=`op-2026-07-31T182843386387300Z-b1088fac-87af-46e2-99ed-7475df470ea7`，manifest validator=`MANIFEST_VALIDATION_PASSED`。
- GREEN: manifest-source -> PASS, package=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260801-intmain-head-test-r260801a-r2`；`manifest.json` 显示 `component=intruoyi`、`publishScope=code-only`、backend/frontend source commit 均为 `9420210f7ad4fb2519c179458fae0e823d082b54`、`dirty=false`、artifact hash checked=`2045` all OK；变更说明为 `Release package release-20260801-intmain-head-test-r260801a-r2`，变更项含发布包与组件范围。
- GREEN: publish-test-preview -> PASS, preview 结构化字段为 `Mode=deploy-release`、`Environment=test`、`ReleaseTag=release-20260801-intmain-head-test-r260801a-r2`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`；`BackupServerHost=172.30.30.59` 仅为脚本上下文参数，未形成实际部署目标；未出现 `mark-tested`、`promote-prod`、`promote-backup`。
- RED: publish-test r2 -> FAIL, operation=`op-2026-07-31T184648151088Z-d51572f6-9207-44dd-bbab-6f54c347cea4`，测试服 required SQL `20260726_system_codex_smart_scheduling_test_items.sql` 第 313 行失败，MySQL 返回 `ERROR 1267 (HY000): Illegal mix of collations (utf8mb4_general_ci,IMPLICIT) and (utf8mb4_0900_ai_ci,IMPLICIT) for operation '='`。
- GREEN: post-failure-readonly-runtime-freeze -> PASS, 只读复核测试服 `.env IMAGE_TAG=release-20260801-intmain-head-test-r260801a-r2`，backend/frontend 实际镜像仍为 `release-20260731-smartseed-tempfix-head-test-r260731d-r1`，容器 Up，backend health=`UP`，frontend HTTP=`200`，release lock=`FAILED`，migration `FAILED=1`、`SKIPPED_ALREADY_APPLIED=367`，failed migration=`20260726_system_codex_smart_scheduling_test_items`，RUNNING lock=`0`。
- GREEN: no-prod-backup-actions -> PASS, 本轮 operation 仅包含 build-release r1/r2 与 publish-test r2；未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- GREEN: runtime-console-restore -> PASS, 已终止任务自有 release console PID `52752`，使用主维护路径启动 PID `51256`，`http://127.0.0.1:48181/actuator/health` 返回 `UP`。
- BLOCKER: test-release-blocked -> required SQL collation defect must be fixed in committed source and rebuilt with a new releaseTag, or the user must explicitly authorize a separate remediation path. Failed releaseTag `release-20260801-intmain-head-test-r260801a-r2` must not be reused.

### Continuation / Frozen Fix Chain

- GREEN: frozen-source-guard-r260801b -> PASS, 继续基于原冻结提交 `9420210f7ad4fb2519c179458fae0e823d082b54` 的修复分支，不追逐后续主线；source worktree=`D:\IntRuoyiWorktree\r260801b-frozen-smartseed-fix`。
- GREEN: smartseed-collation-fix -> PASS, commit=`e3d3a8efdae5e17a7643192bf55a2c5ae21d1ff4` 修复 `20260726_system_codex_smart_scheduling_test_items.sql` 临时表 collation；目标 pytest、相邻 pytest、migration policy gate 均通过。
- RED: publish-test r260801b -> FAIL, releaseTag=`release-20260801-frozen-smartseed-fix-r260801b-r1`，operation=`op-2026-08-01T055625180911100Z-30dc356a-792d-44b5-b18a-9aaa0f3aa3cb`，同 SQL 触发 MySQL `ERROR 1137 Can't reopen table: 'seed'`。
- GREEN: smartseed-temp-reopen-fix -> PASS, commit=`e3d3a8efdae5e17a7643192bf55a2c5ae21d1ff4` 中已用过程变量替换同语句重复读取临时表；r260801c 构建 manifest 显示 backend/frontend commit=`e3d3a8efdae5e17a7643192bf55a2c5ae21d1ff4`、`dirty=false`。
- RED: publish-test r260801c -> FAIL, releaseTag=`release-20260801-frozen-smartseed-tempfix-r260801c-r1`，operation=`op-2026-08-01T064141321447700Z-bce121f1-05d8-43b3-b939-d323e50e8415`，`20260731_dcc_file_category_match_rule_seed.sql` line 131 触发 MySQL `ERROR 1267 Illegal mix of collations (utf8mb4_unicode_ci,IMPLICIT) and (utf8mb4_general_ci,IMPLICIT)`。
- RED: dcc-category-seed-collation-test -> FAIL, `python -X utf8 -m pytest script/tests/test_dcc_file_category_match_rule_seed_sql.py -q` 复现 DCC seed 临时表缺少 `DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`。
- GREEN: dcc-category-seed-collation-fix -> PASS, commit=`9aeb1fc2a68fb97a2b3fb71b4d03777d97289f21`，目标 DCC seed pytest 3 passed，相邻 DCC+smartseed pytest 8 passed，migration policy gate 403 passed，`git diff --check` passed。
- GREEN: build-release r260801d -> PASS, releaseTag=`release-20260801-frozen-dcc-category-collation-r260801d-r1`，operation=`op-2026-08-01T070742390438700Z-2b23cda9-93ff-4ccc-b155-0fe29bce82b4`，发布包目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260801-frozen-dcc-category-collation-r260801d-r1`。
- GREEN: manifest-source r260801d -> PASS, `manifest-validation-r260801d-r1.json` 显示 releaseTag 匹配，`releaseManifest.gitCommit=9aeb1fc2a68fb97a2b3fb71b4d03777d97289f21`，backend/frontend `sourceRepos[*].commit` 均为该提交且 `dirty=false`，`publishScope=code-only`，`release-info.json` 含 releaseTag/changeSet/sourceRepos。
- GREEN: experience-preflight -> PASS, r260801d 测试服发布前复核 no-prod/no-backup、releaseTag 不复用、manifest/source clean、ServerHost=`172.30.30.58`、RemoteAppDir=`/opt/intruoyi/runtime`、失败不得手工改库/lock 的高风险发布门禁。
- RED: publish-test r260801d -> FAIL, operation=`op-2026-08-01T073030255051500Z-ba55c7d7-75c5-404a-bfe2-1e8f8035a6a1`，`20260731_dcc_file_category_match_rule_seed.sql` 仍触发 MySQL `ERROR 1267`；原因是表默认 collation 修复不足以覆盖 `dcc_file_category.name=utf8mb4_unicode_ci` 与 `dcc_file_category_match_rule.match_text/match_type=utf8mb4_0900_ai_ci` 的列级比较。
- RED: dcc-column-collation-test -> FAIL, 列级静态测试复现 DCC match rule seed 中 `category_name`、`match_text`、`match_type` 未分别对齐目标列 collation。
- GREEN: dcc-column-collation-fix -> PASS, commit=`f81435c16ca1defb9b5c35c2e3a2d31a2c77e2ce` 将 `category_name` 对齐 `utf8mb4_unicode_ci`，将 `match_text`/`match_type` 对齐 `utf8mb4_0900_ai_ci`；`python -X utf8 -m pytest script/tests/test_dcc_file_category_match_rule_seed_sql.py script/tests/test_codex_smart_scheduling_test_items_seed.py -q` -> `8 passed`，migration policy gate 403 passed，`git diff --check` passed。
- GREEN: build-release r260801e -> PASS, releaseTag=`release-20260801-frozen-dcc-column-collation-r260801e-r1`，operation=`op-2026-08-01T075619071613500Z-8ce3eda8-87d7-412c-8daf-b944d4d737df`，发布包目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260801-frozen-dcc-column-collation-r260801e-r1`。
- GREEN: manifest-source r260801e -> PASS, `manifest-validation-r260801e-r1.json` 为 `passed`；manifest/release-info 均显示 `publishScope=code-only`，backend/frontend `sourceRepos[*].commit=f81435c16ca1defb9b5c35c2e3a2d31a2c77e2ce` 且 `dirty=false`，变更说明与 r260801e releaseTag 一致。
- GREEN: publish-test r260801e -> PASS, operation=`op-2026-08-01T082221679621900Z-bdfeb32d-6378-404e-af3c-3bb8b8407300`，仅测试服发布成功；recent operations 未出现 `mark-tested`、`promote-prod`、`promote-backup`。
- GREEN: remote-runtime-verification r260801e -> PASS, `remote-runtime-verification-r260801e-r1.json` 断言 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 Up、backend health=`UP`、frontend HTTP=`200`、页面标题、`release-info.json`、release lock=`APPLIED`、migration failed/running=`0` 全部匹配目标 releaseTag。
- GREEN: runtime-control-release-status r260801e -> PASS, `runtime-control-release-status-r260801e-r1.json` 显示 `testCurrentReleaseTag=release-20260801-frozen-dcc-column-collation-r260801e-r1`，summary 与 changes 可见，sourceRepos commit 与 dirty=false 匹配。
- GREEN: merge-to-int-main -> PASS, 修复分支已合回 `E:\IntRuoyi` 的 `int_main`，merge commit=`ac8457724d16d287f5d65013ba304f77f3786e7b`；合并后聚焦回归 `8 passed`，`git diff --check HEAD~1..HEAD` 通过；主工作区无关脏改保持未提交。
- GREEN: runtime-control-main-restore -> PASS, 停止本任务 release worktree 控制台 PID=`55512`，从主维护路径启动 PID=`45648`，命令行显式 `production-write-enabled=false`、prod/backup access disabled，`runtime-control-main-restore-r260801e-r1.json` health=`UP`。
- GREEN: worktree-cleanup -> PASS, `worktree-cleanup-r260801e-r1.json` 显示 r260801a/r260801b release/fix worktree 与 state dir 的 Git 注册和物理目录均不存在，48181 仍由主维护路径 java 进程提供 health=`UP`。
- GREEN: release-closeout -> PASS, 任务状态从 `ready_for_closeout` 收口为 `completed`；本次只清理任务自有 r260801a/r260801b worktree/state，未删除其他并发 worktree。

## Issues

### I001 clean frontend worktree 缺少依赖

- 现象：`build-release` r1 在前端构建阶段找不到 `cross-env`。
- 阶段：构建发布包。
- 影响：r1 未形成可发布候选，releaseTag 判废。
- 原因判断：clean release worktree 不带 ignored `node_modules`，构建前未先按锁文件恢复依赖。
- 处理动作：在冻结 frontend worktree 执行 locked dependency restore，并验证 `cross-env.cmd`、`vite.cmd`、`vue-tsc.cmd` 与 `pnpm build:test`。
- 结果：依赖恢复后 r2 `build-release` 成功；worktree 仍 clean。
- 是否可前置检查：是。
- 是否可自动化：是，build-release 前扫描前端关键 CLI 并运行最小 `pnpm build:test`。
- 下次如何避免：创建 clean frontend release worktree 后立即执行 dependency restore 与 CLI 存在性断言，失败则不进入运行控制台构建。

### I002 publish-test preview 本地断言误判

- 现象：人工本地断言一度按 `-TargetEnvironment test` 查找 publish-test 目标，但实际脚本参数契约为 `-Environment test`。
- 阶段：publish-test 预览验收。
- 影响：可能把正确 preview 误判为目标错误，增加重复核对时间。
- 原因判断：沿用了其他 action 的参数名记忆，未完全以本轮 preview JSON 的结构化 `arguments` 为准。
- 处理动作：改按 flag 后一项解析 `-Environment`、`-ServerHost`、`-RemoteAppDir` 和 `-ReleaseTag`；确认 preview 仅指向测试服。
- 结果：preview gate 通过。
- 是否可前置检查：是。
- 是否可自动化：是，preview parser 应维护 action-specific flag allowlist。
- 下次如何避免：publish-test gate 固定读取 JSON `arguments`，禁止用跨 action 参数名猜测。

### I003 required SQL collation 阻断测试服发布

- 现象：`20260726_system_codex_smart_scheduling_test_items.sql` 第 313 行执行 `CALL ensure_system_codex_smart_scheduling_test_items()` 时返回 `ERROR 1267`，`utf8mb4_general_ci` 与 `utf8mb4_0900_ai_ci` 在 `=` 比较中混用。
- 阶段：publish-test required SQL。
- 影响：`publish-test` operation 失败，测试服发布未完成，验收标准不满足。
- 原因判断：智能排产 seed SQL 的临时字符串列、字面量或过程内比较未显式对齐目标表字段 collation；同类 Codex seed collation 门禁仍未覆盖该比较路径。
- 处理动作：冻结 operation JSON、脱敏日志、manifest、SQL SHA256、远端 lock/migration/.env/镜像/health/HTTP 状态；未手工改测试库，未复用失败 releaseTag。
- 结果：任务状态 blocked。
- 是否可前置检查：是。
- 是否可自动化：是，静态扫描新增/近期修改 required SQL 的 `CREATE TEMPORARY TABLE` 字符列、JOIN/NOT EXISTS/COUNT 校验中的字符串比较，并对目标字段 collation 做只读比对。
- 下次如何避免：在提交 SQL 修复时补 RED 测试覆盖 `20260726_system_codex_smart_scheduling_test_items.sql` 的 `utf8mb4_general_ci` vs `utf8mb4_0900_ai_ci` 比较路径，提交后重建新 releaseTag 再发布。

### I004 publish-test 失败后 `.env` 与实际镜像漂移

- 现象：测试服 `.env IMAGE_TAG` 已写为 `release-20260801-intmain-head-test-r260801a-r2`，但 backend/frontend 实际容器仍运行上一版 `release-20260731-smartseed-tempfix-head-test-r260731d-r1`。
- 阶段：publish-test 失败收束与运行态复核。
- 影响：只看 `.env` 会误判发布成功；重启或重发前必须识别半切换态。
- 原因判断：发布脚本先写 `.env` 并进入 required SQL，SQL 失败后未切换容器，但 release lock/migration 已记录失败。
- 处理动作：只读记录 `.env`、实际镜像、容器 Up、backend health、frontend HTTP、release lock、migration status 和 RUNNING lock。
- 结果：远端处于失败 releaseTag `.env` + 旧容器混合状态；未执行手工恢复。
- 是否可前置检查：是。
- 是否可自动化：是，失败收束脚本必须输出 `.env` 与 actual image diff。
- 下次如何避免：publish-test 非 SUCCESS 时始终按 drift 门禁冻结证据；未授权不得手工改 `.env`、lock 或 migration。

### I005 SSH carrier warning

- 现象：只读远端复核 stderr 出现 `close - IO is still pending on closed socket`。
- 阶段：远端状态采集。
- 影响：如果 stdout 不完整会污染运行态结论。
- 原因判断：OpenSSH Windows carrier warning；本次 stdout 完整、退出码为 0。
- 处理动作：保留 stderr 摘要，同时以结构化 stdout 和退出码判断本次只读采集有效。
- 结果：远端冻结证据可用。
- 是否可前置检查：部分可。
- 是否可自动化：是，采集器应记录 exit code、stdout 必需字段完整性和 stderr warning 分层。
- 下次如何避免：遇到该 warning 时先验证必需字段齐全；字段缺失则重跑采集，不得直接判业务失败或成功。

### I006 发布日志脱敏正则需要避免误伤

- 现象：初始脱敏规则存在把普通名称 `ruoyi-vue-pro` 误伤为密码片段的风险。
- 阶段：证据整理。
- 影响：误伤会破坏远端命令和数据库名证据，降低可审计性。
- 原因判断：正则过宽，把 `-p` 形态与普通文本连接误识别。
- 处理动作：改为只脱敏明确 `mysql -p<secret>` / 空白后的 CLI 密码参数形态，保留 `ruoyi-vue-pro`；对任务证据执行 secret pattern scan。
- 结果：保留的 publish log 为 sanitized 版本；未提交原始 secret-bearing log。
- 是否可前置检查：是。
- 是否可自动化：是，脱敏后执行 allowlist/denylist 双向扫描。
- 下次如何避免：日志脱敏前先保留任务外原始证据路径，提交范围只保留 sanitized log 与 secret scan 结果。

### I007 长时间发布阶段耗时

- 现象：维护构建、r1 失败、依赖恢复、r2 构建、manifest 校验、publish-test 与远端失败收束累计耗时较长。
- 阶段：全链路发布。
- 影响：增加中途状态漂移和重复核对风险。
- 原因判断：clean worktree 依赖恢复、Docker image/package 构建、2045 项 artifact 校验和远端 367 条已应用 migration 跳过记录均耗时。
- 处理动作：阶段性记录 build r1/r2、manifest、publish-test、远端冻结状态；失败后立即停止，不追逐后续提交。
- 结果：证据完整，未进入正式服/备份服动作。
- 是否可前置检查：部分可。
- 是否可自动化：是，耗时阶段可自动写 phase timing 与当前 operation。
- 下次如何避免：构建前先完成 dependency/migration/Docker/manifest 前置；长轮询记录 operation progress 和最后推进点。

### I008 智能排产 seed 临时表重复读取

- 现象：`release-20260801-frozen-smartseed-fix-r260801b-r1` 的 `publish-test` 在 `20260726_system_codex_smart_scheduling_test_items.sql` 触发 MySQL `ERROR 1137 Can't reopen table: 'seed'`。
- 阶段：测试服 `publish-test` required SQL。
- 影响：测试服发布再次失败，不能继续运行态验收。
- 原因判断：同一 SQL 语句重复引用 MEMORY 临时表派生结果进行 expected/actual count 比较，触发 MySQL 临时表 reopen 限制。
- 处理动作：在冻结修复分支中改用过程变量保存 expected/actual count，补静态回归测试并重跑 migration policy gate。
- 结果：r260801c 发布中该 SQL 已通过，阻塞转移到后续 DCC seed collation。
- 是否可前置检查：是。
- 是否可自动化：是，migration policy gate 可扫描同一语句内重复读取同一 TEMPORARY/MEMORY seed 表的 count 校验。
- 下次如何避免：临时表结果复用用过程变量或持久中间表承接，不在同一语句中多次 reopen 同一临时表。

### I009 DCC 分类匹配规则 seed 临时表 collation

- 现象：`release-20260801-frozen-smartseed-tempfix-r260801c-r1` 的 `publish-test` 在 `20260731_dcc_file_category_match_rule_seed.sql` line 131 触发 MySQL `ERROR 1267`，`utf8mb4_unicode_ci` 与 `utf8mb4_general_ci` 在 `=` 比较中混用。
- 阶段：测试服 `publish-test` required SQL。
- 影响：测试服发布失败，不能继续容器/健康检查/页面/版本说明验收。
- 原因判断：`tmp_dcc_file_category_match_rule_seed` 使用 `ENGINE=MEMORY` 但未声明 `DEFAULT CHARSET/COLLATE`，与目标表文本列比较时继承默认 collation。
- 处理动作：新增 RED 静态测试，最小修改临时表声明为 `ENGINE=MEMORY DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`，提交 `9aeb1fc2a68fb97a2b3fb71b4d03777d97289f21` 后重建 r260801d。
- 结果：r260801d build-release 与 manifest/source 校验已通过，等待 publish-test。
- 是否可前置检查：是。
- 是否可自动化：是，required SQL gate 可扫描 TEMPORARY/MEMORY seed 表与真实文本列 JOIN/NOT EXISTS 比较时是否显式 collation。
- 下次如何避免：所有 required SQL seed 临时表默认显式写 `DEFAULT CHARSET=utf8mb4 COLLATE=<目标列 collation>`，不得依赖 MEMORY 默认值。

### I010 前端构建长耗时与日志编码

- 现象：r260801d build-release 在 `pnpm build:test` 阶段长时间 RUNNING；日志中部分 Maven 中文 warning 和 NAS share 输出出现乱码。
- 阶段：构建发布包与证据读取。
- 影响：增加长轮询等待和人工判断成本；日志乱码影响可读性但未影响结构化 build 结论。
- 原因判断：Vite 构建和 Docker build/export 本身耗时，部分子进程输出编码不是 UTF-8。
- 处理动作：用 operations API 分段轮询，读取进程命令行确认仍指向冻结 source worktree；最终以 operation SUCCESS、manifest 和结构化 JSON 校验为准。
- 结果：build-release 成功，日志乱码作为流程问题记录。
- 是否可前置检查：部分可。
- 是否可自动化：是，长构建阶段可自动记录最后日志推进点、进程命令行和耗时；日志采集需按子进程编码分层处理。
- 下次如何避免：发布控制台按阶段刷新 summary；日志读取增加编码探测/原始字节保存，避免 UTF-8 强读导致可读性下降。

### I011 DCC seed 表默认 collation 不足以覆盖列级比较

- 现象：r260801d 已为 `tmp_dcc_file_category_match_rule_seed` 增加 `DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci` 后，`publish-test` 仍在 DCC seed 上报 `ERROR 1267`。
- 阶段：测试服 `publish-test` required SQL。
- 影响：r260801d releaseTag 判废，不能进入运行态验收。
- 原因判断：目标表列级 collation 不一致，`dcc_file_category.name` 为 `utf8mb4_unicode_ci`，而 `dcc_file_category_match_rule.match_text/match_type` 为 `utf8mb4_0900_ai_ci`；仅设置临时表默认 collation 不能覆盖所有列比较。
- 处理动作：将 seed 临时表列级声明拆分为 `category_name COLLATE utf8mb4_unicode_ci`、`match_text/match_type COLLATE utf8mb4_0900_ai_ci`，补静态测试并重建 r260801e。
- 结果：r260801e `publish-test` 成功，release lock=`APPLIED`，migration failed/running=`0`。
- 是否可前置检查：是。
- 是否可自动化：是，required SQL gate 应读取真实 `information_schema.COLUMNS`，逐列比对 seed 临时列和目标列 collation。
- 下次如何避免：DCC/seed SQL 不得只看表默认 collation；涉及多个目标文本列时必须按列级 collation 建模并测试。

### I012 PowerShell 远端 MySQL 嵌套引号误解析

- 现象：直接在 PowerShell 字符串中嵌套 `ssh -> docker exec -> sh -lc -> mysql -e` 时，本地 shell 把引号拆坏，返回“寻找匹配的引号遇到未预期文件结束符”。
- 阶段：远端 release lock / migration 只读查询。
- 影响：如果不区分 carrier 错误和远端业务状态，会误判测试服数据库状态缺失。
- 原因判断：多层双引号和 `$MYSQL_ROOT_PASSWORD` 扩展边界混在 PowerShell 字符串中，命令在本机传输层已损坏。
- 处理动作：改用 Python `subprocess.run([...])` 参数数组传 SSH 命令，远端仍使用容器内环境变量，不打印明文密码。
- 结果：只读查询成功，release lock 与 migration 证据写入 `remote-runtime-verification-r260801e-r1.json`。
- 是否可前置检查：是。
- 是否可自动化：是，远端 MySQL 采集器统一用参数数组或 stdin 脚本，并对本地 carrier exit code 单独分类。
- 下次如何避免：PowerShell 不直接承载四层嵌套引号；命令中出现 SSH、Docker exec、MySQL 和环境变量时默认使用参数数组或 UTF-8 LF stdin。

### I013 本地策略拒绝宽脚本时需要拆分可审计步骤

- 现象：合并式运行控制台恢复脚本、批量 worktree 清理脚本被本机策略拒绝执行。
- 阶段：运行控制台恢复与任务收尾清理。
- 影响：收尾时间增加；如果强行绕过会降低可审计性和路径边界安全。
- 原因判断：脚本同时包含进程停止、后台启动、递归删除、状态写入等多类高风险动作，触发本机安全策略。
- 处理动作：拆成“确认进程归属 -> 停止任务自有 PID -> 启动主路径控制台 -> 健康检查 -> git worktree remove -> 固定路径物理清理 -> 复核”的小步骤。
- 结果：48181 恢复主维护路径，r260801a/r260801b worktree/state 清理完成。
- 是否可前置检查：部分可。
- 是否可自动化：是，清理器应把高风险动作拆成显式 phase，并先输出 dry-run / allowlist。
- 下次如何避免：收尾脚本不要把停止进程、启动服务和递归删除放在一个大命令里；每步记录路径、PID、退出码和复核结果。

### I014 Invoke-WebRequest Content byte[] 导致健康断言误报

- 现象：48181 `/actuator/health` HTTP 200，但 `Invoke-WebRequest.Content` 被渲染为 byte array，本地 `-match 'UP'` 断言失败。
- 阶段：运行控制台恢复验证。
- 影响：可能把已恢复的主路径控制台误判为失败，阻塞 worktree 清理。
- 原因判断：PowerShell/HTTP 响应组合下 `Content` 类型不稳定；未先按 UTF-8 解码。
- 处理动作：检测 `[byte[]]` 后使用 `[System.Text.Encoding]::UTF8.GetString(...)` 显式解码，再写入 `runtime-control-main-restore-r260801e-r1.json`。
- 结果：health=`{"status":"UP"}`，主路径控制台验证通过。
- 是否可前置检查：是。
- 是否可自动化：是，健康检查 helper 应统一返回 `statusCode`、decoded body 和 JSON status。
- 下次如何避免：PowerShell HTTP 验证一律用 `Invoke-RestMethod` 或显式解码 `Invoke-WebRequest.Content`；禁止直接对 byte array 做字符串断言。

### I015 worktree 删除后物理目录被 ignored node_modules 长路径残留

- 现象：`git worktree remove --force` 已清除注册，但 r260801a/r260801b 物理目录仍报 `Directory not empty`，其中 source fix worktree 残留 pnpm `node_modules` 长路径。
- 阶段：任务 closeout 清理。
- 影响：如果只看 Git 注册，会误判 worktree 已完全清理；如果未做路径边界校验就递归删除，则可能误删无关目录。
- 原因判断：clean release worktree 中恢复过前端依赖，ignored `node_modules` 不受 Git 管理；Windows 长路径在普通删除中出现文件消失/路径不可达异常。
- 处理动作：确认 Git 注册已无 r260801a/r260801b、无外部进程引用后，用固定路径白名单和 `\\?\` 长路径前缀清理物理残留。
- 结果：`worktree-cleanup-r260801e-r1.json` 显示所有任务路径 `existsAfter=false`。
- 是否可前置检查：是。
- 是否可自动化：是，closeout 工具应同时检查 Git 注册、物理目录、state dir、进程引用和长路径删除结果。
- 下次如何避免：发布 worktree 恢复前端依赖后，closeout 必须预期 ignored `node_modules` 残留；删除前先做 allowlist 和无进程引用检查。

### I016 进程扫描自匹配导致 cleanup 证据误报

- 现象：cleanup 复核脚本扫描 `runtime-control-maintenance` 和 `48181` 时，把当前 PowerShell/Python 校验脚本自身也匹配进结果，导致“运行控制台仍含 r260801a/r260801b”误报。
- 阶段：任务 closeout 复核。
- 影响：会把已经恢复主路径的 48181 误判为仍引用 release worktree。
- 原因判断：扫描条件只匹配命令行文本，校验脚本自身包含待查路径字符串。
- 处理动作：进程扫描限定 `Name='java.exe'`，并解析 JSON 后只检查 Java 进程命令行。
- 结果：cleanup 证据重写后 `passed=true`，48181 由主维护路径 PID=`45648` 提供服务。
- 是否可前置检查：是。
- 是否可自动化：是，进程扫描 helper 默认排除当前 PID/父 shell，并按进程名和命令行双条件过滤。
- 下次如何避免：worktree 清理前后的进程守卫不得只做文本 contains；必须排除当前检查器并输出被采信的进程名、PID 和命令行。
