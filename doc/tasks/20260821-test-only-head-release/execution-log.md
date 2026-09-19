# Execution Log

## 2026-08-21 启动

- 用户请求：仅基于当前分支最新已提交代码构建并发布到测试服务器；未提交改动不得进入构建产物；成功后沉淀问题为前置经验。
- 授权记录：用户已回复“授权”“继续”，允许测试服发布与远端测试服运行态验证；未授权正式服、备份服、mark-tested、promote-prod、promote-backup。
- BDD: Only test release from frozen HEAD -> Given 当前系统仍在开发且工作区可能较脏, When 执行测试服发布, Then 构建必须来自本轮冻结 HEAD 的干净临时 worktree 且只执行 build-release/publish-test。
- BDD: Runtime verification gates release success -> Given publish-test 返回成功, When 验收测试服真实运行态, Then 必须同时验证 operation、manifest、.env、镜像 tag、容器、health、HTTP、页面、控制台版本与变更说明。
- GREEN: task-document-created -> PASS, 已创建 doc/tasks/20260821-test-only-head-release/task.md。
- P001: 现象=`New-Item -LiteralPath` 不被当前 PowerShell 接受；阶段=任务文档；影响=任务文档写入延迟但未执行构建/发布；原因判断=参数兼容问题；处理动作=改用 `New-Item -Path`；结果=成功；是否可前置检查=是；是否可自动化=是；下次如何避免=发布任务目录创建固定使用兼容参数或 .NET API。
- P002: 现象=长 PowerShell here-string 写入命令悬挂；阶段=任务文档；影响=任务文档写入延迟但未执行构建/发布；原因判断=多行命令承载不稳定；处理动作=终止悬挂会话并改用 apply_patch；结果=成功；是否可前置检查=是；是否可自动化=是；下次如何避免=长中文文档优先 apply_patch 或脚本文件，不用长内联 here-string。

## 2026-08-21 Git 与 worktree 输入锁定

- 维护仓主工作区：`D:\ProjectPackage\Int\IntRuoyiMaintance`，分支 `int_main`，冻结 HEAD `c3c85e7c476392520412f107165f15d277ae4064`（`任务: 绑定发布变更说明与提交`）；主工作区存在大量既有 modified/deleted/untracked 内容，不能作为构建输入。
- 主程序仓主工作区：`E:\IntRuoyi`，分支 `int_main`，冻结 HEAD `12a773ef285ff34bf2bd25036fd3dff2930912bc`；主工作区 `ahead 1` 且存在大量既有 modified/untracked 内容，不能作为构建输入。
- 本轮有效 releaseTag 计划：`release-20260821-intmain-head-test-r260821c-r1`。
- 本轮有效维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821c\m`，detached HEAD `c3c85e7c476392520412f107165f15d277ae4064`，`git status --short --branch` 仅显示 `## HEAD (no branch)`。
- 本轮有效主程序 release worktree：`D:\IntRuoyiWorktree\r260821c\a`，detached HEAD `12a773ef285ff34bf2bd25036fd3dff2930912bc`，`git status --short --branch --untracked-files=no` 仅显示 `## HEAD (no branch)`。
- 构建目录：维护控制台构建在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821c\m`；发布输入后端为 `D:\IntRuoyiWorktree\r260821c\a\IntRuoyiBackend`，前端为 `D:\IntRuoyiWorktree\r260821c\a\IntRuoyiFronted`。
- 本轮运行控制台本地配置：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821c\m\config\runtime-control.local.yaml`；`repo-root/frontend-root/ops-root/state-dir` 均指向本轮 release worktree 或本轮 state 目录；`production-write-enabled=false`，`test.access-enabled=true`，`prod/backup.access-enabled=false`。
- GREEN: experience-preflight -> PASS, 已按 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\worktree-memory.md` 与 `E:\IntRuoyi\docs\worktree-restrictions.md` 完成本轮发布前置门禁摘取和执行；高风险动作仅允许测试服 `172.30.30.58` 的 publish-test 与运行态验证。
- P003: 现象=`r260821a` 维护/主程序 worktree 路径已存在；阶段=worktree 创建；影响=不能复用该路径作为本轮专用 worktree；原因判断=前序/并发发布残留或已占用路径；处理动作=未触碰既有路径，改用新标识；结果=继续创建新路径；是否可前置检查=是；是否可自动化=是；下次如何避免=创建前先检查目标标识和 Git worktree list。
- P004: 现象=停止 Git 进程命令 `"skip $pid: ..."` 触发 PowerShell `$var:` 插值解析错误；阶段=worktree 排障；影响=首次停止命令失败但未停止任何进程；原因判断=PowerShell 冒号插值规则；处理动作=改用 `$procId` 和 `"${procId}"`；结果=仅停止本任务 Git 进程链；是否可前置检查=是；是否可自动化=是；下次如何避免=变量后接冒号一律用 `${var}`。
- P005: 现象=`r260821b\a` checkout 被中断后成为不完整 dirty worktree，状态显示大量 `D`；阶段=worktree 创建；影响=该 worktree 不能作为发布输入；原因判断=quiet/进度输出未设计，误把长 checkout 无输出当作卡死；处理动作=用 `git worktree remove -f -f` 精确删除本任务不完整 worktree并 `prune`；结果=`existsAfter=False`，改用 `r260821c` 重建；是否可前置检查=是；是否可自动化=是；下次如何避免=大仓 checkout 使用 `--quiet` 并按文件规模预留足够等待窗口。
- P006: 现象=Node `-e` 配置生成脚本中的模板反引号被 PowerShell 解析，导致 `Expression expected`；阶段=运行控制台配置；影响=首次未写入配置；原因判断=PowerShell 对反引号的转义行为；处理动作=改用字符串拼接重跑；结果=配置写入成功且未输出 secret；是否可前置检查=是；是否可自动化=是；下次如何避免=PowerShell 内联 Node 脚本禁止使用 JavaScript 模板反引号。

## 2026-08-21 构建维护控制台

- 维护控制台构建命令：`pwsh -NoProfile -ExecutionPolicy Bypass -File D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821c\m\scripts\build.ps1`，执行目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821c\m`，输入仍为 detached clean HEAD `c3c85e7c476392520412f107165f15d277ae4064`。
- P007: 现象=`pnpm --dir frontend install --frozen-lockfile` 输出到 `resolved 70, reused 69, added 69` 后长时间无新输出，且 `frontend\node_modules` 仅有 `.pnpm` 目录、根依赖链接未完成；阶段=维护控制台构建；影响=维护控制台 JAR 未生成，未进入 build-release/publish-test/服务器写入；原因判断=pnpm 安装链接阶段或子进程完成等待异常；处理动作=停止本任务构建进程，未停止并发任务进程；结果=构建退出码 1，准备按 pnpm 发布门禁清理本轮半安装产物后重新构建；是否可前置检查=是；是否可自动化=是；下次如何避免=发布 worktree 构建前先检查 pnpm 版本、ignored-builds、node_modules 半安装残留和真实子进程完成状态。
- P008: 现象=`pnpm approve-builds --all` 在本机 pnpm 10.22.0 返回 `Unknown option: 'all'`，无参 `approve-builds` 返回 `There are no packages awaiting approval`，但单独 `pnpm install --frozen-lockfile --reporter append-only` 仍停在 `resolved 70, reused 70, added 69` 后不退出；阶段=维护控制台依赖恢复；影响=官方构建脚本第二次仍无法进入 typecheck/build/Maven；原因判断=当前 pnpm 版本参数契约与历史文档不一致，同时默认 hardlink/link 导入方式在本 worktree 卡住；处理动作=停止本任务 install，准备清理半安装 `node_modules` 后使用同一 lockfile、同一 pnpm、`package-import-method=copy` 重新恢复依赖；结果=尚未完成重装；是否可前置检查=是；是否可自动化=是；下次如何避免=发布前按实际 `pnpm help approve-builds` 和 `pnpm config get package-import-method` 做版本化门禁，若默认导入方式卡住则 fail fast 记录并切换为可审计的 copy 导入。
- 长过程复盘：当前进度=Git/worktree 冻结与 migration gate 已通过，维护控制台构建卡在 pnpm install；已完成步骤=任务文档、经验门禁、release worktree、runtime config、app/ops migration gate；阻塞点=维护控制台前端依赖安装未完成；耗时原因=pnpm store 复用/链接阶段极慢且无及时 fail fast；下一步动作=复核 pnpm 门禁、清理本任务 release worktree 中半安装 node_modules 后重新执行维护控制台构建。
- 依赖恢复结果：清理本轮半安装 `frontend\node_modules` 后，`pnpm install --frozen-lockfile --package-import-method=copy --child-concurrency=1 --reporter append-only` 26.3s PASS；安装警告忽略 `esbuild@0.27.7`、`vue-demi@0.14.10` 构建脚本。
- build scripts 清零结果：临时写入 `pnpm.onlyBuiltDependencies=["esbuild","vue-demi"]` 后执行 `pnpm rebuild --pending` PASS；随后 `git restore -- frontend/package.json` 恢复源文件，`git status --short --branch --untracked-files=no` 仅 `## HEAD (no branch)`。
- P009: 现象=恢复 `package.json` 后 `pnpm ignored-builds` 输出 `Cannot identify as no node_modules found`，但 `frontend\node_modules` 实际存在，`.modules.yaml` 显示 `pendingBuilds: []`，`esbuild.exe` 存在，且 Vite 构建已实际成功；阶段=维护控制台依赖验证；影响=pnpm CLI 单项证据不能作为唯一验收依据；原因判断=pnpm 10.25 对当前 copy/symlink node_modules 识别异常；处理动作=追加读取 `.modules.yaml`、关键 esbuild 二进制和实际 Vite build 结果作为补充证据；结果=依赖门禁通过但需沉淀为下次前置检查；是否可前置检查=是；是否可自动化=是；下次如何避免=ignored-builds 异常时必须读取 `.modules.yaml pendingBuilds` 和关键二进制，不得只看 CLI 文本。
- GREEN: maintenance-console-build -> PASS, `scripts\build.ps1` 通过：pnpm install already up-to-date、`vue-tsc --noEmit` PASS、`vite build` PASS、Maven tests `26` run / `0` failures / `0` errors / `0` skipped，JAR `backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 生成成功。
- 维护控制台 JAR：路径 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821c\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，size=`35141811`，sha256=`d9f778f6082590f50cee6bc455885c370625040dc8b31ce7475de5a461e796d6`。

## 2026-08-21 build-release r260821c-r1

- build-release preview：payload `action=build-release`、`publishScope=code-only`、`includeOnlyOffice=false`、`includeShowroomBuildPackage=false`、`enableSmartReleaseReport=true`、`releaseTag=release-20260821-intmain-head-test-r260821c-r1`；preview PASS，脚本 `ops\deploy\publish-int-ruoyi.ps1` 参数含 `-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`、三环境 host、冻结后端/前端 worktree 路径，不含 `targetEnvironment`。
- build-release operation：`op-2026-08-20T181747038141600Z-edab6cc7-c23b-4fed-ae64-554d17d8b4dc`，状态 FAILED，退出码 1；未执行 publish-test、mark-tested、promote-prod、promote-backup。
- P010: 现象=build-release 先完成主程序后端 Maven `yudao-server -am -DskipTests clean package`（30/30 reactor SUCCESS，3m08s），随后前端 `pnpm build:test` 失败，提示 `Local package.json exists, but node_modules missing` 与 `cross-env` 不可识别；阶段=build-release；影响=发布包、manifest、版本号和变更说明未生成，`r260821c-r1` 判废且不得发布；原因判断=本轮 app release worktree 的 `IntRuoyiFronted` 未先恢复依赖，发布脚本未自动安装前端依赖；处理动作=停止在构建阶段，不发布测试服，准备在同一冻结 app worktree 恢复前端依赖后使用新 releaseTag 重建；结果=待重建；是否可前置检查=是；是否可自动化=是；下次如何避免=build-release 前必须检查 `IntRuoyiFronted\node_modules\.bin\cross-env.cmd`、`vite.cmd`、`vue-tsc.cmd` 存在并记录 `pnpm install` / ignored-builds 结果。
- 长过程复盘：当前进度=维护控制台构建成功，build-release r1 在 app 前端依赖缺失处失败；已完成步骤=后端 Maven package 成功、Docker/对象锁门禁通过；阻塞点=app 前端依赖缺失；耗时原因=后端完整 Maven package 3m08s 后才暴露前端依赖门禁缺口；下一步动作=恢复 app 前端依赖，验证 app worktree 仍 clean，然后用 `release-20260821-intmain-head-test-r260821c-r2` 重建。
- app 前端依赖恢复：`pnpm install --frozen-lockfile --package-import-method=copy --child-concurrency=1 --reporter append-only` 在 `D:\IntRuoyiWorktree\r260821c\a\IntRuoyiFronted` PASS，1103 packages restored，耗时 11m33s，未下载新包。
- app build scripts 清零：安装后 `ignored-builds` 列出 `core-js`、`esbuild`、`@parcel/watcher`、`vue-demi`、`@swc/core`、`core-js-pure`、`es5-ext`；临时写入 `pnpm.onlyBuiltDependencies` 后 `pnpm rebuild --pending` PASS，再 `git restore -- IntRuoyiFronted/package.json` 恢复；最终 `pnpm ignored-builds` 显示 `None`。
- app 前端依赖验证：`IntRuoyiFronted\node_modules\.bin\cross-env.cmd`、`vite.cmd`、`vue-tsc.cmd` 均存在；主程序 release worktree `git status --short --branch --untracked-files=no` 仅 `## HEAD (no branch)`。

## 2026-08-21 build-release r260821c-r2

- build-release r2 preview：`releaseTag=release-20260821-intmain-head-test-r260821c-r2`，code-only/intruoyi，`includeOnlyOffice=false`，`includeShowroomBuildPackage=false`，`enableSmartReleaseReport=true`，preview PASS。
- build-release r2 operation：`op-2026-08-20T185035166154800Z-2d39ee79-c20c-4a1a-b20e-c79d799b432d`，状态 FAILED，退出码 1；未执行 publish-test、mark-tested、promote-prod、promote-backup。
- r2 进度证据：后端 Maven package SUCCESS（30/30，2m23s）；前端 `pnpm build:test` SUCCESS，`dist-intruoyi-test\release-info.json` 已写入；backend/frontend Docker image build SUCCESS；本地 image tar `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260821-intmain-head-test-r260821c-r2\intruoyi-images_release-20260821-intmain-head-test-r260821c-r2.tar` 已生成。
- P011: 现象=导出镜像并移除 Docker build context 后，脚本失败 `Missing -SmartReleaseBaselineManifestPath; Smart Release report-only requires explicit local input files.`；阶段=build-release manifest/report；影响=manifest/版本号/变更说明未完成，r2 不能发布；原因判断=preview 启用了 `EnableSmartReleaseReport`，但本轮未配置必需 baseline manifest 输入；处理动作=判废 r2，不修改包或补写 manifest，下一轮使用新 releaseTag 且不启用 Smart Release report-only；结果=待 r3 重建；是否可前置检查=是；是否可自动化=是；下次如何避免=build-release preview 若含 `-EnableSmartReleaseReport`，必须同时检查 `SmartReleaseBaselineManifestPath`，缺失则 fail fast 或不启用该可选报告。
- 长过程复盘：当前进度=依赖恢复完成，r2 到镜像/tar 阶段后因 Smart Release baseline 缺失失败；已完成步骤=后端包、前端包、镜像构建、tar 导出；阻塞点=可选 Smart Release report 配置缺 baseline；耗时原因=该缺口在镜像导出后才暴露；下一步动作=用 `release-20260821-intmain-head-test-r260821c-r3` 重建且 `enableSmartReleaseReport=false`，构建后必须直接校验 manifest/sourceRepos/release-info。

## 2026-08-21 build-release r260821c-r3 阻塞

- build-release r3 operation：`op-2026-08-20T190813392637100Z-556cbade-a3e9-4c4a-9dc9-bc791ed59add`，状态 SUCCESS；payload `publishScope=code-only`、`includeOnlyOffice=false`、`includeShowroomBuildPackage=false`、`releaseTag=release-20260821-intmain-head-test-r260821c-r3`，未带 `enableSmartReleaseReport`。
- r3 构建证据：后端 Maven package SUCCESS（30/30，3m05s）；前端 `pnpm build:test` SUCCESS；backend/frontend Docker image build SUCCESS；镜像 tar `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260821-intmain-head-test-r260821c-r3\intruoyi-images_release-20260821-intmain-head-test-r260821c-r3.tar`，size=`735218688`，sha256=`518255e77a7e7b7046f38da42d850ff7de8ac05a53885a0ae6b1071ddba6c753`；本地包含 `manifest.json` 和 `release-manifest.json`，并已上传 NAS `Backup/ReleasePackage/release-20260821-intmain-head-test-r260821c-r3`。
- sourceRepos 校验：`manifest.json` 与前端 `release-info.json` 均记录 `ruoyi-vue-pro` / `yudao-ui-admin-vue3` commit=`12a773ef285ff34bf2bd25036fd3dff2930912bc`、dirty=false；维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821c\m` 与主程序 release worktree `D:\IntRuoyiWorktree\r260821c\a` 均仍为 detached clean。
- BLOCKER: package-validation -> `pwsh -NoProfile -ExecutionPolicy Bypass -File D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821c\m\ops\release\validate-release-manifest.ps1 -PackagePath E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260821-intmain-head-test-r260821c-r3` 返回 status=`failed`、code=`FORBIDDEN_HARDCODED_TARGET_IP`；`runtime-env/test.env`、`prod.env`、`backup.env` 第 10 行均含 `EDHR_S3_ENDPOINT=http://172.30.30.57:9000`。
- BLOCKER: release-info-change-summary -> 冻结主程序提交主题为 `任务: 修复发布Hook镜像参数`，但 manifest 与 `IntRuoyiFronted\dist-intruoyi-test\release-info.json` 的 `changeSet.summary/items` 显示乱码 `浠诲姟: 淇鍙戝竷Hook闀滃儚鍙傛暟`；无法确认运行控制台版本变更说明与本次构建提交一致。
- P012: 现象=manifest validator 发现 forbidden hardcoded target IP；阶段=构建后 manifest/发布包校验；影响=发布包无效，不得进入 publish-test；原因判断=runtime-env 生成仍写入具体 `172.30.30.57` eDHR endpoint；处理动作=停止发布，不修改包、不发布测试服；结果=任务阻塞；是否可前置检查=是；是否可自动化=是；下次如何避免=build-release 成功判定前强制运行 validator 并拦截 runtime-env forbidden IP。
- P013: 现象=manifest/release-info 变更说明乱码；阶段=版本号/变更说明校验；影响=运行控制台无法满足“显示当前版本号和变更说明”验收；原因判断=Git 提交说明采集或写入路径编码错误；处理动作=停止发布，不手工修包；结果=任务阻塞；是否可前置检查=是；是否可自动化=是；下次如何避免=build-release 后 UTF-8 比对 `changeSet` 与 `git log -1 --pretty=%s`，不一致即 fail fast。
- P014: 现象=build-release operation SUCCESS 且包已上传 NAS，但独立 validator 失败；阶段=构建脚本/流程一致性；影响=operation 状态与可发布性不一致；原因判断=构建脚本未把 validator 失败并入成功门禁；处理动作=以后置 validator 为准判定失败，未执行 publish-test、mark-tested、promote-prod 或 promote-backup；结果=任务阻塞；是否可前置检查=是；是否可自动化=是；下次如何避免=发布包上传或 operation SUCCESS 前必须接入 manifest validator。
- 长过程复盘：当前进度=r3 包构建成功但发布前校验失败；已完成步骤=任务文档、经验门禁、clean worktree 冻结、维护控制台构建、app 依赖恢复、r1/r2 失败判废、r3 build-release；阻塞点=发布包 validator failed 与变更说明乱码；耗时原因=前端依赖恢复、后端完整 Maven package、Docker build/save 以及 validator 问题在包生成后才暴露；下一步动作=需要正式修复发布脚本编码与 runtime-env 目标配置契约，提交后以新冻结 HEAD/new releaseTag 重新构建发布。
- 结论：根据用户“如无法确认构建来源、manifest、版本号或变更说明，必须失败并记录问题，不得继续发布”的要求，本轮停止在 publish-test 前；测试服、正式服、备份服均未发布，未执行 `mark-tested`、`promote-prod`、`promote-backup`。

## 2026-08-21 正式修复发布前阻塞

- 用户继续后恢复任务：r260821c-r3 仍按规则判废，未发布；继续路径改为正式修复发布脚本后从新提交重建。
- RED: node scripts/tests/publish_release_info_contract.test.mjs -> FAIL, elease change-set is derived from the exact frozen source commits 缺 Invoke-ProcessCapture -FilePath 'git'，对应 manifest/release-info 中文提交说明乱码风险。
- RED: python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -q -> FAIL, 	est_release_runtime_env_fails_when_test_endpoint_points_outside_test_host 缺 Assert-ReleaseRuntimeEnvTargetBoundary，对应测试服 runtime-env 混入正式/备份 eDHR endpoint 风险。
- 修复动作：ops/deploy/publish-int-ruoyi.ps1 的 Git 元数据采集改为 git -c i18n.logOutputEncoding=UTF-8 + UTF-8 子进程输出读取；Resolve-TargetPublishRuntimeValue 优先使用目标环境 EDHR 变量，并对 test runtime-env 阻断 172.30.30.57/59。
- GREEN: node scripts/tests/publish_release_info_contract.test.mjs -> PASS, 4/4。
- GREEN: python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -q -> PASS, 19/19。
- GREEN: python -X utf8 -m pytest scripts/tests/test_publish_dcc_codex_runtime_contract.py -q -> PASS, 6/6。
- GREEN: powershell-parse -> PASS, PS_PARSE_OK tokens=28906。
- GREEN: git diff --check -> PASS, scoped to publish script and affected contracts。

## 2026-08-21 r260821d-r1 重建失败与正式修复

- 继续输入锁定：维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821d\m` 为 detached clean HEAD `18bcbdace107916bce82b9c576b0bdb9d83507b1`（`任务: 修复测试发布包校验阻塞`）；主程序 release worktree `D:\IntRuoyiWorktree\r260821d\a` 为 detached clean HEAD `12a773ef285ff34bf2bd25036fd3dff2930912bc`（`任务: 修复发布Hook镜像参数`）。
- build-release r260821d-r1 operation：`op-2026-08-20T204410618270900Z-4113eab9-aa9c-410f-bfea-124cabbddb7d`，releaseTag=`release-20260821-intmain-head-test-r260821d-r1`，状态 FAILED；后端 Maven package SUCCESS、前端 `pnpm build:test` SUCCESS、backend/frontend Docker image build SUCCESS、镜像 tar 已生成，但未生成 `manifest.json` 或 `release-manifest.json`。
- BLOCKER: package-validation -> `validate-release-manifest.ps1 -PackagePath E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260821-intmain-head-test-r260821d-r1` 返回 `MANIFEST_MISSING`；该 releaseTag 判废，未执行 publish-test、mark-tested、promote-prod、promote-backup。
- P015: 现象=r260821d-r1 后端/前端和镜像 tar 已生成但根目录缺 `manifest.json`；阶段=build-release manifest 生成前；影响=无法证明构建来源、版本号或变更说明，不得发布；原因判断=runtime-env/test.env 生成阶段发现 eDHR endpoint 指向非测试服后 fail-fast，manifest 未写入；处理动作=停止发布，判废 r1；结果=未发布；是否可前置检查=是；是否可自动化=是；下次如何避免=runtime-env 目标 host 边界在镜像构建前检查。
- RED: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -q` -> FAIL, 新增 `test_release_runtime_env_rebinds_generic_edhr_endpoint_to_target_host` 复现通用 `EDHR_S3_ENDPOINT` 未按 target host 重绑的问题。
- 修复动作：`ops/deploy/publish-int-ruoyi.ps1` 新增 `Resolve-TargetEdhrS3Endpoint`；若缺目标专属 eDHR endpoint 且通用 endpoint 是绝对 URI/IP host，则保留 scheme/port/path 并将 host 重绑到当前 `TargetServerHost`；`Set-PublishRuntimeDefaultsForTarget` 和 `New-ReleaseRuntimeEnvContent` 均传入 `TargetServerHost`。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -q` -> PASS, 20/20。
- GREEN: `node scripts/tests/publish_release_info_contract.test.mjs` -> PASS, 4/4。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_publish_dcc_codex_runtime_contract.py -q` -> PASS, 6/6。
- GREEN: `powershell-parse` -> PASS, `PS_PARSE_OK tokens=30728`。
- GREEN: `git diff --check -- ops\deploy\publish-int-ruoyi.ps1 scripts\tests\test_release_sql_preflight_gate.py` -> PASS。
- P016: 现象=test runtime env 仍解析到非测试服 host；阶段=runtime-env 生成；影响=新 releaseTag 在 manifest 前失败；原因判断=上次修复只支持目标专属变量，缺目标专属变量时仍使用通用 endpoint；处理动作=加入 target host 重绑并补合同；结果=目标合同和相邻合同通过；是否可前置检查=是；是否可自动化=是；下次如何避免=build-release 静态合同覆盖 generic endpoint -> target host 重绑路径。

## 2026-08-21 r260821e-r1 重建失败与 runtime secret 正式修复

- 继续输入锁定：维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821e\m` 为 detached clean HEAD `ea9cc252ab70f0907e19c8601f29a8761b37a0ee`（`任务: 修复测试发布eDHR目标端点`）；主程序 release worktree `D:\IntRuoyiWorktree\r260821e\a` 为 detached clean HEAD `12a773ef285ff34bf2bd25036fd3dff2930912bc`（`任务: 修复发布Hook镜像参数`）。
- build-release r260821e-r1 operation：`op-2026-08-20T212717109994600Z-fd20c0b4-59a1-49d0-9dd9-bac5010e49e8`，releaseTag=`release-20260821-intmain-head-test-r260821e-r1`，状态 FAILED；失败发生在 build-release 前置 eDHR protected storage verifier，未生成发布包、未执行 publish-test、mark-tested、promote-prod、promote-backup。
- P017: 现象=eDHR verifier 返回 `InvalidAccessKeyId`，本地进程 generic `EDHR_S3_ENDPOINT` 指向 `172.30.30.57`，但测试服 `.env` 已存在 `EDHR_S3_*` 且 endpoint host 为 `172.30.30.58`；阶段=build-release 前置对象锁校验；影响=无法生成发布包，不得发布；原因判断=隔离运行控制台缺少 `EDHR_S3_TEST_*` 目标变量，脚本只能把 generic/prod 凭据用于 test endpoint；处理动作=只读读取测试服 `.env` 后在内存中运行 verifier，确认测试服目标配置 PASS；结果=定位为配置注入/脚本 secret 渠道问题，r1 判废；是否可前置检查=是；是否可自动化=是；下次如何避免=启动隔离运行控制台前必须检查 `EDHR_S3_TEST_*` 是否存在，且 build-release verifier 必须用目标环境凭据。
- P018: 现象=一次宽泛 `rg EDHR ...` 扫描命中过往 `ops/backup-ops/tmp` 中的 secret-bearing 历史 runtime env；阶段=排障证据采集；影响=原始命令输出不得写入任务证据或提交；原因判断=扫描范围包含历史备份/恢复临时目录；处理动作=未保存原始输出，后续只用脱敏/窄范围探针；结果=未将明文凭据写入任务文档；是否可前置检查=是；是否可自动化=是；下次如何避免=发布排障搜索默认排除 `ops/backup-ops/tmp`、`runtime`、历史 restore/rehearsal 目录，必须只记录 secret presence/host 摘要。
- P019: 现象=本机 48181 仍运行旧 `r260821c` 维护控制台，当前 `r260821e` 控制台运行在隔离端口 48183；阶段=运行控制台归属检查；影响=若误用 48181 会看到旧 operation/旧 release package 列表；原因判断=此前为避免覆盖稳定主控制台启动了隔离端口；处理动作=继续使用 48183 作为本轮 r260821e 操作面；结果=旧 48181 未停止、未触碰并发/稳定实例；是否可前置检查=是；是否可自动化=是；下次如何避免=每轮 action 前记录实际控制台端口、PID、JAR 路径和 state-dir。
- RED: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -q` -> FAIL, 新增/修改合同证明 release package writer 仍会写入 `runtime-env/*.env` secret 文件，且 deploy-release 未在 eDHR verifier 前导入远端 `.env`。
- 修复动作：`ops/deploy/publish-int-ruoyi.ps1` 的 `Write-ReleaseRuntimeEnvPackage` 改为不写 secret runtime-env 文件；新增 `Import-ExistingRemoteRuntimeEnvSettings`，deploy-release 在对象锁和 DCC secret 门禁前读取目标远端 `.env` 并应用到进程设置。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -q` -> PASS, 21/21。
- GREEN: `node scripts/tests/publish_release_info_contract.test.mjs` -> PASS, 4/4。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_publish_dcc_codex_runtime_contract.py -q` -> PASS, 6/6。
- GREEN: `powershell-parse` -> PASS, `PS_PARSE_OK tokens=30663`。
- GREEN: `git diff --check -- ops\deploy\publish-int-ruoyi.ps1 scripts\tests\test_release_sql_preflight_gate.py` -> PASS。

## 2026-08-21 r260821f-r1 build-release 密钥渠道回归

- 维护 release worktree：D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821f\m，detached clean HEAD a87b0ef0e14c449a71c1a1a39f6183539bba6fe3；主程序 release worktree：D:\IntRuoyiWorktree\r260821f\a，detached clean HEAD 12a773ef285ff34bf2bd25036fd3dff2930912bc。
- GREEN: maintenance-console-build -> PASS，scripts\build.ps1：Vue typecheck/build PASS，Maven tests 26/26 PASS；JAR sha256=2B8D1D9E33CC61990ADBC5DFCF5EBADC86C63E165A7A9091777E8726D4087B69。
- GREEN: runtime-control-isolation -> PASS，r260821f 控制台 JAR 运行于 127.0.0.1:48184，PID 48592，/actuator/health=UP；epo-root/frontend-root/ops-root/state-dir 指向 r260821f，prod/backup access-enabled=false。
- GREEN: build-release-preview -> PASS，releaseTag=release-20260821-intmain-head-test-r260821f-r1，action=build-release，Component=intruoyi，publishScope=code-only，SkipDatabaseSync/SkipMinioSync=true，未包含 publish-test、mark-tested、promote-prod 或 promote-backup。
- BLOCKER: build-release -> op-2026-08-21T085715802852Z-2607b1d9-be5a-4caf-b7a5-d0e40305fb77 FAILED；eDHR protected storage verifier 报 InvalidAccessKeyId，未生成可发布 manifest/package，未执行 publish-test。
- P020: 现象=build-release verifier 仍使用非测试服密钥；阶段=build-release 前置对象锁校验；影响=releaseTag r260821f-r1 判废且不能发布；原因判断=Import-ExistingRemoteRuntimeEnvSettings 在 $Mode -eq 'build-release' 时直接 return，且调用只位于 deploy-release 分支；处理动作=停止发布，创建独立修复 worktree 补回归并正式修复；结果=修复中；是否可前置检查=是；是否可自动化=是；下次如何避免=build-release/deploy-release 等所有 verifier 路径都必须在 verifier 前只读导入目标测试服 runtime .env，且证据记录目标环境。
- 长过程复盘：当前进度=冻结输入、维护控制台、策略门禁、build-release preview 已完成；已完成步骤=构建/隔离控制台/操作预览；阻塞点=build-release 对象锁 verifier 密钥来源仍为本机继承值；耗时原因=错误在迁移策略门禁之后才暴露，且本轮 r260821f 需要再次全量修复-验证-重建；下一步动作=正式修复 build-release 的测试服 .env 只读导入顺序，提交并合回 int_main，使用新的 clean release worktree/new releaseTag 重建。
## 2026-08-21 r260821h-r1 build-release 前端依赖缺失

- BLOCKER: build-release -> op-2026-08-21T101022253432800Z-d2144004-5f85-42b3-b7b5-6214ddd88cb3 FAILED；后端 Maven package 成功，但前端 pnpm build:test 因 node_modules missing / cross-env not recognized 失败；releaseTag=release-20260821-intmain-head-test-r260821h-r1 判废。
- P021：现象=app 发布 worktree 仅检出 HEAD，未恢复依赖；阶段=前端 build；影响=无法生成可发布包，测试服发布无法继续；原因判断=新建 app release worktree 后遗漏前端依赖恢复步骤；处理动作=启动 pnpm install --frozen-lockfile --package-import-method=copy --child-concurrency=1 --reporter append-only 恢复 D:\IntRuoyiWorktree\r260821h\a\IntRuoyiFronted 依赖，再用新 releaseTag 重跑；结果=恢复中；是否可前置检查=是；是否可自动化=是；下次如何避免=app release worktree 进入 build-release 前先自动检查 node_modules\.bin\cross-env.cmd、vite.cmd、vue-tsc.cmd 是否存在。
- 长过程复盘：当前进度=r260821h 的维护控制台、隔离控制台、build-release preview、build-release 实执行已完成；已完成步骤=维护仓构建、repair worktree 合并、隔离控制台 48185、build-release r1 执行与失败定位；阻塞点=app release worktree 前端依赖缺失；耗时原因=前端 pnpm install 需要长时间链接/重建，且 build-release 直到 pnpm build:test 才暴露缺失；下一步动作=完成 app 依赖恢复后重建新的 releaseTag，再回到 manifest/package 校验和 publish-test。
## 2026-08-21 r260821h-r2 前端依赖恢复与重建前门禁

- P022: 现象=首次恢复 `D:\IntRuoyiWorktree\r260821h\a\IntRuoyiFronted` 依赖被用户中断，`pnpm install` 返回进程码 `1073807364`，停在 `added 1093/1103`；阶段=build-release 前端依赖恢复；影响=不能据此进入构建，前端关键命令仍不存在；原因判断=长时间 pnpm 链接阶段被中断，未产生可确认的完整依赖树；处理动作=不使用半安装结果，重新执行同一冻结 worktree、同一 lockfile 的 `pnpm install --frozen-lockfile --package-import-method=copy --child-concurrency=1 --reporter append-only`；结果=第二次安装 PASS，1103 packages，11m03.2s；`cross-env.cmd`、`vite.cmd`、`vue-tsc.cmd` 存在，`.modules.yaml` 的 `pendingBuilds=[]`，worktree 仍 clean；是否可前置检查=是；是否可自动化=是；下次如何避免=依赖安装必须以退出码 0、关键 bin、`.modules.yaml` 和实际 `pnpm build:test` 四项共同通过，长时间无输出先检查进程/CPU，不直接中断。
- 长过程复盘：当前进度=冻结输入、维护控制台构建、eDHR/迁移前置门禁和隔离运行控制台已完成；已完成步骤=app 前端依赖第二次恢复、关键命令检查、冻结 worktree clean 检查、`pnpm build:test` PASS（292.5s）；阻塞点=无，准备进入新 releaseTag 的 build-release；耗时原因=pnpm 依赖链接约 11m，Vite 构建约 292.5s；下一步动作=提交 r260821h-r2 build-release，完成后直接执行独立 manifest/版本/变更说明校验。
- GREEN: experience-preflight -> PASS，提交 build-release 前已重新核对本任务命中的发布前置经验、当前 releaseTag、维护/主程序 worktree 路径与提交、目标仅测试服范围、隔离控制台端口/PID/JAR/state-dir、测试服 host；本轮未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- GREEN: app-frontend-dependencies -> PASS，`pnpm install --frozen-lockfile --package-import-method=copy --child-concurrency=1 --reporter append-only` 完成 1103 packages；`pnpm ignored-builds` 仅报告安装策略提示，`.modules.yaml` `pendingBuilds=[]`，关键 `.bin` 命令均存在。
- GREEN: app-frontend-build -> PASS，`pnpm build:test` 在 `D:\IntRuoyiWorktree\r260821h\a\IntRuoyiFronted` 完成，输出 `Build successful. Please see dist-test directory`；主程序 release worktree `git status --short --branch --untracked-files=no` 仍仅显示 detached clean HEAD。
- GREEN: build-release-preview -> PASS，`releaseTag=release-20260821-intmain-head-test-r260821h-r2`，脚本路径为本轮维护 release worktree，后端/前端路径为本轮冻结 app worktree，包含 `-SkipDatabaseSync`、`-SkipMinioSync`，未包含目标发布动作。
## 2026-08-21 r260821h-r2 build-release 环境前置失败

- BLOCKER: build-release -> operation `op-2026-08-21T202257434311100Z-95a93ed5-d200-4b64-9809-a6b7177d185a` FAILED，日志末尾为 `Missing command: mvn`，退出码 1；releaseTag=`release-20260821-intmain-head-test-r260821h-r2` 判废，未生成可发布 package/manifest，未执行 publish-test。
- P023: 现象=隔离运行控制台 48185 的进程环境 PATH 含已不存在的 Maven 目录，build-release 在 migration policy gate 之后调用 Maven 前置时找不到 `mvn`；阶段=build-release 环境前置/构建；影响=r2 立即失败，未进入后端/前端构建和发布包生成；原因判断=本机 PATH 遗留指向不存在的 `D:\ProjectPackage\AutoProduction\tools\apache-maven-3.9.9\bin`，维护控制台继承了无效 PATH；处理动作=停止 r2，窄范围定位到现存本机 Maven `C:\Users\BJB110\AppData\Local\Temp\chocolatey\ChocolateyScratch\maven\3.9.16\apache-maven-3.9.16\bin`，验证 `mvn -version`，在任务隔离控制台进程启动前显式补入该 bin，健康检查恢复后使用新 releaseTag 重试；结果=r2 判废，r3 重试前 Maven 命令可用；是否可前置检查=是；是否可自动化=是；下次如何避免=运行控制台启动前必须执行 `Get-Command mvn`、`mvn -version` 和 Maven home 存在性检查；build-release preview/submit 前若命令缺失必须 fail fast，不得等到 migration gate 才暴露。
- 长过程复盘：当前进度=app 依赖和前端构建通过，r2 在 build-release 早期因运行控制台 PATH 缺 Maven 失败；已完成步骤=失败 operation 日志脱敏核对、r2 判废、Maven 路径窄范围定位、隔离控制台重启并确认 48185 可用；阻塞点=已解除；耗时原因=此前控制台进程从无效 PATH 启动，缺少运行前命令门禁；下一步动作=使用新 releaseTag `release-20260821-intmain-head-test-r260821h-r3` 重新 preview/submit，成功后立即校验 package/manifest。
- GREEN: runtime-control-maven-preflight -> PASS，已确认本轮控制台使用的 Maven 命令可执行、版本为 3.9.16，Java 21 可用，端口 48185 健康检查恢复。
- 长过程阶段记录（r260821h-r3）：当前进度=operation RUNNING；已完成 eDHR protected storage verifier、Docker 前置检查、冻结后端 Maven package；Maven reactor 30/30 SUCCESS，耗时约 3m19s；阻塞点=无；耗时原因=完整后端 reactor 构建后才进入前端构建；下一步动作=等待 `pnpm build:test`、镜像构建/导出、manifest 写入和 NAS 上传完成，再执行独立 validator。
## 2026-08-21 r260821h-r3 build-release 前端基础镜像网络失败

- BLOCKER: build-release -> operation `op-2026-08-21T203046906602Z-db31bc41-310d-436c-8715-d1989edfd016` FAILED，后端 Maven 30/30 SUCCESS、前端 `pnpm build:test` SUCCESS、后端镜像构建 SUCCESS；前端镜像构建因拉取 `nginx:1.27-alpine` 时 Docker Hub token 请求连接失败而退出码 1，未生成可发布 manifest/package，未执行 publish-test。
- P024: 现象=构建前端镜像时 `docker build` 无法从 `auth.docker.io` 获取匿名 token，错误为连接 `104.244.43.231:443` 失败；阶段=build-release 镜像构建；影响=r3 判废，已完成的后端/前端构建不能直接作为发布包，未发布测试服；原因判断=Docker Hub 网络访问瞬时失败且本地没有 `nginx:1.27-alpine` 镜像；处理动作=先确认 `docker image inspect nginx:1.27-alpine` 不存在、Docker daemon 正常，再不修改 Dockerfile 的前提下执行标准 `docker pull nginx:1.27-alpine`；结果=pull PASS，digest=`sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`，使用新 releaseTag 重建；是否可前置检查=是；是否可自动化=是；下次如何避免=build-release 前检查所需基础镜像是否本地存在；不存在时先执行带超时和退出码断言的标准 pull，pull 失败即 fail fast，不继续消耗后端构建时间。
- 长过程复盘：当前进度=app 依赖、前端构建、Maven、eDHR、Docker daemon 均已通过，r3 在前端镜像基础镜像拉取失败；已完成步骤=失败日志脱敏核对、Docker 镜像缺失/daemon/网络确认、标准 nginx 基础镜像 pull PASS；阻塞点=已解除；耗时原因=前端镜像阶段才暴露 Docker Hub 瞬时网络问题，r3 已完成后端/前端后才判废；下一步动作=使用新 releaseTag `release-20260821-intmain-head-test-r260821h-r4` 重新 preview/submit，成功后继续独立包校验。
- GREEN: docker-base-image-preflight -> PASS，`docker info` server 29.2.1 正常，`nginx:1.27-alpine` 已成功 pull 且 digest 已记录；本轮仍只允许测试服发布范围。
- 长过程阶段记录（r260821h-r4）：当前进度=operation RUNNING；已完成 eDHR、Maven 后端 reactor 30/30 SUCCESS，当前进入前端构建/镜像阶段；阻塞点=无；耗时原因=每次新 releaseTag 均重新执行完整后端构建，r3 已验证前端镜像失败原因并在 r4 前补齐基础镜像；下一步动作=等待镜像导出、manifest/package 写入和 NAS 上传。
## 2026-08-21 r260821h-r4 构建包与 publish-test 前置验收

- GREEN: build-release-r260821h-r4 -> PASS，operation=`op-2026-08-21T204711713137200Z-9de34c7d-990f-4236-8d47-70be7309ce14` 状态=`SUCCESS`；维护控制台 JAR、app 后端/前端 release worktree 均为 detached clean；app source commit=`12a773ef285ff34bf2bd25036fd3dff2930912bc`，subject=`任务: 修复发布Hook镜像参数`；maintenance HEAD=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`。
- GREEN: manifest-validation-r260821h-r4 -> PASS，`validate-release-manifest.ps1 -Mode report-only` 返回 `MANIFEST_VALIDATION_PASSED`；package=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260821-intmain-head-test-r260821h-r4`；`manifest.json`、`release-manifest.json`、镜像 tar 均存在，validator 结构、artifact sha256、forbidden target IP/secret scan 全通过。
- GREEN: package-provenance-r260821h-r4 -> PASS，manifest v1 `packageType=full-release`、`publishScope=code-only`、`packageId/releaseTag` 均为 `release-20260821-intmain-head-test-r260821h-r4`；backend/admin-frontend sourceRepos 均为冻结 app commit、`dirty=false`；legacy `gitCommit` 同一提交；镜像 tar sha256=`b9735d8aaf43e4665aec5ea262a7fa92e8c66e16bbbadad7e31ca5203cb5c040`。
- GREEN: release-info-r260821h-r4 -> PASS，前端 `dist-intruoyi-test/release-info.json` 的 releaseTag/packageId、sourceRepos、dirty=false、changeSet 与 manifest 一致；summary=`任务: 修复发布Hook镜像参数`，items 含短提交 `12a773ef285f` 和相同中文 subject，未出现乱码。
- P025: 现象=验收初查将 `manifest.json` 缺少顶层 `version` 属性误读为版本号为空；阶段=manifest/版本号验收；影响=短暂阻止 publish-test，要求确认版本号权威来源；原因判断=manifest v1 schema/legacy manifest 不定义通用 `version` 字段，现有发布契约使用 `releaseTag/packageId` 作为发布版本标识，运行控制台页面也展示该值；处理动作=读取 `manifest-v1.schema.json`、现有 `test-release-preflight.md` 和运行控制台 UI/API 契约，确认 `releaseTag` 是机器与用户可见版本标识，同时记录 app package version=`2026.04-snapshot`、maintenance JAR version=`2026.06-SNAPSHOT`；结果=版本标识与变更说明可确认，r4 不判废；是否可前置检查=是；是否可自动化=是；下次如何避免=版本验收脚本明确断言 `manifest.packageId/releaseTag`、frontend release-info releaseTag 和运行控制台 testCurrentReleaseTag，不再查询未定义的 `manifest.version`。
- GREEN: publish-test-preview-r260821h-r4 -> PASS，payload 仅为 `action=publish-test`、`targetEnvironment=test`、目标 releaseTag；预览脚本 `-Mode deploy-release -Environment test -ServerHost 172.30.30.58`，未提交 `mark-tested`、`promote-prod`、`promote-backup`。
- GREEN: experience-preflight -> PASS，已在本次测试服远程写入前重新核对测试服 host/目录、releaseTag、manifest/sourceRepos/dirty、release-info/changeSet、对象锁 verifier、远端 `.env` 读取渠道、PowerShell/SSH UTF-8 和禁止正式/备份动作；只允许当前 r4 `publish-test`。

## 2026-08-21 r260821h-r4 publish-test 失败与失败态复核

- publish-test operation：`op-2026-08-21T210307402431400Z-d11e3d45-06fb-4026-a039-a1ee4f70086b`，最终 `FAILED`，summary=`命令退出码非 0: 1`；同一 operation 未重提，未切换 releaseTag，未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- 长过程复盘：当前进度=已完成 r4 build-release、manifest/版本/变更说明校验和 publish-test 预览；发布操作经历包上传、505 个 required SQL 文件同步、约 438 条迁移登记后进入 route snapshot BACKFILL；阻塞点=后端独立运行报告启动失败；耗时原因=逐文件 scp 与逐迁移登记串行耗时，operation summary 长时间保持“命令已提交到本机执行队列”，但日志持续推进；下一步动作=冻结失败证据，复核测试服实际状态并阻止任何重试/状态表修改。
- 失败日志关键错误：`MesProRouteVersionSnapshotMigrationRunner` 在 Spring context 初始化时 `No default constructor found`，随后 `Application run failed`，远端命令退出码 1。
- P026：现象=r4 Docker backend 构建输出 `InvalidDefaultArgInFrom` warning；阶段=镜像构建；影响=构建仍成功，但 Dockerfile 的基础镜像 ARG 默认值契约不明确；原因判断=BuildKit 静态检查发现 ARG/FROM 组合可能产生无效基础镜像引用；处理动作=记录 warning，继续以实际镜像 digest、manifest 和 validator 作为构建验收依据；结果=未阻断 r4 build，但应进入下一轮 build 前置门禁；是否可前置检查=是；是否可自动化=是；下次如何避免=扫描构建 warning，命中该 warning 时要求修复 Dockerfile 或显式批准后重建。
- P027：现象=publish-test operation 原始日志中出现带密码参数的 MySQL 命令；阶段=required SQL/迁移登记；影响=raw log 不得进入长期证据或提交，存在凭据暴露风险；原因判断=发布脚本把完整命令行写入 operation log，日志层未统一脱敏；处理动作=任务证据只保存脱敏摘要，原始日志不复制、不提交；结果=本轮阻塞项已记录，脚本日志契约仍需修复；是否可前置检查=是；是否可自动化=是；下次如何避免=发布脚本输出统一走脱敏 logger，提交前对 raw log 执行 `mysql -p`/password/token secret scan，命中即 fail fast。
- P028：现象=失败 operation 后远端 `/opt/intruoyi/runtime/.env` 的 `IMAGE_TAG` 为 r4，但实际运行镜像仍为 backend=`hotfix-20260814-route-submit-order-r1`、frontend=`release-20260813-intmain-head-test-r260812b-r2`；frontend `release-info.json` 仍为旧版本；阶段=publish-test 失败收束；影响=env、compose 解析镜像、实际容器和前端版本说明不一致，不能判发布成功；原因判断=脚本在迁移前先写 `.env`，失败时没有提供可证明的旧 env 自动恢复；处理动作=只读核对 operation、env、compose images、docker inspect、容器状态、backend health、frontend HTTP 和 release-info；由于旧 env 基线无法安全证明，未猜测回滚、未修改 release lock/migration、未重试；结果=任务状态 blocked；是否可前置检查=是；是否可自动化=是；下次如何避免=写 env 前保存旧文件 hash/内容来源，失败自动恢复并再次验证 env/compose/actual images 一致，无法恢复则保持 blocked。
- P029：现象=route snapshot BACKFILL 启动时 Spring 无法实例化 `MesProRouteVersionSnapshotMigrationRunner`，该类同时存在生产构造函数和测试构造函数但生产构造函数无显式 `@Autowired`；阶段=publish-test 运行报告；影响=新 backend 镜像无法通过发布前独立运行报告，r4 判废；原因判断=多构造函数 Bean 注入契约缺失，Maven 测试只直接实例化类，未覆盖真实 Spring context；处理动作=不修改冻结 app worktree，不在本轮追加修复提交；要求后续独立修复后以新冻结提交/new releaseTag 重建；结果=当前发布阻塞；是否可前置检查=是；是否可自动化=是；下次如何避免=build-release 前运行 Spring context smoke 或扫描 `@Component`/`@Service` 多构造函数，缺唯一显式注入构造函数即 fail fast。

### 失败态远端只读证据

- `show-int-ruoyi-remote-status.ps1 -Component full -Json`：`status=running`，backend/frontend/onlyoffice running，backend/frontend HTTP 200，`currentReleaseTag=r4`（该字段来自 `.env`，不能代替实际镜像验证）。
- 远端 `.env`：`IMAGE_TAG=release-20260821-intmain-head-test-r260821h-r4`；compose config 解析 backend/frontend 也为 r4。
- `docker compose images` / `docker inspect`：backend 实际 `hotfix-20260814-route-submit-order-r1`，frontend 实际 `release-20260813-intmain-head-test-r260812b-r2`；两容器 running，无 Docker healthcheck；backend Actuator 返回 `{"status":"UP"}`，frontend `/` HTTP 200。
- frontend `/release-info.json`：仍为旧 releaseTag `release-20260813-intmain-head-test-r260812b-r2`，未包含本轮冻结提交说明。
- runtime-control `operations` API：r4 build operation SUCCESS、publish operation FAILED；`release-status` 的 `testCurrentReleaseTag=null`、`testCurrentReleaseNotes=null`，未执行页面版本验收。
- 证据结论：测试服旧容器仍可用，但 r4 未上线；`.env` 漂移未恢复，不能进入成功发布结论。正式服、备份服未访问，未执行 mark/promote。
- P030：现象=维护 release worktree 在构建/控制台运行期间生成未跟踪 `runtime/` 目录；阶段=构建与运行控制台；影响=worktree 不能保持 clean，不能直接作为后续发布输入或执行删除；原因判断=部分运行输出未固定写入 state-dir；处理动作=停止隔离控制台，保留本任务 worktree/runtime 供阻塞审计；结果=未扩大清理；是否可前置检查=是；是否可自动化=是；下次如何避免=构建后立即检测本任务生成目录，按绝对路径边界清理或改为统一 state-dir。
- P031：现象=48185 隔离控制台停止后无监听，48181 稳定端口也无监听；阶段=阻塞收尾；影响=未完成稳定控制台恢复，不能标记 completed；原因判断=失败发布按阻塞规则停止临时控制台，未在失败任务中扩大启动主工作区实例；处理动作=记录端口状态，不启动主工作区控制台或修改远端；结果=作为阻塞收尾条件保留；是否可前置检查=是；是否可自动化=是；下次如何避免=仅在发布成功进入 closeout 后恢复稳定控制台，并验证 PID/JAR/config/state/health。
-
## 2026-08-22 构造注入回归修复

BDD: route snapshot runner can start in the publish report -> Given `MesProRouteVersionSnapshotMigrationRunner` has both production and test constructors, When Spring starts the route snapshot migration report, Then the production constructor is selected and the context starts without `No default constructor found`.

RED: `mvn -pl yudao-module-mes -am -Dsurefire.failIfNoSpecifiedTests=false -Dtest=cn.iocoder.yudao.module.mes.service.pro.route.MesProRouteVersionSnapshotMigrationCommandTest#springContextShouldInstantiateRunnerWithAutowiredConstructor test` with `@Autowired` temporarily removed -> FAIL, `BeanCreationException ... No default constructor found`.

GREEN: the same Maven command with the production constructor annotated `@Autowired` -> PASS, target test `1/1`; full reactor through `yudao-module-mes` also PASS; `git diff --check` PASS.

- 修复 worktree：`D:\IntRuoyiWorktree\route-snapshot-autowired-fix`。
- 修复分支：`codex/20260821-route-snapshot-autowired-fix`。
- 实现提交：`c4d2c637bf1f2cea723876ee363f311b1128aaf4`，主题 `任务: 修复路由快照运行器构造注入`。
- 提交前置问题：detached HEAD、缺少 worktree port registry、共享 registry 存在无关 slot 31；切换任务分支并登记任务专用 slot 23 后提交钩子通过。
- 后续发布必须使用该提交创建全新 release worktree 和全新 releaseTag；不得复用 r260821h-r4。

## 2026-08-22 r260822a 新冻结输入与构建前门禁

- 新发布尝试标识：`r260822a`；计划 releaseTag：`release-20260822-intmain-head-test-r260822a-r1`，不复用已判废的 r260821h-r4。
- 维护主工作区：`D:\ProjectPackage\Int\IntRuoyiMaintance`，分支 `int_main`，HEAD=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`，工作区存在既有 modified/deleted/untracked 内容，未作为构建输入。
- app 主工作区：`E:\IntRuoyi`，分支 `int_main`，HEAD=`76ec0a38f9d00704ad05eaea7c0140dedb322044`，工作区存在既有 modified/untracked 内容，未作为构建输入；本轮 app 目标提交固定为已提交修复 `c4d2c637bf1f2cea723876ee363f311b1128aaf4`。
- 维护发布 worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260822a\m`，detached clean，HEAD=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`，主题=`任务: 修复build-release密钥导入`。
- app 发布 worktree：`D:\IntRuoyiWorktree\r260822a\a`，detached clean，HEAD=`c4d2c637bf1f2cea723876ee363f311b1128aaf4`，主题=`任务: 修复路由快照运行器构造注入`。
- 运行控制台配置目标：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260822a\m\config\runtime-control.local.yaml`；repo/frontend/ops/state 均指向本轮 worktree 或 task-owned state；test host=`172.30.30.58`；prod/backup access=false；production-write-enabled=false。
- GREEN: experience-preflight -> PASS，已重新核对本轮 releaseTag、目标提交、专用 worktree、测试服 host/remote 目录、仅测试范围、禁止 mark/promote、PowerShell/SSH 编码和失败态远端漂移，不执行正式服/备份服写入。
- GREEN: app-release-worktree -> PASS，前端依赖安装完成（1103 packages），关键 `vite`/`vue-tsc`/`cross-env` 检查与 `.modules.yaml pendingBuilds=[]` 通过；`pnpm build:test` PASS，输出 `Build successful. Please see dist-test directory`。
- 长过程复盘：app 前端依赖恢复耗时约 12 分钟，Vite test build 约 8 分钟；当前已完成新输入锁定和 app 前置构建，下一步构建维护控制台并启动隔离运行控制台。
- GREEN: maintenance-console-build-r260822a -> PASS，维护前端 typecheck/build PASS，Maven 3.9.16/JDK 21 可执行，Maven tests `26` run / `0` failures / `0` errors / `0` skipped，JAR=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260822a\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`，sha256=`a1699f12eac8ec6068c229b3a350f00ee54d7e54de422bbd7844ccbb64d41aab`。
- P034：维护控制台构建输出了 Java 编译器弃用 API 提示、Mockito 动态 agent 提示和 Vite chunk size warning；阶段=维护控制台构建；影响=本次构建未失败，但 warning 不得替代测试/运行态验收；原因判断=现有依赖/构建配置提示，非本次发布输入漂移；处理动作=记录并继续独立验证，不修改冻结代码；结果=26 项测试仍全部通过；可前置检查=是；可自动化=是；下次避免=构建日志扫描 warning 分类，区分阻断型和提示型，阻断型 fail fast。
- P035：维护控制台 Maven parity 测试在构建期间生成 task-owned `runtime/runtime-control-original-governance-parity-test` 文件；阶段=控制台构建；影响=worktree 暂时出现未跟踪文件，不能直接作为发布输入；原因判断=测试未完全使用隔离 state-dir；处理动作=构建后按绝对路径边界清理生成目录，随后复核 worktree clean；结果=待清理复核；可前置检查=是；可自动化=是；下次避免=控制台测试输出固定写入 state-dir，构建后强制 clean 断言。
- GREEN: remote-readonly-preflight-r260822a -> PASS，测试 host=`172.30.30.58`、remote app dir=`/opt/intruoyi/runtime` 可达，当前容器 running、backend/frontend HTTP 200；观察到失败轮次遗留 `.env IMAGE_TAG=release-20260821-intmain-head-test-r260821h-r4`，本轮将使用全新 releaseTag，不做猜测性回滚或手工状态表修改。
- GREEN: build-release-preview-r260822a -> PASS，控制台预览仅包含 `action=build-release`、`publishScope=code-only`、`-SkipDatabaseSync`、`-SkipMinioSync`，输入后端/前端均指向本轮 release worktree；未包含 publish-test、mark-tested、promote-prod、promote-backup。
- GREEN: experience-preflight -> PASS，执行 build-release 前再次确认远端失败态已只读记录、单一 releaseTag、目标提交和 package provenance 门禁均已准备；下一高风险动作仍仅允许测试服 publish-test。
- P036：现象=r260822a-r1 build-release 在迁移策略门禁后失败，隔离控制台日志为 `Missing command: mvn`；阶段=build-release 环境前置；影响=r1 判废，未生成可发布 manifest/package，未执行 publish-test；原因判断=本轮控制台启动进程继承的 PATH 未包含已验证的 Maven 3.9.16 bin；处理动作=停止隔离控制台，记录失败 operation，按经验门禁在重启前显式加入 Maven bin，并使用新 releaseTag r2 重试；结果=待重试；可前置检查=是；可自动化=是；下次避免=控制台启动前必须在同一进程环境执行 `Get-Command mvn`、`mvn -version` 并记录结果。
- 长过程复盘：r1 operation 很快在 migration policy gate 后失败；耗时点是失败前的 NAS/迁移前置探针连接，下一步已将 Maven PATH 门禁前移到控制台启动环境并使用新 releaseTag。
- GREEN: build-release-r260822a-r2 -> PASS，operation=`op-2026-08-22T033833931534300Z-c3389b33-a5b1-44e0-9b17-e63dc07cce7e` SUCCESS；package=`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260822-intmain-head-test-r260822a-r2`；manifest validator PASS；app sourceRepos backend/admin-frontend 均为 commit `c4d2c637bf1f2cea723876ee363f311b1128aaf4`、`dirty=false`；changeSet summary=`任务: 修复路由快照运行器构造注入`；legacy gitCommit 同一提交。
- GREEN: package-artifact-r260822a-r2 -> PASS，镜像 tar bytes=`706557440`，sha256=`aa2c8e5d2b8748798f2c6f2966806e7c91fb5bedc115a103bddd6c22826ddb68`；backend image tag=`intruoyi-backend:release-20260822-intmain-head-test-r260822a-r2` digest=`sha256:b030a2bebd4a9c483e2442862751bd1b19b56dcefab17bd06a4b534d017ff62e`；frontend image tag=`intruoyi-frontend:release-20260822-intmain-head-test-r260822a-r2` digest=`sha256:0bacb03d3b53e942c484c7df7cd61e5cb90360f35f1a62f2c64cd9b4ea0d5357`。
- GREEN: version-and-change-set-r260822a-r2 -> PASS，frontend package version=`2026.04-snapshot`，maintenance JAR version=`2026.06-SNAPSHOT`；发布版本标识使用 manifest/release-info 的 `releaseTag/packageId=release-20260822-intmain-head-test-r260822a-r2`，与冻结提交和变更说明一致；未依赖未定义的 `manifest.version` 字段。
- GREEN: release-worktree-clean-r260822a -> PASS，维护和 app 发布 worktree 在 build-release 完成后均仅显示 detached HEAD，无未提交改动或未跟踪构建输入。
- P037：manifest v1 顶层 `gitCommit` 为空且不定义通用 `version` 字段；阶段=manifest/版本验收；影响=若按旧字段读取会误判来源或版本缺失；原因判断=当前 schema 使用 `sourceRepos[*].commit` 和 `releaseTag/packageId` 作为权威字段，legacy manifest 承载 gitCommit；处理动作=按 schema 读取并记录三处一致性，未手工改包；结果=通过，不阻断 r2；可前置检查=是；可自动化=是；下次避免=validator/验收脚本明确字段契约，禁止自行推断未定义顶层字段。
- GREEN: experience-preflight -> PASS，publish-test 前已再次确认单一 releaseTag、manifest/sourceRepos/dirty、版本/变更说明、test host/remote dir、当前旧 env 漂移、无运行中 operation；以下高风险动作仅执行 test `publish-test`，不执行 mark-tested/promote-prod/promote-backup。
- 长过程复盘（2026-08-22 12:02）：当前进度=publish-test operation RUNNING；已完成包上传（约 706 MB 镜像 tar）、远端 smoke 文件同步和 required SQL 逐文件同步，日志持续推进；阻塞点=无；耗时原因=发布脚本按文件串行 scp，required SQL 约 500 个文件；下一步=等待迁移登记、route snapshot BACKFILL、容器切换和 operation 最终状态，完成后只读核对真实运行态。
- 长过程复盘（2026-08-22 12:13）：当前进度=publish-test operation 仍 RUNNING；required SQL 登记已推进到 `20260613_erp_production_material_list_menu` 附近，远端 ssh 进程仍活跃；阻塞点=无，未执行重复操作；耗时原因=每条迁移登记通过独立 SSH/MySQL stdin 串行执行；下一步=等待登记阶段完成并进入 route snapshot BACKFILL/容器切换。

## 2026-08-22 r260822a-r2 publish-test 失败收束

- GREEN: route-snapshot-fix-regression -> PASS，提交 `c4d2c637bf1f2cea723876ee363f311b1128aaf4` 的 `@Autowired` 构造注入修复已通过 Spring `ApplicationContextRunner` 回归测试；本轮 app release worktree 使用该已提交修复，不追逐后续提交。
- GREEN: publish-test-scope-r260822a-r2 -> PASS，唯一高风险动作是 `action=publish-test`、`environment=test`、`releaseTag=release-20260822-intmain-head-test-r260822a-r2`；未执行 `mark-tested`、`promote-prod`、`promote-backup`，正式服/备份服未写入。
- 长过程复盘（2026-08-22 12:13-12:45）：当前进度=required SQL 串行登记后进入 route snapshot BACKFILL；已完成=706 MB 镜像包上传、smoke 文件同步、required SQL 同步/登记；阻塞点=BACKFILL 报告 BLOCKED/882，临时 runner 未自行退出，operation API 状态未收束；耗时原因=逐文件 scp、逐迁移 SSH/MySQL 和独立 backend runner；下一步=停止临时 runner、固定失败证据、脱敏日志、标记任务 blocked。
- BLOCKER: route-snapshot-backfill-r260822a-r2 -> `intruoyi-runtime-backend-run-5b246e6c431d` 生成报告 `status=BLOCKED`、`blockerCount=882`；该报告未满足脚本要求的 `status=READY` 与 `blockerCount=0`，不能继续到容器切换。
- P038: 现象=route snapshot BACKFILL 报告存在 882 个 blocker；阶段=publish-test 运行报告；影响=发布未完成、目标镜像未上线；原因判断=测试服真实路由快照身份数据前置状态仍不满足迁移门禁；处理动作=停止本次发布，清理任务创建的临时 runner，不修改业务数据/ledger，不重试失败 releaseTag；结果=阻塞。
- P039: 现象=报告生成后临时 runner 仍保持 running，`docker compose run --rm` 未自然收束；阶段=publish-test 失败收束；影响=远端临时资源残留并拖延 operation 终态；原因判断=失败/阻塞路径的 runner 生命周期与脚本等待边界不完整；处理动作=只删除任务创建的 runner，复核 live backend/frontend 未被删除或停止；结果=runner 清理成功，live 容器仍为旧版本。
- P040: 现象=operation `op-2026-08-22T035621436028400Z-55335b7f-e740-4d0f-a9d1-a85f875648fa` API 和 state JSON 仍为 `RUNNING`，不满足最终 SUCCESS/FAILED；阶段=操作状态收束；影响=不能形成成功证据，控制台可能阻塞后续动作；原因判断=命令执行器先持续读取 stdout，超时检查在流关闭后才执行，异常/强制清理没有可靠终态；处理动作=不手工改为 SUCCESS、不重复提交，保留状态证据并停止本轮；结果=阻塞，需修复控制台状态机/执行器后用新 releaseTag 重试。
- P041: 现象=原始 publish log 曾写入 MySQL `-p` 命令参数；阶段=required SQL/迁移登记；影响=raw log 不可提交或长期保存；原因判断=logger 未统一执行 secret redaction；处理动作=原地以 UTF-8 重写脱敏日志，保留只读摘要和 scan 结果，不复制 raw log；结果=脱敏完成，后续 logger 修复仍为必需项。
- P042: 现象=逐文件 scp 与逐迁移 SSH/MySQL 登记使 operation 长时间停留“命令已提交到本机执行队列”；阶段=长过程发布；影响=耗时和误判风险增加；原因判断=发布脚本缺少阶段计数/可观测 summary，且关键动作串行；处理动作=固定间隔读取 operation、日志 tail、远端容器和 live tag，不重复操作；结果=确认前期在推进，最终在 BACKFILL 门禁阻塞；下次前置进度计数和真实无进展超时。
- P043: 现象=远端 `.env IMAGE_TAG`/Compose 目标为 r2，但 live backend/frontend 实际 tag 仍为旧版本；阶段=publish-test 失败收束；影响=env、compose、actual image 漂移，不能成功验收或重试；原因判断=脚本在 BACKFILL 前先写 `.env`，失败路径没有证明旧 env 自动恢复；处理动作=只读记录 env/compose/actual image/container，未猜测回滚、未改 ledger/lock、未重启 live 容器；结果=阻塞，r2 判废。
- GREEN: failure-state-live-containers-r260822a-r2 -> PASS，临时 runner 清理后远端 live backend=`intruoyi-backend:hotfix-20260814-route-submit-order-r1`、live frontend=`intruoyi-frontend:release-20260813-intmain-head-test-r260812b-r2`，均仍 running；未将旧容器 HTTP/health 200 误判为本轮发布成功。
- GREEN: publish-log-redaction-r260822a-r2 -> PASS，publish log 已用 UTF-8 无 BOM 重写脱敏，未将 raw secret-bearing log 写入任务证据；日志中的 OpenSSH `IO is still pending on closed socket` 作为 carrier warning 单独记录，不替代业务结果。
- GREEN: isolated-console-stop-r260822a -> PASS，任务启动的 48186 维护控制台已停止且端口无监听；由于发布失败，未扩大范围启动主工作区 48181，稳定控制台恢复仍属于 blocked closeout 条件。
- 结论：r260822a-r2 失败并判废；任务 `blocked`。不得复用该 releaseTag，不得执行 mark-tested/promote-prod/promote-backup，不得手工改 migration ledger、release lock 或 live tenant data。

## 2026-08-22 继续执行：route snapshot BLOCKED/882 只读根因诊断

- 用户继续授权本任务；本阶段只读复核，不重新获取 Git 后续提交，不重试 `release-20260822-intmain-head-test-r260822a-r2`，不修改测试服业务数据、migration ledger、release lock 或远端 `.env`。
- GREEN: frozen-input-recheck -> PASS，继续使用维护 HEAD=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`、app 修复提交=`c4d2c637bf1f2cea723876ee363f311b1128aaf4`、专用 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260822a\m` / `D:\IntRuoyiWorktree\r260822a\a`；未追逐后续提交。
- GREEN: route-snapshot-report-evidence -> PASS，远端报告 `/var/lib/docker/intruoyi-releases/release-20260822-intmain-head-test-r260822a-r2/runtime-reports/route-snapshot-identity-backfill.json` 只读复制到 `doc\tasks\20260821-test-only-head-release\evidence\route-snapshot-identity-backfill-r260822a-r2.json`；`status=BLOCKED`、`scannedCount=47`、`updatedCount=0`、`blockerCount=882`。
- GREEN: route-snapshot-blocker-classification -> PASS，分类为 `FLOW_NODES_MISSING=8`、`ROUTE_ID_MISSING=2`、`PROCESS_ID_INVALID=436`、`PRODUCT_BOM_IDENTITY_INVALID=436`；未读取或保存密码、token、私钥等凭据。
- GREEN: route-snapshot-db-readonly-probe -> PASS，按真实表结构核对 `mes_pro_route_version` 共 47 条；租户 1（芋道源码）46 条，租户 122（测试租户）1 条；`route_snapshot_sha256` 与 `route_snapshot_format_version` 两列 47/47 均为空；未执行任何 INSERT/UPDATE/DELETE/DDL。
- GREEN: route-snapshot-sample-readonly-probe -> PASS，版本 `id=110` 的快照包含 26 个 BOM，首条 `processId=0`；当前 `mes_pro_route_product_bom` 对应路线物理表的 `process_id` 为正数，证明不能把当前投影当作历史快照修复源。
- BDD: 历史快照身份门禁必须阻止不可证明的迁移 -> Given 测试服存在缺少流程节点、routeId 或正式 BOM processId 的历史快照 / When publish-test 运行 BACKFILL / Then 报告必须为 `BLOCKED` 且发布不得切换镜像、不得绕过 NOT NULL enforcement。
- BLOCKER: route-snapshot-data-governance -> 882 个 blocker 不是 runner 启动缺陷，而是测试服历史数据不满足当前严格快照契约；其中 46 条属于芋道源码租户，当前规则禁止修改该租户数据，且迁移注释明确禁止从当前路线投影推断不可变快照身份；没有合法数据治理方案前不能继续发布。
- 长过程复盘（2026-08-22 继续）：当前进度=已完成报告、数据库结构、租户分布和样本字段只读核查；已完成=阻塞分类与数据根因确认；阻塞点=历史快照修复授权/正式方案缺失；耗时原因=先后处理远端工具缺失、PowerShell/SSH SQL 引号、MySQL JSON binary 路径探针错误；下一步=保持任务 blocked，等待正式数据治理方案或授权，不执行降级发布。
- P044: 现象=测试服没有 `jq`；阶段=只读报告汇总；影响=首个聚合探针失败，未影响业务；原因判断=运行镜像未安装 jq；处理动作=改用远端已有 python3 标准库解析同一报告；结果=摘要/分类复核 PASS；可前置检查=是；可自动化=是；下次避免=发布诊断工具清单固定并在远端执行前检查版本。
- P045: 现象=第一次 MySQL 聚合探针因 PowerShell/SSH 引号层级报 SQL 语法错误；阶段=只读数据库核查；影响=该次探针失败，无写入；原因判断=内联 SQL 不适合多层引号；处理动作=改用 UTF-8 SQL 文件 stdin 载体并重跑；结果=结构、租户分布和身份列状态 PASS；可前置检查=是；可自动化=是；下次避免=多行/复杂 SQL 固定走 UTF-8 文件载体。
- P046: 现象=第一次 JSON 路径探针因 `CHAR(36)` 返回 binary，MySQL 报 `ERROR 3144`；阶段=只读快照字段核查；影响=该次探针失败，无写入；原因判断=JSON_EXTRACT 路径参数类型不符合 MySQL 要求；处理动作=SQL 文件中使用字面 `$.` 路径，避免 shell 展开；结果=样本结构 PASS；可前置检查=是；可自动化=是；下次避免=JSON 路径探针加入类型校验和最小样例。
- P047: 现象=BACKFILL 真实报告 `BLOCKED/882`；阶段=publish-test 前置运行报告；影响=不能进入容器切换/健康/页面/控制台验收；原因判断=历史 route snapshot 结构和身份不满足门禁；处理动作=分类核验，禁止数据写入、门禁绕过和同 tag 重试；结果=根因确认，任务 blocked；可前置检查=是；可自动化=是；下次避免=远端写入前单独运行 BACKFILL/READINESS 并按租户与 reasonCode fail fast。
- P048: 现象=终端直接输出中文租户名乱码；阶段=租户身份核对；影响=乱码不能作为证据；原因判断=SSH/终端编码链路不稳定；处理动作=查询 `HEX(name)` 后按 UTF-8 解码；结果=确认租户 1=芋道源码、122=测试租户；可前置检查=是；可自动化=是；下次避免=中文数据库证据写 UTF-8 文件或查 HEX。
- GREEN: forbidden-actions-recheck -> PASS，继续确认未执行 `mark-tested`、`promote-prod`、`promote-backup`，未访问正式服/备份服，未修改任何租户数据。
- 结论：r260822a-r2 仍为 NO-GO；任务状态保持 `blocked`；发布 worktree、失败报告和任务证据保留，不执行 task-closeout 删除。

## 2026-08-22 继续执行：冻结输入与测试服失败态复核

- 本次继续未重新获取 Git 后续提交，未重试 `release-20260822-intmain-head-test-r260822a-r2`，未执行任何远端写入。
- GREEN: frozen-worktree-current-state-recheck -> PASS，维护 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260822a\m` 为 detached clean、HEAD=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`；app worktree `D:\IntRuoyiWorktree\r260822a\a` 为 detached clean、HEAD=`c4d2c637bf1f2cea723876ee363f311b1128aaf4`。
- GREEN: route-snapshot-evidence-current-state-recheck -> PASS，本地保存的报告仍为 `status=BLOCKED`、`blockerCount=882`、`scannedCount=47`、`updatedCount=0`。
- GREEN: test-runtime-readonly-current-state-recheck -> PASS，2026-08-22 13:45（Asia/Shanghai）只读核对测试服：远端 `.env` 为 `IMAGE_TAG=release-20260822-intmain-head-test-r260822a-r2`；实际 `intruoyi-backend` 仍为 `intruoyi-backend:hotfix-20260814-route-submit-order-r1`，实际 `intruoyi-frontend` 仍为 `intruoyi-frontend:release-20260813-intmain-head-test-r260812b-r2`，两者仍运行；任务创建的 route runner 未出现在 `docker ps -a`。该状态继续证明 env/实际镜像漂移，不能作为 r2 成功证据。
- 复核范围：仅读取远端 `.env` 和 `docker ps -a`，未读取或写入密码、token、私钥，未重启/删除 live 容器，未访问正式服或备份服。
- P049：现象=本次首次远程只读状态探针因 PowerShell 多层引号解析失败，报 `ParserError: Missing argument in parameter list`；阶段=失败态复核；影响=该探针没有形成远端证据，复核短暂延迟，无远端副作用；原因判断=将 Python 内联代码、SSH 双引号和 PowerShell 字符串叠加，命令边界不稳定；处理动作=改用不含内联 Python 的简单 SSH 只读命令重新核对 `.env`、全部容器和临时 runner；结果=有效复核通过，未执行写操作；是否可前置检查=是；是否可自动化=是；下次如何避免=复杂远端诊断统一使用 UTF-8 文件载体或单一脚本，执行前做语法/退出码检查，避免多层内联引号。
- 载体告警：有效复核命令末尾再次出现 OpenSSH `IO is still pending on closed socket`，按 P041 作为传输载体告警记录，不改变已取得的远端输出，也不替代业务结果。
- 结论：r260822a-r2 仍为 `NO-GO / blocked`；未满足 operation SUCCESS、目标镜像实际运行、前端页面和运行控制台版本验收，不执行 closeout 删除或 `completed` 标记。

## 2026-08-22 继续执行：route snapshot blocker 租户精确关联

- GREEN: route-snapshot-tenant-mapping -> PASS，使用远端只读 SQL `SELECT id, tenant_id FROM mes_pro_route_version ORDER BY id` 获取 47 条真实映射，再在本地将报告 882 条 blocker 按 `routeVersionId` 关联；SSH 退出码=`0`，映射成功=`47/47`，未映射=`0`，未执行 INSERT/UPDATE/DELETE/DDL。
- 精确结果：tenant 1（芋道源码）`FLOW_NODES_MISSING=7`、`ROUTE_ID_MISSING=2`、`PROCESS_ID_INVALID=436`、`PRODUCT_BOM_IDENTITY_INVALID=436`，合计 `881` 个 blocker；tenant 122（测试租户）`FLOW_NODES_MISSING=1`，合计 `1` 个 blocker；总数=`882`。
- 代码契约复核：冻结 app worktree 中 `MesProRouteVersionSnapshotHashMigrationService.backfillAll()` 通过 `selectAllPhysicalRows()` 并在 `TenantUtils.executeIgnore` 中验证全量物理行；`20260812_mes_route_version_snapshot_identity_enforce.sql` 明确要求全表 blocker count 为 0，且迁移只做最终检查、不修复数据。
- P050：现象=报告 JSON 只有 `routeVersionId/routeId/versionNo/reasonCode/detail`，不包含 `tenantId`，仅看报告总数不能直接证明 blocker 租户范围；阶段=route snapshot 根因证据补强；影响=若不关联真实表，容易把“46 条源租户记录/1 条测试租户记录”误写成 blocker 逐项分布；原因判断=运行报告 schema 未输出租户字段，而服务按物理行全租户扫描；处理动作=只读查询真实 `mes_pro_route_version.id -> tenant_id` 并本地关联，保留脱敏计数；结果=882 条全部映射，确认 source tenant=881、test tenant=1；是否可前置检查=是；是否可自动化=是；下次如何避免=报告直接输出并校验 tenantId，发布前按 tenant/reasonCode 聚合，租户字段缺失即 fail fast。
- 结论：全租户门禁仍失败；不能只修测试租户 122，也不能排除受保护的 tenant 1。需要正式授权的数据治理方案覆盖受保护租户，且必须先解决全量历史快照身份/结构问题，再以新提交、新 worktree、新 releaseTag 重建发布。

## 2026-08-22 授权后的测试服历史快照修复预检

- GREEN: experience-preflight -> PASS，已再次核对仅测试服动作边界、目标 host=`172.30.30.58`、远端运行目录、当前冻结 releaseTag、禁止正式/备份动作、以及本轮修复仅限单一 UTF-8 SQL 文件；用户已明确授权允许对测试服历史 route snapshot 做受控修复。
- 计划写入路径：先生成 task-owned 修复 SQL，仅更新测试服 `mes_pro_route_version` 的历史 snapshot JSON 并清空 identity 列，再通过现有 `apply-test-db-sql.ps1` 进入远端执行；不直接改其他表，不触碰正式服或备份服。
- 当前失败态不变：r260822a-r2 仍判废，任何成功判断都必须以新的 BACKFILL/READINESS 与真实运行态复验为准。

## 2026-08-22 授权后的历史快照修复执行与门禁复核

- 用户授权边界：仅允许测试服 `172.30.30.58` 的受控历史 route snapshot 修复和验证；正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup` 仍禁止。
- GREEN: route-snapshot-repair-sql-preflight -> PASS，task-owned SQL=`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260821-test-only-head-release\evidence\route-snapshot-repair-r260822a-r2.sql`，SHA-256=`06d8e6dfcbc1043625d9d50067c6bb84bd6b33a547eb12b1b93dea0f6b5dd5ae`；仅包含 27 条 `mes_pro_route_version` 快照更新，未包含 `DROP DATABASE` 或凭据文本。
- GREEN: route-snapshot-repair-apply -> PASS，按 `E:\IntRuoyi\IntRuoyiBackend\script\deploy\apply-test-db-sql.ps1` 执行测试服数据库写入，目标 host=`172.30.30.58`、数据库=`ruoyi-vue-pro`、远端运行目录=`/opt/intruoyi/runtime`；脚本返回 `APPLY_TEST_DB_SQL_OK`。OpenSSH `close - IO is still pending on closed socket` 仅作为传输载体告警记录，不改变 SQL 成功结论。
- GREEN: route-snapshot-repair-db-postcheck -> PASS，远端只读查询结果为 `total=47`、`snapshot_nonnull=47`、`sha_nonnull=0`、`format_nonnull=0`、`snapshot_null=0`、`identity_null_rows=47`；未执行额外数据库写入。
- 下一步高风险动作：使用测试服当前 `/opt/intruoyi/runtime` 的 compose 与 r2 backend 镜像，仅执行官方发布脚本同源的 route snapshot `BACKFILL` runner，再执行 `READINESS` runner；两个报告必须 `READY` 且 `blockerCount=0`，否则立即阻断，不重建旧 r2、不切换 live 容器。

## 2026-08-22 授权后正式 BACKFILL 复核与阻塞

- 用户授权边界再次确认：仅测试服 `172.30.30.58`；不访问或写入正式服/备份服，不执行 `mark-tested`、`promote-prod`、`promote-backup`。本轮仍固定维护 HEAD=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`、app HEAD=`c4d2c637bf1f2cea723876ee363f311b1128aaf4`，不重新获取 Git 后续提交。
- `GREEN: experience-preflight -> PASS`，已核对本次测试服数据修复的目标、范围、SQL 文件、远端目录、task-owned runner 清理边界和禁止动作；未执行新 build-release 或 publish-test。
- `GREEN: route-snapshot-repair-backfill-evidence -> PASS`，按冻结维护发布脚本同源命令对测试服当前 r2 backend 执行 `mode=BACKFILL`；报告已复制至 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260821-test-only-head-release\evidence\route-snapshot-identity-backfill-authorized-r260822a.json`。
- `BLOCKER: route-snapshot-backfill-authorized-r260822a-r2 -> status=BLOCKED`，报告 `scannedCount=47`、`updatedCount=0`、`blockerCount=8`；8 条均为 `ROUTE_PROCESS_UNRESOLVED`，集中在 `routeVersionId=3`、`routeId=900025`、`configSnapshots.scheduleConfigs[*].routeProcessId`，实际旧 ID 为 `900124`、`900125`、`900126`、`900127`，每个因两轮校验各报告一次。
- 只读源表核查结果：`mes_pro_route_schedule_config` 的真实字段为 `route_version_id`、`route_process_id` 等；`route_version_id=3` 的相关物理配置仍引用 `900124-900127`。`mes_pro_route_process` 当前有效行和含逻辑删除行均没有这些 ID；当前 `route_id=900025` 只有另一组新 `routeProcessId`，未找到可审计的旧新映射来源。
- 冻结代码契约复核：`MesProRouteSnapshotCanonicalizer` 会对 `scheduleConfigs` 的 `routeProcessId` 做严格解析；生命周期服务要求快照 routeProcessId 集合与正式 projection 完全一致；当前快照构造逻辑按 `routeVersionId` 直接带入排产配置。代码、迁移脚本和任务证据中没有正式的旧 ID 恢复映射，不能按排序盲映射、删除配置、置空配置或静默从当前路线推断历史身份。
- `BDD: authorized route snapshot repair must preserve formal identities -> Given test-server historical route snapshots contain orphan scheduleConfig routeProcessId references, When the official BACKFILL gate runs after an authorized snapshot repair, Then unresolved references remain BLOCKED and build/publish must stop until an auditable mapping source exists.`
- 长过程复盘（2026-08-22 授权后）：当前进度=修复 SQL 已执行、数据库后置核对通过、正式 BACKFILL 已完成；已完成=27 条快照修复、47/47 快照非空、报告证据复制、task-owned runner 清理；阻塞点=孤儿排产配置引用 8 条报告 blocker；耗时原因=独立 runner 未自然退出、远端 SSH/容器收束等待和多次只读探针命令边界调整；下一步=等待正式映射/修复方案，未满足前不重建、不发布。
- P051：现象=授权快照修复后 BACKFILL blocker 从 `882` 降至 `8`，仍为 `BLOCKED`；阶段=测试服数据修复后正式门禁；影响=不能进入新构建、容器切换、健康/页面/控制台验收；原因判断=修复 SQL 仅重建了可从当前路线完整证明的快照部分，4 个排产配置仍引用不存在的历史 routeProcessId；处理动作=保留报告并停止后续发布，不用旧 tag 重试；结果=阻塞；是否可前置检查=是；是否可自动化=是；下次如何避免=修复后必须强制运行正式 BACKFILL/READINESS，并按 reasonCode、routeVersionId 和引用来源归零后才放行。
- P052：现象=快照 `routeVersionId=3` 的 `scheduleConfigs` 引用 `900124-900127`，真实 `mes_pro_route_process` 无对应行；阶段=数据修复根因核查；影响=无法证明旧配置应映射到哪组新工序，任何盲映射都可能改变历史业务含义；原因判断=路线重建后物理工序 ID 已变化，排产配置表保留了孤儿外键语义，但未保留可审计映射；处理动作=只读核对真实表结构、有效/逻辑删除行和当前路线工序，未更新 `mes_pro_route_schedule_config`；结果=正式数据来源缺失，fail fast；是否可前置检查=是；是否可自动化=是；下次如何避免=发布前增加孤儿引用扫描和旧新 routeProcessId 映射完整性门禁，缺映射即拒绝数据修复和发布。
- P053：现象=正式 BACKFILL runner 生成报告后未自行退出，清理 task-owned 容器 `intruoyi-runtime-backend-run-24102f6a8ab9` 后本地 SSH 进程以退出码 `137` 收束，并伴随 OpenSSH `IO is still pending on closed socket`；阶段=诊断 runner 收束；影响=增加等待和误判风险，但未停止或删除 live backend/frontend；原因判断=compose run/SSH 流关闭与强制清理之间缺少明确终止契约；处理动作=只清理任务创建的 runner，随后只读确认 live 容器未被任务删除；结果=临时资源已清理，业务运行态未被触碰；是否可前置检查=是；是否可自动化=是；下次如何避免=runner 必须有可验证的超时、终态报告、退出码和容器清理协议，carrier warning 单独记录。
- P054：现象=多次只读命令先使用不存在的 `D:\ProjectPackage\Int\IntRuoyiWorktrees\...` 路径，实际维护 worktree 是 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260822a\m`；阶段=worktree/证据探针；影响=命令失败和定位延迟，无文件或 Git 副作用；原因判断=项目规则中的根目录层级与临时命令路径混淆；处理动作=停止错误路径操作，改用绝对路径并重新核对 HEAD/clean；结果=正确 worktree 已复核；是否可前置检查=是；是否可自动化=是；下次如何避免=启动时生成并锁定绝对路径清单，所有命令只接受清单中的路径。
- P055：现象=PowerShell 将 `foreach (...) | Format-Table` 解析为空管道，报 `An empty pipe element is not allowed`；阶段=worktree 批量只读检查；影响=该检查未执行，无业务副作用；原因判断=PowerShell 语句块不能直接作为管道左值；处理动作=改为先赋值数组再格式化输出；结果=检查成功；是否可前置检查=是；是否可自动化=是；下次如何避免=复杂 PowerShell 先保存为 UTF-8 脚本并执行语法/退出码检查。
- P056：现象=远端报告探针叠加 PowerShell、SSH、Python 和嵌套 `$report` 引号时报 `ParserError: Unexpected token`；阶段=BACKFILL 证据读取；影响=首次探针未执行远端命令，无远端副作用；原因判断=多层内联脚本边界不稳定；处理动作=改用简单 `head`/关键词探针并重新复制报告；结果=证据取得；是否可前置检查=是；是否可自动化=是；下次如何避免=复杂远端脚本固定使用 task-owned UTF-8 文件载体，禁止多层内联代码。
- P057：现象=第一次排产配置 SQL 假定 `mes_pro_route_schedule_config.route_id`，MySQL 返回 `ERROR 1054 Unknown column 'route_id'`；阶段=只读表结构核查；影响=该 SQL 未写入数据，但延迟根因确认；原因判断=按旧/推断字段编写查询，未先以 `DESCRIBE` 为准；处理动作=先读取真实表结构，改用 `route_version_id`、`route_process_id`；结果=正确字段查询成功；是否可前置检查=是；是否可自动化=是；下次如何避免=任何 MES SQL 先执行并保存 `DESCRIBE`/`SHOW CREATE TABLE` 证据，字段不符立即停止。
- P058：现象=第二次 route process SQL 假定 `mes_pro_route_process.route_version_id`，MySQL 返回 `ERROR 1054 Unknown column 'route_version_id'`；阶段=旧新 routeProcessId 映射核查；影响=该 SQL 未写入数据；原因判断=混淆路线版本与路线工序物理表契约；处理动作=改按真实 `mes_pro_route_process(id, route_id, process_id, sort, deleted)` 查询；结果=确认旧 ID 无有效/逻辑删除来源；是否可前置检查=是；是否可自动化=是；下次如何避免=将表字段契约纳入发布诊断脚本，禁止凭 DO 类名或历史记忆推断字段。
- P059：现象=一次宽泛读取 `runtime-control.local.yaml` 的调试命令把 secret-bearing 配置字段输出到终端；阶段=发布配置排障；影响=原始终端输出不适合作为长期证据，存在凭据暴露风险；原因判断=配置读取未使用非敏感 allowlist；处理动作=不复制、不提交原始输出，后续只记录 host/path/access-enabled 等脱敏摘要；结果=任务文档和请求日志未保存明文凭据；是否可前置检查=是；是否可自动化=是；下次如何避免=配置读取默认字段白名单，secret 字段只输出存在性和哈希/脱敏状态，secret scan 命中即 fail fast。
- P060：现象=只读搜索假定冻结 app 仓存在 `yudao-module-mes/src/main/resources/db/migration`，PowerShell 返回路径不存在；阶段=正式修复来源搜索；影响=该搜索未取得结果，无代码或服务器副作用；原因判断=迁移文件实际位于其他项目路径/脚本目录，未先列目录；处理动作=停止该错误路径，改在已确认的 `sql/mysql`、Java migration service 和 docs 范围搜索；结果=未发现正式 routeProcessId 修复映射；是否可前置检查=是；是否可自动化=是；下次如何避免=先用 `rg --files` 确认目录，再执行限定搜索。
- P061：现象=修复元数据 `route-snapshot-repair-r260822a-r2.json` 的 `generatedAt` 为未来时间 `2026-08-23T00:48:03.685692+08:00`，与本次当前日期 `2026-08-22` 的任务时间线不一致；阶段=证据时间与文档一致性；影响=不能把该字段当作可靠的当前时间证明，但不改变 SQL hash、远端报告和数据库结果；原因判断=本机/生成脚本时钟与任务当前日期存在不一致；处理动作=保留原始元数据不篡改，改以远端报告时间和命令结果作为业务证据，并记录时钟差异；结果=非发布成功门禁 blocker，但证据时间可信度降级；是否可前置检查=是；是否可自动化=是；下次如何避免=生成证据前校验本机时间与时区，时间异常即阻止生成长期证据并提示修正。
- 结论：当前仍为 `NO-GO / blocked`。剩余 8 个 blocker 没有正式、可审计的来源映射；不得重建、不发布、不跳过 BACKFILL/READINESS，不删除本任务发布 worktree。

## 2026-08-22 历史备份表只读证据补充

- GREEN: route-snapshot-orphan-history-readonly -> PASS，仅读取测试库历史备份表 `m3syncbk_20260731025047_schedproc`、`m3syncbk_20260731025254_schedproc`、`m3syncbk_20260731025525_schedproc`，三份结果一致；未执行 INSERT/UPDATE/DELETE/DDL，未访问正式服或备份服。
- 历史证据：旧 `routeProcessId=900124/900125/900126/900127` 分别对应历史 process `900331/900333/900370/900371`，旧工序编码为 `B010/B030/PROC-XLSX-00001/PROC-XLSX-00002`，名称分别为“吹球囊成型”“球囊裁剪”“外管拉伸2”“内管拉伸2”，历史排产配置 ID 为 `203/204/205/206`；证据文件为 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260821-test-only-head-release\evidence\route-snapshot-orphan-route-process-history-r260822a.json`。
- 当前只读对照：当前路线 `routeId=900025` 共 23 个工序，前四个新 `routeProcessId` 为 `926785/926786/926787/926788`，对应 process `922894/922895/922896/922897`，编码已变为 `Z2630/Z3710/Z2775/Z2772`；历史与当前 ID、编码均不同，仅名称存在重合。
- 结论：历史备份表只能证明旧身份和历史配置存在，未提供旧 `routeProcessId` 到当前工序的正式、可审计映射；名称或排序相似不能作为映射依据。证据结论继续为 `BLOCKED`，不得盲映射、删除/置空 schedule config 或从当前路线投影推断历史身份。
- P062：现象=三份历史备份表均能查到旧 routeProcess/process/config 身份，但没有旧 ID 到当前 ID 的映射字段或正式转换记录；阶段=历史快照修复来源核查；影响=无法安全修复剩余 8 条 `ROUTE_PROCESS_UNRESOLVED` blocker；原因判断=备份表保留历史快照，不承担路线重建后的身份转换契约；处理动作=生成只读历史证据 JSON，明确 `mappingSourceFound=false`，停止后续写入和发布；结果=阻塞条件被证实；是否可前置检查=是；是否可自动化=是；下次如何避免=修复前必须要求正式 mapping source、唯一性和覆盖率验证，缺失即 fail fast。
- P063：现象=旧工序与当前工序名称部分相同，但当前 ID、编码和路线工序集合已变化，当前路线共 23 个工序；阶段=旧新身份关联判断；影响=按名称、顺序或相似编码猜测会改变历史业务含义并违反不可变快照契约；原因判断=历史路线重建产生新物理身份，缺少审计关联；处理动作=不执行任何猜测性 UPDATE，不删除或置空配置，保留对照证据；结果=安全阻断；是否可前置检查=是；是否可自动化=是；下次如何避免=发布诊断脚本必须拒绝非正式映射，只接受显式旧新 ID 映射及人工批准的修复设计。
- P064：现象=一次直接 `docker exec mysql` 只读探针未传入 `MYSQL_PWD`，返回 `ERROR 1045 Access denied ... using password: NO`；阶段=历史源表只读核查；影响=首次查询未取得证据，无数据库写入或运行态副作用；原因判断=绕过测试运行时 `.env` 的受控凭据注入路径；处理动作=停止该命令，改用测试运行时环境变量注入并重新执行同一只读聚合查询，未记录凭据值；结果=历史证据查询成功；是否可前置检查=是；是否可自动化=是；下次如何避免=所有远端 MySQL 探针先验证受控凭据注入和退出码，禁止无密码或明文密码命令继续执行。
- GREEN: formal-route-process-identity-contract -> PASS，冻结 app 的 `docs/backend-development.md` 明确要求：候选快照身份必须逐项解析并证明唯一映射，任一身份不唯一必须阻塞；发布继承必须使用冻结快照中的正式 `routeProcessId`，不得按 `processId`、工序名称、`sort` 或运行态 fallback 回读旧 ID。该正式文档契约与本轮 `mappingSourceFound=false` 结论一致。
- P065：现象=一次扩大范围的 `rg` 源码/文档搜索输出过大并被截断，混入大量历史任务和 SQL 内容；阶段=历史映射来源搜索；影响=增加审计读取成本，不能把截断输出当作完整证据；原因判断=绝对路径下的排除模式未达到预期，搜索边界过宽；处理动作=立即停止会话，不保存或提交原始输出，改用已确认的 `docs/backend-development.md` 和限定目录搜索；结果=取得正式身份契约，但未发现旧新映射；是否可前置检查=是；是否可自动化=是；下次如何避免=搜索前先用 `rg --files` 固定白名单，排除历史任务/runtime/生成物并设置输出上限，截断即视为无效证据。
- P066：现象=一次限定搜索引用不存在的 `D:\IntRuoyiWorktree\r260822a\a\IntRuoyiBackend\doc\tasks\20260809-active-order-release-dossier-v4-delivery` 路径，返回系统找不到指定文件；阶段=历史映射来源搜索；影响=该路径未形成证据，无代码或服务器副作用；原因判断=把 app 根目录下的任务路径误套到 backend 子目录；处理动作=停止错误路径，改读实际存在的 `D:\IntRuoyiWorktree\r260822a\a\docs\backend-development.md` 和已确认任务目录；结果=正式规则核对通过，映射来源仍缺失；是否可前置检查=是；是否可自动化=是；下次如何避免=任何限定搜索先用 `Test-Path -LiteralPath` 和 `rg --files` 验证目录，再执行内容搜索。
- P067：现象=最终 worktree JSON 核对命令再次把 `foreach` 语句块直接接到管道，PowerShell 报 `An empty pipe element is not allowed`；阶段=任务证据最终复核；影响=首次核对未执行，造成极短延迟，无文件、Git 或服务器副作用；原因判断=重复使用已记录的 PowerShell 管道语法错误模式；处理动作=改为先收集数组再统一 `ConvertTo-Json`，随后成功核对两个 worktree；结果=维护 HEAD=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`、app HEAD=`c4d2c637bf1f2cea723876ee363f311b1128aaf4`，均 detached clean；是否可前置检查=是；是否可自动化=是；下次如何避免=复杂 PowerShell 语句必须先保存中间结果，禁止语句块直接作为管道左值，并将该检查固化为 UTF-8 `.ps1` 脚本。
- 长过程阶段记录（2026-08-22 历史证据补充）：当前进度=剩余 blocker 的历史身份来源已核查；已完成=三份备份表交叉读取、当前路线只读对照、证据 JSON 落盘；阻塞点=没有正式旧新映射；耗时原因=需要区分“历史身份证据”与“可用于修复的映射证据”，并处理一次凭据注入错误；下一步动作=保持 `blocked`，等待正式映射或经批准的可审计修复方案，之后才可重新创建发布输入和 releaseTag。
- 结论：本轮仍不构建、不发布、不重试 `release-20260822-intmain-head-test-r260822a-r2`；不执行 `READINESS` 以制造成功结论，不执行 `mark-tested`、`promote-prod`、`promote-backup`，发布 worktree 继续保留。

## 2026-08-23 formal mapping proof and repair iteration

- `GREEN: route-snapshot-formal-mapping-proof -> PASS`，历史备份表 `m3syncbk_20260731025926_schedproc` 与当前 `mes_pro_route_version.id=3` 快照已形成唯一 1:1 映射：`900124 -> 926785`、`900125 -> 926786`、`900126 -> 926787`、`900127 -> 926788`；对应历史 process `900331/900333/900370/900371` 与当前 process `922894/922895/922896/922897`，排序与名称一致、当前 routeProcessId 互不重复。
- `GREEN: route-snapshot-repair-sql-r3-preflight -> PASS`，已生成 task-owned 修复 SQL `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260821-test-only-head-release\evidence\route-snapshot-repair-r260822a-r3.sql`；修复边界仅限 test server 的 `mes_pro_route_version.id=3`，只改 `configSnapshots.scheduleConfigs[0..3].routeProcessId` 并清空 `route_snapshot_sha256` / `route_snapshot_format_version`，不触碰正式服、备份服、migration ledger 或 release lock。
- 下一步动作：按现有发布脚本同源的 test-only DB 入口应用该 SQL，再立即重跑 route snapshot BACKFILL / READINESS；如果仍非 `READY/0`，继续阻断，不将旧 blocker 误判为成功。

## 2026-08-23 发布重试失败与状态收束

- GREEN: experience-preflight -> PASS：本轮仅允许测试服写入；已确认目标 host/runtime、冻结提交、发布包、官方 test-only DB 入口和禁止正式/备份服动作边界。
- 发布输入保持冻结：maintenance=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`，app=`c4d2c637bf1f2cea723876ee363f311b1128aaf4`；worktree 分别为 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260822a\m`、`D:\IntRuoyiWorktree\r260822a\a`；r2 包为 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260822-intmain-head-test-r260822a-r2`。
- 正确冻结发布脚本已完成远端数据盘、compose、`.env`、镜像包和 smoke 资源同步，但在 route snapshot enforcement 阶段失败，未发生 backend/frontend 容器切换；远端 `.env` 的目标 tag 与实际运行镜像不一致，故不能做运行态成功验证。
- 问题记录 P068-P075 已同步写入 `task.md`；问题覆盖脚本来源、MinIO 容器名、smoke 环境契约、`.env` 解析、PowerShell 内联脚本、敏感进程输出、失败状态收束和 worktree 行尾状态。
- `stale-release-state-recovery-r260822a-r2.sql` 已生成，范围仅为该 releaseTag 对应的 test operation lock 与 route migration 两行；执行前必须复核 SHA、目标条件、无凭据和无危险 SQL。
- 当前结论仍为 `blocked/NO-GO`：需先恢复 stale `RUNNING` 状态并核验 `RUNNING=0`，随后为 P070 走正式代码修复、新冻结 worktree、新 releaseTag、重建和完整测试服验证闭环；不得复用 r2 产物判成功。
- P076：第一份恢复 SQL 只更新了 operation lock；只读元数据显示 migration 行的 `operation_id=release-20260822-intmain-head-test-r260822a-r2`，而 lock 行为 `test-release-20260822-intmain-head-test-r260822a-r2`。原 SQL 条件不匹配 migration，未清除其 `RUNNING` 状态。
- P077：一次未限定 migration_id 的 releaseTag 查询输出被截断，原始输出未写入证据；后续仅保留精确 migration 行和 `RUNNING` 计数作为判断依据。
- 已生成精确 recovery SQL：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260821-test-only-head-release\evidence\stale-migration-recovery-r260822a-r2.sql`；下一步仅通过官方 test-only DB 入口执行，并核验该行=`FAILED`、test `RUNNING` migration/lock 均为 `0`。
- 2026-08-23 只读复核：精确 recovery SQL 已执行成功，`infra_release_operation_lock` 与 `infra_release_migration` 均为 `FAILED`，test 环境 `RUNNING` lock/migration 均为 `0`；这只是失败状态收束，发布本身仍未成功。

## 2026-08-23 scheduler smoke env repair iteration

- BDD: scheduler smoke remote env propagation -> Given deploy-release copies the scheduler smoke runner to the test server, When remote npm wrapper commands run install/exec/check, Then `MES_SMOKE_NODE_IMAGE` must be exported inline so the wrapper can resolve the node image without sourcing the full `.env`.
- RED: `python -X utf8 -m pytest D:\IntRuoyiWorktree\r260823a\a\IntRuoyiBackend\script\tests\test_scheduler_smoke_release_contract.py -q` -> FAIL, current publish script does not export `MES_SMOKE_NODE_IMAGE` to the remote scheduler smoke wrapper commands.
- GREEN: `python -X utf8 -m pytest D:\IntRuoyiWorktree\r260823a\a\IntRuoyiBackend\script\tests\test_scheduler_smoke_release_contract.py -q` -> PASS after patching the three remote smoke invocations to prefix `MES_SMOKE_NODE_IMAGE='$effectiveMesSmokeNodeImage'`.
- 发布重试收获：`-TestServerHost` 和 `-BackupServerHost` 需要显式传入，脚本会 fail fast；补齐后 deploy-release 才进入 NAS、compose、镜像、remote env 和 smoke 复制阶段。
- 当前状态：新 worktree `D:\IntRuoyiWorktree\r260823a\a` 已创建，branch=`codex/release-smoke-node-image-export`；脚本修复尚未提交，也未重新构建新的 releaseTag。
