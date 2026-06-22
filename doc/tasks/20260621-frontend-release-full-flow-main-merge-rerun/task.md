# 任务：主程序合并后重新走页面发布全链路

## 任务目标

在主程序合并新代码后，重新通过运行控制台前端页面，严格执行一次“构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”的完整链路，确认当前主程序基线仍然满足真实页面发布流程。全过程禁止用接口直调替代页面提交；遇到任一步失败，必须先记录到任务文档，再修复并从页面重走，直到单次链路一次性通过。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-rerun\task.md`
- 状态：`COMPLETED`
- 处理：上一任务完成的是“基于现有 v6 证据和远端运行态的完成审计”，证明旧链路曾完整走通；本任务是因主程序合并后担心当前基线已发生变化而重新发起的真实页面全链路重跑，属于新的高风险验证任务，需单独建档。

## 用户要求与执行边界

- 用户要求：
  - 主程序合并修改了部分代码后，重新再走一遍真实页面发布流程
  - 仍然必须按页面前端点击操作走完整链路
  - 禁止直接调接口替代页面动作
  - 每遇到问题先记录到任务文档，修复后继续从页面走
- 当前任务边界：
  - 当前验证目标基线已更新为 clean release backend worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean` 提交 `49248d9f20`（由业务后端主仓提交 `314ebb2204` cherry-pick 而来，已纳入 release transaction permission 漂移修复）
  - 当前验证目标基线是 clean release frontend worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean` 提交 `37359a074`
  - 维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 当前分支为 `int_main`，存在 `backup-ops` 相关未提交改动，但 `ops/deploy` 与运行控制台页面发布链路本次未发现未提交更改
  - 高风险动作前必须在 `execution-log.md` 中记录 `GREEN: experience-preflight -> PASS`

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 构建发布包必须通过运行控制台页面按钮真实提交，命令行只允许做只读核验、失败排查和脚本/测试辅助。
  - 发布前必须确认当前运行控制台实例可用、当前业务前后端基线明确、目标环境明确、目标 `releaseTag` 唯一。
  - 每次主程序发布输入发生变化后，必须使用新的 `releaseTag` 重建并从测试服开始整链重走。
  - 发布验证不能只看健康检查，必须同时核 operation、发布包 manifest、远端 `.env`、运行镜像、页面入口和受保护边界。
  - 正式服和备份服都属于高门禁环境，必须使用已测试通过发布包，并保持 `PROD` 确认语义。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。若当前主程序合并引入任何发布链路问题，必须修正式代码/脚本/契约后再从页面重跑。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 合并后页面真实发布全链路仍可通过 -> Given 主程序前后端已合并新代码且运行控制台可访问 / When 在页面上依次执行构建发布包、部署测试服、标记测试通过、上线正式服、上线备份服 / Then 每一步都必须由真实页面动作触发并最终成功。`
- `BDD: 合并后若链路失败必须先记录再修复重走 -> Given 任一步页面动作或后台执行因当前主程序基线失败 / When 记录失败证据并修复 / Then 必须先把失败与根因写入执行日志，再从页面重新走完整链路直到一次性通过。`

## 里程碑

1. 建立本任务文档，确认上一任务已完成并锁定当前业务前后端与维护仓基线。`DONE`
2. 完成 `experience-preflight`、本机控制台可用性检查与页面提交前预检。`DONE`
3. 通过页面真实执行构建发布包并完成候选包核验。`DONE`（最新有效候选包为 `release-20260621-page-full-flow-mainmerge-v15`）
4. 通过页面真实部署测试服并完成只读运行态验证。`PENDING`（`v14` 证据已失效，需重新执行 `deploy-test(v15)`）
5. 通过页面真实标记测试通过并确认恢复候选/测试结论。`PENDING`（`v14` 证据已失效，需重新执行 `mark-tested(v15)`）
6. 通过页面真实上线正式服并完成运行态与受保护边界验证。`PENDING`
7. 通过页面真实上线备份服并完成运行态与受保护边界验证。`PENDING`
8. 汇总本轮问题、修复、最终通过证据并执行收尾预览。`PENDING`

## 预期验证

- `execution-log.md` 在任何真实写入前存在 `GREEN: experience-preflight -> PASS`
- 明确记录本轮使用的新 `releaseTag` 以及前后端/维护仓基线
- build/test/mark-tested/prod/backup 每一步都存在真实页面触发的 operation ID、状态和日志路径
- 测试服/正式服/备份服远端 `.env` 与运行镜像都切到本轮新 `releaseTag`
- 正式服与备份服 `config_id=28 AND path LIKE 'showroom/%'` 的受保护 URL 边界未漂移
- 若发现问题，存在对应 BDD、失败记录、修复记录和整链重跑证据

## 当前状态

IN_PROGRESS：`2026-06-22` 真实页面 `build-release(v15)` 已成功，operation `op-2026-06-22T121006967109700Z-6dc95b22-9d29-4a00-b432-9cdd4e34bc51` 收口为 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v15\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v15.tar`，且 manifest 已核对 backend commit=`49248d9f20db9e3100bc5f492c7027d4de065f32`、frontend commit=`37359a074cedcc0a341f17cb0abdd1a71f838731`、两仓 `dirty=false`。下一步必须继续复用真实页面会话 `frontend-release-full-flow-mainmerge` 执行 `deploy-test(v15)`，旧 `v14` build/test/mark-tested/prod 证据不得复用。

BLOCKED：`2026-06-22` 真实页面 `deploy-test(v4)` 暴露的 `20260618_mes_edhr_label_print_queue.sql` 菜单主键冲突，已在业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-label-print-menu-id-collision-fix\` 按严格 TDD 修复并通过回归，且修复提交已落盘为 `6d96efef31`。只读证据确认 `900272-900279` 被独立表单占用、`900280-900283` 被其他 eDHR 菜单占用，因此 label print 菜单已切换到独立的 `900320-900331` 号段；`pytest`、迁移策略门禁与真实页面 `build-release(v5)` 均已通过，NAS 产物目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v5`。

`2026-06-22` 继续在真实页面预览 `deploy-test(v5)` 时，测试服预览显示 `-RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1`。这组参数一度被怀疑为漂移，但随后已通过只读核对 `backend/src/main/resources/application.yaml`、`ops/deploy/publish-int-ruoyi.ps1` 环境映射、历史真实通过证据以及测试服 `show-int-ruoyi-remote-status.ps1` 运行态验证为当前测试服真实基线，实机状态返回 `running` 且当前运行标记为 `release-20260621-page-full-flow-mainmerge-v4`。因此本轮未出现新的配置阻塞，真实页面已继续提交 `deploy-test(v5)`。

`2026-06-22` 新的真实阻塞点出现在 `deploy-test(v5)` 远端执行中：operation `op-2026-06-21T224939775740400Z-71e88cac-530c-41f0-a189-d2ca59292b50` 在测试服 required SQL `20260618_mes_edhr_oq_pq_execution_deviation.sql` line 357 因 `Invalid eDHR OQ/PQ button menu definition; cannot merge tenant package menu_ids` 失败。日志同时确认此前的 `20260618_mes_edhr_label_print_queue.sql` 已成功跨过，说明当前主阻塞已切换到新的 OQ/PQ 菜单定义冲突。按任务门禁，下一步必须先在业务后端按严格 TDD 修复该根因；由于发布包输入将再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v5` 不可继续使用，修复后必须以新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test`，再继续后续链路。

`2026-06-22` 上述 OQ/PQ 根因已在业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-oq-pq-menu-definition-fix\` 按严格 TDD 修复完成并正式提交。当前只读源码与测试服真实 `system_menu` 共同证明：旧号段 `900290-900295` 中，`900290-900292` 与其他 eDHR SQL 存在直接复用，`900293-900295` 已被 `eDHR统一变更` 占用，因此 OQ/PQ 菜单整体切换到独立未占用的 `900332-900337`，并加入 `tmp_mes_edhr_oq_pq_legacy_menu_map` 吸收测试库已经落下的旧 OQ/PQ 页面/按钮残留。当前业务修复已通过 `python -X utf8 -m pytest ...test_edhr_oq_pq_schema_sql.py -q`、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...` 与 bug regression validator，提交已落盘为 `0d82319b98`（功能修复）和 `3ace5094ec`（补充回归证据）。由于发布包输入已再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v5` 已失效；下一步必须通过真实页面以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v6`）重新执行 `build-release -> deploy-test`，再继续后续链路。

`2026-06-22` 真实页面已按新输入基线重新执行 `build-release(v6)`，operation `op-2026-06-21T232456287004700Z-51059473-149c-41e4-8fe3-14e2d4a9d7cb` 最终 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v6\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v6.tar`，NAS 发布目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v6`。`manifest.json` 确认 `releaseTag=release-20260621-page-full-flow-mainmerge-v6`、`publishScope=code-only`，并记录 backend 源提交 `3ace5094ec7768237e7249b876a4eca67dad5e2a`、admin frontend 源提交 `37359a074cedcc0a341f17cb0abdd1a71f838731`。

`2026-06-22` 继续准备 `deploy-test(v6)` 前，只读核对 `manifest.json sourceRepos` 与当前源码仓状态时发现新的高风险前置差异：backend 与 admin frontend 在候选包中都被标记为 `dirty=true`。当前 `git status --short` 证明业务后端存在 DCC 文件名识别相关未提交改动（`DccControlledFileProjectCodeRecognitionService*` 等），业务前端存在 DCC 受控预览相关未提交改动（`src/views/dcc/controlled-file/detail/index.vue` 等）。影响：`release-20260621-page-full-flow-mainmerge-v6` 并非“纯已提交 merged main 基线”候选包，而是混入未提交 DCC 工作树改动的 dirty baseline；按 fail-fast 门禁，在未明确这些 dirty 改动是否应纳入本轮真实发布链路前，不应继续 `deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 为消除 dirty baseline 影响，已新建成对 clean release worktree：后端 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro`（branch `codex/20260622-page-full-flow-mainmerge-release-clean`，HEAD `3ace5094ec`，`git status --short` 为空）、前端 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3`（branch `codex/20260622-page-full-flow-mainmerge-release-clean`，HEAD `37359a074`，`git status --short` 为空）。同时已将本机运维台局部配置 `config/runtime-control.local.yaml` 的 `repo-root` / `frontend-root` 切换到这两个 clean worktree，准备重启运维控制台后继续保持“页面按钮触发”的真实链路。

`2026-06-22` 已重新打开运行控制台并核验页面预览弹窗，确认 `build-release` 预览参数已经指向上述 clean worktree；当前需要在真实页面重新提交新的 `releaseTag` 后，从头再走一遍构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服，不能沿用旧的 dirty baseline 结果。

`2026-06-22` 真实页面 `build-release(v7)` 已成功提交到 clean worktree 基线，但 operation `op-2026-06-21T234844686010400Z-12704e02-b10c-472d-af05-cb4b5ff828c3` 在前端打包阶段失败：`D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3\node_modules\vite\bin\vite.js` 缺失，说明 clean frontend worktree 的依赖现场尚未完成 bootstrap。当前发布包未生成，不能继续测试服/正式服/备份服；必须先补齐 clean worktree 依赖，再用新的 `releaseTag` 从真实页面重新执行 build-release。

`2026-06-22` 上述 clean frontend worktree 依赖阻塞已完成现场修复：确认 `node_modules` 原先不存在后，已在 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3` 执行 `pnpm install --frozen-lockfile`，随后 `pnpm build:test` 成功输出 `Build successful. Please see dist-test directory`。当前 clean worktree 前端依赖前置条件已恢复，下一步可回真实页面用新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v8`）重新提交 `build-release`。

`2026-06-22` 真实页面 `build-release(v8)` 已成功通过，operation `op-2026-06-22T000330671317300Z-c009a2ba-8bcf-4210-b73a-2a09a4a1e424` 收口为 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v8\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v8.tar`，NAS 目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v8`。`manifest.json` 已核对 backend/front commit 分别为 `3ace5094ec` / `37359a074`，且 `sourceRepos.dirty` 均为 `false`，说明当前候选包已回到 clean release baseline。下一步继续从真实页面执行 `deploy-test(v8)`。

`2026-06-22` 真实页面 `deploy-test(v8)` 已提交，operation `op-2026-06-22T001514869158500Z-1d251735-38f1-43d5-afe3-c40e4b603a8e` 最终在测试服 required SQL `20260618_mes_edhr_oq_pq_execution_deviation.sql` line 399 失败，错误为 `Missing eDHR OQ/PQ system_menu rows; cannot merge tenant package menu_ids`。日志确认此前的 `20260613_dcc_file_view_matrix_seed`、`20260615_showroom_hall_canvas_background`、`20260618_mes_edhr_label_print_queue` 与 `20260618_post_release_role_e2e_gate` 都已成功跨过，说明当前主阻塞已切换为 OQ/PQ 菜单行缺失，而不是旧的按钮定义冲突。

`2026-06-22` 随后对测试服 `172.30.30.58` 做只读 `system_menu` 核对，确认当前真实库里 `900332-900337` 仅存在 `900335-900337` 三条，`900332-900334` 缺失，且旧 OQ/PQ `900290-900292` 也已不存在；这说明当前 SQL 仍存在 cleanup 顺序缺陷：先按旧 `path/permission` 存在而跳过新 `900332-900334` 插入，再删除 legacy `900290-900292`，最终把页面/查询/创建三条一起删空，只剩执行/复测/关闭三条。按门禁，下一步必须在业务后端按严格 TDD 修复该正式 SQL 顺序问题；由于发布包输入将再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v8` 不可继续使用，修复后必须通过真实页面以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v9`）重新执行 `build-release -> deploy-test`，之后才能继续 `mark-tested -> prod -> backup`。

`2026-06-22` 上述 cleanup 顺序根因已在业务仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-oq-pq-legacy-cleanup-order-fix\` 按严格 TDD 修复完成，并通过 `pytest`、迁移策略门禁与 bug regression validator。当前维护仓必须改用新的 `releaseTag` `release-20260621-page-full-flow-mainmerge-v9` 重新构建发布包，然后继续真实页面 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 真实页面已按新输入基线完成 `build-release(v9)`，operation `op-2026-06-22T010042891831400Z-d59751ca-ab81-4136-b128-0f98537c2cd5` 最终 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v9\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v9.tar`，NAS 发布目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v9`。`manifest.json` 已核对 backend/frontend 源提交分别为 `3ace5094ec7768237e7249b876a4eca67dad5e2a` / `37359a074cedcc0a341f17cb0abdd1a71f838731`，且 `sourceRepos.dirty=false`，说明本轮 v9 候选包仍保持 clean release baseline。

`2026-06-22` 随后真实页面提交 `deploy-test(v9)`，operation `op-2026-06-22T011513436036700Z-42784c13-1bca-48e9-b0a9-fa51f2309f0a` 最终 `FAILED`；远端日志确认前一轮 OQ/PQ 阻塞已跨过，新的失败切换为 `20260618_mes_edhr_print_policy_reissue_void.sql` line 103 的 `Duplicate entry '900285' for key 'system_menu.PRIMARY'`。影响：`release-20260621-page-full-flow-mainmerge-v9` 无法继续用于 `mark-tested -> prod -> backup`；下一步必须先在业务后端记录并修复该 `system_menu` 主键冲突，再改用新的 `releaseTag` 从真实页面重新 `build-release -> deploy-test`。

`2026-06-22` 上述 print policy 根因已在业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-print-policy-menu-id-collision-fix\` 按严格 TDD 修复完成，并通过 `python -X utf8 -m pytest ...test_edhr_print_policy_reissue_schema_sql.py -q`、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...` 与 bug regression validator。当前 clean release backend worktree 已补齐 cherry-pick：功能修复提交为 `ca023336e9`、回归证据提交为 `a72602e2f0`，前端 clean worktree 仍为 `37359a074`。由于发布包输入再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v9` 已失效；下一步必须通过真实页面以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v10`）重新执行 `build-release -> deploy-test`，测试服通过后再继续 `mark-tested -> prod -> backup`。

`2026-06-22` 真实页面 `build-release(v10)` 已成功收口，operation `op-2026-06-22T030125335519200Z-62e5f1af-95d5-4011-9983-9f1c03771bf7` 最终 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v10\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v10.tar`，NAS 发布目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v10`。`manifest.json` 已核对 backend/frontend 源提交分别为 `a72602e2f0` / `37359a074`，且 `sourceRepos.dirty=false`，说明当前候选包继续保持 clean release baseline。

`2026-06-22` 随后真实页面提交 `deploy-test(v10)`，operation `op-2026-06-22T031709289783300Z-b87c3859-b5bf-4f2c-b03f-008cf8d5e7b3` 最终 `FAILED`。远端日志确认此前阻塞的 `20260618_mes_edhr_print_policy_reissue_void.sql` 已在真实测试库成功 `APPLIED`，新的失败切换为 `20260618_mes_edhr_dhr_template_lifecycle.sql`：MySQL 在 line `120` 抛出 `ERROR 1062 (23000): Duplicate entry '900293' for key 'system_menu.PRIMARY'`。只读核对测试服 `system_menu` 现场已确认 `900290-900292` 是当前 DHR 模板菜单本身，而 `900293-900299` 已被 `20260618_mes_edhr_unified_change_impact.sql` 的“eDHR统一变更”整段占用，因此当前 DHR 模板按钮仍复用冲突号段。

`2026-06-22` 按“先记录再修复”门禁，本轮 `deploy-test(v10)` 失败已先在维护仓任务文档落盘。影响：`release-20260621-page-full-flow-mainmerge-v10` 无法继续用于 `mark-tested -> prod -> backup`；下一步必须在业务后端新建严格 TDD 修复任务，给 `20260618_mes_edhr_dhr_template_lifecycle.sql` 切换独立未冲突菜单号段并通过回归验证，随后改用新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 上述 DHR 模板根因已在业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-dhr-template-menu-id-collision-fix\` 按严格 TDD 修复完成，并通过 `python -X utf8 -m pytest ...test_edhr_dhr_template_schema_sql.py -q`、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...` 与 bug regression validator。当前 clean release backend worktree 已补齐 cherry-pick：修复提交为 `d9606a65df`，前端 clean worktree 仍为 `37359a074`。由于发布包输入再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v10` 已失效；下一步必须通过真实页面以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v11`）重新执行 `build-release -> deploy-test`，测试服通过后再继续 `mark-tested -> prod -> backup`。

`2026-06-22` 真实页面随后已实际提交 `build-release(v11)`，operation `op-2026-06-22T034606591995400Z-87264c6d-8e7b-4b5f-801f-e8b6e91e555f` 最终 `FAILED`。本机构建在进入 Maven/Vite 打包前就被维护仓新增的 SQL 预检门禁拦下，报错为 `system_menu.id must be an integer literal for release preflight: .../20260520_system_nas_management_menu.sql:11 -> \`name\``；失败文件是合法 SQL，包含 `ON DUPLICATE KEY UPDATE ... VALUES(\`name\`)`，说明当前维护仓 `release_sql_contract_gate.py` 对 `VALUES(...)` 更新子句存在误判。影响：基于 DHR 模板修复后的最新 clean baseline 目前连新的候选发布包都无法生成，因此测试服/正式服/备份服链路全部暂停；按“先记录再修复”门禁，必须先在维护仓按严格 TDD 修复该 SQL 预检解析根因，再改用新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v12`）从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 上述维护仓 SQL 预检误判根因已在维护仓任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-sql-preflight-gate\` 按严格 TDD 修复完成：新增回归用例覆盖合法 `ON DUPLICATE KEY UPDATE ... VALUES(...)` 菜单 SQL，`release_sql_contract_gate.py` 现只解析真正 `VALUES (...)` 顶层插入元组，已经不再把更新子句里的 `VALUES(\`name\`)` 误当成新的 `system_menu` 记录。当前回归已通过维护仓 `pytest`、showroom 发布合同测试和真实 clean release backend SQL 根目录门禁，因此下一步可以回真实页面以新的 `releaseTag` `release-20260621-page-full-flow-mainmerge-v12` 重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 真实页面 `build-release(v12)` 已最终 `SUCCESS`，operation `op-2026-06-22T040752788980600Z-65f35dd8-4afa-4a4e-a9ee-5f04a5dd500a` 完整跨过本机 SQL 预检、clean backend Maven 打包、clean frontend Vite 打包、backend/frontend Docker 镜像构建、镜像导出与 NAS 上传，日志落盘 `Release package built: release-20260621-page-full-flow-mainmerge-v12`、`NAS release path: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v12`。本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v12\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v12.tar`，其中 `manifest.json` 已核对 backend/front source commit 分别为 `d9606a65dfb4bfd4151970e3393e77be5f13a0c5` / `37359a074cedcc0a341f17cb0abdd1a71f838731`，且两仓 `dirty=false`。下一步必须继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，对同一 clean baseline 执行 `deploy-test(v12)`，再根据结果继续 `mark-tested -> prod -> backup` 或按门禁记录新问题后修复重走。

`2026-06-22` 真实页面 `deploy-test(v12)` 已提交，operation `op-2026-06-22T042335374179300Z-b8f08a6e-3f7d-431a-91b3-df481bd92388` 最终 `FAILED`。当前失败点已不再是前几轮反复暴露的 eDHR 业务 SQL，而是测试环境发布锁阶段：日志确认镜像包与 `required-sql` 已同步到测试服、`post-import.sql` 已成功执行、`20260613_infra_release_migration_state.sql` 已完成 bootstrap，随后在 `infra_release_operation_lock` 的测试环境锁获取步骤中，本机脚本通过 `grep '^LOCK_ACQUIRED$'` 断言锁获取结果时收到退出码 `1`，继而把当前 operation 标记为 `FAILED` 并释放当前尝试的锁记录。影响：`release-20260621-page-full-flow-mainmerge-v12` 尚未进入 required SQL 正式执行、更未完成测试服容器切换，因此不能继续 `mark-tested -> prod -> backup`；按“先记录再修复”门禁，下一步必须先只读核对测试服 `infra_release_operation_lock` 当前真实状态与脚本锁契约，再决定是否需要在维护仓按严格 TDD 修复锁处理根因，修复后再以新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 随后的只读锁现场审计已经把根因进一步收敛。首先，本地维护仓回归 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py -q` 仍然 `2 passed`，说明此前修复过的“持锁后 fail-fast 先释放 `infra_release_operation_lock` 再退出”契约没有被主程序合并回退。其次，测试服当前库里原先阻断 `deploy-test(v12)` 的 `infra_release_operation_lock` 现场并不是本次页面链路自己遗留的锁，而是另一条外部链路 `operation_id=test-20260622_121338` / `release_tag=20260622_121338` 留下的测试环境 `RUNNING` 锁；到本次审计时，这条锁已经被其他流程手动收口为 `FAILED`，`finished_at=2026-06-22 12:45:12`，`error_message='Recovered stale RUNNING lock after 20260622 DCC preview release failures; later fixes require retry.'`。同时只读核对确认测试服已出现共享环境漂移：`.env` 当前 `IMAGE_TAG=20260622_123255`，但运行容器仍混杂为 backend `release-20260621-page-full-flow-mainmerge-v10`、frontend `release-20260621-page-full-flow-v6`，并不存在新的 `RUNNING` 迁移。这说明当前主阻塞已经不再是“维护仓脚本需要继续修”，而是“共享测试环境被外部失败发布链路改写成半切换状态”。由于本轮发布包输入没有变化、维护仓也无需新增代码修复，下一步不应重新 `build-release`；应先把这次共享环境漂移记录为门禁，再继续通过真实页面对同一 `release-20260621-page-full-flow-mainmerge-v12` 重新执行 `deploy-test`，待测试服重新回到本任务候选包后再继续 `mark-tested -> prod -> backup`。

`2026-06-22` 已按上述判断重新通过真实页面对同一 `release-20260621-page-full-flow-mainmerge-v12` 执行第二次 `deploy-test` 重试，operation `op-2026-06-22T045846454437200Z-f0e05484-deef-41e1-b3b6-a0d6b64829b4` 在页面侧成功提交，且只读日志确认这次至少已经把测试服 `.env` 从外部漂移标签重新拉回 `IMAGE_TAG=release-20260621-page-full-flow-mainmerge-v12`，同时后端容器也切到了 `intruoyi-backend:release-20260621-page-full-flow-mainmerge-v12`。但该次真实页面链路最终仍在同一把测试环境发布锁处失败；失败时锁现场已经不是前一条 `test-20260622_121338`，而是另一条更晚出现的外部记录 `operation_id=test-20260622_124533` / `release_tag=20260622_124533`，状态仍为 `RUNNING`，`started_at=2026-06-22 12:56:16`，且对应目录 `/var/lib/docker/intruoyi-releases/20260622_124533/` 完整存在。与此同时，远端运行控制目录 `/opt/intruoyi/runtime/data/runtime-control/` 并没有任何与 `20260622_124533` 相关的新 operation JSON 或 log，`pgrep -af 'publish-int-ruoyi|backup-ops|runtime-control|deploy-release|20260622_124533'` 只看到长期驻留的运行控制 Java 进程，没有可归属到这条外部发布的活跃 shell / publish 进程。这说明当前测试服再次被另一条没有本地 operation 证据的外部 stale `RUNNING` 锁阻断；按此前 `20260618-build-test-backup-release` 与 `20260620-frontend-release-full-flow` 的处理先例，下一步必须先在任务文档补齐数据库状态修复证据，再在确认无活跃发布进程前提下，将 `test-20260622_124533` 从 `RUNNING` 收口为 `FAILED`，然后继续通过真实页面对同一 `release-20260621-page-full-flow-mainmerge-v12` 重试 `deploy-test`。

`2026-06-22` 随后又补做了一轮只读复核，确认上述 stale 锁并未自行收口：测试服 `infra_release_operation_lock` 当前仍只有 `test-20260622_124533 / 20260622_124533` 这一条 `RUNNING` 锁；`infra_release_migration` 当前 `RUNNING` 数量为 `0`；远端运行控制目录中仍查不到任何包含 `20260622_124533` 的 operation 证据，远端进程列表里也依然没有新的 `publish-int-ruoyi|backup-ops|deploy-release|20260622_124533` 活跃 shell。与此同时，测试服当前已保持在 `.env IMAGE_TAG=release-20260621-page-full-flow-mainmerge-v12`、backend `release-20260621-page-full-flow-mainmerge-v12`、frontend 仍为 `release-20260621-page-full-flow-v6` 的半切换态，证明锁阻断仍在阻止本任务把前端也切回 `v12`。因此本轮最新结论没有变化：仍应先按先例完成这条 stale 锁的恢复性收口，而不是重建新的发布包；相关恢复计划和回滚边界已经补充到 `database-schema-evidence.md`，接下来在校验证据通过后即可执行最小回写，再回到真实页面继续点击 `deploy-test(v12)`。

`2026-06-22` 上述恢复性收口已执行完成：先用 `validate_database_schema.py` 校验 `database-schema-evidence.md` 通过，再仅对测试服 `infra_release_operation_lock` 中 `test-20260622_124533 / 20260622_124533 / target_environment=test / status=RUNNING` 这一条外部 stale 锁做最小回写，`ROW_COUNT()=1`。回写后的只读复核确认该锁已改为 `FAILED`，`finished_at=2026-06-22 13:22:21`，同时测试环境 `RUNNING` 锁数量已清零为 `0`、`infra_release_migration` 的 `RUNNING` 数量仍为 `0`。测试服当前运行态依旧是 `.env=v12`、backend=v12、frontend=v6` 的半切换现场，因此下一步不需要重建新的发布包，而是应立即回到真实页面继续第三次 `deploy-test(release-20260621-page-full-flow-mainmerge-v12)`，验证在锁已清零后测试服能否完成剩余切换。

`2026-06-22` 真实页面第三次 `deploy-test(v12)` 已最终 `SUCCESS`，operation `op-2026-06-22T052654342734600Z-d5c5e3f1-3079-4fca-a3c5-668d0651985a` 完整跨过剩余 required SQL、Quartz/showroom schema 检查、测试服 `backend/frontend` 容器重建、远端 readiness、scheduler smoke runtime 校验、测试服发布锁释放与远端临时文件清理。本机 operation JSON 已收口为 `status=SUCCESS / summary=命令执行完成`；只读复核确认测试服 `/opt/intruoyi/runtime/.env` 已为 `IMAGE_TAG=release-20260621-page-full-flow-mainmerge-v12`，`intruoyi-backend` 与 `intruoyi-frontend` 运行镜像都已切到 `release-20260621-page-full-flow-mainmerge-v12`，`http://172.30.30.58:48081/actuator/health` 与 `http://172.30.30.58:8081/` 均返回 HTTP `200`。至此里程碑 T4 已完成；下一步必须继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，执行 `mark-tested(v12)`，再继续 `prod -> backup`。
`2026-06-22` 在将运行控制台 `runtime-control.local.yaml` 的 `repo-root/frontend-root` 切换到真实宿主机 `D:/ProjectPackage/Int/IntRuoyiWorktrees/` 并重启本地运行控制台后，真实页面第三次重试 `mark-tested(v12)` 已最终 `SUCCESS`：页面预览确认 `-BackendRepoRoot/-FrontendRepoRoot` 已指向 `ruoyi-vue-pro-mainmerge-release-clean` 与 `yudao-ui-admin-vue3-mainmerge-release-clean`，operation `op-2026-06-22T072554546125100Z-902f2fa0-b550-42c4-ab7d-551ea179c8c3` 收口为 `status=SUCCESS / summary=命令执行完成`，本机日志明确记录 `Release package marked as tested: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v12`，并同步写入 `rollback-compatibility.json status=BLOCKED` 元数据。至此里程碑 T5 已完成；下一步继续复用真实页面会话 `frontend-release-full-flow-mainmerge` 执行 `上线正式服(v12)`，再继续 `上线备份服(v12)`。

`2026-06-22` 真实页面 `上线正式服(v12)` 已提交，operation `op-2026-06-22T074300534524700Z-82f9bc5a-9e16-466d-97ec-fe9173debb83` 最终 `FAILED`。运行态 JSON 收口为 `status=FAILED / summary=命令退出码非 0: 1`；本机日志确认正式服在成功跨过 `20260619_srm_d7_3_plan_framework.sql`、`20260620_srm_phase1_supplier_access_profile.sql`、`20260618_mes_edhr_print_policy_reissue_void.sql` 与 `20260618_mes_edhr_dhr_template_lifecycle.sql` 后，新的阻塞切换为 `20260618_mes_edhr_release_transaction_lifecycle.sql`：MySQL 在 line `341` 抛出 `ERROR 1644 (45000): Missing eDHR release transaction permission rows; cannot merge tenant package menu_ids`。日志同时确认正式环境发布锁已被脚本恢复性释放为 `LOCK_RELEASED`，因此当前阻塞不是环境锁遗留，而是首次只在正式库暴露出的 release transaction permission 菜单合并缺口。影响：`release-20260621-page-full-flow-mainmerge-v12` 无法继续用于 `上线备份服`；按任务门禁，下一步必须先在业务后端按严格 TDD 修复该正式 SQL 根因，再改用新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 上述 release transaction permission 漂移根因已在业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-release-transaction-permission-rows-fix\` 按严格 TDD 修复完成，并通过 `python -X utf8 -m pytest ...test_edhr_release_precheck_schema_sql.py -q`、`python -X utf8 -m pytest ...test_edhr_release_transaction_schema_sql.py -q`、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...` 与 `validate_bug_regression.py --evidence ...bug-regression-evidence.md`。业务后端主仓修复提交已落盘为 `314ebb2204`，clean release backend worktree 也已补齐 cherry-pick 为 `5c52f2ec42`；当前前端 clean worktree 仍为 `37359a074`。

`2026-06-22` 由于发布包输入已再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v12` 的 `build-release -> deploy-test -> mark-tested -> prod` 证据均不得复用为新输入的放行结果；下一步必须继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v13`）从页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`，直至同一输入基线一次性走通。

`2026-06-22` 真实页面已按上述新输入提交 `build-release(v13)`，operation `op-2026-06-22T092500401085900Z-a5a839af-c197-48a3-9124-e744c0d07f06` 最终 `FAILED`。日志确认 clean backend `5c52f2ec42` 的 Maven 打包已完整 `BUILD SUCCESS`，新的阻塞不是业务 SQL，而是 clean frontend worktree 的依赖现场缺失：`D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean\node_modules\vite\bin\vite.js` 不存在，导致运行控制台在进入前端 Vite 打包前即失败。影响：`release-20260621-page-full-flow-mainmerge-v13` 没有生成候选包，不能继续 `deploy-test -> mark-tested -> prod -> backup`；按任务门禁，下一步必须先恢复 clean frontend worktree 依赖并做本地 `pnpm build:test` 回归，再改用新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v14`）从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 上述 clean frontend 依赖阻塞已完成现场修复：只读确认 `node_modules` 原先整体缺失后，已在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\yudao-ui-admin-vue3-mainmerge-release-clean` 执行 `pnpm install --frozen-lockfile` 恢复依赖，再执行 `pnpm build:test` 成功输出 `Build successful. Please see dist-test directory`。当前 clean frontend worktree 的 Vite CLI 与 test 构建前置已恢复；下一步可以回真实页面继续复用会话 `frontend-release-full-flow-mainmerge`，以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v14`）重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 在上述依赖现场恢复后，真实页面已重新执行 `build-release(v14)`，operation `op-2026-06-22T100123490849400Z-8f1f4b81-4162-4a57-a67c-0859c55285f9` 最终 `SUCCESS`。本机日志确认 clean backend `5c52f2ec42` 与 clean frontend `37359a074` 已完整跨过 Maven/Vite 打包、backend/frontend Docker 镜像构建、镜像导出与 NAS 上传，最终输出 `Release package built: release-20260621-page-full-flow-mainmerge-v14`、`NAS release path: Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v14`。本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v14\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v14.tar`，且 `manifest.json` 已核对 backend/frontend source commit 分别为 `5c52f2ec4268212e71070d57a14f006202f337c8` / `37359a074cedcc0a341f17cb0abdd1a71f838731`、两仓 `dirty=false`。至此里程碑 T3 已按新输入基线重新完成；下一步必须继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，从页面真实执行 `deploy-test(v14)`，再继续 `mark-tested -> prod -> backup`。

`2026-06-22` 真实页面随后已继续执行 `deploy-test(v14)`，operation `op-2026-06-22T103019077626300Z-93205576-f574-4a58-8f1a-75914d4c0ae7` 最终 `SUCCESS`。本机日志确认本轮在测试服完整跨过远端磁盘前置、compose/.env 同步、镜像包与 `required-sql` 传输、`20260618_mes_edhr_release_precheck_engine.sql` 与 `20260618_mes_edhr_release_transaction_lifecycle.sql` 应用、Quartz/showroom schema 检查、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 校验、测试服发布锁释放与远端临时文件清理，最终输出 `Publish completed for test.`。只读复核确认测试服 `/opt/intruoyi/runtime/.env` 已为 `IMAGE_TAG=release-20260621-page-full-flow-mainmerge-v14`，`intruoyi-backend` 与 `intruoyi-frontend` 运行镜像都已切到 `release-20260621-page-full-flow-mainmerge-v14`，`http://172.30.30.58:48081/actuator/health` 与 `http://172.30.30.58:8081/` 均返回 HTTP `200`。至此里程碑 T4 已按新输入基线重新完成；下一步必须继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，从页面真实执行 `mark-tested(v14)`，之后再继续 `prod -> backup`。

`2026-06-22` 继续复用真实页面会话执行 `mark-tested(v14)` 后，操作记录新增 operation `op-2026-06-22T105023931297300Z-9ed9bfdf-0138-4517-a25c-f62380648280`，最终 `SUCCESS`。页面预览已确认执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-mainmerge-v14 -TestConclusion 回归通过，允许上线正式服（v14） -SelectedRecoverySetCandidateId restore:20260621-063218 -RecoverySetId 20260621-063218 ...`，且 `-BackendRepoRoot/-FrontendRepoRoot` 继续指向 `D:/ProjectPackage/Int/IntRuoyiWorktrees/ruoyi-vue-pro-mainmerge-release-clean` 与 `D:/ProjectPackage/Int/IntRuoyiWorktrees/yudao-ui-admin-vue3-mainmerge-release-clean`。本机运行态 JSON 已收口为 `status=SUCCESS / summary=命令执行完成`；日志确认 NAS 发布目录 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v14` 已写入测试通过结论，并同步记录 `rollback-compatibility.json status=BLOCKED` 元数据。至此里程碑 T5 已按新输入基线重新完成；下一步继续复用真实页面会话执行 `上线正式服(v14)`，之后再继续 `上线备份服(v14)`。

`2026-06-22` 真实页面随后已继续执行 `上线正式服(v14)`，operation `op-2026-06-22T112009502106400Z-21cf8b20-6eca-494a-9404-1d16285d1ad1` 最终 `FAILED`。本机运行态 JSON 收口为 `status=FAILED / summary=命令退出码非 0: 1`；日志确认正式服在成功跨过 `20260618_mes_edhr_release_precheck_engine.sql` 后，继续应用 `20260618_mes_edhr_release_transaction_lifecycle.sql` 时于 line `341` 抛出 `ERROR 1644 (45000): Missing eDHR release transaction permission rows; cannot merge tenant package menu_ids`。日志同时确认正式环境发布锁已被脚本收口为 `LOCK_RELEASED`。影响：尽管 `build-release(v14) -> deploy-test(v14) -> mark-tested(v14)` 已真实走通，但当前主程序基线仍无法通过真实页面完成正式服上线，因此 `release-20260621-page-full-flow-mainmerge-v14` 不能继续进入 `上线备份服`；按“先记录再修复”门禁，下一步必须先在业务后端按严格 TDD 修复该正式 SQL 根因，再改用新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 用户随后把当前线程目标切换为“按阶段一次性把 `D:\ProjectPackage\Int\IntRuoyi` holding 改动融合进真正的 `int_main`”。因此本任务在保留 `release-20260621-page-full-flow-mainmerge-v14` 已完成 `build-release -> deploy-test -> mark-tested` 以及 `prod(v14)` 失败证据的前提下，显式挂起，不再继续 `上线正式服 -> 上线备份服`。若后续恢复本任务，必须先确认当时的发布输入和环境状态是否仍允许直接续跑，必要时重新生成新的 `releaseTag`。

`2026-06-22` 当前线程已恢复继续推进“主程序合并后重新走页面发布全链路”。在 clean release backend worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\ruoyi-vue-pro-mainmerge-release-clean` 只读对比正式服/测试服 `system_menu` 后确认：正式库 `900266/900267/900268` 仍被 traveler 菜单占用，而旧 `20260618_mes_edhr_release_transaction_lifecycle.sql` 仍把放行事务 `reject / withdraw / event-query` 绑在这组三号段。业务后端已按严格 TDD 把三条放行事务菜单切换到独立的 `900353/900354/900355`，并同步更新 package menu merge 与 `system_role_menu` 合并逻辑；相关回归、迁移策略门禁与 bug regression evidence 校验均已通过，clean worktree 提交为 `49248d9f20`。由于 backend clean 发布输入已从 `5c52f2ec42` 更新到 `49248d9f20`，frontend clean worktree 仍为 `37359a074`，旧 `release-20260621-page-full-flow-mainmerge-v14` 的 build/test/mark-tested/prod 证据不得复用；下一步必须继续复用真实页面会话 `frontend-release-full-flow-mainmerge`，以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v15`）从页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
