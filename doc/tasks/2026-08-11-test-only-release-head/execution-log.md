# Execution Log

## BDD Scenarios

- BDD: only-test-release-from-frozen-head -> Given 当前分支存在最新已提交 HEAD 且工作区可能存在未提交改动；When 创建干净临时发布 worktree 并从该 HEAD 构建测试发布包；Then 发布包、manifest、版本号、变更说明和运行控制台必须指向该 HEAD，未提交改动不得进入产物。
- BDD: test-server-only-publish -> Given 用户明确要求仅发布测试服务器；When 执行发布流程；Then 只允许执行 build-release -> publish-test 及测试服真实运行态验证，禁止执行 mark-tested、promote-prod 和 promote-backup。
- BDD: runtime-verification-gate -> Given 测试服发布脚本返回成功；When 执行运行态验收；Then 必须同时确认镜像 tag、容器状态、健康检查、前端 HTTP 状态、前端页面、运行控制台版本号和变更说明后，才可判定成功。

## Command Intent Log

- 2026-08-11：创建任务目录与任务记录，记录仅测试服 HEAD 发布目标和验收门禁。
- 2026-08-12：继续使用本任务目录；读取 CI/CD 技能、经验索引、测试服发布、构建、PowerShell、worktree、发布备份、服务器访问与登录文档，准备冻结当前 HEAD 并创建专用 release worktree。

## Evidence

- GREEN: experience-preflight -> PASS, 已读取并摘取 `docs/experience-index.md` 命中的测试服发布、构建 manifest、PowerShell/SSH、worktree、发布备份、服务器访问和登录验证门禁；后续高风险发布动作必须按这些门禁 fail fast。
- GREEN: source-freeze -> PASS, releaseId=`r260812a`; maint HEAD=`3d980bb16a300020985f90d3b118fef45786336a`, worktree=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260812a\m`, status=`## HEAD (no branch)`; app HEAD=`5d503ea5e5d754461031ddb4271e5db77c2c4d91`, worktree=`D:\IntRuoyiWorktree\r260812a-release-app`, status=`## HEAD (no branch)`; stateDir=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260812a-state\runtime-control`。
- GREEN: release-prerequisites -> PASS，Java 21.0.10、Maven 3.9.9、Node 24.12.0、pnpm 10.22.0、Docker client/server 29.2.1、SSH/Git/Python 均可用；48181/48182/48183 无 listener；两个 release worktree dirtyCount=0。
- GREEN: test-server-baseline-readonly -> PASS，发布前测试服 `.env IMAGE_TAG=release-20260811-intmain-head-test-r260811a-r2`；backend/frontend 容器 running，backend health=`UP`，frontend HTTP=`200`；只读 SSH 退出码 0，未写远端。
- BLOCKER: migration-policy-gate -> `python -X utf8 ops/release/run-release-migration-policy-gate.py --sql-root D:\IntRuoyiWorktree\r260812a-release-app\IntRuoyiBackend\sql\mysql --output ...\migration-policy-gate-r260812a.json` 返回 FAIL：`invalid type in ...\20260812_mes_pqc_dcc_qa_c00_backfill.sql: backfill`。
- GREEN: migration-blocker-root-cause -> PASS，`git show HEAD:IntRuoyiBackend/sql/mysql/20260812_mes_pqc_dcc_qa_c00_backfill.sql` 第一行确认 committed metadata 为 `type=backfill`；维护 HEAD 的 Python gate 与 `ops/deploy/publish-int-ruoyi.ps1` 正式 parser 仅允许 `schema/data/menu/config/permission/seed`。两仓 frozen committed contract 不一致。
- GREEN: blocker-containment -> PASS，migration gate 失败后停止本任务维护构建 session `69231` 与 app 前端依赖恢复 session `98168`；`Get-CimInstance Win32_Process` 未发现命令行引用 `r260812a` 的剩余任务进程，两个 worktree `git status --short --branch` 仍仅 `## HEAD (no branch)`。
- BLOCKER: build-release -> NOT STARTED，未生成 releaseTag/发布包/manifest/版本号/变更说明，按 fail-fast 门禁禁止继续。
- BLOCKER: publish-test -> NOT STARTED，未执行任何测试服写入；正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup` 均未执行。
- 2026-08-12 CONTINUATION: 中断后复核 maint/app worktree HEAD 仍分别为 `3d980bb16a300020985f90d3b118fef45786336a` / `5d503ea5e5d754461031ddb4271e5db77c2c4d91`，dirtyCount 均为 0，命令行引用 `r260812a` 的任务进程数为 0。
- BLOCKER: migration-policy-gate-rerun -> FAIL，重新执行同一冻结输入仍返回 `invalid type in ...20260812_mes_pqc_dcc_qa_c00_backfill.sql: backfill`；blocker 未被外部提交或现场变化解除。
- GREEN: project-experience-consolidation -> PASS，按技能查重后合并到既有 `docs/release-build-preflight-lessons.md`、`docs/test-release-preflight.md` 与 `docs/experience-index.md`，未新建长期经验文档；新增门禁要求主程序 SQL、维护仓 Python gate、维护仓 PowerShell parser 的 migration type 集合一致，并把快速 gate 排在耗时 install/build 之前。
- BDD: evidence-only migration contract -> Given 冻结 app HEAD 含 `preflight/backfill/postflight/rollback-dry-run` C00 evidence SQL；When migration policy gate 和 build-release 收集 SQL；Then policy gate 必须验证这些 metadata，正式 required SQL 包必须只包含 executable types，evidence-only SQL 不得自动执行。
- TDD PLAN: 先在维护修复 worktree 添加失败测试，证明 Python manifest 当前拒绝 evidence-only types 且 PowerShell required SQL 收集缺少显式排除；再最小实现共同类型集合与排除规则，运行目标回归、全量 migration gate、维护构建并提交。
- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q` -> FAIL（3 failed, 10 passed）；预期失败为 Python manifest 拒绝 `backfill`、PowerShell 缺少 evidence-only 排除契约；另发现一项既有静态断言未同步当前 `-PublishScope` 调用，已只同步测试到现有正式脚本契约。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q` -> PASS（13 passed）；Python gate 接受并保留 evidence-only metadata，PowerShell required SQL 收集显式排除 `preflight/backfill/postflight/rollback-dry-run`。
- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py::test_migration_policy_gate_rejects_executable_dependency_on_evidence_only_migration -q` -> FAIL（1 failed）；当前 gate 会放过 executable -> evidence-only 依赖，排除证据脚本后存在依赖闭包风险。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q` -> PASS（14 passed）；新增 executable dependency closure 门禁。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_showroom_release_sql_contract.py scripts\tests\test_release_package_slimming.py -q` -> PASS（22 passed）。
- GREEN: `PowerShell Language.Parser ParseFile(ops/deploy/publish-int-ruoyi.ps1)` -> PASS（parser errors=0）。
- GREEN: migration-policy-gate-after-contract-fix -> PASS，正确入口 `ops\release\run-release-migration-policy-gate.py` 扫描冻结 app SQL，status=passed、migrationCount=474；C00 schema 为 executable，preflight/backfill/postflight/rollback-dry-run 保留在审计 manifest 且不会进入 required SQL。
- ISSUE: migration-policy-gate-command-path -> 首次误用不存在的 `ops\release\run_release_migration_policy_gate.py`，退出码 1；经 `rg --files` 定位真实连字符入口后重跑 PASS。影响仅为重复命令耗时，无源码、产物或远端改变。
- GREEN: maintenance-dependency-policy -> PASS；frozen install 完成 70/70，耗时 16m45s；外部 `pnpm-only-built-dependencies-r260812a-fix.json` 通过 `npm_config_only_built_dependencies_file` 注入，`corepack pnpm@10.25.0 rebuild --pending` 后 `ignored-builds=None`、`.modules.yaml pendingBuilds=[]`，冻结 package.json/lockfile 无 diff。
- GREEN: maintenance-console-build -> PASS；最终 `scripts\build.ps1` 前端 vue-tsc、Vite 1419 modules build、Maven test/package 全部成功；tests=26、failures=0、errors=0、skipped=0。
- GREEN: maintenance-jar -> PASS；`backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` SHA256=`3eae95d8b68f802509a29d66e85e06b1dd54074d49b95b9686826a2b13341e58`，包含 `BOOT-INF/classes/static/index.html`。
- ISSUE: maintenance-install-duration -> pnpm store 链接阶段多次长时间无输出并停在 69/70；只读进程检查显示唯一子进程 Responding 且 CPU 增长，未并发启动第二次安装，最终正常完成。
- ISSUE: pnpm-ignored-builds-context -> 系统 pnpm/无外部 policy 上下文一度返回 `Cannot identify as no node_modules found`，但 node_modules、`.modules.yaml`、vite/vue-tsc/esbuild 均存在；固定 Corepack 10.25 与外部 policy 后得到可判定 `None`。
- ISSUE: runtime-test-cleanup-policy -> 递归和空目录删除被执行策略拒绝；用精确文件补丁删除 4 个测试 JSON，空目录 files=0 且不在 Git 状态，留待 closeout allowlist 清理。
- GREEN: maintenance-contract-fix-commit -> PASS；提交 `97723ac524487595ab5b145e31251d6bc1ec0091`（`任务: 修复发布迁移证据类型契约`）只含四个 allowlist 文件。
- GREEN: maintenance-int-main-integration -> PASS；`int_main` 仍位于原基线 `3d980bb`，目标四文件无并发改动，执行 `git merge --ff-only codex/r260812a-migration-evidence-types` 成功；合并后目标回归 22 passed、冻结 app SQL gate status=passed/migrationCount=474、fix commit is ancestor=true。
- GREEN: remediated-source-freeze-plan -> PASS；新 releaseId=`r260812b`，维护目标固定为 `97723ac`，主程序目标继续固定为原发布开始提交 `5d503ea`，不追逐其它后续提交。

## Issues

- 启动阶段：只读 bootstrap 超范围读取发布/服务器文档，已在 task.md Issue Log 记录，后续按任务文档建立后的门禁顺序继续。
- Git/source freeze：主工作区较脏且主程序 status 存在 `target_corrupt_m4_20260802_1327` 缺失目录 warning；影响是禁止主工作区直接构建；处理为创建本轮专用 detached release worktree 并复核 clean，后续仅从 worktree 构建。
- 构建前 migration gate：committed SQL `type=backfill` 不在 committed validator/publish script 允许枚举内；无法生成可信 manifest，任务已 fail fast，测试服未写入。
- 长耗时控制：migration gate 失败时两个依赖安装/维护构建 session 尚在运行；确认 blocker 后停止任务自有 session 并复核无残留进程，避免继续无价值耗时。
- 工具编排：启动阶段有引号转义失败、一次无效 wait 和数次无关只读状态查询；均未改变文件或环境，已纳入下次固定 bootstrap/等待模板改进。
- SSH carrier：测试服基线命令尾部出现 `IO is still pending on closed socket`，但退出码 0 且结构化运行态字段完整；保留 warning，不降级验证。
- 契约闭包：单纯接受 evidence-only 类型不足以保证 required SQL 可执行闭包；已用 RED/GREEN 增加 executable 不得依赖 evidence-only 的 fail-fast 门禁。
- 命令路径：复验时误写策略门禁入口名；已记录并改为执行前用 `rg --files`/`--help` 确认真实脚本契约。
- 依赖耗时与状态：pnpm install 需以真实子进程退出为准；ignored-builds 必须固定项目 Corepack 版本并携带明确外部 policy，不能混用系统 pnpm 的不一致输出。

- ISSUE: tool-wait-misroute-resumed -> 现象：连续多轮恢复时工具调用被误路由到不存在的 wait cell；阶段：发布恢复/命令编排；影响：未执行 build-release/publish-test，避免无证据发布；原因判断：工具选择误触而非项目脚本失败；处理动作：本轮改用 exec/exec_command 单通道复核状态；结果：未产生远端写入，待继续；是否可前置检查：是；是否可自动化：部分；下次如何避免：发布恢复阶段先跑最小 EXEC_OK，再合并实际检查命令，禁止 wait 非真实 cell。
- GREEN: r260812b-resume-precheck -> PASS，已复核 r260812b worktree、隔离配置、依赖、维护 jar 和端口状态；详见本轮 structured precheck 输出。

- ISSUE: r260812b-nas-config-missing -> 现象：build-release preview fail fast，msg=releasePackage.nasUsername is required；阶段：build preview；影响：未提交 build operation、未写测试服；原因判断：隔离 worktree local config 使用模板，缺本机发布包 NAS 配置；处理动作：从主维护工作区既有 local 配置复制 release-package 配置块到 r260812b 隔离配置，未输出明文凭据，并重启任务自有控制台；结果：控制台 health=UP，等待重试 build preview；是否可前置检查：是；是否可自动化：是；下次如何避免：新 release worktree 创建后先校验 release-package 必填项。
- GREEN: r260812b-runtime-restart-after-config -> PASS，复制 release-package 配置后重启控制台，PID=45812，health=UP。

- ISSUE: r260812b-r1-nas-package-exists -> 现象：build-release r1 失败，日志显示 NAS release package already exists: Backup/ReleasePackage/release-20260813-intmain-head-test-r260812b-r1；阶段：build-release 上传发布包；影响：r1 未生成可信可发布闭环，禁止继续 publish-test；原因判断：同名 releaseTag 包目录已存在，脚本按不可覆盖策略 fail fast；处理动作：不复用失败 r1，不删除 NAS 既有目录；固定同一 r260812b clean worktree 与同一 HEAD，切换新 releaseTag r2 重新 build-release；结果：driver 已切换 r2，等待提交 build；是否可前置检查：是；是否可自动化：是；下次如何避免：build preview 前检查 NAS releaseTag 目录是否已存在，若存在先选择新 tag。
- GREEN: r260812b-r2-source-still-clean -> PASS，维护 HEAD=97723ac524487595ab5b145e31251d6bc1ec0091，主程序 HEAD=5d503ea5e5d754461031ddb4271e5db77c2c4d91，两个 release worktree status 均为 detached clean；r2 仍基于同一冻结源码。

- ISSUE: r260812b-runtime-console-nas-config -> 现象：运行控制台页面的 release-status 已成功，但 rollback/restore candidates 因 backupOps.nasUsername 缺失失败，Promise.all 导致版本栏显示测试服未上报；阶段：发布后页面验收；影响：运行控制台版本号和变更说明无法验收，禁止判定发布完成；原因判断：隔离 worktree local config 此前只复制了 release-package 配置块，未复制 backup-ops；处理动作：从主维护工作区既有 local 配置复制 backup-ops 与 release-package 配置块，未输出明文凭据，并重启任务自有控制台；结果：控制台 health=UP，等待页面复验；是否可前置检查：是；是否可自动化：是；下次如何避免：新 release worktree 创建后一次校验并复制两个 NAS 配置块。
- GREEN: r260812b-runtime-restart-after-config -> PASS，复制 backup-ops/release-package 配置后重启控制台，PID=9308，health=UP。

## r260812b Build And Test Publish

- GREEN: r260812b-release-worktrees -> PASS，构建与发布结束后维护 worktree=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260812b\m` HEAD=`97723ac524487595ab5b145e31251d6bc1ec0091`、主程序 worktree=`D:\IntRuoyiWorktree\r260812b-release-app` HEAD=`5d503ea5e5d754461031ddb4271e5db77c2c4d91`，两者 `git status --short --branch` 均仅 `## HEAD (no branch)`；未产生新提交，无需再合回 `int_main`。
- GREEN: build-release-r260812b-r2 -> PASS，releaseTag=`release-20260813-intmain-head-test-r260812b-r2`，operation=`op-2026-08-12T190406618402500Z-3771efa2-38a7-4bf1-be8e-3e0f1f237bde`，status=`SUCCESS`；发布包目录=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260813-intmain-head-test-r260812b-r2`。
- GREEN: manifest-version-changes -> PASS，`manifest-validation-r260812b-r2.json` 校验 484 个 artifact 的 size/SHA256，两个 sourceRepos 均 commit=`5d503ea5e5d754461031ddb4271e5db77c2c4d91`、dirty=false；manifest 与前端镜像 `/usr/share/nginx/html/release-info.json` 的 releaseTag/packageId/changeSet 一致。
- ISSUE: dcc-upload-slot-duplicates -> 现象：首次 publish-test operation=`op-2026-08-12T192401960046800Z-713bf571-0891-49f3-aba7-d5e6d99f107e` 在 `20260811_dcc_upload_slot_idempotency.sql` 失败，报 `DCC_UPLOAD_SLOT_DUPLICATES_REQUIRE_MANUAL_REMEDIATION`；阶段：required SQL；影响：release lock=`FAILED`，migration APPLIED=3/FAILED=1/SKIPPED=423，容器未切换，本轮禁止判定成功；原因判断：测试服同一 tenant/uploader/session/purpose 有两条未绑定 AVAILABLE 且 cleanup_status=ACTIVE 的历史临时文件记录；处理动作：冻结两行完整 TSV、生成精确 rollback inserts，经用户明确授权后用事务和全字段 WHERE 仅将 id=51 标记 CLEANED、保留 id=50 ACTIVE；结果：affectedRows=1、重复组=0，后续同一冻结包重试成功；是否可前置检查：是；是否可自动化：检查可自动化、修复不可自动化；下次如何避免：publish-test preview 后、远端写入前按迁移同口径查询活跃槽重复，发现即 fail fast 并人工判定保留项。
- GREEN: authorized-data-remediation -> PASS，`20260813-r260812b-dcc-upload-slot-backup-summary.json`、rollback inserts、remediation SQL/result/summary 均已保存；未删除行、未改绑定记录，回滚材料可恢复原始两行状态。
- ISSUE: publish-log-redaction-helper -> 现象：重试轮询取日志时报 regex `missing ), unterminated subpattern`；阶段：operation 监控；影响：operation 本身持续运行，但脱敏日志一度不可读；原因判断：前次凭据清洗误改了辅助脚本 `MYSQL_PWD` 正则；处理动作：用精确补丁恢复 `(?i)(MYSQL_PWD=)[^\s'\"]+`，重新生成脱敏日志；结果：日志可读且无密码输出；是否可前置检查：是；是否可自动化：是；下次如何避免：发布前对日志脱敏函数做编译/样例测试，清洗只处理输出文件不修改脚本源码。
- ISSUE: publish-test-duration -> 现象：重试 operation 长时间保持 RUNNING 且 summary 仅为“命令已提交到本机执行队列”；阶段：required SQL 传输/迁移登记；影响：发布耗时增加且易误以为卡死；原因判断：430 个远端 required migration 文件逐项 SCP，再逐项写入 APPLIED/SKIPPED 状态；处理动作：保持唯一 operation id，按脱敏日志的文件日期、日志长度和更新时间判断持续推进，未重复提交；结果：约 23 分钟后 SUCCESS；是否可前置检查：是；是否可自动化：是；下次如何避免：运行控制台显示当前文件/计数进度，轮询同时记录日志 lastWriteTime。
- GREEN: publish-test-r260812b-r2 -> PASS，operation=`op-2026-08-13T001732036464300Z-1541e376-2561-40b8-82c8-77c33bcfda17`，environment=`test`、action=`publish-test`、status=`SUCCESS`；未执行 `mark-tested`、`promote-prod`、`promote-backup`，未操作正式服和备份服。
- ISSUE: postcheck-probe-contract -> 现象：独立探针首次将不存在的 `dcc_upload_slot` 当成表名，并把未定义 Docker healthcheck 的 backend health=`none` 判失败；阶段：发布后验收；影响：产生一次假阴性，未影响服务器；原因判断：探针未按真实 migration 表和 compose 健康契约编写；处理动作：以冻结 SQL 和 compose 为准，改查 `dcc_controlled_file_temporary_file`，容器门禁为 state=running，健康门禁独立使用 Actuator UP；结果：重跑全绿；是否可前置检查：是；是否可自动化：是；下次如何避免：验收 SQL 前先 `rg`/DESCRIBE，Docker healthcheck 未定义时不得臆造 healthy 状态。
- GREEN: remote-runtime-postcheck -> PASS，`.env IMAGE_TAG`、backend/frontend 实际镜像、两个容器 running、backend health HTTP 200/UP、frontend HTTP 200、release-info HTTP 200、source commit/dirty、release lock=APPLIED 全部匹配；migration total=430、APPLIED=4、SKIPPED_ALREADY_APPLIED=426、FAILED/RUNNING=0；活跃上传槽重复组=0。
- ISSUE: runtime-console-version-not-reported -> 现象：首次 Playwright 页面显示本次 SUCCESS operation，但版本栏为“测试服未上报”，并提示 `backupOps.nasUsername is required`；阶段：运行控制台页面验收；影响：版本号和变更说明不可见，按验收标准必须阻塞；原因判断：页面用单个 `Promise.all` 同时加载 release-status/rollback/restore，隔离配置此前只复制 release-package，rollback/restore 失败连带丢弃成功 release-status；处理动作：从主维护配置一次复制 backup-ops 与 release-package 两个块并重启任务控制台，凭据不输出；结果：六个 API 均 200，版本栏和对话框正确显示目标 releaseTag；是否可前置检查：是；是否可自动化：是；下次如何避免：启动 release worktree 控制台前校验两个 NAS 配置块，页面不得用候选接口失败吞掉 release-status 成功结果。
- GREEN: playwright-test-frontend -> PASS，真实浏览器打开 `http://172.30.30.58:8081/` 后进入 `/login?redirect=/user/profile`，标题=`瑛泰管理系统 - 登录`，租户/captcha 请求均 200，console errors=0；截图=`output/playwright/r260812b-test-frontend.png`。
- GREEN: playwright-runtime-console -> PASS，真实浏览器打开 `http://127.0.0.1:48181/`，标题=`运行控制台`，显示目标 releaseTag；点击“查看变更”后版本号=`release-20260813-intmain-head-test-r260812b-r2`，变更项包含发布包和组件范围，console errors=0，overview/operations/capacity/release-status/rollback/restore 均 200；截图=`output/playwright/r260812b-runtime-console-change-notes.png`。
- GREEN: release-verification-gate -> PASS，build operation、publish operation、manifest/source、测试服真实运行态、前端真实页面、运行控制台版本和变更说明全部通过；任务进入 `ready_for_closeout`，待执行本任务 worktree/state/控制台收尾后才能标记 completed。

## Closeout Evidence

- ISSUE: task-closeout-outside-workspace -> 现象：cleanup preview 正确保留三份核心记录，但把任务文档列出的外部 release worktree/state 判为 `Delete path is outside workspace`；阶段：closeout preview；影响：技能 apply 被保护性阻塞；原因判断：维护/app release worktree 位于主维护 Git workspace 之外；处理动作：不绕过技能保护，先用项目 worktree 规则手工做路径/Git/HEAD/clean/进程 allowlist 清理，再移除已完成候选列表并重跑技能；结果：外部清理通过；是否可前置检查：是；是否可自动化：是；下次如何避免：release task closeout 先处理外部 worktree，再运行 repo 内 task-closeout。
- ISSUE: main-runtime-restore-command-policy -> 现象：一次长复合 PowerShell 恢复命令被本机策略拒绝；阶段：运行控制台恢复；影响：未停止进程、未改文件，仅增加一次重试；原因判断：命令含进程终止、启动与多项验证，策略判定过宽；处理动作：改为 UTF-8 任务脚本并保留精确 PID/路径守卫；结果：任务 PID 9308 停止，主路径控制台启动；是否可前置检查：是；是否可自动化：是；下次如何避免：控制台恢复使用仓库内固定脚本，不拼接长 inline 命令。
- ISSUE: main-runtime-stale-jar-state -> 现象：首次恢复主维护路径后 health=UP，但旧 JAR/state 仅显示 `release-20260711-current-head-test-r4`；阶段：稳定控制台恢复；影响：若直接收尾，用户后续看不到本次版本说明；原因判断：主维护 target JAR 与 operation state 长期未刷新；处理动作：确认维护主 HEAD=`97723ac`，复制本次 clean worktree 已验证 JAR，并仅复制本次 4 个 operation JSON 到主 state，不覆盖历史；结果：主路径 PID=5600、health=UP、release-status=r2；是否可前置检查：是；是否可自动化：是；下次如何避免：删除 release worktree 前要求稳定控制台 health 和 testCurrentReleaseTag 同时匹配。
- ISSUE: maintenance-jar-hash-nondeterminism -> 现象：较早修复构建记录 hash=`3eae95...`，最终 r260812b 同 HEAD JAR hash=`A4899B...`；阶段：稳定控制台 JAR 刷新；影响：按旧 hash 门禁首次 fail fast，未覆盖主 JAR；原因判断：Spring Boot JAR重建包含非确定性时间/归档元数据，源码 commit 一致但字节 hash 不一致；处理动作：以本次实际 clean worktree JAR为来源，重新核 HEAD、JAR entry 和页面验收，固定本次真实 hash 后复制；结果：主 JAR hash=`A4899B...` 且页面复验通过；是否可前置检查：是；是否可自动化：部分；下次如何避免：记录每次实际构建 artifact hash，不跨重建复用旧 hash；如要求可复现构建需另设正式改进任务。
- ISSUE: playwright-npm-lock-contention -> 现象：稳定控制台首次并行 npx open/resize/snapshot 中一个子命令报 `ECOMPROMISED Lock compromised`；阶段：最终 Playwright 复验；影响：组合命令退出信息含 npm 锁错误，但浏览器会话和 snapshot 完整；原因判断：多个 npx 进程竞争同一 npm cache lock；处理动作：后续 click/find/console/close 改为顺序独立命令；结果：版本号、发布包、组件范围均找到，console errors=0，会话正常关闭；是否可前置检查：是；是否可自动化：是；下次如何避免：同一 Playwright session 的 npx 调用严格串行，不在单次并发编排中启动多个 npx。
- ISSUE: worktree-remove-directory-not-empty -> 现象：多个 `git worktree remove --force` 返回 `Directory not empty`；阶段：外部 worktree 清理；影响：Git 注册已注销但 ignored node_modules/构建残留仍占物理目录；原因判断：Git 不负责删除所有 ignored 构建产物；处理动作：再次读取 worktree registry，只有已注销、路径位于固定 allowlist、无非 PowerShell 进程引用时才 `Remove-Item -Recurse` 精确清理；结果：五个 worktree、两个 state 根和三个空父目录均不存在；是否可前置检查：是；是否可自动化：是；下次如何避免：closeout 脚本原生支持“注销后物理残留”分支并记录 existsAfter=false。
- GREEN: stable-runtime-final -> PASS，主维护路径 PID=5600，JAR hash=`A4899B4912C3714AF3142104D98CC7F4720B66ABDC5F5A216F61F1698C18D64E`，health=UP，testCurrentReleaseTag=r2，prod/backup access disabled；Playwright 版本对话框复验通过，console errors=0。
- GREEN: external-worktree-cleanup -> PASS，r260812a/r260812a-fix/r260812b 维护 worktree、r260812a/r260812b app worktree、r260812a/r260812b state roots 全部 Git 注册无残留且物理路径不存在；任务分支已在 `int_main` 祖先校验后删除；未触碰其它 worktree。
- GREEN: post-cleanup-remote-verification -> PASS，清理后远端 `.env`、实际镜像、容器、Actuator、frontend HTTP、release-info、lock、430 条 migration 和重复上传槽检查仍全部通过。
- GREEN: task-closeout-cleanup -> PASS，preview/apply 均无 blocked/warnings；已删除本任务辅助证据和两张临时 Playwright 截图，仅保留 `task.md`、`execution-log.md`、`verification-report.md`，任务状态标记为 `completed`。
- ISSUE: final-runtime-status-wrong-route -> 现象：最终本地复核首次请求 `/api/runtime/release-status` 返回 HTTP 404，而 health 仍为 UP；阶段：task-closeout 后最终复核；影响：产生一次校验假阴性，未改变控制台、发布包或服务器；原因判断：复核命令误用了不存在的简写路由；处理动作：从控制器和既有门禁定位真实 `/admin-api/infra/runtime-control/release-status`，以 60 秒超时重新请求；结果：API code=0、PID=5600、目标 r2 和两条变更说明均匹配，正式服/备份服启动参数保持禁用；是否可前置检查：是；是否可自动化：是；下次如何避免：最终检查命令从发布门禁复用固定端点，不凭记忆拼接路径。
